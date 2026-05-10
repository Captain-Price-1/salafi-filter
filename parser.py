"""
Best-effort regex parser for salafi marriage profile posts.

These channels use semi-structured templates that vary post to post, so we
extract conservatively: when a field is uncertain, we leave it None and let
the user see the raw text in the UI.
"""

from __future__ import annotations
import re
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
    # "Age: 28", "28 years", "28 y/o", "Age 28", "Age (Year of birth): 28"
    # Restrict to the part of the post BEFORE "looking for" — otherwise we
    # pick up the partner's preferred age range instead of the poster's age.
    cutoff = re.search(r"looking\s+for", text, re.IGNORECASE)
    haystack = text[: cutoff.start()] if cutoff else text

    patterns = [
        r"\b(\d{2})\s*(?:years?\s*old|y/?o|yrs?)\b",       # "29 years old"
        r"\bage\s*[:\-]\s*(\d{2})\b",                      # "Age: 28"
        r"\bage\s+(\d{2})\b",                              # "Age 28"
        r"\bage\s*\([^)\n]{0,40}\)\s*[:\-]\s*(\d{1,2})\b", # "Age (Year of birth): 28"
    ]
    candidates = []
    for p in patterns:
        for m in re.finditer(p, haystack, re.IGNORECASE):
            age = int(m.group(1))
            if 18 <= age <= 70:
                candidates.append((m.start(), age))
    if candidates:
        # Earliest occurrence wins (profile's own age is typically near the top).
        return sorted(candidates)[0][1]

    # Fallback: derive from a year of birth (only if no explicit age found).
    # Patterns the channel uses:
    #   "Age (Year of birth): 28 (1998)"
    #   "Date of Birth: February 6, 2001"
    #   "Date of Birth (15/08/1999):"
    #   "DOB: 12/04/1995"
    from datetime import datetime
    current_year = datetime.now().year
    dob_patterns = [
        r"(?:date\s+of\s+birth|year\s+of\s+birth|\bdob\b|\bborn\b)[^\n]{0,80}?\b(19[5-9]\d|20[01]\d)\b",
    ]
    for p in dob_patterns:
        m = re.search(p, haystack, re.IGNORECASE)
        if m:
            age = current_year - int(m.group(1))
            if 18 <= age <= 70:
                return age
    return None


def extract_gender(text: str) -> Optional[str]:
    """Return 'male' / 'female' for the person being described in the post."""
    # Strongest signal: an explicit "Gender: ..." field. Handles many variants:
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
