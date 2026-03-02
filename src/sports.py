import urllib.request
import json
from datetime import datetime, timedelta

# (sport, league, team_abbr, team_short_name, indoor_outdoor, neighborhood, price_range)
CHICAGO_TEAMS = [
    ("hockey",     "nhl",      "CHI", "Blackhawks", "indoor",  "West Loop",    "$$"),
    ("basketball", "nba",      "CHI", "Bulls",      "indoor",  "West Loop",    "$$"),
    ("baseball",   "mlb",      "CHC", "Cubs",       "outdoor", "Wrigleyville", "$$"),
    ("football",   "nfl",      "CHI", "Bears",      "outdoor", "Museum Campus","$$$"),
]


def _parse_espn_date(date_str):
    """ESPN UTC date → Chicago local (date, HH:MM). Uses CST (UTC-6) — close enough for March."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    local = dt - timedelta(hours=6)
    return local.date(), local.strftime("%H:%M")


def _get_link(links):
    for link in links:
        if "desktop" in link.get("rel", []):
            return link.get("href", "")
    return links[0].get("href", "") if links else ""


def _fetch(sport, league, abbr):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{abbr}/schedule"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def get_sports_events(week_start, week_end):
    """Return normalized home-game event dicts for all Chicago teams within the week."""
    events = []

    for sport, league, abbr, team_name, indoor_outdoor, neighborhood, price in CHICAGO_TEAMS:
        try:
            data = _fetch(sport, league, abbr)
        except Exception:
            continue  # API down or team offseason — skip silently

        for event in data.get("events", []):
            date_str = event.get("date", "")
            if not date_str:
                continue
            try:
                game_date, game_time = _parse_espn_date(date_str)
            except Exception:
                continue

            if not (week_start <= game_date <= week_end):
                continue

            competitions = event.get("competitions", [])
            if not competitions:
                continue
            comp = competitions[0]
            competitors = comp.get("competitors", [])

            # Only include home games
            is_home = any(
                c.get("homeAway") == "home" and c.get("team", {}).get("abbreviation") == abbr
                for c in competitors
            )
            if not is_home:
                continue

            # Skip games not in Chicago (handles spring training in AZ, suburban venues)
            city = comp.get("venue", {}).get("address", {}).get("city", "Chicago")
            if city and city.lower() != "chicago":
                continue

            opponent = next(
                (c.get("team", {}).get("shortDisplayName", "")
                 for c in competitors if c.get("homeAway") == "away"),
                ""
            )

            venue_name = comp.get("venue", {}).get("fullName", "")
            display_name = f"{team_name} vs {opponent}" if opponent else team_name

            events.append({
                "name": display_name,
                "type": "sports",
                "date": game_date.isoformat(),
                "time": game_time,
                "venue": venue_name,
                "neighborhood": neighborhood,
                "indoor_outdoor": indoor_outdoor,
                "price_range": price,
                "url": _get_link(event.get("links", [])),
                "description": f"Home game — {display_name}.",
            })

    events.sort(key=lambda e: (e["date"], e["time"]))
    return events
