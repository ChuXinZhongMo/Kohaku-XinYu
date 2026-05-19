from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_payload_policy import owner_private_payload_matches, trusted_private_payload_matches
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    owner_private = {"message_type": "private_text", "metadata": {"is_owner_user": True}}
    owner_group = {"message_type": "group_text", "group_id": "7", "metadata": {"is_owner_user": True}}
    owner_desktop = {"message_type": "desktop_private", "metadata": {"is_owner_user": True}}
    trusted_private = {"message_type": "private_text", "metadata": {"is_trusted_user": True}}
    trusted_group = {"message_type": "group_text", "group_id": "7", "metadata": {"is_trusted_user": True}}
    trusted_owner = {"message_type": "private_text", "metadata": {"is_owner_user": True, "is_trusted_user": True}}
    trusted_none_group = {"message_type": "", "group_id": "None", "metadata": {"is_trusted_user": True}}
    trusted_upper_none_group = {"message_type": "", "group_id": "NONE", "metadata": {"is_trusted_user": True}}

    if not owner_private_payload_matches(owner_private):
        failures.append("owner private payload no longer matches")
    if owner_private_payload_matches(owner_group):
        failures.append("owner group payload matched owner private")
    if not owner_private_payload_matches(owner_desktop):
        failures.append("owner desktop payload without group no longer matches")
    if owner_private_payload_matches({"message_type": "private_text", "metadata": "owner"}):
        failures.append("non-dict owner metadata matched")

    if not trusted_private_payload_matches(trusted_private):
        failures.append("trusted private payload no longer matches")
    if trusted_private_payload_matches(trusted_group):
        failures.append("trusted group payload matched trusted private")
    if trusted_private_payload_matches(trusted_owner):
        failures.append("owner payload matched trusted private")
    if not trusted_private_payload_matches(trusted_none_group):
        failures.append("trusted None group compatibility changed")
    if trusted_private_payload_matches(trusted_upper_none_group):
        failures.append("trusted uppercase NONE group compatibility changed")

    if XinYuBridgeRuntime._owner_private_payload_matches(owner_private) is not True:
        failures.append("core bridge owner private alias no longer delegates")
    if XinYuBridgeRuntime._trusted_private_payload_matches(trusted_private) is not True:
        failures.append("core bridge trusted private alias no longer delegates")

    if failures:
        print("XinYu bridge payload policy smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge payload policy smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
