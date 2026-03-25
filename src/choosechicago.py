"""
Choose Chicago event source.

Uses the Tribe Events REST API at choosechicago.com instead of HTML scraping,
since the site is a JS-rendered SPA with no server-side event markup.
"""
import urllib.request
import urllib.parse
import json
from datetime import date, datetime

API_URL = "https://www.choosechicago.com/wp-json/tribe/events/v1/events"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

FESTIVAL_KEYWORDS = [
    "festival", "fest ", "fair", "parade", "block party",
    "street fest", "market", "celebration",
]

# Skip these categories (per user-profile: no theatre)
SKIP_KEYWORDS = ["theatre", "theater", "opera", "ballet"]


def _infer_type(title, categories=None):
    combined = title.lower()
    if categories:
        combined += " " + " ".join(c.lower() for c in categories)
    if any(kw in combined for kw in FESTIVAL_KEYWORDS):
        return "festival"
    if "music" in combined or "concert" in combined:
        return "music"
    if "food" in combined or "taste" in combined or "dining" in combined:
        return "food"
    if "comedy" in combined or "standup" in combined:
        return "comedy"
    return "other"


def _should_skip(title, categories=None):
    combined = title.lower()
    if categories:
        combined += " " + " ".join(c.lower() for c in categories)
    return any(kw in combined for kw in SKIP_KEYWORDS)


def _parse_date(date_str):
    """Parse ISO datetime string from Tribe API → (date, 'HH:MM')."""
    if not date_str:
        return None, "12:00"
    try:
        # Tribe returns "2026-03-25 10:00:00" or ISO format
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.date(), dt.strftime("%H:%M")
    except (ValueError, AttributeError):
        pass
    try:
        date_part = date_str.split("T")[0].split(" ")[0]
        return date.fromisoformat(date_part), "12:00"
    except (ValueError, AttributeError):
        return None, "12:00"


def fetch_choosechicago_events(week_start: date, week_end: date) -> list:
    """Fetch events from the Choose Chicago Tribe Events REST API."""
    params = urllib.parse.urlencode({
        "start_date": week_start.isoformat(),
        "end_date": week_end.isoformat(),
        "per_page": "50",
    })
    url = f"{API_URL}?{params}"

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []

    raw_events = data.get("events", [])
    if not isinstance(raw_events, list):
        return []

    events = []
    for ev in raw_events:
        try:
            title = ev.get("title", "")
            if not title:
                continue

            # Get category names
            categories = []
            for cat in ev.get("categories", []):
                cat_name = cat.get("name", "") if isinstance(cat, dict) else str(cat)
                if cat_name:
                    categories.append(cat_name)

            if _should_skip(title, categories):
                continue

            # Parse date
            start_str = ev.get("start_date", "") or ev.get("utc_start_date", "")
            event_date, event_time = _parse_date(start_str)
            if event_date is None:
                continue
            if not (week_start <= event_date <= week_end):
                continue

            # Venue
            venue_obj = ev.get("venue", {}) or {}
            if isinstance(venue_obj, dict):
                venue = venue_obj.get("venue", "") or venue_obj.get("name", "") or "Chicago"
            else:
                venue = str(venue_obj) or "Chicago"

            # URL
            event_url = ev.get("url", "") or "https://www.choosechicago.com/events/"

            event_type = _infer_type(title, categories)

            events.append({
                "name":           title,
                "type":           event_type,
                "date":           event_date.isoformat(),
                "time":           event_time,
                "venue":          venue,
                "neighborhood":   "Chicago",
                "indoor_outdoor": "outdoor",
                "price_range":    "$",
                "url":            event_url,
                "description":    "",
            })

        except (KeyError, TypeError, ValueError):
            continue

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
