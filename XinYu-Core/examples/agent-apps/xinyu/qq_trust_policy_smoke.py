from __future__ import annotations

from types import SimpleNamespace

import xinyu_qq_trust_policy as trust_policy


def main() -> int:
    failures: list[str] = []

    if not trust_policy.is_trust_grant_command("给她搜索权限"):
        failures.append("grant marker should match compact Chinese command text")
    if not trust_policy.is_trust_grant_command("please trust this user"):
        failures.append("grant marker should match English command text")
    if trust_policy.is_trust_grant_command("只是普通聊天"):
        failures.append("grant marker matched unrelated text")
    if not trust_policy.is_trust_revoke_command("取消信任"):
        failures.append("revoke marker should match Chinese command text")
    if not trust_policy.is_trust_revoke_command("revoke trust"):
        failures.append("revoke marker should match English command text")
    if trust_policy.is_trust_revoke_command("信任这个人"):
        failures.append("revoke marker matched grant text")

    config = SimpleNamespace(
        whitelist_user_ids=frozenset({"trusted"}),
        owner_user_ids=frozenset({"owner"}),
        trusted_user_ids=frozenset({"friend"}),
        blocked_user_ids=frozenset({"blocked"}),
        blocked_group_ids=frozenset({"group"}),
        group_shadow_allowed_group_ids=frozenset({"shadow"}),
    )
    if trust_policy.effective_whitelist_user_ids(config) != {"owner", "trusted", "friend"}:
        failures.append("effective whitelist union changed")
    if not trust_policy.is_blocked_user_id(config, "blocked"):
        failures.append("blocked non-owner user should be blocked")
    if trust_policy.is_blocked_user_id(config, "owner"):
        failures.append("owner user should not be blocked by blocked_user_ids")
    if trust_policy.trust_level_for_user_id(config, "friend") != "trusted":
        failures.append("trusted user level changed")
    if not trust_policy.group_shadow_group_allowed(config, "shadow"):
        failures.append("group shadow allow-list check changed")

    if failures:
        print("XinYu QQ trust policy smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ trust policy smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
