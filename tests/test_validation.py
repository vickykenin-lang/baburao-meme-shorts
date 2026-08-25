import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from generate_script import parse_json_object, validate_script  # noqa: E402


def valid_payload():
    return {
        "hook": "Arre bhai, ye kya ho gaya!",
        "full_script": "Setup. Build. Punchline.",
        "caption": "Relatable scene 😂",
        "hashtags": ["#comedy", "#reels", "#shorts", "#hinglish", "#funny"],
        "topic": "office_lunchbox",
    }


class ValidationTests(unittest.TestCase):
    def test_valid_payload_passes(self):
        self.assertEqual(validate_script(valid_payload(), {"topics": []}), [])

    def test_recent_topic_is_rejected(self):
        errors = validate_script(valid_payload(), {"topics": ["office_lunchbox"]})
        self.assertIn("topic repeats one of the recent topics", errors)

    def test_requires_exactly_five_hashtags(self):
        payload = valid_payload()
        payload["hashtags"] = ["#one"]
        self.assertIn(
            "hashtags must be a list of exactly 5 items",
            validate_script(payload, {"topics": []}),
        )

    def test_parse_raw_json(self):
        payload = valid_payload()
        self.assertEqual(parse_json_object(json.dumps(payload)), payload)

    def test_parse_fenced_json_tolerantly(self):
        payload = valid_payload()
        wrapped = "```json\n" + json.dumps(payload) + "\n```"
        self.assertEqual(parse_json_object(wrapped), payload)


if __name__ == "__main__":
    unittest.main()
