"""
POST /api/rate

New format: { event_id, event: {...full event...}, rating: 1|0|-1 }
Legacy format: { event_id, event_name, event_date, event_type, action: "like" | "unlike" }

Upserts event + tags + rating to Supabase.
Returns: { success: true }
"""
from http.server import BaseHTTPRequestHandler
import hashlib
import json
import os
import urllib.request
import urllib.error
import urllib.parse


def _supabase(method, path, body=None):
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key  = os.environ.get("SUPABASE_ANON_KEY", "")
    if not base or not key:
        return 503, "Supabase not configured"

    headers = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates,return=minimal",
    }
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _event_id(event):
    key = f"{event.get('name', '')}{event.get('date', '')}{event.get('venue', '')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# Inline tag extraction (avoids importing src/db.py in Vercel serverless)
_TEAM_PATTERNS = {
    "cubs": "cubs", "blackhawks": "blackhawks", "bulls": "bulls",
    "bears": "bears", "white sox": "white sox", "fire": "fire",
}
_EDM_KW = {"edm", "techno", "rave", "house music", "electronic dance", "foam party"}
_COMEDY_KW = {"improv", "standup", "stand-up", "comedy", "open mic"}


def _extract_tags(event):
    tags = []
    name = event.get("name", "").lower()
    venue = event.get("venue", "").lower()
    neighborhood = event.get("neighborhood", "").lower()
    etype = event.get("type", "").lower()
    price = event.get("price_range", "").lower()

    if etype:
        tags.append(("type", etype))
    for pattern, team in _TEAM_PATTERNS.items():
        if pattern in name:
            tags.append(("team", team))
    if etype in ("music", "comedy"):
        artist = name
        for sep in [" at ", " @ "]:
            if sep in artist:
                artist = artist[:artist.index(sep)]
        artist = artist.strip()
        if artist:
            tags.append(("artist", artist))
    if venue:
        tags.append(("venue", venue))
    if neighborhood:
        tags.append(("neighborhood", neighborhood))
    if price:
        tags.append(("price", price))
    if any(kw in name for kw in _EDM_KW) or " dj " in f" {name} ":
        tags.append(("keyword", "edm"))
    if any(kw in name for kw in _COMEDY_KW):
        tags.append(("keyword", "comedy"))
    if any(kw in name for kw in ("pop-up", "popup", "pop up")):
        tags.append(("keyword", "popup"))
    if "festival" in name or etype == "festival":
        tags.append(("keyword", "festival"))

    io = event.get("indoor_outdoor", "").lower()
    if io:
        tags.append(("keyword", io))

    from datetime import datetime
    try:
        dt = datetime.fromisoformat(event["date"])
        tags.append(("day_of_week", dt.strftime("%A").lower()))
    except Exception:
        pass

    return tags


def _upsert_event_and_tags(event, eid):
    """Upsert event row and replace tags in Supabase."""
    from datetime import datetime
    now = datetime.utcnow().isoformat()

    _supabase("POST", "/rest/v1/events", {
        "event_id": eid,
        "name": event.get("name"),
        "type": event.get("type"),
        "date": event.get("date"),
        "time": event.get("time"),
        "venue": event.get("venue"),
        "neighborhood": event.get("neighborhood"),
        "indoor_outdoor": event.get("indoor_outdoor"),
        "price_range": event.get("price_range"),
        "url": event.get("url"),
        "description": event.get("description", ""),
        "source": event.get("source", ""),
        "first_seen": now,
        "last_seen": now,
        "raw_json": json.dumps(event),
    })

    # Replace tags
    safe_id = urllib.parse.quote(eid, safe="")
    _supabase("DELETE", f"/rest/v1/tags?event_id=eq.{safe_id}")
    tags = _extract_tags(event)
    for tag_type, tag_value in tags:
        _supabase("POST", "/rest/v1/tags", {
            "event_id": eid,
            "tag_type": tag_type,
            "tag_value": tag_value,
        })


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as exc:
            self._respond(400, {"success": False, "error": str(exc)})
            return

        # ── New format: { event_id, event: {...}, rating: 1|0|-1 } ──────────
        full_event = body.get("event")
        rating     = body.get("rating")
        event_id   = body.get("event_id")

        # ── Legacy format detection ─────────────────────────────────────────
        action = body.get("action")
        if action and rating is None:
            # Old client: translate action to integer rating
            if action == "unlike":
                rating = None  # will delete
            else:
                rating = 1

        if not event_id:
            if full_event:
                event_id = _event_id(full_event)
            else:
                self._respond(400, {"success": False, "error": "missing event_id"})
                return

        try:
            # Upsert full event + tags if provided
            if full_event and isinstance(full_event, dict):
                _upsert_event_and_tags(full_event, event_id)

            safe_id = urllib.parse.quote(event_id, safe="")

            if rating is None:
                # Delete rating (unlike/toggle off)
                status, _ = _supabase("DELETE", f"/rest/v1/ratings?event_id=eq.{safe_id}")
            else:
                from datetime import datetime
                now = datetime.utcnow().isoformat()
                status, _ = _supabase("POST", "/rest/v1/ratings", {
                    "event_id": event_id,
                    "rating":   rating,
                    "rated_at": now,
                    # Keep legacy columns populated for backward compat
                    "event_name": body.get("event_name") or (full_event or {}).get("name"),
                    "event_date": body.get("event_date") or (full_event or {}).get("date"),
                    "event_type": body.get("event_type") or (full_event or {}).get("type"),
                })

            ok = status in (200, 201, 204)
            self._respond(200 if ok else 500, {"success": ok})

        except Exception as exc:
            self._respond(500, {"success": False, "error": str(exc)})

    def _respond(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        pass
