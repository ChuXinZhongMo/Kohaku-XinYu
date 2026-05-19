from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

import json
from tempfile import TemporaryDirectory
from pathlib import Path

from xinyu_qq_config import GatewayConfig
from xinyu_qq_gateway import NativeQQGateway


def main() -> int:
    failures: list[str] = []

    with TemporaryDirectory() as raw_root:
        root = Path(raw_root)
        config_path = root / "xinyu_qq_gateway.config.json"
        spool_path = root / "gateway_ack_spool.jsonl"
        config_path.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "owner_user_ids": ["42"],
                    "trusted_user_ids": ["old"],
                    "custom_key": "keep",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        gateway = NativeQQGateway(
            GatewayConfig(owner_user_ids=frozenset({"42"}), gateway_ack_spool_path=str(spool_path)),
            config_path=config_path,
        )
        if not gateway._persist_trusted_user_ids({"7", "42"}):
            failures.append("trusted user config persistence returned false")
        persisted = json.loads(config_path.read_text(encoding="utf-8-sig"))
        if persisted.get("trusted_user_ids") != ["42", "7"]:
            failures.append(f"trusted user ids were not sorted/persisted: {persisted.get('trusted_user_ids')}")
        if persisted.get("custom_key") != "keep":
            failures.append("trusted user config persistence dropped unrelated keys")
        if list(root.glob("*.tmp")):
            failures.append("trusted user config persistence left temp files behind")

    if failures:
        print("XinYu QQ trust config persistence smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ trust config persistence smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
