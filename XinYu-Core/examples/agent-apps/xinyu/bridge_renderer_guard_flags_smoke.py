from __future__ import annotations

from xinyu_bridge_renderer import critical_final_guard_flags
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    flags = [
        "reply_quality_template_pressure",
        "machine_introspection_naturalized",
        "final_guard_repair_rendered",
        "false_codex_unavailable_claim_blocked",
        "layered_voice_self_analysis_blocked",
    ]
    expected = [
        "machine_introspection_naturalized",
        "false_codex_unavailable_claim_blocked",
        "layered_voice_self_analysis_blocked",
    ]

    if critical_final_guard_flags(flags) != expected:
        failures.append("critical final guard filtering changed")
    if critical_final_guard_flags(tuple(flags)) != expected:
        failures.append("critical final guard tuple filtering changed")
    if XinYuBridgeRuntime._critical_final_guard_flags(flags) != expected:
        failures.append("core bridge critical final guard alias no longer delegates")

    if failures:
        print("XinYu bridge renderer guard flags smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge renderer guard flags smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
