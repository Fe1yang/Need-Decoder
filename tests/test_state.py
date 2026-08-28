import unittest

from need_decoder.questions import next_question
from need_decoder.state import ConversationState


class ConversationStateTests(unittest.TestCase):
    def test_keeps_category_when_intent_is_overridden(self):
        state = ConversationState(profile={})
        state.ingest("I'm looking for Men, Accessories, Belts. Full grain leather.")
        next_question(state)
        state.ingest("Actually, ignore my earlier preference. What I need is: double row stitching.")

        self.assertEqual(state.category, "Men")
        self.assertEqual(state.constraints, ["double row stitching"])
        self.assertEqual(state.override_count, 1)
        self.assertEqual(state.asked_attributes, set())

    def test_negative_reply_does_not_pollute_constraints(self):
        state = ConversationState(profile={})
        state.ingest("I'm looking for Watches Wrist Watches, but I'm still exploring.")
        state.ingest("I don't have an additional preference for material.")

        self.assertEqual(state.constraints, [])

    def test_infers_needs_with_evidence(self):
        state = ConversationState(profile={})
        state.ingest("I need shoes for a company retreat with lots of walking.")
        hypotheses = {item.value: item for item in state.hypotheses}

        self.assertIn("business casual professional", hypotheses)
        self.assertIn("comfortable cushioned durable", hypotheses)
        self.assertGreater(hypotheses["comfortable cushioned durable"].confidence, 0.7)

    def test_question_policy_does_not_repeat_attributes(self):
        state = ConversationState(profile={})
        state.ingest("I'm looking for Shoes, but I'm still exploring.")
        first, _ = next_question(state)
        second, _ = next_question(state)

        self.assertEqual(first, "feature")
        self.assertEqual(second, "material")

    def test_question_policy_requests_missing_category_first(self):
        state = ConversationState(profile={})
        state.ingest("I need some ideas.")
        attribute, _ = next_question(state)

        self.assertEqual(attribute, "category")

    def test_can_request_more_information_for_observed_attribute(self):
        state = ConversationState(profile={})
        state.ingest("I'm looking for Trail Running. A key requirement is: 100% Synthetic.")
        attribute, question = next_question(state)

        self.assertEqual(attribute, "feature")
        self.assertIn("another", question.lower())

    def test_profile_signal_changes_later_question_priority(self):
        state = ConversationState(profile={"preference_tags": ["fit"]})
        state.ingest("I'm looking for Shirts, but I'm still exploring.")
        asked = [next_question(state)[0] for _ in range(4)]

        self.assertEqual(asked, ["feature", "material", "color", "size"])


if __name__ == "__main__":
    unittest.main()
