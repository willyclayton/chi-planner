# Chi This Week 🏙️

A personal "what should I do in Chicago this week?" dashboard. Curated to your tastes, weather-aware, and designed to be scannable in 10 seconds.

## Why
Sites like do312.com show everything. This shows only what matters to you.

## Skills
This project uses Claude Code skills (in `.claude/skills/` or `skills/`) to guide AI-assisted development:

| Skill | Purpose |
|-------|---------|
| `user-profile.md` | Your tastes, preferences, dealbreakers |
| `weather-aware.md` | Outdoor event flagging using Open-Meteo API |
| `event-sourcing.md` | Where events come from, data structure, filtering |
| `calm-ui.md` | Anti-overwhelm design principles |

## Phases

### Phase 1 — CLI + Weather (start here)
- Fetch real Chicago weather for the week
- Display hardcoded sample events with weather flags
- Prove the skeleton works

### Phase 2 — Real Sports Data
- Pull actual Chicago team schedules
- Auto-flag outdoor games with weather

### Phase 3 — Real Events
- Pull music/comedy events from APIs or scraping
- Apply user-profile filters

### Phase 4 — Web UI
- Move from CLI to a simple web dashboard
- Follow calm-ui.md design principles
- Mobile-friendly, dark mode

## Setup
```bash
# Phase 1
cd chi-this-week
python src/main.py
```

## Tech
- Python (CLI phases)
- Open-Meteo API (weather, free, no key)
- React or simple HTML (web phase)
