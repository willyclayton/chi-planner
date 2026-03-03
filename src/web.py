"""
Phase 4 — Web dashboard. Run with:  python src/web.py
"""
import sys
import os
import json as _json
import html as htmllib
import threading
import webbrowser
from datetime import date, datetime, timedelta, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

from weather import fetch_weather, weather_flags, WMO_DESCRIPTIONS
from sports import get_sports_events
from do312 import fetch_do312_events
from events import event_emoji

PORT = 8080

DATA_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SAMPLE_FILE  = os.path.join(DATA_DIR, "sample_events.json")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")

TYPE_COLORS = {
    "sports": "#5b9cf6",
    "music":  "#c084fc",
    "comedy": "#fb923c",
    "food":   "#34d399",
    "other":  "#94a3b8",
}

# ── Data helpers ───────────────────────────────────────────────────────────────

def _load_ratings():
    if not os.path.exists(RATINGS_FILE):
        return []
    with open(RATINGS_FILE) as f:
        return _json.load(f)


def _save_rating(event: dict, rating: int):
    """Upsert: update existing entry by name, or append."""
    ratings = _load_ratings()
    entry = {
        "event":    event,
        "rating":   rating,
        "rated_at": datetime.now(timezone.utc).isoformat(),
    }
    for i, r in enumerate(ratings):
        if r["event"]["name"] == event["name"]:
            ratings[i] = entry
            break
    else:
        ratings.append(entry)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RATINGS_FILE, "w") as f:
        _json.dump(ratings, f, indent=2)


# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:      #f6f5f1;
  --surface: #ffffff;
  --border:  #e8e5df;
  --text:    #1c1a18;
  --dim:     #786f64;
  --accent:  #1d4ed8;
  --r:       8px;
  --yes: #16a34a;
  --mid: #d97706;
  --no:  #dc2626;
}

body {
  background: var(--bg);
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
  padding: 2rem 1.5rem 1.25rem;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.site-title {
  font-size: 26px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.02em;
}

.header-meta {
  font-size: 0.8rem;
  color: var(--dim);
}

/* ── Tab bar ── */
.tab-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 0 1.5rem;
  display: flex;
}

.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.7rem 1rem;
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--dim);
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* ── Section ── */
.section {
  padding: 0 1.5rem;
  margin-bottom: 2.5rem;
  margin-top: 2rem;
}

.section-rule {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  margin-bottom: 1rem;
}

.section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--dim);
  white-space: nowrap;
  flex-shrink: 0;
}

.section-label.today { color: var(--accent); }

.section-rule::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* ── Weather chips ── */
.wx-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1rem;
}

.wx-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 0.25rem 0.75rem;
  font-size: 0.76rem;
  color: var(--dim);
  white-space: nowrap;
}

.wx-chip .wx-day { font-weight: 600; color: var(--text); }

/* ── Cards grid ── */
.events {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.5rem;
}

@media (min-width: 520px) {
  .events { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 800px) {
  .events { grid-template-columns: 1fr 1fr 1fr; }
}

/* ── Swipe row wrapper ── */
.swipe-row {
  position: relative;
  border-radius: var(--r);
  overflow: hidden;
}

/* ── Card ── */
.card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 1rem 1.1rem;
  text-decoration: none;
  display: block;
  overflow: hidden;
  touch-action: pan-y;

  opacity: 0;
  animation: fadeIn 0.3s ease forwards;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  transition: box-shadow 0.18s ease;
}

/* Left accent bar */
.card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--tc, transparent);
}

/* Rating dot */
.card::after {
  content: '';
  position: absolute;
  top: 8px; right: 8px;
  width: 6px; height: 6px;
  border-radius: 50%;
  display: none;
}

.swipe-row[data-rated]   .card::after { display: block; }
.swipe-row[data-rated="1"]  .card::after { background: var(--yes); }
.swipe-row[data-rated="0"]  .card::after { background: var(--mid); }
.swipe-row[data-rated="-1"] .card::after { background: var(--no); }

@media (hover: hover) {
  .swipe-row:hover .card {
    box-shadow: 0 4px 14px rgba(0,0,0,0.09);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .card { animation: none; opacity: 1; }
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
  font-size: 14px;
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
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.69rem;
  color: var(--dim);
  background: var(--bg);
  border: 1px solid var(--border);
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

/* ── Rate strip ── */
.rate-strip {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 72px;
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 0.18s ease;
}

@media (hover: hover) {
  .swipe-row:hover .rate-strip {
    transform: translateX(0);
  }
}

.swipe-row.open .rate-strip {
  transform: translateX(0);
}

.r-btn {
  flex: 1;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  transition: filter 0.12s;
}

.r-btn:hover  { filter: brightness(1.12); }
.r-btn:active { filter: brightness(0.92); }

.r-yes { background: var(--yes); }
.r-mid { background: var(--mid); }
.r-no  { background: var(--no); }

/* ── Train tab ── */
.train-header {
  padding: 1.5rem 1.5rem 0.75rem;
}

.train-stats {
  font-size: 0.8rem;
  color: var(--dim);
  margin-bottom: 0.75rem;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 0.28rem 0.85rem;
  font-size: 0.78rem;
  font-family: inherit;
  color: var(--dim);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}

.chip.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.train-list {
  padding: 0.75rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
"""

# ── Static JS (no Python f-string interpolation needed) ───────────────────────
JS = r"""
// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const target = btn.dataset.tab;
    document.getElementById('tab-week').hidden  = target !== 'week';
    document.getElementById('tab-train').hidden = target !== 'train';
  });
});

// ── Mobile swipe ──────────────────────────────────────────────────────────────
function attachSwipe(row) {
  let startX = 0, startY = 0, tracking = false;

  row.addEventListener('pointerdown', e => {
    startX = e.clientX;
    startY = e.clientY;
    tracking = true;
  });

  row.addEventListener('pointermove', e => {
    if (!tracking) return;
    const dx = startX - e.clientX;
    const dy = Math.abs(e.clientY - startY);
    if (dx > 50 && dy < 40)  row.classList.add('open');
    if (dx < -20)             row.classList.remove('open');
  });

  row.addEventListener('pointerup',     () => { tracking = false; });
  row.addEventListener('pointercancel', () => { tracking = false; });
}

// ── Rating fetch ──────────────────────────────────────────────────────────────
function attachRating(row, onSuccess) {
  row.querySelectorAll('.r-btn').forEach(btn => {
    btn.addEventListener('click', async e => {
      e.preventDefault();
      e.stopPropagation();
      const val   = btn.dataset.val;
      const event = JSON.parse(row.dataset.event);
      try {
        await fetch('/rate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ event, rating: parseInt(val, 10) }),
        });
        row.dataset.rated = val;
        CURRENT_RATINGS[event.name] = parseInt(val, 10);
        row.classList.remove('open');
        if (onSuccess) onSuccess();
      } catch (err) {
        console.error('Rating failed', err);
      }
    });
  });
}

// ── Wire up week-tab cards ─────────────────────────────────────────────────────
document.querySelectorAll('#tab-week .swipe-row').forEach(row => {
  attachSwipe(row);
  attachRating(row);
});

// ── Training tab ──────────────────────────────────────────────────────────────
let activeFilter = 'all';

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function encodeAttrJson(ev) {
  return JSON.stringify(ev)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function typeEmoji(t) {
  return ({sports:'🏟️', music:'🎵', comedy:'🎤', food:'🍽️', other:'🎟️'})[t] || '📅';
}

function updateStats() {
  const stats = document.getElementById('train-stats');
  if (!stats) return;
  const rated   = Object.keys(CURRENT_RATINGS).length;
  const unrated = TRAINING_EVENTS.filter(e => CURRENT_RATINGS[e.name] === undefined).length;
  stats.textContent = rated + ' rated · ' + unrated + ' unrated';
}

function renderTrainList() {
  const list = document.getElementById('train-list');
  if (!list) return;

  const evs = activeFilter === 'all'
    ? TRAINING_EVENTS
    : TRAINING_EVENTS.filter(e => e.type === activeFilter);

  list.innerHTML = evs.map(ev => {
    const color    = TYPE_COLORS[ev.type] || '#94a3b8';
    const rated    = CURRENT_RATINGS[ev.name];
    const rAttr    = rated !== undefined ? ' data-rated="' + rated + '"' : '';
    const evJson   = encodeAttrJson(ev);
    const d        = new Date(ev.date + 'T12:00:00');
    const dayStr   = d.toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
    return (
      '<div class="swipe-row"' + rAttr + ' data-event="' + evJson + '">' +
        '<a class="card" href="' + escHtml(ev.url) + '" target="_blank" rel="noopener"' +
           ' style="--tc:' + color + '">' +
          '<div class="card-top">' +
            '<span class="card-emoji">' + typeEmoji(ev.type) + '</span>' +
            '<div class="card-body">' +
              '<div class="card-name">'  + escHtml(ev.name)  + '</div>' +
              '<div class="card-venue">@ ' + escHtml(ev.venue) + '</div>' +
            '</div>' +
          '</div>' +
          '<div class="card-meta">' +
            '<span class="tag">' + escHtml(dayStr)            + '</span>' +
            '<span class="tag">' + escHtml(ev.neighborhood)   + '</span>' +
            '<span class="tag">' + escHtml(ev.price_range)    + '</span>' +
          '</div>' +
        '</a>' +
        '<div class="rate-strip">' +
          '<button class="r-btn r-yes" data-val="1">✓</button>' +
          '<button class="r-btn r-mid" data-val="0">–</button>' +
          '<button class="r-btn r-no"  data-val="-1">✗</button>' +
        '</div>' +
      '</div>'
    );
  }).join('');

  list.querySelectorAll('.swipe-row').forEach(row => {
    attachSwipe(row);
    attachRating(row, updateStats);
  });

  updateStats();
}

// Build filter chips
(function () {
  const chips   = document.getElementById('filter-chips');
  if (!chips) return;
  const filters = ['all', 'sports', 'music', 'comedy', 'food', 'other'];
  const labels  = ['All', 'Sports', 'Music', 'Comedy', 'Food', 'Other'];
  filters.forEach((f, i) => {
    const btn = document.createElement('button');
    btn.className   = 'chip' + (f === 'all' ? ' active' : '');
    btn.textContent = labels[i];
    btn.addEventListener('click', () => {
      activeFilter = f;
      chips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      renderTrainList();
    });
    chips.appendChild(btn);
  });
})();

renderTrainList();
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


def _card(event, weather, show_day, idx, ratings_map=None):
    day = weather.get(event["date"])
    flag = weather_flags(day, event["indoor_outdoor"]) if day else ""
    color = TYPE_COLORS.get(event["type"], "#6b7280")
    d = date.fromisoformat(event["date"])
    day_part = f"{d.strftime('%a')} {_fmt_time(event['time'])}" if show_day else _fmt_time(event["time"])

    # Serialize event for data-event attribute (HTML-escaped JSON)
    event_json = htmllib.escape(_json.dumps(event))

    # Apply existing rating if present
    rated_attr = ""
    if ratings_map and event["name"] in ratings_map:
        rated_attr = f' data-rated="{ratings_map[event["name"]]}"'

    card_html = (
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

    rate_strip = (
        '<div class="rate-strip">'
        '<button class="r-btn r-yes" data-val="1">✓</button>'
        '<button class="r-btn r-mid" data-val="0">–</button>'
        '<button class="r-btn r-no"  data-val="-1">✗</button>'
        '</div>'
    )

    return (
        f'<div class="swipe-row"{rated_attr} data-event="{event_json}">'
        f'{card_html}{rate_strip}'
        f'</div>'
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
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    saturday = monday + timedelta(days=5)
    sunday   = monday + timedelta(days=6)

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

    try:
        from recommender import score_events
        all_events = score_events(all_events)
        all_events = [e for e in all_events if e.get("score", 0.5) >= 0.3]
        all_events = sorted(all_events, key=lambda e: (e["date"], -e.get("score", 0.5), e["time"]))
    except Exception:
        pass

    # Load ratings for dot indicators and training tab
    ratings     = _load_ratings()
    ratings_map = {r["event"]["name"]: r["rating"] for r in ratings}

    # Build training event pool (sample + live, deduplicated by name)
    sample_events = []
    if os.path.exists(SAMPLE_FILE):
        with open(SAMPLE_FILE) as f:
            sample_events = _json.load(f)
    training_pool = {e["name"]: e for e in sample_events}
    training_pool.update({e["name"]: e for e in sports + culture})
    training_events = list(training_pool.values())

    today_str    = today.isoformat()
    weekend_dates = {friday.isoformat(), saturday.isoformat(), sunday.isoformat()}
    later_dates   = set()
    d = today + timedelta(days=1)
    while d < friday:
        later_dates.add(d.isoformat())
        d += timedelta(days=1)

    today_evts   = [e for e in all_events if e["date"] == today_str][:7]
    weekend_evts = [e for e in all_events if e["date"] in weekend_dates][:7]
    later_evts   = [e for e in all_events if e["date"] in later_dates][:7]

    # Header
    highs = [w["high"] for w in weather.values() if w]
    temp_str  = f"{min(highs)}–{max(highs)}°F" if highs else ""
    week_label = (
        f"{monday.strftime('%a')} {monday.strftime('%b')} {monday.day}"
        " – "
        f"{sunday.strftime('%a')} {sunday.strftime('%b')} {sunday.day}"
    )
    meta_parts = [week_label]
    if temp_str:
        meta_parts.append(f"🌡️ {temp_str}")

    header_html = (
        f'<header>'
        f'<span class="site-title">Chi This Week</span>'
        f'<span class="header-meta">{_e("  ·  ".join(meta_parts))}</span>'
        f'</header>'
    )

    # Tab bar
    tab_bar = (
        '<nav class="tab-bar">'
        '<button class="tab-btn active" data-tab="week">This Week</button>'
        '<button class="tab-btn" data-tab="train">Train</button>'
        '</nav>'
    )

    # TODAY section
    today_wx     = weather.get(today_str)
    today_wx_html = ""
    if today_wx:
        today_wx_html = f'<div class="wx-row">{_wx_chip(today.strftime("%A"), today_wx)}</div>'
    today_sec = _section(
        f"Today · {today.strftime('%A')}",
        "today",
        today_wx_html,
        [_card(e, weather, False, i, ratings_map) for i, e in enumerate(today_evts)],
        "Nothing on the radar today.",
    )

    # THIS WEEKEND section
    wx_pills = "".join(
        _wx_chip(lbl, weather.get(d.isoformat()))
        for d, lbl in [(friday, "Fri"), (saturday, "Sat"), (sunday, "Sun")]
    )
    weekend_sec = _section(
        "This Weekend",
        "",
        f'<div class="wx-row">{wx_pills}</div>' if wx_pills else "",
        [_card(e, weather, True, i, ratings_map) for i, e in enumerate(weekend_evts)],
        "Nothing lined up yet.",
    )

    # LATER THIS WEEK section
    later_sec = _section(
        "Later This Week",
        "",
        "",
        [_card(e, weather, True, i, ratings_map) for i, e in enumerate(later_evts)],
        "Quiet stretch — save your money 💤",
    )

    # Training tab (JS renders the list)
    train_tab = (
        '<div id="tab-train" hidden>'
        '<div class="train-header">'
        '<div id="train-stats" class="train-stats"></div>'
        '<div id="filter-chips" class="filter-chips"></div>'
        '</div>'
        '<div id="train-list" class="train-list"></div>'
        '</div>'
    )

    # Embed JSON data then static JS
    data_js = "\n".join([
        "const TRAINING_EVENTS = " + _json.dumps(training_events) + ";",
        "const CURRENT_RATINGS = " + _json.dumps(ratings_map) + ";",
        "const TYPE_COLORS = "     + _json.dumps(TYPE_COLORS) + ";",
    ])
    script_html = f"<script>\n{data_js}\n{JS}\n</script>"

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
  {tab_bar}
  <div id="tab-week">
    {today_sec}
    {weekend_sec}
    {later_sec}
  </div>
  {train_tab}
  {script_html}
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

    def do_POST(self):
        if self.path != "/rate":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode()
        try:
            data   = _json.loads(body)
            event  = data["event"]
            rating = int(data["rating"])
            _save_rating(event, rating)
            resp = _json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        except Exception as ex:
            resp = _json.dumps({"ok": False, "error": str(ex)}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

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
