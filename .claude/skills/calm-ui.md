# Calm UI — The Anti-Overwhelm Design Skill

## Core Philosophy
This app exists because do312.com and similar sites show EVERYTHING. We show only what matters to Will. The goal: open the app, scan for 10 seconds, know what's worth doing. That's it.

## The 5-7 Rule
- Show a MAXIMUM of 5–7 recommendations per time block
- Time blocks: TODAY | THIS WEEKEND | LATER THIS WEEK
- If there are 30 events that match, YOU pick the best 5–7. That's the whole point.
- Curating is a feature, not a bug.

## Information Hierarchy
Each event gets ONE line in the default view:
```
🎵 Wilco @ Lincoln Hall · Fri 8pm · Lincoln Park · $$ ✅
```
Format: `[type emoji] [name] @ [venue] · [day] [time] · [neighborhood] · [price] [weather flag]`

### Type Emojis
- ⚾🏀🏈🏒⚽ — Sports (use sport-specific)
- 🎵 — Music
- 🎤 — Comedy
- 🍽️ — Food/Drink
- 🎟️ — Other events

## Expand on Demand
- Default: one-line view only
- Click/select to expand: description, link, transit directions
- Never show expanded detail by default

## Layout Rules (CLI Phase)
```
═══════════════════════════════════════
  CHI THIS WEEK · Mon Mar 2 – Sun Mar 8
  📍 Chicago · 🌡️ Highs 35–48°F
═══════════════════════════════════════

▸ TODAY (Monday)
  Light snow, 35°F
  🎤 Stand-up Open Mic @ Lincoln Lodge · 8pm · Lincoln Square · $ ✅

▸ THIS WEEKEND
  Fri: 45°F, clear ✅ | Sat: 42°F, 60% rain 🌧️ | Sun: 38°F, cloudy ✅

  🎵 Jason Isbell @ Thalia Hall · Fri 9pm · Pilsen · $$ ✅
  ⚾ Cubs vs Brewers · Sat 1:20pm · Wrigleyville · $$ 🌧️
  🎤 Nate Bargatze @ Chicago Theatre · Sat 7pm · Loop · $$$ ✅
  🍽️ New: Birrieria Zaragoza pop-up · Sun 11am · Archer Heights · $ ✅

▸ LATER THIS WEEK
  🏀 Bulls vs Celtics · Wed 7pm · West Loop · $$ ✅
  🎵 Turnpike Troubadours @ Riviera · Thu 8pm · Uptown · $$ ✅
```

## Layout Rules (Web Phase)
- Card-based, max 2–3 cards per row
- Muted colors, lots of white space
- No infinite scroll — everything fits on one screen
- Dark mode friendly
- Mobile-first (Will's probably checking this on his phone)

## Tone
- Casual, like a friend texting you recommendations
- No marketing language, no "Don't miss!" hype
- If nothing good is happening, say so: "Quiet week — save your money 💤"

## Anti-Patterns (NEVER do these)
- ❌ Show every event in the city
- ❌ Wall of text descriptions
- ❌ Require scrolling to see all recommendations
- ❌ Use corporate/formal tone
- ❌ Auto-play anything
- ❌ Require signup or login
- ❌ Ads or sponsored content vibes
