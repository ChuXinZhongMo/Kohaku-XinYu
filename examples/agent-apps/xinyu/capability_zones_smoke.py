from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    state = (root / "memory/context/capability_zones_state.md").read_text(encoding="utf-8-sig")
    failures: list[str] = []
    required = (
        "Zone A Always Allowed",
        "Zone B Ask Or Thoughts First",
        "Zone C Blocked Unless Explicit One-Time Approval",
        "read_write_local_authorized_scope: allowed_inside_safe_resolver",
        "local_authorized_scope: D:\\XinYu\\XinYu-Local-Scope",
        "private_file_scope: local_authorized_scope_only",
        "resolver: xinyu_local_scope.resolve_local_scope_path",
        "outside_scope: ask_first_or_blocked",
        "autonomous_search_provider: enabled_duckduckgo_html_bounded",
        "autonomous_search_max_queries_per_pass: 2",
        "proactive_qq_send: enabled_gated_one_short_message",
        "stable_personality_auto_apply: disabled",
        "not_granted_private_full_disk_access: yes",
        "not_granted_credential_cookie_token_access: yes",
    )
    for marker in required:
        if marker not in state:
            failures.append(f"capability zones missing marker: {marker}")
    if failures:
        print("Capability zones smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Capability zones smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
