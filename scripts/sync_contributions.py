#!/usr/bin/env python3
"""Refresh external pull request statuses in the GitHub profile README."""
import datetime as datetime
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = "maharshi-coding"
START = "<!-- UPSTREAM-PR-START -->"
END = "<!-- UPSTREAM-PR-END -->"
README = Path(__file__).resolve().parent.parent / "README.md"


def search(status):
    found = []
    for page in range(1, 11):
        query = "author:" + USERNAME + " is:pr is:" + status
        url = "https://api.github.com/search/issues?" + urlencode(
            {"q": query, "sort": "updated", "order": "desc", "per_page": 100, "page": page})
        headers = {"Accept": "application/vnd.github+json",
                   "User-Agent": "maharshios-contribution-sync"}
        token = os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
        if token:
            headers["Authorization"] = "Bearer " + token
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            result = json.load(response)
        batch = result["items"]
        found.extend(batch)
        if len(batch) != 100:
            break
    return found


def external(items):
    result = []
    seen = set()
    for item in items:
        match = re.search(r"/repos/([^/]+)/([^/]+)$", item.get("repository_url", ""))
        url = item.get("html_url", "")
        if not match or match.group(1).lower() == USERNAME.lower():
            continue
        if not re.fullmatch(r"https://github[.]com/[^/]+/[^/]+/pull/[0-9]+", url):
            continue
        if url not in seen:
            result.append((match.group(1) + "/" + match.group(2),
                           item.get("title", "Untitled"), item["number"], url))
            seen.add(url)
    return result


def table(items):
    if not items:
        return "_No matching upstream contributions found._\n"
    output = ["| Upstream repository | Contribution | PR |", "| :-- | :-- | :-- |"]
    for repository, title, number, url in items:
        safe_title = html.escape(title).replace("|", "&#124;").replace("\n", " ")
        output.append("| **" + html.escape(repository) + "** | " + safe_title +
                      " | [#" + str(number) + "](" + url + ") |")
    return "\n".join(output) + "\n"


def main():
    merged = external(search("merged"))
    opened = external(search("open"))
    checked = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    section = (
        "\n\n_Status last verified: " + checked +
        " · Only external upstream repositories are counted here._\n\n"
        "### ✅ Merged upstream (" + str(len(merged)) + ")\n\n" +
        "Accepted and merged into the original maintainers' repositories.\n\n" +
        table(merged) + "\n" +
        "### 🟣 Open upstream (" + str(len(opened)) + ")\n\n" +
        "Submitted to maintainers but not yet merged; review status can change.\n\n" +
        table(opened) + "\n" +
        "[All authored pull requests](https://github.com/pulls?q=is%3Apr+author%3Amaharshi-coding)"
        " · [Closed without merge](https://github.com/pulls?q=is%3Apr+author%3Amaharshi-coding+is%3Aclosed+-is%3Amerged)\n\n"
    )
    content = README.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise RuntimeError("Profile README does not contain unique contribution markers")
    prefix, after = content.split(START, 1)
    _, suffix = after.split(END, 1)
    updated = prefix + START + section + END + suffix
    if content != updated:
        README.write_text(updated, encoding="utf-8")
        print("Refreshed " + str(len(merged)) + " merged and " + str(len(opened)) + " open upstream PRs")


if __name__ == "__main__":
    main()
