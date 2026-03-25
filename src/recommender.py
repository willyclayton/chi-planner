"""
Adaptive recommendation engine.

Loose mode  (< 20 liked): rule_score, threshold = 0.35
Tight mode  (>= 20 liked): cosine similarity to liked-event centroid,
                            threshold = max(0.3, mean - 1.5*std)

Reads liked events from Supabase when SUPABASE_URL / SUPABASE_ANON_KEY are set,
falls back to local SQLite otherwise (local dev).
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

DATA_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DB_FILE     = os.path.join(DATA_DIR, "ratings.db")
MIN_RATINGS = 20

# ── Keyword / venue sets ──────────────────────────────────────────────────────

ROCK_COUNTRY_KEYWORDS = {
    "rock", "country", "folk", "americana",
    "isbell", "wilco", "turnpike", "truckers",
    "sturgill", "lucinda", "bingham", "deer tick",
    "old crow", "townes", "wheeler walker", "whitehorse",
    "jamey johnson", "bloodshot", "lake street dive",
}

EDM_KEYWORDS = {
    "edm", "techno", "rave", "house music",
    "electronic dance", "foam party",
}

_DJ_PATTERN = " dj "

COMEDY_VENUES = {
    "second city", "io theater", "iO theater",
    "laugh factory", "lincoln lodge", "zanies",
}

ARENA_VENUES = {
    "united center", "wintrust arena", "soldier field",
    "allstate arena", "credit union 1 arena",
}

INTIMATE_VENUES = {
    "thalia hall", "empty bottle", "hideout", "the hideout",
    "schubas", "lincoln hall", "vic theatre",
    "old town school", "metro", "house of blues",
    "riviera theatre", "double door", "bottom lounge",
}

EDM_VENUES = {
    "radius chicago", "smart bar", "spybar",
    "underground chicago", "hydrate nightclub", "float chicago",
}

NEAR_HOME_NEIGHBORHOODS = {
    "lakeview", "lincoln park", "wrigleyville",
    "lincoln square", "bucktown",
}

POPUP_KEYWORDS = {"pop-up", "popup", "pop up"}


# ── Feature extraction ────────────────────────────────────────────────────────

def _features(event):
    """Return a 28-element feature vector for one event."""
    name         = event.get("name", "").lower()
    name_pad     = f" {name} "
    etype        = event.get("type", "")
    venue        = event.get("venue", "").lower()
    neighborhood = event.get("neighborhood", "").lower()
    price        = event.get("price_range", "$$")
    io           = event.get("indoor_outdoor", "indoor")

    try:
        dt          = datetime.fromisoformat(event["date"] + "T" + event.get("time", "20:00"))
        day_of_week = dt.weekday()
        hour        = dt.hour
    except Exception:
        day_of_week = 5
        hour        = 20

    is_music    = int(etype == "music")
    is_comedy   = int(etype == "comedy")
    is_sports   = int(etype == "sports")
    is_food     = int(etype == "food")
    is_festival = int(etype == "festival")
    is_other    = int(etype == "other")

    is_cubs       = int("cubs"       in name)
    is_blackhawks = int("blackhawks" in name)
    is_bulls      = int("bulls"      in name)
    is_bears      = int("bears"      in name)

    is_rock_country       = int(any(kw in name for kw in ROCK_COUNTRY_KEYWORDS))
    is_edm                = int(
        any(kw in name for kw in EDM_KEYWORDS)
        or _DJ_PATTERN in name_pad
        or any(v in venue for v in EDM_VENUES)
    )
    is_comedy_known_venue = int(any(v in venue for v in COMEDY_VENUES))
    is_arena_show         = int(any(v in venue for v in ARENA_VENUES))
    is_intimate_venue     = int(any(v in venue for v in INTIMATE_VENUES))
    is_comedy_open_mic    = int(etype == "comedy" and "open mic" in name)

    is_near_home = int(any(n in neighborhood for n in NEAR_HOME_NEIGHBORHOODS))
    is_suburb    = int(event.get("city", "").lower() not in ("", "chicago"))
    is_outdoor   = int(io == "outdoor")
    is_mixed     = int(io == "mixed")

    price_free = int(price == "free")
    price_low  = int(price == "$")
    price_mid  = int(price == "$$")
    price_high = int(price == "$$$")

    is_weekend   = int(day_of_week >= 4)
    is_weeknight = int(day_of_week < 4)
    hour_norm    = hour / 23.0
    is_prime     = int(19 <= hour <= 22)

    return [
        is_music, is_comedy, is_sports, is_food, is_festival, is_other,
        is_cubs, is_blackhawks, is_bulls, is_bears,
        is_rock_country, is_edm, is_comedy_known_venue,
        is_arena_show, is_intimate_venue, is_comedy_open_mic,
        is_near_home, is_suburb, is_outdoor, is_mixed,
        price_free, price_low, price_mid, price_high,
        is_weekend, is_weeknight, hour_norm, is_prime,
    ]


def _partial_event(name, etype):
    """Minimal event dict reconstructed from Supabase-stored fields."""
    return {
        "name": name, "type": etype,
        "date": "2026-01-01", "time": "20:00",
        "venue": "", "neighborhood": "",
        "indoor_outdoor": "indoor", "price_range": "$$",
    }


# ── Rule-based fallback ───────────────────────────────────────────────────────

def rule_score(event):
    """Heuristic score in [0, 1] based on user-profile.md weights."""
    name      = event.get("name", "").lower()
    name_pad  = f" {name} "
    venue     = event.get("venue", "").lower()
    neighborhood = event.get("neighborhood", "").lower()
    price     = event.get("price_range", "$$")

    try:
        dt = datetime.fromisoformat(event["date"] + "T" + event.get("time", "20:00"))
        is_weekend = dt.weekday() >= 4
    except Exception:
        is_weekend = False

    score = 0.5

    if "cubs"       in name:                                    score += 0.35
    if "blackhawks" in name:                                    score += 0.25
    if any(v in venue for v in COMEDY_VENUES):                  score += 0.25
    if any(kw in name for kw in ROCK_COUNTRY_KEYWORDS):         score += 0.25
    if (any(kw in name for kw in EDM_KEYWORDS)
            or _DJ_PATTERN in name_pad
            or any(v in venue for v in EDM_VENUES)):            score -= 0.50
    if any(v in venue for v in ARENA_VENUES):                   score -= 0.15
    if any(v in venue for v in INTIMATE_VENUES):                score += 0.15
    if any(n in neighborhood for n in NEAR_HOME_NEIGHBORHOODS): score += 0.10
    if price == "$$$":                                          score -= 0.10
    if price == "$$$$":                                         score -= 0.25
    if is_weekend:                                              score += 0.05

    etype = event.get("type", "")
    if etype == "festival":                                     score += 0.20
    if any(kw in name for kw in POPUP_KEYWORDS):                score += 0.15

    return round(max(0.0, min(1.0, score)), 4)


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_liked_from_supabase():
    """
    Returns list of {event_id, event_name, event_type, event_date} dicts,
    or None if Supabase is not configured / unavailable.
    """
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None

    endpoint = url + "/rest/v1/ratings?select=event_id,event_name,event_type,event_date"
    req = urllib.request.Request(endpoint, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _load_liked_from_sqlite():
    """SQLite fallback for local dev."""
    import sqlite3
    if not os.path.exists(DB_FILE):
        return []
    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute(
            "SELECT event_json, rating FROM ratings WHERE rating = 1"
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            try:
                ev = json.loads(row[0])
                result.append({
                    "event_id":   ev.get("id", ev.get("name", "")),
                    "event_name": ev.get("name", ""),
                    "event_type": ev.get("type", ""),
                    "event_date": ev.get("date", ""),
                })
            except Exception:
                pass
        return result
    except Exception:
        return []


# ── Public entry point ────────────────────────────────────────────────────────

def score_events(events):
    """
    Score all events and return (scored_events, threshold).

    threshold is the minimum score for "My Picks" display.
    Never raises — falls back gracefully on any error.
    """
    try:
        liked = _load_liked_from_supabase()
        if liked is None:
            liked = _load_liked_from_sqlite()

        liked_count = len(liked)

        # ── Loose mode ────────────────────────────────────────────────────────
        if liked_count < MIN_RATINGS:
            for event in events:
                event["score"] = rule_score(event)
            return events, 0.35

        # ── Tight mode ────────────────────────────────────────────────────────
        try:
            import numpy as np

            liked_feats = np.array([
                _features(_partial_event(r.get("event_name", ""), r.get("event_type", "")))
                for r in liked
            ], dtype=float)

            centroid      = liked_feats.mean(axis=0)
            centroid_norm = float(np.linalg.norm(centroid))

            def _cos(feat_vec):
                fn = float(np.linalg.norm(feat_vec))
                if centroid_norm == 0 or fn == 0:
                    return 0.0
                return float(np.dot(centroid, feat_vec) / (centroid_norm * fn))

            for event in events:
                feat = np.array(_features(event), dtype=float)
                event["score"] = round((_cos(feat) + 1) / 2, 4)

            liked_scores = [
                (_cos(np.array(
                    _features(_partial_event(r.get("event_name", ""), r.get("event_type", ""))),
                    dtype=float,
                )) + 1) / 2
                for r in liked
            ]

            mean_s    = float(np.mean(liked_scores))
            std_s     = float(np.std(liked_scores))
            threshold = max(0.30, round(mean_s - 1.5 * std_s, 4))

            return events, threshold

        except Exception:
            for event in events:
                event["score"] = rule_score(event)
            return events, 0.35

    except Exception:
        for event in events:
            event["score"] = rule_score(event)
        return events, 0.35
