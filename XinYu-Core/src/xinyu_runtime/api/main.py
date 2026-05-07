"""Entry point for the XinYu Runtime HTTP API server."""

import uvicorn

from xinyu_runtime.api.app import create_app
from xinyu_runtime.serving.web import _resolve_config_dirs
from xinyu_runtime.utils.logging import configure_utf8_stdio

configure_utf8_stdio(log=True)

_creatures_dirs, _terrariums_dirs = _resolve_config_dirs()
UVICORN_APP = "xinyu_runtime.api.main:app"

app = create_app(
    creatures_dirs=_creatures_dirs,
    terrariums_dirs=_terrariums_dirs,
)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="XinYu Runtime API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Auto-reload on code changes (dev only)",
    )
    args = parser.parse_args()

    uvicorn.run(
        UVICORN_APP,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
