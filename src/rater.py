"""
Event rater — run with:  python src/rater.py

Serves on port 8081. Rate events one at a time with keyboard shortcuts:
  y → 👍 Yes    m → 🤷 Maybe    n → 👎 Nope
"""
import sys
import os
import json
import html as htmllib
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(__file__))

PORT     = 8081
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SAMPLE_FILE  = os.path.join(DATA_DIR, "sample_events.json")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")

TYPE_EMOJIS = {
    "music":   "🎵",
    "comedy":  "🎤",
    "sports":  "🏟️",
    "food":    "🍽️",
    "other":   "🎟️",
}

TYPE_COLORS = {
    "sports": "#5b9cf6",
    "music":  "#c084fc",
    "comedy": "#fb923c",
    "food":   "#34d399",
    "other":  "#94a3b8",
}

# ── CSS (same vars as web.py) ─────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Barlow+Condensed:wght@600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:    #09090d;
  --s1:    #111118;
  --s2:    #16161f;
  --b1:    #1c1c28;
  --b2:    #252535;
  --text:  #eaecf0;
  --dim:   #606278;
  --amber: #e8a73a;
  --r:     10px;
}

body {
  background: var(--bg);
  background-image: radial-gradient(ellipse 90% 45% at 50% 0%, rgba(22, 28, 55, 0.7) 0%, transparent 65%);
  color: var(--text);
  font-family: 'DM Sans', -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  max-width: 560px;
  margin: 0 auto;
  padding: 3rem 1.5rem 5rem;
  min-height: 100vh;
}

header {
  margin-bottom: 2.5rem;
}

.site-title {
  font-family: 'Instrument Serif', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: clamp(2rem, 8vw, 2.8rem);
  letter-spacing: -0.02em;
  line-height: 1;
  display: block;
  margin-bottom: 0.75rem;
}

.progress-wrap {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-top: 0.6rem;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--b2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--amber);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-label {
  font-size: 0.72rem;
  color: var(--dim);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

/* ── Event card ── */
.card {
  background: var(--s1);
  border: 1px solid var(--b1);
  border-left: 3px solid var(--tc, var(--b2));
  border-radius: var(--r);
  padding: 1.4rem 1.5rem;
  margin-bottom: 1.8rem;
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  margin-bottom: 0.9rem;
}

.card-emoji { font-size: 1.3rem; line-height: 1.4; flex-shrink: 0; }

.card-name {
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--text);
  line-height: 1.3;
}

.card-venue {
  font-size: 0.8rem;
  color: var(--dim);
  margin-top: 0.15rem;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
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

/* ── Rating buttons ── */
.actions {
  display: flex;
  gap: 0.7rem;
  margin-top: 0.5rem;
}

.btn {
  flex: 1;
  padding: 0.75rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--b2);
  background: var(--s2);
  color: var(--dim);
  font-family: 'DM Sans', sans-serif;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.1s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.btn:hover   { background: var(--b1); border-color: var(--b2); color: var(--text); }
.btn:active  { transform: scale(0.96); }

.btn-yes:hover  { border-color: #4ade80; color: #4ade80; }
.btn-maybe:hover{ border-color: var(--amber); color: var(--amber); }
.btn-no:hover   { border-color: #f87171; color: #f87171; }

.btn .btn-emoji { font-size: 1.3rem; }
.btn .btn-key   {
  font-size: 0.6rem;
  color: var(--dim);
  background: var(--b1);
  border-radius: 3px;
  padding: 0.05rem 0.3rem;
  font-family: monospace;
}

/* ── Hint ── */
.hint {
  text-align: center;
  font-size: 0.72rem;
  color: var(--dim);
  margin-top: 1rem;
}

/* ── Done screen ── */
.done {
  text-align: center;
  padding: 3rem 0;
}

.done h2 {
  font-family: 'Instrument Serif', Georgia, serif;
  font-style: italic;
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.done p { color: var(--dim); font-size: 0.9rem; line-height: 1.6; }
.done code {
  display: block;
  margin-top: 1.2rem;
  background: var(--s1);
  border: 1px solid var(--b2);
  border-radius: 6px;
  padding: 0.8rem 1rem;
  font-size: 0.75rem;
  color: var(--amber);
  text-align: left;
  white-space: pre-wrap;
  word-break: break-all;
}
"""

# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_samples():
    with open(SAMPLE_FILE) as f:
        return json.load(f)


def _load_ratings():
    if not os.path.exists(RATINGS_FILE):
        return []
    with open(RATINGS_FILE) as f:
        return json.load(f)


def _save_rating(event: dict, rating: int):
    ratings = _load_ratings()
    ratings.append({
        "event":    event,
        "rating":   rating,
        "rated_at": datetime.now(timezone.utc).isoformat(),
    })
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RATINGS_FILE, "w") as f:
        json.dump(ratings, f, indent=2)


def _next_event():
    """Return (event_or_None, rated_count, total_count)."""
    samples     = _load_samples()
    ratings     = _load_ratings()
    rated_names = {r["event"]["name"] for r in ratings}
    for ev in samples:
        if ev["name"] not in rated_names:
            return ev, len(rated_names), len(samples)
    return None, len(samples), len(samples)


# ── HTML rendering ────────────────────────────────────────────────────────────

def _e(s):
    return htmllib.escape(str(s))


def _fmt_time(t: str) -> str:
    h, m = map(int, t.split(":"))
    s    = "am" if h < 12 else "pm"
    h12  = h % 12 or 12
    return f"{h12}:{m:02d}{s}" if m else f"{h12}{s}"


def _render_done(rated: int, total: int) -> str:
    verify_cmd = (
        "python -c \""
        "import sys; sys.path.insert(0,'src'); "
        "from recommender import score_events; import json; "
        "events = json.load(open('data/sample_events.json')); "
        "scored = score_events(events); "
        "scored.sort(key=lambda x: -x['score']); "
        "[print(e['score'], e['name']) for e in scored[:10]]\""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Done — Chi This Week Rater</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <span class="site-title">All done.</span>
  </header>
  <div class="done">
    <h2>✓ {rated} events rated</h2>
    <p>
      The recommender will now use your ratings to rank events.<br>
      Verify top scores look right:
    </p>
    <code>{_e(verify_cmd)}</code>
  </div>
</body>
</html>"""


def _render_card(event: dict, rated: int, total: int) -> str:
    color    = TYPE_COLORS.get(event["type"], "#94a3b8")
    emoji    = TYPE_EMOJIS.get(event["type"], "📅")
    pct      = int(rated / total * 100) if total else 0

    try:
        d = datetime.fromisoformat(event["date"])
        date_str = d.strftime("%a %b %-d")
    except Exception:
        date_str = event.get("date", "")

    time_str = _fmt_time(event.get("time", "20:00"))

    tags = "".join([
        f'<span class="tag">{_e(date_str)} {_e(time_str)}</span>',
        f'<span class="tag">{_e(event["neighborhood"])}</span>',
        f'<span class="tag">{_e(event["price_range"])}</span>',
        f'<span class="tag">{_e(event["indoor_outdoor"])}</span>',
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rate Events — Chi This Week</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <span class="site-title">Rate Events</span>
    <div class="progress-wrap">
      <div class="progress-bar">
        <div class="progress-fill" style="width:{pct}%"></div>
      </div>
      <span class="progress-label">{rated} / {total}</span>
    </div>
  </header>

  <div class="card" style="--tc:{_e(color)}">
    <div class="card-top">
      <span class="card-emoji">{emoji}</span>
      <div>
        <div class="card-name">{_e(event["name"])}</div>
        <div class="card-venue">@ {_e(event["venue"])}</div>
      </div>
    </div>
    <div class="tags">{tags}</div>
  </div>

  <form id="rate-form" method="POST" action="/rate">
    <input type="hidden" name="event_name" value="{_e(event['name'])}">
    <input type="hidden" id="rating-val" name="rating" value="">
    <div class="actions">
      <button type="button" class="btn btn-yes"    onclick="submitRating(1)">
        <span class="btn-emoji">👍</span>
        <span>Yes</span>
        <span class="btn-key">y</span>
      </button>
      <button type="button" class="btn btn-maybe"  onclick="submitRating(0)">
        <span class="btn-emoji">🤷</span>
        <span>Maybe</span>
        <span class="btn-key">m</span>
      </button>
      <button type="button" class="btn btn-no"     onclick="submitRating(-1)">
        <span class="btn-emoji">👎</span>
        <span>Nope</span>
        <span class="btn-key">n</span>
      </button>
    </div>
  </form>

  <p class="hint">keyboard: y / m / n</p>

  <script>
    function submitRating(val) {{
      document.getElementById('rating-val').value = val;
      document.getElementById('rate-form').submit();
    }}
    document.addEventListener('keydown', function(e) {{
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'y' || e.key === 'Y') submitRating(1);
      if (e.key === 'm' || e.key === 'M') submitRating(0);
      if (e.key === 'n' || e.key === 'N') submitRating(-1);
    }});
  </script>
</body>
</html>"""


def _build_page() -> str:
    event, rated, total = _next_event()
    if event is None:
        return _render_done(rated, total)
    return _render_card(event, rated, total)


# ── HTTP server ───────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        body = _build_page().encode("utf-8")
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
        params = parse_qs(body)

        event_name = params.get("event_name", [""])[0]
        try:
            rating = int(params.get("rating", [0])[0])
        except ValueError:
            rating = 0

        # Look up full event dict so we store it whole
        for ev in _load_samples():
            if ev["name"] == event_name:
                _save_rating(ev, rating)
                break

        # PRG — redirect back to GET /
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass   # suppress access log noise


def main():
    server = HTTPServer(("", PORT), _Handler)
    url    = f"http://localhost:{PORT}"
    print(f"Chi This Week Rater → {url}")
    print("Keyboard: y=👍  m=🤷  n=👎    Ctrl+C to stop")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        ratings = _load_ratings()
        print(f"Saved {len(ratings)} rating(s) to data/ratings.json")


if __name__ == "__main__":
    main()
