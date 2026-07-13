from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_text_variants import legacy_mojibake_variants


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_QQ_GATEWAY_CONFIG = Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json")
DEFAULT_AUTONOMY_DECISION_WINDOW_MINUTES = 240
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

TEXT_HEALTH_FILES = (
    "memory/context/proactive_presence_state.md",
    "memory/context/proactive_request_state.md",
    "memory/context/proactive_response_diagnostics_state.md",
    "memory/context/proactive_qq_dispatch_state.md",
    "memory/context/memory_braid_state.md",
    "memory/context/turn_coherence_state.md",
    "memory/context/initiative_spine_state.md",
    "memory/context/desire_drive_state.md",
    "memory/context/short_term_continuity_state.md",
    "memory/context/short_term_continuity_canary_state.md",
    "memory/context/short_term_recall_diagnostics_state.md",
    "memory/context/perception_importance_state.md",
    "memory/context/action_feedback_coverage_state.md",
    "memory/context/owner_feedback_effect_state.md",
    "memory/context/decision_chain_latest_state.md",
    "memory/context/feedback_consumption_diagnostics_state.md",
    "memory/context/self_state_capsule_state.md",
    "memory/context/stage9_self_state_model_state.md",
    "memory/context/stage10_proactive_life_loop_state.md",
    "memory/context/stage11_multisensory_extension_state.md",
    "memory/context/stage11_visual_ingress_diagnostics_state.md",
    "memory/context/stage11_voice_ingress_diagnostics_state.md",
    "memory/context/stage12_long_term_evaluation_state.md",
    "memory/context/self_chosen_goal_ecology_state.md",
    "memory/context/self_action_gateway_state.md",
    "memory/context/self_action_gateway_execution_handoff.md",
    "memory/context/self_action_patch_executor_state.md",
    "memory/context/self_action_patch_executor_task.md",
    "memory/context/self_thought_state.md",
    "memory/context/emotion_council_state.md",
    "memory/context/impulse_soup_state.md",
    "memory/context/early_visible_segment_shadow_state.md",
    "memory/self/expression_self_learning_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
)

TEXT_HEALTH_MARKERS = (
    "\u54e5",
    "\u4e3b\u4eba",
    "\u8bb0\u5fc6",
    "\u53cd\u601d\u961f\u5217",
    "\u5173\u4e8e\u88ab\u8bb0\u4f4f",
    "\u8fd8\u6ca1\u653e\u4e0b",
    "\u957f\u671f\u5173\u7cfb",
    "\u5177\u4f53\u5bf9\u8bdd",
    "\u8bb0\u5fc6\u7559\u75d5",
    "\u5916\u90e8\u5b66\u4e60",
    "\u4e3b\u52a8\u7ebf\u7a0b",
    "\u60c5\u611f\u7cfb\u7edf",
    "\u4e3b\u4eba\u683c",
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _stage12_live_status_stub() -> dict[str, Any]:
    # Avoid recursive xinyu_status -> stage12 -> live_loop_report -> xinyu_status.
    return {
        "ok": True,
        "known_error_count": 0,
        "checks": [
            {"name": "core_bridge", "ok": True},
            {"name": "xinyu_qq_gateway_6199", "ok": True},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": True},
        ],
    }


def runtime_text_health_issues(root: Path) -> list[str]:
    issues: list[str] = []
    for rel_path in TEXT_HEALTH_FILES:
        path = root / rel_path
        if not path.exists():
            continue
        text = read_text(path)
        if "\ufffd" in text:
            issues.append(f"{rel_path}:replacement_character")
        marker_hits: list[str] = []
        for marker in TEXT_HEALTH_MARKERS:
            if any(variant in text for variant in legacy_mojibake_variants(marker)):
                marker_hits.append(marker)
        if marker_hits:
            issues.append(f"{rel_path}:legacy_mojibake:{len(marker_hits)}")
    return issues


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def extract_int_value(text: str, field: str, default: int = 0) -> int:
    raw = extract_value(text, field, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def mask_private_identifier(value: str) -> str:
    return re.sub(r"\d{5,}", lambda m: m.group(0)[:2] + "***" + m.group(0)[-2:], value)


def redact_local_path(value: str) -> str:
    text = str(value)
    lowered = text.lower()
    if lowered.endswith("xinyu_core_bridge.py"):
        return "<xinyu_core_bridge.py>"
    if "xinyu_qq_gateway" in lowered:
        return "<xinyu_qq_gateway>"
    if "examples" in lowered and "agent-apps" in lowered and "xinyu" in lowered:
        return "<xinyu_dir>"
    if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\)", text):
        return "<local_path>"
    return text


def redact_core_data(data: dict[str, Any]) -> dict[str, Any]:
    return _redact_status_value(data)


def _redact_status_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_local_path(value)
    if isinstance(value, dict):
        return {key: _redact_status_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_status_value(item) for item in value]
    return value


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _as_status_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _private_id_hash(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _note_metric(notes: Any, prefix: str, default: str = "0") -> str:
    if not isinstance(notes, list):
        return default
    for note in notes:
        text = str(note or "")
        if text.startswith(prefix):
            return _bounded_status_value(text[len(prefix) :], default)
    return default


def _status_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def file_sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plugin_source_digest(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""
    digest = hashlib.sha256()
    for file_path in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not file_path.is_file() or file_path.suffix.lower() not in {".py", ".yaml", ".json"}:
            continue
        digest.update(file_path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(file_path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _bounded_status_value(value: Any, default: str = "missing") -> str:
    if value is None:
        return default
    text = mask_private_identifier(redact_local_path(str(value).strip()))
    if not text:
        return default
    if len(text) > 240:
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
        return f"<omitted_long_value:sha256:{digest}>"
    return text

