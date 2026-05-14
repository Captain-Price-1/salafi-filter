"""Build the deployable HTML shell + per-channel JSON data files.

Output:
  profiles.html               (local copy — same shell as deployed)
  public/index.html           (deployed shell)
  public/data/<channel>.json  (one file per channel, fetched on demand by the shell)

Why split: keeps the HTML small (~50 KB) so the page is interactive immediately,
and the per-channel data is fetched only when the user opens that channel.
A new `build_id` query param on every build forces fresh data without manual reloads.
"""
import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
DB = ROOT / "profiles.db"
OUT_LOCAL = ROOT / "profiles.html"
PUBLIC = ROOT / "public"
DATA_DIR = PUBLIC / "data"

# Note: dropped 'children', 'has_photo', 'photo_path' — UI no longer surfaces them.
SELECT = ("SELECT channel, msg_id, posted_at, raw_text, gender, age, marital_status, "
          "city, state, country, education, profession, height, looking_for, "
          "telegram_url FROM profiles WHERE is_profile=1 ORDER BY channel, msg_id DESC")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
all_rows = [dict(r) for r in conn.execute(SELECT)]
conn.close()

by_channel = {}
for r in all_rows:
    if r["raw_text"]:
        r["raw_text"] = r["raw_text"].strip()
    by_channel.setdefault(r["channel"], []).append(r)

CHANNEL_LABELS = [
    ("salafimarriage1",  "Salafi Marriage"),
    ("salafizawj_nikah", "Zawaj Nikah"),
]
channels_meta = []
for cid, label in CHANNEL_LABELS:
    rows = by_channel.get(cid)
    if rows:
        channels_meta.append({
            "id": cid, "label": label, "count": len(rows),
            "data_url": f"data/{cid}.json",
        })
known = {cid for cid, _ in CHANNEL_LABELS}
for cid, rows in by_channel.items():
    if cid not in known:
        channels_meta.append({
            "id": cid, "label": "@" + cid, "count": len(rows),
            "data_url": f"data/{cid}.json",
        })

PUBLIC.mkdir(exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
for ch in channels_meta:
    rows = by_channel[ch["id"]]
    txt = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    (DATA_DIR / f"{ch['id']}.json").write_text(txt, encoding="utf-8")
    print(f"  data/{ch['id']}.json: {len(rows):,} profiles, {len(txt)//1024:,} KB")

build_id = str(int(time.time()))
# ISO 8601 timestamp — formatted client-side in user's local timezone with AM/PM.
generated_at = datetime.now().isoformat(timespec="seconds")
total_profiles = sum(c["count"] for c in channels_meta)
channels_json = json.dumps(channels_meta, ensure_ascii=False)
print(f"Total: {total_profiles:,} profiles across {len(channels_meta)} channels (build {build_id})")

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Salafi Match — Profile Filter</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0F4C3A">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#F8F4ED;
  --panel:#FFFFFF;
  --panel-soft:#FCFAF5;
  --ink:#1A2620;
  --ink-soft:#3F4F47;
  --muted:#7E8A85;
  --muted-soft:#B5BEB9;
  --accent:#0F4C3A;
  --accent-hover:#0B3A2D;
  --accent-soft:#E5EFE9;
  --accent-pale:#F0F6F1;
  --gold:#B58B4A;
  --gold-soft:#F5EBD9;
  --border:#E8DFCC;
  --border-soft:#F2EAD6;
  --shadow-sm:0 1px 2px rgba(20,40,30,.04);
  --shadow:0 2px 8px rgba(20,40,30,.06);
  --shadow-lg:0 8px 24px rgba(20,40,30,.10);
  --shadow-xl:0 24px 48px rgba(20,40,30,.18);
  --warn:#B45309;
  --warn-soft:#FEF3C7;
  --radius:14px;
  --radius-sm:10px;
  --radius-xs:7px;
  --t:160ms ease;
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  font:15px/1.55 'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  background:var(--bg);color:var(--ink);
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
}
a{color:var(--accent)}

/* ---------- Header / brand ---------- */
header{
  background:var(--panel);
  border-bottom:1px solid var(--border);
  padding:22px 32px 0;
  position:sticky;top:0;z-index:30;
}
.titlebar{display:flex;flex-direction:column;align-items:flex-start;gap:6px}
.brand{
  margin:0;display:flex;align-items:center;gap:14px;
  font:700 30px/1 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.018em;
}
.brand-mark{
  display:inline-flex;align-items:center;color:var(--accent);
  filter:drop-shadow(0 1px 2px rgba(15,76,58,.12));
}
.brand-text{
  background:linear-gradient(120deg, var(--accent) 0%, #1A6B53 60%, #0F4C3A 100%);
  -webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;color:transparent;
}
.tagline{
  font:italic 400 13.5px/1.4 'Playfair Display',Georgia,serif;
  color:var(--muted);letter-spacing:.005em;
}
header .meta{
  color:var(--muted);font-size:13px;font-weight:400;
  margin-top:6px;display:flex;flex-wrap:wrap;gap:6px 14px;
}
header .meta strong{color:var(--ink);font-weight:600}
header .meta .dot{width:3px;height:3px;background:var(--muted-soft);border-radius:50%;align-self:center}
header .meta .ch-source{color:var(--accent);font-weight:500}

/* ---------- Channel switcher ---------- */
.channel-switch{
  display:inline-flex;background:var(--bg);
  border:1px solid var(--border);border-radius:999px;
  padding:4px;margin-top:14px;gap:2px;
  box-shadow:var(--shadow-sm);
}
.channel-switch button{
  background:none;border:none;cursor:pointer;
  padding:8px 16px;border-radius:999px;
  font:600 12.5px/1 'Inter',sans-serif;
  color:var(--muted);letter-spacing:.01em;
  transition:all var(--t);
  display:inline-flex;align-items:center;gap:7px;
}
.channel-switch button:hover{color:var(--ink)}
.channel-switch button.active{
  background:var(--accent);color:#fff;
  box-shadow:0 1px 3px rgba(15,76,58,.18);
}
.channel-switch .ch-count{
  display:inline-block;
  background:rgba(255,255,255,.18);
  color:inherit;opacity:.85;
  padding:1px 7px;border-radius:999px;
  font-size:10.5px;font-weight:700;line-height:1.4;
}
.channel-switch button:not(.active) .ch-count{
  background:var(--accent-soft);color:var(--accent);opacity:1;
}

/* ---------- Tabs ---------- */
nav.tabs{display:flex;gap:2px;margin-top:14px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.tab{
  background:none;border:none;padding:11px 18px 13px;
  font:500 14px/1 'Inter',sans-serif;color:var(--muted);
  cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;
  transition:color var(--t),border-color var(--t);
  display:inline-flex;align-items:center;gap:6px;
}
.tab:hover:not(.disabled){color:var(--ink)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab.disabled{color:var(--muted-soft);cursor:pointer}
.tab.disabled:hover{color:var(--muted)}
.tab .badge{
  display:inline-block;background:#9C3D1A;color:#fff;
  border-radius:999px;padding:2px 8px;
  font:700 11px/1.4 'Inter',sans-serif;
  margin-left:6px;line-height:1.4;vertical-align:middle;
}
.tab .badge.zero{display:none}
.tab .soon{
  display:inline-block;background:var(--gold-soft);color:#8C6B36;
  padding:2px 7px;border-radius:999px;font-size:9.5px;font-weight:700;
  text-transform:uppercase;letter-spacing:.07em;line-height:1.3;
}

/* ---------- Layout ---------- */
.tab-section{display:none;padding:26px 32px;max-width:1320px;margin:0 auto}
.tab-section.active{display:block;animation:fadeIn 240ms ease-out}
.layout{display:grid;grid-template-columns:300px 1fr;gap:28px;align-items:flex-start}

/* ---------- Aside (filters) ---------- */
aside{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:22px;
  position:sticky;top:188px;
  max-height:calc(100vh - 208px);
  overflow-y:auto;overflow-x:hidden;
  box-shadow:var(--shadow-sm);
  min-width:0;
}
aside h3{
  font:600 11px/1 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);margin:18px 0 10px;
  display:flex;align-items:center;gap:8px;
}
aside h3:first-of-type{margin-top:0}
aside h3::after{content:"";flex:1;height:1px;background:var(--border-soft)}
aside .field-help{
  font:400 11.5px/1.4 'Inter',sans-serif;color:var(--muted);
  margin:9px 2px 6px;
}
aside label{display:block;margin:4px 0;font-size:13px;color:var(--ink-soft)}
aside input[type=text],aside input[type=number],aside input[type=date],aside select{
  width:100%;padding:9px 11px;
  border:1px solid var(--border);border-radius:var(--radius-xs);
  font:14px/1.2 'Inter',sans-serif;
  background:#fff;color:var(--ink);
  transition:border-color var(--t),box-shadow var(--t);
}
aside input::placeholder{color:var(--muted-soft)}
aside input:focus,aside select:focus{
  outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-soft);
}
aside select[multiple]{padding:6px;min-height:140px}
aside select[multiple] option{padding:6px 8px;border-radius:4px;font-size:13px}
aside select[multiple] option:checked{background:var(--accent-soft);color:var(--accent);font-weight:500}

/* Single-select dropdown — clean appearance with custom caret */
select.single-dd,
.pf-field select.single-dd{
  appearance:none;-webkit-appearance:none;-moz-appearance:none;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path d='M1 1l5 5 5-5' fill='none' stroke='%237E8A85' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat:no-repeat;
  background-position:right 12px center;
  background-size:11px;
  padding-right:34px;
  cursor:pointer;
}
select.single-dd:hover{border-color:var(--accent)}
select.single-dd:focus{
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path d='M1 1l5 5 5-5' fill='none' stroke='%230F4C3A' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}
/* Style the placeholder option (value="") distinctly */
select.single-dd option[value=""]{color:var(--muted-soft)}
select.single-dd option{color:var(--ink);padding:6px 4px}
.range{display:flex;gap:8px;align-items:center;min-width:0}
.range input{width:0;flex:1;min-width:0;text-align:center}
.range input[type=date]{padding:8px 6px;font-size:13px}
.range span{color:var(--muted-soft);font-size:14px;flex-shrink:0}
.date-presets{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
.date-presets button{
  background:var(--bg);border:1px solid var(--border);
  padding:5px 10px;border-radius:999px;cursor:pointer;
  font:500 11.5px/1 'Inter',sans-serif;color:var(--ink-soft);
  transition:all var(--t);
}
.date-presets button:hover{background:var(--accent-pale);color:var(--accent);border-color:#C4DECC}
.date-presets button.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.checkrow{
  display:flex;align-items:center;gap:9px;
  margin:6px 0;font-size:14px;color:var(--ink-soft);
  cursor:pointer;padding:2px 0;
}
.checkrow input[type=checkbox]{
  width:16px;height:16px;margin:0;
  accent-color:var(--accent);cursor:pointer;flex-shrink:0;
}
.checkrow:hover{color:var(--ink)}
aside .filter-actions{
  margin-top:20px;padding-top:16px;
  border-top:1px solid var(--border-soft);
  display:flex;flex-direction:column;gap:8px;
}

/* ---------- Buttons ---------- */
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:7px;
  padding:9px 16px;border:1px solid var(--border);border-radius:var(--radius-xs);
  background:var(--panel);cursor:pointer;
  font:500 14px/1 'Inter',sans-serif;
  color:var(--ink);text-decoration:none;
  transition:all var(--t);min-height:38px;white-space:nowrap;
}
.btn:hover{background:var(--accent-pale);border-color:#C9DDD0;color:var(--accent)}
.btn:active{transform:translateY(1px)}
.btn.primary{background:var(--accent);color:#fff;border-color:var(--accent);box-shadow:var(--shadow-sm)}
.btn.primary:hover{background:var(--accent-hover);color:#fff;border-color:var(--accent-hover)}
.btn.ghost{background:transparent;border-color:transparent}
.btn.ghost:hover{background:var(--accent-pale);border-color:transparent}

/* ---------- Top bar (filter trigger + count + csv) ---------- */
.topbar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px}
.summary{color:var(--muted);font-size:13px}
.summary strong{color:var(--ink);font-size:16px;font-weight:600;font-family:'Playfair Display',Georgia,serif}

/* ---------- Card ---------- */
.card{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:18px 20px;margin-bottom:14px;
  box-shadow:var(--shadow-sm);
  transition:box-shadow var(--t),transform var(--t),border-color var(--t);
  position:relative;
  animation:cardIn 320ms ease-out backwards;
}
.card:hover{box-shadow:var(--shadow);transform:translateY(-1px);border-color:#D9D0BC}
.card .card-header{
  display:flex;justify-content:space-between;align-items:center;
  flex-wrap:wrap;gap:8px 12px;margin-bottom:12px;
}
.profile-code{
  display:inline-flex;align-items:baseline;gap:6px;
  font:500 11.5px/1.4 'Inter',sans-serif;
  color:var(--muted);letter-spacing:.04em;
}
.profile-code .pc-label{text-transform:uppercase;font-weight:600;letter-spacing:.1em}
.profile-code .pc-num{
  font:700 16px/1 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:.01em;
}
.card .head-line{display:flex;flex-wrap:wrap;align-items:center;gap:8px 10px}
.gender-badge{
  display:inline-flex;align-items:center;
  padding:5px 13px;border-radius:999px;
  font:700 11px/1.5 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.09em;
  border:1px solid transparent;
}
.gender-badge.gender-female{background:#FBE9EE;color:#A0466A;border-color:#F0CFD8}
.gender-badge.gender-male{background:#F1E5D5;color:#7C5234;border-color:#E1CCB1}
.age-badge{
  display:inline-flex;align-items:center;
  padding:5px 14px;border-radius:999px;
  font:700 13px/1.5 'Inter',sans-serif;
  background:var(--accent-soft);color:var(--accent);
  border:1px solid #C4DECC;
}
.loc-badge{
  display:inline-flex;align-items:center;gap:5px;
  padding:5px 13px;border-radius:999px;
  font:600 12px/1.5 'Inter',sans-serif;
  background:#E6EAF1;color:#3F4F6A;
  border:1px solid #C9D2DD;
}
.loc-badge::before{content:"📍";font-size:11px;line-height:1}
.card .posted{
  display:inline-flex;align-items:center;gap:5px;
  background:var(--gold-soft);color:#8C6B36;
  padding:4px 11px;border-radius:6px;
  font:700 10.5px/1.5 'Inter',sans-serif;
  letter-spacing:.07em;text-transform:uppercase;
  width:fit-content;
}
.card .fact-row{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}
.card .fact{
  display:inline-flex;align-items:center;gap:6px;
  background:var(--accent-pale);color:var(--accent);
  padding:6px 13px;border-radius:999px;
  font:500 13px/1.3 'Inter',sans-serif;
  border:1px solid #DCE9DF;
}
.card .fact .fact-icon{font-size:13px;line-height:1;opacity:.85}
.card .fact .fact-key{color:var(--muted);font-weight:500;margin-right:1px}
.card .lookingfor{
  font:italic 400 14px/1.6 'Inter',sans-serif;
  color:var(--ink-soft);
  margin-top:14px;padding:12px 16px;
  border-left:3px solid var(--gold);
  background:var(--gold-soft);
  border-radius:0 var(--radius-xs) var(--radius-xs) 0;
}
.card .lookingfor-label{
  display:block;font-style:normal;font-weight:700;
  color:#8C6B36;font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;margin-bottom:4px;
}
.card details.complete{margin-top:16px;border-top:1px solid var(--border-soft);padding-top:14px}
.card details.complete summary{
  cursor:pointer;list-style:none;
  display:inline-flex;align-items:center;gap:6px;
  font:600 13px/1 'Inter',sans-serif;
  color:var(--accent);user-select:none;padding:6px 0;
}
.card details.complete summary::-webkit-details-marker{display:none}
.card details.complete summary .caret{
  display:inline-block;font-size:15px;transition:transform var(--t);line-height:1;
}
.card details.complete[open] summary .caret{transform:rotate(90deg)}
.card details.complete summary:hover{color:var(--accent-hover)}
.complete-body{
  margin-top:14px;background:var(--panel-soft);
  border:1px solid var(--border-soft);border-radius:var(--radius-sm);
  padding:18px 22px;
}
.raw-message{display:flex;flex-direction:column;gap:5px;font:14px/1.6 'Inter',sans-serif;color:var(--ink-soft)}
.raw-message .raw-header{
  font:700 11px/1.4 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.12em;
  color:var(--accent);padding:6px 0 7px;
  border-bottom:1px solid var(--border);
  margin:10px 0 6px;
}
.raw-message .raw-header:first-child{margin-top:0}
.raw-message .raw-line{display:flex;flex-wrap:wrap;gap:4px 8px;padding:1px 0}
.raw-message .raw-line .raw-key{font-weight:600;color:var(--ink);flex-shrink:0}
.raw-message .raw-line .raw-key::after{content:":";opacity:.55;margin-left:1px}
.raw-message .raw-line .raw-val{color:var(--ink-soft);word-break:break-word;flex:1;min-width:140px}
.raw-message .raw-text{color:var(--ink-soft)}
.raw-message .raw-blank{height:6px}
@media (max-width: 600px){.complete-body{padding:14px 16px}}
.card .foot{
  margin-top:14px;font-size:13px;
  display:flex;justify-content:space-between;align-items:center;
  flex-wrap:wrap;gap:8px;
}
.card .foot a.tg-link{color:var(--accent);text-decoration:none;font-weight:600;display:inline-flex;align-items:center;gap:5px}
.card .foot a.tg-link:hover{text-decoration:underline}
.shortlist-btn{
  display:inline-flex;align-items:center;gap:6px;
  background:transparent;border:1px solid var(--border);
  border-radius:999px;padding:6px 13px;
  font:600 12px/1 'Inter',sans-serif;
  color:var(--muted);cursor:pointer;
  transition:all var(--t);
}
.shortlist-btn:hover{color:#A0466A;border-color:#F0CFD8;background:#FBE9EE}
.shortlist-btn.on{color:#A0466A;background:#FBE9EE;border-color:#E8B6C5;font-weight:700}
.shortlist-btn .heart-icon{font-size:13px;line-height:1;transition:transform var(--t)}
.shortlist-btn.on .heart-icon{transform:scale(1.15);animation:pop 280ms ease-out}
@keyframes pop{0%{transform:scale(1)}50%{transform:scale(1.35)}100%{transform:scale(1.15)}}

/* ---------- Preferences tab (editable form) ---------- */
.prefs-empty-banner{
  display:flex;align-items:center;gap:14px;
  background:var(--gold-soft);color:#8C6B36;
  border:1px solid #E5CFA7;border-radius:var(--radius);
  padding:14px 18px;margin-bottom:20px;max-width:760px;margin-left:auto;margin-right:auto;
  animation:cardIn 320ms ease-out backwards;
}
.prefs-empty-banner .peb-icon{font-size:24px;flex-shrink:0;animation:floaty 3.5s ease-in-out infinite}
.prefs-empty-banner strong{display:block;font-size:14.5px;color:#8C6B36;margin-bottom:2px}
.prefs-empty-banner small{display:block;font-size:12.5px;color:#8C6B36;opacity:.85}

.prefs-form-card{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:28px 30px;
  max-width:760px;margin:0 auto;
  box-shadow:var(--shadow-sm);
  animation:cardIn 320ms ease-out backwards;
}
.prefs-form-card h2{
  margin:0 0 4px;font:700 26px/1.2 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.01em;
}
.prefs-form-card .subtitle{color:var(--muted);font-size:13px;margin-bottom:24px}
.prefs-form-card .subtitle strong{color:var(--ink-soft);font-weight:600}
.prefs-form{display:flex;flex-direction:column;gap:16px}
.pf-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.pf-field{display:flex;flex-direction:column;gap:6px;min-width:0}
.pf-field>label{
  font:600 11px/1 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);
}
.pf-field input[type=text],
.pf-field input[type=number],
.pf-field input[type=date],
.pf-field select{
  width:100%;padding:10px 12px;
  border:1px solid var(--border);border-radius:var(--radius-xs);
  font:14px/1.2 'Inter',sans-serif;
  background:#fff;color:var(--ink);
  transition:border-color var(--t),box-shadow var(--t);
}
.pf-field input:focus,.pf-field select:focus{
  outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft);
}
.pf-field select[multiple]{padding:6px;min-height:160px}
.pf-field select[multiple] option{padding:6px 8px;border-radius:4px;font-size:13px}
.pf-field select[multiple] option:checked{background:var(--accent-soft);color:var(--accent);font-weight:500}
.pf-help{font-size:11.5px;color:var(--muted);line-height:1.4}
.pf-checks{
  display:flex;flex-direction:column;gap:0;
  border:1px solid var(--border);border-radius:var(--radius-xs);
  padding:8px 12px;background:#fff;min-height:42px;
}
.prefs-form-actions{
  display:flex;gap:10px;margin-top:28px;flex-wrap:wrap;
  padding-top:20px;border-top:1px solid var(--border-soft);
}

.prefs-applied-banner{
  display:flex;align-items:center;gap:12px;
  background:var(--accent-soft);color:var(--accent);
  border:1px solid #C4DECC;border-radius:var(--radius);
  padding:14px 18px;margin-bottom:20px;
  animation:cardIn 320ms ease-out backwards;
}
.prefs-applied-banner .pab-check{
  flex-shrink:0;width:30px;height:30px;border-radius:50%;
  background:var(--accent);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:16px;font-weight:700;
}
.prefs-applied-banner strong{display:block;font-size:14.5px;color:var(--accent);margin-bottom:2px}
.prefs-applied-banner small{display:block;font-size:12.5px;color:var(--accent);opacity:.8}
.prefs-summary-card{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:24px 28px;
  max-width:720px;margin:0 auto;
  box-shadow:var(--shadow-sm);
  animation:cardIn 320ms ease-out backwards;
}
.prefs-summary-card h2{
  margin:0 0 4px;font:700 24px/1.2 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.01em;
}
.prefs-summary-card .channel-hint{
  color:var(--muted);font-size:13px;margin-bottom:18px;
}
.prefs-list{display:grid;grid-template-columns:140px 1fr;gap:8px 18px;margin:0 0 22px}
.prefs-list dt{
  font:600 11px/1.5 'Inter',sans-serif;
  color:var(--muted);text-transform:uppercase;letter-spacing:.08em;
  padding-top:3px;
}
.prefs-list dd{margin:0;color:var(--ink);font:400 14px/1.5 'Inter',sans-serif;word-break:break-word}
.prefs-empty{
  text-align:center;padding:70px 24px;
  background:var(--panel);border:1px dashed var(--border);
  border-radius:var(--radius);max-width:560px;margin:0 auto;
}
.prefs-empty .pe-icon{font-size:42px;color:var(--accent);opacity:.7;margin-bottom:16px;animation:floaty 3.5s ease-in-out infinite}
.prefs-empty h2{
  margin:0 0 10px;font:700 22px/1.2 'Playfair Display',Georgia,serif;color:var(--accent);
}
.prefs-empty p{color:var(--ink-soft);font-size:14px;line-height:1.6;margin:0 0 22px}
.tab .badge#prefsBadge{background:var(--accent);font-size:8px;padding:3px 5px;line-height:1}

/* ---------- Source badge (which channel a profile came from) ---------- */
.card .card-header .ch-left{
  display:inline-flex;align-items:center;gap:10px;flex-wrap:wrap;
}
.source-badge{
  display:inline-flex;align-items:center;gap:6px;
  padding:4px 10px;border-radius:6px;
  background:var(--bg);border:1px solid var(--border-soft);
  font:500 11px/1.3 'Inter',sans-serif;
  color:var(--ink-soft);letter-spacing:.01em;
  white-space:nowrap;
}
.source-badge::before{
  content:"";width:6px;height:6px;border-radius:50%;
  background:var(--src-color, var(--muted));
  flex-shrink:0;
}
.source-badge.src-salafimarriage1{--src-color:#0F4C3A}
.source-badge.src-salafizawj_nikah{--src-color:#A56A2C}
.src-dot{
  display:inline-block;width:7px;height:7px;border-radius:50%;
  background:var(--src-color, var(--muted));
  margin-right:2px;flex-shrink:0;
}
.src-dot.src-salafimarriage1{--src-color:#0F4C3A}
.src-dot.src-salafizawj_nikah{--src-color:#A56A2C}

/* ---------- Shortlist tab ---------- */
.shortlist-header{
  display:flex;justify-content:space-between;align-items:flex-end;
  flex-wrap:wrap;gap:12px;margin-bottom:14px;
}
.shortlist-header h2{
  margin:0;font:700 24px/1.2 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.01em;
}
.shortlist-header h2 small{
  display:inline-block;font:500 13px/1.3 'Inter',sans-serif;
  color:var(--muted);margin-left:10px;letter-spacing:0;
}
.shortlist-filter{
  display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;
}
.shortlist-filter button{
  background:var(--panel);
  border:1px solid var(--border);border-radius:999px;
  padding:7px 14px;cursor:pointer;
  font:500 12.5px/1 'Inter',sans-serif;color:var(--ink-soft);
  display:inline-flex;align-items:center;gap:8px;
  transition:all var(--t);
}
.shortlist-filter button:hover{border-color:var(--accent);color:var(--accent)}
.shortlist-filter button.active{
  background:var(--accent);color:#fff;border-color:var(--accent);
}
.shortlist-filter .cnt{
  background:var(--accent-soft);color:var(--accent);
  padding:1px 8px;border-radius:999px;
  font-size:11px;font-weight:700;line-height:1.4;
}
.shortlist-filter button.active .cnt{
  background:rgba(255,255,255,.18);color:#fff;
}
.shortlist-empty{
  text-align:center;padding:70px 24px;
  background:var(--panel);border:1px dashed var(--border);
  border-radius:var(--radius);
}
.shortlist-empty .se-icon{font-size:42px;color:#A0466A;opacity:.7;margin-bottom:16px}
.shortlist-empty h3{
  margin:0 0 10px;font:700 22px/1.2 'Playfair Display',Georgia,serif;color:var(--accent);
}
.shortlist-empty p{color:var(--ink-soft);font-size:14px;line-height:1.6;margin:0}
.shortlist-empty em{color:var(--accent);font-style:normal;font-weight:600}

/* ---------- Pagination & empty ---------- */
.pagination{
  display:flex;justify-content:center;align-items:center;gap:8px;
  margin:28px 0 8px;padding:14px 18px;
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);box-shadow:var(--shadow-sm);
}
.pagination .pageinfo{color:var(--muted);font-size:13px;padding:0 10px}
.empty{
  text-align:center;padding:60px 24px;color:var(--muted);
  background:var(--panel);border:1px dashed var(--border);
  border-radius:var(--radius);
}
.empty .icon{font-size:32px;display:block;margin-bottom:8px;opacity:.6}

/* ---------- Loading + skeletons ---------- */
.loading-overlay{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:50px 24px 30px;color:var(--muted);
  text-align:center;width:100%;
}
.spinner-mark{color:var(--accent);animation:spinPulse 1.6s ease-in-out infinite}
.loading-text{
  margin-top:16px;font:500 14px/1 'Inter',sans-serif;
  letter-spacing:.04em;color:var(--muted);
}
.loading-text small{display:block;margin-top:4px;color:var(--muted-soft);font-size:12px}

.skeleton-card{
  background:var(--panel);border:1px solid var(--border-soft);
  border-radius:var(--radius);padding:18px 20px;margin-bottom:14px;
  box-shadow:var(--shadow-sm);
  animation:cardIn 320ms ease-out backwards;
}
.skel-row{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.skel-row:last-child{margin-bottom:0}
.skel-pill,.skel-line{
  background:linear-gradient(90deg,var(--border-soft) 0%,#F8F4ED 50%,var(--border-soft) 100%);
  background-size:1200px 100%;
  animation:shimmer 1.6s infinite linear;
  border-radius:999px;
}
.skel-line{border-radius:6px;height:10px}

/* ---------- Coming soon placeholder ---------- */
.coming-soon{
  display:flex;flex-direction:column;align-items:center;
  text-align:center;padding:80px 24px;
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);box-shadow:var(--shadow-sm);
  max-width:600px;margin:40px auto 0;
  animation:cardIn 360ms ease-out backwards;
}
.cs-icon{
  font-size:42px;color:var(--accent);margin-bottom:18px;opacity:.85;
  animation:floaty 3.5s ease-in-out infinite;
}
.coming-soon h2{
  margin:0 0 12px;font:700 28px/1.2 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.015em;
}
.coming-soon p{
  margin:0 0 22px;color:var(--ink-soft);font-size:14.5px;line-height:1.65;
  max-width:440px;
}
.cs-badge{
  display:inline-flex;align-items:center;gap:6px;
  background:var(--gold-soft);color:#8C6B36;
  padding:7px 16px;border-radius:999px;
  font:700 11px/1.4 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.1em;
}
.cs-badge::before{content:"⏳";font-size:13px}

/* ---------- Mobile drawer ---------- */
.drawer-trigger{display:none}
.drawer-backdrop{
  display:none;position:fixed;inset:0;
  background:rgba(20,40,30,.45);backdrop-filter:blur(2px);
  -webkit-backdrop-filter:blur(2px);
  z-index:90;animation:fadeIn .18s ease;
}
.drawer-backdrop.open{display:block}
.drawer-close{display:none}

/* ---------- Animations ---------- */
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
@keyframes cardIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes shimmer{0%{background-position:-1200px 0}100%{background-position:1200px 0}}
@keyframes spinPulse{
  0%{transform:rotate(0) scale(1);opacity:.75}
  50%{transform:rotate(180deg) scale(1.04);opacity:1}
  100%{transform:rotate(360deg) scale(1);opacity:.75}
}
@keyframes floaty{
  0%,100%{transform:translateY(0)}
  50%{transform:translateY(-6px)}
}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none !important;transition:none !important}
}

/* ---------- Responsive ---------- */
@media (max-width: 960px){
  header{padding:18px 20px 0}
  .layout{grid-template-columns:1fr;gap:14px}
  .tab-section{padding:22px}
  aside{top:auto}
  .drawer-trigger{
    display:inline-flex;align-items:center;gap:8px;
    padding:10px 16px;
    background:var(--panel);border:1px solid var(--border);
    border-radius:var(--radius-xs);
    font:500 14px/1 'Inter',sans-serif;color:var(--ink);
    cursor:pointer;box-shadow:var(--shadow-sm);
    transition:all var(--t);
  }
  .drawer-trigger:hover{background:var(--accent-pale);border-color:#C9DDD0;color:var(--accent)}
  .drawer-trigger .icon{font-size:14px}
  .drawer-trigger .badge-count{
    background:var(--accent);color:#fff;
    border-radius:999px;padding:2px 8px;font-size:11px;font-weight:700;
    min-width:20px;text-align:center;line-height:1.4;
  }
  .drawer-trigger .badge-count.zero{display:none}
  aside{
    display:none;position:fixed;
    bottom:0;left:0;right:0;top:auto;
    max-height:88vh;height:auto;
    border-radius:var(--radius) var(--radius) 0 0;
    z-index:100;
    padding:24px 22px max(28px,env(safe-area-inset-bottom));
    box-shadow:var(--shadow-xl);
    border:1px solid var(--border);border-bottom:none;
    animation:slideUp .25s ease;overflow-y:auto;
  }
  aside.open{display:block}
  aside::before{
    content:"";display:block;width:42px;height:4px;
    background:var(--muted-soft);border-radius:2px;margin:0 auto 18px;
  }
  .drawer-close{
    display:flex;align-items:center;justify-content:center;
    position:absolute;top:14px;right:14px;
    width:34px;height:34px;border-radius:50%;
    background:var(--bg);border:none;cursor:pointer;
    font-size:18px;color:var(--muted);
    transition:all var(--t);
  }
  .drawer-close:hover{color:var(--ink);background:var(--accent-pale)}
}
@media (max-width: 700px){
  .pf-row{grid-template-columns:1fr;gap:14px}
  .prefs-form-card{padding:22px 18px}
  .prefs-form-card h2{font-size:22px}
}
@media (max-width: 600px){
  header{padding:16px 16px 0}
  .brand{font-size:24px;gap:10px}
  .brand-mark svg{width:46px;height:25px}
  .tagline{font-size:12.5px}
  header .meta{font-size:12px;gap:4px 10px}
  nav.tabs{margin-top:10px}
  .tab{padding:9px 14px;font-size:13px}
  .tab-section{padding:18px 14px}
  .card{padding:14px 16px}
  .card .head-line{gap:6px 8px}
  .card .card-header{flex-direction:column;align-items:flex-start;gap:8px}
  .card .card-header .ch-left{gap:8px}
  .card .lookingfor{font-size:13px;padding:9px 12px}
  .summary{font-size:12px}
  .summary strong{font-size:15px}
  .pagination{gap:6px;padding:12px;flex-wrap:wrap}
  .pagination .pageinfo{flex-basis:100%;text-align:center;order:-1;margin-bottom:4px}
  .coming-soon{padding:54px 22px}
  .coming-soon h2{font-size:24px}
  /* Tighter date input in the filter range so two fit side-by-side */
  .range input[type=date]{padding:7px 4px;font-size:12.5px}
  /* The filter aside drawer needs explicit width clamping on iPhone */
  aside{width:100%;max-width:100%;box-sizing:border-box}
  aside select[multiple]{min-height:130px}
  /* Prefs form */
  .pf-field select[multiple]{min-height:130px}
  .prefs-empty-banner{padding:12px 14px;gap:10px;flex-wrap:wrap}
}
</style>
</head>
<body>

<header>
  <div class="titlebar">
    <h1 class="brand">
      <span class="brand-mark"><svg viewBox="0 0 60 32" width="56" height="30" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <circle cx="22" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="2.2"/>
        <circle cx="38" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="2.2"/>
        <circle cx="22" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="3 28" stroke-dashoffset="2"/>
      </svg></span>
      <span class="brand-text">Salafi Match</span>
    </h1>
    <div class="tagline">A clean filter for Salafi matrimonial profiles</div>
    <div class="meta" id="headerMeta"></div>
  </div>
  <div class="channel-switch" id="channelSwitch"></div>
  <nav class="tabs">
    <button class="tab active" data-tab="browse">Browse</button>
    <button class="tab" data-tab="prefs">My Preferences <span class="badge zero" id="prefsBadge">●</span></button>
    <button class="tab" data-tab="shortlist">Shortlist <span class="badge zero" id="shortlistBadge">0</span></button>
    <button class="tab disabled" data-tab="notif">Notifications <span class="soon">Soon</span></button>
  </nav>
</header>

<!-- ============ BROWSE TAB ============ -->
<section class="tab-section active" id="browse-section">
  <div class="layout">
    <aside id="filterAside">
      <button type="button" class="drawer-close" id="drawerClose" aria-label="Close filters">✕</button>

      <h3>Search profile text</h3>
      <input type="text" id="q" placeholder="Name, education, profession, keywords…">
      <div class="field-help">Searches every word in the original Telegram message.</div>

      <h3>Gender</h3>
      <select id="gender">
        <option value="">Any</option>
        <option value="female">Female (sister)</option>
        <option value="male">Male (brother)</option>
      </select>

      <h3>Age</h3>
      <div class="range">
        <input type="number" id="ageMin" min="18" max="60" placeholder="18">
        <span>—</span>
        <input type="number" id="ageMax" min="18" max="60" placeholder="60">
      </div>

      <h3>Posted Date</h3>
      <div class="range">
        <input type="date" id="dateFrom">
        <span>—</span>
        <input type="date" id="dateTo">
      </div>
      <div class="date-presets" id="datePresets">
        <button type="button" data-days="7">7 days</button>
        <button type="button" data-days="30">30 days</button>
        <button type="button" data-days="90">90 days</button>
        <button type="button" data-days="0">All</button>
      </div>

      <h3>Marital Status</h3>
      <div id="maritalBox"></div>

      <h3>Country</h3>
      <select id="country" class="single-dd"><option value="">Any country</option></select>

      <h3>State</h3>
      <select id="state" class="single-dd"><option value="">Any state</option></select>

      <h3>City</h3>
      <input type="text" id="city" placeholder="Type city name…">

      <h3>Profession</h3>
      <input type="text" id="profession" placeholder="e.g. doctor">

      <h3>Education</h3>
      <input type="text" id="education" placeholder="e.g. mbbs">

      <div class="filter-actions">
        <button class="btn" onclick="resetFilters()">Reset filters</button>
        <a class="btn ghost" onclick="switchTab('prefs');return false;" href="#">Edit my preferences →</a>
      </div>
    </aside>
    <div>
      <div class="topbar">
        <button type="button" class="drawer-trigger" id="drawerTrigger" aria-label="Open filters">
          <span class="icon">☰</span>
          <span>Filters</span>
          <span class="badge-count zero" id="filterBadgeCount">0</span>
        </button>
        <div class="summary" id="count"></div>
        <a href="#" id="downloadCsv" class="btn ghost">↓ Download CSV</a>
      </div>
      <div id="results"></div>
      <div class="pagination" id="pagination"></div>
    </div>
  </div>
</section>

<!-- ============ MY PREFERENCES TAB ============ -->
<section class="tab-section" id="prefs-section">
  <div id="prefsContent"></div>
</section>

<!-- ============ SHORTLIST TAB ============ -->
<section class="tab-section" id="shortlist-section">
  <div id="shortlistContent"></div>
</section>

<!-- ============ COMING SOON: NOTIFICATIONS ============ -->
<section class="tab-section" id="notif-section">
  <div class="coming-soon">
    <div class="cs-icon">🔔</div>
    <h2>Notifications</h2>
    <p>Get alerted the moment a profile matching your saved preferences is posted — across all channels you watch.</p>
    <span class="cs-badge">Coming Soon</span>
  </div>
</section>

<div class="drawer-backdrop" id="drawerBackdrop"></div>

<script>
const CHANNELS    = __CHANNELS__;
const BUILD_ID    = '__BUILD_ID__';
const GENERATED_AT= '__GENERATED_AT__';
const TOTAL_COUNT = __TOTAL_COUNT__;
const PER_PAGE    = 25;

// ============ STATE ============
const ACTIVE_CHANNEL_KEY = 'salafi_active_channel_v1';
let activeChannel = (() => {
  const stored = localStorage.getItem(ACTIVE_CHANNEL_KEY);
  if (stored && CHANNELS.some(c => c.id === stored)) return stored;
  return CHANNELS.length ? CHANNELS[0].id : '';
})();
const dataCache = {};   // channelId → array of profile rows
const fetchInflight = {};
let page = 1;
let activePreset = null;

function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function activeData(){ return dataCache[activeChannel] || []; }
function activeCount(){ return activeData().length; }
function channelLabel(id){
  const c = CHANNELS.find(x => x.id === id);
  return c ? c.label : '@' + id;
}

// ============ PREFERENCES (universal — applies to all channels) ============
const PREFS_KEY = 'salafi_prefs_v1';

function migratePrefsStorage(){
  if (localStorage.getItem(PREFS_KEY) !== null) return;
  // Prefer the most recent per-channel prefs (any non-empty one).
  for (const ch of CHANNELS){
    const oldKey = `salafi_prefs_${ch.id}_v1`;
    const val = localStorage.getItem(oldKey);
    if (val){
      localStorage.setItem(PREFS_KEY, val);
      break;
    }
  }
  // Clean up old keys.
  for (const ch of CHANNELS){
    localStorage.removeItem(`salafi_prefs_${ch.id}_v1`);
  }
}

function loadSavedPrefs(){
  let p;
  try { p = JSON.parse(localStorage.getItem(PREFS_KEY)) || null; } catch(e){ return null; }
  if (!p) return null;
  // Migrate legacy multi-select arrays → single-select strings.
  if (Array.isArray(p.countries)){ p.country = p.countries[0] || null; delete p.countries; }
  if (Array.isArray(p.states)){    p.state   = p.states[0]   || null; delete p.states; }
  return p;
}
function hasSavedPrefs(){
  const p = loadSavedPrefs();
  return prefsAreMeaningful(p);
}
function prefsAreMeaningful(p){
  if (!p) return false;
  if (p.keyword) return true;
  if (p.gender) return true;
  if ((p.ageMin && p.ageMin > 18) || (p.ageMax && p.ageMax < 60)) return true;
  if (p.dateFrom || p.dateTo) return true;
  if (p.country) return true;
  if (p.state) return true;
  if ((p.cityTerms||[]).length) return true;
  if (p.profession) return true;
  if (p.education) return true;
  if ((p.marital||[]).length) return true;
  return false;
}

// Apply saved prefs to the Browse aside form fields (used on page load + channel switch).
function applySavedPrefs(){
  const p = loadSavedPrefs();
  if (!p) return false;
  document.getElementById('q').value          = p.keyword || '';
  document.getElementById('gender').value     = p.gender || '';
  document.getElementById('ageMin').value     = (p.ageMin && p.ageMin > 0) ? p.ageMin : '';
  document.getElementById('ageMax').value     = (p.ageMax && p.ageMax < 999) ? p.ageMax : '';
  document.getElementById('dateFrom').value   = p.dateFrom || '';
  document.getElementById('dateTo').value     = p.dateTo || '';
  document.getElementById('city').value       = (p.cityTerms||[]).join(', ');
  document.getElementById('profession').value = p.profession || '';
  document.getElementById('education').value  = p.education || '';
  const cSel = document.getElementById('country');
  const sSel = document.getElementById('state');
  ensureSelectHas(cSel, p.country);
  ensureSelectHas(sSel, p.state);
  cSel.value = p.country || '';
  sSel.value = p.state   || '';
  document.querySelectorAll('[data-marital]').forEach(cb => {
    cb.checked = (p.marital||[]).includes(cb.value);
  });
  return true;
}
function updatePrefsBadge(){
  const b = document.getElementById('prefsBadge');
  if (!b) return;
  b.classList.toggle('zero', !hasSavedPrefs());
}

// ----- Preferences tab form -----
// Builds a full filter form INSIDE the Preferences tab. Editing happens here,
// not on Browse. Save → applies to Browse on next visit (and immediately).
function uniqAllChannelsField(field){
  const all = [];
  for (const arr of Object.values(dataCache)){
    for (const p of arr) if (p[field]) all.push(p[field]);
  }
  return [...new Set(all)].sort();
}

function renderPrefsTab(){
  const host = document.getElementById('prefsContent');
  if (!host) return;
  const p = loadSavedPrefs() || {};
  const isApplied = prefsAreMeaningful(p);

  const countries = uniqAllChannelsField('country');
  const states    = uniqAllChannelsField('state');
  const statuses  = uniqAllChannelsField('marital_status');

  // Pre-select helpers
  const isChk = (arr, v) => (arr||[]).includes(v) ? ' checked' : '';

  host.innerHTML = `
    ${isApplied ? `
      <div class="prefs-applied-banner">
        <div class="pab-check">✓</div>
        <div>
          <strong>Your preferences are applied.</strong>
          <small>The Browse tab automatically uses these filters on every visit, across all channels.</small>
        </div>
      </div>` : `
      <div class="prefs-empty-banner">
        <div class="peb-icon">💍</div>
        <div>
          <strong>No preferences saved yet.</strong>
          <small>Set filters below and click Save. Browse will then auto-apply them on every visit.</small>
        </div>
      </div>`}

    <div class="prefs-form-card">
      <h2>My Preferences</h2>
      <div class="subtitle">Universal — applies across <strong>${CHANNELS.length}</strong> channel${CHANNELS.length===1?'':'s'}</div>

      <div class="prefs-form">
        <div class="pf-field">
          <label>Search profile text</label>
          <input type="text" id="p_q" placeholder="Name, education, profession, keywords…" value="${escapeHtml(p.keyword || '')}">
          <div class="pf-help">Searches every word in the original Telegram message.</div>
        </div>

        <div class="pf-row">
          <div class="pf-field">
            <label>Gender</label>
            <select id="p_gender">
              <option value=""${p.gender ? '' : ' selected'}>Any</option>
              <option value="female"${p.gender === 'female' ? ' selected' : ''}>Female (sister)</option>
              <option value="male"${p.gender === 'male' ? ' selected' : ''}>Male (brother)</option>
            </select>
          </div>
          <div class="pf-field">
            <label>Marital status</label>
            <div id="p_maritalBox" class="pf-checks">
              ${statuses.map(s => `<label class="checkrow"><input type="checkbox" value="${escapeHtml(s)}" data-pmarital${isChk(p.marital, s)}> ${escapeHtml(s)}</label>`).join('')}
            </div>
          </div>
        </div>

        <div class="pf-row">
          <div class="pf-field">
            <label>Minimum age</label>
            <input type="number" id="p_ageMin" min="18" max="60" placeholder="18" value="${(p.ageMin && p.ageMin > 0) ? p.ageMin : ''}">
          </div>
          <div class="pf-field">
            <label>Maximum age</label>
            <input type="number" id="p_ageMax" min="18" max="60" placeholder="60" value="${(p.ageMax && p.ageMax < 999) ? p.ageMax : ''}">
          </div>
        </div>

        <div class="pf-row">
          <div class="pf-field">
            <label>Posted after</label>
            <input type="date" id="p_dateFrom" value="${escapeHtml(p.dateFrom || '')}">
          </div>
          <div class="pf-field">
            <label>Posted before</label>
            <input type="date" id="p_dateTo" value="${escapeHtml(p.dateTo || '')}">
          </div>
        </div>

        <div class="pf-row">
          <div class="pf-field">
            <label>Country</label>
            <select id="p_country" class="single-dd">
              <option value=""${p.country ? '' : ' selected'}>Any country</option>
              ${countries.map(c => `<option value="${escapeHtml(c)}"${p.country === c ? ' selected' : ''}>${escapeHtml(c)}</option>`).join('')}
            </select>
          </div>
          <div class="pf-field">
            <label>State</label>
            <select id="p_state" class="single-dd">
              <option value=""${p.state ? '' : ' selected'}>Any state</option>
              ${states.map(s => `<option value="${escapeHtml(s)}"${p.state === s ? ' selected' : ''}>${escapeHtml(s)}</option>`).join('')}
            </select>
          </div>
        </div>

        <div class="pf-field">
          <label>City contains</label>
          <input type="text" id="p_city" placeholder="Type city name(s), comma-separated" value="${escapeHtml((p.cityTerms||[]).join(', '))}">
        </div>

        <div class="pf-row">
          <div class="pf-field">
            <label>Profession contains</label>
            <input type="text" id="p_profession" placeholder="e.g. doctor" value="${escapeHtml(p.profession || '')}">
          </div>
          <div class="pf-field">
            <label>Education contains</label>
            <input type="text" id="p_education" placeholder="e.g. mbbs" value="${escapeHtml(p.education || '')}">
          </div>
        </div>
      </div>

      <div class="prefs-form-actions">
        <button class="btn primary" id="savePrefsBtn" onclick="savePrefsFromForm()">★ Save preferences</button>
        <button class="btn" onclick="if(confirm('Clear all preferences? Browse will show all profiles again.'))clearAllPrefs()">Clear all</button>
      </div>
    </div>`;
}

function readPrefsForm(){
  return {
    keyword:    document.getElementById('p_q').value.trim() || null,
    gender:     document.getElementById('p_gender').value || null,
    ageMin:     parseInt(document.getElementById('p_ageMin').value) || 0,
    ageMax:     parseInt(document.getElementById('p_ageMax').value) || 999,
    dateFrom:   document.getElementById('p_dateFrom').value || null,
    dateTo:     document.getElementById('p_dateTo').value || null,
    country:    document.getElementById('p_country').value || null,
    state:      document.getElementById('p_state').value || null,
    cityTerms:  document.getElementById('p_city').value.trim().toLowerCase().split(',').map(s => s.trim()).filter(Boolean),
    profession: document.getElementById('p_profession').value.trim() || null,
    education:  document.getElementById('p_education').value.trim() || null,
    marital:    [...document.querySelectorAll('[data-pmarital]:checked')].map(c => c.value),
  };
}

function savePrefsFromForm(){
  const c = readPrefsForm();
  if (!prefsAreMeaningful(c)){
    alert('No filters set. Tick at least one filter to save preferences.');
    return;
  }
  localStorage.setItem(PREFS_KEY, JSON.stringify(c));
  // Apply immediately to Browse aside so going back shows the filter applied.
  applySavedPrefs();
  page = 1;
  // Re-render Browse so the count + cards reflect the new prefs even if user
  // doesn't switch tabs yet.
  if (typeof renderBrowse === 'function') renderBrowse();
  const btn = document.getElementById('savePrefsBtn');
  const orig = btn.innerHTML;
  btn.innerHTML = '✓ Saved';
  setTimeout(() => {
    btn.innerHTML = orig;
    renderPrefsTab();   // refresh the banner state
  }, 1300);
  updatePrefsBadge();
}

function clearAllPrefs(){
  localStorage.removeItem(PREFS_KEY);
  resetFilters({ rerender: false });
  page = 1;
  if (typeof renderBrowse === 'function') renderBrowse();
  renderPrefsTab();
  updatePrefsBadge();
}

// ============ SHORTLIST (universal across channels) ============
// Storage shape: a single array of "channel:msg_id" strings. One source of
// truth regardless of which channel is active in Browse.
const SHORTLIST_KEY = 'salafi_shortlist_v1';

function migrateShortlistStorage(){
  // One-time migration from the older per-channel keys.
  if (localStorage.getItem(SHORTLIST_KEY) !== null) return;
  const merged = [];
  for (const ch of CHANNELS){
    const oldKey = `salafi_shortlist_${ch.id}_v1`;
    try {
      const arr = JSON.parse(localStorage.getItem(oldKey) || '[]');
      for (const mid of arr) merged.push(`${ch.id}:${mid}`);
      localStorage.removeItem(oldKey);
    } catch(e){}
  }
  if (merged.length) localStorage.setItem(SHORTLIST_KEY, JSON.stringify(merged));
}

function loadShortlist(){
  try { return JSON.parse(localStorage.getItem(SHORTLIST_KEY)) || []; } catch(e){ return []; }
}
function saveShortlist(arr){ localStorage.setItem(SHORTLIST_KEY, JSON.stringify(arr)); }
function entryFor(channel, msg_id){ return `${channel}:${msg_id}`; }
function isShortlisted(channel, msg_id){ return loadShortlist().indexOf(entryFor(channel, msg_id)) >= 0; }

function toggleShortlistFromBtn(btn){
  toggleShortlist(btn.dataset.channel, parseInt(btn.dataset.msgId, 10));
}
function toggleShortlist(channel, msg_id){
  const list = loadShortlist();
  const entry = entryFor(channel, msg_id);
  const idx = list.indexOf(entry);
  const wasOn = idx >= 0;
  if (wasOn) list.splice(idx, 1);
  else list.push(entry);
  saveShortlist(list);
  // Update every visible heart button for this specific channel+msg_id.
  document.querySelectorAll(`.shortlist-btn[data-entry="${entry}"]`).forEach(btn => {
    btn.classList.toggle('on', !wasOn);
    btn.querySelector('.heart-icon').textContent = wasOn ? '♡' : '♥';
    btn.querySelector('span:last-child').textContent = wasOn ? 'Shortlist' : 'Shortlisted';
  });
  if (document.getElementById('shortlist-section').classList.contains('active')){
    renderShortlist();
  }
  updateShortlistBadge();
}

function updateShortlistBadge(){
  const n = loadShortlist().length;
  const b = document.getElementById('shortlistBadge');
  if (!b) return;
  b.textContent = n;
  b.classList.toggle('zero', n === 0);
}

function shortlistByChannel(){
  const list = loadShortlist();
  const groups = {};
  for (const entry of list){
    const [ch] = entry.split(':');
    groups[ch] = (groups[ch] || 0) + 1;
  }
  return groups;
}

async function renderShortlist(){
  const host = document.getElementById('shortlistContent');
  if (!host) return;

  const list = loadShortlist();
  const byCh = shortlistByChannel();
  const channelsWithEntries = Object.keys(byCh);
  const currentFilter = host.dataset.filter || 'all';

  // Header
  const headerLabel = list.length === 0
    ? 'no profiles saved yet'
    : `${list.length} saved across ${channelsWithEntries.length} channel${channelsWithEntries.length === 1 ? '' : 's'}`;

  let html = `<div class="shortlist-header">
    <h2>Shortlist <small>${headerLabel}</small></h2>
  </div>`;

  // Filter chips (only if 2+ channels and 1+ entries)
  if (CHANNELS.length >= 2 && list.length > 0){
    html += `<div class="shortlist-filter" role="tablist">
      <button class="${currentFilter==='all'?'active':''}" data-filter="all">All<span class="cnt">${list.length}</span></button>
      ${CHANNELS.map(c => {
        const cnt = byCh[c.id] || 0;
        if (cnt === 0) return '';
        return `<button class="${currentFilter===c.id?'active':''}" data-filter="${escapeHtml(c.id)}"><span class="src-dot src-${escapeHtml(c.id)}"></span>${escapeHtml(c.label)}<span class="cnt">${cnt}</span></button>`;
      }).join('')}
    </div>`;
  }

  // Empty state
  if (!list.length){
    html += `<div class="shortlist-empty">
      <div class="se-icon">♡</div>
      <h3>No profiles shortlisted yet</h3>
      <p>Tap the ♡ button on any profile to save it here.<br>The Shortlist tab collects saved profiles from <em>all channels</em> in one place — each card shows where it came from.</p>
    </div>`;
    host.innerHTML = html;
    return;
  }

  // Determine which channels' data we need to fetch
  const neededChannels = currentFilter === 'all'
    ? channelsWithEntries
    : [currentFilter];
  const allCached = neededChannels.every(ch => dataCache[ch]);

  if (!allCached){
    // Show a loading state, fetch missing data, then re-render
    html += `<div class="loading-overlay"><div class="spinner-mark">${logoSpinnerSVG()}</div><div class="loading-text">Loading shortlisted profiles…</div></div>`;
    host.innerHTML = html;
    wireShortlistFilters();
    await Promise.all(neededChannels.map(ch => ensureChannelData(ch).catch(() => null)));
    return renderShortlist();
  }

  // Resolve entries to profile objects (preserving shortlist order = oldest-first)
  const profiles = [];
  for (const entry of list){
    const [ch, midStr] = entry.split(':');
    if (currentFilter !== 'all' && currentFilter !== ch) continue;
    const profile = (dataCache[ch] || []).find(p => p.msg_id === parseInt(midStr, 10));
    if (profile) profiles.push(profile);
  }

  if (!profiles.length){
    html += `<div class="empty"><span class="icon">🔎</span>No profiles match this filter.</div>`;
  } else {
    html += profiles.map(p => renderCard(p)).join('');
  }

  host.innerHTML = html;
  wireShortlistFilters();
}

function wireShortlistFilters(){
  const host = document.getElementById('shortlistContent');
  if (!host) return;
  host.querySelectorAll('.shortlist-filter button').forEach(btn => {
    btn.addEventListener('click', () => {
      host.dataset.filter = btn.dataset.filter;
      renderShortlist();
    });
  });
}

const _MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const _MONTHS_LONG = ['January','February','March','April','May','June','July','August','September','October','November','December'];
function _ordinal(day){
  const lastTwo = day % 100;
  const lastOne = day % 10;
  if (lastTwo >= 11 && lastTwo <= 13) return 'th';
  if (lastOne === 1) return 'st';
  if (lastOne === 2) return 'nd';
  if (lastOne === 3) return 'rd';
  return 'th';
}
function formatDate(iso){
  // Profile posted dates — UTC (matches when Telegram displayed them).
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso.slice(0,10);
  const day = d.getUTCDate();
  return `${day}${_ordinal(day)} ${_MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}
function formatDateTime(iso){
  // Header "last updated" — local timezone, with 12-hour clock + AM/PM.
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const day = d.getDate();
  const month = _MONTHS_LONG[d.getMonth()];
  const year = d.getFullYear();
  const h24 = d.getHours();
  const h12 = h24 === 0 ? 12 : (h24 > 12 ? h24 - 12 : h24);
  const mins = String(d.getMinutes()).padStart(2, '0');
  const ampm = h24 < 12 ? 'AM' : 'PM';
  return `${day}${_ordinal(day)} ${month} ${year}, ${h12}:${mins} ${ampm}`;
}

// ============ LAZY DATA LOADING ============
function logoSpinnerSVG(){
  return `<svg viewBox="0 0 60 32" width="56" height="30" xmlns="http://www.w3.org/2000/svg">
    <circle cx="22" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="2.2"/>
    <circle cx="38" cy="16" r="11" fill="none" stroke="currentColor" stroke-width="2.2"/>
  </svg>`;
}

function showLoading(channelId){
  const ch = CHANNELS.find(c => c.id === channelId);
  document.getElementById('count').innerHTML = `<strong>${ch.count.toLocaleString()}</strong> profiles · loading…`;
  document.getElementById('results').innerHTML = `
    <div class="loading-overlay">
      <div class="spinner-mark">${logoSpinnerSVG()}</div>
      <div class="loading-text">Loading ${ch.count.toLocaleString()} profiles…<small>fetching freshest data</small></div>
    </div>
    ${renderSkeletons(4)}
  `;
  document.getElementById('pagination').innerHTML = '';
}

function renderSkeletons(n){
  let out = '';
  for (let i = 0; i < n; i++){
    out += `<div class="skeleton-card">
      <div class="skel-row" style="justify-content:space-between">
        <div class="skel-pill" style="width:90px;height:18px"></div>
        <div class="skel-pill" style="width:130px;height:20px"></div>
      </div>
      <div class="skel-row">
        <div class="skel-pill" style="width:72px;height:24px"></div>
        <div class="skel-pill" style="width:54px;height:24px"></div>
        <div class="skel-pill" style="width:120px;height:24px"></div>
      </div>
      <div class="skel-row">
        <div class="skel-pill" style="width:100px;height:28px"></div>
        <div class="skel-pill" style="width:140px;height:28px"></div>
        <div class="skel-pill" style="width:120px;height:28px"></div>
      </div>
    </div>`;
  }
  return out;
}

async function ensureChannelData(channelId){
  if (dataCache[channelId]) return dataCache[channelId];
  if (fetchInflight[channelId]) return fetchInflight[channelId];
  showLoading(channelId);
  const ch = CHANNELS.find(c => c.id === channelId);
  const url = `${ch.data_url}?v=${BUILD_ID}`;
  fetchInflight[channelId] = (async () => {
    try {
      const resp = await fetch(url, { cache: 'default' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const rows = await resp.json();
      dataCache[channelId] = rows;
      return rows;
    } finally {
      delete fetchInflight[channelId];
    }
  })();
  return fetchInflight[channelId];
}

// ============ HEADER + CHANNEL SWITCHER ============
function renderHeaderMeta(){
  const meta = document.getElementById('headerMeta');
  if (!meta) return;
  const ch = activeChannel;
  meta.innerHTML = `
    <span><strong>${TOTAL_COUNT.toLocaleString()}</strong> total profiles</span>
    <span class="dot"></span>
    <span>updated ${escapeHtml(formatDateTime(GENERATED_AT))}</span>
    <span class="dot"></span>
    <span>from <a class="ch-source" href="https://t.me/${encodeURIComponent(ch)}" target="_blank" rel="noopener">@${escapeHtml(ch)}</a></span>
  `;
}
function renderChannelSwitch(){
  const host = document.getElementById('channelSwitch');
  if (!host) return;
  if (CHANNELS.length < 2){ host.style.display = 'none'; return; }
  host.innerHTML = CHANNELS.map(c => {
    const isActive = c.id === activeChannel;
    return `<button class="${isActive ? 'active' : ''}" data-channel="${escapeHtml(c.id)}">
      ${escapeHtml(c.label)}<span class="ch-count">${c.count.toLocaleString()}</span>
    </button>`;
  }).join('');
  host.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => switchChannel(btn.dataset.channel));
  });
}
async function switchChannel(id){
  if (!CHANNELS.some(c => c.id === id) || id === activeChannel) return;
  activeChannel = id;
  localStorage.setItem(ACTIVE_CHANNEL_KEY, id);
  page = 1;
  resetFilters({ rerender: false });
  renderHeaderMeta();
  renderChannelSwitch();
  await ensureChannelData(id);
  rebuildDynamicLists();
  // Auto-apply saved preferences for the new channel (if any). Falls back to
  // the India default already set by rebuildDynamicLists when no prefs exist.
  applySavedPrefs();
  updatePrefsBadge();
  updateShortlistBadge();
  renderBrowse();
}

// ============ TABS ============
document.querySelectorAll('.tab').forEach(b => {
  b.addEventListener('click', () => switchTab(b.dataset.tab));
});
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.tab-section').forEach(s => s.classList.toggle('active', s.id===name+'-section'));
  closeDrawer();
  if (name === 'prefs')     renderPrefsTab();
  if (name === 'shortlist') renderShortlist();
}

// ============ MOBILE DRAWER ============
const drawerTrigger = document.getElementById('drawerTrigger');
const drawerClose   = document.getElementById('drawerClose');
const drawerBackdrop= document.getElementById('drawerBackdrop');
const filterAside   = document.getElementById('filterAside');

function openDrawer(){
  filterAside.classList.add('open');
  drawerBackdrop.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeDrawer(){
  filterAside.classList.remove('open');
  drawerBackdrop.classList.remove('open');
  document.body.style.overflow = '';
}
drawerTrigger?.addEventListener('click', openDrawer);
drawerClose?.addEventListener('click', closeDrawer);
drawerBackdrop?.addEventListener('click', closeDrawer);
document.addEventListener('keydown', e => { if (e.key==='Escape') closeDrawer(); });

// ============ DYNAMIC DROPDOWNS ============
function uniq(arr){ return [...new Set(arr.filter(Boolean))]; }
function fillSingleSelect(sel, values, placeholder){
  const current = sel.value;
  sel.innerHTML = '';
  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = placeholder || 'Any';
  sel.appendChild(ph);
  for (const v of values){
    const o = document.createElement('option');
    o.value = v; o.textContent = v;
    sel.appendChild(o);
  }
  if (current && values.includes(current)) sel.value = current;
}
// Ensure a select has the given option (so a saved pref value is selectable
// even if the active channel's data doesn't include it).
function ensureSelectHas(sel, val){
  if (!val) return;
  if (![...sel.options].some(o => o.value === val)){
    const o = document.createElement('option');
    o.value = val; o.textContent = val;
    sel.appendChild(o);
  }
}
function fillMaritalBox(box, statuses){
  box.innerHTML = '';
  statuses.forEach(s => {
    const lab = document.createElement('label');
    lab.className = 'checkrow';
    lab.innerHTML = `<input type="checkbox" value="${escapeHtml(s)}" data-marital> ${escapeHtml(s)}`;
    box.appendChild(lab);
  });
}
function rebuildDynamicLists(){
  const data = activeData();
  fillSingleSelect(document.getElementById('country'), uniq(data.map(p=>p.country)).sort(), 'Any country');
  fillSingleSelect(document.getElementById('state'),   uniq(data.map(p=>p.state)).sort(),   'Any state');
  fillMaritalBox(document.getElementById('maritalBox'), uniq(data.map(p=>p.marital_status)).sort());
  document.querySelectorAll('[data-marital]').forEach(c =>
    c.addEventListener('change', () => { page=1; renderBrowse(); }));
  // Default country = India (when no saved prefs override).
  const country = document.getElementById('country');
  if ([...country.options].some(o => o.value === 'India')) country.value = 'India';
}

// ============ FILTER ============
function browseFilters(){
  return {
    keyword:    document.getElementById('q').value.trim() || null,
    gender:     document.getElementById('gender').value || null,
    ageMin:     parseInt(document.getElementById('ageMin').value)||0,
    ageMax:     parseInt(document.getElementById('ageMax').value)||999,
    dateFrom:   document.getElementById('dateFrom').value || null,
    dateTo:     document.getElementById('dateTo').value || null,
    country:    document.getElementById('country').value || null,
    state:      document.getElementById('state').value || null,
    cityTerms:  document.getElementById('city').value.trim().toLowerCase().split(',').map(s=>s.trim()).filter(Boolean),
    profession: document.getElementById('profession').value.trim() || null,
    education:  document.getElementById('education').value.trim() || null,
    marital:    [...document.querySelectorAll('[data-marital]:checked')].map(c=>c.value),
  };
}

function matches(p, c){
  if (c.gender){
    if (p.gender !== c.gender) return false;
  }
  if (p.age != null){
    if (p.age < (c.ageMin||0) || p.age > (c.ageMax||999)) return false;
  } else if ((c.ageMin && c.ageMin>18) || (c.ageMax && c.ageMax<60)){
    return false;
  }
  if (c.dateFrom || c.dateTo){
    const d = (p.posted_at || '').slice(0,10);
    if (!d) return false;
    if (c.dateFrom && d < c.dateFrom) return false;
    if (c.dateTo   && d > c.dateTo)   return false;
  }
  if (c.country && p.country !== c.country) return false;
  if (c.state   && p.state   !== c.state)   return false;
  if (c.cityTerms && c.cityTerms.length){
    const loc = ((p.city||'')+' '+(p.state||'')).toLowerCase();
    if (!c.cityTerms.some(t => loc.includes(t))) return false;
  }
  if (c.profession && !(p.profession||'').toLowerCase().includes(c.profession.toLowerCase())) return false;
  if (c.education  && !(p.education ||'').toLowerCase().includes(c.education .toLowerCase())) return false;
  if (c.marital && c.marital.length && !c.marital.includes(p.marital_status)) return false;
  if (c.keyword && !(p.raw_text||'').toLowerCase().includes(c.keyword.toLowerCase())) return false;
  return true;
}

function activeFilterCount(){
  let n = 0;
  if (document.getElementById('q').value.trim()) n++;
  if (document.getElementById('gender').value) n++;
  if (document.getElementById('ageMin').value || document.getElementById('ageMax').value) n++;
  if (document.getElementById('dateFrom').value || document.getElementById('dateTo').value) n++;
  if (document.getElementById('country').value) n++;
  if (document.getElementById('state').value) n++;
  if (document.getElementById('city').value.trim()) n++;
  if (document.getElementById('profession').value.trim()) n++;
  if (document.getElementById('education').value.trim()) n++;
  if (document.querySelectorAll('[data-marital]:checked').length) n++;
  return n;
}
function updateFilterBadge(){
  const n = activeFilterCount();
  const b = document.getElementById('filterBadgeCount');
  if (!b) return;
  b.textContent = n;
  b.classList.toggle('zero', n===0);
}

// ============ DATE PRESETS ============
function applyDatePreset(days){
  const dateTo = document.getElementById('dateTo');
  const dateFrom = document.getElementById('dateFrom');
  if (!days){
    dateTo.value = '';
    dateFrom.value = '';
    activePreset = 'all';
  } else {
    const now = new Date();
    const from = new Date(now);
    from.setDate(from.getDate() - days);
    dateFrom.value = from.toISOString().slice(0,10);
    dateTo.value   = now.toISOString().slice(0,10);
    activePreset = String(days);
  }
  document.querySelectorAll('#datePresets button').forEach(b => {
    b.classList.toggle('active', b.dataset.days === activePreset);
  });
  page = 1;
  renderBrowse();
}
document.getElementById('datePresets').addEventListener('click', e => {
  if (e.target.matches('button[data-days]')) applyDatePreset(parseInt(e.target.dataset.days, 10));
});
['dateFrom','dateTo'].forEach(id => {
  document.getElementById(id).addEventListener('input', () => {
    activePreset = null;
    document.querySelectorAll('#datePresets button').forEach(b => b.classList.remove('active'));
  });
});

// ============ RAW-TEXT FORMATTING ============
function extractProfileCode(raw){
  if (!raw) return null;
  const m = raw.match(/profile\s*code\b[\s:#\-]{0,5}([A-Za-z]?\d{3,5}[A-Za-z]?)/i);
  return m ? m[1].toUpperCase() : null;
}
const SKIP_LINE_RX = /^(profile\s*code|bride\s*details|groom\s*details|disclose\s*later|disclaimer|note|---+|===+)/i;
const KV_PARSE_RX = /^([A-Za-z][A-Za-z\s/(),.&'\-]{1,45})\s*[:\-]\s*(.+)$/;
function parseRawProfile(raw){
  if (!raw) return [];
  const cleaned = raw.replace(/\*+/g,'').replace(/__+/g,'');
  const lines = cleaned.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const seen = new Map();
  for (const line of lines){
    if (SKIP_LINE_RX.test(line)) continue;
    const m = line.match(KV_PARSE_RX);
    if (!m) continue;
    const label = m[1].trim().replace(/\s+/g,' ');
    const value = m[2].trim().replace(/^["'\s]+|["'\s]+$/g,'');
    if (!value || value.length > 600) continue;
    const key = label.toLowerCase();
    if (!seen.has(key)) seen.set(key, [label, value]);
  }
  return [...seen.values()];
}
const RAW_HEADER_RX = /^(profile\s*code\b.*|bride\s*details|groom\s*details)$/i;
const RAW_KV_RX = /^([A-Za-z][A-Za-z0-9\s/()&,.'\-]{0,55}?)\s*:\s*(.*)$/;
function formatRawProfile(raw){
  if (!raw) return '<div class="raw-message"><div class="raw-text">No details available.</div></div>';
  const cleaned = raw.replace(/\*+/g,'').replace(/__+/g,'');
  const lines = cleaned.split(/\r?\n/);
  const out = [];
  for (const original of lines){
    const trimmed = original.trim();
    if (!trimmed){
      if (out.length && !out[out.length-1].includes('class="raw-blank"')){
        out.push('<div class="raw-blank"></div>');
      }
      continue;
    }
    if (RAW_HEADER_RX.test(trimmed)){
      out.push(`<div class="raw-header">${escapeHtml(trimmed)}</div>`);
      continue;
    }
    const kv = trimmed.match(RAW_KV_RX);
    if (kv && kv[2] !== undefined && kv[2].length > 0){
      out.push(`<div class="raw-line"><span class="raw-key">${escapeHtml(kv[1].trim())}</span><span class="raw-val">${escapeHtml(kv[2].trim())}</span></div>`);
      continue;
    }
    out.push(`<div class="raw-text">${escapeHtml(trimmed)}</div>`);
  }
  return `<div class="raw-message">${out.join('')}</div>`;
}

// ============ CARD ============
function renderCard(p){
  const code = extractProfileCode(p.raw_text);
  const codeEl = code
    ? `<span class="profile-code"><span class="pc-label">Profile</span><span class="pc-num">${escapeHtml(code)}</span></span>`
    : '';
  const sourceEl = p.channel
    ? `<span class="source-badge src-${escapeHtml(p.channel)}" title="From ${escapeHtml(channelLabel(p.channel))}">${escapeHtml(channelLabel(p.channel))}</span>`
    : '';
  const posted = formatDate(p.posted_at);
  const postedEl = posted ? `<span class="posted">Posted · ${posted}</span>` : '';
  const headerLeft = (codeEl || sourceEl) ? `<div class="ch-left">${codeEl}${sourceEl}</div>` : '';
  const headerRow = (headerLeft || posted) ? `<div class="card-header">${headerLeft}${postedEl}</div>` : '';

  const genderClass = p.gender || '';
  const genderLabel = p.gender || '';
  const genderBadge = genderClass ? `<span class="gender-badge gender-${genderClass}">${escapeHtml(genderLabel)}</span>` : '';
  const ageEl = p.age != null ? `<span class="age-badge">${p.age}</span>` : '';
  const locParts = [p.city, p.state].filter(Boolean);
  const locText = locParts.length ? locParts.map(escapeHtml).join(', ') : (p.country ? escapeHtml(p.country) : '');
  const locEl = locText ? `<span class="loc-badge">${locText}</span>` : '';

  const pairs = parseRawProfile(p.raw_text);
  const lookup = {};
  for (const [k,v] of pairs) lookup[k.toLowerCase()] = v;
  const complexion = lookup['complexion'] || lookup['skin'] || '';

  const facts = [];
  if (p.height)     facts.push(`<span class="fact"><span class="fact-icon">📏</span><span class="fact-key">Height</span> ${escapeHtml(p.height)}</span>`);
  if (complexion)   facts.push(`<span class="fact"><span class="fact-icon">✨</span><span class="fact-key">Complexion</span> ${escapeHtml(complexion)}</span>`);
  if (p.profession) facts.push(`<span class="fact"><span class="fact-icon">💼</span><span class="fact-key">Profession</span> ${escapeHtml(p.profession)}</span>`);

  // Note: the "Looking for" callout was removed from the card summary on
  // purpose — the full text is still available inside "Complete details".

  return `<div class="card">
    ${headerRow}
    <div class="head-line">${genderBadge}${ageEl}${locEl}</div>
    ${facts.length?`<div class="fact-row">${facts.join('')}</div>`:''}
    <details class="complete">
      <summary><span class="caret">›</span>Complete details</summary>
      <div class="complete-body">${formatRawProfile(p.raw_text)}</div>
    </details>
    <div class="foot">
      <a class="tg-link" href="${p.telegram_url}" target="_blank" rel="noopener">Open in Telegram ↗</a>
      ${shortlistBtnHtml(p)}
    </div>
  </div>`;
}

function shortlistBtnHtml(p){
  const on = isShortlisted(p.channel, p.msg_id);
  const entry = entryFor(p.channel, p.msg_id);
  return `<button class="shortlist-btn${on?' on':''}" data-entry="${escapeHtml(entry)}" data-channel="${escapeHtml(p.channel)}" data-msg-id="${p.msg_id}" onclick="toggleShortlistFromBtn(this)" aria-label="${on?'Remove from':'Add to'} shortlist">
    <span class="heart-icon">${on?'♥':'♡'}</span>
    <span>${on?'Shortlisted':'Shortlist'}</span>
  </button>`;
}

// ============ BROWSE RENDER ============
function renderBrowse(){
  const data = activeData();
  if (!data.length && !dataCache[activeChannel]){
    // Data not loaded yet — show loading state
    showLoading(activeChannel);
    return;
  }
  const c = browseFilters();
  const filtered = data.filter(p => matches(p, c));
  const total = filtered.length;
  document.getElementById('count').innerHTML = `<strong>${total.toLocaleString()}</strong> matching profiles`;

  const totalPages = Math.max(1, Math.ceil(total/PER_PAGE));
  if (page > totalPages) page = totalPages;
  const slice = filtered.slice((page-1)*PER_PAGE, page*PER_PAGE);

  const out = document.getElementById('results');
  out.innerHTML = slice.length
    ? slice.map(p => renderCard(p)).join('')
    : '<div class="empty"><span class="icon">🔎</span>No profiles match those filters.<br>Try loosening them.</div>';

  const pag = document.getElementById('pagination');
  if (total > PER_PAGE){
    pag.innerHTML = `
      <button class="btn" ${page<=1?'disabled':''} onclick="page=1;renderBrowse();window.scrollTo(0,0)">« First</button>
      <button class="btn" ${page<=1?'disabled':''} onclick="page--;renderBrowse();window.scrollTo(0,0)">‹ Prev</button>
      <span class="pageinfo">Page ${page} of ${totalPages}</span>
      <button class="btn" ${page>=totalPages?'disabled':''} onclick="page++;renderBrowse();window.scrollTo(0,0)">Next ›</button>
      <button class="btn" ${page>=totalPages?'disabled':''} onclick="page=${totalPages};renderBrowse();window.scrollTo(0,0)">Last »</button>`;
  } else { pag.innerHTML = ''; }

  updateFilterBadge();

  document.getElementById('downloadCsv').onclick = e => {
    e.preventDefault();
    const cols = ['msg_id','posted_at','gender','age','marital_status','city','state','country','education','profession','height','looking_for','telegram_url'];
    const esc = v => v==null?'':`"${String(v).replace(/"/g,'""')}"`;
    const csv = [cols.join(','), ...filtered.map(p=>cols.map(c=>esc(p[c])).join(','))].join('\n');
    const blob = new Blob([csv], {type:'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `profiles_${activeChannel}.csv`; a.click();
    URL.revokeObjectURL(url);
  };
}

function resetFilters(opts){
  ['q','ageMin','ageMax','city','profession','education','dateFrom','dateTo'].forEach(id => document.getElementById(id).value='');
  document.getElementById('gender').value = '';
  document.getElementById('country').value = '';
  document.getElementById('state').value = '';
  document.querySelectorAll('[data-marital]').forEach(c => c.checked = false);
  document.querySelectorAll('#datePresets button').forEach(b => b.classList.remove('active'));
  activePreset = null;
  page = 1;
  if (!opts || opts.rerender !== false) renderBrowse();
}

// ============ EVENT WIRING ============
['q','gender','ageMin','ageMax','city','profession','education','dateFrom','dateTo']
  .forEach(id => document.getElementById(id).addEventListener('input', () => { page=1; renderBrowse(); }));
['country','state'].forEach(id =>
  document.getElementById(id).addEventListener('change', () => { page=1; renderBrowse(); }));
// Browse aside dropdowns also need styling cleanup for single-select native UI

// ============ FIRST RENDER ============
(async () => {
  migrateShortlistStorage();
  migratePrefsStorage();
  renderHeaderMeta();
  renderChannelSwitch();
  updatePrefsBadge();
  updateShortlistBadge();
  showLoading(activeChannel);
  try {
    await ensureChannelData(activeChannel);
    rebuildDynamicLists();
    applySavedPrefs();   // overlay user's saved preferences (if any)
    renderBrowse();
  } catch (err) {
    document.getElementById('results').innerHTML = `<div class="empty"><span class="icon">⚠</span>Couldn't load profiles. ${escapeHtml(String(err.message||err))}<br><br><button class="btn" onclick="location.reload()">Retry</button></div>`;
  }
})();
</script>
</body>
</html>"""

html = (HTML
        .replace("__CHANNELS__",    channels_json)
        .replace("__BUILD_ID__",    build_id)
        .replace("__GENERATED_AT__", generated_at)
        .replace("__TOTAL_COUNT__", str(total_profiles)))

OUT_LOCAL.write_text(html, encoding="utf-8")
print(f"Wrote {OUT_LOCAL} ({OUT_LOCAL.stat().st_size//1024} KB)")

(PUBLIC / "index.html").write_text(html, encoding="utf-8")
print(f"Wrote {PUBLIC / 'index.html'} (deploy directory)")
