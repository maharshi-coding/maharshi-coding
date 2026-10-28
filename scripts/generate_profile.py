#!/usr/bin/env python3
"""Generate the RPG profile from current, publicly visible GitHub API data.

Never publishes private repositories or unpublished PRs. Requires only Python 3.10+.
GH_DATA_TOKEN (optional PAT) > GH_TOKEN > GITHUB_TOKEN. With no token, public
REST requests work until the anonymous rate limit is reached.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

USER = "maharshi-coding"
ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DATA = ROOT / "docs" / "data" / "profile.json"
TOKEN = os.getenv("GH_DATA_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
FEATURED = ["ai-tutor-app", "FulfillFlow", "oss-agent", "seller-shield",
            "outfallwatch", "overturn", "agent-pixel-visualizer", "datahub-steward-squad"]
EMOJI = {
    "ai-tutor-app": "🧙", "FulfillFlow": "🤖", "oss-agent": "🧠",
    "seller-shield": "🛡️", "outfallwatch": "🌊", "overturn": "⚖️",
    "agent-pixel-visualizer": "👾", "datahub-steward-squad": "🗺️",
}
TAGLINES = {
    "ai-tutor-app": "Your AI tutor, powered by retrieval, voice and avatars",
    "FulfillFlow": "Warehouse robot navigation powered by ROS 2 and Gazebo",
    "oss-agent": "Human-approved AI agent for real open-source fixes",
    "seller-shield": "Multi-agent risk defense for independent sellers",
    "outfallwatch": "Low-power coastal sensor alerts and storm simulation",
    "overturn": "Stateful agent workflows for insurance denial appeals",
    "agent-pixel-visualizer": "Turns VS Code agent activity into a pixel-art world",
    "datahub-steward-squad": "MCP-powered multi-agent metadata governance",
}


def github(path, params=None, graphql=None):
    if graphql is not None:
        url = "https://api.github.com/graphql"
        body = json.dumps({"query": graphql}).encode("utf-8")
    else:
        url = "https://api.github.com" + path
        if params:
            url += "?" + urlencode(params)
        body = None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "maharshi-rpg-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    if body:
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=35) as response:
            result = json.load(response)
    except HTTPError as err:
        detail = err.read(500).decode("utf-8", errors="replace")
        raise RuntimeError("GitHub API HTTP " + str(err.code) + " at " + path +
                           ": " + detail) from err
    except URLError as err:
        raise RuntimeError("GitHub API connection failed: " + str(err)) from err
    if graphql is not None and result.get("errors"):
        raise RuntimeError("GraphQL query failed: " + json.dumps(result["errors"])[:400])
    return result


def pages(path, params=None):
    items = []
    for page in range(1, 12):
        query = dict(params or {})
        query.update({"per_page": 100, "page": page})
        chunk = github(path, query)
        if not isinstance(chunk, list):
            raise RuntimeError("Unexpected paginated GitHub API response for " + path)
        items.extend(chunk)
        if len(chunk) < 100:
            break
    return items


def find_prs(state):
    # GitHub Search counts PRs across every publicly visible repository.
    # Search API caps result retrieval at 1000 records.
    items = []
    for page in range(1, 11):
        query = "author:" + USER + " is:pr is:" + state
        data = github("/search/issues",
                      {"q": query, "per_page": 100, "page": page, "sort": "updated", "order": "desc"})
        chunk = data.get("items", [])
        if not isinstance(chunk, list):
            raise RuntimeError("Invalid GitHub PR search response")
        items.extend(chunk)
        if len(chunk) < 100:
            break
    out, seen = [], set()
    visibility_cache = {}
    for item in items:
        url = item.get("html_url", "")
        match = re.fullmatch(r"https://github[.]com/([^/]+)/([^/]+)/pull/([0-9]+)", url)
        if not match or url in seen:
            continue
        full_name = match.group(1) + "/" + match.group(2)
        if full_name not in visibility_cache:
            try:
                visibility_cache[full_name] = not github("/repos/" + full_name).get("private", True)
            except RuntimeError:
                visibility_cache[full_name] = False
        if not visibility_cache[full_name]:
            continue
        seen.add(url)
        out.append({
            "title": item.get("title", "Untitled PR"),
            "url": url,
            "repo": match.group(1) + "/" + match.group(2),
            "number": int(match.group(3)),
            "upstream": match.group(1).lower() != USER.lower(),
            "state": state,
        })
    return out


def pinned_and_contributions():
    if not TOKEN:
        return [], None
    start = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    end = datetime.now(timezone.utc).isoformat()
    gql = """query {
      user(login:"%s") {
        pinnedItems(first:6,types:REPOSITORY) {
          nodes { ... on Repository { nameWithOwner isPrivate isFork url } }
        }
        contributionsCollection(from:"%s",to:"%s") {
          contributionCalendar { totalContributions }
        }
      }
    }""" % (USER, start, end)
    try:
        data = github("/graphql", graphql=gql)["data"]["user"]
        pins = [p["nameWithOwner"] for p in data["pinnedItems"]["nodes"]
                if not p["isPrivate"]]
        total = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        return pins, total
    except (RuntimeError, KeyError, TypeError) as err:
        print("GraphQL pin/contribution lookup unavailable: " + str(err), file=sys.stderr)
        return [], None


def valid_live_url(raw):
    if not raw or not isinstance(raw, str):
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        return None
    # A conference paper, source hosting and video are not a PLAYABLE DEMO.
    if parsed.netloc.lower() in ("github.com", "doi.org", "youtu.be", "youtube.com",
                                  "www.youtube.com", "pypi.org"):
        return None
    return raw


def normalize_repo(r):
    name = r["name"]
    return {
        "name": name,
        "full_name": r["full_name"],
        "url": r["html_url"],
        "description": r.get("description") or "",
        "language": r.get("language") or "Unspecified",
        "stars": r.get("stargazers_count", 0),
        "topics": r.get("topics") or [],
        "live": valid_live_url(r.get("homepage")),
        "fork": bool(r.get("fork")),
        "archived": bool(r.get("archived")),
        "featured": name in FEATURED and not r.get("fork"),
        "tagline": TAGLINES.get(name) or r.get("description") or "Explore source and project history",
    }


def safe(s):
    return html.escape(str(s), quote=True).replace("|", "&#124;").replace("\n", " ")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def section_replace(markdown, label, content):
    start = "<!--START_SECTION:" + label + "-->"
    end = "<!--END_SECTION:" + label + "-->"
    if markdown.count(start) != 1 or markdown.count(end) != 1:
        raise RuntimeError("Missing/duplicate README markers for " + label)
    before, rest = markdown.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + "\n" + content.strip() + "\n" + end + after


def render_prs(data):
    bits = []
    for state, heading, label in (("merged", "✅ CLEARED BOUNTIES // MERGED", "Completed"),
                                  ("open", "🔶 ACTIVE RAIDS // OPEN", "In review")):
        items = data["prs"][state]
        upstream = sum(p["upstream"] for p in items)
        bits.append("### " + heading + " (" + str(len(items)) + ")\n")
        bits.append("**" + label + "** · " + str(upstream) + " upstream · " +
                    str(len(items) - upstream) + " own-repository contributions\n")
        bits.append("| Guild / Repository | Quest completed or attempted | Scroll |")
        bits.append("| :-- | :-- | :-- |")
        if not items:
            bits.append("| — | No public PRs in this state | — |")
        for p in items:
            guild = "⚔️ " if p["upstream"] else "🏠 "
            bits.append("| " + guild + safe(p["repo"]) + " | " + safe(p["title"]) +
                        " | [#" + str(p["number"]) + "](" + p["url"] + ") |")
        bits.append("")
    bits.append("**⚔️** External upstream PR · **🏠** PR in my namespace. " +
                "Closed-without-merge PRs are not listed as completed bounties.")
    return "\n".join(bits)


def project_card(r):
    name = r["name"]
    tag = " · ".join([r["language"]] + r["topics"][:2])
    live = ('<a href="' + safe(r["live"]) + '">▶ PLAY DEMO</a> &nbsp; ' if r["live"] else "")
    return (
        '<td width="50%" valign="top">\n'
        '<a href="' + safe(r["url"]) + '"><img width="100%" alt="' + safe(name) + ' RPG cartridge" src="assets/covers/' + safe(name) + '.svg"></a>\n' +
        '<h3>' + EMOJI.get(name, "🎮") + " " + safe(name) + '</h3>\n'
        '<p>' + safe(r["tagline"]) + '</p>\n'
        '<p><code>' + safe(tag) + '</code></p>\n'
        '<p>⭐ ' + str(r["stars"]) + ' stars &nbsp; / &nbsp; ' + live +
        '<a href="' + safe(r["url"]) + '">⌘ CODE</a></p>\n'
        '</td>'
    )


def render_projects(data):
    repos = [r for r in data["repos"] if not r["fork"] and not r["archived"]]
    by_name = {r["name"]: r for r in repos}
    featured = [by_name[n] for n in FEATURED if n in by_name]
    other = [r for r in repos if r["name"] not in FEATURED and r["name"] != USER]
    other.sort(key=lambda r: r["name"].lower())
    parts = ["_Live GitHub project metadata • A star is a GitHub star, not a review rating._\n"]
    parts.append('<table>')
    for i in range(0, len(featured), 2):
        parts.append("<tr>\n" + "\n".join(project_card(r) for r in featured[i:i+2]) + "\n</tr>")
    parts.append("</table>")
    parts.append("\n<details><summary><b>🗄️ OPEN THE SIDE-QUEST SHELF (" +
                 str(len(other)) + " other original public repositories)</b></summary>\n")
    parts.append("| Game / Repository | Tech | ⭐ | Enter |")
    parts.append("| :-- | :-- | --: | :-- |")
    for r in other:
        parts.append("| " + safe(r["name"]) + " — " + safe(r["description"][:85]) +
                     " | " + safe(r["language"]) + " | " + str(r["stars"]) +
                     " | [CODE](" + r["url"] + ")" +
                     (" · [PLAY](" + r["live"] + ")" if r["live"] else "") + " |")
    parts.append("\n</details>")
    forks = sorted((r for r in data["repos"] if r["fork"]), key=lambda r: r["name"].lower())
    parts.append("\n<details><summary><b>🧬 FORK ARCHIVE (" +
                 str(len(forks)) + " public forks / upstream workbenches)</b></summary>\n")
    parts.append("These are forks, not original games. Authored PRs are credited in the raid log.\n")
    for r in forks:
        parts.append("- [" + safe(r["name"]) + "](" + r["url"] + ")")
    parts.append("\n</details>")
    return "\n".join(parts)


def render_hud(data):
    v = data["stats"]
    bars = Counter(r["language"] for r in data["repos"] if not r["fork"] and
                   r["language"] != "Unspecified")
    lines = [
        "| HUD field | Live value |", "| :-- | :-- |",
        "| 🎮 Account spawned | " + safe(v.get("created_at") or "GitHub profile API unavailable") + " |",
        "| 📦 Public repositories | " + str(v["public_repos"]) + " |",
        "| 🧬 Forks | " + str(v["forks"]) + " |",
        "| ⭐ Stars (public repos) | " + str(v["stars"]) + " |",
        "| ⚔️ Authored public PRs (merged / open) | " +
        str(len(data["prs"]["merged"])) + " / " + str(len(data["prs"]["open"])) + " |",
        "| 🟩 Contributions in trailing 365 days | " +
        (str(v["annual_contributions"]) if v["annual_contributions"] is not None else
         "Unavailable (GraphQL authorization needed)") + " |",
        "",
        "**Language inventory** (number of nonfork public repos where language is primary):",
        "",
    ]
    lines.extend("- " + safe(name) + ": " + str(count) for name, count in bars.most_common(12))
    if data["pinned"]:
        lines.append("\n**Pinned loadout:** " + " · ".join(
            "[" + safe(r) + "](https://github.com/" + quote(r, safe="/") + ")"
            for r in data["pinned"]))
    else:
        lines.append("\n**Pinned loadout:** Not available from this API run; GitHub GraphQL refresh may supply it.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and print a summary, without changing any files")
    args = parser.parse_args()
    profile = github("/users/" + USER)
    raw_repos = pages("/users/" + USER + "/repos", {"type": "owner", "sort": "updated"})
    public = [normalize_repo(r) for r in raw_repos
              if not r.get("private") and r.get("owner", {}).get("login", "").lower() == USER]
    merged, opened = find_prs("merged"), find_prs("open")
    pins, contributions = pinned_and_contributions()
    data = {
        "username": USER, "name": profile.get("name") or USER,
        "avatar": profile.get("avatar_url"), "location": profile.get("location"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pinned": pins, "repos": public,
        "prs": {"merged": merged, "open": opened},
        "stats": {
            "created_at": profile.get("created_at", "")[:10],
            "public_repos": len(public),
            "forks": sum(r["fork"] for r in public),
            "stars": sum(r["stars"] for r in public),
            "annual_contributions": contributions,
        },
    }
    print("Public repos:", len(public), "| merged PRs:", len(merged),
          "| open PRs:", len(opened), "| pins:", len(pins))
    if args.dry_run:
        return
    text = README.read_text(encoding="utf-8")
    for key, rendered in (("prs", render_prs(data)), ("projects", render_projects(data)),
                          ("hud", render_hud(data))):
        text = section_replace(text, key, rendered)
    README.write_text(text, encoding="utf-8")
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
