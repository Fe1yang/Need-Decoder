import unittest

from need_decoder.text import (
    PricePreference,
    extract_category,
    extract_constraint,
    extract_excluded_terms,
    parse_price_preference,
    search_terms,
)


class TextTests(unittest.TestCase):
    def test_extracts_opening_category(self):
        message = "I'm looking for Men Accessories Belts, but I'm still exploring."
        self.assertEqual(extract_category(message), "Men Accessories Belts")

    def test_extracts_structured_constraint(self):
        message = "For that, what matters is: 100% Leather; Buckle closure."
        self.assertEqual(extract_constraint(message, None), "100% Leather; Buckle closure")

    def test_extracts_structured_constraint_without_colon(self):
        message = "Actually, what I need is breathable mesh."
        self.assertEqual(extract_constraint(message, None), "breathable mesh")

    def test_extracts_category_from_natural_request(self):
        message = "I need running shoes for daily walks."
        category = extract_category(message)

        self.assertEqual(category, "running shoes")
        self.assertEqual(extract_constraint(message, category), "daily walks")

    def test_structured_override_is_not_mistaken_for_a_category(self):
        message = "Actually, what I need is: double row stitching."
        self.assertIsNone(extract_category(message))

    def test_extracts_exclusions(self):
        self.assertEqual(
            extract_excluded_terms("I prefer black, but no leather or suede."),
            {"leather", "suede"},
        )

    def test_care_instructions_are_not_product_exclusions(self):
        self.assertEqual(
            extract_excluded_terms("Machine wash; no bleach; no dry clean; no ironing."),
            set(),
        )

    def test_parses_price_range(self):
        self.assertEqual(
            parse_price_preference("My budget is between $30 and $55."),
            PricePreference(minimum=30.0, maximum=55.0),
        )

    def test_does_not_parse_material_percentage_as_price(self):
        self.assertIsNone(parse_price_preference("95% Polyester, 5% Spandex"))

    def test_search_terms_are_unique_and_drop_wrapper_words(self):
        self.assertEqual(search_terms("I need a leather leather belt"), ["leather", "belt"])


if __name__ == "__main__":
    unittest.main()
