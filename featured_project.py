#!/usr/bin/env python3
"""
Fetches the user's **actually pinned** repositories from the GitHub
profile via the GraphQL API, then rewrites the block between
<!--START_SECTION:projects--> and <!--END_SECTION:projects--> in
README.md as a 2-row markdown table.

The GraphQL query returns whatever repos the user has pinned in their
GitHub profile — including repos owned by other orgs/users.

Requires env vars: GH_TOKEN, GH_USERNAME
"""
import os
import sys
import urllib.request
import json
import math

GH_TOKEN = os.environ["GH_TOKEN"]
GH_USERNAME = os.environ["GH_USERNAME"]
README_PATH = "README.md"

# Maximum pinned repos GitHub allows is 6.
MAX_PINNED = 6
# Columns per table row.
COLS = 3

START_MARKER = "<!--START_SECTION:projects-->"
END_MARKER = "<!--END_SECTION:projects-->"


# ── GitHub GraphQL helper ──────────────────────────────────────

def graphql(query, variables=None):
    """Execute a GitHub GraphQL query and return the JSON response."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": GH_USERNAME,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


# ── Fetch pinned repos ─────────────────────────────────────────

PINNED_QUERY = """
query($login: String!, $count: Int!) {
  user(login: $login) {
    pinnedItems(first: $count, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          primaryLanguage {
            name
          }
          owner {
            login
          }
        }
      }
    }
  }
}
"""


def fetch_pinned_repos():
    """Return the list of repos the user has pinned on their profile."""
    result = graphql(PINNED_QUERY, {"login": GH_USERNAME, "count": MAX_PINNED})

    errors = result.get("errors")
    if errors:
        print(f"GraphQL errors: {errors}", file=sys.stderr)
        return []

    nodes = result.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
    return [n for n in nodes if n]  # filter out any nulls


# ── Table formatting ───────────────────────────────────────────

def _cell(repo):
    """Build a single table cell for a repo."""
    name = repo["name"]
    desc = repo.get("description") or "No description provided."
    url = repo["url"]
    stars = repo.get("stargazerCount", 0)
    lang_node = repo.get("primaryLanguage")
    lang = lang_node["name"] if lang_node else ""
    owner = repo.get("owner", {}).get("login", GH_USERNAME)

    # Show owner prefix only for repos not owned by the user
    display_name = f"{owner}/{name}" if owner.lower() != GH_USERNAME.lower() else name

    # Truncate long descriptions to keep the table tidy
    max_desc = 60
    if len(desc) > max_desc:
        desc = desc[: max_desc - 1].rstrip() + "…"

    parts = [f"**[{display_name}]({url})**"]
    parts.append(f"<br/>{desc}")
    tag_parts = []
    if lang:
        tag_parts.append(f"`{lang}`")
    tag_parts.append(f"⭐ {stars}")
    parts.append(f"<br/>{' · '.join(tag_parts)}")

    return " ".join(parts)


def _empty_cell():
    return " "


def build_table(repos):
    """Render repos as a 2-row × COLS-column markdown table."""
    if not repos:
        return "_✨ Projects coming soon — stay tuned!_"

    rows = []
    num_rows = math.ceil(len(repos) / COLS)

    # Header row
    header = "| " + " | ".join(["Project"] * COLS) + " |"
    sep = "| " + " | ".join(["---"] * COLS) + " |"
    rows.append(header)
    rows.append(sep)

    for r in range(num_rows):
        cells = []
        for c in range(COLS):
            idx = r * COLS + c
            if idx < len(repos):
                cells.append(_cell(repos[idx]))
            else:
                cells.append(_empty_cell())
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join(rows)


# ── README update ──────────────────────────────────────────────

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
        + "\n\n" + block + "\n\n"
        + content[end:]
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


# ── Main ───────────────────────────────────────────────────────

def main():
    print("Fetching pinned repos via GraphQL...")
    repos = fetch_pinned_repos()
    print(f"  Found {len(repos)} pinned repo(s)")

    for r in repos:
        owner = r.get("owner", {}).get("login", "?")
        print(f"    • {owner}/{r['name']} (⭐ {r.get('stargazerCount', 0)})")

    block = build_table(repos)
    update_readme(block)
    print("README.md updated with pinned repos table.")


if __name__ == "__main__":
    main()
