import json
import tempfile
import unittest
from pathlib import Path

from need_decoder.retrieval import CatalogSearch
from need_decoder.state import ConversationState


class CatalogSearchTests(unittest.TestCase):
    def test_skips_a_damaged_catalog_row(self):
        product = {
            "parent_asin": "VALID",
            "title": "Breathable walking shoes",
            "categories": ["Shoes"],
            "features": ["Mesh upper"],
            "price": 60.0,
            "average_rating": 4.6,
            "rating_number": 120,
        }
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                json.dumps(product) + "\n" + '{"parent_asin":"BROKEN"\n',
                encoding="utf-8",
            )

            search = CatalogSearch(catalog_path)

        self.assertEqual(search.document_count, 1)

    def test_budget_and_exclusion_affect_ranking(self):
        products = [
            {
                "parent_asin": "LEATHER",
                "title": "Black leather walking shoes",
                "categories": ["Shoes"],
                "features": ["Cushioned leather upper"],
                "price": 85.0,
                "average_rating": 4.9,
                "rating_number": 5000,
            },
            {
                "parent_asin": "CANVAS",
                "title": "Black canvas walking shoes",
                "categories": ["Shoes"],
                "features": ["Cushioned textile upper"],
                "price": 45.0,
                "average_rating": 4.2,
                "rating_number": 50,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                "\n".join(json.dumps(product) for product in products) + "\n",
                encoding="utf-8",
            )
            search = CatalogSearch(catalog_path)
            state = ConversationState(profile={})
            state.ingest("I'm looking for Shoes. I want black, no leather, under $60.")
            recommendations = search.search(state)

        self.assertEqual(recommendations[0]["parent_asin"], "CANVAS")


if __name__ == "__main__":
    unittest.main()
