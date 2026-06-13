from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_private_reply_selftest_store import append_private_reply_selftest_trace
from xinyu_private_reply_selftest_store import read_private_reply_selftest_text
from xinyu_private_reply_selftest_store import write_private_reply_selftest_state
from xinyu_qq_config import GatewayConfig
from xinyu_qq_gateway import NativeQQGateway


SELFTEST_STATE_REL = Path("runtime") / "private_reply_selftest_state.json"
SELFTEST_TRACE_REL = Path("runtime") / "private_reply_selftest_trace.jsonl"
SYNTHETIC_OWNER_USER_ID = "4242424242"
SYNTHETIC_PRIVATE_TEXT = "网关私聊自测：请只用一句话回应你已接住当前私聊。"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _short_hash(text: str) -> str:
    if not text:
        return ""
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{digest[:16]}"


def _bounded_text(value: Any, *, limit: int = 180) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return text[:limit]


def _project_root_from_app(root: Path) -> Path:
    current = root.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".xinyu_bridge_token").exists() or (parent / "XinYu.ps1").exists():
            return parent
    return current


def _load_bridge_token(project_root: Path, config: GatewayConfig) -> str:
    token = (config.bridge_token or os.environ.get("XINYU_BRIDGE_TOKEN") or "").strip()
    if token:
        return token
    token_path = project_root / ".xinyu_bridge_token"
    if not token_path.exists():
        return ""
    return read_private_reply_selftest_text(token_path).strip()


def _safe_trace_note(note: Any) -> str:
    text = _bounded_text(note, limit=120)
    allowed_prefixes = (
        "chunk_count:",
        "visible_chars:",
        "raw_assistant_chars:",
        "completion_tokens:",
        "tool_call_count:",
        "empty_",
        "timeout_seconds:",
    )
    return text if text.startswith(allowed_prefixes) else ""


def _read_jsonl_tail(path: Path, *, max_lines: int = 600) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = read_private_reply_selftest_text(path)
    if not text:
        return []
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _model_trace_summary(root: Path, turn_id: str) -> dict[str, Any]:
    if not turn_id:
        return {"present": False}
    rows = [
        row
        for row in _read_jsonl_tail(root / "runtime/turn_route_trace.jsonl")
        if str(row.get("turn_id") or "") == turn_id
    ]
    if not rows:
        return {"present": False, "turn_id": turn_id}

    route_decided = next((row for row in rows if row.get("stage") == "route_decided"), {})
    inject = next((row for row in reversed(rows) if row.get("stage") == "model_inject_finished"), {})
    finished = next((row for row in reversed(rows) if row.get("stage") == "route_finished"), {})
    empty_retry_rows = [
        row for row in rows if str(row.get("stage") or "").startswith("model_inject_empty_visible")
    ]
    raw_notes = inject.get("notes") if isinstance(inject.get("notes"), list) else []
    notes = [note for note in (_safe_trace_note(item) for item in raw_notes) if note]
    return {
        "present": True,
        "turn_id": turn_id,
        "route": _bounded_text(route_decided.get("route") or finished.get("route")),
        "route_status": _bounded_text(finished.get("status")),
        "model_inject_status": _bounded_text(inject.get("status")),
        "model_notes": notes,
        "empty_visible_stage_count": len(empty_retry_rows),
        "empty_visible_statuses": [
            _bounded_text(row.get("status")) for row in empty_retry_rows if row.get("status")
        ],
    }


class SyntheticPrivateGateway(NativeQQGateway):
    def __init__(self, config: GatewayConfig, *, client: Any | None = None) -> None:
        super().__init__(config)
        if client is not None:
            self.client = client
        self.synthetic_traces: list[dict[str, Any]] = []
        self.synthetic_sent_replies: list[dict[str, Any]] = []
        self.synthetic_acks: list[dict[str, Any]] = []

    def _trace_qq_inbound(
        self,
        event: dict[str, Any],
        *,
        stage: str,
        arrival_seq: int = 0,
        prepared: Any = None,
        session_queue_key: str = "",
        queue_depth: int | None = None,
        drop_reason: str = "",
        error: str = "",
        delivery_kind: str = "",
        adapter_message_id: str = "",
        adapter_error: str = "",
        voice_fallback_reason: str = "",
    ) -> None:
        del event, session_queue_key, queue_depth, delivery_kind, adapter_message_id, adapter_error, voice_fallback_reason
        route = ""
        text_len = 0
        if prepared is not None:
            route = _bounded_text(getattr(prepared, "route", ""))
            payload = getattr(prepared, "payload", {})
            if isinstance(payload, dict):
                text_len = len(str(payload.get("text") or ""))
        self.synthetic_traces.append(
            {
                "stage": _bounded_text(stage),
                "route": route,
                "arrival_seq": int(arrival_seq or 0),
                "drop_reason": _bounded_text(drop_reason),
                "error_type": _bounded_text(str(error).split(":", 1)[0] if error else ""),
                "text_len": text_len,
            }
        )

    def _trace_qq_rich_context(self, event: dict[str, Any], prepared: Any, *, stage: str) -> None:
        del event, prepared, stage

    def _record_direct_visible_send_shadow(
        self,
        prepared: Any,
        reply: str,
        core_response: dict[str, Any],
    ) -> dict[str, Any]:
        del prepared, reply, core_response
        return {
            "shadow_only": True,
            "raw_prompt_saved": False,
            "raw_reply_saved": False,
            "synthetic_selftest": True,
        }

    async def send_reply(self, websocket: Any, target: Any, text: str) -> dict[str, Any] | None:
        del websocket, target
        self.synthetic_sent_replies.append(
            {
                "reply_len": len(text or ""),
                "reply_hash": _short_hash(text or ""),
            }
        )
        return {"status": "ok", "retcode": 0, "data": {"message_id": 989001}}

    async def _ack_sent_visible_reply(
        self,
        prepared: Any,
        *,
        reply: str,
        core_response: dict[str, Any],
        action_response: dict[str, Any] | None,
    ) -> None:
        del prepared, action_response
        archive_ids = core_response.get("archive_message_ids")
        self.synthetic_acks.append(
            {
                "reply_len": len(reply or ""),
                "reply_hash": _bounded_text(core_response.get("reply_hash")),
                "turn_id": _bounded_text(core_response.get("turn_id")),
                "archive_count": len(archive_ids) if isinstance(archive_ids, list) else 0,
            }
        )


def _synthetic_event(*, test_id: str, text: str = SYNTHETIC_PRIVATE_TEXT) -> dict[str, Any]:
    return {
        "post_type": "message",
        "message_type": "private",
        "sub_type": "friend",
        "user_id": SYNTHETIC_OWNER_USER_ID,
        "message_id": test_id,
        "time": int(datetime.now().timestamp()),
        "message": [{"type": "text", "data": {"text": text}}],
        "raw_message": text,
    }


def _build_config(
    root: Path,
    *,
    core_url: str,
    token: str,
    config_path: Path | None = None,
    timeout_seconds: int = 300,
) -> GatewayConfig:
    if config_path and config_path.exists():
        base = GatewayConfig.from_file(config_path)
        core_chat_url = core_url.rstrip("/") + "/chat" if not core_url.rstrip("/").endswith("/chat") else core_url
        base = base.with_overrides(core_chat_url=core_chat_url, bridge_token=token)
        return replace(
            base,
            owner_user_ids=frozenset({SYNTHETIC_OWNER_USER_ID}),
            whitelist_user_ids=frozenset({SYNTHETIC_OWNER_USER_ID}),
            owner_private_coalesce_seconds=0.0,
            send_replies=True,
            timeout_seconds=timeout_seconds,
            gateway_ack_spool_path=str(root / "runtime/private_reply_selftest_ack_spool.jsonl"),
        )
    core_chat_url = core_url.rstrip("/") + "/chat" if not core_url.rstrip("/").endswith("/chat") else core_url
    return GatewayConfig(
        bridge_token=token,
        core_chat_url=core_chat_url,
        owner_user_ids=frozenset({SYNTHETIC_OWNER_USER_ID}),
        whitelist_user_ids=frozenset({SYNTHETIC_OWNER_USER_ID}),
        owner_private_coalesce_seconds=0.0,
        send_replies=True,
        timeout_seconds=timeout_seconds,
        gateway_ack_spool_path=str(root / "runtime/private_reply_selftest_ack_spool.jsonl"),
    )


async def run_private_reply_selftest(
    root: Path,
    *,
    core_url: str = "http://127.0.0.1:8765",
    token: str = "",
    config_path: Path | None = None,
    client: Any | None = None,
    write: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    checked_at = _now_iso()
    test_id = "private-reply-selftest-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f")
    config = _build_config(root, core_url=core_url, token=token, config_path=config_path)
    gateway = SyntheticPrivateGateway(config, client=client)
    error = ""
    try:
        await gateway._handle_onebot_event(
            None,
            _synthetic_event(test_id=test_id),
            arrival_seq=7001,
            session_queue_key="private-reply-selftest",
        )
    except Exception as exc:  # pragma: no cover - defensive for live operator path
        error = f"{type(exc).__name__}: {_bounded_text(exc)}"

    stages = [item.get("stage", "") for item in gateway.synthetic_traces]
    drop_reasons = [item.get("drop_reason", "") for item in gateway.synthetic_traces if item.get("drop_reason")]
    latest_ack = gateway.synthetic_acks[-1] if gateway.synthetic_acks else {}
    turn_id = _bounded_text(latest_ack.get("turn_id"))
    model_trace = _model_trace_summary(root, turn_id)
    reply_sent = "reply_sent" in stages
    empty_drop = "empty_visible_reply" in drop_reasons
    ok = bool(reply_sent and gateway.synthetic_sent_replies and gateway.synthetic_acks and not empty_drop and not error)
    state = {
        "schema_version": 1,
        "status": "pass" if ok else "fail",
        "checked_at": checked_at,
        "test_id_hash": _short_hash(test_id),
        "scope": "synthetic_owner_private_gateway_to_core_no_real_qq_send",
        "core_url": core_url.rstrip("/"),
        "trace": {
            "stages": stages,
            "drop_reasons": drop_reasons,
            "reply_sent": reply_sent,
            "empty_visible_drop": empty_drop,
            "dispatch_error": any(stage == "dispatch_error" for stage in stages),
        },
        "send": {
            "captured_send_count": len(gateway.synthetic_sent_replies),
            "captured_replies": gateway.synthetic_sent_replies,
            "real_qq_send": False,
        },
        "ack": {
            "captured_ack_count": len(gateway.synthetic_acks),
            "captured_acks": gateway.synthetic_acks,
            "real_ack_written": False,
        },
        "model": model_trace,
        "error": error,
        "privacy": {
            "raw_user_text_included": False,
            "visible_reply_text_included": False,
            "raw_prompt_included": False,
            "raw_reply_included": False,
            "qq_inbound_trace_written": False,
            "only_hashes_lengths_stages_and_counts": True,
        },
    }
    if write:
        state_path = root / SELFTEST_STATE_REL
        trace_path = root / SELFTEST_TRACE_REL
        write_private_reply_selftest_state(state_path, state)
        append_private_reply_selftest_trace(trace_path, state)
    return state


def format_report(state: dict[str, Any]) -> str:
    trace = state.get("trace") if isinstance(state.get("trace"), dict) else {}
    send = state.get("send") if isinstance(state.get("send"), dict) else {}
    ack = state.get("ack") if isinstance(state.get("ack"), dict) else {}
    model = state.get("model") if isinstance(state.get("model"), dict) else {}
    lines = [
        "XinYu 私聊回复链路自检",
        f"结果: {'通过' if state.get('status') == 'pass' else '失败'}",
        f"检查时间: {state.get('checked_at')}",
        f"范围: {state.get('scope')}",
        "",
        "证据:",
        f"- stages: {','.join(str(item) for item in trace.get('stages', []))}",
        f"- reply_sent: {trace.get('reply_sent')} empty_visible_drop: {trace.get('empty_visible_drop')}",
        f"- captured_send_count: {send.get('captured_send_count')} real_qq_send: {send.get('real_qq_send')}",
        f"- captured_ack_count: {ack.get('captured_ack_count')} real_ack_written: {ack.get('real_ack_written')}",
        (
            f"- model: present={model.get('present')} route={model.get('route', '')} "
            f"notes={','.join(str(item) for item in model.get('model_notes', []))}"
        ),
        "",
        "隐私边界: 不输出私聊原文、可见回复正文、prompt 原文或 reply 原文。",
    ]
    if state.get("error"):
        lines.append(f"error: {state.get('error')}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a privacy-safe synthetic owner-private reply self-test.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default="http://127.0.0.1:8765")
    parser.add_argument("--qq-config", type=Path, default=Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json"))
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    project_root = _project_root_from_app(root)
    base_config = GatewayConfig.from_file(args.qq_config) if args.qq_config.exists() else GatewayConfig()
    token = _load_bridge_token(project_root, base_config)
    state = asyncio.run(
        run_private_reply_selftest(
            root,
            core_url=args.core_url,
            token=token,
            config_path=args.qq_config if args.qq_config.exists() else None,
            write=not args.no_write,
        )
    )
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
    else:
        print(format_report(state))
    return 0 if state.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
