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

from weather import fetch_weather, weather_flags, format_day_summary
from sports import get_sports_events
from do312 import fetch_do312_events
from events import event_emoji

PORT = 8080

TYPE_COLORS = {
    "sports":  "#3b82f6",
    "music":   "#a78bfa",
    "comedy":  "#fbbf24",
    "food":    "#34d399",
    "other":   "#6b7280",
}


def _fmt_time(t):
    h, m = map(int, t.split(":"))
    s = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{s}" if m else f"{h12}{s}"


def _esc(s):
    return htmllib.escape(str(s))


def _card(event, weather, show_day=True):
    day = weather.get(event["date"])
    flag = weather_flags(day, event["indoor_outdoor"]) if day else ""
    emoji = event_emoji(event)
    color = TYPE_COLORS.get(event["type"], "#6b7280")
    name = _esc(event["name"])
    venue = _esc(event["venue"])
    nbhd = _esc(event["neighborhood"])
    price = _esc(event["price_range"])
    url = _esc(event["url"])
    time_str = _fmt_time(event["time"])

    if show_day:
        d = date.fromisoformat(event["date"])
        day_part = f"{d.strftime('%a')} {time_str}"
    else:
        day_part = time_str

    return f"""
<a class="card" href="{url}" target="_blank" rel="noopener"
   style="border-left-color:{color}">
  <div class="card-top">
    <span class="card-emoji">{emoji}</span>
    <div>
      <div class="card-name">{name}</div>
      <div class="card-venue">@ {venue}</div>
    </div>
  </div>
  <div class="card-meta">
    <span class="tag">{day_part}</span>
    <span class="tag">{nbhd}</span>
    <span class="tag">{price}</span>
    <span class="flag">{flag}</span>
  </div>
</a>"""


def _section(label, label_class, weather_html, event_cards, empty_msg):
    cards_html = "\n".join(event_cards) if event_cards else (
        f'<p class="no-events">{empty_msg}</p>'
    )
    return f"""
<section class="section">
  <div class="section-header">
    <span class="section-label {label_class}">{label}</span>
  </div>
  {weather_html}
  <div class="events">
    {cards_html}
  </div>
</section>"""


def _weather_pill(label, day):
    if not day:
        return ""
    desc_parts = [f"{day['high']}°F"]
    from weather import WMO_DESCRIPTIONS
    desc = WMO_DESCRIPTIONS.get(day["weather_code"], "")
    if desc:
        desc_parts.append(desc)
    if day["precip_prob"] > 0:
        desc_parts.append(f"{day['precip_prob']}% rain")
    flag = weather_flags(day, "outdoor")
    summary = ", ".join(desc_parts)
    return f'<span class="wx-pill"><b>{label}</b> {_esc(summary)} {flag}</span>'


def build_page():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    saturday = monday + timedelta(days=5)
    sunday = monday + timedelta(days=6)

    # ── Fetch data ──────────────────────────────────────────────────────
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

    # ── Bucket into time blocks ─────────────────────────────────────────
    today_str = today.isoformat()
    weekend_dates = {friday.isoformat(), saturday.isoformat(), sunday.isoformat()}
    later_dates = set()
    d = today + timedelta(days=1)
    while d < friday:
        later_dates.add(d.isoformat())
        d += timedelta(days=1)

    today_events   = [e for e in all_events if e["date"] == today_str][:7]
    weekend_events = [e for e in all_events if e["date"] in weekend_dates][:7]
    later_events   = [e for e in all_events if e["date"] in later_dates][:7]

    # ── Header values ───────────────────────────────────────────────────
    week_highs = [w["high"] for w in weather.values() if w]
    temp_range = f"{min(week_highs)}–{max(week_highs)}°F" if week_highs else ""
    week_label = (
        f"{monday.strftime('%a')} {monday.strftime('%b')} {monday.day}"
        f" – "
        f"{sunday.strftime('%a')} {sunday.strftime('%b')} {sunday.day}"
    )

    # ── TODAY section ───────────────────────────────────────────────────
    today_wx = weather.get(today_str)
    today_wx_html = ""
    if today_wx:
        today_wx_html = f'<div class="weather-block">{_weather_pill(today.strftime("%A"), today_wx)}</div>'
    today_cards = [_card(e, weather, show_day=False) for e in today_events]
    today_sec = _section(
        f"TODAY · {today.strftime('%A')}",
        "today",
        today_wx_html,
        today_cards,
        "Nothing on the radar today."
    )

    # ── THIS WEEKEND section ────────────────────────────────────────────
    wx_pills = "".join(
        _weather_pill(lbl, weather.get(d.isoformat()))
        for d, lbl in [(friday, "Fri"), (saturday, "Sat"), (sunday, "Sun")]
    )
    weekend_wx_html = f'<div class="weather-block">{wx_pills}</div>' if wx_pills else ""
    weekend_cards = [_card(e, weather) for e in weekend_events]
    weekend_sec = _section(
        "THIS WEEKEND",
        "",
        weekend_wx_html,
        weekend_cards,
        "Nothing lined up yet."
    )

    # ── LATER THIS WEEK section ─────────────────────────────────────────
    later_cards = [_card(e, weather) for e in later_events]
    later_sec = _section(
        "LATER THIS WEEK",
        "",
        "",
        later_cards,
        "Quiet stretch — save your money 💤"
    )

    # ── Assemble page ───────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chi This Week</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:           #0f1117;
      --surface:      #1c1e26;
      --surface-hover:#22252f;
      --border:       #272a36;
      --text:         #dde2ec;
      --muted:        #5c6275;
      --muted2:       #8891a5;
      --accent:       #5b9cf6;
      --today:        #f0a040;
      --radius:       8px;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, sans-serif;
      font-size: 15px;
      line-height: 1.5;
      max-width: 920px;
      margin: 0 auto;
      padding-bottom: 4rem;
    }}

    /* ── Header ── */
    header {{
      padding: 1.4rem 1.25rem 1.1rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 1.75rem;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 0.4rem;
    }}
    .site-title {{
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--text);
    }}
    .header-meta {{
      font-size: 0.82rem;
      color: var(--muted2);
    }}

    /* ── Sections ── */
    .section {{
      padding: 0 1.25rem 0.5rem;
      margin-bottom: 1.75rem;
    }}
    .section-label {{
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted2);
      margin-bottom: 0.75rem;
      display: block;
    }}
    .section-label.today {{
      color: var(--today);
    }}

    /* ── Weather block ── */
    .weather-block {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 0.55rem 0.9rem;
      margin-bottom: 0.75rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.25rem 1.25rem;
    }}
    .wx-pill {{
      font-size: 0.8rem;
      color: var(--muted2);
      white-space: nowrap;
    }}
    .wx-pill b {{
      color: var(--text);
      font-weight: 600;
    }}

    /* ── Event cards grid ── */
    .events {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 0.5rem;
    }}
    @media (min-width: 540px) {{
      .events {{ grid-template-columns: 1fr 1fr; }}
    }}
    @media (min-width: 780px) {{
      .events {{ grid-template-columns: 1fr 1fr 1fr; }}
    }}

    /* ── Card ── */
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 3px solid transparent;
      border-radius: var(--radius);
      padding: 0.75rem 0.9rem;
      text-decoration: none;
      display: block;
      transition: background 0.12s, border-color 0.12s;
    }}
    .card:hover {{
      background: var(--surface-hover);
      border-color: #353848;
      border-left-color: inherit;
    }}
    .card-top {{
      display: flex;
      align-items: flex-start;
      gap: 0.55rem;
    }}
    .card-emoji {{
      font-size: 1.05rem;
      flex-shrink: 0;
      margin-top: 1px;
    }}
    .card-name {{
      font-size: 0.88rem;
      font-weight: 500;
      color: var(--text);
      line-height: 1.35;
    }}
    .card-venue {{
      font-size: 0.78rem;
      color: var(--muted2);
      margin-top: 0.1rem;
    }}
    .card-meta {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.3rem;
      margin-top: 0.6rem;
    }}
    .tag {{
      font-size: 0.72rem;
      color: var(--muted2);
      background: rgba(255,255,255,0.05);
      border-radius: 3px;
      padding: 0.15rem 0.45rem;
      white-space: nowrap;
    }}
    .flag {{
      font-size: 0.85rem;
      margin-left: auto;
    }}

    .no-events {{
      font-size: 0.85rem;
      color: var(--muted);
      padding: 0.35rem 0;
    }}
  </style>
</head>
<body>
  <header>
    <span class="site-title">Chi This Week</span>
    <span class="header-meta">
      {_esc(week_label)}
      {"&nbsp;·&nbsp;🌡️ Highs " + _esc(temp_range) if temp_range else ""}
    </span>
  </header>

  {today_sec}
  {weekend_sec}
  {later_sec}
</body>
</html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = build_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # quiet


def main():
    server = HTTPServer(("", PORT), _Handler)
    url = f"http://localhost:{PORT}"
    print(f"Chi This Week → {url}")
    print("Ctrl+C to stop\n")
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
