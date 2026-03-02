import urllib.request
import re
import html
from datetime import datetime

BASE_URL = "https://do312.com"
EVENTS_URL = "https://do312.com/events/week"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# do312 category → our event type (None = skip)
CATEGORY_MAP = {
    "music":                    "music",
    "comedy":                   "comedy",
    "food-drink":               "food",
    "arts-culture":             "other",
    "festivals-fairs":          "other",
    "lgbtq":                    "other",
    "parties-djs":              None,   # EDM/DJ per user-profile
    "theatre-performing-arts":  None,   # not Will's scene
    "health-wellness":          None,
    "poetry-literary":          None,
    "film":                     None,
    "sports-recreation":        None,   # we have real sports from ESPN
}

# zip code → Chicago neighborhood (best-effort)
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

# Known outdoor/mixed venues
OUTDOOR_VENUES = {"millennium park", "grant park", "wrigley field", "soldier field"}
MIXED_VENUES = {"salt shed"}

# EDM/DJ keyword filter for music events
EDM_KEYWORDS = {"edm", " dj ", "techno", "rave", "house music", "nightclub"}

# Chain/undesirable venue skip list (user-profile: skip chain restaurant events)
SKIP_VENUES = {"dave & buster's", "dave and busters", "dave & busters"}


def _fix_offset(dt_str):
    """Python 3.9 fromisoformat can't handle -0600, needs -06:00."""
    return re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', dt_str)


def _indoor_outdoor(venue_name):
    vl = venue_name.lower()
    if any(v in vl for v in OUTDOOR_VENUES):
        return "outdoor"
    if any(v in vl for v in MIXED_VENUES):
        return "mixed"
    return "indoor"


def _is_edm(name, category):
    if category == "parties-djs":
        return True
    nl = name.lower()
    return any(kw in nl for kw in EDM_KEYWORDS)


def _price_range(name):
    if re.search(r'\bfree\b', name, re.IGNORECASE):
        return "free"
    return "$$"


def fetch_do312_events(week_start, week_end):
    """Scrape do312.com/events/week and return normalized event dicts."""
    req = urllib.request.Request(EVENTS_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    events = []
    # Split into per-event-card blocks (each starts at itemprop="event")
    cards = re.split(r'(?=<div[^>]+itemprop="event")', raw)

    for card in cards[1:]:
        cat_m = re.search(r'ds-event-category-([a-z0-9\-]+)', card)
        if not cat_m:
            continue
        do312_cat = cat_m.group(1)
        event_type = CATEGORY_MAP.get(do312_cat)
        if event_type is None:
            continue

        date_m = re.search(r'itemprop="startDate"\s+datetime="([^"]+)"', card)
        if not date_m:
            continue
        try:
            dt = datetime.fromisoformat(_fix_offset(date_m.group(1)))
        except Exception:
            continue

        game_date = dt.date()
        if not (week_start <= game_date <= week_end):
            continue

        name_m = re.search(
            r'class="ds-listing-event-title-text" itemprop="name">([^<]+)<', card
        )
        url_m = re.search(
            r'<a href="(/events/[^"]+)" itemprop="url" class="ds-listing-event-title', card
        )
        venue_m = re.search(
            r'href="/venues/[^"]*"[^>]*><span itemprop="name">([^<]+)', card
        )
        city_m = re.search(r'itemprop="addressLocality"\s+content="([^"]+)"', card)
        zip_m = re.search(r'itemprop="postalCode"\s+content="([^"]+)"', card)

        # Skip non-Chicago venues (suburbs)
        city = city_m.group(1) if city_m else ""
        if city and city.lower() != "chicago":
            continue

        name = html.unescape(name_m.group(1).strip()) if name_m else ""
        if not name:
            continue

        # Apply user-profile: skip EDM
        if _is_edm(name, do312_cat):
            continue

        venue = html.unescape(venue_m.group(1).strip()) if venue_m else "Chicago"

        # Skip chain restaurant events (user-profile dealbreaker)
        if venue.lower() in SKIP_VENUES:
            continue
        zipcode = zip_m.group(1) if zip_m else ""
        neighborhood = ZIP_NEIGHBORHOODS.get(zipcode, "Chicago")
        event_url = BASE_URL + url_m.group(1) if url_m else EVENTS_URL

        events.append({
            "name": name,
            "type": event_type,
            "date": game_date.isoformat(),
            "time": dt.strftime("%H:%M"),
            "venue": venue,
            "neighborhood": neighborhood,
            "indoor_outdoor": _indoor_outdoor(venue),
            "price_range": _price_range(name),
            "url": event_url,
            "description": "",
        })

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
