import unittest
from datetime import datetime, timezone

from backend.services.followup_extractor import extract_followups
from backend.services.thread_ranker import rank_thread
from backend.services.tone_risk_detector import detect_tone_risks


class ThreadRankerTests(unittest.TestCase):
    def test_sensitive_thread_requires_careful_review(self):
        ranked = rank_thread(
            {
                "latest_at": datetime.now(timezone.utc),
                "needs_response_estimate": True,
                "messages": [
                    {
                        "is_from_me": False,
                        "text": "The medical bill and lawyer deadline both need a response today.",
                    }
                ],
            }
        )

        self.assertEqual(ranked["priority_label"], "risky_to_answer_fast")
        self.assertEqual(ranked["category"], "review_carefully")
        self.assertEqual(ranked["urgency"], "high")
        self.assertGreaterEqual(ranked["risk_score"], 2)

    def test_completed_thread_does_not_request_a_reply(self):
        ranked = rank_thread(
            {
                "latest_at": datetime.now(timezone.utc),
                "needs_response_estimate": False,
                "messages": [{"is_from_me": False, "text": "Are you free for coffee today?"}],
            }
        )

        self.assertEqual(ranked["priority_label"], "no_response_needed")
        self.assertEqual(ranked["category"], "no_reply_needed")


class ToneRiskTests(unittest.TestCase):
    def test_multiple_risks_raise_high_severity(self):
        result = detect_tone_risks(
            "I was just trying to help. You always make this ridiculous. "
            "Maybe later, we'll see."
        )

        self.assertEqual(result["severity"], "high")
        self.assertIn("too_defensive", result["flags"])
        self.assertIn("angry", result["flags"])
        self.assertIn("vague", result["flags"])

    def test_grounded_draft_has_no_flags(self):
        result = detect_tone_risks("Thanks for checking in. I can call Thursday at 3 PM.")

        self.assertEqual(result["severity"], "none")
        self.assertEqual(result["flags"], [])


class FollowupExtractorTests(unittest.TestCase):
    def test_extracts_direction_due_date_and_question(self):
        followups = extract_followups(
            [
                {
                    "message_id": "out-1",
                    "is_from_me": True,
                    "text": "I'll send the report by Friday.",
                },
                {
                    "message_id": "in-1",
                    "is_from_me": False,
                    "text": "Can you check the totals today?",
                },
            ],
            "thread-1",
        )

        directions = {item["direction"] for item in followups}
        self.assertIn("user_owes_them", directions)
        self.assertIn("they_owe_user", directions)
        self.assertIn("unanswered_question", directions)

        promise = next(item for item in followups if item["direction"] == "user_owes_them")
        self.assertEqual(promise["due_date"], "by friday")
        self.assertEqual(promise["source_message_id"], "out-1")


if __name__ == "__main__":
    unittest.main()
