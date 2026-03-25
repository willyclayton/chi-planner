"""
DCASE (Department of Cultural Affairs and Special Events) source.

Queries the Chicago Data Portal Socrata API for public festivals,
street events, and cultural programming.
"""
import urllib.request
import urllib.parse
import json
from datetime import date

# DCASE-specific Socrata dataset endpoints
SOCRATA_URLS = [
    "https://data.cityofchicago.org/resource/m3c6-iqrs.json",  # DCASE Special Events
    "https://data.cityofchicago.org/resource/pk66-w54g.json",   # DCASE Cultural Events
]

DATE_FIELDS = ["start_date", "date", "event_date", "start_date_time"]

FESTIVAL_KEYWORDS = [
    "festival", "fest ", "fair", "parade", "celebration",
    "market", "block party", "street fest",
]


def _infer_type(title, description=""):
    combined = (title + " " + description).lower()
    if any(kw in combined for kw in FESTIVAL_KEYWORDS):
        return "festival"
    return "other"


def _parse_date(record):
    for field in DATE_FIELDS:
        raw = record.get(field, "")
        if not raw:
            continue
        try:
            date_part = raw.split("T")[0].split(" ")[0]
            return date.fromisoformat(date_part)
        except (ValueError, AttributeError):
            continue
    return None


def _parse_time(record):
    for field in ("start_time", "time", "event_time", "starttime"):
        raw = record.get(field, "")
        if not raw:
            continue
        cleaned = str(raw).strip()[:5]
        if len(cleaned) >= 4 and cleaned[2:3] == ":":
            return cleaned[:5]
    return "12:00"


def _venue_name(record):
    for field in ("event_location", "location", "venue", "park_name", "facility_name"):
        val = record.get(field, "")
        if val:
            return str(val).strip()
    return "Chicago"


def _fetch_dataset(url, week_start, week_end):
    for date_field in DATE_FIELDS:
        where = (
            f"{date_field} between '{week_start.isoformat()}' "
            f"and '{week_end.isoformat()}'"
        )
        params = urllib.parse.urlencode({
            "$where": where,
            "$limit": "50",
        })
        full_url = f"{url}?{params}"
        try:
            with urllib.request.urlopen(full_url, timeout=15) as resp:
                records = json.loads(resp.read())
            if isinstance(records, list):
                return records
        except Exception:
            continue
    return None


def fetch_dcase_events(week_start: date, week_end: date) -> list:
    """Fetch DCASE events from the Chicago Data Portal."""
    events = []

    for url in SOCRATA_URLS:
        try:
            records = _fetch_dataset(url, week_start, week_end)
        except Exception:
            continue

        if not records:
            continue

        for record in records:
            try:
                event_date = _parse_date(record)
                if event_date is None:
                    continue
                if not (week_start <= event_date <= week_end):
                    continue

                name = (
                    record.get("event_name")
                    or record.get("event_title")
                    or record.get("name")
                    or record.get("title")
                    or ""
                )
                name = str(name).strip()
                if not name:
                    continue

                description = str(
                    record.get("description", "") or record.get("event_description", "")
                ).strip()

                event_type = _infer_type(name, description)
                event_time = _parse_time(record)
                venue = _venue_name(record)

                events.append({
                    "name":           name,
                    "type":           event_type,
                    "date":           event_date.isoformat(),
                    "time":           event_time,
                    "venue":          venue,
                    "neighborhood":   "Chicago",
                    "indoor_outdoor": "outdoor",
                    "price_range":    "free",
                    "url":            "https://www.chicago.gov/city/en/depts/dca.html",
                    "description":    description,
                })

            except Exception:
                continue

        if events:
            break

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
