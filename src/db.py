"""
Database abstraction — SQLite locally, Supabase in prod.

Tables: events, ratings, tags.
"""
import hashlib
import json
import os
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DB_FILE = os.path.join(DATA_DIR, "events.db")

# ── Tag extraction ────────────────────────────────────────────────────────────

TEAM_PATTERNS = {
    "cubs": "cubs", "blackhawks": "blackhawks", "bulls": "bulls",
    "bears": "bears", "white sox": "white sox", "fire": "fire",
}

EDM_KEYWORDS = {
    "edm", "techno", "rave", "house music", "electronic dance", "foam party",
}

COMEDY_KEYWORDS = {"improv", "standup", "stand-up", "comedy", "open mic"}


def event_id(event):
    key = f"{event['name']}{event['date']}{event.get('venue', '')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def extract_tags(event):
    """Extract tag (type, value) pairs from an event dict."""
    tags = []
    name = event.get("name", "").lower()
    venue = event.get("venue", "").lower()
    neighborhood = event.get("neighborhood", "").lower()
    etype = event.get("type", "").lower()
    price = event.get("price_range", "").lower()

    # Type tag
    if etype:
        tags.append(("type", etype))

    # Team tags
    for pattern, team in TEAM_PATTERNS.items():
        if pattern in name:
            tags.append(("team", team))

    # Artist tag — for music/comedy, use the event name as artist identifier
    if etype in ("music", "comedy"):
        # Strip venue suffix like "at Thalia Hall"
        artist = name
        for sep in [" at ", " @ "]:
            if sep in artist:
                artist = artist[:artist.index(sep)]
        artist = artist.strip()
        if artist:
            tags.append(("artist", artist))

    # Venue tag
    if venue:
        tags.append(("venue", venue))

    # Neighborhood tag
    if neighborhood:
        tags.append(("neighborhood", neighborhood))

    # Price tag
    if price:
        tags.append(("price", price))

    # Keyword tags
    if any(kw in name for kw in EDM_KEYWORDS) or " dj " in f" {name} ":
        tags.append(("keyword", "edm"))
    if any(kw in name for kw in COMEDY_KEYWORDS):
        tags.append(("keyword", "comedy"))
    if any(kw in name for kw in ("pop-up", "popup", "pop up")):
        tags.append(("keyword", "popup"))
    if "festival" in name or etype == "festival":
        tags.append(("keyword", "festival"))
    if "trivia" in name:
        tags.append(("keyword", "trivia"))
    if "brunch" in name:
        tags.append(("keyword", "brunch"))

    # Indoor/outdoor tag
    io = event.get("indoor_outdoor", "").lower()
    if io:
        tags.append(("keyword", io))

    # Day of week tag
    try:
        dt = datetime.fromisoformat(event["date"])
        day_name = dt.strftime("%A").lower()
        tags.append(("day_of_week", day_name))
    except Exception:
        pass

    return tags


# ── SQLite backend ────────────────────────────────────────────────────────────

def _get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id      TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            type          TEXT,
            date          TEXT,
            time          TEXT,
            venue         TEXT,
            neighborhood  TEXT,
            indoor_outdoor TEXT,
            price_range   TEXT,
            url           TEXT,
            description   TEXT,
            source        TEXT,
            first_seen    TEXT,
            last_seen     TEXT,
            score         REAL,
            raw_json      TEXT
        );
        CREATE TABLE IF NOT EXISTS ratings (
            event_id  TEXT PRIMARY KEY,
            rating    INTEGER NOT NULL,
            rated_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tags (
            event_id  TEXT NOT NULL,
            tag_type  TEXT NOT NULL,
            tag_value TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tags_event ON tags(event_id);
        CREATE INDEX IF NOT EXISTS idx_tags_type_value ON tags(tag_type, tag_value);
    """)


def upsert_events(events):
    """Store events and their tags in SQLite. Updates last_seen on duplicates."""
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    try:
        for event in events:
            eid = event.get("id") or event_id(event)
            conn.execute("""
                INSERT INTO events (event_id, name, type, date, time, venue,
                    neighborhood, indoor_outdoor, price_range, url, description,
                    source, first_seen, last_seen, score, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    score = excluded.score,
                    raw_json = excluded.raw_json
            """, (
                eid, event.get("name"), event.get("type"), event.get("date"),
                event.get("time"), event.get("venue"), event.get("neighborhood"),
                event.get("indoor_outdoor"), event.get("price_range"),
                event.get("url"), event.get("description"),
                event.get("source", ""), now, now,
                event.get("score"), json.dumps(event),
            ))

            # Refresh tags
            conn.execute("DELETE FROM tags WHERE event_id = ?", (eid,))
            tag_rows = [(eid, t, v) for t, v in extract_tags(event)]
            conn.executemany(
                "INSERT INTO tags (event_id, tag_type, tag_value) VALUES (?, ?, ?)",
                tag_rows,
            )
        conn.commit()
    finally:
        conn.close()


def save_rating(event_id_val, rating, event=None):
    """Save a rating. Optionally upsert the event too."""
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    try:
        if event:
            upsert_events([event])
        conn.execute("""
            INSERT INTO ratings (event_id, rating, rated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                rating = excluded.rating,
                rated_at = excluded.rated_at
        """, (event_id_val, rating, now))
        conn.commit()
    finally:
        conn.close()


def get_all_ratings_with_tags():
    """Return list of (event_id, rating, [(tag_type, tag_value), ...])."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT event_id, rating FROM ratings"
        ).fetchall()
        result = []
        for eid, rating in rows:
            tag_rows = conn.execute(
                "SELECT tag_type, tag_value FROM tags WHERE event_id = ?", (eid,)
            ).fetchall()
            result.append((eid, rating, tag_rows))
        return result
    finally:
        conn.close()


def get_tag_affinities():
    """
    Compute affinity for each (tag_type, tag_value) from all ratings.

    affinity = (liked_count - disliked_count) / total_rated_with_tag
    Returns dict of {(tag_type, tag_value): affinity_float}
    """
    ratings_with_tags = get_all_ratings_with_tags()
    if not ratings_with_tags:
        return {}

    # Accumulate per-tag stats
    tag_stats = {}  # (type, value) -> [liked, disliked, total]
    for _, rating, tag_list in ratings_with_tags:
        for tag_type, tag_value in tag_list:
            key = (tag_type, tag_value)
            if key not in tag_stats:
                tag_stats[key] = [0, 0, 0]
            tag_stats[key][2] += 1
            if rating == 1:
                tag_stats[key][0] += 1
            elif rating == -1:
                tag_stats[key][1] += 1

    affinities = {}
    for key, (liked, disliked, total) in tag_stats.items():
        affinities[key] = (liked - disliked) / total

    return affinities


def get_unrated_events():
    """Return event dicts that have no rating."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT e.raw_json FROM events e
            LEFT JOIN ratings r ON e.event_id = r.event_id
            WHERE r.event_id IS NULL
            ORDER BY e.date, e.time
        """).fetchall()
        return [json.loads(r[0]) for r in rows if r[0]]
    finally:
        conn.close()


def get_ratings_count():
    """Return total number of ratings."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ── Supabase backend ──────────────────────────────────────────────────────────

def _supabase_request(method, path, body=None):
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not base or not key:
        return None

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception:
        return None


def supabase_upsert_event(event):
    """Upsert a single event to Supabase events table."""
    eid = event.get("id") or event_id(event)
    now = datetime.utcnow().isoformat()
    result = _supabase_request("POST", "/rest/v1/events", {
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
        "description": event.get("description"),
        "source": event.get("source", ""),
        "first_seen": now,
        "last_seen": now,
        "score": event.get("score"),
        "raw_json": json.dumps(event),
    })
    return result


def supabase_upsert_tags(eid, tags):
    """Replace tags for an event in Supabase."""
    import urllib.parse
    safe_id = urllib.parse.quote(eid, safe="")
    _supabase_request("DELETE", f"/rest/v1/tags?event_id=eq.{safe_id}")
    for tag_type, tag_value in tags:
        _supabase_request("POST", "/rest/v1/tags", {
            "event_id": eid,
            "tag_type": tag_type,
            "tag_value": tag_value,
        })


def supabase_save_rating(eid, rating):
    """Save rating to Supabase."""
    now = datetime.utcnow().isoformat()
    return _supabase_request("POST", "/rest/v1/ratings", {
        "event_id": eid,
        "rating": rating,
        "rated_at": now,
    })


def supabase_get_ratings_with_tags():
    """Fetch all ratings and their tags from Supabase for scoring."""
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not base or not key:
        return None

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    # Get ratings
    req = urllib.request.Request(
        base + "/rest/v1/ratings?select=event_id,rating",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ratings = json.loads(resp.read().decode())
    except Exception:
        return None

    # Get tags
    req = urllib.request.Request(
        base + "/rest/v1/tags?select=event_id,tag_type,tag_value",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            all_tags = json.loads(resp.read().decode())
    except Exception:
        return None

    # Group tags by event_id
    tags_by_event = {}
    for t in all_tags:
        eid = t["event_id"]
        if eid not in tags_by_event:
            tags_by_event[eid] = []
        tags_by_event[eid].append((t["tag_type"], t["tag_value"]))

    result = []
    for r in ratings:
        eid = r["event_id"]
        result.append((eid, r["rating"], tags_by_event.get(eid, [])))

    return result
