from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from xinyu_runtime_security import (
    bridge_source_version,
    runtime_source_paths,
    source_file_digest,
    source_files_digest,
)
from xinyu_status_collect import (
    check_core,
    check_ports,
    check_qq_gateway_config,
    check_state,
    status_fields,
)
from xinyu_status_models import (
    DEFAULT_CORE_URL,
    DEFAULT_QQ_GATEWAY_CONFIG,
    Check,
    redact_core_data,
)


def print_section(title: str) -> None:
    print(f"=== {title} ===")


def print_checks(checks: list[Check]) -> None:
    for check in checks:
        status = "OK" if check.ok else "WARN"
        print(f"{status:4} {check.name}: {check.detail}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only XinYu runtime status summary.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--qq-config", type=Path, default=DEFAULT_QQ_GATEWAY_CONFIG)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    qq_config = args.qq_config.resolve()

    expected_core_version = bridge_source_version(root / "xinyu_core_bridge.py")
    expected_core_digest = source_file_digest(root / "xinyu_core_bridge.py")
    expected_runtime_digest = source_files_digest(runtime_source_paths(root))
    core_checks, core_data = check_core(
        args.core_url,
        expected_core_version,
        expected_core_digest,
        expected_runtime_digest,
    )
    port_checks = check_ports()
    qq_gateway_checks = check_qq_gateway_config(root, qq_config)
    state_checks = check_state(root)
    fields = status_fields(root)
    all_checks = core_checks + port_checks + qq_gateway_checks + state_checks

    if args.json:
        print(
            json.dumps(
                {
                    "ok": all(check.ok for check in all_checks if check.name != "dispatch_state"),
                    "checks": [check.__dict__ for check in all_checks],
                    "core": redact_core_data(core_data),
                    "fields": fields,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if all(check.ok for check in all_checks if check.name != "dispatch_state") else 1

    print_section("XinYu Runtime")
    print_checks(core_checks)
    print_checks(port_checks)
    print_section("XinYu QQ Gateway")
    print_checks(qq_gateway_checks)
    print_section("XinYu State")
    print_checks(state_checks)
    print_section("Key Fields")
    for key, value in fields.items():
        print(f"{key}: {value}")

    hard_checks = [check for check in all_checks if check.name != "dispatch_state"]
    return 0 if all(check.ok for check in hard_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
