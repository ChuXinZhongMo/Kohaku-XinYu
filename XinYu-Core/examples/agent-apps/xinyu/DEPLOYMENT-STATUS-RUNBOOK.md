# Deployment Status Runbook

Current local QQ path:

```text
NapCatQQ -> ws://127.0.0.1:6199/ws -> xinyu_qq_gateway.py -> http://127.0.0.1:8765/chat -> XinYu Core
```

AstrBot is no longer part of the runtime chain.

## Start

From `D:\XinYu`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-XinYu-QQ.ps1
```

The script starts:

- XinYu Core bridge on `127.0.0.1:8765`
- XinYu native QQ gateway on `127.0.0.1:6199`
- NapCat WebUI on `127.0.0.1:6099`

## Check

From this directory:

```powershell
.\.venv\Scripts\python.exe xinyu_status.py
.\.venv\Scripts\python.exe deployment_status_smoke.py
.\.venv\Scripts\python.exe runtime_readiness_smoke.py
```

Expected live checks:

- `core_bridge` and `core_bridge_version` are OK.
- `xinyu_qq_gateway_6199` is OK.
- `napcat_webui_6099` is OK.
- `napcat_to_xinyu_qq_gateway_ws` is OK.
- `qq_gateway_config_present`, `qq_gateway_enabled`, and `qq_gateway_whitelist` are OK.

## Config

Native QQ gateway config:

```text
xinyu_qq_gateway.config.json
```

Important defaults:

- only whitelisted owner QQ IDs are accepted for private chat
- group messages require mention or configured prefix
- the gateway only handles QQ transport and normal chat forwarding
- Codex, learning ingest, and proactive claim delivery are not auto-triggered from QQ chat by this gateway

## Troubleshooting

If NapCat shows `ECONNREFUSED 127.0.0.1:6199`, start or restart the native gateway:

```powershell
.\start_xinyu_qq_gateway.ps1
```

If `deployment_status_smoke.py` fails on Core version, restart Core:

```powershell
.\stop_xinyu_core_bridge.ps1
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
```
