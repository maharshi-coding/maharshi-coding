#!/usr/bin/env python3
"""Generate the professional GitHub profile from current, publicly visible API data.

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
VERIFIED_DEMOS = {"oss-agent": "https://maharshi-coding.github.io/oss-agent/"}
COMPANY_REPOSITORIES = (
    ("Tesla", "https://github.com/teslamotors", (
        "teslamotors/vehicle-command", "teslamotors/react-native-camera-kit")),
    ("Meta", "https://github.com/facebook", (
        "facebook/mariana-trench", "facebook/pyrefly", "facebook/ThreatExchange")),
    ("Google DeepMind", "https://github.com/google-deepmind", (
        "google-deepmind/mujoco",)),
    ("Waymo", "https://github.com/waymo-research", (
        "waymo-research/waymax",)),
)

# Meta's CodeSync can land an approved change upstream while GitHub records
# the original PR as 'closed' with merged_at=None. Verify each exceptional
# integration against the public PR, landed commit, and default-branch ancestry.
CODESYNC_INTEGRATIONS = (
    {"repo": "facebook/mariana-trench", "number": 277,
     "commit": "81b835dff56763b871d9db8dcbf29bdb1bb35973",
     "method": "Meta CodeSync"},
)

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
        "User-Agent": "maharshi-portfolio-profile",
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
        "live": valid_live_url(r.get("homepage")) or VERIFIED_DEMOS.get(name),
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


def verified_codesync_integrations():
    """Check that Meta's closed PR truly landed on the public upstream branch.

    CodeSync imports a reviewed change as an upstream commit instead of using
    GitHub's merge button. Never claim merged_at was set on the GitHub PR.
    """
    verified = []
    for ref in CODESYNC_INTEGRATIONS:
        repo, number, sha = ref["repo"], ref["number"], ref["commit"]
        pull = github("/repos/" + repo + "/pulls/" + str(number))
        if pull.get("user", {}).get("login", "").lower() != USER:
            raise RuntimeError("CodeSync PR author mismatch: " + repo)
        # When a PR is normally merged, global merged search already includes it.
        if pull.get("merged_at") is not None:
            continue
        if pull.get("state") != "closed":
            continue
        commit = github("/repos/" + repo + "/commits/" + sha)
        if commit.get("sha") != sha or "(#" + str(number) + ")" not in (
                commit.get("commit", {}).get("message", "")):
            raise RuntimeError("CodeSync commit does not reference the PR: " + repo)
        default_branch = github("/repos/" + repo).get("default_branch")
        if not default_branch:
            raise RuntimeError("Could not verify the upstream default branch: " + repo)
        compare = github("/repos/" + repo + "/compare/" + sha + "..." +
                         quote(default_branch, safe=""))
        if compare.get("status") not in ("identical", "ahead"):
            raise RuntimeError("CodeSync commit is not in the default-branch history: " + repo)
        verified.append({
            "repo": repo,
            "number": number,
            "title": pull.get("title", "Upstream code integration"),
            "url": pull.get("html_url"),
            "state": "landed",
            "upstream": True,
            "method": ref["method"],
            "integration_commit": sha,
            "integration_url": commit.get("html_url"),
        })
    return verified


def company_contributions(prs, landed):
    """Group GitHub merges, verified upstream landings and open PRs separately."""
    result = []
    for name, url, repositories in COMPANY_REPOSITORIES:
        allowed = {r.lower() for r in repositories}
        merged = [p for p in prs["merged"]
                  if p["upstream"] and p["repo"].lower() in allowed]
        landed_here = [p for p in landed if p["repo"].lower() in allowed]
        opened = [p for p in prs["open"]
                  if p["upstream"] and p["repo"].lower() in allowed]
        if merged or landed_here or opened:
            result.append({"name": name, "url": url, "merged": merged,
                           "landed": landed_here, "open": opened})
    return result


def render_prs(data):
    """Only big-tech company PRs, grouped beneath the company that maintains them."""
    lines = []
    for company in data["company_contributions"]:
        lines.extend(["### [" + safe(company["name"]) + "](" + company["url"] + ")", ""])
        for state, heading in (
                ("merged", "Merged on GitHub"),
                ("landed", "Landed upstream via Meta CodeSync"),
                ("open", "Open · under review")):
            if not company[state]:
                continue
            lines.extend(["**" + heading + "**", ""])
            for pr in company[state]:
                project = pr["repo"].split("/", 1)[1]
                line = ("- **" + safe(project) + "** · [PR #" +
                        str(pr["number"]) + "](" + pr["url"] + ") — " +
                        safe(pr["title"]))
                if state == "landed":
                    line += (" · [Upstream commit " +
                             pr["integration_commit"][:7] + "](" +
                             pr["integration_url"] + ")")
                lines.append(line)
            lines.append("")
    if not lines:
        return "_No matching publicly visible company pull requests found._"
    lines.append("_GitHub merge and Meta CodeSync integration are labeled separately. "
                 "These are public open-source contributions—not company employment or endorsement._")
    return "\n".join(lines)


def project_card(r):
    """A minimal, readable project cell rendered with GitHub-safe HTML."""
    name = safe(r["name"])
    summary = safe(r["tagline"])
    tags = " · ".join([r["language"]] + r["topics"][:2])
    live = (' &nbsp; · &nbsp; <a href="' + safe(r["live"]) +
            '">Live demo</a>' if r["live"] else "")
    return (
        '<td width="50%" valign="top">\n'
        '<p><a href="' + safe(r["url"]) + '"><strong>' + name + '</strong></a></p>\n'
        '<p>' + summary + '</p>\n'
        '<p><sub>' + safe(tags) + ' · ★ ' + str(r["stars"]) + ' GitHub stars</sub></p>\n'
        '<p><a href="' + safe(r["url"]) + '">Source code</a>' + live + '</p>\n'
        '</td>'
    )

def render_projects(data):
    repos = [r for r in data["repos"] if not r["fork"] and not r["archived"]]
    by_name = {r["name"]: r for r in repos}
    featured = [by_name[n] for n in FEATURED if n in by_name]
    other = sorted(
        (r for r in repos if r["name"] not in FEATURED and r["name"] != USER),
        key=lambda r: r["name"].lower(),
    )
    parts = ['<table>']
    for i in range(0, len(featured), 2):
        parts.append("<tr>\n" + "\n".join(project_card(r) for r in featured[i:i+2]) + "\n</tr>")
    parts.append("</table>")
    parts.append("\n<details><summary><b>Browse " + str(len(other)) +
                 " more original public repositories</b></summary>\n")
    parts += ["| Repository | Primary language | Stars | Links |", "| :-- | :-- | --: | :-- |"]
    for r in other:
        links = "[Code](" + r["url"] + ")"
        if r["live"]:
            links += " · [Live](" + r["live"] + ")"
        parts.append("| **" + safe(r["name"]) + "** — " + safe(r["description"][:90]) +
                     " | " + safe(r["language"]) + " | " + str(r["stars"]) +
                     " | " + links + " |")
    parts.append("\n</details>")
    forks = sorted([r for r in data["repos"] if r["fork"]],
                   key=lambda r: r["name"].lower())
    parts.append("\n<details><summary>Open the " + str(len(forks)) +
                 "-repository public fork archive</summary>\n")
    parts.append("_Forks are shown separately from original projects._\n")
    for r in forks:
        parts.append("- [" + safe(r["name"]) + "](" + r["url"] + ")")
    parts.append("\n</details>")
    return "\n".join(parts)


def render_hud(data):
    stats = data["stats"]
    main_languages = Counter(
        r["language"] for r in data["repos"] if not r["fork"] and
        r["language"] != "Unspecified"
    )
    lines = [
        "| Public GitHub activity | Count |",
        "| :-- | --: |",
        "| Public repositories | " + str(stats["public_repos"]) + " |",
        "| Original repositories | " + str(stats["public_repos"] - stats["forks"]) + " |",
        "| Total public repository stars | " + str(stats["stars"]) + " |",
        "| Integrated contributions to featured tech companies | " +
        str(sum(len(c["merged"]) + len(c["landed"])
                for c in data["company_contributions"])) + " |",
        "| Open PRs to featured tech companies | " +
        str(sum(len(c["open"]) for c in data["company_contributions"])) + " |",
        "| Contributions in last 365 days | " +
        (str(stats["annual_contributions"]) if stats["annual_contributions"] is not None
         else "Not available") + " |",
        "",
        "**Primary repository languages:** " +
        (", ".join(safe(k) + " (" + str(v) + ")" for k, v in main_languages.most_common(6))
         or "Not available"),
        "",
    ]
    if data["pinned"]:
        lines.append("**GitHub pinned:** " + " · ".join(
            "[" + safe(repo) + "](https://github.com/" + quote(repo, safe="/") + ")"
            for repo in data["pinned"]
        ))
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
    data["verified_upstream_integrations"] = verified_codesync_integrations()
    data["company_contributions"] = company_contributions(
        data["prs"], data["verified_upstream_integrations"])
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
