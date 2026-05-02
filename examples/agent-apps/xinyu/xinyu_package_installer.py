from __future__ import annotations

import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_dialogue_working_memory import load_dialogue_tail


PACKAGE_SPEC_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?(?:(?:==|~=|>=|<=|>|<|!=)[A-Za-z0-9.*+!_,.-]+)?$"
)
PACKAGE_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
DENIED_PACKAGES = {"pip", "setuptools", "wheel"}
IMPORT_NAME_OVERRIDES = {
    "beautifulsoup4": "bs4",
    "opencv-python": "cv2",
    "pillow": "PIL",
    "pymupdf": "fitz",
    "pypdf2": "PyPDF2",
    "pyyaml": "yaml",
    "python-docx": "docx",
}
PACKAGE_CONTEXT_MARKERS = (
    "pip install",
    "install",
    "package",
    "module",
    "import",
    "缺",
    "库",
    "装",
)
PACKAGE_TOKEN_RE = re.compile(
    r"(?<![/\\])\b[A-Za-z][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?(?:(?:==|~=|>=|<=|>|<|!=)[A-Za-z0-9.*+!_,.-]+)?\b"
)
PACKAGE_TOKEN_STOPWORDS = {
    "a",
    "all",
    "and",
    "attention",
    "google",
    "install",
    "is",
    "it",
    "module",
    "need",
    "package",
    "pdf",
    "pip",
    "python",
    "read",
    "self",
    "the",
    "this",
    "to",
    "transformer",
    "you",
}


class PackageInstallError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class PackageSpec:
    raw: str
    name: str
    import_name: str


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _split_package_text(text: str) -> list[str]:
    cleaned = text.replace(",", " ").replace("，", " ")
    return [part.strip() for part in cleaned.split() if part.strip()]


def _package_name(spec: str) -> str:
    match = PACKAGE_NAME_RE.match(spec)
    return match.group(1) if match else ""


def _import_name(name: str, explicit: str = "") -> str:
    if explicit.strip():
        return explicit.strip()
    normalized = name.lower().replace("_", "-")
    return IMPORT_NAME_OVERRIDES.get(normalized, name.replace("-", "_"))


def parse_package_specs(payload: dict[str, Any]) -> list[PackageSpec]:
    raw_packages = payload.get("packages")
    candidates: list[str] = []
    if isinstance(raw_packages, str):
        candidates.extend(_split_package_text(raw_packages))
    elif isinstance(raw_packages, (list, tuple)):
        candidates.extend(_safe_str(item).strip() for item in raw_packages if _safe_str(item).strip())
    text = _safe_str(payload.get("package_text")).strip()
    if text:
        candidates.extend(_split_package_text(text))

    explicit_imports = payload.get("import_names")
    import_names: list[str] = []
    if isinstance(explicit_imports, str):
        import_names = _split_package_text(explicit_imports)
    elif isinstance(explicit_imports, (list, tuple)):
        import_names = [_safe_str(item).strip() for item in explicit_imports if _safe_str(item).strip()]

    specs: list[PackageSpec] = []
    seen: set[str] = set()
    for index, raw in enumerate(candidates):
        spec = raw.strip()
        if not spec or spec.lower() in {"install", "add"}:
            continue
        if spec.startswith("-") or "://" in spec or any(ch in spec for ch in "\\/;&|`$'\""):
            raise PackageInstallError(HTTPStatus.BAD_REQUEST, f"unsafe package spec: {spec}")
        if not PACKAGE_SPEC_RE.match(spec):
            raise PackageInstallError(HTTPStatus.BAD_REQUEST, f"invalid package spec: {spec}")
        name = _package_name(spec)
        if not name:
            raise PackageInstallError(HTTPStatus.BAD_REQUEST, f"missing package name: {spec}")
        if name.lower().replace("_", "-") in DENIED_PACKAGES:
            raise PackageInstallError(HTTPStatus.BAD_REQUEST, f"package is blocked for runtime safety: {name}")
        key = spec.lower()
        if key in seen:
            continue
        seen.add(key)
        explicit_import = import_names[index] if index < len(import_names) else ""
        specs.append(PackageSpec(raw=spec, name=name, import_name=_import_name(name, explicit_import)))
    if not specs:
        raise PackageInstallError(HTTPStatus.BAD_REQUEST, "no valid package names were provided")
    if len(specs) > 8:
        raise PackageInstallError(HTTPStatus.BAD_REQUEST, "too many packages in one request")
    return specs


def _session_id_from_payload(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return _safe_str(payload.get("session_id") or metadata.get("session_id")).strip()


def _candidate_package_text_from_content(text: str) -> str:
    if not text.strip():
        return ""
    lowered = text.lower()
    if not any(marker in lowered or marker in text for marker in PACKAGE_CONTEXT_MARKERS):
        return ""
    candidates: list[str] = []
    for match in PACKAGE_TOKEN_RE.finditer(text):
        token = match.group(0).strip().strip(".,;:!?()[]{}<>")
        if not token:
            continue
        lowered_token = token.lower()
        if lowered_token in PACKAGE_TOKEN_STOPWORDS:
            continue
        if lowered_token.endswith((".pdf", ".md", ".txt", ".py", ".json")):
            continue
        if len(lowered_token) <= 1:
            continue
        candidates.append(token)
    unique: list[str] = []
    seen: set[str] = set()
    for token in candidates:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(token)
    return " ".join(unique[:4])


def infer_package_text_from_dialogue(root: Path, payload: dict[str, Any]) -> str:
    current = _safe_str(payload.get("current_text") or payload.get("text") or payload.get("package_text")).strip()
    direct = _candidate_package_text_from_content(current)
    if direct:
        return direct
    session_id = _session_id_from_payload(payload)
    if not session_id:
        return ""
    tail = load_dialogue_tail(root, session_id, max_entries=8)
    for item in reversed(tail):
        content = _safe_str(item.get("content")).strip()
        candidate = _candidate_package_text_from_content(content)
        if candidate:
            return candidate
    return ""


def _trace_path(root: Path) -> Path:
    return root / "runtime/package_installer/install_trace.jsonl"


def _write_trace(root: Path, row: dict[str, Any]) -> None:
    try:
        path = _trace_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _tail(text: str, *, limit: int = 1200) -> str:
    compact = "\n".join(line.rstrip() for line in text.splitlines() if line.strip())
    return compact[-limit:]


def _check_imports(specs: list[PackageSpec]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    importlib.invalidate_caches()
    for spec in specs:
        found = importlib.util.find_spec(spec.import_name) is not None
        checks.append({"package": spec.name, "import_name": spec.import_name, "ok": found})
    return checks


def install_python_packages(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        specs = parse_package_specs(payload)
    except PackageInstallError as exc:
        if exc.message != "no valid package names were provided":
            raise
        inferred = infer_package_text_from_dialogue(root, payload)
        if not inferred:
            raise
        enriched_payload = dict(payload)
        enriched_payload["packages"] = inferred
        specs = parse_package_specs(enriched_payload)
    dry_run = _as_bool(payload.get("dry_run"), default=False)
    timeout_seconds = max(30, min(_as_int(payload.get("timeout_seconds"), 180), 600))
    package_args = [spec.raw for spec in specs]
    started_at = _now_iso()
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        *package_args,
    ]

    if dry_run:
        import_checks = [{"package": spec.name, "import_name": spec.import_name, "ok": False} for spec in specs]
        result = {
            "accepted": True,
            "reply": "dry run: package install request is valid.",
            "packages": package_args,
            "dry_run": True,
            "installed": False,
            "return_code": None,
            "import_checks": import_checks,
            "notes": ["package_install_dry_run"],
        }
        _write_trace(root, {"started_at": started_at, "dry_run": True, "packages": package_args, "ok": True})
        return result

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return_code: int | None = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout = _safe_str(exc.stdout)
        stderr = _safe_str(exc.stderr)
        return_code = None
        timed_out = True

    import_checks = _check_imports(specs) if return_code == 0 and not timed_out else []
    imports_ok = bool(import_checks) and all(bool(item.get("ok")) for item in import_checks)
    installed = return_code == 0 and not timed_out and imports_ok
    notes: list[str] = ["package_install"]
    if timed_out:
        notes.append("pip_timeout")
    if return_code not in {0, None}:
        notes.append(f"pip_exit:{return_code}")
    if import_checks and not imports_ok:
        notes.append("import_check_failed")

    package_label = ", ".join(package_args)
    if installed:
        reply = f"装好了：{package_label}。导入检查也过了。"
    elif timed_out:
        reply = f"安装超时：{package_label}。没有算完成。"
    else:
        reply = f"没装成功：{package_label}。退出码 {return_code}。"

    trace = {
        "started_at": started_at,
        "finished_at": _now_iso(),
        "dry_run": False,
        "packages": package_args,
        "return_code": return_code,
        "timed_out": timed_out,
        "installed": installed,
        "import_checks": import_checks,
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
    }
    _write_trace(root, trace)
    return {
        "accepted": True,
        "reply": reply,
        "packages": package_args,
        "dry_run": False,
        "installed": installed,
        "return_code": return_code,
        "import_checks": import_checks,
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
        "notes": notes,
    }
