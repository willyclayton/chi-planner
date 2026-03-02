# Weather-Aware Recommendations

## Data Source
- Use the Open-Meteo API (free, no API key required)
- Base URL: https://api.open-meteo.com/v1/forecast
- Geocoding: 41.931593 °N, -87.648249 °W
- Fetch: daily high/low temp, precipitation probability, wind speed, weather code

## Weather Flags
For ANY outdoor or partially outdoor event, check conditions and apply flags:

| Condition | Threshold | Flag | Action |
|-----------|-----------|------|--------|
| Rain likely | Precip prob > 40% | 🌧️ | Warn user |
| Snow likely | Weather code = snow | ❄️ | Warn user |
| Bitter cold | High temp < 30°F | 🥶 | Warn user |
| Very windy | Wind > 20mph | 💨 | Warn for lakefront/outdoor |
| Clear/safe | None of the above | ✅ | Good to go |

## Rules
- Indoor events are ALWAYS safe — mark with ✅ and no weather note
- Outdoor events with warnings should NOT be excluded — just flagged clearly
- If multiple weather warnings apply, show all flags
- Include a single weather summary line at the top of the daily view:
  Example: "Saturday: 45°F, partly cloudy, 20% rain ✅"
- Use Fahrenheit (this is Chicago)

## Caching
- Fetch weather once per run, not per event
- Store the week forecast and look up per-event-date