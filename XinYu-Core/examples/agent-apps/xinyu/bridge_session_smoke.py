from __future__ import annotations

from xinyu_bridge_session import AgentSession, session_key_from_payload, session_keys_to_expire


class DummyAgent:
    pass


def _session(key: str, last_used_at: float) -> AgentSession:
    return AgentSession(key=key, agent=DummyAgent(), prompt_signature="smoke", last_used_at=last_used_at)


def main() -> int:
    failures: list[str] = []

    if session_key_from_payload({"session_id": "s1", "user_id": "u1"}) != "s1":
        failures.append("session_id should win over user_id")
    if session_key_from_payload({"user_id": "u1"}) != "u1":
        failures.append("user_id fallback changed")
    if session_key_from_payload({}) != "qq:default":
        failures.append("empty payload fallback changed")

    sessions = {
        "old": _session("old", 70.0),
        "fresh": _session("fresh", 95.0),
        "kept": _session("kept", 10.0),
    }
    expired = session_keys_to_expire(
        sessions,
        now=100.0,
        idle_ttl_seconds=20,
        max_sessions=0,
        preserve_keys={"kept"},
    )
    if expired != {"old"}:
        failures.append(f"idle expiry changed: {sorted(expired)}")

    sessions = {
        "a": _session("a", 10.0),
        "b": _session("b", 20.0),
        "c": _session("c", 30.0),
    }
    expired = session_keys_to_expire(
        sessions,
        now=100.0,
        idle_ttl_seconds=0,
        max_sessions=2,
        preserve_keys={"a"},
    )
    if expired != {"b"}:
        failures.append(f"max-session overflow changed: {sorted(expired)}")

    if failures:
        print("Bridge session smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Bridge session smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
