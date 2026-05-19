from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
CANONICAL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
PROVIDER_MODULE = "xinyu_context_retrieval"
OWNER_MODULE = "xinyu_living_memory_recall"
ALLOWED_PROVIDER_IMPORTERS = {OWNER_MODULE}
IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "memory",
    "runtime",
    "data",
    "library",
    "workspaces",
}


def build_live_memory_recall_boundary_audit(repo_root: Path) -> dict[str, Any]:
    app_root = _resolve_app_root(repo_root)
    modules = _scan_python_modules(app_root)
    provider_importers = sorted(
        module
        for module, imports in modules.items()
        if PROVIDER_MODULE in imports and module not in ALLOWED_PROVIDER_IMPORTERS
    )
    canonical_importers = sorted(
        module for module, imports in modules.items() if OWNER_MODULE in imports and module != PROVIDER_MODULE
    )
    runtime_entrypoints = _find_symbol_references(
        app_root,
        symbols=("run_living_memory_recall_algorithm", "retrieve_living_memory", "build_renderer_memory_context"),
    )
    role_counts = Counter(_module_role(module) for module in modules)
    return {
        "canonical_owner": CANONICAL_OWNER,
        "provider_module": PROVIDER_MODULE,
        "provider_role": "provider/compatibility",
        "allowed_provider_importers": sorted(ALLOWED_PROVIDER_IMPORTERS),
        "provider_importers_outside_owner": provider_importers,
        "canonical_importers": canonical_importers,
        "runtime_entrypoints": runtime_entrypoints,
        "module_role_counts": dict(sorted(role_counts.items())),
        "status": "pass" if not provider_importers else "fail",
        "privacy_note": "Scans Python source paths/imports only; does not read memory, runtime, QQ payloads, tokens, or private data bodies.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Live Memory Recall Boundary Audit",
        "",
        "This report checks that live memory recall has one public owner and that old recall code is only used as a provider/compatibility layer.",
        "",
        f"- status: {audit['status']}",
        f"- canonical_owner: `{audit['canonical_owner']}`",
        f"- provider_module: `{audit['provider_module']}`",
        f"- provider_role: {audit['provider_role']}",
        f"- privacy_note: {audit['privacy_note']}",
        "",
        "## Provider Importers Outside Owner",
        "",
    ]
    violations = list(audit.get("provider_importers_outside_owner") or [])
    if violations:
        for module in violations:
            lines.append(f"- `{module}`")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Canonical Importers",
            "",
        ]
    )
    for module in audit.get("canonical_importers") or []:
        lines.append(f"- `{module}`")
    if not audit.get("canonical_importers"):
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Runtime Entrypoints",
            "",
        ]
    )
    for symbol, refs in (audit.get("runtime_entrypoints") or {}).items():
        lines.append(f"### {symbol}")
        if refs:
            for ref in refs[:20]:
                lines.append(f"- `{ref}`")
        else:
            lines.append("- none")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _resolve_app_root(repo_root: Path) -> Path:
    root = repo_root.resolve()
    if (root / "xinyu_living_memory_recall.py").exists():
        return root
    return root / APP_REL


def _scan_python_modules(app_root: Path) -> dict[str, set[str]]:
    modules: dict[str, set[str]] = {}
    for path in _iter_python_files(app_root):
        module = _module_name(app_root, path)
        modules[module] = _imports_for_file(path)
    return modules


def _iter_python_files(app_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in app_root.rglob("*.py"):
        rel_parts = set(path.relative_to(app_root).parts)
        if rel_parts & IGNORED_DIRS:
            continue
        if "tests" in rel_parts or "ops" in rel_parts:
            continue
        files.append(path)
    return sorted(files)


def _imports_for_file(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, SyntaxError):
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.level == 0:
                imports.add(node.module.split(".", 1)[0])
    return imports


def _find_symbol_references(app_root: Path, *, symbols: tuple[str, ...]) -> dict[str, list[str]]:
    refs = {symbol: [] for symbol in symbols}
    for path in _iter_python_files(app_root):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(app_root).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for symbol in symbols:
                if symbol in line:
                    refs[symbol].append(f"{rel}:{lineno}")
    return refs


def _module_name(app_root: Path, path: Path) -> str:
    rel = path.relative_to(app_root).with_suffix("")
    return ".".join(rel.parts)


def _module_role(module: str) -> str:
    if module == OWNER_MODULE:
        return "canonical_owner"
    if module == PROVIDER_MODULE:
        return "provider_compatibility"
    if module.startswith("custom."):
        return "adapter_or_service"
    if module.startswith("xinyu_"):
        return "runtime_module"
    return "other"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit live memory recall canonical owner boundaries.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    audit = build_live_memory_recall_boundary_audit(Path(args.repo_root))
    rendered = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(audit)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0 if audit.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
