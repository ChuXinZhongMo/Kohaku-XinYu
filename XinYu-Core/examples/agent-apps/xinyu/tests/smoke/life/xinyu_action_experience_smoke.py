from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import json
import tempfile
from pathlib import Path

from xinyu_action_layer import XinyuActionLayer
from xinyu_action_reply_composer import compose_action_reply
from xinyu_experience_frame import (
    build_experience_frame,
    compose_recent_action_followup,
    read_recent_action_context,
    write_action_experience_residue,
    write_recent_action_experience,
)
from xinyu_memory_event_sourcing import record_action_experience_event
from xinyu_self_choice_store import SelfChoiceStore
from xinyu_tool_protocol import ActionOutcome, ToolIntent, ToolRequest, ToolTarget


def _owner_payload(text: str = "ping") -> dict:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "owner",
        "message_id": "msg-1",
        "text": text,
        "metadata": {"is_owner_user": True},
    }


def _write_config(root: Path) -> None:
    config = {
        "version": 1,
        "targets": {
            "xinyu_logs": {
                "kind": "logs",
                "read_roots": ["logs"],
                "patterns": ["*.log"],
                "owner_setup_required": False,
            },
            "minecraft_server": {
                "kind": "logs",
                "read_roots": [],
                "patterns": ["logs/latest.log"],
                "owner_setup_required": True,
            },
        },
    }
    path = root / "config/tool_targets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


async def _run() -> list[str]:
    failures: list[str] = []
    scratch = ROOT / "runtime/action_layer_smoke_tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xinyu-action-smoke-", dir=str(scratch)) as tmp:
        root = Path(tmp)
        (root / "logs").mkdir(parents=True)
        (root / "logs/core.log").write_text(
            "2026-05-05 ok\n2026-05-05 ERROR bridge request timeout\n",
            encoding="utf-8",
        )
        _write_config(root)
        layer = XinyuActionLayer(root)
        payload = _owner_payload()

        if layer.route(payload, "那个破网关又卡死了，烦死").kind != "no_action":
            failures.append("ordinary complaint should not trigger tools")
        status_decision = layer.route(payload, "/status")
        if status_decision.kind != "action_request" or not status_decision.request or status_decision.request.tool != "status_probe":
            failures.append("/status should route to status_probe")
        negative_decision = layer.route(payload, "别帮我扫 xinyu_logs 日志")
        if negative_decision.kind != "blocked":
            failures.append("negative marker should block tool route")

        missing_req = ToolRequest(
            turn_id="turn-missing",
            source="qq_owner_private",
            intent=ToolIntent("local_inspect", 0.9, ["test"]),
            tool="log_scan",
            target=ToolTarget(alias="missing_logs"),
        )
        missing_outcome = layer.execute(missing_req, payload)
        if missing_outcome.get("result") != "blocked_by_boundary":
            failures.append("missing alias should be blocked")

        mc_req = ToolRequest(
            turn_id="turn-mc",
            source="qq_owner_private",
            intent=ToolIntent("local_inspect", 0.9, ["test"]),
            tool="log_scan",
            target=ToolTarget(alias="minecraft_server"),
        )
        mc_outcome = layer.execute(mc_req, payload)
        if mc_outcome.get("error_code") != "target_setup_required":
            failures.append("owner-setup-required alias should be blocked")

        log_req = ToolRequest(
            turn_id="turn-log",
            source="qq_owner_private",
            intent=ToolIntent("local_inspect", 0.9, ["test"]),
            tool="log_scan",
            target=ToolTarget(alias="xinyu_logs"),
        )
        log_outcome = layer.execute(log_req, payload)
        if not log_outcome.get("ok") or not Path(str(log_outcome.get("report_path"))).exists():
            failures.append("log_scan should succeed and write report")
        diagnosis = (log_outcome.get("load") or {}).get("diagnosis") if isinstance(log_outcome.get("load"), dict) else {}
        if not isinstance(diagnosis, dict) or diagnosis.get("kind") != "timeout":
            failures.append("log_scan should attach a deterministic diagnosis")

        low_frame = build_experience_frame(log_req.to_dict(), log_outcome)
        low_impulse = low_frame.get("affect_impulse", {})
        if float(low_impulse.get("fatigue_delta") or 0) > 0.05:
            failures.append("bounded success should not create large fatigue impulse")

        high_outcome = ActionOutcome.failed(
            tool="log_scan",
            target_alias="xinyu_logs",
            summary="timeout",
            error_code="timeout",
            load={"timeout": True, "error_lines": 80, "files_scanned": 8},
        ).to_dict()
        high_frame = build_experience_frame(log_req.to_dict(), high_outcome)
        if float(high_frame["affect_impulse"]["fatigue_delta"]) <= float(low_impulse.get("fatigue_delta") or 0):
            failures.append("high pressure failure should create stronger fatigue impulse")

        store = SelfChoiceStore(root)
        public_before = await store.snapshot_public(consume_cues=False)
        public_after = await store.apply_experience_impulse(low_frame)
        if "runtime_affect" in public_after or "fatigue_delta" in json.dumps(public_after, ensure_ascii=False):
            failures.append("public self choice snapshot leaked raw values")
        if not public_before or not public_after:
            failures.append("self choice public snapshots should be readable")
        log_reply = compose_action_reply(log_outcome, frame=low_frame, self_choice_public=public_after)
        if "初步判断" in log_reply or "扫到" not in log_reply or "没碰未登记目录" not in log_reply:
            failures.append("log scan reply should use natural action reply v2 wording")

        event = record_action_experience_event(root, payload, frame=high_frame, outcome=high_outcome)
        if event.get("gate_status") not in {"ok", "passed"} or int(event.get("claim_count") or 0) < 2:
            failures.append("action experience memory event should pass gate with claims")

        residue = write_action_experience_residue(root, high_frame, high_outcome, salience_threshold=0.1)
        if not residue.get("written"):
            failures.append("high salience action residue should be written")

        recent = write_recent_action_experience(root, low_frame, log_outcome)
        if not recent.get("written"):
            failures.append("recent action experience should always be written")
        recent_context = read_recent_action_context(root)
        if (
            "recent action sidecar" not in recent_context
            or "xinyu_logs" not in recent_context
            or "日志" not in recent_context
            or "请求超时" not in recent_context
        ):
            failures.append("recent action context should expose the last action for callback turns")
        if any(marker in recent_context for marker in ("log_scan:", "result=", "pressure=", "local action pressure")):
            failures.append("recent action context should not leak internal action markers")
        followup = compose_recent_action_followup(root, "所以主要问题是什么？")
        followup_reply = str((followup or {}).get("reply", ""))
        if "xinyu_logs" not in followup_reply or "请求超时" not in followup_reply:
            failures.append("recent action followup should answer with the last log diagnosis")

        reply = compose_action_reply(mc_outcome, frame=high_frame, self_choice_public=public_after)
        if "没登记" not in reply or "不乱扫" not in reply:
            failures.append("blocked target reply should state boundary naturally")

    return failures


def main() -> int:
    failures = asyncio.run(_run())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS xinyu_action_experience_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
