"""
Recommendation engine: feature extraction, model training, scoring.

Falls back to rule_score() when sklearn is unavailable or < MIN_RATINGS exist.
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")
MIN_RATINGS = 10

# ── Keyword / venue sets ───────────────────────────────────────────────────────

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

# Names that include " dj " (space-padded to avoid "adjust" etc.)
_DJ_PATTERN = " dj "

COMEDY_VENUES = {
    "second city", "io theater", "iO theater",
    "laugh factory", "lincoln lodge", "zanies",
}

ARENA_VENUES = {
    "united center", "wintrust arena", "soldier field",
    "allstate arena", "credit union 1 arena",
}

# Mid-size and small venues Will prefers
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


# ── Feature extraction ────────────────────────────────────────────────────────

def _features(event: dict) -> list:
    """Return a 27-element feature vector for one event."""
    name        = event.get("name", "").lower()
    name_pad    = f" {name} "          # pad so " dj " matches at word boundaries
    etype       = event.get("type", "")
    venue       = event.get("venue", "").lower()
    neighborhood = event.get("neighborhood", "").lower()
    price       = event.get("price_range", "$$")
    io          = event.get("indoor_outdoor", "indoor")

    try:
        dt          = datetime.fromisoformat(event["date"] + "T" + event.get("time", "20:00"))
        day_of_week = dt.weekday()   # Mon=0 … Sun=6
        hour        = dt.hour
    except Exception:
        day_of_week = 5
        hour        = 20

    # — Type (5) —
    is_music   = int(etype == "music")
    is_comedy  = int(etype == "comedy")
    is_sports  = int(etype == "sports")
    is_food    = int(etype == "food")
    is_other   = int(etype == "other")

    # — Sports team (4) —
    is_cubs       = int("cubs" in name)
    is_blackhawks = int("blackhawks" in name)
    is_bulls      = int("bulls" in name)
    is_bears      = int("bears" in name)

    # — Genre / tier (6) —
    is_rock_country      = int(any(kw in name for kw in ROCK_COUNTRY_KEYWORDS))
    is_edm               = int(
        any(kw in name for kw in EDM_KEYWORDS)
        or _DJ_PATTERN in name_pad
        or any(v in venue for v in EDM_VENUES)
    )
    is_comedy_known_venue = int(any(v in venue for v in COMEDY_VENUES))
    is_arena_show         = int(any(v in venue for v in ARENA_VENUES))
    is_intimate_venue     = int(any(v in venue for v in INTIMATE_VENUES))
    is_comedy_open_mic    = int(is_comedy and "open mic" in name)

    # — Venue / location (4) —
    is_near_home = int(any(n in neighborhood for n in NEAR_HOME_NEIGHBORHOODS))
    is_suburb    = int(event.get("city", "").lower() not in ("", "chicago"))
    is_outdoor   = int(io == "outdoor")
    is_mixed     = int(io == "mixed")

    # — Price (4) —
    price_free = int(price == "free")
    price_low  = int(price == "$")
    price_mid  = int(price == "$$")
    price_high = int(price == "$$$")

    # — Day / time (4) —
    is_weekend   = int(day_of_week >= 4)          # Fri / Sat / Sun
    is_weeknight = int(day_of_week < 4)           # Mon – Thu
    hour_norm    = hour / 23.0
    is_prime     = int(19 <= hour <= 22)

    return [
        is_music, is_comedy, is_sports, is_food, is_other,
        is_cubs, is_blackhawks, is_bulls, is_bears,
        is_rock_country, is_edm, is_comedy_known_venue,
        is_arena_show, is_intimate_venue, is_comedy_open_mic,
        is_near_home, is_suburb, is_outdoor, is_mixed,
        price_free, price_low, price_mid, price_high,
        is_weekend, is_weeknight, hour_norm, is_prime,
    ]


# ── Rule-based fallback ───────────────────────────────────────────────────────

def rule_score(event: dict) -> float:
    """Heuristic score in [0, 1] based on user-profile.md weights."""
    name  = event.get("name", "").lower()
    name_pad = f" {name} "
    venue = event.get("venue", "").lower()
    neighborhood = event.get("neighborhood", "").lower()
    price = event.get("price_range", "$$")

    try:
        dt = datetime.fromisoformat(event["date"] + "T" + event.get("time", "20:00"))
        is_weekend = dt.weekday() >= 4
    except Exception:
        is_weekend = False

    score = 0.5

    if "cubs" in name:                                    score += 0.35
    if "blackhawks" in name:                              score += 0.25
    if any(v in venue for v in COMEDY_VENUES):            score += 0.25
    if any(kw in name for kw in ROCK_COUNTRY_KEYWORDS):   score += 0.25
    if (any(kw in name for kw in EDM_KEYWORDS)
            or _DJ_PATTERN in name_pad
            or any(v in venue for v in EDM_VENUES)):      score -= 0.50
    if any(v in venue for v in ARENA_VENUES):             score -= 0.15
    if any(v in venue for v in INTIMATE_VENUES):          score += 0.15
    if any(n in neighborhood for n in NEAR_HOME_NEIGHBORHOODS): score += 0.10
    if price == "$$$":                                    score -= 0.10
    if is_weekend:                                        score += 0.05

    return round(max(0.0, min(1.0, score)), 4)


# ── Model training ────────────────────────────────────────────────────────────

def _load_ratings() -> list:
    if not os.path.exists(RATINGS_FILE):
        return []
    with open(RATINGS_FILE) as f:
        return json.load(f)


def _train_model(ratings: list):
    from sklearn.linear_model import LogisticRegression

    X = [_features(r["event"]) for r in ratings]
    y = [r["rating"] for r in ratings]

    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(X, y)
    return model


# ── Public entry point ────────────────────────────────────────────────────────

def score_events(events: list) -> list:
    """Add a 'score' field to each event. Never raises — falls back on any error."""
    try:
        ratings = _load_ratings()

        if len(ratings) >= MIN_RATINGS:
            try:
                model  = _train_model(ratings)
                classes = list(model.classes_)
                idx_pos = classes.index(1)  if 1  in classes else None
                idx_neu = classes.index(0)  if 0  in classes else None

                for event in events:
                    proba = model.predict_proba([_features(event)])[0]
                    p_pos = proba[idx_pos] if idx_pos is not None else 0.0
                    p_neu = proba[idx_neu] if idx_neu is not None else 0.0
                    event["score"] = round(p_pos + 0.5 * p_neu, 4)

                return events
            except Exception:
                pass    # fall through to rule_score

        # Fewer than MIN_RATINGS or sklearn unavailable → rule-based
        for event in events:
            event["score"] = rule_score(event)
        return events

    except Exception:
        for event in events:
            event["score"] = rule_score(event)
        return events
