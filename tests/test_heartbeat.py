import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import heartbeat


class HeartbeatTests(unittest.TestCase):
    def test_required_governance_exists(self):
        for name in heartbeat.REQUIRED_GOVERNANCE:
            self.assertTrue((ROOT / name).exists(), name)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_are_reported_without_values(self):
        status = heartbeat.build_status()
        self.assertFalse(status["production_provider_ready"])
        self.assertIn("AWS_BEDROCK_CREDENTIALS_UNAVAILABLE", status["blockers"])
        serialized = str(status)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY=", serialized)

    @patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}, clear=True)
    def test_provider_ready_when_required_credentials_present(self):
        status = heartbeat.build_status()
        self.assertTrue(status["production_provider_ready"])
        self.assertEqual(status["department_state"], "READY_FOR_DIAGNOSIS")


if __name__ == "__main__":
    unittest.main()
