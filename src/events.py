# Shared emoji helpers used by display.py and sports.py

_SPORT_EMOJIS = {
    "cubs": "⚾",
    "white sox": "⚾",
    "sox": "⚾",
    "bulls": "🏀",
    "bears": "🏈",
    "blackhawks": "🏒",
    "fire": "⚽",
}

TYPE_EMOJIS = {
    "music": "🎵",
    "comedy": "🎤",
    "food": "🍽️",
    "other": "🎟️",
}


def event_emoji(event):
    if event["type"] == "sports":
        name_lower = event["name"].lower()
        for team, emoji in _SPORT_EMOJIS.items():
            if team in name_lower:
                return emoji
        return "🏟️"
    return TYPE_EMOJIS.get(event["type"], "📅")
