from __future__ import annotations

from xinyu_runtime_failure_freshness import (
    codex_delegate_failure_active,
    parse_inline_fields,
    runtime_failure_counts_active,
    runtime_failure_detail_active,
)


CHECKED_AT = "2026-05-07T10:00:00+08:00"


def main() -> int:
    failures: list[str] = []

    stale_dead = {
        "dead_count": "1",
        "recent_dead_count": "0",
        "last_dead_at": "2026-05-06T23:00:00+08:00",
    }
    if runtime_failure_counts_active(stale_dead, checked_at=CHECKED_AT):
        failures.append("stale dead-only queue state should not be active")

    recent_dead = {
        "dead_count": "1",
        "recent_dead_count": "1",
        "last_dead_at": "2026-05-07T09:30:00+08:00",
    }
    if not runtime_failure_counts_active(recent_dead, checked_at=CHECKED_AT):
        failures.append("recent dead queue state should be active")

    stale_detail = (
        "failed_count=0 dead_count=1 recent_failed_count=0 "
        "recent_dead_count=0 last_dead_at=2026-05-06T23:00:00+08:00"
    )
    if runtime_failure_detail_active(stale_detail, checked_at=CHECKED_AT):
        failures.append("stale inline dead detail should not be active")

    failed_without_stamp = "failed_count=1 dead_count=0 last_failed_at=none"
    if not runtime_failure_detail_active(failed_without_stamp, checked_at=CHECKED_AT):
        failures.append("failed count without timestamp should stay active for compatibility")

    stale_codex = parse_inline_fields("status=failed updated_at=2026-05-06T23:00:00+08:00")
    if codex_delegate_failure_active(stale_codex, checked_at=CHECKED_AT):
        failures.append("stale codex delegate failure should not be active")

    missing_stamp_codex = parse_inline_fields("status=failed job_id=legacy")
    if not codex_delegate_failure_active(missing_stamp_codex, checked_at=CHECKED_AT):
        failures.append("codex delegate failure without timestamp should stay active for compatibility")

    if failures:
        print("Runtime failure freshness smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Runtime failure freshness smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
