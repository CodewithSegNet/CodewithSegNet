#!/usr/bin/env python3
"""
Looks at this user's recent PushEvents, extracts the distinct repos
committed to (most recent first), and rewrites the block between
<!--START_SECTION:building--> and <!--END_SECTION:building--> in README.md.

Only own (non-fork) repos are considered. A repo already listed in
EXCLUDE_REPOS is skipped entirely (e.g. config repos, forks you patch
occasionally, this profile repo itself).

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

# Repo names to never show here, e.g. this profile repo.
EXCLUDE_REPOS = [
    GH_USERNAME,  # the username/username profile repo
]

START_MARKER = "<!--START_SECTION:building-->"
END_MARKER = "<!--END_SECTION:building-->"


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


def fetch_recent_push_repos():
    """Returns distinct repo full_names from recent push events, most recent first."""
    events = gh_api(f"/users/{GH_USERNAME}/events/public?per_page=100")
    seen = []
    for e in events:
        if e.get("type") != "PushEvent":
            continue
        full_name = e["repo"]["name"]  # "owner/repo"
        owner, name = full_name.split("/", 1)
        if owner.lower() != GH_USERNAME.lower():
            continue  # skip pushes to other people's/org repos you don't own
        if name in EXCLUDE_REPOS:
            continue
        if full_name not in seen:
            seen.append(full_name)
        if len(seen) >= MAX_PROJECTS:
            break
    return seen


def fetch_repo_details(full_name):
    return gh_api(f"/repos/{full_name}")


def format_project(repo):
    name = repo["name"]
    desc = repo.get("description") or "No description provided."
    url = repo["html_url"]
    return f"- **[{name}]({url})** — {desc}"


def build_block(full_names):
    if not full_names:
        return "_🔧 Working on something new — check back soon!_"
    lines = []
    for full_name in full_names:
        repo = fetch_repo_details(full_name)
        lines.append(format_project(repo))
    return "\n".join(lines)


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
        + "\n" + block + "\n"
        + content[end:]
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    repos = fetch_recent_push_repos()
    block = build_block(repos)
    update_readme(block)


if __name__ == "__main__":
    main()