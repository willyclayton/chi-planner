import urllib.request
import json

CHICAGO_LAT = 41.931593
CHICAGO_LON = -87.648249

SNOW_CODES = {71, 73, 75, 77, 85, 86}

WMO_DESCRIPTIONS = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    77: "snow grains",
    80: "showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm",
}


def fetch_weather():
    """Fetch 7-day Chicago forecast from Open-Meteo. Returns {date_str: day_dict}."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={CHICAGO_LAT}&longitude={CHICAGO_LON}"
        "&daily=temperature_2m_max,temperature_2m_min"
        ",precipitation_probability_max,windspeed_10m_max,weathercode"
        "&temperature_unit=fahrenheit"
        "&windspeed_unit=mph"
        "&timezone=America%2FChicago"
        "&forecast_days=7"
    )
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())

    daily = data["daily"]
    # Handle both old (weathercode) and new (weather_code) API naming
    code_key = "weathercode" if "weathercode" in daily else "weather_code"

    forecast = {}
    for i, date_str in enumerate(daily["time"]):
        forecast[date_str] = {
            "high": round(daily["temperature_2m_max"][i]),
            "low": round(daily["temperature_2m_min"][i]),
            "precip_prob": daily["precipitation_probability_max"][i] or 0,
            "wind_speed": round(daily["windspeed_10m_max"][i]),
            "weather_code": daily[code_key][i],
        }
    return forecast


def weather_flags(day, indoor_outdoor):
    """Return weather flag emojis. Indoor events always get ✅."""
    if indoor_outdoor == "indoor":
        return "✅"

    flags = []
    if day["weather_code"] in SNOW_CODES:
        flags.append("❄️")
    if day["precip_prob"] > 40:
        flags.append("🌧️")
    if day["high"] < 30:
        flags.append("🥶")
    if day["wind_speed"] > 20:
        flags.append("💨")
    return " ".join(flags) if flags else "✅"


def format_day_summary(day):
    """e.g. '45°F, partly cloudy, 20% rain ✅'"""
    desc = WMO_DESCRIPTIONS.get(day["weather_code"], "cloudy")
    precip = f", {day['precip_prob']}% rain" if day["precip_prob"] > 0 else ""
    flag = weather_flags(day, "outdoor")
    return f"{day['high']}°F, {desc}{precip} {flag}"
