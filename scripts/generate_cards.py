#!/usr/bin/env python3
"""Render the VRally28 GitHub profile as a coordinated set of editorial SVG cards.

The renderer intentionally keeps all visual content local to SVG files so the
profile README works without JavaScript, remote stylesheets, or badge services.
Set STATIC=1 to render stable end-state frames for screenshots and validation.
"""
from __future__ import annotations

import base64
import json
import os
import textwrap
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
USER = os.getenv("GH_USER", "VRally28")

# Editorial palette: paper, ink, cobalt, and restrained neutral tints.
C = {
    "paper": "#F5F4F0",
    "surface": "#FBFAF7",
    "surface_alt": "#ECEBE6",
    "ink": "#17191F",
    "muted": "#646873",
    "quiet": "#9296A0",
    "line": "#D9D9D3",
    "cobalt": "#315BEE",
    "cobalt_mid": "#7893F7",
    "cobalt_pale": "#DCE4FF",
    "cobalt_faint": "#EEF1FF",
    "white": "#FFFFFF",
}

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
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
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
    longest_streak = streak = 0
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
        "busiest_day": {"date": busiest["date"], "count": int(busiest["contributionCount"])},
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
      <pattern id="paper-grid" width="28" height="28" patternUnits="userSpaceOnUse">
        <path d="M28 0H0V28" fill="none" stroke="{C['line']}" stroke-opacity=".25" stroke-width="1"/>
      </pattern>
      <linearGradient id="cobalt-wash" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="{C['cobalt_pale']}"/>
        <stop offset="1" stop-color="{C['surface']}"/>
      </linearGradient>
      <style>
        {font_css()}
        text{{font-family:Inter,Arial,sans-serif}}
        .serif{{font-family:Georgia,'Times New Roman',serif;font-weight:400}}
        .eyebrow{{font-size:10px;font-weight:750;letter-spacing:1.8px;fill:{C['cobalt']}}}
        .label{{font-size:9px;font-weight:750;letter-spacing:1.25px;fill:{C['quiet']}}}
        .body{{font-size:12px;font-weight:450;fill:{C['muted']}}}
        .small{{font-size:9px;font-weight:600;fill:{C['muted']}}}
        .rise{{animation:rise .72s cubic-bezier(.2,.75,.25,1) both}}
        .bar{{transform-box:fill-box;transform-origin:bottom;animation:barIn .85s cubic-bezier(.2,.75,.25,1) both}}
        .heat{{transform-box:fill-box;transform-origin:center;animation:heatIn .42s ease both}}
        .pulse{{animation:pulse 2.4s ease-in-out infinite}}
        @keyframes rise{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
        @keyframes barIn{{from{{transform:scaleY(.04);opacity:.35}}to{{transform:scaleY(1);opacity:1}}}}
        @keyframes heatIn{{from{{opacity:.18;transform:scale(.72)}}to{{opacity:1;transform:scale(1)}}}}
        @keyframes pulse{{0%,100%{{opacity:.45}}50%{{opacity:1}}}}
        .static *{{animation:none!important;opacity:1!important;transform:none!important}}
        @media(prefers-reduced-motion:reduce){{
          .rise,.bar,.heat,.pulse{{animation:none!important;opacity:1!important;transform:none!important}}
        }}
      </style>
    </defs>
    """


def start(width: int, height: int, grid: bool = False) -> str:
    overlay = '<rect width="100%" height="100%" fill="url(#paper-grid)"/>' if grid else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" class="{"static" if STATIC else ""}">'
        f'{defs()}<rect width="{width}" height="{height}" rx="5" fill="{C["paper"]}" stroke="{C["line"]}"/>'
        f'{overlay}'
    )


def end(svg: str) -> str:
    return svg + "</svg>\n"


def t(x, y, value, size=16, fill=None, weight=500, extra="") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill or C["ink"]}" '
            f'font-weight="{weight}" {extra}>{escape(str(value))}</text>')


def save(name: str, svg: str) -> None:
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    (CARD_DIR / name).write_text(end(svg), encoding="utf-8")


def wrap_lines(value: str, max_chars: int, max_lines: int = 2) -> list[str]:
    """Word-aware wrapping with an ellipsis when text exceeds the card."""
    lines = textwrap.wrap(value.strip(), width=max_chars, break_long_words=False, break_on_hyphens=False)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        lines[-1] = last[:max(1, max_chars - 1)].rstrip() + "…"
    return lines


def draw_hero() -> None:
    s = start(880, 360, True)
    # Left typography column.
    s += t(48, 48, "VANSH RALLY   /   CSE · THAPAR", 10, C["cobalt"], 750, 'letter-spacing="1.8"')
    s += '<circle cx="52" cy="83" r="3.5" fill="#315BEE"/>'
    s += t(66, 87, "ENGINEERING IDEAS INTO USEFUL THINGS", 9, C["muted"], 650, 'letter-spacing="1.15"')
    s += '<g class="rise">'
    s += '<text x="43" y="194" class="serif" font-size="104" letter-spacing="-4" fill="#17191F">Vansh</text>'
    s += '<text x="43" y="282" class="serif" font-size="104" font-style="italic" letter-spacing="-4" fill="#315BEE">Rally.</text>'
    s += '</g>'
    s += t(50, 322, "CSE student · Developer · Curious builder", 13, C["muted"], 500)
    # Abstract cobalt field: a modular orbital / circuit composition, not a stock illustration.
    s += '<g transform="translate(570 48)">'
    s += '<rect x="0" y="0" width="258" height="258" rx="4" fill="url(#cobalt-wash)" stroke="#D9D9D3"/>'
    s += '<path d="M0 86H258M0 172H258M86 0V258M172 0V258" stroke="#315BEE" stroke-opacity=".13"/>'
    s += '<circle cx="129" cy="129" r="88" fill="none" stroke="#315BEE" stroke-width="1.2" stroke-dasharray="2 6"/>'
    s += '<circle cx="129" cy="129" r="59" fill="none" stroke="#315BEE" stroke-width="1.2"/>'
    s += '<path d="M129 30V228M30 129H228M59 59L199 199M199 59L59 199" stroke="#315BEE" stroke-opacity=".26"/>'
    s += '<path d="M129 45L155 104L213 129L155 154L129 213L103 154L45 129L103 104Z" fill="#315BEE" fill-opacity=".10" stroke="#315BEE" stroke-width="1.2"/>'
    s += '<circle cx="129" cy="129" r="23" fill="#315BEE"/>'
    s += '<circle cx="129" cy="129" r="7" fill="#FBFAF7"/>'
    s += '<circle cx="129" cy="41" r="5" fill="#315BEE"><animate attributeName="r" values="4;7;4" dur="2.8s" repeatCount="indefinite"/></circle>'
    s += '<circle cx="217" cy="129" r="4" fill="#315BEE"/>'
    s += '<circle cx="41" cy="129" r="4" fill="#315BEE"/>'
    s += '<path d="M18 18H40M18 18V40M240 18H218M240 18V40M18 240H40M18 240V218M240 240H218M240 240V218" stroke="#315BEE" stroke-width="2"/>'
    s += '</g>'
    s += '<path d="M48 343H832" stroke="#D9D9D3"/>'
    s += t(48, 356, "01  /  PROFILE", 8, C["quiet"], 700, 'letter-spacing="1.3"')
    s += t(832, 356, "BUILD · LEARN · CONTRIBUTE", 8, C["quiet"], 700, 'text-anchor="end" letter-spacing="1.3"')
    save("hero.svg", s)


def draw_world_tile(filename: str, index: str, label: str, title: str,
                    description: str, accent: str, delay: float) -> None:
    s = start(293, 220, True)
    s += f'<g class="rise" style="animation-delay:{delay}s">'
    s += f'<rect x="8" y="8" width="277" height="204" rx="4" fill="{C["surface"]}" stroke="{C["line"]}"/>'
    s += f'<rect x="8" y="8" width="4" height="204" fill="{accent}"/>'
    s += t(26, 39, f"{index}  /  {label}", 9, accent, 750, 'letter-spacing="1.3"')
    s += f'<text x="26" y="91" class="serif" font-size="29" fill="{C["ink"]}">{escape(title)}</text>'
    for i, line in enumerate(wrap_lines(description, 34, 2)):
        s += t(26, 126 + i*17, line, 10, C["muted"], 500)
    s += f'<path d="M26 174H266" stroke="{C["line"]}"/>'
    s += t(266, 195, "↗", 16, accent, 700, 'text-anchor="end"')
    s += '</g>'
    save(filename, s)


def draw_activity(data: dict) -> None:
    placeholder = bool(data.get("placeholder", False))
    monthly = data.get("monthly", {})
    entries = sorted(monthly.items())[-12:]
    s = start(880, 240, True)
    s += t(48, 42, "02  /  CONTRIBUTION RHYTHM", 9, C["cobalt"], 750, 'letter-spacing="1.6"')
    s += '<text x="48" y="82" class="serif" font-size="30" fill="#17191F">Consistency, in context.</text>'
    # Compact metric rail: no duplicate annual summary panel.
    stats = [
        ("CONTRIBUTIONS", "—" if placeholder else f'{data.get("total_contributions", 0):,}'),
        ("ACTIVE DAYS", "—" if placeholder else str(data.get("active_days", 0))),
        ("CURRENT STREAK", "—" if placeholder else f'{data.get("current_streak", 0)}d'),
        ("LONGEST STREAK", "—" if placeholder else f'{data.get("longest_streak", 0)}d')
    ]
    for i, (label, value) in enumerate(stats):
        x = 48 + i*196
        s += t(x, 112, label, 8, C["quiet"], 750, 'letter-spacing="1"')
        s += f'<text x="{x}" y="145" class="serif" font-size="26" fill="{C["ink"]}">{escape(value)}</text>'
        if i < 3:
            s += f'<path d="M{x+170} 98V151" stroke="{C["line"]}"/>'
    # Monthly bars, with peak highlighted in cobalt.
    chart_x, chart_y, chart_w, chart_h = 48, 174, 784, 43
    values = [int(v) for _, v in entries]
    peak = max(values, default=0)
    max_value = max(peak, 1)
    slot = chart_w / max(len(entries), 1)
    for i, (month, value) in enumerate(entries):
        x = chart_x + i*slot
        h = max(2, (int(value)/max_value)*(chart_h-10)) if entries else 2
        color = C["cobalt"] if int(value) == peak and peak > 0 else C["cobalt_pale"]
        s += f'<rect class="bar" style="animation-delay:{i*55}ms" x="{x+slot*.27:.1f}" y="{chart_y+chart_h-h:.1f}" width="{slot*.46:.1f}" height="{h:.1f}" rx="2" fill="{color}"/>'
        label = date.fromisoformat(month + "-01").strftime("%b").upper()
        s += t(x+slot/2, 231, label, 7, C["quiet"], 650, 'text-anchor="middle"')
        if int(value) == peak and peak > 0:
            s += t(x+slot/2, chart_y+chart_h-h-5, value, 8, C["cobalt"], 750, 'text-anchor="middle"')
    busy = data.get("busiest_day", {})
    busy_text = "Busiest day · awaiting data sync" if placeholder else (
        f'BEST DAY  {busy.get("date", "—")}  /  {busy.get("count", 0)} CONTRIBUTIONS'
    )
    s += t(832, 42, busy_text, 8, C["muted"], 650, 'text-anchor="end" letter-spacing=".45"')
    save("activity.svg", s)


def draw_contributions(data: dict) -> None:
    raw_days = data.get("days", [])
    if not raw_days:
        raw_days = [{"date": (date.today()-timedelta(days=i)).isoformat(), "contributionCount": 0}
                    for i in range(364, -1, -1)]
    by_date = {date.fromisoformat(d["date"]): int(d["contributionCount"]) for d in raw_days}
    today = max(by_date, default=date.today())
    end_day = today
    # Align columns to Sunday so rows consistently represent weekdays.
    start_day = end_day - timedelta(days=363)
    start_day -= timedelta(days=(start_day.weekday()+1) % 7)
    columns = ((end_day-start_day).days // 7) + 1
    columns = min(columns, 53)
    palette = [C["surface_alt"], "#DCE4FF", "#AFC0FF", "#7893F7", "#315BEE"]
    s = start(880, 190, True)
    s += t(48, 40, "03  /  THE LAST 52 WEEKS", 9, C["cobalt"], 750, 'letter-spacing="1.6"')
    s += '<text x="48" y="77" class="serif" font-size="29" fill="#17191F">A year of making things move.</text>'
    s += t(832, 43, f'{data.get("total_contributions", 0):,} CONTRIBUTIONS', 8, C["muted"], 650, 'text-anchor="end" letter-spacing=".8"')
    left, top, step, cell = 48, 98, 15, 11
    for row, label in enumerate(["S", "M", "T", "W", "T", "F", "S"]):
        s += t(35, top+row*step+9, label, 7, C["quiet"], 600, 'text-anchor="middle"')
    prev_month = None
    for col in range(columns):
        d = start_day + timedelta(days=col*7)
        if d.month != prev_month:
            s += t(left+col*step, 92, d.strftime("%b").upper(), 7, C["quiet"], 650)
            prev_month = d.month
        for row in range(7):
            current = d + timedelta(days=row)
            if current > end_day:
                continue
            count = by_date.get(current, 0)
            level = 0 if count == 0 else min(4, 1+(count-1)//4)
            x, y = left+col*step, top+row*step
            s += (f'<rect class="heat" style="animation-delay:{(col*7+row)*1.2:.1f}ms" '
                  f'x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{palette[level]}">'
                  f'<title>{current.isoformat()} · {count} contributions</title></rect>')
    s += t(832, 180, "LESS", 7, C["quiet"], 600, 'text-anchor="end"')
    for i, color in enumerate(palette):
        s += f'<rect x="{738+i*17}" y="171" width="11" height="11" rx="2" fill="{color}"/>'
    save("contributions.svg", s)


def project_card(filename: str, index: str, name: str, description: str, tags: str) -> None:
    s = start(293, 205, True)
    s += f'<rect x="8" y="8" width="277" height="189" rx="4" fill="{C["surface"]}" stroke="{C["line"]}"/>'
    s += f'<rect x="8" y="8" width="4" height="189" fill="{C["cobalt"]}"/>'
    s += t(26, 38, f"SELECTED WORK  /  {index}", 8, C["quiet"], 750, 'letter-spacing="1.15"')
    # Use a smaller title for long names to keep every card within its grid.
    title_size = 19 if len(name) <= 15 else 15
    s += t(26, 77, name, title_size, C["ink"], 750, 'letter-spacing="-.25"')
    for i, line in enumerate(wrap_lines(description, 34, 2)):
        s += t(26, 111+i*16, line, 10, C["muted"], 500)
    s += f'<path d="M26 158H266" stroke="{C["line"]}"/>'
    s += t(26, 180, tags, 7, C["cobalt"], 750, 'letter-spacing=".45"')
    s += t(266, 38, "↗", 15, C["cobalt"], 700, 'text-anchor="end"')
    save(filename, s)


def draw_section_title() -> None:
    s = start(880, 66)
    s += t(48, 40, "04  /  SELECTED WORK", 10, C["cobalt"], 750, 'letter-spacing="1.8"')
    s += '<path d="M246 35H832" stroke="#D9D9D3"/>'
    s += '<circle cx="832" cy="35" r="3" fill="#315BEE"/>'
    save("title-coding.svg", s)


def main() -> None:
    if os.getenv("GH_TOKEN"):
        fetch_contributions()
    if not DATA_FILE.exists():
        raise FileNotFoundError("Missing data/contributions.json. Run the contribution refresh first.")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    draw_hero()
    draw_activity(data)
    draw_contributions(data)
    draw_world_tile("build.svg", "01", "BUILD", "Web & systems",
                    "React interfaces, JavaScript and Python projects with a growing backend focus.",
                    C["cobalt"], 0.12)
    draw_world_tile("learn.svg", "02", "EXPLORE", "New ground",
                    "AI and machine learning, systems thinking, and the foundations behind software.",
                    C["ink"], 0.25)
    draw_world_tile("community.svg", "03", "CONTRIBUTE", "Build together",
                    "Hackathons, student communities, and learning through open-source work.",
                    C["muted"], 0.38)
    draw_section_title()
    project_card("repo-codevibe.svg", "01", "CODEVIBE",
                 "A browser-based coding practice platform.",
                 "HTML  /  CSS  /  JAVASCRIPT")
    project_card("repo-hack-helix.svg", "02", "HACK HELIX",
                 "A collaborative hackathon build exploring a real-world problem.",
                 "HACKATHON  /  PRODUCT BUILDING")
    project_card("repo-basketball-scorecard.svg", "03", "BASKETBALL SCORECARD",
                 "A focused scoring interface for tracking the game.",
                 "FRONTEND  /  JAVASCRIPT")


if __name__ == "__main__":
    main()
