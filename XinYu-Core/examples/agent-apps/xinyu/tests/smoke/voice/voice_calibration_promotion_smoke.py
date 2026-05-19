from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import shutil
import tempfile
from pathlib import Path

from xinyu_voice_promotion_gate import build_voice_promotion_review


def main() -> int:
    root = ROOT
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-voice-promotion-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/self"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "memory/self/voice_calibration_log.md", target / "voice_calibration_log.md")
        shutil.copy2(root / "memory/self/voice_profile_zh.md", target / "voice_profile_zh.md")
        before_profile = (target / "voice_profile_zh.md").read_text(encoding="utf-8-sig")

        result = build_voice_promotion_review(
            temp_root,
            evaluated_at="2026-04-27T02:30:00+08:00",
            min_evidence=2,
        )
        state_path = target / "voice_profile_review_state.md"
        if not state_path.exists():
            failures.append("review state file was not written")
        else:
            state = state_path.read_text(encoding="utf-8")
            for marker in (
                "review_status: pending_owner_review",
                "stable_profile_write: blocked_until_owner_accepts",
                "owner_review_status: pending",
                "rollback_note:",
                "voice-profile-gpt_like_smoothness",
                "affected_smokes: tests/smoke/voice/voice_learning_smoke.py, tests/smoke/voice/chinese_voice_guard_smoke.py, tests/smoke/voice/integration/real_conversation_quality_smoke.py",
            ):
                if marker not in state:
                    failures.append(f"review state missing marker: {marker}")

        after_profile = (target / "voice_profile_zh.md").read_text(encoding="utf-8-sig")
        if before_profile != after_profile:
            failures.append("promotion gate rewrote stable voice_profile_zh.md")
        if int(result["candidate_count"]) < 1:
            failures.append(f"expected at least one promotion candidate: {result}")
        if int(result["entry_count"]) < 2:
            failures.append(f"expected repeated evidence entries: {result}")

    if failures:
        print("Voice calibration promotion smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Voice calibration promotion smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
