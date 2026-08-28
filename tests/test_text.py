import unittest

from need_decoder.text import extract_category, extract_constraint, search_terms


class TextTests(unittest.TestCase):
    def test_extracts_opening_category(self):
        message = "I'm looking for Men Accessories Belts, but I'm still exploring."
        self.assertEqual(extract_category(message), "Men Accessories Belts")

    def test_extracts_structured_constraint(self):
        message = "For that, what matters is: 100% Leather; Buckle closure."
        self.assertEqual(extract_constraint(message, None), "100% Leather; Buckle closure")

    def test_search_terms_are_unique_and_drop_wrapper_words(self):
        self.assertEqual(search_terms("I need a leather leather belt"), ["leather", "belt"])


if __name__ == "__main__":
    unittest.main()
