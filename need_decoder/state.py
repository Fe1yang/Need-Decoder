from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from need_decoder.text import (
    OVERRIDE_PATTERN,
    PricePreference,
    extract_category,
    extract_constraint,
    extract_excluded_terms,
    parse_price_preference,
)


@dataclass(frozen=True)
class NeedHypothesis:
    attribute: str
    value: str
    confidence: float
    evidence: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConversationState:
    profile: dict
    category: str | None = None
    constraints: list[str] = field(default_factory=list)
    hypotheses: list[NeedHypothesis] = field(default_factory=list)
    excluded_terms: set[str] = field(default_factory=set)
    price_preference: PricePreference | None = None
    asked_attributes: set[str] = field(default_factory=set)
    observed_attributes: set[str] = field(default_factory=set)
    intent: str = "browsing"
    override_count: int = 0

    def ingest(self, message: str) -> bool:
        new_category = extract_category(message)
        if new_category:
            self.category = new_category
            self.observed_attributes.add("category")

        constraint = extract_constraint(message, self.category)
        excluded_terms = extract_excluded_terms(message)
        price_preference = parse_price_preference(message)
        was_overridden = bool(OVERRIDE_PATTERN.search(message))
        if was_overridden:
            # The opening preference is the value being replaced. Constraints
            # collected through later, direct clarification remain useful;
            # dropping the entire state would force the customer to repeat it.
            self.constraints = self.constraints[1:]
            self.hypotheses.clear()
            self.excluded_terms.clear()
            self.price_preference = None
            self.asked_attributes.clear()
            self.observed_attributes = {"category"} if self.category else set()
            for preserved_constraint in self.constraints:
                self.observed_attributes.update(detect_attributes(preserved_constraint))
                self.excluded_terms.update(extract_excluded_terms(preserved_constraint))
                preserved_price = parse_price_preference(preserved_constraint)
                if preserved_price:
                    self.price_preference = preserved_price
            self.override_count += 1

        if constraint and constraint not in self.constraints:
            self.constraints.append(constraint)
            self.observed_attributes.update(detect_attributes(constraint))
        self.excluded_terms.update(excluded_terms)
        if price_preference:
            self.price_preference = price_preference

        self.intent = classify_intent(message, self.constraints)
        self._infer_needs(message)
        return was_overridden

    def mark_asked(self, attribute: str) -> None:
        self.asked_attributes.add(attribute)

    def _infer_needs(self, message: str) -> None:
        lowered = message.lower()
        inference_rules = (
            (("work", "office", "company", "interview"), "style", "business casual professional", 0.72, "professional setting"),
            (("travel", "retreat", "walking", "standing"), "feature", "comfortable cushioned durable", 0.74, "extended wear"),
            (("outdoor", "hiking", "rain"), "feature", "water resistant non slip", 0.78, "outdoor activity"),
            (("wedding", "party", "dinner"), "style", "dress polished versatile", 0.68, "social occasion"),
            (("winter", "cold"), "feature", "warm insulated", 0.82, "cold weather"),
            (("summer", "hot", "humid"), "feature", "lightweight breathable moisture wicking", 0.82, "warm weather"),
            (("gift",), "feature", "gift ready versatile", 0.62, "recipient uncertainty"),
            (("sensitive skin", "allergy", "allergic"), "material", "soft hypoallergenic nickel free", 0.86, "skin sensitivity"),
            (("child", "kid", "school"), "feature", "durable easy clean secure", 0.70, "frequent active use"),
        )
        existing = {(item.attribute, item.value) for item in self.hypotheses}
        for triggers, attribute, value, confidence, evidence in inference_rules:
            if any(trigger in lowered for trigger in triggers) and (attribute, value) not in existing:
                self.hypotheses.append(NeedHypothesis(attribute, value, confidence, evidence))

    def debug_snapshot(self) -> dict:
        return {
            "intent": self.intent,
            "category": self.category,
            "explicit_constraints": list(self.constraints),
            "excluded_terms": sorted(self.excluded_terms),
            "price_preference": self.price_preference.as_dict() if self.price_preference else None,
            "hidden_need_hypotheses": [item.as_dict() for item in self.hypotheses],
            "profile_signals": list(self.profile.get("preference_tags", [])),
            "override_count": self.override_count,
        }


ATTRIBUTE_PATTERNS = {
    "budget": re.compile(r"(?:\$\s*\d+|\b(?:under|below|budget|price)\b)", re.I),
    "material": re.compile(r"\b(cotton|polyester|nylon|leather|wool|silk|rayon|spandex|fabric|material)\b", re.I),
    "color": re.compile(r"\b(black|white|blue|red|pink|green|brown|gr[ae]y|purple|yellow|orange|color)\b", re.I),
    "size": re.compile(r"\b(size|sizing|width|wide|narrow|petite|plus size)\b", re.I),
    "style": re.compile(r"\b(department|style|formal|casual|business|vintage|classic|modern|fit|sleeve|neck)\b", re.I),
    "brand": re.compile(r"\b(brand|made by|manufacturer)\b", re.I),
    "use_case": re.compile(r"\b(hiking|running|gym|winter|outdoor|work)\b", re.I),
}


def detect_attributes(text: str) -> set[str]:
    detected = {name for name, pattern in ATTRIBUTE_PATTERNS.items() if pattern.search(text)}
    if not detected:
        detected.add("feature")
    return detected


def classify_intent(message: str, constraints: list[str]) -> str:
    if re.search(r"\b(still exploring|ideas|not sure|browse|browsing)\b", message, re.I) and not constraints:
        return "browsing"
    return "buying" if constraints else "browsing"
