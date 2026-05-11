"""
Best-effort regex parser for salafi marriage profile posts.

These channels use semi-structured templates that vary post to post, so we
extract conservatively: when a field is uncertain, we leave it None and let
the user see the raw text in the UI.
"""

from __future__ import annotations
import re
from datetime import datetime
from typing import Optional

# ---------- Indian cities & states (extend as needed) ----------
INDIAN_CITIES = [
    "Mumbai", "Delhi", "New Delhi", "Bangalore", "Bengaluru", "Hyderabad",
    "Chennai", "Kolkata", "Pune", "Ahmedabad", "Surat", "Jaipur", "Lucknow",
    "Kanpur", "Nagpur", "Indore", "Bhopal", "Patna", "Vadodara", "Ghaziabad",
    "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi",
    "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Allahabad", "Prayagraj",
    "Howrah", "Ranchi", "Gwalior", "Jabalpur", "Coimbatore", "Vijayawada",
    "Jodhpur", "Madurai", "Raipur", "Kota", "Guwahati", "Chandigarh",
    "Solapur", "Hubli", "Mysore", "Mysuru", "Tiruchirappalli", "Bareilly",
    "Aligarh", "Moradabad", "Saharanpur", "Gorakhpur", "Bikaner", "Mangalore",
    "Mangaluru", "Belgaum", "Kochi", "Cochin", "Kozhikode", "Calicut",
    "Thiruvananthapuram", "Trivandrum", "Bhubaneswar", "Cuttack", "Dehradun",
    "Noida", "Gurgaon", "Gurugram", "Greater Noida", "Thane", "Navi Mumbai",
    "Nellore", "Tirupati", "Warangal", "Karimnagar", "Hubballi", "Vellore",
    "Erode", "Salem", "Tiruppur", "Pondicherry", "Puducherry", "Goa",
    "Panaji", "Shillong", "Imphal", "Aizawl", "Itanagar", "Gangtok", "Agartala",
    "Hyd", "Blr", "Chn",  # common abbreviations
]
INDIAN_STATES = [
    "Maharashtra", "Karnataka", "Tamil Nadu", "Kerala", "Telangana",
    "Andhra Pradesh", "West Bengal", "Uttar Pradesh", "UP", "Bihar",
    "Madhya Pradesh", "MP", "Rajasthan", "Gujarat", "Punjab", "Haryana",
    "Delhi", "Odisha", "Assam", "Jharkhand", "Chhattisgarh", "Uttarakhand",
    "Himachal Pradesh", "Goa", "Tripura", "Manipur", "Meghalaya", "Nagaland",
    "Mizoram", "Arunachal Pradesh", "Sikkim", "Jammu and Kashmir", "Kashmir",
]

# Build a single regex for fast city/state matching (case-insensitive, word-bounded)
_CITY_RX = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in INDIAN_CITIES) + r")\b", re.IGNORECASE
)
_STATE_RX = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in INDIAN_STATES) + r")\b", re.IGNORECASE
)

# ---------- Field extractors ----------

def _first(rx: re.Pattern, text: str, group: int = 1) -> Optional[str]:
    m = rx.search(text)
    return m.group(group).strip() if m else None


def extract_age(text: str) -> Optional[int]:
    """Extract the poster's age. Returns int (18-70) or None.

    Handles 20+ explicit format variations across these categories:

    DIRECT AGE (the number IS the age)
      1.  "Age (Year of birth): 28"      — parenthesized qualifier + colon
      2.  "Age: 28" / "Age - 28" / "Age :-28"  — labeled, any separator (incl. ":-")
      3.  "Age 28"                        — labeled, no separator
      4.  "Age: 28 years" / "Age- 28 yrs" — labeled with redundant unit
      5.  "28 years old" / "28 yrs old"   — number + unit + "old"
      6.  "28 y/o" / "28 y.o." / "28yo"   — y/o variants
      7.  "28-year-old"                   — hyphenated

    DERIVED FROM YEAR OF BIRTH (4-digit year)
      8.  "DOB: 1998" / "YOB - 1998"      — year only after birth label
      9.  "DOB: 12/05/1998"               — numeric date
      10. "DOB: 12th Aug 1998"            — day-month-year (ordinal optional)
      11. "DOB: August 12, 1998"          — month-day-year
      12. "DOB (15/08/1999):"             — parenthesized date
      13. "Born in 1998" / "Born: 1998"   — "born" variant
      14. "Age (Year of Birth): 28 (1998)"— year in parens after age

    DERIVED FROM 2-DIGIT YEAR (YY ≥ 30 → 19YY, else 20YY)
      15. "DOB :- 17/2/83"                — 2-digit year date
      16. "D.O.B :- 17/2/97"              — common typo "D.O.B" reversed

    STANDALONE DATES (only if a birth/age keyword sits within 80 chars)
      17. "12th August 1998"              — day-month-year
      18. "August 12, 1998"               — month-day-year
      19. "12/05/1998" / "12-05-1998"     — numeric date
      20. "1998-05-12"                    — ISO format

    Also strips Telegram markdown chars (*/_) before matching, and tolerates
    compound separators like ":-" common in user-edited templates.
    Restricts search to text BEFORE "looking for" so the partner's preferred
    age range isn't mistaken for the poster's age.
    """
    if not text:
        return None

    # Strip Telegram markdown that breaks separator regex (e.g. "Age:- *35 yrs*" → "Age:- 35 yrs")
    text = re.sub(r"[\*_]+", "", text)

    current_year = datetime.now().year

    # Cutoff at the STRUCTURED "Looking for:" field marker — not at every
    # narrative use of "looking for" (e.g. "...is looking for 2nd marriage").
    cutoff = re.search(r"\blooking\s+for\s*[:\-—]", text, re.IGNORECASE)
    haystack = text[: cutoff.start()] if cutoff else text

    # Separator between label and value: one-or-more of : - — (compound like ":-" allowed)
    SEP = r"[:\-—]+"

    # ---- DIRECT AGE PATTERNS (the number is the age) ----
    direct_patterns = [
        # 1: "Age (Year of birth): 28"
        rf"\bage\s*\([^)\n]{{0,50}}\)\s*{SEP}\s*(\d{{1,2}})\b",
        # 2: "Age: 28" / "Age - 28" / "Age :- 28" / "Age:-28"
        rf"\bage\s*{SEP}\s*(\d{{1,2}})\s*(?:years?|yrs?)?\b",
        # 3: "Age 28"
        r"\bage\s+(\d{1,2})\b(?!\s*[/\-.]\d)",
        # 3b: "Age. 29" (period separator — common in some templates)
        r"\bage\s*\.\s*(\d{1,2})\b(?!\s*(?:years?|yrs?)\s+(?:of|experience|exp)\b)",
        # 4-6: "28 years old", "28 yrs old", "28 y/o", "28 y.o.", "28yo"
        r"\b(\d{1,2})\s*(?:years?\s*old|yrs?\.?\s*old|y\.?\s*o\.?\b|y\s*/\s*o\b)",
        # 7: "28-year-old"
        r"\b(\d{1,2})\s*-\s*year\s*-\s*old\b",
    ]
    candidates = []
    for p in direct_patterns:
        for m in re.finditer(p, haystack, re.IGNORECASE):
            age = int(m.group(1))
            if 18 <= age <= 70:
                candidates.append((m.start(), age))
    if candidates:
        return sorted(candidates)[0][1]

    # ---- YEAR-OF-BIRTH PATTERNS (compute age from year) ----
    months_rx = r"jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec"
    year_rx   = r"(19[3-9]\d|20[01]\d)"
    # birth_kw also covers the common typo "D.B.O" (transposed D.O.B)
    birth_kw  = r"(?:d\.?o\.?b\.?|d\.?b\.?o\.?|date\s*of\s*birth|year\s*of\s*birth|y\.?o\.?b\.?|birth\s*year|born)"

    yob_patterns = [
        # 8: "DOB: 1998", "Year of birth - 1998"
        rf"\b{birth_kw}\s*{SEP}?\s*{year_rx}\b",
        # 9: "DOB: 12/05/1998"
        rf"\b{birth_kw}\s*{SEP}?\s*\d{{1,2}}[/\-.]\d{{1,2}}[/\-.]{year_rx}",
        # 10: "DOB: 12th Aug 1998" (no-space variants like "12april1998" also accepted)
        rf"\b{birth_kw}\s*{SEP}?\s*\d{{1,2}}(?:st|nd|rd|th)?\s*(?:{months_rx})[a-z]*\s*{year_rx}",
        # 11: "DOB: August 12, 1998"
        rf"\b{birth_kw}\s*{SEP}?\s*(?:{months_rx})[a-z]*\s*\d{{1,2}}(?:st|nd|rd|th)?,?\s*{year_rx}",
        # 12: "DOB (15/08/1999):" / "Date of Birth (1999):"
        rf"\b{birth_kw}[^\n]{{0,30}}?\((?:\d{{1,2}}[/\-.]\d{{1,2}}[/\-.])?{year_rx}\b",
        # 13: "Born in 1998", "Born on 1998"
        rf"\bborn\s*(?:in|on)?\s*{SEP}?\s*{year_rx}\b",
        # 14: "Age (Year of Birth): 28 (1998)" — year in trailing parens
        rf"\bage[^\n]{{0,60}}?\(\s*{year_rx}\s*\)",
        # 15 (catch-all): "DOB ... 1998" with anything in between (up to 80 chars)
        rf"\b{birth_kw}[^\n]{{0,80}}?\b{year_rx}\b",
    ]
    for p in yob_patterns:
        for m in re.finditer(p, haystack, re.IGNORECASE):
            year = int(m.group(1))
            age = current_year - year
            if 18 <= age <= 70:
                return age

    # ---- 2-DIGIT YEAR DOB (e.g. "DOB :- 17/2/83") ----
    yy_pattern = rf"\b{birth_kw}\s*{SEP}?\s*\d{{1,2}}[/\-.]\d{{1,2}}[/\-.](\d{{2}})\b(?!\d)"
    for m in re.finditer(yy_pattern, haystack, re.IGNORECASE):
        yy = int(m.group(1))
        # YY ≥ 30 → 19YY (1930-1999), else → 20YY (2000-2029).
        year = 1900 + yy if yy >= 30 else 2000 + yy
        age = current_year - year
        if 18 <= age <= 70:
            return age

    # ---- STANDALONE DATE PATTERNS (need a birth/age keyword within 80 chars) ----
    standalone_patterns = [
        # 17: "12th August 1998" / "12April1998"
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s*(?:{months_rx})[a-z]*\s*{year_rx}\b",
        # 18: "August 12, 1998"
        rf"\b(?:{months_rx})[a-z]*\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+{year_rx}\b",
        # 19: "12/05/1998" / "12-05-1998" / "12.05.1998"
        rf"\b\d{{1,2}}[/\-.]\d{{1,2}}[/\-.]{year_rx}\b",
        # 20: "1998-05-12" (ISO)
        rf"\b{year_rx}[/\-.]\d{{1,2}}[/\-.]\d{{1,2}}\b",
    ]
    nearby_kw = re.compile(r"\b(birth|born|dob|d\.?b\.?o|yob|age)\b", re.IGNORECASE)
    for p in standalone_patterns:
        for m in re.finditer(p, haystack, re.IGNORECASE):
            year = int(m.group(1))
            ctx_start = max(0, m.start() - 80)
            ctx_end = min(len(haystack), m.end() + 80)
            if nearby_kw.search(haystack[ctx_start:ctx_end]):
                age = current_year - year
                if 18 <= age <= 70:
                    return age

    return None


def extract_gender(text: str) -> Optional[str]:
    """Return 'male' / 'female' for the person being described in the post.

    Priority:
      1. Profile-code prefix — these channels use 'M####' for grooms, 'F####' for brides
      2. Explicit "Gender: ..." field
      3. Brother / sister keywords in first 500 chars
      4. Pronoun count fallback
    """
    # 1. Profile-code prefix is the most reliable signal on these channels.
    code_match = re.search(
        r"profile\s*code\b[\s:#\-]{0,5}([MFmf])\d", text, re.IGNORECASE
    )
    if code_match:
        return "male" if code_match.group(1).upper() == "M" else "female"

    # 2. Explicit "Gender: ..." field. Handles many variants:
    #   "Gender: Male" / "Gender: Female"
    #   "Gender: M" / "Gender: F"  (single-letter answers)
    #   "Gender: M/F : Female"     (template form where the user fills in after second colon)
    field_match = re.search(r"\bgender\b[^\n]*", text, re.IGNORECASE)
    if field_match:
        line = field_match.group(0)
        # If the line has a colon (the "Gender:" separator and possibly a second one
        # from "M/F : Female"-style templates), prefer what comes after the LAST colon.
        last_colon = line.rfind(":")
        after = line[last_colon + 1:] if last_colon != -1 and last_colon < len(line) - 1 else line
        words = re.findall(r"\b([Mm]ale|[Ff]emale|[Mm]|[Ff])\b", after)
        if not words and after != line:
            words = re.findall(r"\b([Mm]ale|[Ff]emale|[Mm]|[Ff])\b", line)
        if words:
            first = words[0].lower()
            if first in ("m", "male"):
                return "male"
            if first in ("f", "female"):
                return "female"

    # Heuristic fallback: brother/sister keywords in the first 500 chars
    t = text.lower()
    first_500 = t[:500]
    if re.search(r"\b(brother|bhai|male|groom)\b", first_500):
        if re.search(r"looking\s+for\s+(a\s+)?(brother|bhai|male|groom|husband)", first_500):
            return "female"
        return "male"
    if re.search(r"\b(sister|behan|behen|female|bride)\b", first_500):
        if re.search(r"looking\s+for\s+(a\s+)?(sister|behan|behen|female|bride|wife)", first_500):
            return "male"
        return "female"

    # Pronoun fallback
    he_count = len(re.findall(r"\b(he|him|his)\b", t))
    she_count = len(re.findall(r"\b(she|her|hers)\b", t))
    if he_count >= 3 and he_count > she_count * 2:
        return "male"
    if she_count >= 3 and she_count > he_count * 2:
        return "female"
    return None


def extract_marital_status(text: str) -> Optional[str]:
    t = text.lower()
    if re.search(r"\bnever\s+married\b|\bunmarried\b|\bsingle\b|\bbachelor\b|\bspinster\b", t):
        return "Never married"
    if re.search(r"\bdivorc(e|ed|ee)\b|\bkhula\b|\btalaq\b|\btalaaq\b", t):
        return "Divorced"
    if re.search(r"\bwidow(er|ed)?\b", t):
        return "Widowed"
    if re.search(r"\bseparat(ed|ion)\b", t):
        return "Separated"
    return None


def extract_children(text: str) -> Optional[str]:
    t = text.lower()
    m = re.search(r"(\d+)\s*(?:kid|kids|child|children|son|sons|daughter|daughters)", t)
    if m:
        return f"{m.group(1)} children"
    if re.search(r"\bno\s+(kids|children)\b|\bchildless\b", t):
        return "No children"
    return None


def extract_city(text: str) -> Optional[str]:
    m = _CITY_RX.search(text)
    return m.group(1).title() if m else None


def extract_state(text: str) -> Optional[str]:
    m = _STATE_RX.search(text)
    return m.group(1).title() if m else None


def extract_country(text: str) -> Optional[str]:
    t = text.lower()
    # Heuristic: if any Indian city/state matches, default country is India
    countries = {
        "india": "India", "pakistan": "Pakistan", "bangladesh": "Bangladesh",
        "uk": "UK", "united kingdom": "UK", "usa": "USA", "us ": "USA",
        "united states": "USA", "canada": "Canada", "australia": "Australia",
        "uae": "UAE", "saudi": "Saudi Arabia", "ksa": "Saudi Arabia",
        "qatar": "Qatar", "kuwait": "Kuwait", "oman": "Oman", "bahrain": "Bahrain",
        "malaysia": "Malaysia", "singapore": "Singapore", "south africa": "South Africa",
    }
    for key, name in countries.items():
        if re.search(rf"\b{re.escape(key)}\b", t):
            return name
    if extract_city(text) or extract_state(text):
        return "India"
    return None


def extract_education(text: str) -> Optional[str]:
    """Pulls a one-line education descriptor."""
    patterns = [
        r"education[:\-]\s*([^\n]+)",
        r"qualification[:\-]\s*([^\n]+)",
        r"\b(b\.?tech|m\.?tech|mbbs|md|phd|b\.?e\b|m\.?e\b|b\.?sc|m\.?sc|bca|mca|bba|mba|ca|llb|llm|b\.?com|m\.?com|ba|ma|diploma|graduate|post[\s-]?graduate|alim|alima|hafiz|hafiza|hifz)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(".,;")[:80]
    return None


def extract_profession(text: str) -> Optional[str]:
    patterns = [
        r"profession[:\-]\s*([^\n]+)",
        r"occupation[:\-]\s*([^\n]+)",
        r"work(?:ing)?\s+as[:\-]?\s*([^\n]+)",
        r"job[:\-]\s*([^\n]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(".,;")[:80]
    # Common job keywords as last resort
    keywords = ["doctor", "engineer", "teacher", "businessman", "business", "lawyer",
                "accountant", "developer", "designer", "imam", "scholar", "homemaker",
                "housewife", "student", "nurse", "pharmacist", "professor", "artist",
                "freelancer", "self-employed", "entrepreneur"]
    for kw in keywords:
        if re.search(rf"\b{kw}\b", text, re.IGNORECASE):
            return kw.title()
    return None


def extract_height(text: str) -> Optional[str]:
    # 5'7", 5'7, 5 ft 7, 5ft 7in, 170 cm
    # Require an apostrophe or "ft" to avoid matching "29 years" as 2'9".
    patterns = [
        r"\b([4-6])\s*['’]\s*(\d{1,2})\s*[\"”]?",
        r"\b([4-6])\s*ft\s*(\d{1,2})\s*(?:in|inches|\")?",
        r"\b([4-6])\s*feet\s*(\d{1,2})\s*(?:in|inches|\")?",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m and 0 <= int(m.group(2)) <= 11:
            return f"{m.group(1)}'{m.group(2)}\""
    m = re.search(r"\b(1[4-9]\d|20\d)\s*cm\b", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} cm"
    return None


def extract_looking_for(text: str) -> Optional[str]:
    m = re.search(
        r"looking\s+for[:\-]?\s*([^\n]+)", text, re.IGNORECASE
    )
    if m:
        return m.group(1).strip().rstrip(".,;")[:200]
    return None


# ---------- Top-level parse ----------

def parse_profile(text: str) -> dict:
    """Run all extractors on a profile post and return a dict of fields."""
    if not text:
        return {}
    return {
        "gender":         extract_gender(text),
        "age":            extract_age(text),
        "marital_status": extract_marital_status(text),
        "children":       extract_children(text),
        "city":           extract_city(text),
        "state":          extract_state(text),
        "country":        extract_country(text),
        "education":      extract_education(text),
        "profession":     extract_profession(text),
        "height":         extract_height(text),
        "looking_for":    extract_looking_for(text),
    }


def is_profile_post(text: str) -> bool:
    """Heuristic: does this message look like a profile rather than admin chatter?"""
    if not text or len(text) < 80:
        return False
    t = text.lower()
    has_age = bool(extract_age(text))
    has_role = bool(re.search(r"\b(brother|sister|bhai|behan|behen|male|female|groom|bride)\b", t))
    has_marital = "married" in t or "divorc" in t or "widow" in t or "single" in t
    # Strong signal: an explicit profile-code header. Channel admins use this
    # consistently for genuine profiles, so accept on any other profile cue.
    has_code = bool(re.search(r"profile\s*code\b[^a-z\n]{0,5}[a-z]?\d", t))
    if has_code and (has_age or has_role or has_marital):
        return True
    return has_age and (has_role or has_marital)
