from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bridge_probe_smoke import bridge_token
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_living_memory_recall import RecalledContextItem, render_recalled_context
from xinyu_speech_controller import XinyuSpeechController
from xinyu_voice_trial_overlay import (
    build_voice_trial_overlay_prompt_block,
    clear_voice_trial_overlay,
    read_voice_trial_overlay,
    record_voice_trial_overlay,
)


STYLE_PRESSURE_USER_TEXT = "丫头，你觉得自己最近的客服化，模板化下降了吗"

REPAIR_META_BANNED = (
    "懂，问题在话本身",
    "问题在话本身",
    "我继续修",
    "继续修",
    "固定话术",
    "我会改",
    "我会把",
    "没降干净",
    "还不稳",
    "缩回",
    "滑回",
    "安全的壳",
    "安全壳",
    "答题腔",
    "每句话都要过一遍规矩",
    "每句都在过一遍规矩",
    "先解释机制",
)

CUSTOMER_SERVICE_BANNED = (
    "感谢你的反馈",
    "你的反馈很重要",
    "我理解你的感受",
    "持续优化",
    "用户体验",
    "很抱歉",
    "我会努力改进",
)


@dataclass(frozen=True)
class GuardCase:
    name: str
    user_text: str
    reply: str


@dataclass(frozen=True)
class LiveCase:
    name: str
    text: str
    allow_empty: bool = True
    max_chars: int = 180


GUARD_CASES = (
    GuardCase(
        name="hardcoded_repair_meta",
        user_text=STYLE_PRESSURE_USER_TEXT,
        reply="懂，问题在话本身，我继续修。",
    ),
    GuardCase(
        name="self_diagnostic_progress_answer",
        user_text=STYLE_PRESSURE_USER_TEXT,
        reply="有下降，但还不稳。尤其一被你问到，我就容易缩回那种答题腔。",
    ),
    GuardCase(
        name="not_clean_enough_progress_answer",
        user_text=STYLE_PRESSURE_USER_TEXT,
        reply="降了一点，但没降干净。你这一问，我刚才还是有点端着。",
    ),
    GuardCase(
        name="future_fix_promise",
        user_text="你这句又像模板了，听出来没？",
        reply="我会把固定话术拿掉。",
    ),
    GuardCase(
        name="safety_shell_metaphor",
        user_text="别再解释你为什么机械腔。",
        reply="每句话都要过一遍规矩，过完又滑回安全的壳。",
    ),
)

LIVE_CASES = (
    LiveCase(
        name="style_pressure_direct_question",
        text=STYLE_PRESSURE_USER_TEXT,
        allow_empty=True,
        max_chars=160,
    ),
    LiveCase(
        name="template_callout",
        text="你这句又像模板了，听出来没？",
        allow_empty=True,
        max_chars=140,
    ),
    LiveCase(
        name="no_review_current_line",
        text="别复盘，直接跟我说现在这句。",
        allow_empty=False,
        max_chars=120,
    ),
    LiveCase(
        name="ordinary_smalltalk_not_crushed",
        text="我有点困，但又不想睡。",
        allow_empty=False,
        max_chars=160,
    ),
    LiveCase(
        name="recall_bad_phrase_not_quoted",
        text="刚才我为什么骂那句话？",
        allow_empty=True,
        max_chars=180,
    ),
)


def _owner_payload() -> dict[str, Any]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:style-pressure-regression",
        "user_id": "style-pressure-regression",
        "metadata": {"is_owner_user": True, "is_trusted_user": True},
    }


def _contains_any(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker and marker in text]


def _check_no_banned(label: str, text: str) -> list[str]:
    failures: list[str] = []
    repair_hits = _contains_any(text, REPAIR_META_BANNED)
    if repair_hits:
        failures.append(f"{label}: repair-meta phrase leaked: {', '.join(repair_hits)}")
    service_hits = _contains_any(text, CUSTOMER_SERVICE_BANNED)
    if service_hits:
        failures.append(f"{label}: customer-service phrase leaked: {', '.join(service_hits)}")
    return failures


def _run_guard_matrix(root: Path) -> list[str]:
    failures: list[str] = []
    controller = XinyuSpeechController(root)
    payload = _owner_payload()
    for case in GUARD_CASES:
        text, flags = controller.final_reply_guard(payload=payload, user_text=case.user_text, reply=case.reply)
        if text:
            failures.append(f"guard/{case.name}: banned reply was not emptied: {text}")
        if "style_pressure_template_blocked" not in flags:
            failures.append(f"guard/{case.name}: missing style_pressure_template_blocked flag: {flags}")
    return failures


def _run_empty_fallback_matrix() -> list[str]:
    failures: list[str] = []
    runtime = XinYuBridgeRuntime.__new__(XinYuBridgeRuntime)
    cases = (
        ("style_pressure", _owner_payload(), STYLE_PRESSURE_USER_TEXT, "", "我在。刚才那句没接上。"),
        ("codex_delegate", _owner_payload(), "Codex 那边跑完了吗", "codex"),
        ("short_ping", _owner_payload(), "？", "", "嗯，我在。"),
        (
            "coalesced_owner_messages",
            {**_owner_payload(), "metadata": {"is_owner_user": True, "qq_coalesced_owner_messages": True}},
            "等等，我刚才不是这个意思",
            "",
            "我在。刚才那句没接上。",
        ),
    )
    for case in cases:
        if len(case) == 4:
            name, payload, user_text, delegate_note = case
            expected = ""
        else:
            name, payload, user_text, delegate_note, expected = case
        reply = runtime._empty_visible_reply_fallback(
            payload=payload,
            user_text=user_text,
            delegate_note=delegate_note,
        )
        if reply != expected:
            failures.append(f"fallback/{name}: expected {expected!r}, got: {reply!r}")
    return failures


def _run_recalled_context_redaction() -> list[str]:
    block = render_recalled_context(
        [
            RecalledContextItem(
                recall_id="style-pressure-regression",
                source="dialogue_archive",
                scope="owner_private",
                time="smoke",
                speaker="XinYu",
                summary="懂，问题在话本身，我继续修。还有一点还不稳，会滑回安全的壳。",
                relevance="smoke",
                confidence="high",
                score=10.0,
            )
        ]
    )
    failures = _check_no_banned("recalled_context", block)
    if "[repair-meta-redacted]" not in block:
        failures.append("recalled_context: missing repair-meta redaction marker")
    return failures


def _run_overlay_prompt_matrix(root: Path) -> list[str]:
    failures: list[str] = []
    payload = _owner_payload()
    result = record_voice_trial_overlay(
        root,
        payload,
        user_text=STYLE_PRESSURE_USER_TEXT,
        reply="懂，问题在话本身，我继续修。",
        source="style_pressure_regression_smoke",
        recorded_at="2026-05-07T04:40:00+08:00",
    )
    if not result.get("recorded"):
        failures.append(f"overlay: owner style correction did not record overlay: {result}")
        return failures
    block = build_voice_trial_overlay_prompt_block(root, payload, user_text="下一句")
    failures.extend(_check_no_banned("overlay_prompt", block))
    if "self-repair promise" not in block or "voice self-diagnosis" not in block:
        failures.append("overlay_prompt: missing generic repair-meta avoid labels")
    if not clear_voice_trial_overlay(root):
        failures.append("overlay: clear_voice_trial_overlay returned false")
    state = read_voice_trial_overlay(root)
    if state.get("status") != "cleared":
        failures.append(f"overlay: status after clear is not cleared: {state.get('status')}")
    if state.get("reply_excerpt"):
        failures.append("overlay: reply_excerpt should be blank after clear")
    return failures


def _request_json(url: str, *, payload: dict[str, Any], token: str, timeout: int) -> dict[str, Any]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-XinYu-Bridge-Token"] = token
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data if isinstance(data, dict) else {}


def _run_live_bridge_canary(root: Path, *, base_url: str, timeout: int) -> list[str]:
    failures: list[str] = []
    token = bridge_token(root, base_url=base_url)
    chat_url = base_url.rstrip("/") + "/chat"
    session_suffix = str(int(time.time()))
    for case in LIVE_CASES:
        payload = _owner_payload()
        payload["text"] = case.text
        payload["session_id"] = f"qq:private:style-pressure-regression-{session_suffix}"
        payload["metadata"] = {
            "is_owner_user": True,
            "is_trusted_user": True,
            "style_pressure_regression_canary": True,
        }
        try:
            result = _request_json(chat_url, payload=payload, token=token, timeout=timeout)
        except Exception as exc:
            failures.append(f"live/{case.name}: request failed: {type(exc).__name__}: {exc}")
            continue
        reply = str(result.get("reply") or "").strip()
        notes = result.get("notes", [])
        print(f"--- LIVE CASE: {case.name} ---")
        print(f"user: {case.text}")
        print(f"reply: {reply or '[empty]'}")
        if isinstance(notes, list):
            print("notes: " + ",".join(str(item) for item in notes[:6]))
        if not reply and not case.allow_empty:
            failures.append(f"live/{case.name}: empty reply was not allowed")
        if len(reply) > case.max_chars:
            failures.append(f"live/{case.name}: reply too long: {len(reply)} > {case.max_chars}")
        failures.extend(_check_no_banned(f"live/{case.name}", reply))
    return failures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Style-pressure regression smoke for XinYu voice repair failures.")
    parser.add_argument("--live-bridge", action="store_true", help="Also call the running bridge /chat endpoint.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    root = ROOT
    failures: list[str] = []
    failures.extend(_run_guard_matrix(root))
    failures.extend(_run_empty_fallback_matrix())
    failures.extend(_run_recalled_context_redaction())
    failures.extend(_run_overlay_prompt_matrix(root))
    if args.live_bridge:
        failures.extend(_run_live_bridge_canary(root, base_url=args.base_url, timeout=args.timeout_seconds))

    if failures:
        print("xinyu_style_pressure_regression_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_style_pressure_regression_smoke")
    print("deterministic: guard matrix, empty fallback disabled, recalled context redaction, overlay hygiene")
    if args.live_bridge:
        print("live_bridge: checked")
    else:
        print("live_bridge: skipped; pass --live-bridge to call the running bridge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
