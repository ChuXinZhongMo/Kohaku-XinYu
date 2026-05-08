from __future__ import annotations

from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_trust_policy import compact_command_text, is_trust_grant_command, is_trust_revoke_command


def main() -> int:
    failures: list[str] = []

    grant_text = "please trust this user"
    revoke_text = "revoke trust"
    compact_text = " Please   Trust "

    if NativeQQGateway._compact_command_text(compact_text) != compact_command_text(compact_text):
        failures.append("gateway compact command alias no longer delegates")
    if NativeQQGateway._looks_like_trust_command(grant_text) != is_trust_grant_command(grant_text):
        failures.append("gateway trust grant alias no longer delegates")
    if NativeQQGateway._looks_like_trust_revoke_command(revoke_text) != is_trust_revoke_command(revoke_text):
        failures.append("gateway trust revoke alias no longer delegates")
    if NativeQQGateway._looks_like_trust_command("ordinary chat"):
        failures.append("gateway trust grant alias matched ordinary chat")
    if NativeQQGateway._looks_like_trust_revoke_command("ordinary chat"):
        failures.append("gateway trust revoke alias matched ordinary chat")

    if failures:
        print("XinYu QQ trust aliases smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ trust aliases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
