"""
Phase 4 — Web dashboard. Run with:
  python src/web.py
"""
import sys
import os
import html as htmllib
import threading
import webbrowser
from datetime import date, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

from weather import fetch_weather, weather_flags, WMO_DESCRIPTIONS
from sports import get_sports_events
from do312 import fetch_do312_events
from events import event_emoji

PORT = 8080

TYPE_COLORS = {
    "sports": "#5b9cf6",
    "music":  "#c084fc",
    "comedy": "#fb923c",
    "food":   "#34d399",
    "other":  "#94a3b8",
}

# ── CSS ────────────────────────────────────────────────────────────────────────
# Kept as a plain string so CSS braces don't need escaping in the f-string below.
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Barlow+Condensed:wght@600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #09090d;
  --s1:       #111118;
  --s2:       #16161f;
  --b1:       #1c1c28;
  --b2:       #252535;
  --text:     #eaecf0;
  --dim:      #606278;
  --amber:    #e8a73a;
  --r:        10px;
}

/* Subtle film grain */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 999;
  opacity: 0.032;
  background-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>");
  background-size: 180px;
}

body {
  background: var(--bg);
  background-image: radial-gradient(ellipse 90% 45% at 50% 0%, rgba(22, 28, 55, 0.7) 0%, transparent 65%);
  color: var(--text);
  font-family: 'DM Sans', -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: 5rem;
  min-height: 100vh;
}

/* ── Header ── */
header {
  padding: 2.75rem 1.5rem 2rem;
}

.site-title {
  font-family: 'Instrument Serif', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(2.6rem, 8vw, 4rem);
  letter-spacing: -0.025em;
  line-height: 1;
  color: var(--text);
  display: block;
  margin-bottom: 0.75rem;
  animation: fadeIn 0.6s ease both;
}

.header-sub {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
  animation: fadeIn 0.6s 0.1s ease both;
}

.header-chip {
  font-size: 0.75rem;
  color: var(--dim);
  background: var(--s1);
  border: 1px solid var(--b2);
  border-radius: 100px;
  padding: 0.22rem 0.7rem;
  white-space: nowrap;
}

.header-sep { color: var(--b2); font-size: 0.7rem; }

/* ── Section ── */
.section {
  padding: 0 1.5rem;
  margin-bottom: 2.75rem;
}

.section-rule {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  margin-bottom: 1.1rem;
}

.section-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--dim);
  white-space: nowrap;
  flex-shrink: 0;
}

.section-label.today { color: var(--amber); }

.section-rule::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--b2), transparent);
}

/* ── Weather chips ── */
.wx-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1.1rem;
}

.wx-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--s1);
  border: 1px solid var(--b2);
  border-radius: 100px;
  padding: 0.28rem 0.8rem;
  font-size: 0.76rem;
  color: var(--dim);
  white-space: nowrap;
}

.wx-chip .wx-day { font-weight: 600; color: var(--text); }

/* ── Cards grid ── */
.events {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.55rem;
}

@media (min-width: 520px) {
  .events { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 800px) {
  .events { grid-template-columns: 1fr 1fr 1fr; }
}

/* ── Card ── */
.card {
  position: relative;
  background: var(--s1);
  border: 1px solid var(--b1);
  border-radius: var(--r);
  padding: 1rem 1.1rem;
  text-decoration: none;
  display: block;
  overflow: hidden;

  opacity: 0;
  animation: slideUp 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: calc(var(--i, 0) * 55ms);

  transition: transform 0.2s ease, box-shadow 0.2s ease,
              background 0.2s ease, border-color 0.2s ease;
}

/* Left accent bar drawn via pseudo-element */
.card::before {
  content: '';
  position: absolute;
  left: 0; top: 12%; bottom: 12%;
  width: 2px;
  background: var(--tc, transparent);
  border-radius: 0 2px 2px 0;
  opacity: 0.85;
  transition: top 0.2s ease, bottom 0.2s ease, opacity 0.2s ease;
}

.card:hover {
  transform: translateY(-3px);
  background: var(--s2);
  border-color: var(--b2);
  box-shadow: 0 16px 40px rgba(0,0,0,0.55);
}

.card:hover::before {
  top: 8%; bottom: 8%;
  opacity: 1;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .card, .site-title, .header-sub {
    animation: none; opacity: 1;
  }
  .card:hover { transform: none; }
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
}

.card-emoji {
  font-size: 1.1rem;
  flex-shrink: 0;
  line-height: 1.45;
}

.card-body { min-width: 0; }

.card-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-venue {
  font-size: 0.75rem;
  color: var(--dim);
  margin-top: 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.8rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.69rem;
  color: var(--dim);
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  white-space: nowrap;
}

.flag {
  margin-left: auto;
  font-size: 0.88rem;
  line-height: 1;
}

.no-events {
  font-size: 0.85rem;
  color: var(--dim);
  font-style: italic;
  padding: 0.2rem 0;
}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_time(t):
    h, m = map(int, t.split(":"))
    s = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{s}" if m else f"{h12}{s}"


def _e(s):
    return htmllib.escape(str(s))


def _wx_chip(label, day):
    if not day:
        return ""
    parts = [f"{day['high']}°F"]
    desc = WMO_DESCRIPTIONS.get(day["weather_code"], "")
    if desc:
        parts.append(desc)
    if day["precip_prob"] > 0:
        parts.append(f"{day['precip_prob']}% rain")
    flag = weather_flags(day, "outdoor")
    return (
        f'<span class="wx-chip">'
        f'<span class="wx-day">{label}</span>'
        f' {_e(", ".join(parts))} {flag}'
        f'</span>'
    )


def _card(event, weather, show_day, idx):
    day = weather.get(event["date"])
    flag = weather_flags(day, event["indoor_outdoor"]) if day else ""
    color = TYPE_COLORS.get(event["type"], "#6b7280")
    d = date.fromisoformat(event["date"])
    day_part = f"{d.strftime('%a')} {_fmt_time(event['time'])}" if show_day else _fmt_time(event["time"])

    return (
        f'<a class="card" href="{_e(event["url"])}" target="_blank" rel="noopener"'
        f' style="--tc:{color};--i:{idx}">'
        f'<div class="card-top">'
        f'<span class="card-emoji">{event_emoji(event)}</span>'
        f'<div class="card-body">'
        f'<div class="card-name">{_e(event["name"])}</div>'
        f'<div class="card-venue">@ {_e(event["venue"])}</div>'
        f'</div></div>'
        f'<div class="card-meta">'
        f'<span class="tag">{_e(day_part)}</span>'
        f'<span class="tag">{_e(event["neighborhood"])}</span>'
        f'<span class="tag">{_e(event["price_range"])}</span>'
        f'<span class="flag">{flag}</span>'
        f'</div></a>'
    )


def _section(label, label_class, wx_html, cards, empty_msg):
    inner = "\n".join(cards) if cards else f'<p class="no-events">{empty_msg}</p>'
    return (
        f'<section class="section">'
        f'<div class="section-rule">'
        f'<span class="section-label {label_class}">{label}</span>'
        f'</div>'
        f'{wx_html}'
        f'<div class="events">{inner}</div>'
        f'</section>'
    )


# ── Page builder ──────────────────────────────────────────────────────────────

def build_page():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    saturday = monday + timedelta(days=5)
    sunday = monday + timedelta(days=6)

    try:
        weather = fetch_weather()
    except Exception:
        weather = {}

    try:
        sports = get_sports_events(monday, sunday)
    except Exception:
        sports = []

    try:
        culture = fetch_do312_events(monday, sunday)
    except Exception:
        culture = []

    all_events = sorted(sports + culture, key=lambda e: (e["date"], e["time"]))

    today_str = today.isoformat()
    weekend_dates = {friday.isoformat(), saturday.isoformat(), sunday.isoformat()}
    later_dates = set()
    d = today + timedelta(days=1)
    while d < friday:
        later_dates.add(d.isoformat())
        d += timedelta(days=1)

    today_evts   = [e for e in all_events if e["date"] == today_str][:7]
    weekend_evts = [e for e in all_events if e["date"] in weekend_dates][:7]
    later_evts   = [e for e in all_events if e["date"] in later_dates][:7]

    # Header
    highs = [w["high"] for w in weather.values() if w]
    temp_range = f"{min(highs)}–{max(highs)}°F" if highs else ""
    week_label = (
        f"{monday.strftime('%a')} {monday.strftime('%b')} {monday.day}"
        " – "
        f"{sunday.strftime('%a')} {sunday.strftime('%b')} {sunday.day}"
    )

    chips = f'<span class="header-chip">{_e(week_label)}</span>'
    if temp_range:
        chips += f'<span class="header-sep">·</span><span class="header-chip">🌡️ {_e(temp_range)}</span>'

    header_html = (
        f'<header>'
        f'<span class="site-title">Chi This Week</span>'
        f'<div class="header-sub">{chips}</div>'
        f'</header>'
    )

    # TODAY
    today_wx = weather.get(today_str)
    today_wx_html = ""
    if today_wx:
        today_wx_html = f'<div class="wx-row">{_wx_chip(today.strftime("%A"), today_wx)}</div>'
    today_sec = _section(
        f"Today · {today.strftime('%A')}",
        "today",
        today_wx_html,
        [_card(e, weather, False, i) for i, e in enumerate(today_evts)],
        "Nothing on the radar today.",
    )

    # THIS WEEKEND
    wx_pills = "".join(
        _wx_chip(lbl, weather.get(d.isoformat()))
        for d, lbl in [(friday, "Fri"), (saturday, "Sat"), (sunday, "Sun")]
    )
    weekend_sec = _section(
        "This Weekend",
        "",
        f'<div class="wx-row">{wx_pills}</div>' if wx_pills else "",
        [_card(e, weather, True, i) for i, e in enumerate(weekend_evts)],
        "Nothing lined up yet.",
    )

    # LATER THIS WEEK
    later_sec = _section(
        "Later This Week",
        "",
        "",
        [_card(e, weather, True, i) for i, e in enumerate(later_evts)],
        "Quiet stretch — save your money 💤",
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chi This Week</title>
  <style>{CSS}</style>
</head>
<body>
  {header_html}
  {today_sec}
  {weekend_sec}
  {later_sec}
</body>
</html>"""


# ── Server ────────────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = build_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    server = HTTPServer(("", PORT), _Handler)
    url = f"http://localhost:{PORT}"
    print(f"Chi This Week → {url}")
    print("Ctrl+C to stop")
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
