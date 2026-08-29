"""End-to-end terminal demo for the project walkthrough."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from starter.agent import Agent

CATALOG_PATH = Path("data/catalog.jsonl")
SCENARIOS = {
    "hidden-needs": {
        "title": "Hidden needs from a real-world situation",
        "session_id": "company-retreat-demo",
        "messages": (
            "I'm looking for Men's Walking Shoes. I need them for a company retreat with lots of walking.",
            "Some activities are outdoors, but we also have a business-casual dinner.",
        ),
    },
    "intent-override": {
        "title": "Recovering when the shopper changes direction",
        "session_id": "intent-override-demo",
        "messages": (
            "I'm looking for Women's Walking Shoes. I would prefer leather.",
            "Actually, ignore my earlier preference. What I need is breathable mesh for hot weather.",
        ),
    },
}


def load_product_titles() -> dict[str, str]:
    titles: dict[str, str] = {}
    with CATALOG_PATH.open(encoding="utf-8") as catalog:
        for line in catalog:
            product = json.loads(line)
            titles[str(product["parent_asin"])] = str(product.get("title") or "Untitled product")
    return titles


def run_scenario(agent: Agent, product_titles: dict[str, str], scenario_name: str) -> None:
    scenario = SCENARIOS[scenario_name]
    print(f"\n=== {scenario['title']} ===\n")
    session_id = str(scenario["session_id"])
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

    for turn, customer_message in enumerate(scenario["messages"], start=1):
        response = agent.respond(session_id, str(customer_message), turn, top_k=3)
        state = agent.inspect_session(session_id)

        print(f"TURN {turn}")
        print(f"Customer: {customer_message}")
        print(f"Need Decoder: {response['message']}")
        print(f"Route: {state['intent'].title()}")
        print(f"Explicit constraints: {state['explicit_constraints'] or ['none yet']}")
        if state["override_count"]:
            print(f"Intent overrides handled: {state['override_count']}")
        print("Inferred needs:")
        if not state["hidden_need_hypotheses"]:
            print("  - none")
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Need Decoder walkthrough")
    parser.add_argument(
        "--scenario",
        choices=("all", *SCENARIOS),
        default="all",
        help="walkthrough to run (default: all)",
    )
    args = parser.parse_args()
    product_titles = load_product_titles()
    agent = Agent(CATALOG_PATH)
    selected = SCENARIOS if args.scenario == "all" else (args.scenario,)
    for scenario_name in selected:
        run_scenario(agent, product_titles, scenario_name)


if __name__ == "__main__":
    main()
