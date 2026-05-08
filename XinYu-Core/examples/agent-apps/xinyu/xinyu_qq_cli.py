from __future__ import annotations

import argparse
from pathlib import Path


def build_gateway_parser(default_config_path: Path | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Native XinYu QQ gateway for NapCat OneBot reverse WebSocket.")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path or Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json"),
    )
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--path", default="")
    parser.add_argument("--core-url", default="")
    parser.add_argument("--bridge-token", default=None)
    return parser
