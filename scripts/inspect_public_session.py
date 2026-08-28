"""Print one labeled public session for retrieval debugging.

This script is deliberately separate from the Agent. It reads public labels for
development diagnostics; submission-time inference never reads ground truth.
"""

from __future__ import annotations

import argparse

from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
)
from starter.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample_id")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    sample = next(item for item in samples if item["sample_id"] == args.sample_id)
    catalog_ids, categories, products = catalog_index(args.catalog)
    target = str(sample["ground_truth"]["parent_asin"])
    intent_card, behavior = materialize_hidden_fields(sample, products)
    effective_sample = {**sample, "intent_card": intent_card, "behavior": behavior}

    agent = Agent(args.catalog)
    session_id = "diagnostic"
    agent.reset(session_id, sample["user_profile"])
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    message = initial_message(effective_sample, coarse_category(categories[target]), disclosed)

    print(f"Target: {target} — {products[target]['title']}")
    print(f"Intent card: {intent_card}\n")
    for turn in range(1, MAX_TURNS + 1):
        response = agent.respond(session_id, message, turn, TOP_K)
        ranked = [item["parent_asin"] for item in response["recommendations"]]
        print(f"Turn {turn}\nCustomer: {message}\nAgent: {response['message']}")
        print("Recommendations:")
        for rank, parent_asin in enumerate(ranked, 1):
            marker = " <-- target" if parent_asin == target else ""
            print(f"  {rank:>2}. {parent_asin} {products[parent_asin]['title'][:100]}{marker}")
        print()
        if override_applied and target in ranked:
            break
        override = effective_sample.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            message = str(override["message"])
        else:
            message, boundary_used = customer_reply(
                effective_sample, response.get("ask_attribute"), disclosed, boundary_used
            )


if __name__ == "__main__":
    main()
