import sys
import os
from datetime import date, timedelta

# Allow running as `python src/main.py` from the project root
sys.path.insert(0, os.path.dirname(__file__))

from weather import fetch_weather
from sports import get_sports_events
from do312 import fetch_do312_events
from display import render


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

    all_events = sorted(
        sports + culture,
        key=lambda e: (e["date"], e["time"]),
    )

    render(all_events, weather)


if __name__ == "__main__":
    main()
