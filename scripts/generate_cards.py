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
    "bg": "#080D19", "panel": "#101A2B", "panel2": "#142239",
    "line": "#263B58", "blue": "#38BDF8", "cyan": "#67E8F9",
    "violet": "#8B7CFF", "white": "#F3F7FF", "muted": "#9AAEC8",
    "dim": "#60748F", "green": "#65D6A5"
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
      <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1">
        <stop stop-color="{C['panel']}"/><stop offset="1" stop-color="{C['bg']}"/>
      </linearGradient>
      <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
        <stop stop-color="{C['blue']}"/><stop offset=".55" stop-color="{C['cyan']}"/><stop offset="1" stop-color="{C['violet']}"/>
      </linearGradient>
      <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0">
        <stop stop-color="{C['violet']}"/><stop offset="1" stop-color="{C['cyan']}"/>
      </linearGradient>
      <radialGradient id="halo">
        <stop stop-color="{C['blue']}" stop-opacity=".22"/><stop offset="1" stop-color="{C['blue']}" stop-opacity="0"/>
      </radialGradient>
      <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
        <path d="M28 0H0V28" fill="none" stroke="#A9C8F0" stroke-opacity=".055" stroke-width="1"/>
      </pattern>
      <style>
        {font_css()}
        text{{font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
        .eyebrow{{font-size:12px;font-weight:750;letter-spacing:2.4px;fill:{C['blue']}}}
        .heading{{font-size:25px;font-weight:750;fill:{C['white']}}}
        .body{{font-size:14px;font-weight:450;fill:{C['muted']}}}
        .small{{font-size:11px;font-weight:600;fill:{C['muted']}}}
        .enter{{transform-box:fill-box;transform-origin:center;animation:rise .7s cubic-bezier(.2,.7,.2,1) both}}
        .glow{{animation:breathe 5s ease-in-out infinite}}
        .dash{{stroke-dasharray:900;stroke-dashoffset:900;animation:trace 1.7s ease forwards}}
        .bar{{transform-box:fill-box;transform-origin:bottom;animation:barIn .8s cubic-bezier(.2,.7,.2,1) both}}
        .heat{{transform-box:fill-box;transform-origin:center;animation:heatIn .55s ease both}}
        @keyframes rise{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
        @keyframes breathe{{50%{{opacity:.55;transform:scale(1.06)}}}}
        @keyframes trace{{to{{stroke-dashoffset:0}}}}
        @keyframes barIn{{from{{transform:scaleY(.05);opacity:.3}}to{{transform:scaleY(1);opacity:1}}}}
        @keyframes heatIn{{from{{opacity:.15;transform:scale(.55)}}to{{opacity:1;transform:scale(1)}}}}
        .static *{{animation:none!important;opacity:1;transform:none;stroke-dashoffset:0}}
        @media(prefers-reduced-motion:reduce){{.enter,.glow,.dash,.bar,.heat{{animation:none!important;opacity:1;transform:none;stroke-dashoffset:0}}}}
      </style>
    </defs>
    """


def start(width: int, height: int, grid: bool = False) -> str:
    overlay = '<rect width="100%" height="100%" rx="26" fill="url(#grid)"/>' if grid else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" class="{"static" if STATIC else ""}">{defs()}'
        f'<rect width="{width}" height="{height}" rx="26" fill="url(#surface)" stroke="{C["line"]}"/>'
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
    s = start(1200, 356, True)
    s += '<circle cx="1040" cy="65" r="250" fill="url(#halo)" class="glow"/>'
    s += '<circle cx="1040" cy="65" r="168" fill="none" stroke="#38BDF8" stroke-opacity=".13"/>'
    s += '<circle cx="1040" cy="65" r="124" fill="none" stroke="#8B7CFF" stroke-opacity=".16" stroke-dasharray="4 9"/>'
    s += '<path d="M0 300 C250 230 390 390 670 292 S1040 260 1200 305" fill="none" stroke="url(#edge)" stroke-opacity=".17" stroke-width="2"/>'
    # Monogram medallion / orbit motif
    s += '<g class="enter"><rect x="54" y="66" width="224" height="224" rx="34" fill="#0B1425" stroke="#294666" stroke-width="1.5"/>'
    s += '<rect x="65" y="77" width="202" height="202" rx="27" fill="none" stroke="url(#edge)" stroke-opacity=".55"/>'
    s += '<circle cx="166" cy="178" r="72" fill="#12243B" stroke="#315578"/>'
    s += '<circle cx="166" cy="178" r="87" fill="none" stroke="#38BDF8" stroke-opacity=".35" stroke-dasharray="2 8"/>'
    s += t(166,196,"VR",62,C["white"],800,'text-anchor="middle" letter-spacing="-4"')
    s += '<circle cx="241" cy="112" r="5" fill="#67E8F9"/><circle cx="91" cy="239" r="3" fill="#8B7CFF"/></g>'
    s += t(326,91,"VANSH RALLY",13,C["blue"],800,'letter-spacing="3.5"')
    s += t(326,151,"I build things",48,C["white"],800,'letter-spacing="-1.8"')
    s += t(326,205,"for the web.",48,C["white"],800,'letter-spacing="-1.8"')
    s += t(329,247,"Computer Science Student  /  Frontend Developer  /  Builder",15,C["muted"],500)
    s += '<rect x="328" y="273" width="112" height="30" rx="15" fill="#102C42" stroke="#24516C"/>'
    s += t(384,293,"REACT",10,C["cyan"],750,'text-anchor="middle" letter-spacing="1.2"')
    s += '<rect x="449" y="273" width="130" height="30" rx="15" fill="#19233F" stroke="#3A3C70"/>'
    s += t(514,293,"JAVASCRIPT",10,"#B8B0FF",750,'text-anchor="middle" letter-spacing="1.2"')
    s += '<rect x="588" y="273" width="105" height="30" rx="15" fill="#102C42" stroke="#24516C"/>'
    s += t(640,293,"PYTHON",10,C["cyan"],750,'text-anchor="middle" letter-spacing="1.2"')
    s += '<rect x="702" y="273" width="150" height="30" rx="15" fill="#19233F" stroke="#3A3C70"/>'
    s += t(777,293,"FULL-STACK",10,"#B8B0FF",750,'text-anchor="middle" letter-spacing="1.2"')
    s += t(1144,48,"01 / PROFILE",10,C["dim"],700,'text-anchor="end" letter-spacing="2"')
    s += '<path d="M328 326 H1144" stroke="url(#edge)" stroke-opacity=".7" stroke-width="2" class="dash"/>'
    s += '<circle cx="1144" cy="326" r="4" fill="#67E8F9" class="glow">' + ('' if STATIC else '<animate attributeName="r" values="3;6;3" dur="3s" repeatCount="indefinite"/>') + '</circle>'
    save("hero.svg", s)


def draw_social() -> None:
    tiles = [
        ("tile-github.svg", "GITHUB", "Code, experiments & open source", "GH", "01"),
        ("tile-linkedin.svg", "LINKEDIN", "Professional journey & updates", "in", "02"),
        ("tile-instagram.svg", "INSTAGRAM", "A little life beyond the terminal", "◎", "03")
    ]
    for index, (filename, title, subtitle, mark, number) in enumerate(tiles):
        s = start(390, 132)
        s += '<rect x="1" y="1" width="388" height="130" rx="24" fill="url(#surface)" stroke="#2A405E"/>'
        s += f'<rect x="18" y="18" width="82" height="96" rx="18" fill="#142A43" stroke="#294E70"/>'
        s += t(59, 78, mark, 31, C["cyan"], 800, 'text-anchor="middle"')
        s += t(121, 47, number + "  /  CONNECT", 9, C["blue"], 750, 'letter-spacing="1.8"')
        s += t(121, 76, title, 17, C["white"], 800, 'letter-spacing=".7"')
        s += t(121, 99, subtitle, 10, C["muted"], 500)
        s += t(358, 48, "↗", 20, C["blue"], 700, 'text-anchor="middle"')
        s += '<path d="M121 112 H356" stroke="url(#edge)" stroke-opacity=".45" stroke-width="1.5" class="dash"/>'
        save(filename, s)


def draw_activity(data: dict) -> None:
    placeholder = bool(data.get("placeholder", False))
    s = start(1200, 326, True)
    s += t(36, 43, "GITHUB / ACTIVITY", 11, C["blue"], 800, 'letter-spacing="2.4"')
    s += t(36, 76, "Consistency, in motion.", 27, C["white"], 750, 'letter-spacing="-.5"')
    s += t(36, 99, "A rolling 12-month view of public contributions.", 12, C["muted"])
    stats = [
        ("TOTAL CONTRIBUTIONS", "—" if placeholder else f'{data.get("total_contributions", 0):,}', "LAST 12 MONTHS"),
        ("ACTIVE DAYS", "—" if placeholder else data.get("active_days", 0), "DAYS WITH ACTIVITY"),
        ("CURRENT STREAK", "—" if placeholder else f'{data.get("current_streak", 0)}d', "CONSECUTIVE DAYS"),
        ("LONGEST STREAK", "—" if placeholder else f'{data.get("longest_streak", 0)}d', "IN THIS 12-MONTH WINDOW")
    ]
    positions = [(36, 130), (322, 130), (36, 222), (322, 222)]
    for i, ((label, value, caption), (x, y)) in enumerate(zip(stats, positions)):
        s += f'<g class="enter" style="animation-delay:{i * 90}ms"><rect x="{x}" y="{y}" width="268" height="78" rx="15" fill="#111F34" stroke="#293F5D"/>'
        s += t(x + 17, y + 29, label, 9, C["dim"], 750, 'letter-spacing="1.1"')
        s += t(x + 17, y + 59, value, 24, C["white"], 800)
        s += t(x + 249, y + 58, caption, 8, C["muted"], 600, 'text-anchor="end"')
        s += '</g>'
    # Chart panel
    s += '<rect x="620" y="115" width="544" height="185" rx="18" fill="#0D1728" stroke="#293F5D"/>'
    s += t(646, 144, "MONTHLY CONTRIBUTIONS", 10, C["muted"], 750, 'letter-spacing="1.6"')
    months = data.get("monthly", {})
    labels = list(months.keys())[-12:]
    values = [int(months[key]) for key in labels]
    if placeholder or not labels:
        s += t(892, 210, "AWAITING FIRST DATA SYNC", 12, C["dim"], 750, 'text-anchor="middle" letter-spacing="1.6"')
        for j in range(12):
            x = 650 + j * 41
            s += f'<rect x="{x}" y="176" width="22" height="72" rx="6" fill="#17263B"/>'
    else:
        max_value = max(values) or 1
        for j, (month, value) in enumerate(zip(labels, values)):
            x = 650 + j * 41
            height = max(3, 76 * value / max_value)
            s += f'<rect class="bar" style="animation-delay:{j * 45}ms" x="{x}" y="{250-height:.1f}" width="22" height="{height:.1f}" rx="6" fill="url(#bar)"><title>{escape(month)}: {value} contributions</title></rect>'
            s += t(x + 11, 270, month[-2:], 8, C["dim"], 600, 'text-anchor="middle"')
    busy = data.get("busiest_day", {})
    busy_text = "Busiest day: data pending" if placeholder else f'Busiest day  /  {busy.get("date", "—")}  ·  {busy.get("count", 0)} contributions'
    s += t(646, 291, busy_text, 10, C["blue"], 600)
    save("activity.svg", s)


def project_card(filename: str, index: str, name: str, description: str,
                 tags: str, motif: str) -> None:
    s = start(1200, 190, True)
    s += '<rect x="18" y="17" width="1164" height="156" rx="22" fill="#101C30" stroke="#2A405E"/>'
    s += f'<rect x="38" y="38" width="54" height="54" rx="15" fill="#152E49" stroke="#2F5578"/>'
    s += t(65, 73, index, 16, C["cyan"], 800, 'text-anchor="middle"')
    s += t(118, 57, "SELECTED BUILD  /  " + index, 9, C["blue"], 750, 'letter-spacing="1.7"')
    s += t(118, 91, name, 23, C["white"], 800, 'letter-spacing="-.4"')
    s += t(118, 119, description, 12, C["muted"], 500)
    s += f'<rect x="118" y="137" width="300" height="22" rx="11" fill="#172943" stroke="#29445F"/>'
    s += t(268, 152, tags, 9, C["cyan"], 700, 'text-anchor="middle" letter-spacing=".5"')
    # Project-specific visual motif on the right
    s += '<rect x="790" y="32" width="354" height="126" rx="16" fill="#0A1424" stroke="#263F5D"/>'
    if motif == "terminal":
        s += '<circle cx="814" cy="53" r="4" fill="#F38BA8"/><circle cx="829" cy="53" r="4" fill="#F9E2AF"/><circle cx="844" cy="53" r="4" fill="#A6E3A1"/>'
        s += t(814, 83, "$", 13, C["green"], 700)
        s += t(832, 83, "learn();", 13, C["white"], 650)
        s += t(814, 108, "01  practice  →  build", 10, C["blue"], 600)
        s += '<path d="M814 126 H1050" stroke="#29445F"/><path d="M814 126 H946" stroke="url(#edge)" stroke-width="2"/>'
    elif motif == "nodes":
        points = [(840, 65), (900, 50), (958, 85), (1020, 53), (1080, 91), (900, 125), (1040, 130)]
        links = [(0,1),(1,2),(2,3),(3,4),(1,5),(5,6),(2,6),(4,6)]
        for a,b in links:
            x1,y1=points[a]; x2,y2=points[b]
            s += f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#3B638A" stroke-width="1.5"/>'
        for j,(x,y) in enumerate(points):
            s += f'<circle cx="{x}" cy="{y}" r="{6 if j==2 else 4}" fill="{C["cyan"] if j==2 else C["violet"]}" stroke="#B8ECFF" stroke-opacity=".5"/>'
    else:
        s += '<rect x="826" y="47" width="280" height="94" rx="12" fill="#13243B" stroke="#2D496B"/>'
        s += t(846, 70, "HOME", 8, C["muted"], 700, 'letter-spacing="1.2"')
        s += t(846, 108, "24", 30, C["white"], 800)
        s += t(892, 108, "—", 18, C["cyan"], 700)
        s += t(1012, 108, "18", 30, C["white"], 800)
        s += t(846, 128, "TEAM A", 8, C["muted"], 650)
        s += t(1012, 128, "TEAM B", 8, C["muted"], 650)
    s += t(1143, 53, "↗", 19, C["blue"], 700, 'text-anchor="middle"')
    s += '<path d="M38 171 H1160" stroke="url(#edge)" stroke-opacity=".45" stroke-width="1.5" class="dash"/>'
    save(filename, s)


def draw_contributions(data: dict) -> None:
    days = data.get("days", [])
    today = date.today()
    if len(days) < 350:
        days = [{
            "date": (today - timedelta(days=364-i)).isoformat(),
            "contributionCount": 0
        } for i in range(365)]
    days = days[-364:]
    day_map = {item["date"]: int(item["contributionCount"]) for item in days}
    palette = ["#17253A", "#173D58", "#17628A", "#248CB5", "#45C9F5"]
    s = start(1200, 284, True)
    s += t(36, 43, "THE CONTRIBUTION GRID", 11, C["blue"], 800, 'letter-spacing="2.4"')
    s += t(36, 72, "Small steps. Compounded.", 25, C["white"], 750)
    s += t(1160, 17, "LAST 52 WEEKS", 9, C["dim"], 750, 'text-anchor="end" letter-spacing="1.5"')
    s += t(36, 158, "MON", 8, C["dim"], 650)
    s += t(36, 198, "WED", 8, C["dim"], 650)
    s += t(36, 238, "FRI", 8, C["dim"], 650)
    start_x, start_y, step, cell = 86, 130, 20, 16
    # Month labels sit just above the grid at the first week of each month.
    previous_month = None
    for col in range(52):
        first_day = days[col * 7] if col * 7 < len(days) else None
        if first_day:
            month = date.fromisoformat(first_day["date"]).strftime("%b")
            if month != previous_month:
                s += t(start_x + col * step, 123, month.upper(), 8, C["dim"], 650)
                previous_month = month
    # Draw in row-major order so the reveal cascades from top to bottom.
    for row in range(7):
        for col in range(52):
            item = days[col * 7 + row] if col * 7 + row < len(days) else None
            if item is None:
                continue
            count = int(item["contributionCount"])
            level = 0 if count == 0 else min(4, 1 + (count - 1) // 4)
            x, y = start_x + col * step, start_y + row * step
            delay = (row * 52 + col) * 3
            s += (f'<rect class="heat" style="animation-delay:{delay}ms" x="{x}" y="{y}" '
                  f'width="{cell}" height="{cell}" rx="3" fill="{palette[level]}">'
                  f'<title>{escape(item["date"])} · {count} contributions</title></rect>')
    for i, color in enumerate(palette):
        s += f'<rect x="{1010+i*23}" y="28" width="12" height="12" rx="3" fill="{color}"/>'
    s += t(1000, 42, "LESS", 8, C["dim"], 650, 'text-anchor="end"')
    s += t(1136, 42, "MORE", 8, C["dim"], 650, 'text-anchor="start"')
    if data.get("placeholder"):
        s += t(86, 221, "Contribution history will populate after the first successful workflow refresh.", 9, C["dim"], 500)
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
