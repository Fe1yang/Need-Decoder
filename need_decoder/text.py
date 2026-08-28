from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

# These words occur in the simulator's conversational wrappers and carry no
# product meaning. Keeping this list explicit makes retrieval deterministic.
SEARCH_STOPWORDS = {
    "a", "about", "additional", "an", "and", "are", "ask", "but", "by",
    "do", "for", "from", "have", "here", "i", "in", "is", "it", "key",
    "looking", "me", "my", "need", "not", "of", "on", "or", "please",
    "preference", "requirement", "some", "still", "that", "the", "these",
    "this", "those", "to", "want", "what", "with", "would", "yet", "you",
}

NEGATIVE_REPLY_PATTERN = re.compile(
    r"\b(?:do not|don't|no)\s+(?:have|want|need|an? additional|a preference)\b|"
    r"\bnot quite right\b|\buse your judgment\b",
    re.IGNORECASE,
)
OVERRIDE_PATTERN = re.compile(
    r"\b(?:actually|instead|ignore (?:that|my earlier preference)|changed my mind|not that)\b",
    re.IGNORECASE,
)


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
    """Extract the category phrase from the evaluator's opening message."""
    match = re.search(r"\blooking for\s+(.+?)(?:,|\.|$)", message, re.IGNORECASE)
    if not match:
        return None
    category = match.group(1).strip(" -")
    return category if category else None


def extract_constraint(message: str, category: str | None) -> str | None:
    """Remove conversational wrappers while preserving the user's evidence."""
    if NEGATIVE_REPLY_PATTERN.search(message):
        return None
    for marker in ("what matters is:", "what i need is:", "key requirement is:"):
        position = message.lower().find(marker)
        if position >= 0:
            value = message[position + len(marker):].strip(" .")
            return value or None
    cleaned = message
    if category:
        cleaned = re.sub(
            r"\b(?:i'm|i am)\s+looking for\s+" + re.escape(category) + r"\s*[,\.]?",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(r"\b(?:but )?i'm still exploring\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" .,;-")
    return cleaned or None
