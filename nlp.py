"""
Natural language parsing module (Ukrainian NLP).
Detects user intent: save an item or query an item.
"""
import re

# ─── Keyword dictionaries ─────────────────────────────────────────────────────

# Verbs that mean storing/placing an item
SAVE_VERBS = (
    r"(?:поклав|поклала|залишив|залишила|поставив|поставила|"
    r"сховав|сховала|кинув|кинула|прибрав|прибрала|"
    r"поміщу|помістив|помістила|відклав|відклала|"
    r"поклала|поставив|поставила|засунув|засунула)"
)

# Prepositions indicating place
PLACE_PREPS = (
    r"(?:на|в|у|під|біля|за|перед|коло|всередині|"
    r"між|поряд з|поряд із|зверху|знизу|над|зліва|справа|до|поза)"
)

# Words that can follow «де» in a query — we skip them
QUERY_SKIP = (
    r"(?:мої|мій|моя|моє|я|знайти|є|там|"
    r"лежать|лежить|знаходяться|знаходиться|"
    r"стоїть|стоять|висять|висить)?"
)

# ─── Patterns ─────────────────────────────────────────────────────────────────

# Patterns for SAVE: "я поклав X на Y"
SAVE_PATTERNS = [
    # Main: "[я] <verb> <item> <prep> <place>"
    re.compile(
        rf"(?:я\s+)?{SAVE_VERBS}\s+(.+?)\s+{PLACE_PREPS}\s+(.+?)(?:\.|,|$)",
        re.IGNORECASE | re.UNICODE,
    ),
    # Stative: "<item> лежить/стоїть/знаходиться <prep> <place>"
    re.compile(
        rf"(.+?)\s+(?:лежить|стоїть|знаходиться|висить)\s+{PLACE_PREPS}\s+(.+?)(?:\.|,|\?|$)",
        re.IGNORECASE | re.UNICODE,
    ),
]

# Patterns for QUERY: "де мої ключі?"
QUERY_PATTERNS = [
    # "де [мої/знайти/...] <item>?"
    re.compile(
        rf"де\s+{QUERY_SKIP}\s*(.+?)(?:\?|$)",
        re.IGNORECASE | re.UNICODE,
    ),
    # "де я поклав/залишив <item>?"
    re.compile(
        rf"де\s+(?:я\s+)?{SAVE_VERBS}\s+(.+?)(?:\?|$)",
        re.IGNORECASE | re.UNICODE,
    ),
    # "не можу знайти <item>"
    re.compile(
        r"(?:не\s+(?:можу\s+)?знайти|не\s+можу\s+відшукати|шукаю)\s+(.+?)(?:\?|$)",
        re.IGNORECASE | re.UNICODE,
    ),
    # "куди я поклав <item>?"
    re.compile(
        rf"куди\s+(?:я\s+)?(?:{SAVE_VERBS}\s+)?(.+?)(?:\?|$)",
        re.IGNORECASE | re.UNICODE,
    ),
]

# ─── Helper functions ─────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Normalize text: lower case and collapse extra spaces."""
    return re.sub(r"\s+", " ", text.lower().strip())


def clean_item(raw: str) -> str:
    """
    Clean item name from "service" words.
    Example: 'мої старі ключі' → 'старі ключі'
    """
    # Remove possessive pronouns at the beginning
    raw = re.sub(
        r"^(?:мої|мій|моя|моє|свої|свій|своя|своє)\s+",
        "",
        raw.strip(),
        flags=re.IGNORECASE | re.UNICODE,
    )
    # Remove question marks and dots at the end
    return raw.rstrip("?.,!").strip()


# ─── Main function ────────────────────────────────────────────────────────────

def parse_intent(text: str) -> dict:
    """
    Determine user intent from Ukrainian text.

    Returns one of:
      - {'intent': 'save',  'item': str, 'location': str}
      - {'intent': 'query', 'item': str}
      - {'intent': 'unknown'}
    """
    normalized = normalize(text)

    # ── First, check if this is a query (question) ────────────────────────────
    # Key markers: words «де», «куди», «не можу знайти»
    is_query = any(
        normalized.startswith(kw) or f" {kw}" in normalized
        for kw in ["де ", "куди ", "не можу знайти", "не можу відшукати", "шукаю "]
    )

    if is_query:
        for pattern in QUERY_PATTERNS:
            m = pattern.search(normalized)
            if m:
                item = clean_item(m.group(1))
                if len(item) > 1:  # Ignore too short matches
                    return {"intent": "query", "item": item}

    # ── Then check for save pattern ───────────────────────────────────────────
    for pattern in SAVE_PATTERNS:
        m = pattern.search(normalized)
        if m:
            item = clean_item(m.group(1))
            location = m.group(2).strip().rstrip(".,?!")
            if item and location:
                return {"intent": "save", "item": item, "location": location}

    # ── If it is not a "де" query but contains a save verb — try once more ───
    if not is_query:
        for pattern in QUERY_PATTERNS:
            m = pattern.search(normalized)
            if m:
                item = clean_item(m.group(1))
                if len(item) > 1:
                    return {"intent": "query", "item": item}

    return {"intent": "unknown"}
