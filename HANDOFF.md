# Handoff: Salafi Marriage Profile Filter

You are Claude Code, picking up an existing personal project. This document is the full briefing — read it end to end before suggesting changes.

## What this is

A local-only matrimonial profile filter for the public Telegram channel `@salafimarriage1`. The user (Anas, +91 6387073072, anas@slikr.com.au) is searching for a marriage partner and the channel has thousands of profiles posted by members. Scrolling Telegram is painful because Telegram has no filtering. This app scrapes the channel, parses each post into structured fields, and gives him a filterable UI.

It runs entirely on his Mac. No server. No data leaves the machine.

## Current state (as of handoff)

- 1,848 profiles parsed and stored in SQLite (`profiles.db`, ~13 MB)
- 5,375 total messages stored (the rest are admin chatter / non-profile posts)
- Static HTML file (`profiles.html`, ~4.5 MB) with three tabs: Browse, My Preferences, Notifications
- macOS LaunchAgent re-runs the scraper + rebuild every 5 hours

## Project layout

```
~/salafi-filter/
├── .env                          # API_ID, API_HASH, TELEGRAM_PHONE, CHANNEL
├── .venv/                        # Python virtualenv (telethon, python-dotenv)
├── requirements.txt
├── parser.py                     # Regex profile-text → structured fields
├── scrape.py                     # Telethon → SQLite, incremental
├── build_html.py                 # SQLite → profiles.html (single self-contained file)
├── update.sh                     # Wrapper: source venv, scrape, rebuild
├── com.user.salafifilter.plist   # LaunchAgent (every 5h)
├── telegram-session.session      # Telethon auth (DO NOT DELETE — it's the login)
├── profiles.db                   # The data
├── profiles.html                 # The UI (open this in any browser)
├── photos/                       # Empty unless `python scrape.py --photos` was run
└── logs/                         # update.sh + launchd output
```

## Tech stack & dependencies

- **Python 3.10+** (Mac default works, currently using `.venv` in project)
- `telethon>=1.36` — Telegram MTProto client (logs in as the user, not as a bot)
- `python-dotenv>=1.0` — `.env` loader
- **No frontend framework**. The UI is one HTML file with embedded JSON and vanilla JS. Total external deps: zero.

## Data flow

```
@salafimarriage1 (Telegram public channel)
        │  Telethon iter_messages(min_id=checkpoint)
        ▼
scrape.py  ─── parser.parse_profile(text) ───► SQLite (profiles table)
        ▼
build_html.py  ─── reads profile rows ───► profiles.html (data embedded inline)
        ▼
User opens profiles.html in their browser
```

The scraper is **incremental**: `latest_msg_id(conn)` from the DB becomes the `min_id` for the next `iter_messages` call. Re-runs are fast (only new posts are pulled). `--full` overrides the checkpoint.

## Database schema

```sql
CREATE TABLE profiles (
    msg_id          INTEGER PRIMARY KEY,
    posted_at       TEXT,            -- ISO 8601
    raw_text        TEXT,            -- the original post, untouched
    gender          TEXT,            -- 'male' | 'female' | NULL
    age             INTEGER,         -- 18..70
    marital_status  TEXT,            -- 'Never married' | 'Divorced' | 'Widowed' | 'Separated' | NULL
    children        TEXT,            -- e.g. '2 children' | 'No children' | NULL
    city            TEXT,            -- title-cased Indian city
    state           TEXT,            -- title-cased Indian state
    country         TEXT,            -- title-cased
    education       TEXT,
    profession      TEXT,
    height          TEXT,            -- e.g. "5'9\""
    looking_for     TEXT,            -- the "Looking for:" line, raw
    is_profile      INTEGER,         -- 1 if parser.is_profile_post() said yes; 0 = admin/chatter
    has_photo       INTEGER,         -- 1 if msg.photo was set
    photo_path      TEXT,            -- relative path inside ./photos/, only if --photos was used
    telegram_url    TEXT             -- https://t.me/salafimarriage1/{msg_id}
);
```

Indexes on `age`, `gender`, `city`, `country`, `is_profile`.

## Parser behaviour & known quirks

`parser.py` is regex-based. It is **deliberately conservative** — when uncertain, it returns `None` rather than guessing wrong. This means many profiles have partial fields. The UI compensates by showing the full raw text under "Show full profile text" so nothing is lost.

Things to know before changing parser:

- `extract_age` restricts itself to text *before* "Looking for" — otherwise it picks up the partner's preferred age range. We tested this: removing that cutoff regressed an early sample.
- `extract_gender` looks for `Brother`/`Sister`/etc. in the first 500 chars, with a "looking for X" inversion check (a post saying "looking for a brother" was written by a sister).
- `extract_height` requires an apostrophe or `ft`/`feet` literal — earlier we had it matching `29 years` as `2'9"`. Don't loosen that.
- `INDIAN_CITIES` and `INDIAN_STATES` are explicit allowlists. Adding cities is the right way to extend coverage; trying to do it via regex over capitalized words generates false positives.
- `is_profile_post` heuristic: `len(text) >= 80 AND has_age AND (has_role OR has_marital_status)`. This filters out admin posts but loses some real profiles that omit age. ~5,375 messages → 1,848 profiles, so ~34% acceptance rate.

## UI architecture (profiles.html)

Single HTML file. Generated by `build_html.py` which reads `profiles.db`, dumps the profile rows as JSON, and inlines them into a `<script>const DATA = [...]</script>` block. JS-side filtering is then in-memory.

**Tabs:**

1. **Browse** — sidebar of filters, paginated cards. Inputs auto-trigger re-render on `input`/`change`.
2. **My Preferences** — form that writes to `localStorage[salafi_prefs_v1]`. Shows count of profiles currently matching. "Apply to Browse tab" and "Edit preferences" cross-link.
3. **Notifications** — derived view: `DATA.filter(d => d.msg_id > localStorage[salafi_last_seen_msgid_v1] && matches(d, prefs))`. "Mark all as read" sets the watermark to `max(msg_id)`.

The `matches(profile, criteria)` function is shared between Browse filters and Preferences/Notifications, so behaviour is consistent.

**Why localStorage and not server-side state:** the user wanted simple. Static HTML opens directly from `file://` and persists across reloads. Trade-off: prefs are per-browser, not synced across devices. Acceptable for now.

## Auto-update

`com.user.salafifilter.plist` is a LaunchAgent installed at `~/Library/LaunchAgents/com.user.salafifilter.plist`. It runs `update.sh` on load and every `StartInterval=18000` seconds (5 hours). `update.sh` activates the venv, runs `scrape.py` (incremental), then `build_html.py`. Logs to `logs/launchd.log` and `logs/update-YYYYMMDD.log`.

To check status: `launchctl list | grep salafifilter`.
To unload: `launchctl unload ~/Library/LaunchAgents/com.user.salafifilter.plist`.

## Configuration

`.env` (already populated, don't ask for these unless something's broken):

```
TELEGRAM_API_ID=<numeric>
TELEGRAM_API_HASH=<32 hex>
TELEGRAM_PHONE=+91...
CHANNEL=salafimarriage1
```

Credentials came from https://my.telegram.org. The `.session` file caches the auth — first run prompted SMS code + 2FA password. Don't delete it unless you want to re-auth.

## Decisions and their reasoning

These are deliberate choices. Don't regress them without checking:

- **Static HTML over a Flask/Streamlit server.** User isn't a developer; an always-running server adds operational burden. Static file works offline, opens with double-click.
- **Telethon (user account) over Bot API.** Bot API needs admin access to the channel, which the user doesn't have. MTProto via Telethon reads any public channel.
- **Regex parsing, not LLM-based extraction.** Cost, speed, transparency. The regexes are easy to tweak when the user sees mis-parses.
- **SQLite with `is_profile=0` rows kept.** Lets us improve the heuristic later and re-classify without re-scraping. Re-scraping is ~30 min and risks FloodWait throttling.
- **Photo download is opt-in (`--photos`).** Photos are ~1800 of the 1848 profiles, would add ~hundreds of MB and hours. The Telegram-link-back is sufficient for most filtering.
- **Embed all data inline, not fetch from JSON file.** Dropbox-friendly, email-friendly, no CORS, no `file://` AJAX issues. Trade-off: HTML is 4.5 MB. Loads in <500ms in Chrome/Safari, fine.

## What the user might ask you to do next

He said "I want to implement the complex things in there." Some likely directions, with notes:

### Feature: actual macOS notifications

Right now "Notifications" is a tab. He may want OS-level alerts ("3 new profiles match your preferences"). Options:

- **`osascript -e 'display notification...'`** in `update.sh` after build. Cheapest. Read the prefs from a separate JSON file (since `update.sh` is bash, not JS), count matches in `profiles.db`, fire if > 0. Requires a small Python helper to read SQLite and apply the same `matches()` logic.
- **`terminal-notifier`** (Homebrew) — nicer UX, supports click-to-open.
- **Reading the prefs from localStorage:** can't be done from outside the browser. Either duplicate prefs into a `prefs.json` file when saved (modify `build_html.py` to expose a write path — actually impossible from `file://`, JS sandbox), OR have the user re-enter prefs in a separate config file. Simplest: have a `prefs.json` next to the project, read by both update.sh and the HTML. Switching the source-of-truth is a real change worth discussing with him.

### Feature: photo downloads

`scrape.py --photos` already exists but is opt-in per-run. Might want to make it lazy ("download photo for *this* profile when I click on the card"). Would require a small local server (Flask), or pre-download photos for profiles matching saved prefs only.

### Feature: contacted/favorited/dismissed status per profile

He'll want to mark profiles he's interested in or has reached out to. Options:

- Client-side in localStorage (simple, but lost if browser data clears)
- A separate `interactions.json` next to `profiles.db` that build_html embeds and re-emits
- A new SQLite table `interactions(msg_id, status, note, updated_at)` — survives re-scrapes naturally because `msg_id` is stable

The third option is the cleanest. It also lets `update.sh` count "new matches" excluding ones he's already dismissed.

### Feature: better parser

There's headroom. ~34% of messages are accepted as profiles; some real profiles are missed (no explicit age, or age in non-standard format like "twenty-five"). Could:

- Add an LLM fallback (Claude Haiku via API) for messages that *look* profile-shaped but failed regex extraction. Cheap (~$0.001/profile), and you can cache results in the DB.
- Add more city/state coverage (look at the `(unknown)` country bucket — 33 profiles).
- Detect WhatsApp/Telegram contact fields (some profiles include a contact channel).

### Feature: cross-channel scraping

He mentioned `salafimarriage1`. There may be sister channels. Multi-channel would mean:
- Add a `channel` column to the schema
- Loop over channels in `scrape.py`
- A channel filter in the UI

### Feature: matching score / ranking

Instead of binary match/no-match, compute a score per profile against prefs. Sort the Browse tab by relevance.

### Feature: deploy to phone

He'd want this on his phone. Options:
- Host the HTML on a private gist or local network share, open from phone browser
- Convert to a PWA (offline cache, add-to-home-screen)
- Build a real iOS/Android app (much bigger lift)

The PWA route is reasonable: same static HTML, add a manifest + service worker, host once. localStorage prefs survive.

## Things to watch out for

- **Don't bypass the venv.** The user's system Python may not have telethon. Always: `source .venv/bin/activate && python3 ...` or use the venv's python directly: `.venv/bin/python`.
- **FloodWait.** Telegram throttles aggressive scraping. The current `scrape.py` has a `FloodWaitError` retry loop. Don't paralellise message fetching.
- **Don't print the api_hash or .session file contents.** Treat them as secrets.
- **Don't `git init` and push to a public repo.** `.env` and the `.session` file are sensitive.
- **The user is non-technical.** He'll trust you on Terminal commands. Double-check anything destructive (`rm -rf`, `launchctl unload` of unrelated services, etc.).

## How to run things

```bash
# Activate venv (every new shell)
cd ~/salafi-filter && source .venv/bin/activate

# Manual incremental scrape + rebuild
./update.sh

# Full re-scrape (ignores checkpoint)
python3 scrape.py --full && python3 build_html.py

# With photos
python3 scrape.py --photos && python3 build_html.py

# Inspect the DB
sqlite3 profiles.db
> SELECT COUNT(*), gender FROM profiles WHERE is_profile=1 GROUP BY gender;

# Watch the auto-update logs
tail -f logs/launchd.log
```

## First thing to do when he gives you a task

1. Read this file (you're doing it).
2. `ls -la ~/salafi-filter/` to confirm current state.
3. `sqlite3 ~/salafi-filter/profiles.db ".schema profiles"` to verify the schema matches this doc (in case it's drifted).
4. Open `~/salafi-filter/profiles.html` in a browser to see what the UI currently looks like before you change it.
5. *Then* propose the change.

Good luck.
