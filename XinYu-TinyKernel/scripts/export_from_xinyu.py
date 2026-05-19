from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from common import CONFIG_DIR, DATA_DIR, compact_space, load_json, read_jsonl, rel_to, write_jsonl


MIN_TEXT_CHARS = 1
MAX_TEXT_CHARS = 700


def _target_reply(reply: str) -> dict[str, Any]:
    return {
        "mode": "reply",
        "reply": reply,
        "tool_request": None,
        "memory_candidates": [],
        "style": {"length": "short", "tone": "direct", "avoid": ["report_voice", "tool_leak"]},
        "confidence": 0.78,
    }


def _candidate(
    *,
    row_id: str,
    source: str,
    kind: str,
    user_text: str,
    target: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    recent_turns: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "id": row_id,
        "source": source,
        "kind": kind,
        "input": {
            "user_text": compact_space(user_text),
            "context": {
                "recent_turns": recent_turns or [],
                "persona_state": "",
                "owner_profile": "",
                "runtime_state": "",
                "memory_recall": [],
            },
            "capabilities": {
                "codex_available": True,
                "external_api_available": False,
                "local_tools_available": True,
            },
        },
        "target": target,
        "metadata": {"quality": "candidate", **(metadata or {})},
    }


def _valid_text(text: str) -> bool:
    stripped = compact_space(text)
    return MIN_TEXT_CHARS <= len(stripped) <= MAX_TEXT_CHARS


def export_dialogue_pairs(db_path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not db_path.exists():
        return rows
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        messages = con.execute(
            """
            select id, session_key_hash, scope, channel, role, text, created_at
            from dialogue_messages
            where scope = 'owner_private' and role in ('user', 'assistant')
            order by session_key_hash, id
            """
        ).fetchall()
    finally:
        con.close()

    previous_by_session: dict[str, sqlite3.Row] = {}
    recent_by_session: dict[str, list[dict[str, str]]] = {}
    for msg in messages:
        session = str(msg["session_key_hash"])
        role = str(msg["role"])
        text = compact_space(str(msg["text"]))
        previous = previous_by_session.get(session)
        if role == "assistant" and previous and previous["role"] == "user":
            user_text = compact_space(str(previous["text"]))
            if _valid_text(user_text) and _valid_text(text):
                recent_turns = recent_by_session.get(session, [])[-4:]
                rows.append(
                    _candidate(
                        row_id=f"cand-dialogue-{previous['id']}-{msg['id']}",
                        source="dialogue_archive",
                        kind="dialogue_pair",
                        user_text=user_text,
                        target=_target_reply(text),
                        metadata={
                            "user_message_id": previous["id"],
                            "assistant_message_id": msg["id"],
                            "created_at": msg["created_at"],
                            "channel": msg["channel"],
                        },
                        recent_turns=recent_turns,
                    )
                )
                if len(rows) >= limit:
                    break
            recent = recent_by_session.setdefault(session, [])
            recent.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": text}])
            recent_by_session[session] = recent[-8:]
        previous_by_session[session] = msg
    return rows


def export_memory_candidates(db_path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not db_path.exists():
        return rows
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        candidates = con.execute(
            """
            select candidate_id, created_at, candidate_type, candidate_text, confidence_score, status
            from memory_candidates
            order by id
            limit ?
            """,
            (limit,),
        ).fetchall()
    finally:
        con.close()
    for idx, row in enumerate(candidates, start=1):
        text = compact_space(str(row["candidate_text"]))
        if not _valid_text(text):
            continue
        target = {
            "mode": "memory_candidate",
            "reply": "",
            "tool_request": None,
            "memory_candidates": [
                {
                    "text": text,
                    "kind": str(row["candidate_type"]),
                    "confidence": min(0.95, max(0.1, int(row["confidence_score"] or 50) / 100)),
                }
            ],
            "style": {"length": "short", "tone": "direct", "avoid": ["report_voice", "tool_leak"]},
            "confidence": 0.72,
        }
        rows.append(
            _candidate(
                row_id=f"cand-memory-{idx:04d}",
                source="dialogue_archive",
                kind="memory_candidate",
                user_text=text,
                target=target,
                metadata={
                    "candidate_id": row["candidate_id"],
                    "created_at": row["created_at"],
                    "status": row["status"],
                },
            )
        )
    return rows


def export_regression_baselines(regression_dir: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not regression_dir.exists():
        return rows
    for path in sorted(regression_dir.glob("live_chat_baseline_*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        for result in value.get("results", []):
            if not isinstance(result, dict):
                continue
            user_text = compact_space(str(result.get("text", "")))
            reply = compact_space(str(result.get("reply", "")))
            quality = result.get("quality") if isinstance(result.get("quality"), dict) else {}
            if not _valid_text(user_text) or not _valid_text(reply):
                continue
            if quality.get("mechanic_leak") or quality.get("reportish") or quality.get("empty_reply"):
                continue
            rows.append(
                _candidate(
                    row_id=f"cand-regression-{path.stem}-{len(rows)+1:04d}",
                    source="regression_baseline",
                    kind="live_chat_baseline",
                    user_text=user_text,
                    target=_target_reply(reply),
                    metadata={
                        "case_id": result.get("case_id", ""),
                        "case_kind": result.get("case_kind", ""),
                        "baseline_file": path.name,
                    },
                )
            )
            if len(rows) >= limit:
                return rows
    return rows


def export_tool_seed_cases(seed_dir: Path) -> list[dict[str, Any]]:
    seed_rows: list[dict[str, Any]] = []
    for seed_path in sorted(seed_dir.glob("*.jsonl")):
        seed_rows.extend(read_jsonl(seed_path))
    rows: list[dict[str, Any]] = []
    for idx, seed in enumerate(seed_rows, start=1):
        text = compact_space(str(seed.get("user_text", "")))
        mode = str(seed.get("mode", "reply"))
        if not text:
            continue
        if mode == "codex_delegate":
            task = compact_space(str(seed.get("task") or text))
            target = {
                "mode": mode,
                "reply": "",
                "tool_request": {"tool": "codex_delegate", "risk": "delegated_local", "task": task},
                "memory_candidates": [],
                "style": {"length": "short", "tone": "direct", "avoid": ["report_voice", "tool_leak"]},
                "confidence": 0.9,
            }
        elif mode == "status_probe":
            task = compact_space(str(seed.get("task") or text))
            target = {
                "mode": mode,
                "reply": "",
                "tool_request": {"tool": "status_probe", "risk": "read_only", "task": task},
                "memory_candidates": [],
                "style": {"length": "short", "tone": "direct", "avoid": ["report_voice", "tool_leak"]},
                "confidence": 0.86,
            }
        elif mode == "wait":
            target = {**_target_reply("[WAITING]"), "mode": "wait", "confidence": 0.88}
        elif mode == "local_only_limitation":
            target = {
                **_target_reply("复杂部分需要外部模型。我现在能先做本地检查和记忆整理，等 API 恢复后再继续。"),
                "mode": "local_only_limitation",
                "confidence": 0.82,
            }
        elif mode == "memory_candidate":
            memory_text = compact_space(str(seed.get("memory_text") or text))
            target = {
                **_target_reply("这个先作为候选记下来，后面多轮确认后再固化。"),
                "mode": "memory_candidate",
                "memory_candidates": [{"text": memory_text, "kind": "owner_goal_or_preference", "confidence": 0.86}],
                "confidence": 0.84,
            }
        elif mode == "clarify":
            target = {**_target_reply(compact_space(str(seed.get("reply") or "你再说具体一点。"))), "mode": "clarify", "confidence": 0.82}
        else:
            target = _target_reply(compact_space(str(seed.get("reply") or "嗯。")))
        rows.append(
            _candidate(
                row_id=str(seed.get("id") or f"cand-seed-{idx:04d}"),
                source="manual_seed",
                kind="tool_route_seed",
                user_text=text,
                target=target,
                metadata={"quality": "seed"},
            )
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_DIR / "data_sources.json"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--out", default=str(DATA_DIR / "candidates" / "candidates_v0.jsonl"))
    args = parser.parse_args()

    config = load_json(Path(args.config))
    xinyu_root = Path(config["xinyu_root"])
    dialogue_path = rel_to(xinyu_root, config["allowed_sources"]["dialogue_archive"]["path"])
    regression_dir = rel_to(xinyu_root, config["allowed_sources"]["regression_baselines"]["path"])

    rows: list[dict[str, Any]] = []
    rows.extend(export_dialogue_pairs(dialogue_path, limit=args.limit))
    rows.extend(export_memory_candidates(dialogue_path, limit=120))
    rows.extend(export_regression_baselines(regression_dir, limit=120))
    rows.extend(export_tool_seed_cases(DATA_DIR / "manual_seed"))

    count = write_jsonl(Path(args.out), rows)
    print(f"wrote {count} candidates to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
