import sys
import os
from datetime import date, timedelta

# Allow running as `python src/main.py` from the project root
sys.path.insert(0, os.path.dirname(__file__))


def _load_env():
    """Load .env file into os.environ using stdlib only."""
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


_load_env()

from weather import fetch_weather
from sports import get_sports_events
from do312 import fetch_do312_events
from display import render

try:
    from ticketmaster import fetch_ticketmaster_events
except ImportError:
    fetch_ticketmaster_events = lambda a, b: []

try:
    from eventbrite import fetch_eventbrite_events
except ImportError:
    fetch_eventbrite_events = lambda a, b: []

try:
    from chicago_parks import fetch_parks_events
except ImportError:
    fetch_parks_events = lambda a, b: []

try:
    from choosechicago import fetch_choosechicago_events
except ImportError:
    fetch_choosechicago_events = lambda a, b: []

try:
    from dcase import fetch_dcase_events
except ImportError:
    fetch_dcase_events = lambda a, b: []


def main():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    print("Fetching weather...", end="", flush=True)
    try:
        weather = fetch_weather()
        print(" done.")
    except Exception as e:
        print(f"\n  ⚠ Couldn't fetch weather: {e}")
        weather = {}

    print("Fetching sports schedules...", end="", flush=True)
    try:
        sports = get_sports_events(monday, sunday)
        print(f" {len(sports)} home game(s) found.")
    except Exception as e:
        print(f"\n  ⚠ Sports fetch failed: {e}")
        sports = []

    print("Fetching do312 events...", end="", flush=True)
    try:
        culture = fetch_do312_events(monday, sunday)
        print(f" {len(culture)} event(s) found.")
    except Exception as e:
        print(f"\n  ⚠ do312 fetch failed: {e}")
        culture = []

    print("Fetching Ticketmaster events...", end="", flush=True)
    try:
        tm = fetch_ticketmaster_events(monday, sunday)
        print(f" {len(tm)} event(s) found.")
    except Exception as e:
        print(f"\n  ⚠ Ticketmaster fetch failed: {e}")
        tm = []

    print("Fetching Eventbrite events...", end="", flush=True)
    try:
        eb = fetch_eventbrite_events(monday, sunday)
        print(f" {len(eb)} event(s) found.")
    except Exception as e:
        print(f"\n  ⚠ Eventbrite fetch failed: {e}")
        eb = []

    print("Fetching Chicago Parks events...", end="", flush=True)
    try:
        parks = fetch_parks_events(monday, sunday)
        print(f" {len(parks)} event(s) found.")
    except Exception as e:
        print(f"\n  ⚠ Chicago Parks fetch failed: {e}")
        parks = []

    print("Fetching Choose Chicago events...", end="", flush=True)
    try:
        choosechicago = fetch_choosechicago_events(monday, sunday)
        print(f" {len(choosechicago)} event(s) found.")
    except Exception as e:
        print(f"\n  ⚠ Choose Chicago fetch failed: {e}")
        choosechicago = []

    print("Fetching DCASE events...", end="", flush=True)
    try:
        dcase = fetch_dcase_events(monday, sunday)
        print(f" {len(dcase)} event(s) found.")
    except Exception as e:
        print(f"\n  ⚠ DCASE fetch failed: {e}")
        dcase = []

    # Merge + dedup by name+date
    seen, unique = set(), []
    for e in sports + culture + tm + eb + parks + choosechicago + dcase:
        key = f"{e['name'].lower()}|{e['date']}"
        if key not in seen:
            seen.add(key)
            unique.append(e)

    all_events = sorted(unique, key=lambda e: (e["date"], e["time"]))

    try:
        from recommender import score_events
        all_events, threshold = score_events(all_events)
        all_events = [e for e in all_events if e.get("score", 0.5) >= threshold]
        all_events = sorted(all_events, key=lambda e: (e["date"], -e.get("score", 0.5), e["time"]))
    except Exception:
        pass  # degrade gracefully — original sort preserved

    render(all_events, weather)


if __name__ == "__main__":
    main()
