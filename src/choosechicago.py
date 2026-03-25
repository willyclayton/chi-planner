"""
Choose Chicago scraper for festival and street event listings.

Scrapes choosechicago.com/events/ using urllib + regex.
Returns [] gracefully if the page is JS-rendered or unparseable.
"""
import urllib.request
import re
import html
from datetime import date, datetime

EVENTS_URL = "https://www.choosechicago.com/events/"

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


def _infer_type(title):
    tl = title.lower()
    if any(kw in tl for kw in FESTIVAL_KEYWORDS):
        return "festival"
    return "other"


def _parse_date_str(date_str):
    """Try common date formats from Choose Chicago."""
    date_str = date_str.strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    # Try ISO substring
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, IndexError):
        pass
    return None


def fetch_choosechicago_events(week_start: date, week_end: date) -> list:
    """Scrape choosechicago.com/events/ for festival/street event listings."""
    req = urllib.request.Request(EVENTS_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    # If page is mostly JS-rendered, we won't find event markup
    if len(raw) < 500 or "<noscript" in raw.lower() and "enable javascript" in raw.lower():
        return []

    events = []

    # Try to find event cards — Choose Chicago uses various markup patterns
    # Pattern 1: structured event cards with title + date
    cards = re.findall(
        r'<(?:article|div)[^>]*class="[^"]*event[^"]*"[^>]*>(.*?)</(?:article|div)>',
        raw, re.DOTALL | re.IGNORECASE
    )

    for card in cards:
        # Extract title
        title_m = re.search(
            r'<(?:h[2-4]|a)[^>]*>([^<]{5,120})</(?:h[2-4]|a)>', card
        )
        if not title_m:
            continue
        name = html.unescape(title_m.group(1).strip())
        if not name:
            continue

        # Extract date
        date_m = re.search(
            r'(?:datetime|date|time)[^>]*>([^<]+)<',
            card, re.IGNORECASE
        )
        if not date_m:
            # Try date in any text containing month names
            date_m = re.search(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*\d{4})',
                card, re.IGNORECASE
            )
        if not date_m:
            continue

        event_date = _parse_date_str(date_m.group(1))
        if event_date is None:
            continue
        if not (week_start <= event_date <= week_end):
            continue

        # Extract URL
        url_m = re.search(r'href="([^"]+)"', card)
        event_url = url_m.group(1) if url_m else EVENTS_URL
        if event_url.startswith("/"):
            event_url = "https://www.choosechicago.com" + event_url

        # Extract venue/location if available
        venue_m = re.search(
            r'(?:location|venue|place)[^>]*>([^<]+)<',
            card, re.IGNORECASE
        )
        venue = html.unescape(venue_m.group(1).strip()) if venue_m else "Chicago"

        events.append({
            "name":           name,
            "type":           _infer_type(name),
            "date":           event_date.isoformat(),
            "time":           "12:00",
            "venue":          venue,
            "neighborhood":   "Chicago",
            "indoor_outdoor": "outdoor",
            "price_range":    "$",
            "url":            event_url,
            "description":    "",
        })

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
