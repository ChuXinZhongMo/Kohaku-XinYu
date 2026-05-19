from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_persona_state import build_persona_prompt_block, observe_persona_turn


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        payload = {
            "message_type": "private_text",
            "session_id": "owner-private",
            "user_id": "owner-1",
            "message_id": "dream-1",
            "metadata": {"is_owner_user": True},
        }
        text = (
            "我久违的做梦了，我梦见我将心玉的人格做出来了。"
            "不仅做出来，还拥有了仿生人的实体，能主动识别环境，"
            "眼中出现分析框，选择自己要进行的节点反应。"
            "使用很恍惚啊，真能实现吗。"
        )

        result = observe_persona_turn(root, payload, text=text)
        if not result["state_changed"]:
            failures.append("owner dream turn did not update persona state")
        if not result["event_recorded"]:
            failures.append("owner dream turn did not record relationship event")
        for tag in ("rare_dream", "xinyu_persona", "embodiment", "feasibility_doubt"):
            if tag not in result["tags"]:
                failures.append(f"missing detected tag: {tag}")

        state = _read_json(root / "runtime/persona_state.json")
        if state["xinyu"]["reply_posture"] != "treat_rare_dream_as_relationship_memory_then_answer_feasibility":
            failures.append("persona reply posture did not switch to dream/feasibility mode")
        if "owner_dreamed_xinyu_persona_and_embodiment" not in state["owner"]["active_themes"]:
            failures.append("owner active themes missed dream/persona/embodiment event")

        events = _read_jsonl(root / "memory/relationships/owner_recent_events.jsonl")
        if len(events) != 1:
            failures.append(f"expected one relationship event, got {len(events)}")
        else:
            event = events[0]
            if event["stable_write_permission"] != "blocked_without_review":
                failures.append("relationship event did not keep stable write blocked")
            if event["salience"] < 80:
                failures.append(f"relationship event salience too low: {event['salience']}")

        mirror = (root / "memory/relationships/owner_recent_events.md").read_text(encoding="utf-8")
        if "Owner Recent Relationship Events" not in mirror or "android-like embodied form" not in mirror:
            failures.append("relationship event markdown mirror is incomplete")

        duplicate = observe_persona_turn(root, payload, text=text)
        duplicate_events = _read_jsonl(root / "memory/relationships/owner_recent_events.jsonl")
        if duplicate["event_recorded"]:
            failures.append("duplicate message recorded a second relationship event")
        if len(duplicate_events) != 1:
            failures.append("duplicate message changed relationship event count")

        group_payload = {
            "message_type": "group_text",
            "session_id": "group-session",
            "user_id": "owner-1",
            "group_id": "group-1",
            "message_id": "dream-group",
            "metadata": {"is_owner_user": True},
        }
        group_result = observe_persona_turn(root, group_payload, text=text)
        if group_result["event_recorded"]:
            failures.append("group context wrote owner relationship event")

        block = build_persona_prompt_block(root, current_tags=tuple(result["tags"]), current_salience=result["salience"])
        if "Current Reply Guidance" not in block or "answer the feeling first" not in block:
            failures.append("persona prompt block missed current reply guidance")

    if failures:
        print("Persona state flow smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Persona state flow smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
