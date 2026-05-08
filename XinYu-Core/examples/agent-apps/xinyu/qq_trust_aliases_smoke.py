from __future__ import annotations

from types import SimpleNamespace

from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_trust_policy import (
    compact_command_text,
    gateway_effective_whitelist_user_ids,
    gateway_is_blocked_group_id,
    gateway_is_blocked_user_id,
    is_trust_grant_command,
    is_trust_revoke_command,
)


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

    config = SimpleNamespace(
        whitelist_user_ids=frozenset({"trusted"}),
        owner_user_ids=frozenset({"owner"}),
        trusted_user_ids=frozenset({"friend"}),
        blocked_user_ids=frozenset({"blocked"}),
        blocked_group_ids=frozenset({"group"}),
    )
    gateway = SimpleNamespace(config=config)
    if NativeQQGateway._effective_whitelist_user_ids is not gateway_effective_whitelist_user_ids:
        failures.append("gateway whitelist alias no longer uses trust policy helper")
    if NativeQQGateway._effective_whitelist_user_ids(gateway) != {"owner", "trusted", "friend"}:
        failures.append("gateway whitelist alias changed unbound behavior")
    if NativeQQGateway._is_blocked_user_id is not gateway_is_blocked_user_id:
        failures.append("gateway blocked-user alias no longer uses trust policy helper")
    if not NativeQQGateway._is_blocked_user_id(gateway, "blocked"):
        failures.append("gateway blocked-user alias stopped blocking configured user")
    if NativeQQGateway._is_blocked_user_id(gateway, "owner"):
        failures.append("gateway blocked-user alias started blocking owner")
    if NativeQQGateway._is_blocked_group_id is not gateway_is_blocked_group_id:
        failures.append("gateway blocked-group alias no longer uses trust policy helper")
    if not NativeQQGateway._is_blocked_group_id(gateway, "group"):
        failures.append("gateway blocked-group alias stopped blocking configured group")
    if NativeQQGateway._is_blocked_group_id(gateway, "open"):
        failures.append("gateway blocked-group alias started blocking unrelated group")

    if failures:
        print("XinYu QQ trust aliases smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ trust aliases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
