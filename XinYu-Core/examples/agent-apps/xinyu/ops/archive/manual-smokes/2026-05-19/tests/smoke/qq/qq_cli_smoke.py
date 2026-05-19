from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from pathlib import Path

from xinyu_qq_cli import build_gateway_parser


def main() -> int:
    failures: list[str] = []
    default_config = Path("custom_gateway.json")
    parser = build_gateway_parser(default_config)
    defaults = parser.parse_args([])
    if defaults.config != default_config or defaults.port != 0 or defaults.bridge_token is not None:
        failures.append("gateway parser defaults changed")

    args = parser.parse_args(
        [
            "--config",
            "runtime_gateway.json",
            "--host",
            "127.0.0.1",
            "--port",
            "6200",
            "--path",
            "/onebot",
            "--core-url",
            "http://127.0.0.1:8765/chat",
            "--bridge-token",
            "token-smoke",
        ]
    )
    if args.config != Path("runtime_gateway.json"):
        failures.append("config argument changed")
    if args.host != "127.0.0.1" or args.port != 6200 or args.path != "/onebot":
        failures.append("onebot override arguments changed")
    if args.core_url != "http://127.0.0.1:8765/chat" or args.bridge_token != "token-smoke":
        failures.append("core bridge override arguments changed")

    if failures:
        print("QQ CLI smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ CLI smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

