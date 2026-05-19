from __future__ import annotations

import sys
from pathlib import Path


CUSTOM_DIR = Path(__file__).resolve().parents[1] / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from source_protocol_utils import (  # noqa: E402
    extract_dash_value,
    is_allowed_source_url,
    next_dated_id,
    split_search_results,
    split_source_requests,
)
from source_request_planner_engine import extract_value as extract_planner_value  # noqa: E402
from source_search_provider_engine import extract_value as extract_provider_value  # noqa: E402
from ops.probes.xinyu_research_loop_dry_run import split_requests as split_probe_source_requests  # noqa: E402
from xinyu_self_thought_loop import _split_source_requests as split_self_thought_source_requests  # noqa: E402


def test_split_source_requests_preserves_default_fields_and_skips_none_question() -> None:
    text = """# Source Requests

## request-2026-05-18-001
- question_id: q-001
- target: ai-self-understanding
- query: ai memory agents reliable source
- url: none
- status: pending_url

## request-local
- question_id: none
- target: ignored
- status: hold
"""

    requests = split_source_requests(text)

    assert len(requests) == 1
    assert requests[0]["request_id"] == "request-2026-05-18-001"
    assert requests[0]["reason"] == "existing request"
    assert requests[0]["followup_slot"] == "1"


def test_split_source_requests_can_keep_none_question_for_gate_counts() -> None:
    text = """## request-local
- question_id: none
- target: general
- url: https://example.test/source
- status: ready
"""

    requests = split_source_requests(
        text,
        fields=("question_id", "target", "url", "status"),
        skip_none_question=False,
    )

    assert requests == [
        {
            "request_id": "request-local",
            "question_id": "none",
            "target": "general",
            "url": "https://example.test/source",
            "status": "ready",
        }
    ]


def test_split_search_results_and_next_dated_id() -> None:
    text = """## result-2026-05-18-001
- request_id: request-2026-05-18-001
- url: https://example.test/a
- status: candidate

## result-2026-05-18-002
- request_id: request-2026-05-18-001
- url: https://example.test/b
- status: candidate
"""

    results = split_search_results(text)

    assert [item["result_id"] for item in results] == ["result-2026-05-18-001", "result-2026-05-18-002"]
    assert next_dated_id(results, id_field="result_id", prefix="result", date_part="2026-05-18") == "result-2026-05-18-003"


def test_is_allowed_source_url_requires_http_host() -> None:
    assert is_allowed_source_url("https://example.test/page")
    assert not is_allowed_source_url("file:///C:/secret.txt")
    assert not is_allowed_source_url("https:///missing-host")


def test_source_protocol_dash_value_wrappers_keep_legacy_names() -> None:
    text = """# State
- activation_permission: provider_allowed
- reason: owner approved
"""

    assert extract_dash_value(text, "activation_permission", "blocked") == "provider_allowed"
    assert extract_planner_value(text, "reason", "unknown") == "owner approved"
    assert extract_provider_value(text, "missing", "fallback") == "fallback"


def test_self_thought_source_request_parser_keeps_legacy_defaults() -> None:
    text = """## request-local
- question_id: none
- query: reliable source
- status: pending_url
"""

    requests = split_self_thought_source_requests(text)

    assert requests == [
        {
            "request_id": "request-local",
            "question_id": "none",
            "target": "general",
            "query": "reliable source",
            "status": "pending_url",
            "followup_kind": "none",
            "reason": "none",
        }
    ]


def test_research_probe_source_request_parser_keeps_legacy_id_shape() -> None:
    text = """## request-2026-05-18-001
- question_id: q-006
- target: ai-self-understanding
- query: ai memory agents
- url: none
- status: ready
- source_policy: controlled_fetch_only
"""

    requests = split_probe_source_requests(text)

    assert requests == [
        {
            "id": "request-2026-05-18-001",
            "question_id": "q-006",
            "target": "ai-self-understanding",
            "query": "ai memory agents",
            "url": "",
            "status": "ready",
            "source_policy": "controlled_fetch_only",
        }
    ]
