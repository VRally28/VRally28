#!/usr/bin/env python3
"""Render the profile README as a coordinated stack of animated SVG cards."""
from __future__ import annotations

import base64
from io import BytesIO
import json
import os
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "cards"
FONT = ROOT / "assets" / "Inter-subset.woff2"
STATIC = os.getenv("STATIC") == "1"
USER = os.getenv("GH_USER", "VRally28")
W = 880
PAPER, PAPER_DARK, INK, SOFT, MUTED = "#f3f3f1", "#e4e4e0", "#111111", "#3a3a3c", "#707076"
BLUE, RED, GOLD = "#315BEE", "#ef4938", "#f4c52f"
PALETTE = [PAPER_DARK, "#cbd5ff", "#9baeff", "#6683ff", BLUE, "#2140d0"]

CSS = """
@keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(.02)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.4)}75%{opacity:1;transform:scale(1.08)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes tilein{0%{opacity:0;transform:translateY(36px) scale(.96)}100%{opacity:1;transform:none}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
.f{opacity:0;animation:fade .8s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;animation:grow .75s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .42s ease-out both}
.tile{opacity:0;animation:tilein .8s cubic-bezier(.2,.7,.2,1) both}
.live{animation:pulse 1.6s ease-in-out infinite}
@media(prefers-reduced-motion:reduce){.r,.f,.g,.p,.tile,.live{animation:none!important;opacity:1!important;transform:none!important}animate,animateTransform{display:none!important}}
.static .r,.static .f,.static .g,.static .p,.static .tile,.static .live{animation:none!important;opacity:1!important;transform:none!important}
"""


def refresh_data() -> None:
    token = os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN is required when refreshing contribution data.")
    today = date.today()
    start = today - timedelta(days=364)
    query = (
        'query($login:String!){user(login:$login){contributionsCollection(from:"'
        + start.isoformat() + 'T00:00:00Z",to:"' + today.isoformat()
        + 'T23:59:59Z"){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'
    )
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "VRally28-profile-cards"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError(f"Contribution query failed: {result.get('errors', 'user not found')}")
    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    counts = {date.fromisoformat(d["date"]): int(d["contributionCount"]) for d in days}
    active = sum(value > 0 for value in counts.values())
    busiest = max(days, key=lambda d: int(d["contributionCount"]), default={"date": today.isoformat(), "contributionCount": 0})
    cursor = today if counts.get(today, 0) else today - timedelta(days=1)
    current = 0
    while counts.get(cursor, 0):
        current += 1
        cursor -= timedelta(days=1)
    longest = streak = 0
    for day in days:
        streak = streak + 1 if int(day["contributionCount"]) else 0
        longest = max(longest, streak)
    monthly = Counter()
    for day in days:
        monthly[day["date"][:7]] += int(day["contributionCount"])
    months, cursor_month = [], start.replace(day=1)
    while cursor_month <= today.replace(day=1):
        months.append(cursor_month.strftime("%Y-%m"))
        cursor_month = (cursor_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps({
        "username": USER, "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": int(calendar["totalContributions"]), "active_days": active,
        "current_streak": current, "longest_streak": longest,
        "busiest_day": {"date": busiest["date"], "count": int(busiest["contributionCount"])},
        "monthly": {month: int(monthly[month]) for month in months[-12:]}, "days": days,
    }, indent=2) + "\n", encoding="utf-8")


def font_face() -> str:
    if not FONT.exists():
        return ""
    encoded = base64.b64encode(FONT.read_bytes()).decode("ascii")
    return f"@font-face{{font-family:Inter;src:url(data:font/woff2;base64,{encoded}) format('woff2');font-weight:100 900}}"


def svg(width: int, height: int, body: str, label: str) -> str:
    static = "static" if STATIC else ""
    body = "\n".join(line.rstrip() for line in body.splitlines())
    style = font_face() + CSS + "text{font-family:Inter,Arial,sans-serif}.serif{font-family:Georgia,'Times New Roman',serif}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(label)}" class="{static}"><title>{escape(label)}</title><style>{style}</style>{body}</svg>\n')


def write(name: str, width: int, height: int, body: str, label: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg(width, height, body, label), encoding="utf-8")


def text(x, y, value, size=16, color=INK, family="Inter,Arial,sans-serif", extra=""):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'


def delay(seconds: float) -> str:
    return f'style="animation-delay:{seconds:.2f}s"'


def hero() -> None:
    image = ROOT / "assets" / "portrait.png"
    portrait = Image.open(image).convert("RGB")
    portrait.thumbnail((640, 640), Image.Resampling.LANCZOS)
    optimized = BytesIO()
    portrait.save(optimized, format="JPEG", quality=90, optimize=True)
    encoded = base64.b64encode(optimized.getvalue()).decode("ascii")
    graphic = f'''<defs><clipPath id="portrait-circle"><circle cx="705" cy="205" r="120"/></clipPath></defs>
    <g class="f" {delay(.45)}><circle cx="705" cy="205" r="136" fill="#e7eaff"/>
    <circle cx="705" cy="205" r="128" fill="none" stroke="{BLUE}" stroke-opacity=".22" stroke-width="1"/>
    <image href="data:image/jpeg;base64,{encoded}" x="585" y="85" width="240" height="240" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-circle)"/>
    <circle cx="705" cy="205" r="120" fill="none" stroke="{BLUE}" stroke-width="2"/></g>'''
    body = f'''<rect width="880" height="420" rx="14" fill="{PAPER}"/>
    <g class="f" {delay(0)}><rect class="live" x="48" y="49" width="8" height="8" rx="2" fill="{BLUE}"/>{text(66,57,"CSE STUDENT · THAPAR INSTITUTE",12,MUTED,"monospace",'letter-spacing="1"')}</g>
    <text class="r serif" {delay(.15)} x="44" y="190" font-size="112" letter-spacing="-3" fill="{INK}">Vansh</text>
    <text class="r serif" {delay(.3)} x="44" y="290" font-style="italic" font-size="112" letter-spacing="-3" fill="{INK}">Rally</text>
    <g class="r" {delay(.55)}>{text(48,351,"I build useful things on the web and learn by making.",18,SOFT)}</g>
    <g class="f" {delay(.8)}>{text(48,402,"BUILD · EXPLORE · CONTRIBUTE",12,MUTED,"monospace",'letter-spacing=".8"')}</g>{graphic}'''
    write("hero-photo.svg", 880, 420, body, "Vansh Rally — CSE student and developer building useful things on the web.")


def heatmap(data: dict) -> None:
    days = data.get("days", [])
    if not days:
        days = [{"date": (date.today()-timedelta(days=i)).isoformat(), "contributionCount": 0} for i in range(364, -1, -1)]
    day_counts = {date.fromisoformat(item["date"]): int(item.get("contributionCount", item.get("count", 0))) for item in days}
    end = max(day_counts)
    start = end - timedelta(days=363)
    start -= timedelta(days=(start.weekday()+1) % 7)
    cols = min(53, (end-start).days // 7 + 1)
    x0, y0, step, cell = 44, 93, 15, 12
    out = [f'<rect width="880" height="205" rx="14" fill="{PAPER}"/>',
           f'<text class="r serif" {delay(6.35)} x="42" y="57" font-size="34" fill="{INK}">Every day, <tspan font-style="italic" fill="{BLUE}">in blue</tspan></text>',
           f'<text class="f" {delay(6.35)} x="836" y="54" text-anchor="end" font-size="11" letter-spacing="1" fill="{MUTED}" font-family="monospace">REFRESHED DAILY</text>']
    previous = None
    for col in range(cols):
        sunday = start + timedelta(days=col*7)
        if sunday.month != previous:
            out.append(text(x0+col*step, 82, sunday.strftime("%b").upper(), 9, MUTED, "monospace"))
            previous = sunday.month
        for row in range(7):
            d = sunday + timedelta(days=row)
            if d > end: continue
            count = day_counts.get(d, 0)
            level = 0 if count == 0 else min(5, 1 + (count-1)//5)
            out.append(f'<rect class="p" {delay(6.55+col*.012+row*.008)} x="{x0+col*step}" y="{y0+row*step}" width="{cell}" height="{cell}" rx="3" fill="{PALETTE[level]}"><title>{d.isoformat()}: {count} contributions</title></rect>')
    out.append(text(44, 197, "LESS", 9, MUTED, "monospace"))
    for i, color in enumerate(PALETTE): out.append(f'<rect x="{702+i*16}" y="185" width="11" height="11" rx="3" fill="{color}"/>')
    out.append(text(806, 197, "MORE", 9, MUTED, "monospace"))
    write("contributions.svg", 880, 205, "".join(out), "GitHub contributions over the last year, shown in cobalt blue.")


def activity(data: dict) -> None:
    months = sorted(data.get("monthly", {}).items())[-12:]
    maxval = max([int(v) for _, v in months] or [1])
    x0, base, chart_h, bw, gap = 40, 287, 145, 36, 11
    out = [f'<rect width="880" height="340" rx="14" fill="{PAPER}"/>',
           f'<text class="f" {delay(7.55)} x="40" y="54" font-size="11" letter-spacing="1" fill="{MUTED}" font-family="monospace">THE LAST 12 MONTHS ON GITHUB</text>',
           f'<text class="r serif" {delay(7.65)} x="38" y="111" font-size="49" fill="{INK}">{int(data.get("total_contributions",0)):,} <tspan font-style="italic">contributions</tspan></text>']
    best = max(months, key=lambda item: int(item[1]), default=("",0))
    for i, (month, value) in enumerate(months):
        h = max(4, round(int(value)/maxval*chart_h))
        x = x0+i*(bw+gap)
        color = BLUE if (month,value)==best else ("#c9c9c4" if i==len(months)-1 else INK)
        out.append(f'<rect class="g" {delay(7.85+i*.055)} x="{x}" y="{base-h}" width="{bw}" height="{h}" rx="4" fill="{color}"><title>{month}: {int(value):,}</title></rect>')
        out.append(text(x+bw/2, base+21, date.fromisoformat(month+"-01").strftime("%b"), 9, MUTED, "monospace",'text-anchor="middle"'))
    busy=data.get("busiest_day", {})
    metrics=[(f'{data.get("current_streak",0)} days',"current streak"),(str(data.get("active_days",0)),"active days"),(str(busy.get("count",0)),"on the busiest day")]
    for i,(big,small) in enumerate(metrics):
        y=105+i*82
        out.append(f'<g class="r" {delay(7.8+i*.15)}>{text(650,y,big,34,INK,"Georgia,serif")}{text(650,y+24,small,13,MUTED)}</g>')
        if i<2: out.append(f'<line x1="650" y1="{y+43}" x2="836" y2="{y+43}" stroke="#d8d8d4"/>')
    out.append(text(650, 339-6, f'BUSIEST DAY  {busy.get("date","—")}', 9, MUTED, "monospace"))
    write("activity.svg", 880, 340, "".join(out), f'{int(data.get("total_contributions",0)):,} contributions, {data.get("current_streak",0)} day streak, {data.get("active_days",0)} active days.')


def tile(filename: str, eyebrow: str, title: str, sub: str, color: str, foreground: str, delay_s: float) -> None:
    out=[f'<rect width="293" height="220" rx="14" fill="{color}"/>',
         f'<g class="tile" {delay(delay_s)}><text x="24" y="37" font-size="11" letter-spacing="1" fill="{foreground}" font-family="monospace">{escape(eyebrow)}</text>',
         f'<text x="24" y="104" class="serif" font-size="38" fill="{foreground}">{escape(title)}</text>',
         f'<text x="24" y="143" font-size="14" fill="{foreground}" opacity=".88">{escape(sub)}</text>',
         f'<path d="M24 181H269" stroke="{foreground}" stroke-opacity=".28"/><text x="269" y="204" text-anchor="end" font-size="15" fill="{foreground}">↗</text></g>']
    write(filename,293,220,"".join(out),f"{eyebrow}: {title}. {sub}")


def repo_card(filename: str, name: str, description: str, language: str, accent: str, delay_s: float) -> None:
    out=[f'<rect width="293" height="178" rx="14" fill="{PAPER}"/>',
         f'<g class="r" {delay(delay_s)}><rect x="24" y="29" width="8" height="8" rx="2" fill="{accent}"/>',
         text(42,38,name,17,INK,"Inter,Arial,sans-serif",'font-weight="600"')]
    for i,line in enumerate(description.split("|")): out.append(text(24,75+i*21,line,13,SOFT))
    out.extend([f'<text x="24" y="153" font-size="10" letter-spacing=".6" fill="{MUTED}" font-family="monospace">{escape(language.upper())}</text>',
                f'<text x="269" y="153" text-anchor="end" font-size="15" fill="{accent}">↗</text></g>'])
    write(filename,293,178,"".join(out),f"{name}: {description.replace('|',' ')}")


def main() -> None:
    if os.getenv("GH_TOKEN"): refresh_data()
    if not DATA.exists(): raise FileNotFoundError("Missing data/contributions.json; refresh contribution data first.")
    data=json.loads(DATA.read_text(encoding="utf-8"))
    hero()
    heatmap(data)
    activity(data)
    tile("build.svg","BUILD","Web & systems","Ideas shaped into useful tools.",BLUE,"#fff",9.1)
    tile("learn.svg","EXPLORE","New ground","AI, software and what comes next.",RED,"#fff",9.35)
    tile("community.svg","CONTRIBUTE","Build together","Hackathons, community and open source.",GOLD,INK,9.6)
    title=f'<rect width="880" height="64" fill="{INK}"/><text class="r serif" {delay(11.1)} x="42" y="46" font-size="34" fill="#fff">A few things <tspan font-style="italic">I\'ve built</tspan></text>'
    write("title-coding.svg",880,64,title,"A few things I've built")
    repo_card("repo-codevibe.svg","CODEVIBE","A browser-based coding practice platform.|Built for learning by doing.","HTML · CSS · JAVASCRIPT",BLUE,11.5)
    repo_card("repo-hack-helix.svg","HACK HELIX","A collaborative hackathon project.|Made with a team, around a real problem.","HACKATHON · PRODUCT",RED,11.65)
    repo_card("repo-basketball-scorecard.svg","BASKETBALL SCORECARD","A focused frontend for tracking|the score and rhythm of a game.","FRONTEND · JAVASCRIPT",GOLD,11.8)


if __name__ == "__main__":
    main()
