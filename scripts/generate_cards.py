#!/usr/bin/env python3
"""Build the animated SVG components used by the VRally28 profile README."""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "contributions.json"
CARD_DIR = ROOT / "cards"
FONT_FILE = ROOT / "assets" / "Inter-subset.woff2"
STATIC = os.getenv("STATIC") == "1"

C = {
    "bg": "#f3f3f1", "panel": "#f3f3f1", "panel2": "#e8e8e4",
    "line": "#d8d8d2", "blue": "#2f55ff", "cyan": "#2f55ff",
    "violet": "#ef3b2d", "white": "#111111", "muted": "#626267",
    "dim": "#85858a", "green": "#ffc81a"
}
USER = os.getenv("GH_USER", "VRally28")


def fetch_contributions() -> None:
    token = os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN is required to refresh contribution data.")
    today = date.today()
    start = today - timedelta(days=364)
    query = (
        'query($login:String!){user(login:$login){'
        'contributionsCollection(from:"' + start.isoformat() + 'T00:00:00Z",'
        'to:"' + today.isoformat() + 'T23:59:59Z"){contributionCalendar{'
        'totalContributions weeks{contributionDays{date contributionCount}}}}}}'
    )
    payload = json.dumps({"query": query, "variables": {"login": USER}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=payload,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "VRally28-profile-cards"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError("GitHub contribution query failed: " + str(result.get("errors", "User not found")))
    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    by_date = {date.fromisoformat(day["date"]): int(day["contributionCount"]) for day in days}
    active = [day for day in days if int(day["contributionCount"]) > 0]
    busiest = max(days, key=lambda day: int(day["contributionCount"]), default={
        "date": today.isoformat(), "contributionCount": 0
    })
    cursor = today if by_date.get(today, 0) else today - timedelta(days=1)
    current_streak = 0
    while by_date.get(cursor, 0) > 0:
        current_streak += 1
        cursor -= timedelta(days=1)
    longest_streak = 0
    streak = 0
    for day in days:
        streak = streak + 1 if int(day["contributionCount"]) else 0
        longest_streak = max(longest_streak, streak)
    monthly = Counter()
    for day in days:
        monthly[day["date"][:7]] += int(day["contributionCount"])
    months = []
    month_cursor = start.replace(day=1)
    for _ in range(13):
        key = month_cursor.strftime("%Y-%m")
        if key <= today.strftime("%Y-%m"):
            months.append(key)
        month_cursor = (month_cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps({
        "username": USER,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "placeholder": False,
        "total_contributions": int(calendar["totalContributions"]),
        "active_days": len(active),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "busiest_day": {
            "date": busiest["date"],
            "count": int(busiest["contributionCount"])
        },
        "monthly": {month: int(monthly.get(month, 0)) for month in months[-12:]},
        "days": days
    }, indent=2) + "\n", encoding="utf-8")


def font_css() -> str:
    if not FONT_FILE.exists():
        return ""
    encoded = base64.b64encode(FONT_FILE.read_bytes()).decode("ascii")
    return f"@font-face{{font-family:Inter;src:url(data:font/woff2;base64,{encoded}) format('woff2');font-weight:100 900}}"


def defs() -> str:
    return f"""
    <defs>
      <pattern id="paper" width="24" height="24" patternUnits="userSpaceOnUse">
        <path d="M24 0H0V24" fill="none" stroke="{C['line']}" stroke-opacity=".22" stroke-width="1"/>
      </pattern>
      <style>
        {font_css()}
        text{{font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
        .serif{{font-family:Georgia,'Times New Roman',serif;font-weight:400}}
        .eyebrow{{font-size:11px;font-weight:750;letter-spacing:2px;fill:{C['blue']}}}
        .heading{{font-size:25px;font-weight:750;fill:{C['white']}}}
        .body{{font-size:13px;font-weight:450;fill:{C['muted']}}}
        .small{{font-size:10px;font-weight:600;fill:{C['muted']}}}
        .enter{{animation:rise .7s ease both}}
        .bar{{transform-box:fill-box;transform-origin:bottom;animation:barIn .8s ease both}}
        .heat{{transform-box:fill-box;transform-origin:center;animation:heatIn .45s ease both}}
        @keyframes rise{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
        @keyframes barIn{{from{{transform:scaleY(.05);opacity:.3}}to{{transform:scaleY(1);opacity:1}}}}
        @keyframes heatIn{{from{{opacity:.2;transform:scale(.7)}}to{{opacity:1;transform:scale(1)}}}}
        .static *{{animation:none!important;opacity:1;transform:none;stroke-dashoffset:0}}
        @media(prefers-reduced-motion:reduce){{.enter,.bar,.heat{{animation:none!important;opacity:1;transform:none}}}}
      </style>
    </defs>
    """

def start(width: int, height: int, grid: bool = False) -> str:
    overlay = '<rect width="100%" height="100%" fill="url(#paper)"/>' if grid else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" class="{"static" if STATIC else ""}">{defs()}'
        f'<rect width="{width}" height="{height}" rx="4" fill="{C["bg"]}" stroke="{C["line"]}"/>'
        f'{overlay}'
    )

def end(svg: str) -> str:
    return svg + "</svg>\n"


def t(x, y, value, size=16, fill=None, weight=500, extra="") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill or C["white"]}" '
            f'font-weight="{weight}" {extra}>{escape(str(value))}</text>')


def save(name: str, svg: str) -> None:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    (CARD_DIR / name).write_text(end(svg), encoding="utf-8")


def draw_hero() -> None:
    s = start(1200, 300, True)
    s += t(48, 54, "VANSH RALLY  /  GITHUB PROFILE", 11, C["blue"], 750, 'letter-spacing="2.2"')
    s += t(48, 143, "Building, learning,", 66, C["white"], 400, 'class="serif" letter-spacing="-2"')
    s += t(48, 211, "and figuring things out.", 66, C["white"], 400, 'class="serif" letter-spacing="-2"')
    s += t(52, 254, "CSE STUDENT  ·  DEVELOPER  ·  OPEN-SOURCE CONTRIBUTOR", 11, C["muted"], 650, 'letter-spacing="1.4"')
    s += '<path d="M48 274 H1152" stroke="#d8d8d2" stroke-width="1"/>'
    s += '<circle cx="1152" cy="274" r="4" fill="#2f55ff"/>'
    save("hero.svg", s)

def draw_social() -> None:
    # Social links are intentionally plain text in README, matching the reference.
    return

def draw_activity(data: dict) -> None:
    placeholder = bool(data.get("placeholder", False))
    s = start(1200, 250, True)
    s += t(48, 48, "GITHUB / ACTIVITY", 10, C["blue"], 750, 'letter-spacing="2"')
    s += t(48, 91, "A year of showing up.", 38, C["white"], 400, 'class="serif"')
    stats = [
        ("CONTRIBUTIONS", "—" if placeholder else f'{data.get("total_contributions", 0):,}'),
        ("ACTIVE DAYS", "—" if placeholder else str(data.get("active_days", 0))),
        ("CURRENT STREAK", "—" if placeholder else f'{data.get("current_streak", 0)} days'),
        ("LONGEST STREAK", "—" if placeholder else f'{data.get("longest_streak", 0)} days')
    ]
    for i, (label, value) in enumerate(stats):
        x = 48 + i * 282
        s += f'<path d="M{x} 125 V220" stroke="{C["line"]}" stroke-width="1"/>'
        s += t(x + 18, 151, label, 9, C["dim"], 750, 'letter-spacing="1.2"')
        s += t(x + 18, 194, value, 30, C["white"], 650, 'class="serif"')
    s += f'<path d="M48 220 H1152" stroke="{C["line"]}" stroke-width="1"/>'
    busy = data.get("busiest_day", {})
    busy_text = "Busiest day: awaiting first data sync" if placeholder else f'BUSIEST DAY  /  {busy.get("date", "—")}  ·  {busy.get("count", 0)} CONTRIBUTIONS'
    s += t(48, 239, busy_text, 9, C["muted"], 600, 'letter-spacing=".8"')
    save("activity.svg", s)

def project_card(filename: str, index: str, name: str, description: str,
                 tags: str, motif: str) -> None:
    s = start(390, 190, True)
    accent = C["blue"] if index == "01" else (C["violet"] if index == "02" else C["green"])
    s += f'<rect x="18" y="18" width="354" height="154" rx="3" fill="{C["bg"]}" stroke="{C["line"]}"/>'
    s += f'<rect x="18" y="18" width="4" height="154" fill="{accent}"/>'
    s += t(38, 48, "PROJECT  /  " + index, 9, C["dim"], 750, 'letter-spacing="1.5"')
    s += t(38, 87, name, 22, C["white"], 750, 'letter-spacing="-.4"')
    lines = [description[i:i+37] for i in range(0, min(len(description), 74), 37)]
    for j, line in enumerate(lines[:2]):
        s += t(38, 115 + j*17, line, 10, C["muted"], 500)
    s += f'<path d="M38 151 H352" stroke="{C["line"]}" stroke-width="1"/>'
    s += t(38, 165, tags, 8, accent, 700, 'letter-spacing=".4"')
    s += t(348, 48, "↗", 17, accent, 650, 'text-anchor="end"')
    save(filename, s)

def draw_contributions(data: dict) -> None:
    days = data.get("days", [])
    today = date.today()
    if len(days) < 350:
        days = [{"date": (today - timedelta(days=364-i)).isoformat(), "contributionCount": 0} for i in range(365)]
    days = days[-364:]
    palette = ["#e5e5e1", "#c8d2ff", "#8fa4ff", "#536fff", "#2f55ff"]
    s = start(1200, 250, True)
    s += t(48, 48, "CONTRIBUTION HISTORY", 10, C["blue"], 750, 'letter-spacing="2"')
    s += t(48, 91, "Small steps. Compounded.", 38, C["white"], 400, 'class="serif"')
    s += t(1152, 45, "LAST 52 WEEKS", 9, C["dim"], 650, 'text-anchor="end" letter-spacing="1.4"')
    start_x, start_y, step, cell = 48, 122, 20, 14
    previous_month = None
    for col in range(52):
        first_day = days[col * 7] if col * 7 < len(days) else None
        if first_day:
            month = date.fromisoformat(first_day["date"]).strftime("%b")
            if month != previous_month:
                s += t(start_x + col * step, 115, month.upper(), 8, C["dim"], 600)
                previous_month = month
    for row in range(7):
        for col in range(52):
            item = days[col * 7 + row] if col * 7 + row < len(days) else None
            if item is None:
                continue
            count = int(item["contributionCount"])
            level = 0 if count == 0 else min(4, 1 + (count - 1) // 4)
            x, y = start_x + col * step, start_y + row * step
            s += f'<rect class="heat" style="animation-delay:{(row*52+col)*2}ms" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{palette[level]}"><title>{escape(item["date"])} · {count} contributions</title></rect>'
    s += t(48, 264, "LESS", 8, C["dim"], 600)
    for i, color in enumerate(palette):
        s += f'<rect x="{88+i*19}" y="253" width="12" height="12" rx="2" fill="{color}"/>'
    s += t(194, 264, "MORE", 8, C["dim"], 600)
    save("contributions.svg", s)

def main() -> None:
    if os.getenv("GH_TOKEN"):
        fetch_contributions()
    if not DATA_FILE.exists():
        raise FileNotFoundError("Missing data/contributions.json. Run the contribution refresh first.")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    draw_hero()
    draw_social()
    draw_activity(data)
    project_card("repo-codevibe.svg", "01", "CODEVIBE",
                 "A browser-based coding practice platform.",
                 "HTML  /  CSS  /  JAVASCRIPT", "terminal")
    project_card("repo-hack-helix.svg", "02", "HACK HELIX",
                 "A hackathon project built through collaboration.",
                 "HACKATHON  /  DEVELOPMENT", "nodes")
    project_card("repo-basketball-scorecard.svg", "03", "BASKETBALL SCORECARD",
                 "A focused scoring interface for the game.",
                 "FRONTEND  /  JAVASCRIPT", "score")
    draw_contributions(data)


if __name__ == "__main__":
    main()
