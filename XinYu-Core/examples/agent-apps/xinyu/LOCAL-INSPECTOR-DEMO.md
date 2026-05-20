# XinYu Local Inspector Demo Notes

This note is for public demos and grant evidence. It shows runtime status without raw private chat text, full QQ IDs, secrets, or local file paths.

## CLI

```powershell
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network
```

Use `--json` when recording structured evidence:

```powershell
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network --json
```

The summary covers:

- current turn state and age
- latest route stage/status and route timeline
- QQ gateway configuration and coarse connection status
- proactive request and dispatch status
- memory candidate counts
- stale turn and timeout warnings

## Dashboard

```powershell
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network dashboard
```

The generated file is:

```text
runtime/local_inspector_dashboard.html
```

Open it locally for a screenshot. The dashboard embeds only the same sanitized summary as the CLI.

## Intervention API

The CLI can call the already existing bridge intervention routes:

```powershell
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene current
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene status-message
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene cancel
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene retry-lightweight --force
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene skip-sidecar --force
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene continue --force
```

If the bridge is started with a token, pass `--token` or record the status through the bridge UI instead. Do not include the token in screenshots.

## Screenshot Boundary

Before recording:

- prefer `--no-network` if the demo only needs local state
- do not show raw `memory/` files or trace files directly
- crop the terminal to the inspector output only
- verify no private message text, full QQ ID, token, or local path is visible
