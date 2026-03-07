import urllib.request
import urllib.parse
import json
import os
from datetime import date

# zip code → Chicago neighborhood (shared with do312.py)
ZIP_NEIGHBORHOODS = {
    "60601": "Loop",          "60602": "Loop",
    "60603": "Loop",          "60604": "Loop",
    "60605": "Museum Campus", "60606": "Loop",
    "60607": "West Loop",     "60608": "Pilsen",
    "60609": "Bridgeport",    "60610": "Old Town",
    "60611": "Streeterville", "60612": "West Loop",
    "60613": "Wrigleyville",  "60614": "Lincoln Park",
    "60615": "Hyde Park",     "60616": "Chinatown",
    "60618": "Ravenswood",    "60622": "Wicker Park",
    "60625": "Lincoln Square","60626": "Rogers Park",
    "60640": "Andersonville", "60642": "River North",
    "60647": "Logan Square",  "60654": "River North",
    "60657": "Lakeview",      "60660": "Rogers Park",
    "60661": "West Loop",
}

BASE_URL = "https://www.eventbriteapi.com/v3/events/search/"

# User-profile: skip EDM/DJ events
EDM_KEYWORDS = ["edm", "techno", "rave", " dj ", "house music"]

# Eventbrite category_id → our event type
CATEGORY_MAP = {
    "103": "music",
    "110": "food",
    "116": "festival",
}


def _is_edm(name):
    nl = name.lower()
    return any(kw in nl for kw in EDM_KEYWORDS)


def _map_price(min_price):
    """Map a minimum ticket price to a price_range tier."""
    if min_price < 15:
        return "$"
    if min_price < 35:
        return "$$"
    if min_price < 75:
        return "$$$"
    return "$$$$"


def _parse_local_datetime(local_str):
    """Parse 'YYYY-MM-DDTHH:MM:SS' → (date, 'HH:MM')."""
    # local_str is like "2026-03-07T19:30:00"
    parts = local_str.split("T")
    event_date = date.fromisoformat(parts[0])
    event_time = parts[1][:5] if len(parts) > 1 else "20:00"
    return event_date, event_time


def fetch_eventbrite_events(week_start: date, week_end: date) -> list:
    """Fetch Chicago events from the Eventbrite API v3."""
    token = os.environ.get("EVENTBRITE_API_KEY", "")
    if not token:
        return []

    params = urllib.parse.urlencode({
        "location.address":     "Chicago, IL",
        "location.within":      "25mi",
        "start_date.range_start": f"{week_start.isoformat()}T00:00:00Z",
        "start_date.range_end":   f"{week_end.isoformat()}T23:59:59Z",
        "categories":           "103,110,116",
        "expand":               "venue,category",
        "page_size":            "50",
    })
    url = f"{BASE_URL}?{params}"

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []

    raw_events = data.get("events", [])

    events = []
    for ev in raw_events:
        try:
            # --- venue / city gate ---
            venue_obj = ev.get("venue") or {}
            address_obj = venue_obj.get("address") or {}
            city = address_obj.get("city", "")
            if city.lower() != "chicago":
                continue

            # --- name / EDM gate ---
            name = (ev.get("name") or {}).get("text", "")
            if not name:
                continue
            if _is_edm(name):
                continue

            # --- dates ---
            start_local = (ev.get("start") or {}).get("local", "")
            if not start_local:
                continue
            try:
                event_date, event_time = _parse_local_datetime(start_local)
            except (ValueError, IndexError):
                continue

            if not (week_start <= event_date <= week_end):
                continue

            # --- type ---
            category_obj = ev.get("category") or {}
            category_id = str(category_obj.get("id", ""))
            event_type = CATEGORY_MAP.get(category_id, "other")

            # --- venue details ---
            venue_name = venue_obj.get("name", "Chicago")
            zip_raw = address_obj.get("postal_code", "")
            zipcode = zip_raw[:5] if zip_raw else ""
            neighborhood = ZIP_NEIGHBORHOODS.get(zipcode, "Chicago")

            # --- price ---
            is_free = ev.get("is_free", False)
            if is_free:
                price_range = "free"
            else:
                ticket_avail = ev.get("ticket_availability") or {}
                min_price_obj = ticket_avail.get("minimum_ticket_price") or {}
                min_price_val = min_price_obj.get("major_value")
                if min_price_val is not None:
                    try:
                        price_range = _map_price(float(min_price_val))
                    except (TypeError, ValueError):
                        price_range = "$$"
                else:
                    price_range = "$$"

            # --- url ---
            event_url = ev.get("url", "https://www.eventbrite.com")

            events.append({
                "name":           name,
                "type":           event_type,
                "date":           event_date.isoformat(),
                "time":           event_time,
                "venue":          venue_name,
                "neighborhood":   neighborhood,
                "indoor_outdoor": "indoor",
                "price_range":    price_range,
                "url":            event_url,
                "description":    "",
            })

        except (KeyError, IndexError, TypeError):
            continue

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
