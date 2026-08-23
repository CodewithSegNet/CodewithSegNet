#!/usr/bin/env python3
"""
Pulls this user's repos from the GitHub API, picks the ones to feature,
and rewrites the block between <!--START_SECTION:projects--> and
<!--END_SECTION:projects--> in README.md.

Selection logic:
  1. Any repo name listed in PINNED_REPOS is always included, in that order.
  2. Remaining slots are filled with the user's own (non-fork) repos sorted
     by star count, until MAX_PROJECTS is reached.

Requires env vars: GH_TOKEN, GH_USERNAME
"""
import os
import sys
import urllib.request
import json

GH_TOKEN = os.environ["GH_TOKEN"]
GH_USERNAME = os.environ["GH_USERNAME"]
README_PATH = "README.md"
MAX_PROJECTS = 4

# Repo names (not full URLs) you always want featured, in priority order.
# Edit this list any time — no need to touch the workflow.
PINNED_REPOS = [
    "EddieHubCommunity/open-source-practice",
    " Poietes-ng/rezzidentEcosystem",
    "hngprojects/aivideo_be",
    "EELI_Project",
    "AirBnB",
    "alx-files_manager",
]

START_MARKER = "<!--START_SECTION:projects-->"
END_MARKER = "<!--END_SECTION:projects-->"


def gh_api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": GH_USERNAME,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch_repos():
    repos = gh_api(f"/users/{GH_USERNAME}/repos?per_page=100&sort=updated")
    return [r for r in repos if not r.get("fork") and not r.get("archived")]


def select_projects(repos):
    by_name = {r["name"]: r for r in repos}
    ordered = []

    for name in PINNED_REPOS:
        if name in by_name:
            ordered.append(by_name.pop(name))

    remaining = sorted(by_name.values(), key=lambda r: r["stargazers_count"], reverse=True)
    ordered.extend(remaining)

    return ordered[:MAX_PROJECTS]


def format_project(repo):
    name = repo["name"]
    desc = repo.get("description") or "No description provided."
    lang = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    url = repo["html_url"]

    lang_line = f"**{lang}**" if lang else ""
    stats = f"⭐ {stars}"
    if lang_line:
        stats = f"{lang_line} · {stats}"

    return (
        f"### [{name}]({url})\n"
        f"{desc}\n\n"
        f"{stats}\n"
    )


def build_block(repos):
    if not repos:
        return "_✨ Projects coming soon — stay tuned!_"
    return "\n".join(format_project(r) for r in repos)


def update_readme(block):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start == -1 or end == -1:
        print("Markers not found in README.md — nothing updated.", file=sys.stderr)
        sys.exit(1)

    start += len(START_MARKER)
    new_content = (
        content[:start]
        + "\n\n" + block + "\n"
        + content[end:]
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    repos = fetch_repos()
    selected = select_projects(repos)
    block = build_block(selected)
    update_readme(block)


if __name__ == "__main__":
    main()
