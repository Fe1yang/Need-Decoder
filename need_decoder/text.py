from __future__ import annotations

import re
from dataclasses import asdict, dataclass

TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

# These words occur in the simulator's conversational wrappers and carry no
# product meaning. Keeping this list explicit makes retrieval deterministic.
SEARCH_STOPWORDS = {
    "a", "about", "additional", "an", "and", "are", "ask", "avoid", "but", "by",
    "do", "exclude", "excluding", "except", "for", "from", "have", "here", "i", "in", "is", "it", "key",
    "looking", "me", "my", "need", "not", "of", "on", "or", "please",
    "no", "preference", "requirement", "some", "still", "that", "the", "these",
    "this", "those", "to", "want", "what", "with", "without", "would", "yet", "you",
}

NEGATIVE_REPLY_PATTERN = re.compile(
    r"\b(?:do not|don't|no)\s+(?:have|want|need|an? additional|a preference)\b|"
    r"\bnot quite right\b|\buse your judgment\b",
    re.IGNORECASE,
)
OVERRIDE_PATTERN = re.compile(
    r"\b(?:actually|instead|ignore (?:that|my earlier preference)|changed my mind|"
    r"not that|scratch that|forget (?:that|my earlier preference)|rather than)\b",
    re.IGNORECASE,
)

CATEGORY_PATTERNS = (
    re.compile(r"\b(?:looking|shopping|searching)\s+for\s+(.+?)(?:,|\.|;|$)", re.IGNORECASE),
    re.compile(
        r"\b(?:(?:need|want)(?!\s+is\b)|buy|find|show me)\s+"
        r"(?:a|an|some|new|the)?\s*"
        r"(.+?)(?=\s+(?:for|that|which|with|under|below|around)\b|,|\.|;|$)",
        re.IGNORECASE,
    ),
)
GENERIC_CATEGORIES = {"anything", "idea", "ideas", "item", "options", "product", "something", "them"}
PRICE_CONTEXT_PATTERN = re.compile(
    r"(?:\$\s*\d|\b(?:budget|price|cost|spend|under|below|less than|up to|"
    r"over|above|more than|at least|between|around)\b)",
    re.IGNORECASE,
)
PRICE_NUMBER_PATTERN = re.compile(r"\$?\s*(\d+(?:\.\d{1,2})?)")
EXCLUSION_PATTERN = re.compile(
    r"\b(?:avoid|without|except|excluding|exclude|not)\s+(?:any\s+)?"
    r"(.+?)(?=,|\.|;|\bbut\b|\band\s+(?:need|want|prefer|would|am|i'm)\b|$)",
    re.IGNORECASE,
)
NO_EXCLUSION_PATTERN = re.compile(
    r"\bno\s+(?:any\s+)?(.+?)(?=,|\.|;|\bbut\b|\band\s+(?:need|want|prefer|would|am|i'm)\b|$)",
    re.IGNORECASE,
)
STRUCTURED_CONSTRAINT_PATTERN = re.compile(
    r"\b(?:what matters is|what i need is|key requirement is)\s*:?\s*(.+)",
    re.IGNORECASE,
)
NEGATABLE_TERMS = {
    "beige", "black", "blue", "brown", "cotton", "faux", "gray", "green",
    "grey", "heel", "heels", "latex", "leather", "logo", "logos", "metal",
    "nickel", "nylon", "orange", "pattern", "patterns", "pink", "polyester",
    "purple", "rayon", "red", "silk", "spandex", "suede", "white", "wool",
    "yellow", "zipper", "zippers",
}


@dataclass(frozen=True)
class PricePreference:
    target: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def search_terms(text: str) -> list[str]:
    """Return stable, de-duplicated terms suitable for the catalog index."""
    terms: list[str] = []
    seen: set[str] = set()
    for token in TOKEN_PATTERN.findall(text.lower()):
        if len(token) < 2 or token in SEARCH_STOPWORDS or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms


def normalized_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def extract_category(message: str) -> str | None:
    """Extract a concise product category from a shopping request."""
    for pattern in CATEGORY_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        category = match.group(1).strip(" -")
        if category and category.lower() not in GENERIC_CATEGORIES:
            return category
    return None


def extract_constraint(message: str, category: str | None) -> str | None:
    """Remove conversational wrappers while preserving the user's evidence."""
    if NEGATIVE_REPLY_PATTERN.search(message):
        return None
    structured = STRUCTURED_CONSTRAINT_PATTERN.search(message)
    if structured:
        value = structured.group(1).strip(" .")
        return value or None
    cleaned = message
    if category:
        category_request_patterns = (
            r"\b(?:(?:i'm|i am)\s+)?(?:looking|shopping|searching)\s+for\s+",
            r"\b(?:i\s+)?(?:need|want|buy|find)\s+(?:a|an|some|new|the)?\s*",
            r"\bshow me\s+(?:a|an|some|new|the)?\s*",
        )
        for prefix in category_request_patterns:
            cleaned = re.sub(
                prefix + re.escape(category) + r"\s*[,\.]?",
                "",
                cleaned,
                count=1,
                flags=re.IGNORECASE,
            )
    cleaned = re.sub(r"\b(?:but )?i'm still exploring\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(?:for|that|which|with)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" .,;-")
    return cleaned or None


def extract_excluded_terms(message: str) -> set[str]:
    """Return normalized terms from explicit exclusion clauses."""
    if NEGATIVE_REPLY_PATTERN.search(message):
        return set()
    excluded: set[str] = set()
    for match in EXCLUSION_PATTERN.finditer(message):
        excluded.update(search_terms(match.group(1)))
    for match in NO_EXCLUSION_PATTERN.finditer(message):
        excluded.update(set(search_terms(match.group(1))) & NEGATABLE_TERMS)
    return excluded


def parse_price_preference(message: str) -> PricePreference | None:
    """Parse a shopper's numeric budget without treating percentages as prices."""
    if not PRICE_CONTEXT_PATTERN.search(message):
        return None
    values = [float(value) for value in PRICE_NUMBER_PATTERN.findall(message)]
    if not values:
        return None

    lowered = message.lower()
    if "between" in lowered and len(values) >= 2:
        lower, upper = sorted(values[:2])
        return PricePreference(minimum=lower, maximum=upper)
    if re.search(r"\b(?:under|below|less than|up to|maximum|max)\b", lowered):
        return PricePreference(maximum=values[0])
    if re.search(r"\b(?:over|above|more than|at least|minimum|min)\b", lowered):
        return PricePreference(minimum=values[0])
    return PricePreference(target=values[0])
