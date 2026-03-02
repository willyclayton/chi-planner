from datetime import date, timedelta
from events import event_emoji
from weather import format_day_summary, weather_flags

WIDTH = 50


def _fmt_time(time_str):
    """'21:00' → '9pm', '19:30' → '7:30pm'"""
    h, m = map(int, time_str.split(":"))
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{suffix}" if m else f"{h12}{suffix}"


def _event_line(event, weather, day_label=None):
    emoji = event_emoji(event)
    time_fmt = _fmt_time(event["time"])
    day = weather.get(event["date"])
    flag = weather_flags(day, event["indoor_outdoor"]) if day else ""
    price = event["price_range"]

    day_part = f"{day_label} " if day_label else ""
    return (
        f"  {emoji} {event['name']} @ {event['venue']} · "
        f"{day_part}{time_fmt} · {event['neighborhood']} · {price} {flag}"
    )


def render(events, weather):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    saturday = monday + timedelta(days=5)
    sunday = monday + timedelta(days=6)

    weekend_dates = {friday.isoformat(), saturday.isoformat(), sunday.isoformat()}

    # Days between today and the weekend (exclusive)
    later_dates = set()
    d = today + timedelta(days=1)
    while d < friday:
        later_dates.add(d.isoformat())
        d += timedelta(days=1)

    today_events = [e for e in events if e["date"] == today.isoformat()]
    weekend_events = [e for e in events if e["date"] in weekend_dates]
    later_events = [e for e in events if e["date"] in later_dates]

    # Temp range across the week
    week_highs = [w["high"] for w in weather.values()]
    temp_range = f"{min(week_highs)}–{max(week_highs)}°F" if week_highs else "N/A"

    week_label = (
        f"{monday.strftime('%a')} {monday.strftime('%b')} {monday.day}"
        f" – "
        f"{sunday.strftime('%a')} {sunday.strftime('%b')} {sunday.day}"
    )

    # ── Header ──────────────────────────────────────────
    print("═" * WIDTH)
    print(f"  CHI THIS WEEK · {week_label}")
    print(f"  📍 Chicago · 🌡️  Highs {temp_range}")
    print("═" * WIDTH)

    # ── TODAY ────────────────────────────────────────────
    print(f"\n▸ TODAY ({today.strftime('%A')})")
    today_wx = weather.get(today.isoformat())
    if today_wx:
        print(f"  {format_day_summary(today_wx)}")
    if today_events:
        for e in today_events[:7]:
            print(_event_line(e, weather))
    else:
        print("  Nothing on the radar for today.")

    # ── THIS WEEKEND ─────────────────────────────────────
    print("\n▸ THIS WEEKEND")
    wx_parts = []
    for d, lbl in [(friday, "Fri"), (saturday, "Sat"), (sunday, "Sun")]:
        w = weather.get(d.isoformat())
        if w:
            wx_parts.append(f"{lbl}: {format_day_summary(w)}")
    if wx_parts:
        print("  " + " | ".join(wx_parts))
    if weekend_events:
        for e in weekend_events[:7]:
            day_lbl = date.fromisoformat(e["date"]).strftime("%a")
            print(_event_line(e, weather, day_lbl))
    else:
        print("  Nothing lined up yet.")

    # ── LATER THIS WEEK ───────────────────────────────────
    if later_events:
        print("\n▸ LATER THIS WEEK")
        for e in later_events[:7]:
            day_lbl = date.fromisoformat(e["date"]).strftime("%a")
            print(_event_line(e, weather, day_lbl))

    print()
