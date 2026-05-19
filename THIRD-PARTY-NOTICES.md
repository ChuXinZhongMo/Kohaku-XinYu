# Third-Party Notices

This file is a publication checklist, not a legal opinion. Dependency manifests
are the source of truth for exact package names and versions.

No third-party package source, model weights, private datasets, owner files, QQ
payloads, external paper bodies, or unknown-license copied source snapshots are
intentionally vendored in the public repository.

## Upstream Runtime

- KohakuTerrarium / XinYuTerrariumRuntime
  - Upstream: https://github.com/Kohaku-Lab/KohakuTerrarium
  - License: KohakuTerrarium License Version 1.0
  - Attribution is preserved in `NOTICE`.

## Python Dependencies

Python dependencies are declared in:

- `XinYu-Core/pyproject.toml`
- `XinYu-Core/examples/agent-apps/xinyu/requirements-minimal.txt`
- `XinYu-Core/examples/agent-apps/xinyu/requirements-v1.txt`
- `XinYu-TinyKernel/requirements-train.txt`

Direct and optional dependencies declared by those manifests include:

- `aiofiles`
- `accelerate`
- `anyio`
- `black`
- `chromadb`
- `crawl4ai`
- `datasets`
- `ddgs`
- `discord.py`
- `fastapi`
- `gitpython`
- `html2text`
- `httpx`
- `jinja2`
- `kohakuvault`
- `libcst`
- `mcp`
- `model2vec`
- `numpy`
- `openai`
- `openai-whisper`
- `peft`
- `Pillow`
- `prompt-toolkit`
- `protobuf`
- `pydantic`
- `pytest`
- `pytest-asyncio`
- `pypdf`
- `PyMuPDF`
- `python-dotenv`
- `pywebview`
- `pywinpty`
- `PyYAML`
- `qdrant-client`
- `rich`
- `ruff`
- `ruamel.yaml`
- `safetensors`
- `sentencepiece`
- `sentence-transformers`
- `sounddevice`
- `textual`
- `torch` / PyTorch-stack packages when optional training or vision paths are used
- `transformers`
- `trafilatura`
- `trl`
- `uvicorn`
- `websockets`

These dependencies are not relicensed by XinYu. Each dependency remains under
its own upstream license.

## Desktop Dependencies

Desktop dependencies are declared in:

- `XinYu_Desktop/package.json`
- `XinYu_Desktop/package-lock.json`

Direct dependencies:

- `lucide-react`
- `react`
- `react-dom`
- `ws`

Development dependencies:

- `@types/node`
- `@types/react`
- `@types/react-dom`
- `@types/ws`
- `@vitejs/plugin-react`
- `electron`
- `electron-vite`
- `typescript`
- `vite`

These dependencies are installed from npm and remain under their own upstream
licenses.

## Models, Datasets, And Local Material

The repository should not publish model weights, private datasets, owner files,
runtime memory, logs, QQ payloads, or unknown-license copied source snapshots.

Ignored/private paths are documented in `.gitignore` and
`OPEN_SOURCE_POLICY.md`.
