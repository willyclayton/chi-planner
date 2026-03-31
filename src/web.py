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


def _load_env():
    """Load .env file into os.environ using stdlib only."""
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


_load_env()

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

try:
    from choosechicago import fetch_choosechicago_events
except ImportError:
    fetch_choosechicago_events = lambda a, b: []

try:
    from dcase import fetch_dcase_events
except ImportError:
    fetch_dcase_events = lambda a, b: []


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

/* ── 3-way rating buttons (Train tab) ── */
.rate-btns {
  display: flex; gap: 4px; flex-shrink: 0;
}
.rate-btn {
  background: none; border: 1.5px solid var(--rule); border-radius: 4px;
  cursor: pointer; font-size: 16px; padding: 4px 8px; line-height: 1;
  transition: background .15s, border-color .15s, transform .1s;
  opacity: 0.5;
}
.rate-btn:hover { transform: scale(1.15); opacity: 1; }
.rate-btn.active { opacity: 1; }
.rate-btn.active[data-rating="1"] { background: #dcfce7; border-color: #22c55e; }
.rate-btn.active[data-rating="0"] { background: #fef9c3; border-color: #eab308; }
.rate-btn.active[data-rating="-1"] { background: #fecaca; border-color: #ef4444; }
.event-row.rated { opacity: 0.45; }
.event-row.rated:hover { opacity: 0.7; }

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
// ratings: { event_id: 1|0|-1 }
let ratings     = JSON.parse(localStorage.getItem('chiRatings') || '{}');
// Migrate old likes into ratings
likedIds.forEach(id => { if (!(id in ratings)) ratings[id] = 1; });
localStorage.setItem('chiRatings', JSON.stringify(ratings));

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

function fmtShortDate(iso) {
  const d = new Date(iso + 'T12:00:00');
  const day = d.toLocaleDateString('en-US', {weekday:'short'});
  const m = d.getMonth() + 1;
  const dt = d.getDate();
  return `${day} ${m}/${dt}`;
}

// ── Render ─────────────────────────────────────────────────────────────────
function render() {
  const isTrain = currentTab === 'train';
  document.getElementById('train-counter').classList.toggle('hidden', !isTrain);
  document.getElementById('like-count').textContent = Object.keys(ratings).length;

  if (isTrain) {
    renderTrain(ALL_EVENTS);
    return;
  }

  // My Week tab
  let evts = ALL_EVENTS;
  if (currentMode === 'picks') {
    if (currentCat !== 'all') evts = evts.filter(e => e.type === currentCat);
    evts = evts.filter(e => (e.score || 0) >= SCORE_THRESHOLD);
  }
  renderMyWeek(evts);
}

function renderMyWeek(evts) {
  const byDate = {};
  evts.forEach(e => {
    if (!byDate[e.date]) byDate[e.date] = [];
    byDate[e.date].push(e);
  });

  const dates = Object.keys(byDate).sort();
  let html = '';
  let total = 0;

  dates.forEach(d => {
    const dayEvts = byDate[d].slice(0, 7);
    total += dayEvts.length;

    const dt      = new Date(d + 'T12:00:00');
    const dayName = dt.toLocaleDateString('en-US', {weekday:'long'});
    const m       = dt.getMonth() + 1;
    const day     = dt.getDate();
    const isToday = d === TODAY_DATE;
    const titleCls = isToday ? 'section-title today-title' : 'section-title';

    const wx = WEATHER_DATA[d];
    let wxHtml = '';
    if (wx) {
      let txt = `${esc(wx.high)}\u00B0F`;
      if (wx.desc)        txt += ` \u00B7 ${esc(wx.desc)}`;
      if (wx.precip_prob) txt += ` \u00B7 ${wx.precip_prob}% rain`;
      wxHtml = `<div class="wx-row"><span class="wx-chip">${txt}${wx.flag ? ' ' + wx.flag : ''}</span></div>`;
    }

    html += `
<div class="section-block">
  <div class="section-header">
    <span class="${titleCls}">${dayName}</span>
    <span class="section-date">${m}/${day}</span>
  </div>
  <hr class="section-rule">
  ${wxHtml}
  ${dayEvts.map(e => buildRow(e, false)).join('')}
</div>`;
  });

  document.getElementById('empty-state').classList.toggle('hidden', total > 0);
  document.getElementById('event-list').innerHTML = html;
}

function renderTrain(evts) {
  // Unrated first, then rated (dimmed); both sorted chronologically
  const unrated = evts.filter(e => !(e.id in ratings))
    .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
  const rated = evts.filter(e => e.id in ratings)
    .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));

  const ratedCount = Object.keys(ratings).length;
  document.getElementById('like-count').textContent = ratedCount;
  document.getElementById('empty-state').classList.toggle('hidden', evts.length > 0);
  document.getElementById('event-list').innerHTML =
    unrated.map(e => buildRow(e, true)).join('') +
    (rated.length ? '<hr style="margin:24px 0;border-color:var(--rule)">' : '') +
    rated.map(e => buildRow(e, true)).join('');
}

function buildRow(e, showRating) {
  const curRating = ratings[e.id];
  const isRated = curRating !== undefined;

  const priceHtml = (e.price_range === 'free')
    ? `<span class="price-free">FREE</span>`
    : `<span class="event-price">${esc(e.price_range || '')}</span>`;

  const starBadge   = (e.score || 0) >= SCORE_THRESHOLD
    ? `<span class="star-badge" title="Recommended">&#9733;</span>` : '';

  const outdoorFlag = (e.indoor_outdoor === 'outdoor' || e.indoor_outdoor === 'mixed')
    ? `<span class="outdoor-flag" title="Outdoor \u2014 check weather">\uD83C\uDF24 outdoors</span>` : '';

  const when = [fmtShortDate(e.date), fmtTime(e.time)].filter(Boolean).join(' @ ');
  const meta = [e.venue, e.neighborhood, when].filter(Boolean).join(' \u00B7 ');

  let ratingHtml = '';
  if (showRating) {
    const a = (v) => curRating === v ? 'active' : '';
    ratingHtml = `<div class="rate-btns">
      <button class="rate-btn ${a(1)}" data-id="${esc(e.id)}" data-rating="1" onclick="rateEvent(event,this)" title="Like">\uD83D\uDC4D</button>
      <button class="rate-btn ${a(0)}" data-id="${esc(e.id)}" data-rating="0" onclick="rateEvent(event,this)" title="Meh">\uD83E\uDD37</button>
      <button class="rate-btn ${a(-1)}" data-id="${esc(e.id)}" data-rating="-1" onclick="rateEvent(event,this)" title="Nope">\uD83D\uDC4E</button>
    </div>`;
  }

  const rowClass = (showRating && isRated) ? 'event-row rated' : 'event-row';

  return `<div class="${rowClass}" data-id="${esc(e.id)}">
  <span class="type-chip ${esc(e.type)}">${esc(e.type)}</span>
  <div class="event-main">
    <a class="event-link" href="${esc(e.url || '#')}" target="_blank" rel="noopener">${esc(e.name)}${starBadge}</a>
    <span class="event-meta">&nbsp;\u00B7&nbsp;${esc(meta)}</span>
    ${outdoorFlag}
  </div>
  ${priceHtml}
  ${ratingHtml}
</div>`;
}

// ── Rate event (3-way) ────────────────────────────────────────────────────
async function rateEvent(evt, btn) {
  evt.preventDefault();
  evt.stopPropagation();

  const id        = btn.dataset.id;
  const newRating = parseInt(btn.dataset.rating, 10);
  const event     = ALL_EVENTS.find(e => e.id === id);
  if (!event) return;

  const oldRating = ratings[id];
  const isSame    = oldRating === newRating;

  // Toggle off if clicking same rating again
  if (isSame) {
    delete ratings[id];
  } else {
    ratings[id] = newRating;
  }

  // Also keep likedIds in sync for backward compat
  if (ratings[id] === 1) likedIds.add(id);
  else likedIds.delete(id);

  localStorage.setItem('chiRatings', JSON.stringify(ratings));
  localStorage.setItem('chiLiked', JSON.stringify([...likedIds]));
  render();

  try {
    const resp = await fetch('/api/rate', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({
        event_id: id,
        event:    event,
        rating:   isSame ? null : newRating,
        // Backward compat
        event_name: event.name,
        event_date: event.date,
        event_type: event.type,
        action:     isSame ? 'unlike' : 'like',
      }),
    });
    if (!resp.ok) throw new Error('failed');
  } catch(e) {
    // Rollback
    if (oldRating !== undefined) ratings[id] = oldRating;
    else delete ratings[id];
    if (ratings[id] === 1) likedIds.add(id); else likedIds.delete(id);
    localStorage.setItem('chiRatings', JSON.stringify(ratings));
    localStorage.setItem('chiLiked', JSON.stringify([...likedIds]));
    render();
    console.error('Rating failed:', e);
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
    end_date = today + timedelta(days=7)

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

    sports       = _safe(get_sports_events, today, end_date)
    culture      = _safe(fetch_do312_events, today, end_date)
    tm           = _safe(fetch_ticketmaster_events, today, end_date)
    eb           = _safe(fetch_eventbrite_events, today, end_date)
    parks        = _safe(fetch_parks_events, today, end_date)
    choosechicago = _safe(fetch_choosechicago_events, today, end_date)
    dcase        = _safe(fetch_dcase_events, today, end_date)

    # Merge + dedup by name+date; drop anything before today
    today_str = today.isoformat()
    seen, unique = set(), []
    for e in sports + culture + tm + eb + parks + choosechicago + dcase:
        if e.get("date", "") < today_str:
            continue
        key = f"{e['name'].lower()}|{e['date']}"
        if key not in seen:
            seen.add(key)
            unique.append(e)

    all_events = sorted(unique, key=lambda e: (e["date"], e["time"]))

    # ── IDs ───────────────────────────────────────────────────────────────────
    for e in all_events:
        e["id"] = _eid(e)

    # ── Persist events + tags to DB ───────────────────────────────────────────
    try:
        from db import upsert_events
        upsert_events(all_events)
    except Exception:
        pass

    # ── Score + threshold ─────────────────────────────────────────────────────
    threshold = 0.35
    try:
        from recommender import score_events
        all_events, threshold = score_events(all_events)
    except Exception:
        pass

    # ── Store scores back to DB ───────────────────────────────────────────────
    try:
        from db import upsert_events as _update_scores
        _update_scores(all_events)
    except Exception:
        pass

    # ── Time buckets (today + next 7 days) ────────────────────────────────────
    weekend_dates = []
    later_dates   = []
    d = today + timedelta(days=1)
    while d <= end_date:
        if d.weekday() in (4, 5, 6):  # Fri/Sat/Sun
            weekend_dates.append(d.isoformat())
        else:
            later_dates.append(d.isoformat())
        d += timedelta(days=1)

    # ── Weather for JS ────────────────────────────────────────────────────────
    wx_data = {}
    for ds, day in weather.items():
        if day:
            wx_data[ds] = {
                "high":        day.get("high", 0),
                "low":         day.get("low", 0),
                "desc":        WMO_DESCRIPTIONS.get(day.get("weather_code", 0), ""),
                "precip_prob": day.get("precip_prob", 0),
                "flag":        weather_flags(day, "outdoor"),
            }

    # ── Masthead strings ──────────────────────────────────────────────────────
    week_label = (
        f"{today.strftime('%b')} {today.day}"
        " \u2013 "
        f"{end_date.strftime('%b')} {end_date.day}, {end_date.year}"
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
    <span>events rated so far</span>
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
