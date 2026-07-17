from __future__ import annotations

"""XinYu runtime status facade.

Implementation lives in:
- xinyu_status_models.py  (Check, constants, pure helpers)
- xinyu_status_qq_fields.py (QQ / private-reply / learning-trial field collectors)
- xinyu_status_checks.py (health / port / gateway / state checks)
- xinyu_status_collect.py (aggregate status_fields + re-exports)
- xinyu_status_render.py  (CLI / printing)

Public entrypoints remain importable from this module.
"""

from xinyu_status_models import (  # noqa: F401
    DEFAULT_AUTONOMY_DECISION_WINDOW_MINUTES,
    DEFAULT_CORE_URL,
    DEFAULT_QQ_GATEWAY_CONFIG,
    NO_PROXY_OPENER,
    TEXT_HEALTH_FILES,
    TEXT_HEALTH_MARKERS,
    Check,
    _as_status_str_list,
    _bounded_status_value,
    _note_metric,
    _private_id_hash,
    _redact_status_value,
    _stage12_live_status_stub,
    _status_int,
    extract_int_value,
    extract_value,
    file_sha256,
    load_json,
    mask_private_identifier,
    plugin_source_digest,
    read_text,
    redact_core_data,
    redact_local_path,
    runtime_text_health_issues,
)
from xinyu_status_checks import (  # noqa: F401
    check_core,
    check_ports,
    check_qq_gateway_config,
    check_state,
    dispatch_state_detail,
    extract_gateway_version,
    extract_shell_version,
    has_established_local,
    http_json,
    netstat_lines,
    tcp_connect,
)
from xinyu_status_collect import (  # noqa: F401
    _load_jsonl_tail,
    _qq_private_no_reply_explanation,
    _qq_rows_with_prepared_links,
    _qq_trace_generation_groups,
    autonomy_decision_chain_fields,
    group_social_fields,
    learning_trial_gate_fields,
    nine_score_fields,
    private_reply_selftest_fields,
    qq_group_reply_boundary_fields,
    qq_latest_inbound_flow_fields,
    qq_private_reply_flow_fields,
    status_fields,
)
from xinyu_status_render import (  # noqa: F401
    build_parser,
    main,
    print_checks,
    print_section,
)

if __name__ == "__main__":
    raise SystemExit(main())
