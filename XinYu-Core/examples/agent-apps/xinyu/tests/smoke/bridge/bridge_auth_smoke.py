from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_auth import bridge_request_authorized


class Headers(dict[str, str]):
    def get(self, key: str, default: str = "") -> str:
        return super().get(key, default)


def main() -> int:
    failures: list[str] = []

    if not bridge_request_authorized(Headers(), ""):
        failures.append("empty token should allow loopback-style local requests")
    if not bridge_request_authorized(Headers({"Authorization": "Bearer bridge-token"}), "bridge-token"):
        failures.append("bearer token was rejected")
    if not bridge_request_authorized(Headers({"X-XinYu-Bridge-Token": "bridge-token"}), "bridge-token"):
        failures.append("xinyu bridge token header was rejected")
    if bridge_request_authorized(Headers({"Authorization": "Bearer wrong"}), "bridge-token"):
        failures.append("wrong bearer token was accepted")
    if bridge_request_authorized(Headers({"X-XinYu-Bridge-Token": "wrong"}), "bridge-token"):
        failures.append("wrong header token was accepted")
    if bridge_request_authorized(object(), "bridge-token"):
        failures.append("header object without get() was accepted")

    if failures:
        print("bridge_auth_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("bridge_auth_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
