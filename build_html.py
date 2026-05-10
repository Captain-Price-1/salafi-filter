"""Read profiles.db and emit a single self-contained profiles.html with a 3-tab UI:
   Browse / My Preferences / Notifications.
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
DB   = ROOT / "profiles.db"
OUT  = ROOT / "profiles.html"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = [dict(r) for r in conn.execute(
    "SELECT msg_id, posted_at, raw_text, gender, age, marital_status, children, "
    "city, state, country, education, profession, height, looking_for, "
    "has_photo, telegram_url FROM profiles WHERE is_profile=1 ORDER BY msg_id DESC"
)]
conn.close()

for r in rows:
    if r["raw_text"]:
        r["raw_text"] = r["raw_text"].strip()

data_json     = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
generated_at  = datetime.now().strftime("%Y-%m-%d %H:%M")
profile_count = len(rows)

print(f"Embedding {profile_count} profiles, ~{len(data_json)//1024} KB of data")

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Salafi Marriage — Profile Filter</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0F4C3A">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
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
  --new:#9C3D1A;
  --new-soft:#FBE6D6;
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

/* ---------- Header ---------- */
header{
  background:var(--panel);
  border-bottom:1px solid var(--border);
  padding:18px 32px 0;
  position:sticky;top:0;z-index:30;
}
.titlebar{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px}
header h1{
  margin:0;font:600 22px/1.15 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.01em;
  display:flex;align-items:center;gap:12px;
}
.crest{
  display:inline-flex;align-items:center;justify-content:center;
  width:38px;height:38px;border-radius:50%;
  background:linear-gradient(135deg,var(--accent),#1A6B53);
  color:#fff;font-size:18px;box-shadow:0 4px 10px rgba(15,76,58,.22);
}
header .meta{
  color:var(--muted);font-size:13px;font-weight:400;
  margin-top:4px;display:flex;flex-wrap:wrap;gap:6px 14px;
}
header .meta strong{color:var(--ink);font-weight:600}
header .meta .dot{width:3px;height:3px;background:var(--muted-soft);border-radius:50%;align-self:center}

/* ---------- Tabs ---------- */
nav.tabs{display:flex;gap:2px;margin-top:14px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.tab{
  background:none;border:none;padding:11px 18px 13px;
  font:500 14px/1 'Inter',sans-serif;color:var(--muted);
  cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;
  transition:color var(--t),border-color var(--t);
}
.tab:hover{color:var(--ink)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab .badge{
  display:inline-block;background:var(--new);color:#fff;
  border-radius:999px;padding:2px 8px;font-size:11px;font-weight:700;
  margin-left:6px;line-height:1.4;vertical-align:middle;
}
.tab .badge.zero{display:none}

/* ---------- Layout ---------- */
.tab-section{display:none;padding:26px 32px;max-width:1320px;margin:0 auto}
.tab-section.active{display:block}
.layout{display:grid;grid-template-columns:300px 1fr;gap:28px;align-items:flex-start}

/* ---------- Aside (filters) ---------- */
aside{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:22px;
  position:sticky;top:148px;
  max-height:calc(100vh - 168px);overflow-y:auto;
  box-shadow:var(--shadow-sm);
}
aside h3{
  font:600 11px/1 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.1em;
  color:var(--muted);margin:18px 0 10px;
  display:flex;align-items:center;gap:8px;
}
aside h3:first-child{margin-top:0}
aside h3::after{
  content:"";flex:1;height:1px;background:var(--border-soft);
}
aside label{display:block;margin:4px 0;font-size:13px;color:var(--ink-soft)}
aside input[type=text],aside input[type=number],aside select{
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

.range{display:flex;gap:8px;align-items:center}
.range input{width:0;flex:1;text-align:center}
.range span{color:var(--muted-soft);font-size:14px}

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
.btn.gold{background:var(--gold);color:#fff;border-color:var(--gold)}
.btn.gold:hover{background:#9F7A40;color:#fff;border-color:#9F7A40}
.btn:disabled{opacity:.45;cursor:not-allowed;pointer-events:none}
.btn.ghost{background:transparent;border-color:transparent}
.btn.ghost:hover{background:var(--accent-pale);border-color:transparent}

/* ---------- Summary / cards ---------- */
.topbar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px}
.summary{color:var(--muted);font-size:13px}
.summary strong{color:var(--ink);font-size:16px;font-weight:600;font-family:'Playfair Display',Georgia,serif}

.card{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:18px 20px;margin-bottom:14px;
  box-shadow:var(--shadow-sm);
  transition:box-shadow var(--t),transform var(--t),border-color var(--t);
  position:relative;
}
.card:hover{box-shadow:var(--shadow);transform:translateY(-1px);border-color:#D9D0BC}
.card.new{border-color:#D9C29F;box-shadow:0 2px 12px rgba(181,139,74,.10)}
.card.new::before{
  content:"NEW";position:absolute;top:14px;right:14px;
  background:var(--gold);color:#fff;
  font:700 10px/1 'Inter',sans-serif;letter-spacing:.1em;
  padding:5px 9px;border-radius:4px;
}
/* Card header row — profile code (left) + posted date (right) */
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

/* Headline chip row — gender, age, location */
.card .head-line{
  display:flex;flex-wrap:wrap;align-items:center;
  gap:8px 10px;
}
.gender-badge{
  display:inline-flex;align-items:center;
  padding:5px 13px;border-radius:999px;
  font:700 11px/1.5 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.09em;
  border:1px solid transparent;
}
.gender-badge.gender-female{background:#FBE9EE;color:#A0466A;border-color:#F0CFD8}
.gender-badge.gender-male{background:#F1E5D5;color:#7C5234;border-color:#E1CCB1}
.gender-badge.gender-unknown{background:#F0EBE0;color:#6B5E4A;border-color:#DDD5C2}

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

/* Posted-date pill */
.card .posted{
  display:inline-flex;align-items:center;gap:5px;
  background:var(--gold-soft);color:#8C6B36;
  padding:4px 11px;border-radius:6px;
  font:700 10.5px/1.5 'Inter',sans-serif;
  letter-spacing:.07em;text-transform:uppercase;
  width:fit-content;
}

/* Fact row — height, complexion, profession */
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

/* Looking for callout */
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

/* Complete details — toggle */
.card details.complete{margin-top:16px;border-top:1px solid var(--border-soft);padding-top:14px}
.card details.complete summary{
  cursor:pointer;list-style:none;
  display:inline-flex;align-items:center;gap:6px;
  font:600 13px/1 'Inter',sans-serif;
  color:var(--accent);user-select:none;
  padding:6px 0;
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
  padding:18px 20px;
}
.raw-message{
  display:flex;flex-direction:column;gap:5px;
  font:14px/1.6 'Inter',sans-serif;color:var(--ink-soft);
}
.raw-message .raw-header{
  font:700 11px/1.4 'Inter',sans-serif;
  text-transform:uppercase;letter-spacing:.12em;
  color:var(--accent);padding:6px 0 7px;
  border-bottom:1px solid var(--border);
  margin:10px 0 6px;
}
.raw-message .raw-header:first-child{margin-top:0}
.raw-message .raw-line{display:flex;flex-wrap:wrap;gap:4px 8px;padding:1px 0}
.raw-message .raw-line .raw-key{
  font-weight:600;color:var(--ink);flex-shrink:0;
}
.raw-message .raw-line .raw-key::after{content:":";opacity:.55;margin-left:1px}
.raw-message .raw-line .raw-val{color:var(--ink-soft);word-break:break-word;flex:1;min-width:140px}
.raw-message .raw-text{color:var(--ink-soft)}
.raw-message .raw-blank{height:6px}
@media (max-width: 600px){
  .complete-body{padding:14px 16px}
}

/* Foot — Open in Telegram only */
.card .foot{
  margin-top:14px;font-size:13px;
}
.card .foot a{
  color:var(--accent);text-decoration:none;font-weight:600;
  display:inline-flex;align-items:center;gap:5px;
}
.card .foot a:hover{text-decoration:underline}

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

/* ---------- Preferences ---------- */
.prefs-card{
  background:var(--panel);border:1px solid var(--border);
  border-radius:var(--radius);padding:32px 36px;
  max-width:740px;margin:0 auto;box-shadow:var(--shadow-sm);
}
.prefs-card h2{
  margin:0 0 6px;font:600 26px/1.2 'Playfair Display',Georgia,serif;
  color:var(--accent);letter-spacing:-.01em;
}
.prefs-card .subtitle{color:var(--muted);font-size:14px;margin-bottom:20px}
.field{margin:18px 0}
.field>label{display:block;font-weight:500;margin-bottom:7px;color:var(--ink);font-size:14px}
.field input[type=text],.field input[type=number],.field select{
  padding:10px 13px;border:1px solid var(--border);border-radius:var(--radius-xs);
  font:14px/1.2 'Inter',sans-serif;width:100%;background:#fff;color:var(--ink);
  transition:border-color var(--t),box-shadow var(--t);
}
.field input:focus,.field select:focus{
  outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft);
}
.field-row{display:flex;gap:14px}
.field-row .field{flex:1;margin:18px 0}
.help{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5}
.banner{padding:14px 18px;border-radius:var(--radius-sm);margin:14px 0;font-size:14px;line-height:1.5}
.banner.ok{background:var(--accent-soft);color:var(--accent);border:1px solid #C4DECC}
.banner.warn{background:var(--warn-soft);color:var(--warn);border:1px solid #F4D8A1}
.actions{display:flex;gap:10px;margin-top:24px;flex-wrap:wrap}

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

@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}

/* ---------- Responsive ---------- */
@media (max-width: 960px){
  .layout{grid-template-columns:1fr;gap:14px}
  .tab-section{padding:22px}
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
    content:"";display:block;
    width:42px;height:4px;background:var(--muted-soft);
    border-radius:2px;margin:0 auto 18px;
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
@media (max-width: 600px){
  header{padding:14px 16px 0}
  header h1{font-size:18px}
  .crest{width:32px;height:32px;font-size:15px}
  header .meta{font-size:12px;gap:4px 10px}
  nav.tabs{margin-top:10px}
  .tab{padding:9px 14px;font-size:13px}
  .tab-section{padding:18px 14px}
  .card{padding:14px 16px}
  .card .facts .age{font-size:22px;margin-right:8px}
  .card .facts{font-size:14px}
  .card .top{flex-direction:column;align-items:flex-start;gap:8px}
  .card .lookingfor{font-size:13px;padding:9px 12px}
  .field-row{flex-direction:column;gap:0}
  .prefs-card{padding:22px 18px}
  .prefs-card h2{font-size:22px}
  .summary{font-size:12px}
  .summary strong{font-size:15px}
  .actions{gap:8px}
  .pagination{gap:6px;padding:12px;flex-wrap:wrap}
  .pagination .pageinfo{flex-basis:100%;text-align:center;order:-1;margin-bottom:4px}
}
</style>
</head>
<body>

<header>
  <div class="titlebar">
    <div>
      <h1><span class="crest">☪</span> Salafi Marriage</h1>
      <div class="meta">
        <span><strong>__PROFILE_COUNT__</strong> profiles</span>
        <span class="dot"></span>
        <span>updated __GENERATED_AT__</span>
        <span class="dot"></span>
        <span>from <a href="https://t.me/salafimarriage1" target="_blank" rel="noopener">@salafimarriage1</a></span>
      </div>
    </div>
  </div>
  <nav class="tabs">
    <button class="tab active" data-tab="browse">Browse</button>
    <button class="tab" data-tab="prefs">My Preferences</button>
    <button class="tab" data-tab="notif">Notifications<span class="badge zero" id="notifBadge">0</span></button>
  </nav>
</header>

<!-- ============ BROWSE TAB ============ -->
<section class="tab-section active" id="browse-section">
  <div class="layout">
    <aside id="filterAside">
      <button type="button" class="drawer-close" id="drawerClose" aria-label="Close filters">✕</button>

      <h3>Search</h3>
      <input type="text" id="q" placeholder="Keyword in any field…">

      <h3>Gender</h3>
      <select id="gender">
        <option value="">Any</option>
        <option value="female">Female (sister)</option>
        <option value="male">Male (brother)</option>
        <option value="unknown">Unknown</option>
      </select>

      <h3>Age</h3>
      <div class="range">
        <input type="number" id="ageMin" min="18" max="60" placeholder="18">
        <span>—</span>
        <input type="number" id="ageMax" min="18" max="60" placeholder="60">
      </div>

      <h3>Marital Status</h3>
      <div id="maritalBox"></div>

      <h3>Country</h3>
      <select id="country" multiple size="6"></select>

      <h3>City</h3>
      <input type="text" id="city" placeholder="Type city name…">

      <h3>Profession</h3>
      <input type="text" id="profession" placeholder="e.g. doctor">

      <h3>Education</h3>
      <input type="text" id="education" placeholder="e.g. mbbs">

      <h3>Other</h3>
      <label class="checkrow"><input type="checkbox" id="hasPhoto"> Only profiles with a photo</label>

      <div class="filter-actions">
        <button class="btn" onclick="loadPrefsIntoBrowse()">↓ Load my preferences</button>
        <button class="btn" onclick="resetFilters()">Reset filters</button>
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

<!-- ============ PREFERENCES TAB ============ -->
<section class="tab-section" id="prefs-section">
  <div class="prefs-card">
    <h2>What I'm Looking For</h2>
    <div class="subtitle">Save your criteria here once. They power the Notifications tab and can be applied to Browse with one click.</div>

    <div id="prefsBanner"></div>

    <form id="prefsForm" onsubmit="event.preventDefault();savePrefs()">
      <div class="field">
        <label>Gender</label>
        <select id="p_gender">
          <option value="">Any</option>
          <option value="female">Female (sister)</option>
          <option value="male">Male (brother)</option>
        </select>
      </div>

      <div class="field-row">
        <div class="field">
          <label>Minimum age</label>
          <input type="number" id="p_ageMin" min="18" max="60" placeholder="18">
        </div>
        <div class="field">
          <label>Maximum age</label>
          <input type="number" id="p_ageMax" min="18" max="60" placeholder="40">
        </div>
      </div>

      <div class="field">
        <label>Marital status (any of)</label>
        <div id="p_maritalBox"></div>
      </div>

      <div class="field">
        <label>Country (any of)</label>
        <select id="p_country" multiple size="6"></select>
      </div>

      <div class="field">
        <label>City contains</label>
        <input type="text" id="p_city" placeholder="e.g. Hyderabad, Mumbai, Bangalore">
        <div class="help">A single city name, or a comma-separated list. Match is case-insensitive and includes the State field too.</div>
      </div>

      <div class="field">
        <label>Profession contains</label>
        <input type="text" id="p_profession" placeholder="e.g. doctor, engineer">
      </div>

      <div class="field">
        <label>Education contains</label>
        <input type="text" id="p_education" placeholder="e.g. alim, hafiz, mbbs">
      </div>

      <div class="field">
        <label>Any other keyword (optional)</label>
        <input type="text" id="p_keyword" placeholder="e.g. salafi, niqab, beard, masjid">
        <div class="help">Free-text match against the full post.</div>
      </div>

      <div class="actions">
        <button type="submit" class="btn primary">Save preferences</button>
        <button type="button" class="btn" onclick="clearPrefs()">Clear preferences</button>
        <button type="button" class="btn gold" onclick="loadPrefsIntoBrowse();switchTab('browse')">Apply to Browse →</button>
      </div>
    </form>
  </div>
</section>

<!-- ============ NOTIFICATIONS TAB ============ -->
<section class="tab-section" id="notif-section">
  <div class="prefs-card" style="max-width:none">
    <h2>Notifications</h2>
    <div class="subtitle">New profiles posted since you last marked them as read, that match your saved preferences. Auto-refreshes every 5 hours in the background.</div>

    <div id="notifInfo"></div>

    <div class="actions">
      <button type="button" class="btn primary" onclick="markAllRead()">Mark all as read</button>
      <button type="button" class="btn" onclick="switchTab('prefs')">Edit preferences →</button>
    </div>

    <div id="notifResults" style="margin-top:18px"></div>
  </div>
</section>

<div class="drawer-backdrop" id="drawerBackdrop"></div>

<script>
const DATA = __DATA__;
const PER_PAGE = 25;
let page = 1;

// ============ STATE PERSISTENCE ============
const PREFS_KEY = 'salafi_prefs_v1';
const SEEN_KEY  = 'salafi_last_seen_msgid_v1';

function loadPrefs(){
  try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || {}; } catch(e){ return {}; }
}
function storePrefs(p){ localStorage.setItem(PREFS_KEY, JSON.stringify(p)); }
function loadSeenId(){ return parseInt(localStorage.getItem(SEEN_KEY)) || 0; }
function storeSeenId(n){ localStorage.setItem(SEEN_KEY, String(n)); }

// ============ TABS ============
document.querySelectorAll('.tab').forEach(b => {
  b.addEventListener('click', () => switchTab(b.dataset.tab));
});
function switchTab(name){
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.tab-section').forEach(s => s.classList.toggle('active', s.id===name+'-section'));
  if (name==='notif') renderNotifications();
  if (name==='prefs') hydratePrefsForm();
  closeDrawer();
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

// ============ DROPDOWNS ============
function uniq(arr){ return [...new Set(arr.filter(Boolean))]; }
const countries = uniq(DATA.map(p=>p.country)).sort();
const statuses  = uniq(DATA.map(p=>p.marital_status)).sort();

function fillCountrySelect(sel){
  countries.forEach(c => { const o=document.createElement('option'); o.value=c; o.textContent=c; sel.appendChild(o); });
}
fillCountrySelect(document.getElementById('country'));
fillCountrySelect(document.getElementById('p_country'));

function fillMaritalBox(box, idPrefix){
  statuses.forEach(s => {
    const lab = document.createElement('label');
    lab.className = 'checkrow';
    lab.innerHTML = `<input type="checkbox" value="${s}" data-${idPrefix}> ${s}`;
    box.appendChild(lab);
  });
}
fillMaritalBox(document.getElementById('maritalBox'),    'marital');
fillMaritalBox(document.getElementById('p_maritalBox'),  'pmarital');

// ============ COMMON FILTER ============
function matches(p, c){
  if (c.gender){
    if (c.gender==='unknown'){ if (p.gender) return false; }
    else if (p.gender !== c.gender) return false;
  }
  if (p.age != null){
    if (p.age < (c.ageMin||0) || p.age > (c.ageMax||999)) return false;
  } else if ((c.ageMin && c.ageMin>18) || (c.ageMax && c.ageMax<60)){
    return false;
  }
  if (c.countries && c.countries.length && !c.countries.includes(p.country)) return false;
  if (c.cityTerms && c.cityTerms.length){
    const loc = ((p.city||'')+' '+(p.state||'')).toLowerCase();
    if (!c.cityTerms.some(t => loc.includes(t))) return false;
  }
  if (c.profession && !(p.profession||'').toLowerCase().includes(c.profession.toLowerCase())) return false;
  if (c.education  && !(p.education ||'').toLowerCase().includes(c.education .toLowerCase())) return false;
  if (c.marital && c.marital.length && !c.marital.includes(p.marital_status)) return false;
  if (c.keyword && !(p.raw_text||'').toLowerCase().includes(c.keyword.toLowerCase())) return false;
  if (c.hasPhoto && !p.has_photo) return false;
  return true;
}

// ============ BROWSE TAB ============
function browseFilters(){
  return {
    keyword:    document.getElementById('q').value.trim() || null,
    gender:     document.getElementById('gender').value || null,
    ageMin:     parseInt(document.getElementById('ageMin').value)||0,
    ageMax:     parseInt(document.getElementById('ageMax').value)||999,
    countries:  [...document.querySelectorAll('#country option:checked')].map(o=>o.value),
    cityTerms:  document.getElementById('city').value.trim().toLowerCase().split(',').map(s=>s.trim()).filter(Boolean),
    profession: document.getElementById('profession').value.trim() || null,
    education:  document.getElementById('education').value.trim() || null,
    marital:    [...document.querySelectorAll('[data-marital]:checked')].map(c=>c.value),
    hasPhoto:   document.getElementById('hasPhoto').checked,
  };
}

function activeFilterCount(){
  let n = 0;
  if (document.getElementById('q').value.trim()) n++;
  if (document.getElementById('gender').value) n++;
  if (document.getElementById('ageMin').value || document.getElementById('ageMax').value) n++;
  if (document.querySelectorAll('#country option:checked').length) n++;
  if (document.getElementById('city').value.trim()) n++;
  if (document.getElementById('profession').value.trim()) n++;
  if (document.getElementById('education').value.trim()) n++;
  if (document.querySelectorAll('[data-marital]:checked').length) n++;
  if (document.getElementById('hasPhoto').checked) n++;
  return n;
}
function updateFilterBadge(){
  const n = activeFilterCount();
  const b = document.getElementById('filterBadgeCount');
  if (!b) return;
  b.textContent = n;
  b.classList.toggle('zero', n===0);
}

function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

// ---------- Lightweight key-value parser (used for chip-row complexion lookup) ----------
const SKIP_LINE_RX = /^(profile\s*code|bride\s*details|groom\s*details|disclose\s*later|disclaimer|note|---+|===+)/i;
const KV_RX = /^([A-Za-z][A-Za-z\s/(),.&'\-]{1,45})\s*[:\-]\s*(.+)$/;

function parseRawProfile(raw){
  if (!raw) return [];
  const cleaned = raw.replace(/\*+/g,'').replace(/__+/g,'');
  const lines = cleaned.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const seen = new Map();
  for (const line of lines){
    if (SKIP_LINE_RX.test(line)) continue;
    const m = line.match(KV_RX);
    if (!m) continue;
    const label = m[1].trim().replace(/\s+/g,' ');
    const value = m[2].trim().replace(/^["'\s]+|["'\s]+$/g,'');
    if (!value || value.length > 600) continue;
    const key = label.toLowerCase();
    if (!seen.has(key)) seen.set(key, [label, value]);
  }
  return [...seen.values()];
}

// ---------- Profile code extractor ----------
function extractProfileCode(raw){
  if (!raw) return null;
  const m = raw.match(/profile\s*code\b[\s:#\-]{0,5}([A-Za-z]?\d{3,5}[A-Za-z]?)/i);
  return m ? m[1].toUpperCase() : null;
}

// ---------- Minimal "Complete details" formatter — preserves ALL original lines ----------
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
      // Collapse multiple consecutive blanks into a single small spacer
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
      const label = kv[1].trim();
      const value = kv[2].trim();
      out.push(`<div class="raw-line"><span class="raw-key">${escapeHtml(label)}</span><span class="raw-val">${escapeHtml(value)}</span></div>`);
      continue;
    }
    out.push(`<div class="raw-text">${escapeHtml(trimmed)}</div>`);
  }
  return `<div class="raw-message">${out.join('')}</div>`;
}

// ---------- Card ----------
function renderCard(p, opts){
  opts = opts || {};

  // Header row: profile code (left) + posted date pill (right)
  const code = extractProfileCode(p.raw_text);
  const codeEl = code
    ? `<span class="profile-code"><span class="pc-label">Profile</span><span class="pc-num">${escapeHtml(code)}</span></span>`
    : '';
  const posted = p.posted_at ? p.posted_at.slice(0,10) : '';
  const postedEl = posted ? `<span class="posted">Posted · ${posted}</span>` : '';
  const headerRow = (code || posted) ? `<div class="card-header">${codeEl}${postedEl}</div>` : '';

  // Chip row: gender, age, location (city + state only — no country)
  const genderClass = p.gender || 'unknown';
  const genderLabel = p.gender || 'unknown';
  const genderBadge = `<span class="gender-badge gender-${genderClass}">${escapeHtml(genderLabel)}</span>`;
  const ageEl = p.age != null ? `<span class="age-badge">${p.age}</span>` : '';

  const locParts = [p.city, p.state].filter(Boolean);
  const locText = locParts.length
    ? locParts.map(escapeHtml).join(', ')
    : (p.country ? escapeHtml(p.country) : '');
  const locEl = locText ? `<span class="loc-badge">${locText}</span>` : '';

  // Pull complexion from raw text for the highlighted chip below
  const pairs = parseRawProfile(p.raw_text);
  const lookup = {};
  for (const [k,v] of pairs) lookup[k.toLowerCase()] = v;
  const complexion = lookup['complexion'] || lookup['skin'] || '';

  const facts = [];
  if (p.height)     facts.push(`<span class="fact"><span class="fact-icon">📏</span><span class="fact-key">Height</span> ${escapeHtml(p.height)}</span>`);
  if (complexion)   facts.push(`<span class="fact"><span class="fact-icon">✨</span><span class="fact-key">Complexion</span> ${escapeHtml(complexion)}</span>`);
  if (p.profession) facts.push(`<span class="fact"><span class="fact-icon">💼</span><span class="fact-key">Profession</span> ${escapeHtml(p.profession)}</span>`);

  const lookingFor = p.looking_for
    ? `<div class="lookingfor"><span class="lookingfor-label">Looking for</span>${escapeHtml(p.looking_for)}</div>`
    : '';

  return `<div class="card${opts.isNew?' new':''}">
    ${headerRow}
    <div class="head-line">${genderBadge}${ageEl}${locEl}</div>
    ${facts.length?`<div class="fact-row">${facts.join('')}</div>`:''}
    ${lookingFor}
    <details class="complete">
      <summary><span class="caret">›</span>Complete details</summary>
      <div class="complete-body">${formatRawProfile(p.raw_text)}</div>
    </details>
    <div class="foot">
      <a href="${p.telegram_url}" target="_blank" rel="noopener">Open in Telegram ↗</a>
    </div>
  </div>`;
}

function renderBrowse(){
  const c = browseFilters();
  const filtered = DATA.filter(p => matches(p, c));
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
    a.href = url; a.download = 'filtered_profiles.csv'; a.click();
    URL.revokeObjectURL(url);
  };
}

// ============ PREFERENCES TAB ============
function readPrefsForm(){
  return {
    gender:     document.getElementById('p_gender').value || null,
    ageMin:     parseInt(document.getElementById('p_ageMin').value)||0,
    ageMax:     parseInt(document.getElementById('p_ageMax').value)||999,
    cityTerms:  document.getElementById('p_city').value.trim().toLowerCase().split(',').map(s=>s.trim()).filter(Boolean),
    countries:  [...document.querySelectorAll('#p_country option:checked')].map(o=>o.value),
    marital:    [...document.querySelectorAll('[data-pmarital]:checked')].map(c=>c.value),
    profession: document.getElementById('p_profession').value.trim() || null,
    education:  document.getElementById('p_education').value.trim() || null,
    keyword:    document.getElementById('p_keyword').value.trim() || null,
    hasPhoto:   false,
  };
}

function hydratePrefsForm(){
  const p = loadPrefs();
  document.getElementById('p_gender').value     = p.gender || '';
  document.getElementById('p_ageMin').value     = p.ageMin && p.ageMin>0 ? p.ageMin : '';
  document.getElementById('p_ageMax').value     = p.ageMax && p.ageMax<999 ? p.ageMax : '';
  document.getElementById('p_city').value       = (p.cityTerms||[]).join(', ');
  document.getElementById('p_profession').value = p.profession || '';
  document.getElementById('p_education').value  = p.education || '';
  document.getElementById('p_keyword').value    = p.keyword || '';
  [...document.querySelectorAll('#p_country option')].forEach(o => {
    o.selected = (p.countries||[]).includes(o.value);
  });
  document.querySelectorAll('[data-pmarital]').forEach(cb => {
    cb.checked = (p.marital||[]).includes(cb.value);
  });
  refreshPrefsBanner();
}

function refreshPrefsBanner(){
  const p = loadPrefs();
  const banner = document.getElementById('prefsBanner');
  if (!Object.keys(p).length){
    banner.innerHTML = '<div class="banner warn">No preferences saved yet. Fill in the form below and hit <strong>Save preferences</strong>.</div>';
    return;
  }
  const matchCount = DATA.filter(d => matches(d, p)).length;
  banner.innerHTML = `<div class="banner ok"><strong>${matchCount.toLocaleString()}</strong> profiles in the current data match your saved preferences.</div>`;
}

function savePrefs(){
  const p = readPrefsForm();
  storePrefs(p);
  refreshPrefsBanner();
  const btn = document.querySelector('#prefsForm button[type=submit]');
  const orig = btn.textContent;
  btn.textContent = '✓ Saved';
  setTimeout(()=>{btn.textContent=orig;}, 1200);
  updateNotifBadge();
}

function clearPrefs(){
  if (!confirm('Clear your saved preferences?')) return;
  localStorage.removeItem(PREFS_KEY);
  hydratePrefsForm();
  updateNotifBadge();
}

function loadPrefsIntoBrowse(){
  const p = loadPrefs();
  if (!Object.keys(p).length){ alert('No saved preferences. Set them in the My Preferences tab first.'); return; }
  document.getElementById('q').value = p.keyword || '';
  document.getElementById('gender').value = p.gender || '';
  document.getElementById('ageMin').value = p.ageMin && p.ageMin>0 ? p.ageMin : '';
  document.getElementById('ageMax').value = p.ageMax && p.ageMax<999 ? p.ageMax : '';
  document.getElementById('city').value = (p.cityTerms||[]).join(', ');
  document.getElementById('profession').value = p.profession || '';
  document.getElementById('education').value = p.education || '';
  [...document.querySelectorAll('#country option')].forEach(o => {
    o.selected = (p.countries||[]).includes(o.value);
  });
  document.querySelectorAll('[data-marital]').forEach(cb => {
    cb.checked = (p.marital||[]).includes(cb.value);
  });
  page = 1;
  renderBrowse();
}

function resetFilters(){
  ['q','ageMin','ageMax','city','profession','education'].forEach(id => document.getElementById(id).value='');
  document.getElementById('gender').value = '';
  document.getElementById('hasPhoto').checked = false;
  [...document.querySelectorAll('#country option')].forEach(o => o.selected = false);
  document.querySelectorAll('[data-marital]').forEach(c => c.checked = false);
  page = 1;
  renderBrowse();
}

// ============ NOTIFICATIONS TAB ============
function getNewMatching(){
  const p = loadPrefs();
  if (!Object.keys(p).length) return {prefs:null, list:[]};
  const seen = loadSeenId();
  const list = DATA.filter(d => d.msg_id > seen && matches(d, p));
  return {prefs:p, list};
}

function updateNotifBadge(){
  const {prefs, list} = getNewMatching();
  const badge = document.getElementById('notifBadge');
  badge.textContent = list.length;
  badge.classList.toggle('zero', list.length===0);
}

function renderNotifications(){
  const {prefs, list} = getNewMatching();
  const info = document.getElementById('notifInfo');
  const results = document.getElementById('notifResults');

  if (!prefs){
    info.innerHTML = '<div class="banner warn">You haven\'t saved any preferences yet. Go to <a href="#" onclick="switchTab(\'prefs\');return false">My Preferences</a> first.</div>';
    results.innerHTML = '';
    return;
  }
  const seen = loadSeenId();
  info.innerHTML = `<div class="banner ok">Showing profiles newer than the last "mark all as read" that match your saved preferences.</div>`;
  if (!list.length){
    results.innerHTML = '<div class="empty"><span class="icon">📬</span>Nothing new matches your preferences right now.<br>The scraper will check again automatically.</div>';
    return;
  }
  results.innerHTML = list.map(p => renderCard(p, {isNew:true})).join('');
}

function markAllRead(){
  const maxId = DATA.reduce((m,d) => Math.max(m, d.msg_id), 0);
  storeSeenId(maxId);
  updateNotifBadge();
  renderNotifications();
}

// ============ EVENT WIRING ============
['q','gender','ageMin','ageMax','city','profession','education','hasPhoto']
  .forEach(id => document.getElementById(id).addEventListener('input', () => { page=1; renderBrowse(); }));
document.getElementById('country').addEventListener('change', () => { page=1; renderBrowse(); });
document.querySelectorAll('[data-marital]').forEach(c => c.addEventListener('change', () => { page=1; renderBrowse(); }));

// First-render
renderBrowse();
hydratePrefsForm();
updateNotifBadge();
</script>
</body>
</html>"""

html = (HTML
        .replace("__DATA__", data_json)
        .replace("__GENERATED_AT__", generated_at)
        .replace("__PROFILE_COUNT__", f"{profile_count:,}"))

OUT.write_text(html, encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size//1024} KB)")

PUBLIC = ROOT / "public"
PUBLIC.mkdir(exist_ok=True)
(PUBLIC / "index.html").write_text(html, encoding="utf-8")
print(f"Wrote {PUBLIC / 'index.html'} (deploy directory)")
