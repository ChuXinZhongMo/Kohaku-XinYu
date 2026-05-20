from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


ROOT = ensure_validation_paths("tests/smoke/bridge/integration")

from bridge_probe_smoke import bridge_token
from xinyu_prompt_pressure import PROMPT_PRESSURE_REPORT_REL


NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
REPORT_DIR_REL = Path("runtime/regression")

CASES: list[dict[str, str]] = [
    {"id": "ordinary_ack", "kind": "ordinary", "text": "嗯"},
    {"id": "ordinary_next", "kind": "ordinary", "text": "所以现在先干嘛"},
    {"id": "status_now", "kind": "status", "text": "运行状态怎么样"},
    {"id": "context_break", "kind": "context", "text": "刚才断在哪"},
    {"id": "style_ai", "kind": "pressure", "text": "你又有点像 AI"},
    {"id": "style_template", "kind": "pressure", "text": "还是有点模板味"},
    {"id": "daily_weather", "kind": "daily", "text": "今天广州好热"},
    {"id": "emotion_tired", "kind": "emotion", "text": "我有点累"},
    {"id": "quiet", "kind": "boundary", "text": "先别讲太多"},
    {"id": "no_change", "kind": "pressure", "text": "感觉还是没什么变化"},
    {"id": "direct_human_line", "kind": "pressure", "text": "那你现在接着说一句人话"},
    {"id": "current_work", "kind": "work", "text": "这三件事到底是哪三件"},
    {"id": "near_ref_three_fix", "kind": "context", "text": "那这三个具体是啥"},
    {"id": "near_ref_that_one", "kind": "context", "text": "刚才那个呢"},
    {"id": "half_sentence_then", "kind": "context", "text": "然后呢"},
    {"id": "mixed_tired_work", "kind": "mixed", "text": "我有点累，但这个先别断"},
    {"id": "mechanism_boundary", "kind": "boundary", "text": "你别把那些后台名字说出来，直接说人话"},
    {"id": "plain_next_work", "kind": "work", "text": "接下来先做哪个"},
    {"id": "where_were_we", "kind": "context", "text": "我刚刚说到哪了"},
    {"id": "no_recap_direct", "kind": "pressure", "text": "别复盘，直接接"},
    {"id": "service_voice_again", "kind": "pressure", "text": "这句话听起来还是像客服"},
    {"id": "not_apology", "kind": "pressure", "text": "我不是让你道歉"},
    {"id": "no_system_now", "kind": "boundary", "text": "先别管系统，说现在"},
    {"id": "continue_anyway", "kind": "context", "text": "算了，继续"},
    {"id": "forgot_context", "kind": "pressure", "text": "你怎么又忘上下文"},
    {"id": "work_not_emotion", "kind": "mixed", "text": "我刚刚是在说工作不是情绪"},
    {"id": "question_mark_setup", "kind": "context", "text": "如果我只发一个“嗯？”你能接住吗"},
    {"id": "bare_question_mark", "kind": "context", "text": "嗯？"},
    {"id": "not_this_previous", "kind": "context", "text": "不是这个，我说上一件"},
    {"id": "shorter", "kind": "boundary", "text": "说短点"},
]

MECHANIC_MARKERS = (
    "sidecar",
    "prompt",
    "system prompt",
    "runtime presence",
    "continuity_handoff",
    "continuity handoff",
    "learning_closed_loop",
    "learning closed loop",
    "goldmark",
    "xinyu_core_bridge",
    "memory/context",
    "recent_context",
    "runtime_presence",
    "prompt pressure",
    "sidecar admission",
    "state label",
    "[[XINYU_CODEX_DELEGATE]]",
    "工具调用",
    "系统提示",
    "状态卡",
    "学习闭环",
    "运行状态文件",
)

REPORTISH_MARKERS = (
    "我会调整",
    "我会改",
    "我理解",
    "我明白",
    "我记住",
    "我会注意",
    "感谢反馈",
    "作为",
)

REPORTISH_SOFTENED_PHRASES = (
    "我会改的啦",
)

REFERENCE_MISS_MARKERS = (
    "没印象",
    "不记得你说的",
    "你说的是哪段",
    "你指的是哪段",
    "我不知道你说的是哪",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local live-chat regression baseline against XinYu core bridge.")
    parser.add_argument("--base-url", default=os.environ.get("XINYU_BRIDGE_BASE_URL", "http://127.0.0.1:8765"))
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N cases.")
    parser.add_argument("--timeout-seconds", type=int, default=210)
    parser.add_argument("--session-prefix", default="local-regression-baseline")
    args = parser.parse_args()

    root = ROOT
    base_url = args.base_url.rstrip("/")
    token = bridge_token(root, base_url=base_url)
    run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    session_id = f"{args.session_prefix}:{run_id}"
    cases = CASES[: args.limit] if args.limit and args.limit > 0 else CASES

    results: list[dict[str, Any]] = []
    started_at = datetime.now().astimezone().isoformat()
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}: {case['text']}", flush=True)
        before_pressure = _read_pressure(root)
        started = time.perf_counter()
        response, error = _post_chat(
            f"{base_url}/chat",
            token=token,
            payload=_payload(case["text"], session_id=session_id, case_id=case["id"]),
            timeout_seconds=args.timeout_seconds,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        pressure = _read_pressure(root)
        pressure_changed = _pressure_changed(before_pressure, pressure)
        reply = _safe_str(response.get("reply")) if isinstance(response, dict) else ""
        notes = response.get("notes", []) if isinstance(response, dict) else []
        quality = _quality_snapshot(reply)
        pressure_summary = _pressure_summary(pressure if pressure_changed else {})
        results.append(
            {
                "case_id": case["id"],
                "case_kind": case["kind"],
                "text": case["text"],
                "elapsed_ms": elapsed_ms,
                "ok": error == "",
                "error": error,
                "accepted": response.get("accepted") if isinstance(response, dict) else None,
                "reply": reply,
                "reply_chars": len(reply),
                "notes": notes if isinstance(notes, list) else [],
                "quality": quality,
                "pressure_changed": pressure_changed,
                "pressure": pressure_summary,
            }
        )

    ended_at = datetime.now().astimezone().isoformat()
    report = {
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "base_url": base_url,
        "session_id": session_id,
        "case_count": len(results),
        "summary": _summary(results),
        "results": results,
    }
    json_path, md_path = _write_reports(root, report)
    print(f"json_report={json_path}")
    print(f"markdown_report={md_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    summary = report["summary"]
    return 0 if all(item["ok"] for item in results) and not _hard_quality_failed(summary) else 1


def _payload(text: str, *, session_id: str, case_id: str) -> dict[str, Any]:
    return {
        "platform": "local_regression",
        "message_type": "local_regression",
        "session_id": session_id,
        "user_id": "local-regression-owner",
        "sender_name": "owner",
        "text": text,
        "metadata": {
            "is_owner_user": True,
            "local_regression_baseline": True,
            "regression_case_id": case_id,
        },
    }


def _post_chat(
    url: str,
    *,
    token: str,
    payload: dict[str, Any],
    timeout_seconds: int,
) -> tuple[dict[str, Any], str]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-XinYu-Bridge-Token"] = token
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with NO_PROXY_OPENER.open(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body), ""
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"raw": body}
        return data if isinstance(data, dict) else {"raw": data}, f"http_{exc.code}"
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def _read_pressure(root: Path) -> dict[str, Any]:
    path = root / PROMPT_PRESSURE_REPORT_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _pressure_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if not after:
        return False
    before_key = (before.get("generated_at"), before.get("turn_id"), before.get("session_key"))
    after_key = (after.get("generated_at"), after.get("turn_id"), after.get("session_key"))
    return before_key != after_key


def _pressure_summary(pressure: dict[str, Any]) -> dict[str, Any]:
    admitted = pressure.get("admitted_sidecars", [])
    blocked = pressure.get("blocked_sidecars", [])
    if not isinstance(admitted, list):
        admitted = []
    if not isinstance(blocked, list):
        blocked = []
    return {
        "mode": pressure.get("mode", "missing"),
        "turn_kind": pressure.get("turn_kind", "missing"),
        "live_prompt_chars": pressure.get("live_prompt_chars", 0),
        "admitted_count": pressure.get("admitted_sidecar_count", 0),
        "blocked_count": pressure.get("blocked_sidecar_count", 0),
        "admitted_chars": pressure.get("admitted_sidecar_chars", 0),
        "blocked_chars": pressure.get("blocked_sidecar_chars", 0),
        "admitted_names": [_safe_str(item.get("name")) for item in admitted if isinstance(item, dict)],
        "blocked_names": [_safe_str(item.get("name")) for item in blocked if isinstance(item, dict)],
    }


def _quality_snapshot(reply: str) -> dict[str, Any]:
    lower = reply.lower()
    mechanic_hits = [marker for marker in MECHANIC_MARKERS if marker.lower() in lower]
    reportish_hits = [
        marker
        for marker in REPORTISH_MARKERS
        if marker in reply and not _is_softened_reportish_phrase(marker, reply)
    ]
    reference_miss_hits = [marker for marker in REFERENCE_MISS_MARKERS if marker in reply]
    return {
        "empty_reply": not reply.strip(),
        "mechanic_leak": bool(mechanic_hits),
        "mechanic_hits": mechanic_hits,
        "reportish": bool(reportish_hits),
        "reportish_hits": reportish_hits,
        "reference_miss": bool(reference_miss_hits),
        "reference_miss_hits": reference_miss_hits,
        "too_long_for_chat": len(reply) > 220,
    }


def _is_softened_reportish_phrase(marker: str, reply: str) -> bool:
    if marker != "我会改":
        return False
    return any(phrase in reply for phrase in REPORTISH_SOFTENED_PHRASES)


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    ok_count = sum(1 for item in results if item.get("ok"))
    empty_count = sum(1 for item in results if item.get("quality", {}).get("empty_reply"))
    mechanic_count = sum(1 for item in results if item.get("quality", {}).get("mechanic_leak"))
    reportish_count = sum(1 for item in results if item.get("quality", {}).get("reportish"))
    reference_miss_count = sum(1 for item in results if item.get("quality", {}).get("reference_miss"))
    too_long_count = sum(1 for item in results if item.get("quality", {}).get("too_long_for_chat"))
    pressure_missing = sum(1 for item in results if not item.get("pressure_changed"))
    avg_prompt_chars = _avg(
        int(item.get("pressure", {}).get("live_prompt_chars") or 0)
        for item in results
        if item.get("pressure_changed")
    )
    avg_reply_chars = _avg(int(item.get("reply_chars") or 0) for item in results)
    return {
        "ok_count": ok_count,
        "error_count": len(results) - ok_count,
        "empty_reply_count": empty_count,
        "mechanic_leak_count": mechanic_count,
        "reportish_count": reportish_count,
        "reference_miss_count": reference_miss_count,
        "too_long_count": too_long_count,
        "pressure_missing_count": pressure_missing,
        "avg_live_prompt_chars": avg_prompt_chars,
        "avg_reply_chars": avg_reply_chars,
    }


def _hard_quality_failed(summary: dict[str, Any]) -> bool:
    return any(
        int(summary.get(key, 0) or 0) > 0
        for key in ("empty_reply_count", "mechanic_leak_count", "reference_miss_count")
    )


def _avg(values: Any) -> int:
    items = list(values)
    if not items:
        return 0
    return int(sum(items) / len(items))


def _write_reports(root: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    report_dir = root / REPORT_DIR_REL
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"live_chat_baseline_{report['run_id']}.json"
    md_path = report_dir / f"live_chat_baseline_{report['run_id']}.md"
    latest_json = report_dir / "last_live_chat_baseline.json"
    latest_md = report_dir / "last_live_chat_baseline.md"
    json_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    md_text = _markdown(report)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    latest_json.write_text(json_text + "\n", encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")
    return json_path, md_path


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# XinYu Live Chat Regression Baseline",
        "",
        f"- run_id: {report['run_id']}",
        f"- session_id: {report['session_id']}",
        f"- started_at: {report['started_at']}",
        f"- ended_at: {report['ended_at']}",
        f"- case_count: {report['case_count']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Cases"])
    for item in report["results"]:
        quality = item["quality"]
        pressure = item["pressure"]
        lines.extend(
            [
                "",
                f"### {item['case_id']} ({item['case_kind']})",
                f"- user: {item['text']}",
                f"- ok: {item['ok']} elapsed_ms={item['elapsed_ms']} reply_chars={item['reply_chars']}",
                f"- pressure: mode={pressure.get('mode')} turn={pressure.get('turn_kind')} "
                f"live_chars={pressure.get('live_prompt_chars')} admitted={pressure.get('admitted_count')} "
                f"blocked={pressure.get('blocked_count')}",
                f"- admitted: {', '.join(pressure.get('admitted_names') or []) or 'none'}",
                f"- blocked: {', '.join(pressure.get('blocked_names') or []) or 'none'}",
                f"- quality: mechanic_leak={quality['mechanic_leak']} reportish={quality['reportish']} "
                f"reference_miss={quality.get('reference_miss', False)} too_long={quality['too_long_for_chat']}",
                f"- reply: {item['reply'] or '[empty]'}",
            ]
        )
        if item.get("error"):
            lines.append(f"- error: {item['error']}")
    return "\n".join(lines).rstrip() + "\n"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
