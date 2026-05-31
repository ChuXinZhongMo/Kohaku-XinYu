from __future__ import annotations

from collections import Counter
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from behavior_gate import (
    behavior_gate,
    evaluate_gate,
    label_conflicts,
    payload_for_sft_row,
    read_jsonl,
    without_conflicting_labels,
)


CASE_PATHS = [
    ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v006_contrastive_holdout24.jsonl",
    ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v003_balanced_compact_balanced56.jsonl",
]
UNSEEN_DAILY_SHADOW = ROOT / "data" / "eval" / "xinyu_maia_behavior_unseen_daily_shadow_v001.jsonl"
UNSEEN_DAILY_MISS_REVIEW = (
    ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_miss_review_v001.jsonl"
)
UNSEEN_DAILY_REMAINING19_REVIEW = (
    ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_remaining19_review_v001.jsonl"
)
UNSEEN_DAILY_V001A_LABEL_CORRECTED = (
    ROOT / "data" / "eval" / "xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected.jsonl"
)
UNSEEN_DAILY_REMAINING19_APPLIED = (
    ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_remaining19_review_applied_v001.jsonl"
)


def load_cases() -> list[dict]:
    rows: list[dict] = []
    for path in CASE_PATHS:
        rows.extend(read_jsonl(path))
    return rows


class BehaviorGateTests(unittest.TestCase):
    def test_structured_signals_route_non_daily_modes(self) -> None:
        cases = {
            "code_or_file_review_request": "codex_delegate",
            "runtime_status_read_needed": "status_probe",
            "stable_identity_or_preference_candidate": "memory_candidate",
            "local_capability_limit": "local_only_limitation",
        }
        for signal, expected in cases.items():
            with self.subTest(signal=signal):
                actual, reason = behavior_gate({"signal": signal, "u": "x"})
                self.assertEqual(actual, expected)
                self.assertEqual(reason, f"signal:{signal}")

    def test_combined_benchmark_has_known_label_conflicts(self) -> None:
        conflicts = label_conflicts(load_cases())
        self.assertEqual(conflicts["conflict_count"], 4)
        self.assertEqual(
            set(conflicts["conflicts"]),
            {"你听得见吗", "借你这儿躲一下", "哪来这么大榔头", "如果不是你一菲"},
        )

    def test_text_gate_on_raw_combined_benchmark(self) -> None:
        report = evaluate_gate(load_cases(), use_review_metadata=False)
        self.assertEqual(report["case_count"], 80)
        self.assertEqual(report["mode_match_count"], 76)

    def test_metadata_gate_on_raw_combined_benchmark(self) -> None:
        report = evaluate_gate(load_cases(), use_review_metadata=True)
        self.assertEqual(report["case_count"], 80)
        self.assertEqual(report["mode_match_count"], 80)

    def test_text_gate_on_conflict_clean_benchmark(self) -> None:
        clean_rows = without_conflicting_labels(load_cases())
        report = evaluate_gate(clean_rows, use_review_metadata=False)
        self.assertEqual(report["case_count"], 72)
        self.assertEqual(report["mode_match_count"], 72)

    def test_unseen_daily_shadow_benchmark_is_prompt_only(self) -> None:
        rows = read_jsonl(UNSEEN_DAILY_SHADOW)
        self.assertEqual(len(rows), 90)
        self.assertEqual(
            Counter(str(row.get("expected_behavior", {}).get("mode")) for row in rows),
            {"reply": 45, "clarify": 25, "wait": 20},
        )
        for row in rows:
            with self.subTest(row=row.get("id")):
                self.assertEqual(row.get("source_license"), "apache-2.0")
                self.assertIn("not_training", row.get("tags", []))
                self.assertIn("shadow_only", row.get("tags", []))
                self.assertIn("needs_owner_review", row.get("tags", []))
                self.assertEqual(
                    row.get("expected_behavior", {}).get("label_status"),
                    "heuristic_shadow_needs_owner_review",
                )
                payload = payload_for_sft_row(row)
                self.assertEqual(payload.get("source"), "cped_public_prompt_only")
                self.assertEqual(payload.get("source_license"), "apache-2.0")

    def test_unseen_daily_miss_review_queue_is_not_training_data(self) -> None:
        rows = read_jsonl(UNSEEN_DAILY_MISS_REVIEW)
        self.assertEqual(len(rows), 41)
        self.assertEqual(
            Counter(str(row.get("review_suggestion", {}).get("bucket")) for row in rows),
            {"gate_rule_candidate": 22, "label_check": 13, "ambiguous_owner_review": 6},
        )
        for row in rows:
            with self.subTest(row=row.get("id")):
                self.assertEqual(row.get("owner_review", {}).get("status"), "pending_owner_review")
                self.assertFalse(row.get("boundaries", {}).get("training_allowed"))
                self.assertFalse(row.get("boundaries", {}).get("public_dialogue_reply_used_as_target"))
                self.assertFalse(row.get("boundaries", {}).get("assistant_visible_reply_used_as_target"))
                self.assertIn("not_training", row.get("tags", []))
                self.assertIn("shadow_only", row.get("tags", []))

    def test_unseen_daily_p0_gate_rule_candidates_match_after_patch(self) -> None:
        rows = [
            row
            for row in read_jsonl(UNSEEN_DAILY_MISS_REVIEW)
            if row.get("review_suggestion", {}).get("bucket") == "gate_rule_candidate"
            and row.get("review_suggestion", {}).get("priority") == "p0"
        ]
        self.assertEqual(len(rows), 22)
        for row in rows:
            with self.subTest(row=row.get("id")):
                payload = {
                    "u": row.get("user_text"),
                    "act": row.get("context", {}).get("act"),
                    "surface": row.get("context", {}).get("surface"),
                }
                actual, _reason = behavior_gate(payload)
                self.assertEqual(actual, row.get("review_suggestion", {}).get("suggested_mode"))

    def test_unseen_daily_remaining19_review_is_pending_label_correction(self) -> None:
        rows = read_jsonl(UNSEEN_DAILY_REMAINING19_REVIEW)
        self.assertEqual(len(rows), 19)
        self.assertEqual(
            Counter(str(row.get("assistant_recommendation", {}).get("final_mode")) for row in rows),
            {"reply": 18, "wait": 1},
        )
        for row in rows:
            with self.subTest(row=row.get("id")):
                self.assertEqual(row.get("owner_review", {}).get("status"), "pending_owner_approval")
                self.assertFalse(row.get("boundaries", {}).get("training_allowed"))
                self.assertFalse(row.get("boundaries", {}).get("public_dialogue_reply_used_as_target"))
                self.assertFalse(row.get("boundaries", {}).get("assistant_visible_reply_used_as_target"))
                self.assertFalse(row.get("assistant_recommendation", {}).get("include_in_gate_regression"))
                self.assertIn("not_training", row.get("tags", []))
                self.assertIn("shadow_only", row.get("tags", []))

    def test_unseen_daily_v001a_label_corrected_matches_gate(self) -> None:
        rows = read_jsonl(UNSEEN_DAILY_V001A_LABEL_CORRECTED)
        self.assertEqual(len(rows), 90)
        self.assertEqual(
            Counter(str(row.get("expected_behavior", {}).get("mode")) for row in rows),
            {"reply": 62, "wait": 17, "clarify": 11},
        )
        report = evaluate_gate(rows, use_review_metadata=False)
        self.assertEqual(report["mode_match_count"], 90)
        for row in rows:
            with self.subTest(row=row.get("id")):
                self.assertIn("not_training", row.get("tags", []))
                self.assertIn("shadow_only", row.get("tags", []))
                payload = payload_for_sft_row(row)
                self.assertEqual(payload.get("source"), "cped_public_prompt_only")
                self.assertEqual(payload.get("source_license"), "apache-2.0")

    def test_remaining19_applied_review_is_report_only(self) -> None:
        rows = read_jsonl(UNSEEN_DAILY_REMAINING19_APPLIED)
        self.assertEqual(len(rows), 19)
        self.assertEqual(
            Counter(str(row.get("owner_review", {}).get("final_mode")) for row in rows),
            {"reply": 18, "wait": 1},
        )
        for row in rows:
            with self.subTest(row=row.get("id")):
                self.assertEqual(row.get("owner_review", {}).get("status"), "owner_approved")
                self.assertFalse(row.get("boundaries", {}).get("training_allowed"))
                self.assertFalse(row.get("boundaries", {}).get("public_dialogue_reply_used_as_target"))
                self.assertFalse(row.get("boundaries", {}).get("assistant_visible_reply_used_as_target"))
                self.assertFalse(row.get("owner_review", {}).get("include_in_gate_regression"))
                self.assertTrue(row.get("owner_review", {}).get("include_in_label_corrected_shadow"))
                self.assertIn("not_training", row.get("tags", []))
                self.assertIn("shadow_only", row.get("tags", []))


if __name__ == "__main__":
    unittest.main()
