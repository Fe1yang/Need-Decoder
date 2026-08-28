import json
import tempfile
import unittest
from pathlib import Path

from starter.agent import Agent


class AgentContractTests(unittest.TestCase):
    def test_response_matches_official_shape(self):
        products = [
            {
                "parent_asin": "B000TEST01",
                "title": "Black leather walking shoe",
                "categories": ["Shoes", "Walking"],
                "features": ["Leather", "Comfort sole"],
                "details": {"Color": "Black"},
                "description": [],
                "store": "Example",
                "average_rating": 4.5,
                "rating_number": 25,
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text("\n".join(json.dumps(item) for item in products) + "\n", encoding="utf-8")
            agent = Agent(catalog_path)
            agent.reset("contract", {"preference_tags": []})
            response = agent.respond("contract", "I'm looking for Shoes Walking.", 1, 10)

        self.assertEqual(
            set(response),
            {"message", "ask_attribute", "recommendations", "usage"},
        )
        self.assertIsInstance(response["message"], str)
        self.assertLessEqual(len(response["recommendations"]), 10)
        self.assertEqual(response["usage"], {"prompt_tokens": 0, "completion_tokens": 0})


if __name__ == "__main__":
    unittest.main()
