# api/

FastAPI HTTP and WebSocket server for XinYu Runtime.

## Responsibility

Exposes the `serving/` layer over HTTP and WebSocket so web frontends, desktop
apps, and automation tools can drive agents and terrariums without importing
the Python package directly. This layer is intentionally thin: request routing
and serialization live here, while runtime state stays in `serving/`.

## Files

| File | Responsibility |
| --- | --- |
| `__init__.py` | Package marker |
| `app.py` | `create_app(...)` FastAPI factory, CORS, router registration, optional SPA mount |
| `main.py` | Uvicorn entrypoint (`python -m xinyu_runtime.api.main`), default port 8001 |
| `deps.py` | Singleton manager dependency |
| `schemas.py` | Pydantic request and response models |
| `events.py` | In-memory event log and `StreamOutput` |
| `routes/` | REST endpoints |
| `ws/` | WebSocket handlers |

## Runtime Paths

`deps.py` reads `XINYU_SESSION_DIR` first, then legacy `KT_SESSION_DIR`, and
defaults to `~/.xinyu/sessions`. Existing `.xinyu` session files remain
readable through the runtime's legacy fallback paths.

## See Also

- `../serving/README.md`
- `routes/README.md`
- `ws/README.md`

