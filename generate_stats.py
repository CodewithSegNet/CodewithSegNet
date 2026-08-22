#!/usr/bin/env python3
"""
Generates a retro / CRT-terminal styled SVG showing GitHub stats
and language breakdown. Commits the SVG to the repo so the README
can reference it directly — no external service needed.

Requires env vars: GH_TOKEN, GH_USERNAME
"""
import os
import sys
import json
import urllib.request

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
    """Aggregate byte counts per language across all repos."""
    lang_totals = {}
    for repo in repos:
        try:
            langs = gh_api(f"/repos/{GH_USERNAME}/{repo['name']}/languages")
            for lang, bytes_count in langs.items():
                lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
        except Exception:
            continue
    return lang_totals


# ── Retro colour palette ──────────────────────────────────────

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
}

DEFAULT_COLOR = "#888888"


def get_color(lang):
    return LANG_COLORS.get(lang, DEFAULT_COLOR)


# ── SVG generation ────────────────────────────────────────────

def generate_svg(user, repos, languages):
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_repos = len(repos)
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    # Sort languages by bytes, take top 8
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:8]
    total_bytes = sum(v for _, v in sorted_langs) or 1

    # Calculate percentages
    lang_data = []
    for lang, bytes_count in sorted_langs:
        pct = (bytes_count / total_bytes) * 100
        lang_data.append((lang, pct, get_color(lang)))

    # SVG dimensions
    w, h = 520, 400
    pad = 20

    # Build the SVG
    svg_parts = []

    # ── Header ──
    svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=VT323&amp;display=swap');
      @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&amp;display=swap');

      .crt-bg {{ fill: #0a0a0a; }}
      .crt-border {{ fill: none; stroke: #333; stroke-width: 2; rx: 8; ry: 8; }}
      .crt-glow {{ fill: none; stroke: #00ff41; stroke-width: 1; rx: 8; ry: 8; opacity: 0.3; }}

      .title {{
        font-family: 'Press Start 2P', 'VT323', monospace;
        font-size: 14px;
        fill: #00ff41;
      }}
      .stat-label {{
        font-family: 'VT323', monospace;
        font-size: 20px;
        fill: #888;
      }}
      .stat-value {{
        font-family: 'VT323', monospace;
        font-size: 20px;
        fill: #00ff41;
      }}
      .lang-label {{
        font-family: 'VT323', monospace;
        font-size: 18px;
        fill: #ccc;
      }}
      .lang-pct {{
        font-family: 'VT323', monospace;
        font-size: 18px;
        fill: #888;
      }}
      .bar-bg {{
        fill: #1a1a2e;
        rx: 2;
        ry: 2;
      }}
      .cursor {{
        fill: #00ff41;
        animation: blink 1s step-end infinite;
      }}

      @keyframes blink {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0; }}
      }}

      @keyframes scanline {{
        0% {{ transform: translateY(-100%); }}
        100% {{ transform: translateY(400px); }}
      }}

      .scanline {{
        fill: url(#scanlineGrad);
        animation: scanline 4s linear infinite;
        opacity: 0.04;
      }}
    </style>

    <linearGradient id="scanlineGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="white" stop-opacity="0"/>
      <stop offset="50%" stop-color="white" stop-opacity="1"/>
      <stop offset="100%" stop-color="white" stop-opacity="0"/>
    </linearGradient>

    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- CRT background -->
  <rect class="crt-bg" width="{w}" height="{h}" rx="8" ry="8"/>
  <rect class="crt-border" x="1" y="1" width="{w-2}" height="{h-2}"/>
  <rect class="crt-glow" x="3" y="3" width="{w-6}" height="{h-6}"/>

  <!-- Scanline overlay -->
  <rect class="scanline" x="0" y="0" width="{w}" height="60" rx="8"/>
''')

    # ── Title bar ──
    y = pad + 18
    svg_parts.append(f'''
  <!-- Title -->
  <text class="title" x="{pad}" y="{y}" filter="url(#glow)">
    &gt; {GH_USERNAME.upper()}'s STATS_
  </text>
  <rect class="cursor" x="{pad + len(GH_USERNAME) * 10 + 110}" y="{y - 10}" width="10" height="14"/>

  <!-- Separator -->
  <line x1="{pad}" y1="{y + 10}" x2="{w - pad}" y2="{y + 10}" stroke="#333" stroke-width="1" stroke-dasharray="4,4"/>
''')

    # ── Stats row ──
    y += 38
    stats = [
        ("REPOS", str(total_repos)),
        ("STARS", str(total_stars)),
        ("FOLLOWERS", str(followers)),
        ("FOLLOWING", str(following)),
    ]

    col_w = (w - 2 * pad) // len(stats)
    for i, (label, value) in enumerate(stats):
        x = pad + i * col_w
        svg_parts.append(f'''
  <text class="stat-label" x="{x}" y="{y}">{label}</text>
  <text class="stat-value" x="{x}" y="{y + 22}">{value}</text>
''')

    # ── Separator ──
    y += 38
    svg_parts.append(f'''
  <line x1="{pad}" y1="{y}" x2="{w - pad}" y2="{y}" stroke="#333" stroke-width="1" stroke-dasharray="4,4"/>
''')

    # ── Languages header ──
    y += 24
    svg_parts.append(f'''
  <text class="title" x="{pad}" y="{y}" filter="url(#glow)" font-size="12">
    &gt; TOP LANGUAGES_
  </text>
''')

    # ── Language bars ──
    y += 16
    bar_max_w = w - 2 * pad - 160  # space for label + percentage
    bar_h = 14
    spacing = 30

    for lang, pct, color in lang_data:
        y += spacing
        bar_w = max(4, (pct / 100) * bar_max_w)

        # Label
        svg_parts.append(f'  <text class="lang-label" x="{pad}" y="{y + 11}">{lang}</text>')

        # Bar background
        bar_x = pad + 120
        svg_parts.append(f'  <rect class="bar-bg" x="{bar_x}" y="{y}" width="{bar_max_w}" height="{bar_h}"/>')

        # Bar fill with glow
        svg_parts.append(f'  <rect x="{bar_x}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" fill="{color}" rx="2" ry="2" opacity="0.85"/>')
        svg_parts.append(f'  <rect x="{bar_x}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" fill="{color}" rx="2" ry="2" opacity="0.3" filter="url(#glow)"/>')

        # Percentage
        svg_parts.append(f'  <text class="lang-pct" x="{bar_x + bar_max_w + 8}" y="{y + 12}">{pct:.1f}%</text>')

    # ── Footer ──
    svg_parts.append(f'''
  <!-- Pixel dots decoration -->
  <g opacity="0.15">
    <rect x="{pad}" y="{h - 18}" width="4" height="4" fill="#00ff41"/>
    <rect x="{pad + 8}" y="{h - 18}" width="4" height="4" fill="#00ff41"/>
    <rect x="{pad + 16}" y="{h - 18}" width="4" height="4" fill="#00ff41"/>
  </g>

</svg>
''')

    return "".join(svg_parts)


# ── Main ──────────────────────────────────────────────────────

def main():
    print("Fetching user data...")
    user = fetch_user()

    print("Fetching repos...")
    repos = fetch_repos()

    print(f"Fetching languages for {len(repos)} repos...")
    languages = fetch_languages(repos)

    print("Generating retro SVG...")
    svg = generate_svg(user, repos, languages)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
