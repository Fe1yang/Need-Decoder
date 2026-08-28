"""Small end-to-end demo used for the project walkthrough."""

from __future__ import annotations

import json
from pathlib import Path

from starter.agent import Agent

CATALOG_PATH = Path("data/catalog.jsonl")


def load_product_titles() -> dict[str, str]:
    titles: dict[str, str] = {}
    with CATALOG_PATH.open(encoding="utf-8") as catalog:
        for line in catalog:
            product = json.loads(line)
            titles[str(product["parent_asin"])] = str(product.get("title") or "Untitled product")
    return titles


def main() -> None:
    product_titles = load_product_titles()
    agent = Agent(CATALOG_PATH)
    session_id = "company-retreat-demo"
    agent.reset(
        session_id,
        {
            "purchase_frequency": "3-4 prior purchases",
            "average_prior_rating": 4.5,
            "rating_style": "usually positive",
            "preference_tags": ["comfort", "durability", "style"],
            "summary": "Prior purchases emphasize comfort, durability, and style.",
        },
    )

    customer_messages = (
        "I'm looking for Shoes. I need them for a company retreat with lots of walking.",
        "Some activities are outdoors, but we also have a business-casual dinner.",
    )
    for turn, customer_message in enumerate(customer_messages, start=1):
        response = agent.respond(session_id, customer_message, turn, top_k=5)
        state = agent.inspect_session(session_id)

        print(f"TURN {turn}")
        print(f"Customer: {customer_message}")
        print(f"Need Decoder: {response['message']}")
        print(f"Intent: {state['intent']}")
        print("Inferred needs:")
        for need in state["hidden_need_hypotheses"]:
            print(
                f"  - {need['value']} "
                f"(confidence {need['confidence']:.0%}; evidence: {need['evidence']})"
            )
        print("Recommendations:")
        for rank, recommendation in enumerate(response["recommendations"], start=1):
            parent_asin = recommendation["parent_asin"]
            print(f"  {rank}. {product_titles[parent_asin]} [{parent_asin}]")
        print()


if __name__ == "__main__":
    main()
