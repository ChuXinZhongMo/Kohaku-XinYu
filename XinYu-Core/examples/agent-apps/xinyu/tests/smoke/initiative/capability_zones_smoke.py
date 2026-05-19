from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from pathlib import Path


def main() -> int:
    root = ROOT
    state = (root / "memory/context/capability_zones_state.md").read_text(encoding="utf-8-sig")
    failures: list[str] = []
    required = (
        "Zone A Always Allowed",
        "Zone B Ask Or Thoughts First",
        "Zone C Blocked Unless Explicit One-Time Approval",
        "read_write_local_authorized_scope: allowed_inside_safe_resolver",
        "read_owner_designated_directories: allowed_read_only_inside_safe_resolver",
        "local_authorized_scope: D:\\XinYu\\XinYu-Local-Scope",
        "private_file_scope: local_authorized_scope_only",
        "owner_designated_read_dirs: configured_by_XINYU_LOCAL_READ_DIRS",
        "owner_designated_read_policy: read_only_no_parent_traversal_no_indexing_without_new_grant",
        "owner_designated_read_resolver: xinyu_local_scope.resolve_read_only_scope_path",
        "resolver: xinyu_local_scope.resolve_local_scope_path",
        "outside_scope: ask_first_or_blocked",
        "autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain",
        "autonomous_search_max_queries_per_pass: 3",
        "regular_mind_loop: approved_low_frequency_autonomous_passes",
        "desktop_thought_autonomy_notes: allowed_periodic",
        "proactive_qq_send: enabled_gated_one_short_message",
        "codex_as_eye_and_hand: approved_bounded_delegate",
        "codex_request_queue: D:\\XinYu\\XinYu-Local-Scope\\Requests",
        "codex_download_workspace: D:\\XinYu\\XinYu-Local-Scope\\Workspace",
        "codex_learning_acceptance: source_comparison_learner_integration_learning_quality_required",
        "request_codex_image_analysis: allowed_for_owner_provided_or_authorized_local_scope_images",
        "use_codex_to_bypass_privacy_source_or_learning_gates: blocked",
        "receive_non_owner_private_qq: allowed_as_external_contact",
        "receive_group_qq_when_mentioned_or_prefixed: allowed_as_group_context",
        "qq_group_bridge: enabled_mention_or_prefix_only",
        "qq_priority_passive_learning_group: enabled_no_reply_observe_only",
        "qq_priority_passive_learning_group_scope: group_context_source_candidates_not_facts",
        "qq_priority_passive_learning_group_reply_policy: no_visible_reply_stop_pipeline",
        "proactive_qq_to_non_owner_or_group: blocked",
        "write_group_or_non_owner_private_facts_to_owner_memory: blocked",
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
