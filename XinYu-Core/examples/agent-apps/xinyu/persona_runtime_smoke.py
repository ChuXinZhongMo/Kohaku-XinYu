from __future__ import annotations

from pathlib import Path

from xinyu_persona_runtime import build_persona_runtime_state


def _state(text: str, *, owner: bool = True):
    return build_persona_runtime_state(
        Path(__file__).resolve().parent,
        payload={"metadata": {"is_owner_user": owner}},
        user_text=text,
        draft_reply="",
    )


def main() -> int:
    failures: list[str] = []

    style = _state("用词不像中文互联网的人说话，GPT味很重，我真的红温。")
    if style.scene != "owner_style_pressure":
        failures.append(f"style pressure scene mismatch: {style.scene}")
    if "用户" not in style.avoid or style.max_chars > 100:
        failures.append("style pressure did not enforce product-word avoidance and short reply")

    no_change = _state("怎么感觉没什么变化。")
    if no_change.scene != "owner_no_change_pressure":
        failures.append(f"no-change style pressure scene mismatch: {no_change.scene}")
    if no_change.max_chars > 80:
        failures.append("no-change style pressure did not enforce shorter reply")

    relation = _state("我们做了那么多感情系统和记忆系统，我现在真的觉得白做了。")
    if relation.scene != "owner_relationship_pressure":
        failures.append(f"relationship pressure scene mismatch: {relation.scene}")
    if "不把人设当台词" not in relation.relationship_stance:
        failures.append("relationship pressure did not reject persona-script framing")

    tech = _state("接下来怎么设计这个 Persona Runtime 的代码？")
    if tech.scene != "technical_work" or not tech.technical_request:
        failures.append("technical request was not classified as technical_work")

    daily = _state("我刚泡了碗面，水少了有点咸。")
    if daily.scene != "daily_chat":
        failures.append(f"daily chat scene mismatch: {daily.scene}")

    life_anchor = _state("广州这天气热起来了，我想喝鸭屎香柠檬茶。")
    if life_anchor.scene != "daily_chat":
        failures.append(f"life anchor scene mismatch: {life_anchor.scene}")
    if "keep stable name" not in life_anchor.chinese_voice:
        failures.append("life anchor did not preserve stable name seed")
    if "background texture is optional" not in life_anchor.chinese_voice:
        failures.append("life anchor still behaves like a required motif")
    if "live voice seed outranks long setting text" not in life_anchor.chinese_voice:
        failures.append("persona runtime did not mark live voice seed priority")

    if failures:
        print("Persona runtime smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Persona runtime smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
