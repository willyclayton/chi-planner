# Chi This Week

A personal Chicago weekly events dashboard. Curated, weather-aware, not overwhelming.

## What This Project Does
Shows Will what's worth doing in Chicago this week — sports, music, comedy, food — filtered to his tastes, flagged for weather, and displayed so he can scan it in 10 seconds.

## Skills
Read these before building anything:
- `skills/user-profile.md` — Will's preferences, dealbreakers, and context. Every recommendation filters through this.
- `skills/weather-aware.md` — How to fetch and apply weather data. Outdoor events get flagged.
- `skills/event-sourcing.md` — Where events come from, data format, filtering rules.
- `skills/calm-ui.md` — Design principles. Max 5-7 events per time block. One-line default view. No walls of text.

## Current Phase
Phase 1 — CLI with real weather + hardcoded sample events.

## Tech Decisions
- Python for CLI phases
- Open-Meteo API for weather (free, no key)
- All source files in `src/`
- No external dependencies unless absolutely necessary (use stdlib where possible)
- Fahrenheit, not Celsius

## Code Style
- Keep it simple. This is a personal tool, not enterprise software.
- Functions should do one thing.
- No classes unless they genuinely help.
- Comments only where something isn't obvious.

## Key Rules
- ALWAYS check skills/ before implementing a feature
- ALWAYS apply user-profile.md filters before displaying events
- NEVER show more than 7 events per time block
- NEVER skip weather flags on outdoor events
- Output should match the format in calm-ui.md
