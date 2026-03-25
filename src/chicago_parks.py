import urllib.request
import urllib.parse
import json
from datetime import date

# Socrata dataset endpoints to try, in order
SOCRATA_URLS = [
    "https://data.cityofchicago.org/resource/pk66-w54g.json",  # Parks Special Events/Permits
]

# SoQL date field names to probe (datasets vary)
DATE_FIELDS = ["reservation_start_date", "start_date", "date", "event_date"]

# Keywords that suggest a festival vs a generic other event
FESTIVAL_KEYWORDS = ["festival", "fest ", "fair", "parade", "celebration", "market"]


def _infer_type(title, description=""):
    combined = (title + " " + description).lower()
    if any(kw in combined for kw in FESTIVAL_KEYWORDS):
        return "festival"
    return "other"


def _parse_date(record, date_fields):
    """Try multiple field names; return a date object or None."""
    for field in date_fields:
        raw = record.get(field, "")
        if not raw:
            continue
        try:
            # Handle ISO datetime strings and plain date strings
            date_part = raw.split("T")[0].split(" ")[0]
            return date.fromisoformat(date_part)
        except (ValueError, AttributeError):
            continue
    return None


def _parse_time(record):
    """Try common time field names; return 'HH:MM' or default '12:00'."""
    for field in ("start_time", "time", "event_time", "starttime"):
        raw = record.get(field, "")
        if not raw:
            continue
        cleaned = str(raw).strip()[:5]
        if len(cleaned) >= 4 and cleaned[2:3] == ":":
            return cleaned[:5]
    # Try extracting time from ISO datetime fields
    for field in DATE_FIELDS:
        raw = record.get(field, "")
        if raw and "T" in str(raw):
            time_part = str(raw).split("T")[1][:5]
            if len(time_part) >= 4 and time_part[2:3] == ":":
                return time_part
    return "12:00"


def _fetch_dataset(url, week_start: date, week_end: date):
    """
    Try a Socrata endpoint with SoQL date filters.
    Returns a list of raw record dicts, or None if the endpoint fails.
    """
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
            # Socrata returns an error dict on bad column names, or an empty list
            if isinstance(records, list):
                return records, date_field
        except Exception:
            continue
    return None, None


def _venue_name(record):
    """Return the best venue/park name available in the record."""
    for field in ("park_name", "facility_name", "venue_name", "location", "park", "facility"):
        val = record.get(field, "")
        if val:
            return str(val).strip()
    return "Chicago Park"


def fetch_parks_events(week_start: date, week_end: date) -> list:
    """Fetch Chicago Park District / Cultural events from the Chicago Data Portal."""
    events = []

    for url in SOCRATA_URLS:
        try:
            records, date_field = _fetch_dataset(url, week_start, week_end)
        except Exception:
            continue

        if records is None:
            continue
        if not records:
            continue  # try next dataset

        for record in records:
            try:
                # --- date ---
                event_date = _parse_date(record, DATE_FIELDS)
                if event_date is None:
                    continue
                if not (week_start <= event_date <= week_end):
                    continue

                # --- name ---
                name = (
                    record.get("event_name")
                    or record.get("event_description")
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
                    "url":            "https://www.chicagoparkdistrict.com",
                    "description":    description,
                })

            except Exception:
                continue

        # If we got records from this URL, stop trying fallback datasets
        if events:
            break

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
