from __future__ import annotations

from xinyu_bridge_desktop_self_action_approval_dispatch import (
    ToThreadFunc,
    apply_existing_patch_executor_result,
    attach_desktop_self_action_patch_executor,
    attach_desktop_self_action_response,
    decide_desktop_self_action_approval,
    dispatch_desktop_self_action_approval_result,
    existing_handoff_authorized_result,
    existing_handoff_denied_result,
    should_attach_pending_patch_executor,
    should_authorize_existing_handoff,
    should_keep_existing_denied_noop,
)
from xinyu_bridge_desktop_self_action_approval_payload import (
    APPROVAL_DECISIONS,
    AUTHORIZE_CODEX_KEYS,
    AUTHORIZE_EXISTING_KEYS,
    DECISION_ALIASES,
    AsBoolFunc,
    DesktopSelfActionApprovalPayload,
    SafeStrFunc,
    first_present_payload_value,
    normalize_self_action_approval_decision,
    parse_desktop_self_action_approval_payload,
    parse_timeout_seconds,
    resolve_desktop_self_action_pending_item,
)
