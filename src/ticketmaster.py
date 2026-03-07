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

BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

# User-profile: skip EDM/DJ events
EDM_KEYWORDS = ["edm", "techno", "rave", " dj ", "house music"]

# Ticketmaster segment name → our event type (None = skip)
SEGMENT_MAP = {
    "Music":             "music",
    "Sports":            "sports",
    "Arts & Theatre":    None,      # not Will's scene per user-profile
    "Festivals":         "festival",
}


def _map_price(min_price):
    """Map a minimum ticket price to a price_range tier."""
    if min_price < 15:
        return "$"
    if min_price < 35:
        return "$$"
    if min_price < 75:
        return "$$$"
    return "$$$$"


def _is_edm(name):
    nl = name.lower()
    return any(kw in nl for kw in EDM_KEYWORDS)


def fetch_ticketmaster_events(week_start: date, week_end: date) -> list:
    """Fetch Chicago events from the Ticketmaster Discovery API v2."""
    api_key = os.environ.get("TICKETMASTER_API_KEY", "")
    if not api_key:
        return []

    params = urllib.parse.urlencode({
        "apikey":             api_key,
        "city":               "Chicago",
        "stateCode":          "IL",
        "classificationName": "Music,Sports,Arts & Theatre,Festivals",
        "startDateTime":      f"{week_start.isoformat()}T00:00:00Z",
        "endDateTime":        f"{week_end.isoformat()}T23:59:59Z",
        "size":               "50",
        "sort":               "date,asc",
    })
    url = f"{BASE_URL}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []

    try:
        raw_events = data["_embedded"]["events"]
    except (KeyError, TypeError):
        return []

    events = []
    for ev in raw_events:
        try:
            # --- venue / city gate ---
            venues = ev.get("_embedded", {}).get("venues", [])
            venue_obj = venues[0] if venues else {}
            city = venue_obj.get("city", {}).get("name", "")
            if city.lower() != "chicago":
                continue

            # --- classification / type gate ---
            classifications = ev.get("classifications", [])
            segment_name = ""
            classification_name = ""
            if classifications:
                seg = classifications[0].get("segment", {})
                segment_name = seg.get("name", "")
                genre = classifications[0].get("genre", {})
                classification_name = genre.get("name", "")

            event_type = SEGMENT_MAP.get(segment_name)
            if event_type is None:
                continue

            # Skip theatre/film sub-classifications
            if "Theatre" in classification_name or "Film" in classification_name:
                continue

            # --- name / EDM gate ---
            name = ev.get("name", "")
            if not name:
                continue
            if _is_edm(name):
                continue

            # --- dates ---
            dates_obj = ev.get("dates", {}).get("start", {})
            local_date_str = dates_obj.get("localDate", "")
            if not local_date_str:
                continue
            try:
                event_date = date.fromisoformat(local_date_str)
            except ValueError:
                continue

            if not (week_start <= event_date <= week_end):
                continue

            local_time = dates_obj.get("localTime", "")
            event_time = local_time[:5] if local_time else "20:00"

            # --- venue details ---
            venue_name = venue_obj.get("name", "Chicago")
            zip_raw = venue_obj.get("postalCode", "")
            # Ticketmaster sometimes returns 5+4 format; keep only first 5 digits
            zipcode = zip_raw[:5] if zip_raw else ""
            neighborhood = ZIP_NEIGHBORHOODS.get(zipcode, "Chicago")

            # --- price ---
            price_ranges = ev.get("priceRanges", [])
            if price_ranges:
                try:
                    min_price = float(price_ranges[0].get("min", 35))
                    price_range = _map_price(min_price)
                except (TypeError, ValueError):
                    price_range = "$$"
            else:
                price_range = "$$"

            # --- url ---
            event_url = ev.get("url", "https://www.ticketmaster.com")

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
