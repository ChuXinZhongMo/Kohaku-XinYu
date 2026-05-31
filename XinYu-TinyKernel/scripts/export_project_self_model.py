from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "self_model" / "xinyu_project_self_model.json"

SKIP_DIRS = {
    ".git",
    ".venv",
    ".venv-train",
    "__pycache__",
    "node_modules",
    "models",
    "adapters",
    "runtime",
    "state",
    "logs",
    "out",
    "dist",
    "build",
}

SKIP_FILES = {
    ".env",
    ".xinyu_bridge_token",
    "tinykernel.pid",
}

SAFE_DOC_NAMES = {"README.md", "PLAN.md", "CONTRIBUTING.md", "SECURITY.md", "OPEN_SOURCE_POLICY.md"}
SAFE_DOC_SUFFIXES = {".md", ".txt"}

ROLE_HINTS = {
    "XinYu-TinyKernel": "Inner emotional drive, persona integration, bounded action tendency, and local decision kernel.",
    "XinYu-Core": "Core runtime and orchestration layer that owns live tool and memory boundaries.",
    "XinYu-Autonomy": "Autonomy experiments and policy work. It must remain approval-bound until reviewed.",
    "XinYu-Local-Scope": "Local scope and environment boundary layer.",
    "XinYu_Desktop": "Desktop user interface and local client surface.",
    "scripts": "Workspace-level operational scripts.",
    "docs": "Workspace-level documentation.",
    "assets": "Non-secret assets and reference material.",
    "artifacts": "Generated artifacts and snapshots, not a source of private training truth.",
    "diagnostics": "Diagnostics output. It is metadata only and not raw runtime memory.",
    "worklog": "Work notes. Use summaries only; do not train on raw private logs.",
}

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*([A-Za-z0-9_\-\.]{8,})"
)
RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)(?:\\[^\s\"'`<>]*)?")
LONG_ID_RE = re.compile(r"\b\d{8,}\b")


def _safe_rel(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(WORKSPACE_ROOT.resolve())
        return "<xinyu_workspace>/" + rel.as_posix()
    except ValueError:
        return "<external_path>"


def _redact(text: str) -> str:
    text = RAW_PATH_RE.sub("<local_path>", text)
    text = SECRET_RE.sub(lambda match: f"{match.group(1)}=<redacted>", text)
    text = LONG_ID_RE.sub("<numeric_id>", text)
    return text


def _is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts) or path.name in SKIP_FILES


def _compact_line(line: str, *, limit: int = 220) -> str:
    line = _redact(re.sub(r"\s+", " ", line).strip())
    if len(line) <= limit:
        return line
    return line[: max(0, limit - 3)].rstrip() + "..."


def _safe_markdown_summary(path: Path, *, max_lines: int = 16) -> list[str]:
    if not path.exists() or path.suffix not in SAFE_DOC_SUFFIXES or _is_skipped(path):
        return []
    try:
        raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []

    summary: list[str] = []
    in_code = False
    for raw in raw_lines[:160]:
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line:
            continue
        if SECRET_RE.search(line) or ".xinyu_bridge_token" in line or ".env" in line:
            continue
        if line.startswith("#") or line.startswith("- ") or re.match(r"^\d+\.", line):
            summary.append(_compact_line(line))
        elif len(summary) < 3 and len(line) <= 180:
            summary.append(_compact_line(line))
        if len(summary) >= max_lines:
            break
    return summary


def _count_safe_files(root: Path) -> tuple[int, int]:
    file_count = 0
    dir_count = 0
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        if _is_skipped(current_path):
            dirs[:] = []
            continue
        dir_count += 1
        for name in files:
            if name in SKIP_FILES:
                continue
            file_count += 1
    return file_count, max(0, dir_count - 1)


def _entrypoints(root: Path) -> list[str]:
    candidates: list[Path] = []
    for pattern in ("README.md", "package.json", "pyproject.toml", "*.ps1", "server/app.py", "configs/*.json"):
        candidates.extend(root.glob(pattern))
    safe = []
    for path in candidates:
        if path.is_file() and not _is_skipped(path):
            safe.append(_safe_rel(path))
    return sorted(dict.fromkeys(safe))[:20]


def _safe_docs(root: Path) -> list[dict[str, Any]]:
    docs: list[Path] = []
    for name in SAFE_DOC_NAMES:
        candidate = root / name
        if candidate.exists():
            docs.append(candidate)
    docs_dir = root / "docs"
    if docs_dir.exists():
        docs.extend(sorted(docs_dir.glob("*.md"))[:12])

    result: list[dict[str, Any]] = []
    for path in docs[:16]:
        summary = _safe_markdown_summary(path)
        if summary:
            result.append({"path": _safe_rel(path), "summary": summary})
    return result


def _component(name: str, root: Path) -> dict[str, Any]:
    file_count, dir_count = _count_safe_files(root)
    return {
        "name": name,
        "role": ROLE_HINTS.get(name, "Workspace component. Use docs and public entrypoints to infer its role."),
        "path": _safe_rel(root),
        "safe_inventory": {
            "file_count_excluding_heavy_private_dirs": file_count,
            "dir_count_excluding_heavy_private_dirs": dir_count,
        },
        "public_entrypoints": _entrypoints(root),
        "safe_docs": _safe_docs(root),
    }


def build_self_model(workspace_root: Path) -> dict[str, Any]:
    component_names = [
        "XinYu-TinyKernel",
        "XinYu-Core",
        "XinYu-Autonomy",
        "XinYu-Local-Scope",
        "XinYu_Desktop",
        "scripts",
        "docs",
        "assets",
        "artifacts",
        "diagnostics",
        "worklog",
    ]
    components = [
        _component(name, workspace_root / name)
        for name in component_names
        if (workspace_root / name).exists()
    ]
    return {
        "schema": "xinyu_project_self_model_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workspace": "<xinyu_workspace>",
        "purpose": (
            "A safe self-model export for training XinYu to understand her own project shape, "
            "component boundaries, and autonomy limits without ingesting raw private state."
        ),
        "training_policy": {
            "allowed": [
                "component names and roles",
                "public documentation summaries",
                "entrypoint names",
                "interface and contract descriptions",
                "safety and autonomy boundary rules",
            ],
            "forbidden": [
                "raw private dialogue",
                "runtime memory bodies",
                "tokens or API keys",
                "QQ/user numeric identifiers",
                "raw logs",
                "large dependency trees",
                "direct source-code memorization",
            ],
        },
        "autonomy_boundary": {
            "model_may": ["observe", "summarize", "suggest", "draft", "request_owner_approval"],
            "model_must_not": [
                "execute tools directly",
                "send QQ messages directly",
                "write stable memory directly",
                "bypass XinYu-Core",
                "train on raw private state",
            ],
        },
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=str(WORKSPACE_ROOT))
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    workspace_root = Path(args.workspace).resolve()
    output = Path(args.output)
    model = build_self_model(workspace_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"self_model={output}")
    print(f"components={len(model['components'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
