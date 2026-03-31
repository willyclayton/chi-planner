"""
Tag-affinity recommendation engine.

Scores events by weighted average of tag affinities learned from ratings.
Falls back to rule_score() with < 10 ratings (cold start).

Reads from Supabase when configured, falls back to local SQLite.
"""
import os
from datetime import datetime

MIN_RATINGS = 10
NOVELTY_BONUS = 0.35  # score for events with no matching tags

TAG_WEIGHTS = {
    "artist":       5.0,
    "team":         4.0,
    "venue":        3.0,
    "type":         2.0,
    "neighborhood": 1.5,
    "keyword":      1.0,
    "price":        0.5,
    "day_of_week":  0.3,
}

# ── Keyword / venue sets (kept for rule_score fallback) ───────────────────────

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


# ── Rule-based fallback (cold start) ─────────────────────────────────────────

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


# ── Tag affinity scoring ─────────────────────────────────────────────────────

def _score_event_by_tags(event, affinities, tags):
    """
    Score one event using weighted tag affinities.
    Returns float in [0, 1].
    """
    weighted_sum = 0.0
    weight_total = 0.0

    for tag_type, tag_value in tags:
        key = (tag_type, tag_value)
        weight = TAG_WEIGHTS.get(tag_type, 1.0)

        if key in affinities:
            weighted_sum += affinities[key] * weight
            weight_total += weight

    if weight_total == 0:
        return NOVELTY_BONUS

    # Raw score is in [-1, 1], normalize to [0, 1]
    raw = weighted_sum / weight_total
    return round(max(0.0, min(1.0, (raw + 1) / 2)), 4)


def _load_affinities():
    """Load tag affinities + rating count from best available source."""
    try:
        from db import supabase_get_ratings_with_tags, get_tag_affinities, get_ratings_count

        # Try Supabase first
        sb_data = supabase_get_ratings_with_tags()
        if sb_data is not None and len(sb_data) >= MIN_RATINGS:
            # Compute affinities from Supabase data
            tag_stats = {}
            for _, rating, tag_list in sb_data:
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

            return affinities, len(sb_data)

        # Fall back to SQLite
        count = get_ratings_count()
        if count >= MIN_RATINGS:
            return get_tag_affinities(), count

        return {}, count

    except Exception:
        return {}, 0


# ── Public entry point ────────────────────────────────────────────────────────

def score_events(events):
    """
    Score all events and return (scored_events, threshold).

    threshold is the minimum score for "My Picks" display.
    Never raises — falls back gracefully on any error.
    """
    try:
        affinities, rating_count = _load_affinities()

        # Cold start — use rules
        if rating_count < MIN_RATINGS:
            for event in events:
                event["score"] = rule_score(event)
            return events, 0.35

        # Tag affinity scoring
        from db import extract_tags

        for event in events:
            tags = extract_tags(event)
            event["score"] = _score_event_by_tags(event, affinities, tags)

        # Dynamic threshold: median of all scores, floored at 0.35
        scores = sorted(e.get("score", 0) for e in events)
        if scores:
            median = scores[len(scores) // 2]
            threshold = max(0.35, round(median, 4))
        else:
            threshold = 0.35

        return events, threshold

    except Exception:
        for event in events:
            event["score"] = rule_score(event)
        return events, 0.35
