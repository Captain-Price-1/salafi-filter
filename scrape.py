"""
Scrape messages from a public Telegram channel into a local SQLite DB.

First run    : pulls the entire channel history (slow, 15-30 min for ~10k posts).
Subsequent   : only fetches messages newer than what's already in the DB.

Usage:
    python scrape.py              # incremental, no photos
    python scrape.py --photos     # also download photos for parsed profiles
    python scrape.py --full       # ignore checkpoint, re-scrape everything
"""

from __future__ import annotations
import argparse
import asyncio
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError

import parser as profile_parser

load_dotenv()

API_ID    = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH  = os.getenv("TELEGRAM_API_HASH", "")
PHONE     = os.getenv("TELEGRAM_PHONE", "")
CHANNEL   = os.getenv("CHANNEL", "salafimarriage1")

ROOT     = Path(__file__).parent
DB_PATH  = ROOT / "profiles.db"
PHOTO_DIR = ROOT / "photos"
SESSION  = ROOT / "telegram-session"


SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    channel         TEXT NOT NULL DEFAULT 'salafimarriage1',
    msg_id          INTEGER NOT NULL,
    posted_at       TEXT,
    raw_text        TEXT,
    gender          TEXT,
    age             INTEGER,
    marital_status  TEXT,
    children        TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    education       TEXT,
    profession      TEXT,
    height          TEXT,
    looking_for     TEXT,
    is_profile      INTEGER,
    has_photo       INTEGER,
    photo_path      TEXT,
    telegram_url    TEXT,
    PRIMARY KEY (channel, msg_id)
);
CREATE INDEX IF NOT EXISTS idx_age      ON profiles(age);
CREATE INDEX IF NOT EXISTS idx_gender   ON profiles(gender);
CREATE INDEX IF NOT EXISTS idx_city     ON profiles(city);
CREATE INDEX IF NOT EXISTS idx_country  ON profiles(country);
CREATE INDEX IF NOT EXISTS idx_profile  ON profiles(is_profile);
CREATE INDEX IF NOT EXISTS idx_channel  ON profiles(channel);
"""


def _migrate_to_multichannel(conn: sqlite3.Connection) -> None:
    """One-time migration: add `channel` column + composite PK to existing DBs."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(profiles)").fetchall()]
    if not cols or "channel" in cols:
        return
    print("Migrating DB: adding `channel` column and composite PK...")
    conn.executescript("""
    BEGIN;
    CREATE TABLE profiles_new (
        channel         TEXT NOT NULL DEFAULT 'salafimarriage1',
        msg_id          INTEGER NOT NULL,
        posted_at       TEXT,
        raw_text        TEXT,
        gender          TEXT,
        age             INTEGER,
        marital_status  TEXT,
        children        TEXT,
        city            TEXT,
        state           TEXT,
        country         TEXT,
        education       TEXT,
        profession      TEXT,
        height          TEXT,
        looking_for     TEXT,
        is_profile      INTEGER,
        has_photo       INTEGER,
        photo_path      TEXT,
        telegram_url    TEXT,
        PRIMARY KEY (channel, msg_id)
    );
    INSERT INTO profiles_new
        SELECT 'salafimarriage1' AS channel, msg_id, posted_at, raw_text, gender, age,
               marital_status, children, city, state, country, education, profession,
               height, looking_for, is_profile, has_photo, photo_path, telegram_url
        FROM profiles;
    DROP TABLE profiles;
    ALTER TABLE profiles_new RENAME TO profiles;
    COMMIT;
    """)
    print("Migration complete.")


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    # Migrate first (in case of existing single-channel DB), then apply current schema.
    _migrate_to_multichannel(conn)
    conn.executescript(SCHEMA)
    return conn


def latest_msg_id(conn, channel: str) -> int:
    row = conn.execute("SELECT MAX(msg_id) FROM profiles WHERE channel=?", (channel,)).fetchone()
    return row[0] or 0


def upsert(conn, row: dict):
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    conn.execute(
        f"INSERT OR REPLACE INTO profiles ({cols}) VALUES ({placeholders})",
        tuple(row.values()),
    )


async def run(download_photos: bool, full_rescrape: bool):
    if not API_ID or not API_HASH:
        raise SystemExit(
            "Missing TELEGRAM_API_ID / TELEGRAM_API_HASH. "
            "Copy .env.example to .env and fill it in."
        )

    PHOTO_DIR.mkdir(exist_ok=True)
    conn = connect_db()

    # CHANNEL env var supports a comma-separated list for multi-channel scraping.
    channels = [c.strip().lstrip("@") for c in CHANNEL.split(",") if c.strip()]
    print(f"Channels   : {', '.join('@' + c for c in channels)}")
    print(f"DB         : {DB_PATH}")
    print()

    async with TelegramClient(str(SESSION), API_ID, API_HASH) as client:
        await client.start(phone=PHONE)

        for channel in channels:
            entity = await client.get_entity(channel)
            checkpoint = 0 if full_rescrape else latest_msg_id(conn, channel)
            print(f"--- @{channel} ---")
            print(f"Checkpoint : msg_id > {checkpoint}" if checkpoint else "Checkpoint : none (full scrape)")

            seen = 0
            added = 0
            skipped_non_profile = 0

            async for msg in client.iter_messages(entity, min_id=checkpoint):
                seen += 1
                text = msg.text or ""
                parsed = profile_parser.parse_profile(text)
                is_profile = profile_parser.is_profile_post(text)

                photo_path = None
                if is_profile and download_photos and msg.photo:
                    try:
                        photo_path = await msg.download_media(
                            file=str(PHOTO_DIR / f"{channel}_{msg.id}.jpg")
                        )
                        photo_path = str(Path(photo_path).relative_to(ROOT))
                    except Exception as e:
                        print(f"  photo download failed for {channel}/{msg.id}: {e}")

                row = {
                    "channel":        channel,
                    "msg_id":         msg.id,
                    "posted_at":      msg.date.isoformat() if msg.date else None,
                    "raw_text":       text,
                    "is_profile":     1 if is_profile else 0,
                    "has_photo":      1 if msg.photo else 0,
                    "photo_path":     photo_path,
                    "telegram_url":   f"https://t.me/{channel}/{msg.id}",
                    **parsed,
                }
                upsert(conn, row)

                if is_profile:
                    added += 1
                else:
                    skipped_non_profile += 1

                if seen % 100 == 0:
                    conn.commit()
                    print(f"  ..processed {seen} messages ({added} profiles, {skipped_non_profile} non-profile)")

            conn.commit()
            print(f"Done @{channel}. Processed {seen} messages, {added} profiles, {skipped_non_profile} non-profile.")
            print()

        total = conn.execute("SELECT COUNT(*) FROM profiles WHERE is_profile=1").fetchone()[0]
        per_ch = conn.execute("SELECT channel, COUNT(*) FROM profiles WHERE is_profile=1 GROUP BY channel").fetchall()
        print(f"Total profiles in DB: {total}")
        for ch, n in per_ch:
            print(f"  @{ch}: {n}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", action="store_true", help="Download photos for parsed profiles")
    ap.add_argument("--full",   action="store_true", help="Ignore checkpoint, re-scrape everything")
    args = ap.parse_args()

    while True:
        try:
            asyncio.run(run(args.photos, args.full))
            break
        except FloodWaitError as e:
            print(f"Telegram asked us to wait {e.seconds}s — sleeping then resuming.")
            import time; time.sleep(e.seconds + 5)


if __name__ == "__main__":
    main()
