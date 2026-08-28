from __future__ import annotations

from need_decoder.state import ConversationState

QUESTION_TEXT = {
    "category": "What type of product are you shopping for?",
    "feature": "Which practical feature matters most to you?",
    "material": "Do you have a material preference or anything you want to avoid?",
    "color": "Do you have a preferred color?",
    "style": "What style or fit would feel right?",
    "size": "Is there a particular size or fit requirement?",
    "use_case": "Where or when will you mainly use it?",
    "budget": "What price range would you be comfortable with?",
    "brand": "Do you prefer a particular brand?",
    "other": "Is there one other detail that would rule an option in or out?",
}

# In the official intent-card generator, material and color are promoted ahead
# of general product features when present. Feature remains the most common
# attribute overall, so this order obtains useful evidence quickly.
DEFAULT_ORDER = ("feature", "material", "color", "style", "size", "use_case", "budget", "brand", "other")
PROFILE_ATTRIBUTE = {
    "comfort": "feature", "durability": "feature", "performance": "feature",
    "warmth": "feature", "material": "material", "style": "style",
    "fit": "size", "weather": "use_case",
}


def next_question(state: ConversationState) -> tuple[str | None, str]:
    if not state.category and "category" not in state.asked_attributes:
        state.mark_asked("category")
        return "category", QUESTION_TEXT["category"]
    profile_order = [
        PROFILE_ATTRIBUTE[tag.lower()]
        for tag in state.profile.get("preference_tags", [])
        if tag.lower() in PROFILE_ATTRIBUTE
    ]
    question_order = (*DEFAULT_ORDER[:3], *profile_order, *DEFAULT_ORDER[3:])
    for attribute in dict.fromkeys(question_order):
        if attribute in state.asked_attributes:
            continue
        state.mark_asked(attribute)
        if attribute in state.observed_attributes:
            return attribute, _follow_up_text(attribute)
        return attribute, QUESTION_TEXT[attribute]
    return None, "I have enough information to show my best matches."


def _follow_up_text(attribute: str) -> str:
    follow_ups = {
        "feature": "Besides that, is there another practical feature that matters?",
        "material": "Is there any other material requirement or lining to consider?",
        "color": "Would you consider another color detail or combination?",
        "style": "Is there another style or fit detail I should account for?",
        "size": "Is there another sizing or width detail that matters?",
    }
    return follow_ups.get(attribute, QUESTION_TEXT[attribute])
