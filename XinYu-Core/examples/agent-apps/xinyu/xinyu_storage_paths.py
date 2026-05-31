from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence


APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
CASES_CONVERSATION_REL = Path("assets/cases/conversation")
LIBRARY_DATASETS_REL = Path("assets/library/datasets")
WORKSPACE_CASES_CONVERSATION_REL = Path("cases/conversation")
WORKSPACE_LIBRARY_DATASETS_REL = Path("library/datasets")
LEGACY_CASES_CONVERSATION_REL = Path("data/conversation_experience")
LEGACY_EXTERNAL_DATASETS_REL = Path("data/external")
MEMORY_KNOWLEDGE_REL = Path("memory/knowledge")

PUBLIC_DATASET_SUFFIXES = {".jsonl", ".ndjson", ".json", ".parquet"}
STORAGE_BOUNDARY_TABLE: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "cases.conversation",
        CASES_CONVERSATION_REL.as_posix(),
        (WORKSPACE_CASES_CONVERSATION_REL.as_posix(), LEGACY_CASES_CONVERSATION_REL.as_posix()),
        "canonical_preferred_legacy_fallback",
    ),
    (
        "library.datasets",
        LIBRARY_DATASETS_REL.as_posix(),
        (WORKSPACE_LIBRARY_DATASETS_REL.as_posix(), LEGACY_EXTERNAL_DATASETS_REL.as_posix()),
        "canonical_preferred_legacy_fallback",
    ),
    (
        "memory.knowledge",
        MEMORY_KNOWLEDGE_REL.as_posix(),
        (),
        "mixed_knowledge_pending_library_split",
    ),
)


def workspace_root(root: Path | str) -> Path:
    base = Path(root).resolve()
    for current in (base, *base.parents):
        if (current / APP_REL / "config.yaml").exists():
            return current
    return base


def app_root(root: Path | str) -> Path:
    base = Path(root).resolve()
    if (base / "config.yaml").exists() and base.name.lower() == "xinyu":
        return base

    candidate = base / APP_REL
    if (candidate / "config.yaml").exists():
        return candidate

    for current in (base, *base.parents):
        if (current / "config.yaml").exists() and current.name.lower() == "xinyu":
            return current
    return base


def storage_boundary_table() -> tuple[tuple[str, str, tuple[str, ...], str], ...]:
    return STORAGE_BOUNDARY_TABLE


def cases_conversation_dir(root: Path | str) -> Path:
    base = Path(root).resolve()
    local_canonical = base / CASES_CONVERSATION_REL
    canonical = workspace_root(root) / CASES_CONVERSATION_REL
    local_workspace = base / WORKSPACE_CASES_CONVERSATION_REL
    workspace = workspace_root(root) / WORKSPACE_CASES_CONVERSATION_REL
    local_legacy = base / LEGACY_CASES_CONVERSATION_REL
    legacy = app_root(root) / LEGACY_CASES_CONVERSATION_REL
    return _first_existing(
        _dedupe_paths((local_canonical, canonical, local_workspace, workspace, local_legacy, legacy)),
        default=local_canonical,
    )


def conversation_case_source_path(root: Path | str, filename: str) -> Path:
    base = Path(root).resolve()
    local_canonical = base / CASES_CONVERSATION_REL / filename
    canonical = workspace_root(root) / CASES_CONVERSATION_REL / filename
    local_workspace = base / WORKSPACE_CASES_CONVERSATION_REL / filename
    workspace = workspace_root(root) / WORKSPACE_CASES_CONVERSATION_REL / filename
    local_legacy = base / LEGACY_CASES_CONVERSATION_REL / filename
    legacy = app_root(root) / LEGACY_CASES_CONVERSATION_REL / filename
    return _first_existing(
        _dedupe_paths((local_canonical, canonical, local_workspace, workspace, local_legacy, legacy)),
        default=local_canonical,
    )


def public_dataset_registry_path(root: Path | str) -> Path:
    return conversation_case_source_path(root, "public_dataset_registry.json")


def seed_owner_cases_path(root: Path | str) -> Path:
    return conversation_case_source_path(root, "seed_owner_cases.jsonl")


def knowledge_dir(root: Path | str) -> Path:
    base = Path(root).resolve()
    if (base / "config.yaml").exists() and base.name.lower() == "xinyu":
        return base / MEMORY_KNOWLEDGE_REL

    workspace_app = base / APP_REL
    if (workspace_app / "config.yaml").exists():
        return workspace_app / MEMORY_KNOWLEDGE_REL

    return base / MEMORY_KNOWLEDGE_REL


def knowledge_file_path(root: Path | str, filename: str) -> Path:
    return knowledge_dir(root) / _clean_filename(filename)


def knowledge_ref(filename: str) -> str:
    return (MEMORY_KNOWLEDGE_REL / _clean_filename(filename)).as_posix()


def public_dataset_source_dirs(root: Path | str) -> tuple[Path, ...]:
    base = Path(root).resolve()
    local_canonical = base / LIBRARY_DATASETS_REL
    canonical = workspace_root(root) / LIBRARY_DATASETS_REL
    local_workspace = base / WORKSPACE_LIBRARY_DATASETS_REL
    workspace = workspace_root(root) / WORKSPACE_LIBRARY_DATASETS_REL
    local_legacy = base / LEGACY_EXTERNAL_DATASETS_REL
    legacy = app_root(root) / LEGACY_EXTERNAL_DATASETS_REL
    return _dedupe_paths((local_canonical, canonical, local_workspace, workspace, local_legacy, legacy))


def resolve_public_dataset_input_paths(
    root: Path | str,
    paths: Sequence[Path | str],
    *,
    dataset_id: str = "",
) -> tuple[Path, ...]:
    resolved: list[Path] = []
    for item in paths:
        matches = _resolve_public_dataset_input(root, item)
        if matches:
            resolved.extend(matches)
            continue
        resolved.append(_default_relative_path(root, item))

    if not resolved and dataset_id:
        resolved.extend(_dataset_alias_matches(root, dataset_id))
    return _dedupe_paths(resolved)


def _resolve_public_dataset_input(root: Path | str, item: Path | str) -> tuple[Path, ...]:
    raw = Path(item)
    if raw.is_absolute():
        return (raw,) if raw.exists() else ()

    direct_candidates = _dedupe_paths(
        (
            app_root(root) / raw,
            workspace_root(root) / raw,
            Path(root).resolve() / raw,
        )
    )
    for candidate in direct_candidates:
        if candidate.exists():
            return (candidate,)

    text = str(item).strip()
    if _looks_like_path(text):
        return ()
    return _dataset_alias_matches(root, text)


def _dataset_alias_matches(root: Path | str, alias: str) -> tuple[Path, ...]:
    clean_alias = _clean_alias(alias)
    if not clean_alias:
        return ()

    first_alias_token = clean_alias.split("_", 1)[0]
    for directory in public_dataset_source_dirs(root):
        if not directory.exists():
            continue
        matches: list[Path] = []
        for child in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
            if child.is_file() and child.suffix.lower() not in PUBLIC_DATASET_SUFFIXES:
                continue
            child_alias = _clean_alias(child.stem if child.is_file() else child.name)
            if (
                child_alias == clean_alias
                or child_alias.startswith(f"{clean_alias}_")
                or child_alias.startswith(f"{first_alias_token}_")
            ):
                matches.append(child)
        if matches:
            return _dedupe_paths(matches)
    return ()


def _default_relative_path(root: Path | str, item: Path | str) -> Path:
    raw = Path(item)
    if raw.is_absolute():
        return raw
    return app_root(root) / raw


def _looks_like_path(text: str) -> bool:
    return any(sep in text for sep in ("/", "\\")) or Path(text).suffix != ""


def _first_existing(paths: Iterable[Path], *, default: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return default


def _dedupe_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return tuple(result)


def _clean_alias(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _clean_filename(value: str) -> str:
    path = Path(str(value or "").strip())
    if path.name != str(path) or not path.name:
        raise ValueError(f"expected bare filename, got {value!r}")
    return path.name
