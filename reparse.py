"""Re-run the parser on every row's raw_text and update parsed fields in place.

No re-scraping. Use after parser.py changes to back-fill the DB without
re-pulling messages from Telegram (which would risk FloodWait).
"""
import sqlite3
from pathlib import Path
import parser as profile_parser

DB = Path(__file__).parent / "profiles.db"

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT msg_id, raw_text, is_profile FROM profiles").fetchall()
    print(f"Re-parsing {len(rows)} rows...")

    flipped_to_profile = 0
    flipped_to_nonprofile = 0
    updated = 0

    for msg_id, raw_text, old_is_profile in rows:
        text = raw_text or ""
        parsed = profile_parser.parse_profile(text)
        new_is_profile = 1 if profile_parser.is_profile_post(text) else 0

        conn.execute(
            """UPDATE profiles SET
                gender=?, age=?, marital_status=?, children=?,
                city=?, state=?, country=?, education=?, profession=?,
                height=?, looking_for=?, is_profile=?
               WHERE msg_id=?""",
            (
                parsed.get("gender"), parsed.get("age"),
                parsed.get("marital_status"), parsed.get("children"),
                parsed.get("city"), parsed.get("state"), parsed.get("country"),
                parsed.get("education"), parsed.get("profession"),
                parsed.get("height"), parsed.get("looking_for"),
                new_is_profile, msg_id,
            ),
        )
        updated += 1

        if old_is_profile == 0 and new_is_profile == 1:
            flipped_to_profile += 1
        elif old_is_profile == 1 and new_is_profile == 0:
            flipped_to_nonprofile += 1

    conn.commit()
    total_profiles = conn.execute("SELECT COUNT(*) FROM profiles WHERE is_profile=1").fetchone()[0]
    print(f"Updated {updated} rows.")
    print(f"  newly classified as profile : {flipped_to_profile}")
    print(f"  reclassified as non-profile : {flipped_to_nonprofile}")
    print(f"  total profiles now          : {total_profiles}")

if __name__ == "__main__":
    main()
