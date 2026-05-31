from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from behavior_shadow_log import append_behavior_shadow_event, behavior_shadow_event, shadow_gate_payload


class BehaviorShadowLogTests(unittest.TestCase):
    def test_shadow_gate_payload_maps_user_text(self) -> None:
        payload = shadow_gate_payload({"user_text": "\u8c01\u554a", "act": "question", "source": "unit_test"})
        self.assertEqual(payload["u"], "\u8c01\u554a")
        self.assertEqual(payload["act"], "question")
        self.assertEqual(payload["source"], "unit_test")

    def test_shadow_event_is_safe_by_default(self) -> None:
        event = behavior_shadow_event({"user_text": "\u4f60\u5148\u522b\u54ed", "turn_id": "t1"})
        self.assertEqual(event["schema"], "xinyu_behavior_shadow_log_v001")
        self.assertEqual(event["behavior"]["mode"], "reply")
        self.assertNotIn("u", event)
        self.assertTrue(event["shadow_only"])
        self.assertFalse(event["visible_reply_sent"])
        self.assertFalse(event["stable_memory_written"])
        self.assertFalse(event["tool_executed"])
        self.assertFalse(event["adapter_activated"])
        self.assertFalse(event["training_target"])

    def test_shadow_event_can_include_text_explicitly(self) -> None:
        event = behavior_shadow_event({"user_text": "\u8c01\u554a"}, include_text=True)
        self.assertEqual(event["u"], "\u8c01\u554a")
        self.assertEqual(event["behavior"]["mode"], "clarify")

    def test_append_behavior_shadow_event_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "shadow.jsonl"
            result = append_behavior_shadow_event(
                {"user_text": "\u5982\u679c\u4ed6\u4e0d\u5728\u8fd9\u91cc"},
                path=path,
                source_endpoint="unit_test",
            )
            self.assertTrue(result["stored"])
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["behavior"]["mode"], "wait")
            self.assertEqual(rows[0]["source_endpoint"], "unit_test")
            self.assertNotIn("u", rows[0])


if __name__ == "__main__":
    unittest.main()
