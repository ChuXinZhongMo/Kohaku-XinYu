from __future__ import annotations

from xinyu_life_reply_policy import apply_life_reply_policy, build_life_reply_policy, build_life_reply_prompt_block


def main() -> int:
    failures: list[str] = []

    tired_policy = build_life_reply_policy(
        self_choice_public={"affect_band": {"fatigue": "tired", "closure": "guarded", "urge": "warm"}},
        entropy_state={"entropy_level": 0.12, "entropy_band": "clear"},
        user_text="有点累，陪我聊聊",
    )
    if tired_policy.get("mode") != "low_energy":
        failures.append(f"tired policy mode mismatch: {tired_policy}")
    if not tired_policy.get("suppress_optional_question"):
        failures.append(f"tired policy should suppress optional question: {tired_policy}")

    reply = "嗯，我在。今天先别把话说得太满。慢一点也行。要不要我继续陪你拆这个问题？"
    shaped = apply_life_reply_policy(reply, policy=tired_policy, user_text="有点累，陪我聊聊")
    shaped_reply = str(shaped.get("reply") or "")
    if "要不要" in shaped_reply:
        failures.append(f"optional question not removed: {shaped}")
    if shaped_reply.count("。") > 2:
        failures.append(f"low energy reply not shortened enough: {shaped}")

    technical_policy = build_life_reply_policy(
        self_choice_public={"affect_band": {"fatigue": "tired", "closure": "guarded", "urge": "warm"}},
        entropy_state={"entropy_level": 0.8, "entropy_band": "fracture"},
        user_text="这个 Core Bridge 报错怎么修？",
    )
    if not technical_policy.get("technical_turn"):
        failures.append(f"technical turn not detected: {technical_policy}")
    tech_reply = "先看 token。然后看端口。再看日志。最后重启。要不要我继续？"
    tech_shaped = apply_life_reply_policy(tech_reply, policy=technical_policy, user_text="这个 Core Bridge 报错怎么修？")
    if "先看 token" not in str(tech_shaped.get("reply")):
        failures.append(f"technical facts were lost: {tech_shaped}")
    if "要不要" in str(tech_shaped.get("reply")):
        failures.append(f"technical optional tail not removed: {tech_shaped}")

    block = build_life_reply_prompt_block(tired_policy)
    if "life reply policy sidecar" not in block or "low_energy" not in block:
        failures.append(f"prompt block missing policy facts: {block}")

    if failures:
        print("xinyu_life_reply_policy_smoke FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("xinyu_life_reply_policy_smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
