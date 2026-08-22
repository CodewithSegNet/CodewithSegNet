#!/usr/bin/env python3
"""
Generates a retro / CRT-terminal styled SVG showing GitHub stats,
streak info, and language breakdown. Commits the SVG to the repo
so the README can reference it directly — no external service needed.

Requires env vars: GH_TOKEN, GH_USERNAME
"""
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

GH_TOKEN = os.environ["GH_TOKEN"]
GH_USERNAME = os.environ["GH_USERNAME"]
OUTPUT_PATH = "github-stats.svg"


# ── GitHub API helpers ─────────────────────────────────────────

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


def fetch_user():
    return gh_api(f"/users/{GH_USERNAME}")


def fetch_repos():
    repos = gh_api(f"/users/{GH_USERNAME}/repos?per_page=100&sort=updated")
    return [r for r in repos if not r.get("fork") and not r.get("archived")]


def fetch_languages(repos):
    lang_totals = {}
    for repo in repos:
        try:
            langs = gh_api(f"/repos/{GH_USERNAME}/{repo['name']}/languages")
            for lang, bytes_count in langs.items():
                lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
        except Exception:
            continue
    return lang_totals


def fetch_streak_data():
    """Calculate streak from recent push events."""
    try:
        events = gh_api(f"/users/{GH_USERNAME}/events/public?per_page=100")
    except Exception:
        return {"current": 0, "best": 0, "total_contributions": 0}

    push_dates = set()
    for e in events:
        if e.get("type") == "PushEvent":
            dt = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
            push_dates.add(dt.date())

    if not push_dates:
        return {"current": 0, "best": 0, "total_contributions": len(events)}

    sorted_dates = sorted(push_dates, reverse=True)
    today = datetime.now(timezone.utc).date()

    # Current streak
    current = 0
    check = today
    for _ in range(len(sorted_dates) + 2):
        if check in push_dates:
            current += 1
            check -= timedelta(days=1)
        elif check == today:
            # allow today to not have a push yet
            check -= timedelta(days=1)
        else:
            break

    # Best streak (from available data)
    best = 0
    streak = 0
    for i, d in enumerate(sorted_dates):
        if i == 0:
            streak = 1
        else:
            if (sorted_dates[i - 1] - d).days == 1:
                streak += 1
            else:
                best = max(best, streak)
                streak = 1
    best = max(best, streak, current)

    return {
        "current": current,
        "best": best,
        "total_contributions": len(events),
    }


# ── Colour palette ────────────────────────────────────────────

LANG_COLORS = {
    "Python": "#f1e05a",
    "JavaScript": "#00ff41",
    "TypeScript": "#00d4ff",
    "HTML": "#ff6e40",
    "CSS": "#ff40ff",
    "Shell": "#89e051",
    "Dockerfile": "#0db7ed",
    "C": "#ff4444",
    "C++": "#f34b7d",
    "Java": "#b07219",
    "Go": "#00add8",
    "Rust": "#dea584",
    "Ruby": "#cc342d",
    "PHP": "#4F5D95",
    "Swift": "#ffac45",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Vue": "#41b883",
    "SCSS": "#c6538c",
    "Makefile": "#427819",
    "HCL": "#844FBA",
    "Jinja": "#a52a22",
}

DEFAULT_COLOR = "#888888"


def get_color(lang):
    return LANG_COLORS.get(lang, DEFAULT_COLOR)


# ── SVG generation ────────────────────────────────────────────

def generate_svg(user, repos, languages, streak):
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_repos = len(repos)
    followers = user.get("followers", 0)

    # Top 6 languages
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:6]
    total_bytes = sum(v for _, v in sorted_langs) or 1
    lang_data = [(lang, (b / total_bytes) * 100, get_color(lang)) for lang, b in sorted_langs]

    w = 520
    # Calculate height dynamically
    lang_section_h = len(lang_data) * 28 + 40
    h = 240 + lang_section_h
    pad = 20

    svg = []

    # ── Opening + styles ──
    svg.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=VT323&amp;display=swap');
      @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&amp;display=swap');

      .bg {{ fill: #0d1117; }}
      .border {{ fill: none; stroke: #00ff41; stroke-width: 1.5; rx: 6; ry: 6; opacity: 0.5; }}
      .inner-border {{ fill: none; stroke: #1a1a2e; stroke-width: 1; rx: 4; ry: 4; }}

      .title {{
        font-family: 'Press Start 2P', 'Courier New', monospace;
        font-size: 13px;
        fill: #00ff41;
      }}
      .section-title {{
        font-family: 'Press Start 2P', 'Courier New', monospace;
        font-size: 10px;
        fill: #00ff41;
        opacity: 0.8;
      }}
      .stat-label {{
        font-family: 'VT323', 'Courier New', monospace;
        font-size: 18px;
        fill: #7a7a8e;
      }}
      .stat-value {{
        font-family: 'VT323', 'Courier New', monospace;
        font-size: 22px;
        fill: #e6e6e6;
        font-weight: bold;
      }}
      .streak-value {{
        font-family: 'VT323', 'Courier New', monospace;
        font-size: 22px;
        fill: #ff6e40;
        font-weight: bold;
      }}
      .lang-label {{
        font-family: 'VT323', 'Courier New', monospace;
        font-size: 16px;
        fill: #b0b0c0;
      }}
      .lang-pct {{
        font-family: 'VT323', 'Courier New', monospace;
        font-size: 16px;
        fill: #7a7a8e;
      }}
      .bar-bg {{
        fill: #161b22;
        rx: 3;
        ry: 3;
      }}
      .cursor {{
        fill: #00ff41;
        animation: blink 1s step-end infinite;
      }}
      @keyframes blink {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0; }}
      }}
      @keyframes scanmove {{
        0% {{ transform: translateY(-{h}px); }}
        100% {{ transform: translateY({h}px); }}
      }}
      .scan {{
        fill: rgba(255,255,255,0.02);
        animation: scanmove 6s linear infinite;
      }}
    </style>

    <filter id="glow">
      <feGaussianBlur stdDeviation="1.5" result="b"/>
      <feComposite in="SourceGraphic" in2="b" operator="over"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect class="bg" width="{w}" height="{h}" rx="6" ry="6"/>
  <rect class="border" x="1" y="1" width="{w-2}" height="{h-2}"/>

  <!-- Scanline -->
  <rect class="scan" x="0" y="0" width="{w}" height="40" rx="6"/>
''')

    # ── Title ──
    y = pad + 16
    svg.append(f'''
  <text class="title" x="{pad}" y="{y}" filter="url(#glow)">&gt; {GH_USERNAME}@github $</text>
  <rect class="cursor" x="{pad + len(GH_USERNAME) * 9 + 135}" y="{y - 10}" width="8" height="13" rx="1"/>
''')

    # ── Divider ──
    y += 14
    svg.append(f'  <line x1="{pad}" y1="{y}" x2="{w-pad}" y2="{y}" stroke="#1a1a2e" stroke-width="1"/>')

    # ── Stats row ──
    y += 28
    stats = [
        ("REPOS", str(total_repos), "stat-value"),
        ("STARS", str(total_stars), "stat-value"),
        ("FOLLOWERS", str(followers), "stat-value"),
        ("STREAK", f"{streak['current']}d", "streak-value"),
        ("BEST", f"{streak['best']}d", "streak-value"),
    ]

    col_w = (w - 2 * pad) // len(stats)
    for i, (label, value, cls) in enumerate(stats):
        x = pad + i * col_w
        svg.append(f'  <text class="stat-label" x="{x}" y="{y}">{label}</text>')
        svg.append(f'  <text class="{cls}" x="{x}" y="{y + 24}">{value}</text>')

    # ── Divider ──
    y += 42
    svg.append(f'  <line x1="{pad}" y1="{y}" x2="{w-pad}" y2="{y}" stroke="#1a1a2e" stroke-width="1"/>')

    # ── Languages header ──
    y += 20
    svg.append(f'  <text class="section-title" x="{pad}" y="{y}" filter="url(#glow)">&gt; TOP_LANGUAGES</text>')

    # ── Language bars ──
    bar_max_w = w - 2 * pad - 150
    bar_h = 12

    for lang, pct, color in lang_data:
        y += 28
        bar_w = max(4, (pct / 100) * bar_max_w)
        bar_x = pad + 110

        svg.append(f'  <text class="lang-label" x="{pad}" y="{y + 10}">{lang}</text>')
        svg.append(f'  <rect class="bar-bg" x="{bar_x}" y="{y}" width="{bar_max_w}" height="{bar_h}"/>')
        svg.append(f'  <rect x="{bar_x}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" fill="{color}" rx="3" ry="3" opacity="0.9"/>')
        svg.append(f'  <rect x="{bar_x}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" fill="{color}" rx="3" ry="3" opacity="0.25" filter="url(#glow)"/>')
        svg.append(f'  <text class="lang-pct" x="{bar_x + bar_max_w + 8}" y="{y + 11}">{pct:.1f}%</text>')

    # ── Footer decoration ──
    svg.append(f'''
  <g opacity="0.2">
    <rect x="{pad}" y="{h - 16}" width="3" height="3" fill="#00ff41"/>
    <rect x="{pad + 6}" y="{h - 16}" width="3" height="3" fill="#00ff41"/>
    <rect x="{pad + 12}" y="{h - 16}" width="3" height="3" fill="#00ff41"/>
    <rect x="{pad + 18}" y="{h - 16}" width="3" height="3" fill="#ff6e40"/>
    <rect x="{pad + 24}" y="{h - 16}" width="3" height="3" fill="#ff6e40"/>
  </g>

</svg>''')

    return "\n".join(svg)


# ── Main ──────────────────────────────────────────────────────

def main():
    print("Fetching user data...")
    user = fetch_user()

    print("Fetching repos...")
    repos = fetch_repos()

    print(f"Fetching languages for {len(repos)} repos...")
    languages = fetch_languages(repos)

    print("Calculating streak data...")
    streak = fetch_streak_data()

    print("Generating retro SVG...")
    svg = generate_svg(user, repos, languages, streak)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT_PATH} ({len(svg)} bytes)")
    print(f"  Repos: {len(repos)}, Streak: {streak['current']}d, Best: {streak['best']}d")


if __name__ == "__main__":
    main()
