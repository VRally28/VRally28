#!/usr/bin/env python3
"""Generate animated, self-contained SVG cards for the GitHub profile README."""
from __future__ import annotations
import base64, json, os, urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "cards"
STATIC = os.getenv("STATIC", "0") == "1"
BG, PANEL, ACCENT, VIOLET, TEXT, MUTED = "#0B1020", "#111A2E", "#38BDF8", "#818CF8", "#E5EEF9", "#91A4BD"
FONT_PATH = ROOT / "assets" / "Inter-subset.woff2"

def fetch_contributions():
    token = os.getenv("GH_TOKEN")
    user = os.getenv("GH_USER", "VRally28")
    if not token:
        raise RuntimeError("GH_TOKEN is required to refresh contribution data.")
    query = """query($login:String!){user(login:$login){contributionsCollection(from:FROM,to:TO){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    today = date.today()
    start = today - timedelta(days=364)
    q = query.replace("FROM", start.isoformat() + "T00:00:00Z").replace("TO", today.isoformat() + "T23:59:59Z")
    body = json.dumps({"query": q, "variables": {"login": user}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-card-generator"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + str(payload["errors"]))
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    counts = [int(d["contributionCount"]) for d in days]
    active = [d for d in days if int(d["contributionCount"]) > 0]
    busiest = max(days, key=lambda d: int(d["contributionCount"]), default={"date": today.isoformat(), "contributionCount": 0})
    monthly = Counter(d["date"][:7] for d in days if int(d["contributionCount"]) > 0)
    # Current streak includes today, or yesterday if today has no contribution.
    by_date = {date.fromisoformat(d["date"]): int(d["contributionCount"]) for d in days}
    cursor = today if by_date.get(today, 0) else today - timedelta(days=1)
    streak = 0
    while by_date.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    longest, run = 0, 0
    for d in days:
        run = run + 1 if int(d["contributionCount"]) else 0
        longest = max(longest, run)
    months = [(start.replace(day=1) + timedelta(days=32*i)).replace(day=1).strftime("%Y-%m") for i in range(12)]
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps({
        "username": user, "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": int(calendar["totalContributions"]), "active_days": len(active),
        "current_streak": streak, "longest_streak": longest,
        "busiest_day": {"date": busiest["date"], "count": int(busiest["contributionCount"])},
        "monthly": {m: int(monthly.get(m, 0)) for m in months}, "days": days
    }, indent=2) + "\n", encoding="utf-8")

def load_font():
    if FONT_PATH.exists():
        return "data:font/woff2;base64," + base64.b64encode(FONT_PATH.read_bytes()).decode()
    return None

def svg_start(w, h, delay=0):
    font = load_font()
    face = f"@font-face{{font-family:Inter;src:url('{font}') format('woff2');font-weight:100 900}}" if font else ""
    motion = "" if STATIC else """
    .enter{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) forwards}
    .glow{animation:pulse 4s ease-in-out infinite}
    .draw{stroke-dasharray:900;stroke-dashoffset:900;animation:draw 1.8s ease forwards}
    @keyframes rise{to{opacity:1;transform:translateY(0)}}
    @keyframes pulse{50%{opacity:.55}}
    @keyframes draw{to{stroke-dashoffset:0}}
    @media(prefers-reduced-motion:reduce){.enter,.glow,.draw{animation:none!important;opacity:1;stroke-dashoffset:0}}
    """
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
    <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{PANEL}"/><stop offset="1" stop-color="{BG}"/></linearGradient>
    <linearGradient id="accent"><stop stop-color="{ACCENT}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>
    <style>{face}text{{font-family:Inter,ui-sans-serif,system-ui,sans-serif}}{motion}</style></defs>
    <rect width="{w}" height="{h}" rx="24" fill="url(#bg)" stroke="#263650"/>
    <circle cx="{w-35}" cy="20" r="100" fill="{ACCENT}" opacity=".055" class="glow"/>
    '''

def svg_end():
    return "</svg>\n"

def text(x, y, value, size=18, fill=TEXT, weight=500, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" {extra}>{escape(str(value))}</text>'

def card_shell(title, subtitle, w=1200, h=180):
    return svg_start(w,h) + text(38,48,title,15,ACCENT,700,'letter-spacing="2"') + text(38,78,subtitle,13,MUTED)

def write(name, content):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/name).write_text(content + svg_end(), encoding="utf-8")

def main():
    if os.getenv("GH_TOKEN"):
        fetch_contributions()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    # Hero
    s = svg_start(1200,270)
    s += '<rect x="28" y="28" width="214" height="214" rx="30" fill="#172742" stroke="#2C4568"/>'
    s += text(135,163,"VR",72,ACCENT,800,'text-anchor="middle"')
    s += text(285,93,"VANSH RALLY",15,ACCENT,700,'letter-spacing="3"')
    s += text(285,145,"Building useful things for the web.",36,TEXT,750)
    s += text(287,184,"Computer Science Student  ·  Frontend Developer  ·  Open Source",17,MUTED)
    s += text(287,224,"React • JavaScript • Python • Exploring full-stack engineering",15,TEXT)
    if not STATIC:
        s += '<path d="M285 245 H1100" stroke="url(#accent)" stroke-width="2" class="draw"/>'
        s += '<circle cx="1110" cy="245" r="5" fill="#38BDF8"><animate attributeName="r" values="4;7;4" dur="2.4s" repeatCount="indefinite"/></circle>'
    else:
        s += '<path d="M285 245 H1100" stroke="url(#accent)" stroke-width="2"/>'
    write("hero.svg", s)

    # Social tiles
    tiles = [("tile-github.svg","GITHUB","Code, experiments & projects","GH"),
             ("tile-linkedin.svg","LINKEDIN","Professional updates & work","in"),
             ("tile-instagram.svg","INSTAGRAM","A little beyond the terminal","◎")]
    for i,(filename,title,desc,mark) in enumerate(tiles):
        s = svg_start(380,132)
        s += f'<rect x="14" y="14" width="352" height="104" rx="18" fill="#14213A" stroke="#2B4262"/>'
        s += text(38,78,mark,35,ACCENT,800)
        s += text(105,57,title,14,TEXT,750,'letter-spacing="1.5"')
        s += text(105,83,desc,11,MUTED)
        if not STATIC:
            s += f'<path d="M28 112 H350" stroke="url(#accent)" stroke-width="2" class="draw" style="animation-delay:{i*.15}s"/>'
        write(filename,s)

    # Activity summary + monthly bars
    s = card_shell("CONTRIBUTION PULSE", "A rolling 12-month snapshot from GitHub", h=230)
    stats = [("TOTAL CONTRIBUTIONS",data.get("total_contributions",0)),("ACTIVE DAYS",data.get("active_days",0)),("CURRENT STREAK",f'{data.get("current_streak",0)} days'),("LONGEST STREAK",f'{data.get("longest_streak",0)} days')]
    for i,(label,value) in enumerate(stats):
        x=38+i*286
        s += text(x,130,str(value),31,TEXT,750)
        s += text(x,153,label,11,MUTED,650,'letter-spacing="1"')
    busy=data.get("busiest_day",{})
    s += text(38,198,f'Busiest day: {busy.get("date","—")}  ·  {busy.get("count",0)} contributions',13,ACCENT,600)
    months=data.get("monthly",{})
    vals=list(months.values())[-12:] or [0]
    labels=list(months.keys())[-12:]
    maxv=max(vals) or 1
    for i,(label,val) in enumerate(zip(labels,vals)):
        x=650+i*42
        height=54*val/maxv
        s += f'<rect x="{x}" y="{185-height:.1f}" width="22" height="{height:.1f}" rx="5" fill="url(#accent)" opacity=".85"/>'
        s += text(x+11,211,label[-2:],9,MUTED,500,'text-anchor="middle"')
    write("activity.svg",s)

    # Featured projects
    projects=[
      ("repo-codevibe.svg","CODEVIBE","Browser-based coding practice platform","HTML • CSS • JavaScript","https://github.com/VRally28/CODEVIBE-"),
      ("repo-hack-helix.svg","HACK HELIX","Hackathon project and collaborative build","Hackathon • Development","https://github.com/VRally28/hack-helix"),
      ("repo-basketball-scorecard.svg","BASKETBALL SCORECARD","A lightweight basketball scoring project","Frontend • JavaScript","https://github.com/VRally28/basketball-scorecard")]
    for i,(filename,name,desc,tags,url) in enumerate(projects):
        s=svg_start(1200,142)
        s += '<rect x="20" y="18" width="1160" height="106" rx="18" fill="#14213A" stroke="#2B4262"/>'
        s += text(48,61,f"0{i+1}",20,ACCENT,750)
        s += text(110,57,name,19,TEXT,750)
        s += text(110,84,desc,13,MUTED)
        s += text(110,108,tags,11,ACCENT,600)
        s += text(1120,77,"↗",28,ACCENT,600,'text-anchor="middle"')
        if not STATIC:
            s += '<path d="M42 119 H1150" stroke="url(#accent)" stroke-width="2" class="draw"/>'
        write(filename,s)

    # Contribution heatmap (52 weeks x 7 days)
    days=data.get("days",[])
    if len(days)<350:
        days=[{"date":(date.today()-timedelta(days=364-i)).isoformat(),"contributionCount":0} for i in range(365)]
    s=svg_start(1200,190)
    s += text(32,35,"CONTRIBUTION MAP",14,ACCENT,700,'letter-spacing="2"')
    s += text(1165,35,"Less  ·  More",11,MUTED,500,'text-anchor="end"')
    palette=["#17243A","#183A56","#17618A","#258BB5","#38BDF8"]
    start_x,start_y,cell,gap=34,56,11,4
    for idx,d in enumerate(days[-364:]):
        col,row=idx//7,idx%7
        count=int(d.get("contributionCount",0))
        level=0 if count==0 else min(4,1+count//4)
        x,y=start_x+col*(cell+gap),start_y+row*(cell+gap)
        s += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{palette[level]}"/>'
    for i,c in enumerate(palette):
        s += f'<rect x="{1035+i*25}" y="15" width="12" height="12" rx="3" fill="{c}"/>'
    write("contributions.svg",s)

if __name__ == "__main__":
    main()
