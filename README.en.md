# Kohaku-XinYu

<p align="center">
  <img src="images/xinyu-repository-banner.jpg" alt="XinYu repository banner" width="100%">
</p>

<p align="center">
  <strong>A long-running personal AI companion system for memory, relationships, emotional trajectory, learning, self-checks, and controlled proactivity.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-local_runtime_active-2f855a" alt="Local runtime active">
  <img src="https://img.shields.io/badge/QQ-NapCat%20%2B%20native%20gateway-2563eb" alt="NapCat native gateway">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/privacy-runtime_files_ignored-6b7280" alt="Runtime files ignored">
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README.zh.md">繁體中文</a> · <strong>English</strong> · <a href="README.ja.md">日本語</a>
</p>

---

## Repository Notice

This repository now presents **XinYu** as the main project, rather than a general KohakuTerrarium framework repository. KohakuTerrarium remains the underlying runtime framework snapshot; XinYu is the long-running AI system built on top of it.

The public repository includes:

- XinYu core app, prompts, writers, bridge, status checks, and smoke tests
- Native QQ gateway: `NapCatQQ -> xinyu_qq_gateway.py -> xinyu_core_bridge.py`
- v1 core refactor skeleton: routing, memory, emotion, response, gateway, observability, and storage modules
- Portable seed memory, learning material pipeline, memory event sourcing, persona stability checks, and safety boundary checks
- Deployment and validation documentation

The public repository does not include:

- Local QQ account configuration
- Runtime memory, logs, or runtime traces
- Private chats, private learning materials, real tokens, or local environment files

The old AstrBot integration path has been removed from the active runtime. The current local QQ path uses the native `xinyu_qq_gateway.py` included in this repository.

## Current Runtime Chain

```text
NapCatQQ
  -> ws://127.0.0.1:6199/ws
  -> examples/agent-apps/xinyu/xinyu_qq_gateway.py
  -> http://127.0.0.1:8765/chat
  -> examples/agent-apps/xinyu/xinyu_core_bridge.py
  -> XinYu Kohaku agent runtime
```

This chain separates the transport shell from the persona core:

| Layer | Responsibility |
| --- | --- |
| NapCatQQ | QQ client and OneBot event source |
| `xinyu_qq_gateway.py` | Whitelist, group triggers, message normalization, forwarding to Core |
| `xinyu_core_bridge.py` | HTTP bridge, sessions, learning entry points, proactive candidates, maintenance tasks |
| Kohaku runtime | XinYu prompts, writers, plugin lifecycle, and behavior execution |
| Memory / learning layers | Long-term memory, seed memory, learning materials, event records, and quality gates |

Architecture diagram: [`XINYU-ARCHITECTURE-DIAGRAM.svg`](examples/agent-apps/xinyu/XINYU-ARCHITECTURE-DIAGRAM.svg)

## Project Status

Implemented and tracked in this repository:

- Local XinYu Core bridge with `/health`, `/probe`, `/chat`, `/proactive`, `/proactive/ack`, learning, and Codex delegation endpoints
- Native QQ gateway with whitelist, private chat, group trigger prefix, timeout control, and OneBot sending
- Controlled state machine for proactive message candidates, claim, and ack
- Structured persona, relationship, emotion, reflection, dream, archive, learning, and context layers
- Memory event sourcing, seed memory packaging and sync, persona state, and life-month slots
- Smoke guards for dialogue curiosity, visible voice, Chinese expression, persona stability, runtime safety, and deployment readiness
- v1 refactor skeleton covering gateway, routing, memory, emotion, response, autonomy, observability, and storage

Still treated as local runtime state:

- Real model keys and `xinyu.local.env`
- `xinyu_qq_gateway.config.json`
- `logs/`, `memory/`, `runtime/`
- `learning/self_found/` and `learning/owner_supplied/`

These paths are ignored by Git by default.

## Quick Start

Enter the XinYu app directory:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

Create a local environment file:

```powershell
copy xinyu.local.env.example xinyu.local.env
```

Fill in at least:

```text
XINYU_API_KEY=
XINYU_BASE_URL=
XINYU_LLM_MODEL=
```

Install minimal dependencies:

```powershell
python -m pip install -r requirements-minimal.txt
```

Start the Core bridge:

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
```

Start the native QQ gateway:

```powershell
.\start_xinyu_qq_gateway.ps1
```

See [`DEPLOYMENT-STATUS-RUNBOOK.md`](examples/agent-apps/xinyu/DEPLOYMENT-STATUS-RUNBOOK.md) for more deployment steps.

## Status Check

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python xinyu_status.py
python deployment_status_smoke.py
python runtime_readiness_smoke.py
```

Machine-readable status:

```powershell
python xinyu_status.py --json
```

## Privacy Boundary

Do not upload these paths to the public repository:

```text
examples/agent-apps/xinyu/xinyu.local.env
examples/agent-apps/xinyu/xinyu_qq_gateway.config.json
examples/agent-apps/xinyu/logs/
examples/agent-apps/xinyu/memory/
examples/agent-apps/xinyu/runtime/
examples/agent-apps/xinyu/learning/self_found/
examples/agent-apps/xinyu/learning/owner_supplied/
```

The public repository keeps reproducible code, structure, documentation, tests, and portable seed material only. Real runtime residue stays local.

## License

This repository contains XinYu project code and a KohakuTerrarium source snapshot used as the underlying dependency. See [`LICENSE`](LICENSE).
