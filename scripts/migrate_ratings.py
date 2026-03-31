"""
One-time migration: seed events.db from data/ratings.json.

Reads the 61 rated events, inserts into events + tags + ratings tables.

Usage:  python scripts/migrate_ratings.py
"""
import json
import os
import sys

# Add src/ to path for db module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from db import event_id, extract_tags, _get_conn, DB_FILE, DATA_DIR

RATINGS_JSON = os.path.join(DATA_DIR, "ratings.json")


def migrate():
    if not os.path.exists(RATINGS_JSON):
        print(f"ERROR: {RATINGS_JSON} not found")
        sys.exit(1)

    with open(RATINGS_JSON) as f:
        entries = json.loads(f.read())

    print(f"Loaded {len(entries)} rated events from ratings.json")

    # Remove old DB to start fresh
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed old {DB_FILE}")

    conn = _get_conn()

    events_inserted = 0
    ratings_inserted = 0
    tags_inserted = 0

    for entry in entries:
        event = entry["event"]
        rating = entry["rating"]
        rated_at = entry.get("rated_at", "")

        eid = event_id(event)

        # Insert event
        conn.execute("""
            INSERT OR REPLACE INTO events
            (event_id, name, type, date, time, venue, neighborhood,
             indoor_outdoor, price_range, url, description,
             source, first_seen, last_seen, score, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eid, event.get("name"), event.get("type"), event.get("date"),
            event.get("time"), event.get("venue"), event.get("neighborhood"),
            event.get("indoor_outdoor"), event.get("price_range"),
            event.get("url"), event.get("description", ""),
            "ratings.json", rated_at, rated_at, None, json.dumps(event),
        ))
        events_inserted += 1

        # Insert rating
        conn.execute("""
            INSERT OR REPLACE INTO ratings (event_id, rating, rated_at)
            VALUES (?, ?, ?)
        """, (eid, rating, rated_at))
        ratings_inserted += 1

        # Insert tags
        tags = extract_tags(event)
        conn.execute("DELETE FROM tags WHERE event_id = ?", (eid,))
        for tag_type, tag_value in tags:
            conn.execute(
                "INSERT INTO tags (event_id, tag_type, tag_value) VALUES (?, ?, ?)",
                (eid, tag_type, tag_value),
            )
            tags_inserted += 1

    conn.commit()
    conn.close()

    print(f"Migration complete:")
    print(f"  {events_inserted} events")
    print(f"  {ratings_inserted} ratings")
    print(f"  {tags_inserted} tags")
    print(f"  DB: {DB_FILE}")


if __name__ == "__main__":
    migrate()
