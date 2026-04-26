from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


ORIGINS = {
    "self": "self_found",
    "self_found": "self_found",
    "auto": "self_found",
    "autonomous": "self_found",
    "owner": "owner_supplied",
    "user": "owner_supplied",
    "supplied": "owner_supplied",
    "owner_supplied": "owner_supplied",
}

TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".rst",
    ".toml",
    ".ts",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

REPO_STUDY_EXTENSIONS = {
    ".cfg",
    ".conf",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

REPO_PRIORITY_NAMES = {
    "readme.md",
    "readme.rst",
    "metadata.yaml",
    "_conf_schema.json",
    "plugin.json",
    "main.py",
    "__init__.py",
    "requirements.txt",
    "pyproject.toml",
}

SKIP_DIRS = {
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}

DEFAULT_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_TEXT_BYTES = 320_000
DEFAULT_MAX_REPO_FILES = 80


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")


def root_dir() -> Path:
    return Path(__file__).resolve().parent


def library_dir(root: Path) -> Path:
    return root / "learning"


def normalize_origin(value: str) -> str:
    key = value.strip().lower()
    if key not in ORIGINS:
        raise ValueError(f"unknown origin: {value}")
    return ORIGINS[key]


def slugify(value: str, fallback: str = "material") -> str:
    value = unquote(value).strip()
    value = re.sub(r"[^\w.\-]+", "-", value, flags=re.ASCII).strip(".-_")
    return value[:80] or fallback


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:8]


def ensure_layout(root: Path) -> None:
    base = library_dir(root)
    (base / "self_found").mkdir(parents=True, exist_ok=True)
    (base / "owner_supplied").mkdir(parents=True, exist_ok=True)


def manifest_path(root: Path) -> Path:
    return library_dir(root) / "manifest.jsonl"


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def item_id_for(created_at: str, seed: str) -> str:
    date_part = created_at[:10].replace("-", "")
    time_part = created_at[11:19].replace(":", "")
    return f"learn-{date_part}-{time_part}-{short_hash(seed)}"


def create_item_dir(root: Path, origin: str, label: str, item_id: str) -> Path:
    base = library_dir(root) / origin
    folder = base / f"{now_stamp()}_{slugify(label)}_{item_id[-8:]}"
    if not folder.exists():
        folder.mkdir(parents=True)
        return folder
    suffix = 2
    while True:
        candidate = base / f"{folder.name}-{suffix}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        suffix += 1


def append_manifest(root: Path, metadata: dict[str, object]) -> None:
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")


def load_manifest(root: Path) -> list[dict[str, object]]:
    path = manifest_path(root)
    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def write_metadata(root: Path, item_dir: Path, metadata: dict[str, object]) -> None:
    (item_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    append_manifest(root, metadata)


def guess_extension(url: str, content_type: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix
    if suffix:
        return suffix[:12]
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    return guessed or ".bin"


def filename_from_url(url: str, content_type: str) -> str:
    path_name = Path(urlparse(url).path).name
    if path_name:
        return slugify(path_name)
    return "downloaded" + guess_extension(url, content_type)


def download_bytes(url: str, max_bytes: int = DEFAULT_MAX_BYTES) -> tuple[bytes, str, str]:
    request = Request(url, headers={"User-Agent": "XinYuLearningLibrary/0.1"})
    try:
        with urlopen(request, timeout=30) as response:
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "application/octet-stream")
            data = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise RuntimeError(f"download failed with HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"download failed: {exc.reason}") from exc
    if len(data) > max_bytes:
        raise RuntimeError(f"download exceeds max bytes: {max_bytes}")
    return data, final_url, content_type


def clean_html_text(raw: str) -> str:
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_text_from_bytes(data: bytes, filename: str, content_type: str) -> str:
    lower_type = content_type.lower()
    suffix = Path(filename).suffix.lower()
    if "html" in lower_type or suffix in {".html", ".htm"}:
        return clean_html_text(decode_text(data))
    if lower_type.startswith("text/") or suffix in TEXT_EXTENSIONS:
        return decode_text(data)
    return ""


def truncate_text(text: str, max_chars: int = DEFAULT_MAX_TEXT_BYTES) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[truncated by XinYu learning library]\n"


def claim_from_text(text: str, fallback: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return fallback
    return cleaned[:520].replace("|", "/")


def write_extracted_text(item_dir: Path, title: str, text: str) -> Path | None:
    if not text.strip():
        return None
    path = item_dir / "extracted_text.md"
    path.write_text(f"# {title}\n\n{truncate_text(text).rstrip()}\n", encoding="utf-8")
    return path


def source_type_for_download(url: str, filename: str, content_type: str) -> str:
    host = urlparse(url).netloc.lower()
    suffix = Path(filename).suffix.lower()
    if "github.com" in host:
        return "github_source"
    if suffix == ".pdf" or "pdf" in content_type.lower():
        return "paper_pdf"
    if host.endswith(".edu") or host.endswith(".gov"):
        return "public_institutional_source"
    if content_type.lower().startswith("text/") or suffix in TEXT_EXTENSIONS:
        return "public_web_source"
    return "downloaded_file"


def register_downloaded_item(
    root: Path,
    origin: str,
    kind: str,
    label: str,
    source_url: str,
    title: str,
    claim: str,
    source_type: str,
    stored_paths: list[Path],
    extracted_text_path: Path | None,
    reason: str,
    question_id: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    created_at = now_iso()
    item_id = item_id_for(created_at, source_url + label + reason)
    item_dir = create_item_dir(root, origin, label, item_id)
    moved_paths: list[Path] = []
    for stored in stored_paths:
        target = item_dir / stored.name
        if stored.resolve() != target.resolve():
            if stored.is_dir():
                shutil.copytree(stored, target)
            else:
                shutil.copy2(stored, target)
        moved_paths.append(target)
    final_extracted: Path | None = None
    if extracted_text_path and extracted_text_path.exists():
        final_extracted = item_dir / extracted_text_path.name
        if extracted_text_path.resolve() != final_extracted.resolve():
            shutil.copy2(extracted_text_path, final_extracted)

    metadata: dict[str, object] = {
        "id": item_id,
        "origin": origin,
        "kind": kind,
        "created_at": created_at,
        "title": title,
        "reason": reason,
        "question_id": question_id,
        "source_url": source_url,
        "source_type": source_type,
        "claim": claim,
        "item_dir": rel_to_root(root, item_dir),
        "stored_paths": [rel_to_root(root, path) for path in moved_paths],
        "extracted_text_path": rel_to_root(root, final_extracted) if final_extracted else "",
        "stage_status": "not_staged",
    }
    if extra:
        metadata.update(extra)
    write_metadata(root, item_dir, metadata)
    return metadata


def command_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else root_dir()
    ensure_layout(root)
    print("learning_library:", rel_to_root(root, library_dir(root)))
    print("self_found:", rel_to_root(root, library_dir(root) / "self_found"))
    print("owner_supplied:", rel_to_root(root, library_dir(root) / "owner_supplied"))
    return 0


def command_url(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else root_dir()
    ensure_layout(root)
    origin = normalize_origin(args.origin)
    data, final_url, content_type = download_bytes(args.url, args.max_bytes)
    filename = filename_from_url(final_url, content_type)
    title = args.title or filename
    source_type = source_type_for_download(final_url, filename, content_type)
    with tempfile.TemporaryDirectory(prefix="xinyu-learning-url-") as tmp:
        tmpdir = Path(tmp)
        raw_path = tmpdir / filename
        raw_path.write_bytes(data)
        extracted_text = extract_text_from_bytes(data, filename, content_type)
        text_path = write_extracted_text(tmpdir, title, extracted_text)
        fallback = f"downloaded {source_type} from {final_url}"
        metadata = register_downloaded_item(
            root=root,
            origin=origin,
            kind="url",
            label=args.label or title,
            source_url=final_url,
            title=title,
            claim=claim_from_text(extracted_text, fallback),
            source_type=source_type,
            stored_paths=[raw_path],
            extracted_text_path=text_path,
            reason=args.reason,
            question_id=args.question_id,
            extra={"content_type": content_type},
        )
    print_created(metadata)
    if args.stage:
        stage_item(root, str(metadata["id"]), curated=args.curated)
    return 0


def parse_github_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    if parsed.netloc.lower() != "github.com":
        raise ValueError("GitHub URL must use github.com")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must include owner and repo")
    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    return owner, repo


def github_archive_urls(owner: str, repo: str, branch: str | None) -> list[tuple[str, str]]:
    branches = [branch] if branch else []
    for fallback in ("main", "master"):
        if fallback not in branches:
            branches.append(fallback)
    return [
        (candidate, f"https://github.com/{owner}/{repo}/archive/refs/heads/{candidate}.zip")
        for candidate in branches
        if candidate
    ]


def is_repo_study_file(rel_path: Path) -> bool:
    parts = {part.lower() for part in rel_path.parts}
    if parts.intersection(SKIP_DIRS):
        return False
    name = rel_path.name.lower()
    if name in REPO_PRIORITY_NAMES:
        return True
    return rel_path.suffix.lower() in REPO_STUDY_EXTENSIONS


def safe_extract_name(rel_path: Path) -> Path:
    parts = [slugify(part, "part") for part in rel_path.parts if part not in {"", ".", ".."}]
    return Path(*parts) if parts else Path("file")


def collect_repo_study_files(zip_path: Path, output_dir: Path, max_files: int) -> tuple[list[Path], str]:
    selected: list[tuple[zipfile.ZipInfo, Path]] = []
    with zipfile.ZipFile(zip_path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        for info in infos:
            raw = Path(info.filename)
            rel = Path(*raw.parts[1:]) if len(raw.parts) > 1 else raw
            if not is_repo_study_file(rel):
                continue
            if info.file_size > 260_000:
                continue
            priority = rel.name.lower() in REPO_PRIORITY_NAMES
            selected.append((info, rel if priority else Path("zz") / rel))
        selected.sort(key=lambda item: (0 if item[1].parts[0] != "zz" else 1, str(item[1]).lower()))
        chosen = selected[:max_files]
        extracted_paths: list[Path] = []
        combined_parts: list[str] = []
        for info, sort_rel in chosen:
            raw = Path(info.filename)
            rel = Path(*raw.parts[1:]) if len(raw.parts) > 1 else raw
            target = output_dir / safe_extract_name(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(info)
            target.write_bytes(data)
            extracted_paths.append(target)
            text = extract_text_from_bytes(data, target.name, "text/plain")
            if text.strip():
                combined_parts.append(f"## {rel.as_posix()}\n\n```text\n{truncate_text(text, 40_000).rstrip()}\n```\n")
    return extracted_paths, "\n".join(combined_parts).strip()


def command_github(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else root_dir()
    ensure_layout(root)
    origin = normalize_origin(args.origin)
    owner, repo = parse_github_url(args.url)
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-learning-github-") as tmp:
        tmpdir = Path(tmp)
        archive_path = tmpdir / f"{owner}-{repo}.zip"
        branch_used = ""
        for branch, archive_url in github_archive_urls(owner, repo, args.branch):
            try:
                data, final_url, content_type = download_bytes(archive_url, args.max_bytes)
                archive_path.write_bytes(data)
                branch_used = branch
                break
            except RuntimeError as exc:
                errors.append(str(exc))
        if not branch_used:
            raise RuntimeError("; ".join(errors) or "could not download GitHub archive")

        selected_dir = tmpdir / "selected_files"
        selected_dir.mkdir()
        selected_paths, combined_text = collect_repo_study_files(archive_path, selected_dir, args.max_files)
        title = args.title or f"{owner}/{repo}"
        text_path = write_extracted_text(tmpdir, title, combined_text)
        claim = (
            f"GitHub repository snapshot {owner}/{repo} branch {branch_used}; "
            f"selected {len(selected_paths)} readable study files for plugin/code learning."
        )
        stored_paths = [archive_path, selected_dir]
        metadata = register_downloaded_item(
            root=root,
            origin=origin,
            kind="github_repo",
            label=args.label or f"github-{owner}-{repo}",
            source_url=f"https://github.com/{owner}/{repo}",
            title=title,
            claim=claim,
            source_type="github_repository",
            stored_paths=stored_paths,
            extracted_text_path=text_path,
            reason=args.reason,
            question_id=args.question_id,
            extra={
                "github_owner": owner,
                "github_repo": repo,
                "github_branch": branch_used,
                "selected_file_count": len(selected_paths),
            },
        )
    print_created(metadata)
    if args.stage:
        stage_item(root, str(metadata["id"]), curated=args.curated)
    return 0


def should_copy_local_file(path: Path, max_bytes: int) -> bool:
    if any(part.lower() in SKIP_DIRS for part in path.parts):
        return False
    try:
        return path.stat().st_size <= max_bytes
    except OSError:
        return False


def copy_local_path(source: Path, target: Path, max_bytes: int) -> list[Path]:
    copied: list[Path] = []
    if source.is_file():
        target.mkdir(parents=True, exist_ok=True)
        dest = target / source.name
        shutil.copy2(source, dest)
        copied.append(dest)
        return copied
    for path in source.rglob("*"):
        if not path.is_file() or not should_copy_local_file(path, max_bytes):
            continue
        rel = path.relative_to(source)
        dest = target / safe_extract_name(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        copied.append(dest)
    return copied


def combined_text_from_files(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        data = path.read_bytes()
        text = extract_text_from_bytes(data, path.name, "text/plain")
        if text.strip():
            parts.append(f"## {path.name}\n\n```text\n{truncate_text(text, 40_000).rstrip()}\n```\n")
    return "\n".join(parts).strip()


def command_add(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else root_dir()
    ensure_layout(root)
    origin = normalize_origin(args.origin)
    source = Path(args.path).resolve()
    if not source.exists():
        raise RuntimeError(f"path does not exist: {source}")
    with tempfile.TemporaryDirectory(prefix="xinyu-learning-local-") as tmp:
        tmpdir = Path(tmp)
        copied_dir = tmpdir / ("local_folder" if source.is_dir() else "local_file")
        copied = copy_local_path(source, copied_dir, args.max_bytes)
        if not copied:
            raise RuntimeError("no files were copied from local path")
        title = args.title or source.name
        combined_text = combined_text_from_files(copied)
        text_path = write_extracted_text(tmpdir, title, combined_text)
        fallback = f"owner/local material copied from {source.name}"
        metadata = register_downloaded_item(
            root=root,
            origin=origin,
            kind="local_path",
            label=args.label or source.name,
            source_url=source.as_uri() if source.is_absolute() else str(source),
            title=title,
            claim=claim_from_text(combined_text, fallback),
            source_type="owner_local_file" if origin == "owner_supplied" else "local_file",
            stored_paths=[copied_dir],
            extracted_text_path=text_path,
            reason=args.reason,
            question_id=args.question_id,
            extra={"copied_file_count": len(copied)},
        )
    print_created(metadata)
    if args.stage:
        stage_item(root, str(metadata["id"]), curated=args.curated)
    return 0


def print_created(metadata: dict[str, object]) -> None:
    print("created:", metadata["id"])
    print("origin:", metadata["origin"])
    print("kind:", metadata["kind"])
    print("title:", metadata["title"])
    print("item_dir:", metadata["item_dir"])
    print("extracted_text:", metadata.get("extracted_text_path") or "none")


def find_manifest_item(root: Path, item_id: str) -> dict[str, object] | None:
    for item in load_manifest(root):
        if item.get("id") == item_id:
            return item
    return None


def ensure_source_materials_file(root: Path) -> Path:
    path = root / "memory/knowledge/source_materials.md"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    created_at = now_iso()
    path.write_text(
        f"""---
title: Source Materials
memory_type: source_materials
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: system
created_at: {created_at}
updated_at: {created_at}
last_confirmed_at: {created_at}
importance_score: 74
impact_score: 72
confidence_score: 100
status: active
tags: [knowledge, sources, materials]
---

# Source Materials
""",
        encoding="utf-8",
    )
    return path


def next_material_id(text: str, date_part: str) -> str:
    pattern = re.compile(rf"(?m)^## material-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(text)]
    return f"material-{date_part}-{max(numbers, default=0) + 1:03d}"


def source_url_for_stage(item: dict[str, object]) -> str:
    source_url = str(item.get("source_url") or "").strip()
    if source_url:
        return source_url
    return "learning://" + str(item.get("id", "unknown"))


def sanitize_field(value: object, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("|", "/")
    return text[:limit] or "none"


def stage_manifest_record(root: Path, item: dict[str, object], curated: bool = False) -> str:
    path = ensure_source_materials_file(root)
    text = path.read_text(encoding="utf-8-sig").rstrip()
    item_id = str(item["id"])
    if f"- learning_item_id: {item_id}" in text:
        return "already_staged"

    created_at = str(item.get("created_at") or now_iso())
    fetched_at = created_at
    date_part = fetched_at[:10] if re.match(r"\d{4}-\d{2}-\d{2}", fetched_at) else datetime.now().strftime("%Y-%m-%d")
    material_id = next_material_id(text, date_part)
    origin = str(item.get("origin", "unknown"))
    is_curated = curated or origin == "owner_supplied"
    reliability = "curated" if is_curated else "medium_ready"
    comparison_status = "curated" if is_curated else "not_compared"
    evidence_hosts = "1" if is_curated else "0"
    local_path = str(item.get("item_dir") or "")
    addition = (
        f"\n\n## {material_id}\n"
        f"- question_id: {sanitize_field(item.get('question_id') or 'learning-library')}\n"
        f"- source_question: {sanitize_field(item.get('reason') or item.get('title'))}\n"
        f"- url: {sanitize_field(source_url_for_stage(item))}\n"
        f"- source_type: {sanitize_field(item.get('source_type') or item.get('kind'))}\n"
        f"- reliability: {reliability}\n"
        "- integration_scope: knowledge_only\n"
        "- status: ready\n"
        f"- fetched_at: {fetched_at}\n"
        f"- comparison_status: {comparison_status}\n"
        f"- evidence_hosts: {evidence_hosts}\n"
        f"- learning_origin: {origin}\n"
        f"- learning_item_id: {item_id}\n"
        f"- local_path: {sanitize_field(local_path)}\n"
        f"- claim: {sanitize_field(item.get('claim'))}\n"
    )
    path.write_text(text + addition + "\n", encoding="utf-8")
    return material_id


def stage_item(root: Path, item_id: str, curated: bool = False) -> str:
    item = find_manifest_item(root, item_id)
    if not item:
        raise RuntimeError(f"learning item not found in manifest: {item_id}")
    material_id = stage_manifest_record(root, item, curated=curated)
    print("staged:", item_id)
    print("material:", material_id)
    return material_id


def command_stage(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else root_dir()
    ensure_layout(root)
    if args.all:
        staged = 0
        for item in load_manifest(root):
            result = stage_manifest_record(root, item, curated=args.curated)
            if result != "already_staged":
                print(f"staged: {item['id']} -> {result}")
                staged += 1
        print("staged_count:", staged)
        return 0
    if not args.id:
        raise RuntimeError("stage requires --id or --all")
    stage_item(root, args.id, curated=args.curated)
    return 0


def command_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else root_dir()
    ensure_layout(root)
    items = load_manifest(root)
    if args.origin:
        origin = normalize_origin(args.origin)
        items = [item for item in items if item.get("origin") == origin]
    for item in items[-args.limit :]:
        print(
            f"{item.get('id')} | {item.get('origin')} | {item.get('kind')} | "
            f"{item.get('title')} | {item.get('item_dir')}"
        )
    if not items:
        print("(no learning items)")
    return 0


def add_common_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--origin", default="owner_supplied", help="owner_supplied or self_found")
    parser.add_argument("--reason", default="unspecified learning material")
    parser.add_argument("--question-id", default="learning-library")
    parser.add_argument("--title", default="")
    parser.add_argument("--label", default="")
    parser.add_argument("--stage", action="store_true", help="also stage item into memory/knowledge/source_materials.md")
    parser.add_argument("--curated", action="store_true", help="stage as curated even if origin is self_found")
    parser.add_argument("--root", default="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XinYu local learning-material library.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create learning/self_found and learning/owner_supplied")
    init.add_argument("--root", default="")
    init.set_defaults(func=command_init)

    url = sub.add_parser("url", help="download a URL, file, web page, or paper")
    url.add_argument("url")
    url.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    add_common_source_args(url)
    url.set_defaults(func=command_url)

    github = sub.add_parser("github", help="download and inspect a GitHub repository archive")
    github.add_argument("url")
    github.add_argument("--branch", default="")
    github.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    github.add_argument("--max-files", type=int, default=DEFAULT_MAX_REPO_FILES)
    add_common_source_args(github)
    github.set_defaults(func=command_github)

    add = sub.add_parser("add", help="copy a local file or folder into the learning library")
    add.add_argument("path")
    add.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    add_common_source_args(add)
    add.set_defaults(func=command_add)

    stage = sub.add_parser("stage", help="stage manifest items into source_materials")
    stage.add_argument("--id", default="")
    stage.add_argument("--all", action="store_true")
    stage.add_argument("--curated", action="store_true")
    stage.add_argument("--root", default="")
    stage.set_defaults(func=command_stage)

    list_cmd = sub.add_parser("list", help="list registered learning items")
    list_cmd.add_argument("--origin", default="")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument("--root", default="")
    list_cmd.set_defaults(func=command_list)

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
