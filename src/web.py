"""
Static HTML generator — editorial style.

Call build_page() → returns full HTML string.
Run:  python3 build.py
"""
import sys
import os
import json
import html as _html
import hashlib
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from weather import fetch_weather, weather_flags, WMO_DESCRIPTIONS
from sports import get_sports_events
from do312 import fetch_do312_events

try:
    from ticketmaster import fetch_ticketmaster_events
except ImportError:
    fetch_ticketmaster_events = lambda a, b: []

try:
    from eventbrite import fetch_eventbrite_events
except ImportError:
    fetch_eventbrite_events = lambda a, b: []

try:
    from chicago_parks import fetch_parks_events
except ImportError:
    fetch_parks_events = lambda a, b: []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _eid(event):
    key = f"{event['name']}{event['date']}{event['venue']}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Inter:wght@400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --cream:   #faf8f4;
  --ink:     #1a1a1a;
  --dim:     #666;
  --rule:    #d6d0c4;
  --gold:    #c9a84c;
  --accent:  #1d4ed8;
  --c-sports:  #3b82f6;
  --c-music:   #a855f7;
  --c-comedy:  #f97316;
  --c-food:    #10b981;
  --c-festival:#f59e0b;
  --c-other:   #6b7280;
}

body {
  background: var(--cream);
  color: var(--ink);
  font-family: 'Inter', -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  min-height: 100vh;
}

/* ── Masthead ── */
.masthead {
  border-bottom: 3px double var(--ink);
  padding: 18px 32px 14px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.masthead-left { display: flex; flex-direction: column; gap: 2px; }
.paper-label {
  font-size: 10px; font-weight: 600; letter-spacing: .18em;
  text-transform: uppercase; color: var(--dim);
}
.paper-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 42px; font-weight: 900; line-height: 1; letter-spacing: -.5px;
}
.paper-tagline { font-size: 12px; color: var(--dim); font-style: italic; margin-top: 2px; }
.masthead-right { display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }

.weather-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: #fff; border: 1px solid var(--rule); border-radius: 20px;
  padding: 5px 13px; font-size: 12px; font-weight: 500; white-space: nowrap;
}

.mode-toggle {
  display: flex; border: 1.5px solid var(--ink); border-radius: 4px; overflow: hidden;
}
.mode-btn {
  background: transparent; border: none; cursor: pointer;
  padding: 6px 14px; font-size: 12px; font-weight: 600;
  font-family: inherit; letter-spacing: .04em; color: var(--dim);
  transition: background .15s, color .15s;
}
.mode-btn:first-child { border-right: 1.5px solid var(--ink); }
.mode-btn.active { background: var(--ink); color: #fff; }

/* ── Nav tabs ── */
.nav-tabs {
  display: flex; padding: 0 32px;
  border-bottom: 1px solid var(--rule);
}
.nav-tab {
  background: none; border: none; cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 600;
  letter-spacing: .06em; text-transform: uppercase; color: var(--dim);
  padding: 13px 20px 11px; border-bottom: 3px solid transparent;
  transition: color .15s, border-color .15s;
}
.nav-tab.active   { color: var(--accent); border-bottom-color: var(--accent); }
.nav-tab:hover:not(.active) { color: var(--ink); }

/* ── Category bar ── */
.category-bar {
  display: flex; gap: 8px; padding: 14px 32px;
  border-bottom: 1px solid var(--rule); flex-wrap: wrap; align-items: center;
}
.cat-label {
  font-size: 10px; font-weight: 600; letter-spacing: .14em;
  text-transform: uppercase; color: var(--dim); margin-right: 4px;
}
.cat-chip {
  background: none; border: 1.5px solid var(--rule); border-radius: 3px;
  cursor: pointer; font-family: inherit; font-size: 11px; font-weight: 600;
  letter-spacing: .1em; text-transform: uppercase; color: var(--dim);
  padding: 4px 12px; transition: background .14s, color .14s, border-color .14s;
}
.cat-chip.active        { background: var(--ink); border-color: var(--ink); color: #fff; }
.cat-chip:hover:not(.active) { border-color: var(--ink); color: var(--ink); }

/* ── Content ── */
.content { padding: 24px 32px 56px; max-width: 900px; }

/* ── Section ── */
.section-block { margin-bottom: 36px; }
.section-header {
  display: flex; align-items: baseline; gap: 14px; margin-bottom: 8px;
}
.section-title {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 22px; font-weight: 700; letter-spacing: -.2px;
}
.section-title.today-title { color: var(--accent); }
.section-date {
  font-size: 11px; font-weight: 500; letter-spacing: .1em;
  text-transform: uppercase; color: var(--dim);
}
.section-rule { border: none; border-top: 1.5px solid var(--ink); margin-bottom: 6px; }

/* ── Weather row ── */
.wx-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px; }
.wx-chip {
  display: inline-flex; align-items: center; gap: 4px;
  background: #fff; border: 1px solid var(--rule); border-radius: 20px;
  padding: 4px 12px; font-size: 12px; color: var(--dim); white-space: nowrap;
}
.wx-day { font-weight: 600; color: var(--ink); }

/* ── Event row ── */
.event-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 0; border-bottom: 1px solid var(--rule);
  transition: background .1s;
}
.event-row:last-child { border-bottom: none; }
.event-row:hover {
  background: rgba(0,0,0,.025);
  margin: 0 -8px; padding-left: 8px; padding-right: 8px;
}

.type-chip {
  display: inline-block; border-radius: 3px;
  padding: 2px 7px; font-size: 10px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase;
  color: #fff; white-space: nowrap; flex-shrink: 0; width: 68px; text-align: center;
}
.type-chip.sports   { background: var(--c-sports); }
.type-chip.music    { background: var(--c-music); }
.type-chip.comedy   { background: var(--c-comedy); }
.type-chip.food     { background: var(--c-food); }
.type-chip.festival { background: var(--c-festival); }
.type-chip.other    { background: var(--c-other); }

.event-main {
  flex: 1; display: flex; align-items: baseline;
  flex-wrap: wrap; font-size: 14px; line-height: 1.4; min-width: 0;
}
.event-link {
  font-weight: 600; color: var(--ink); text-decoration: none;
}
.event-link:hover { text-decoration: underline; }
.star-badge { color: var(--gold); font-size: 12px; margin-left: 4px; }
.event-meta { color: var(--dim); font-size: 13px; margin-left: 3px; }
.outdoor-flag { font-size: 11px; color: #999; margin-left: 6px; }

.event-price {
  font-size: 12px; font-weight: 600; color: var(--dim); flex-shrink: 0; white-space: nowrap;
}
.price-free {
  font-size: 11px; font-weight: 700; color: var(--c-food); flex-shrink: 0;
}

/* ── Heart button (Train tab) ── */
.heart-btn {
  background: none; border: none; cursor: pointer;
  font-size: 19px; color: #ccc; flex-shrink: 0;
  transition: color .15s, transform .1s; padding: 0 4px; line-height: 1;
}
.heart-btn.liked { color: #e53e3e; }
.heart-btn:hover { transform: scale(1.2); }

/* ── Train counter ── */
.train-counter {
  display: inline-flex; align-items: center; gap: 8px;
  background: #fff; border: 1px solid var(--rule); border-radius: 6px;
  padding: 10px 18px; margin-bottom: 24px;
  font-size: 14px; font-weight: 600; color: var(--ink);
}
.count-num {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 24px; font-weight: 700; color: var(--accent); line-height: 1;
}

/* ── States ── */
.hidden { display: none !important; }
.empty-state {
  text-align: center; padding: 48px 0;
  color: var(--dim); font-style: italic; font-size: 15px;
}

/* ── Footer ── */
.footer-rule {
  border: none; border-top: 3px double var(--ink);
  margin: 0 32px;
}
.footer-text {
  text-align: center; padding: 12px 32px 28px;
  font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: #aaa;
}

@media (max-width: 600px) {
  .masthead { padding: 14px 16px 12px; }
  .paper-title { font-size: 30px; }
  .nav-tabs, .category-bar, .content, .footer-rule { padding-left: 16px; padding-right: 16px; }
  .footer-text { padding-left: 16px; padding-right: 16px; }
  .event-meta { font-size: 12px; }
}
"""

# ── JS ────────────────────────────────────────────────────────────────────────

JS = r"""
// ── State ──────────────────────────────────────────────────────────────────
let currentTab  = 'myweek';
let currentMode = 'picks';
let currentCat  = 'all';
let likedIds    = new Set(JSON.parse(localStorage.getItem('chiLiked') || '[]'));

// ── Helpers ────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtTime(t) {
  if (!t) return '';
  const [h, m] = t.split(':').map(Number);
  const ampm = h < 12 ? 'am' : 'pm';
  const h12  = h % 12 || 12;
  return m ? `${h12}:${String(m).padStart(2,'0')}${ampm}` : `${h12}${ampm}`;
}

function fmtDate(iso) {
  return new Date(iso + 'T12:00:00')
    .toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
}

// ── Render ─────────────────────────────────────────────────────────────────
function render() {
  const isTrain = currentTab === 'train';
  document.getElementById('train-counter').classList.toggle('hidden', !isTrain);
  document.getElementById('like-count').textContent = likedIds.size;

  let evts = ALL_EVENTS;
  if (currentCat !== 'all') evts = evts.filter(e => e.type === currentCat);

  if (isTrain) {
    renderTrain(evts);
  } else {
    if (currentMode === 'picks') evts = evts.filter(e => (e.score || 0) >= SCORE_THRESHOLD);
    renderMyWeek(evts);
  }
}

function renderMyWeek(evts) {
  const SECTIONS = [
    { key: 'today',   label: 'Today',          dates: TODAY_DATE ? [TODAY_DATE] : [] },
    { key: 'weekend', label: 'This Weekend',    dates: WEEKEND_DATES },
    { key: 'later',   label: 'Later This Week', dates: LATER_DATES   },
  ];

  let html = '';
  let total = 0;

  SECTIONS.forEach(sec => {
    const secEvts = evts.filter(e => sec.dates.includes(e.date)).slice(0, 7);
    if (!secEvts.length) return;
    total += secEvts.length;

    const isToday   = sec.key === 'today';
    const titleCls  = isToday ? 'section-title today-title' : 'section-title';
    const subline   = isToday ? fmtDate(TODAY_DATE) : '';

    // Weather chips for this section
    let wxHtml = '';
    sec.dates.forEach(d => {
      const wx = WEATHER_DATA[d];
      if (!wx) return;
      const dayName = new Date(d + 'T12:00:00')
        .toLocaleDateString('en-US', {weekday:'short'});
      let txt = `${esc(wx.high)}\u00B0F`;
      if (wx.desc)         txt += ` \u00B7 ${esc(wx.desc)}`;
      if (wx.precip_prob)  txt += ` \u00B7 ${wx.precip_prob}% rain`;
      wxHtml += `<span class="wx-chip"><span class="wx-day">${dayName}</span> ${txt}${wx.flag ? ' ' + wx.flag : ''}</span>`;
    });

    html += `
<div class="section-block">
  <div class="section-header">
    <span class="${titleCls}">${sec.label}</span>
    ${subline ? `<span class="section-date">${subline}</span>` : ''}
  </div>
  <hr class="section-rule">
  ${wxHtml ? `<div class="wx-row">${wxHtml}</div>` : ''}
  ${secEvts.map(e => buildRow(e, false)).join('')}
</div>`;
  });

  document.getElementById('empty-state').classList.toggle('hidden', total > 0);
  document.getElementById('event-list').innerHTML = html;
}

function renderTrain(evts) {
  const sorted = [...evts].sort((a, b) =>
    (a.date + a.time).localeCompare(b.date + b.time));
  document.getElementById('empty-state').classList.toggle('hidden', sorted.length > 0);
  document.getElementById('event-list').innerHTML = sorted.map(e => buildRow(e, true)).join('');
}

function buildRow(e, showHeart) {
  const isLiked = likedIds.has(e.id);

  const priceHtml = (e.price_range === 'free')
    ? `<span class="price-free">FREE</span>`
    : `<span class="event-price">${esc(e.price_range || '')}</span>`;

  const starBadge   = (e.score || 0) >= SCORE_THRESHOLD
    ? `<span class="star-badge" title="Recommended">&#9733;</span>` : '';

  const outdoorFlag = (e.indoor_outdoor === 'outdoor' || e.indoor_outdoor === 'mixed')
    ? `<span class="outdoor-flag" title="Outdoor \u2014 check weather">\uD83C\uDF24 outdoors</span>` : '';

  const meta = [e.venue, e.neighborhood, fmtTime(e.time)].filter(Boolean).join(' \u00B7 ');

  const heartBtn = showHeart
    ? `<button class="heart-btn${isLiked ? ' liked' : ''}" data-id="${esc(e.id)}" onclick="toggleLike(event,this)">${isLiked ? '\u2665' : '\u2661'}</button>`
    : '';

  return `<div class="event-row" data-id="${esc(e.id)}">
  <span class="type-chip ${esc(e.type)}">${esc(e.type)}</span>
  <div class="event-main">
    <a class="event-link" href="${esc(e.url || '#')}" target="_blank" rel="noopener">${esc(e.name)}${starBadge}</a>
    <span class="event-meta">&nbsp;\u00B7&nbsp;${esc(meta)}</span>
    ${outdoorFlag}
  </div>
  ${priceHtml}
  ${heartBtn}
</div>`;
}

// ── Heart toggle ───────────────────────────────────────────────────────────
async function toggleLike(evt, btn) {
  evt.preventDefault();
  evt.stopPropagation();

  const id    = btn.dataset.id;
  const event = ALL_EVENTS.find(e => e.id === id);
  if (!event) return;

  const wasLiked = likedIds.has(id);
  const action   = wasLiked ? 'unlike' : 'like';

  // Optimistic update
  wasLiked ? likedIds.delete(id) : likedIds.add(id);
  btn.classList.toggle('liked', !wasLiked);
  btn.textContent = !wasLiked ? '\u2665' : '\u2661';
  document.getElementById('like-count').textContent = likedIds.size;
  localStorage.setItem('chiLiked', JSON.stringify([...likedIds]));

  try {
    const resp = await fetch('/api/rate', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({
        event_id:   id,
        event_name: event.name,
        event_date: event.date,
        event_type: event.type,
        action,
      }),
    });
    if (!resp.ok) throw new Error('failed');
  } catch(e) {
    // Rollback
    wasLiked ? likedIds.add(id) : likedIds.delete(id);
    btn.classList.toggle('liked', wasLiked);
    btn.textContent = wasLiked ? '\u2665' : '\u2661';
    document.getElementById('like-count').textContent = likedIds.size;
    localStorage.setItem('chiLiked', JSON.stringify([...likedIds]));
    console.error('Like failed:', e);
  }
}

// ── Tab / filter controls ─────────────────────────────────────────────────
function setTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  render();
}
function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + mode).classList.add('active');
  render();
}
function setCat(el, cat) {
  currentCat = cat;
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  render();
}

// ── Boot ──────────────────────────────────────────────────────────────────
render();
"""


# ── Page builder ──────────────────────────────────────────────────────────────

def build_page():
    today    = date.today()
    monday   = today - timedelta(days=today.weekday())
    friday   = monday + timedelta(days=4)
    saturday = monday + timedelta(days=5)
    sunday   = monday + timedelta(days=6)

    # ── Weather ──────────────────────────────────────────────────────────────
    try:
        weather = fetch_weather()
    except Exception:
        weather = {}

    # ── Events from all sources ───────────────────────────────────────────────
    def _safe(fn, *args):
        try:
            return fn(*args)
        except Exception:
            return []

    sports = _safe(get_sports_events, monday, sunday)
    culture = _safe(fetch_do312_events, monday, sunday)
    tm     = _safe(fetch_ticketmaster_events, monday, sunday)
    eb     = _safe(fetch_eventbrite_events, monday, sunday)
    parks  = _safe(fetch_parks_events, monday, sunday)

    # Merge + dedup by name+date
    seen, unique = set(), []
    for e in sports + culture + tm + eb + parks:
        key = f"{e['name'].lower()}|{e['date']}"
        if key not in seen:
            seen.add(key)
            unique.append(e)

    all_events = sorted(unique, key=lambda e: (e["date"], e["time"]))

    # ── IDs ───────────────────────────────────────────────────────────────────
    for e in all_events:
        e["id"] = _eid(e)

    # ── Score + threshold ─────────────────────────────────────────────────────
    threshold = 0.35
    try:
        from recommender import score_events
        all_events, threshold = score_events(all_events)
    except Exception:
        from events import event_emoji   # noqa: avoids unused import warning
        pass

    # ── Time buckets ──────────────────────────────────────────────────────────
    today_str     = today.isoformat()
    weekend_dates = [friday.isoformat(), saturday.isoformat(), sunday.isoformat()]
    later_dates   = []
    d = today + timedelta(days=1)
    while d < friday:
        later_dates.append(d.isoformat())
        d += timedelta(days=1)

    # ── Weather for JS ────────────────────────────────────────────────────────
    wx_data = {}
    for ds, day in weather.items():
        if day:
            wx_data[ds] = {
                "high":        day.get("high", 0),
                "desc":        WMO_DESCRIPTIONS.get(day.get("weather_code", 0), ""),
                "precip_prob": day.get("precip_prob", 0),
                "flag":        weather_flags(day, "outdoor"),
            }

    # ── Masthead strings ──────────────────────────────────────────────────────
    week_label = (
        f"{today.strftime('%b')} {today.day}"
        " \u2013 "
        f"{sunday.strftime('%b')} {sunday.day}, {sunday.year}"
    )

    today_wx  = weather.get(today_str, {}) or {}
    wx_parts  = []
    if today_wx.get("high"):
        wx_parts.append(f"{today_wx['high']}\u00B0F")
    wx_desc = WMO_DESCRIPTIONS.get(today_wx.get("weather_code", 0), "")
    if wx_desc:
        wx_parts.append(wx_desc)
    if today_wx.get("precip_prob"):
        wx_parts.append(f"{today_wx['precip_prob']}% rain")
    wx_flag = weather_flags(today_wx, "outdoor") if today_wx else ""

    wx_chip_html = ""
    if wx_parts:
        wx_first = _html.escape(wx_parts[0])
        wx_rest  = _html.escape(" \u00B7 ".join(wx_parts[1:]))
        if len(wx_parts) > 1:
            wx_chip_html = (
                f'<div class="weather-chip">'
                f'{wx_flag} <strong>{wx_first}</strong>'
                f'&nbsp;&nbsp;{wx_rest}'
                f'</div>'
            )
        else:
            wx_chip_html = f'<div class="weather-chip">{wx_flag} <strong>{wx_first}</strong></div>'

    # ── Embedded JS data ──────────────────────────────────────────────────────
    data_js = "\n".join([
        f"const ALL_EVENTS     = {json.dumps(all_events)};",
        f"const SCORE_THRESHOLD = {threshold};",
        f"const TODAY_DATE     = {json.dumps(today_str)};",
        f"const WEEKEND_DATES  = {json.dumps(weekend_dates)};",
        f"const LATER_DATES    = {json.dumps(later_dates)};",
        f"const WEATHER_DATA   = {json.dumps(wx_data)};",
    ])

    # ── HTML ──────────────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chi This Week</title>
  <style>{CSS}</style>
</head>
<body>

<header class="masthead">
  <div class="masthead-left">
    <span class="paper-label">Chicago &nbsp;\u00B7&nbsp; {_html.escape(week_label)}</span>
    <div class="paper-title">Chi This Week</div>
    <div class="paper-tagline">Your personal guide to what&#39;s worth doing in the city</div>
  </div>
  <div class="masthead-right">
    {wx_chip_html}
    <div class="mode-toggle">
      <button class="mode-btn active" id="btn-picks" onclick="setMode('picks')">My Picks &#10024;</button>
      <button class="mode-btn"        id="btn-all"   onclick="setMode('all')">Everything</button>
    </div>
  </div>
</header>

<nav class="nav-tabs">
  <button class="nav-tab active" id="tab-myweek" onclick="setTab('myweek')">My Week</button>
  <button class="nav-tab"        id="tab-train"  onclick="setTab('train')">Train</button>
</nav>

<div class="category-bar">
  <span class="cat-label">Section:</span>
  <button class="cat-chip active" onclick="setCat(this,'all')">All</button>
  <button class="cat-chip"        onclick="setCat(this,'sports')">Sports</button>
  <button class="cat-chip"        onclick="setCat(this,'music')">Music</button>
  <button class="cat-chip"        onclick="setCat(this,'festival')">Festivals</button>
  <button class="cat-chip"        onclick="setCat(this,'comedy')">Comedy</button>
  <button class="cat-chip"        onclick="setCat(this,'food')">Food</button>
</div>

<main class="content">
  <div class="train-counter hidden" id="train-counter">
    <span class="count-num" id="like-count">0</span>
    <span>events liked so far</span>
  </div>
  <div id="event-list"></div>
  <div class="empty-state hidden" id="empty-state">No events match your current filters.</div>
</main>

<hr class="footer-rule">
<div class="footer-text">Chi This Week &nbsp;\u00B7&nbsp; Personal Edition</div>

<script>
{data_js}
{JS}
</script>
</body>
</html>"""
