# Event Sourcing

## Event Categories
1. **Sports** — Chicago home games (Top: Cubs,Blackhawks Others: Sox, Bulls, Bears,  Fire)
2. **Music** — concerts, live shows at local venues
3. **Comedy** — standup, improv, touring acts
4. **Food/Drink** — new openings, pop-ups, food events
5. **Other** — festivals (I love street festivals!), markets, free events, exhibits worth knowing about

## Data Structure
Every event should be normalized to this format:
```json
{
  "name": "String — event/artist/team name",
  "type": "sports | music | comedy | food | other",
  "date": "YYYY-MM-DD",
  "time": "HH:MM (24hr)",
  "venue": "Venue name",
  "neighborhood": "e.g. Wrigleyville, Lincoln Park, West Loop",
  "indoor_outdoor": "indoor | outdoor | mixed",
  "price_range": "free | $ | $$ | $$$",
  "url": "Link to tickets or info",
  "description": "One sentence max"
}
```

## Sources (phased approach)

### Phase 1 — Hardcoded / Manual
- Seed with sample events to build the UI and filtering logic
- Use realistic data so the app feels real during development

### Phase 2 — Real APIs
- **Sports schedules**: Free tier of ESPN API, or scrape Chicago team schedule pages
- **Weather**: Open-Meteo (already covered in weather-aware skill)

### Phase 3 — Scraping / Advanced APIs
- **do312.com**: Scrape event listings (respect robots.txt)
- **Songkick / Bandsintown**: Music event APIs (free tiers available)
- **Yelp Fusion API**: Restaurant openings and trending spots
- **Second City / iO websites**: Comedy schedules

## Filtering Rules
- Apply user-profile.md preferences BEFORE displaying
- Sports: Prioritize Cubs, then other Chicago teams. Deprioritize Sox.
- Music: Filter by genre preferences. Skip EDM/electronic.
- Price: Flag anything that would blow past the $50-100 budget
- Location: City only, no suburbs. Bonus points for CTA-accessible.

## Freshness
- Events should be for the current week (Mon–Sun)
- Past events should be auto-removed
- "This weekend" = Friday 5pm through Sunday
