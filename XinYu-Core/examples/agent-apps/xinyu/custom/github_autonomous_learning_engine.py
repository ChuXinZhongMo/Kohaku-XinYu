from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


CONFIG_REL = Path("memory/context/github_learning_sources.md")
STATE_REL = Path("memory/context/github_learning_state.md")
CANDIDATES_REL = Path("memory/knowledge/github_learning_candidates.md")
TRACE_REL = Path("runtime/github_learning_trace.jsonl")

DEFAULT_GITHUB_SEARCH_ENDPOINT = "https://api.github.com/search/repositories"
DEFAULT_TIMEOUT_SECONDS = 16.0
DEFAULT_MAX_QUERIES = 2
DEFAULT_MAX_REPOS = 1
DEFAULT_MIN_INTERVAL_SECONDS = 21600
DEFAULT_MIN_STARS = 0
DEFAULT_MAX_FILES = 60
DEFAULT_MAX_BYTES = 25 * 1024 * 1024
DISABLED_VALUES = {"", "0", "false", "no", "off", "disabled", "block", "blocked"}
ENABLED_VALUES = {"1", "true", "yes", "on", "enabled", "allow", "allowed"}

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def one_line(value: Any, *, limit: int = 260, default: str = "none") -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split()).strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if not text:
        return default
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def clean_token(value: Any, *, default: str = "item") -> str:
    text = one_line(value, limit=100, default="").lower().replace(" ", "-")
    text = re.sub(r"[^a-z0-9_-]+", "-", text).strip("-_")
    return text or default


def extract_value(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            return one_line(match.group(2), limit=500, default=default)
    return default


def as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return as_int(raw, default)


def source_int(source: dict[str, str], key: str, default: int) -> int:
    return max(0, as_int(source.get(key), default))


def load_sources(root: Path) -> list[dict[str, str]]:
    text = read_text(root / CONFIG_REL)
    if not text:
        return []
    parts = re.split(r"(?m)^##\s+([A-Za-z0-9_-]+)\s*$", text)
    sources: list[dict[str, str]] = []
    for index in range(1, len(parts), 2):
        source_id = clean_token(parts[index], default="github-source")
        body = parts[index + 1]
        fields = {"source_id": source_id}
        for match in _FIELD_RE.finditer(body):
            fields[match.group(1)] = one_line(match.group(2), limit=800)
        if fields.get("enabled", "true").strip().lower() not in ENABLED_VALUES:
            continue
        query = fields.get("query", "").strip()
        url = fields.get("url", "").strip()
        if not query and not allowed_github_repo_url(url):
            continue
        fields.setdefault("question_id", f"github-{source_id}")
        fields.setdefault("reason", "study public GitHub repository patterns for XinYu implementation learning")
        fields.setdefault("max_repos", "1")
        fields.setdefault("min_stars", str(DEFAULT_MIN_STARS))
        fields.setdefault("max_files", str(DEFAULT_MAX_FILES))
        fields.setdefault("max_bytes", str(DEFAULT_MAX_BYTES))
        fields.setdefault("include_forks", "false")
        fields.setdefault("include_archived", "false")
        fields.setdefault("stage", "true")
        fields.setdefault("curated", "false")
        sources.append(fields)
    return sources


def github_autonomy_allowed(root: Path) -> tuple[bool, str]:
    raw = os.environ.get("XINYU_AUTONOMOUS_GITHUB", "").strip().lower()
    if raw:
        if raw in DISABLED_VALUES:
            return False, "env_disabled"
        if raw in ENABLED_VALUES:
            return True, "env_enabled"

    capability = read_text(root / "memory/context/capability_zones_state.md")
    grants = read_text(root / "memory/context/owner_permission_grants.md")
    if (
        "public_github_discovery: enabled_read_only_public_repos" in capability
        or "grant_autonomous_public_github_discovery: approved_read_only_public_repos" in grants
    ):
        return True, "owner_policy_granted"
    return False, "policy_not_granted"


def parse_repo_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url.strip())
    if parsed.netloc.lower() != "github.com":
        raise ValueError("not a github.com URL")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("missing owner/repo")
    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    return owner, repo


def allowed_github_repo_url(url: str) -> bool:
    try:
        owner, repo = parse_repo_url(url)
    except ValueError:
        return False
    blocked = {"pull", "issues", "commit", "tree", "blob", "releases", "actions", "wiki"}
    parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    return bool(owner and repo) and (len(parts) <= 2 or parts[2] not in blocked)


def canonical_repo_url(url: str) -> str:
    owner, repo = parse_repo_url(url)
    return f"https://github.com/{owner}/{repo}"


def source_type_for_candidate(url: str) -> str:
    return "github_repository" if allowed_github_repo_url(url) else "unknown_source"


def fetch_github_search(
    query: str,
    *,
    endpoint: str,
    per_page: int,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    headers = {
        "User-Agent": "XinYuGitHubAutonomousLearning/0.1 read-only public repos",
        "Accept": "application/vnd.github+json, application/json",
    }
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": max(1, min(per_page, 10))}
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = client.get(endpoint, params=params)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def direct_repo_candidate(source: dict[str, str]) -> dict[str, Any]:
    url = canonical_repo_url(source["url"])
    owner, repo = parse_repo_url(url)
    return {
        "full_name": f"{owner}/{repo}",
        "html_url": url,
        "description": source.get("description", "configured public GitHub repository"),
        "language": source.get("language", "unknown"),
        "stargazers_count": as_int(source.get("stars"), 0),
        "fork": False,
        "archived": False,
        "pushed_at": source.get("pushed_at", "unknown"),
    }


def normalize_candidate(
    item: dict[str, Any],
    source: dict[str, str],
    *,
    discovered_at: str,
) -> dict[str, str] | None:
    html_url = one_line(item.get("html_url") or item.get("url"), limit=500, default="")
    if not allowed_github_repo_url(html_url):
        return None
    if bool(item.get("private")):
        return None
    include_forks = source.get("include_forks", "false").lower() in ENABLED_VALUES
    include_archived = source.get("include_archived", "false").lower() in ENABLED_VALUES
    if bool(item.get("fork")) and not include_forks:
        return None
    if bool(item.get("archived")) and not include_archived:
        return None
    stars = as_int(item.get("stargazers_count"), 0)
    if stars < source_int(source, "min_stars", DEFAULT_MIN_STARS):
        return None
    url = canonical_repo_url(html_url)
    owner, repo = parse_repo_url(url)
    full_name = one_line(item.get("full_name") or f"{owner}/{repo}", limit=180)
    return {
        "source_id": source["source_id"],
        "question_id": source.get("question_id", f"github-{source['source_id']}"),
        "query": source.get("query") or source.get("url", ""),
        "reason": source.get("reason", "study public GitHub repository patterns"),
        "full_name": full_name,
        "url": url,
        "description": one_line(item.get("description"), limit=300),
        "language": one_line(item.get("language"), limit=80),
        "stars": str(stars),
        "pushed_at": one_line(item.get("pushed_at"), limit=120),
        "source_type": source_type_for_candidate(url),
        "status": "candidate",
        "stage_status": "not_staged",
        "learning_item_id": "none",
        "material_id": "none",
        "discovered_at": discovered_at,
        "last_seen_at": discovered_at,
    }


def split_candidates(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (github-candidate-[\w-]+)\n", text or "")
    results: list[dict[str, str]] = []
    if len(parts) < 3:
        return results
    for index in range(1, len(parts), 2):
        item = {"candidate_id": parts[index].strip()}
        for line in parts[index + 1].splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and ": " in stripped:
                key, value = stripped[2:].split(": ", 1)
                item[key.strip()] = value.strip()
        if item.get("url") and item.get("url") != "none":
            results.append(item)
    return results


def next_candidate_id(existing: list[dict[str, str]], date_part: str) -> str:
    numbers: list[int] = []
    for item in existing:
        candidate_id = item.get("candidate_id", "")
        match = re.match(rf"github-candidate-{re.escape(date_part)}-(\d{{3}})$", candidate_id)
        if match:
            numbers.append(int(match.group(1)))
    return f"github-candidate-{date_part}-{max(numbers, default=0) + 1:03d}"


def render_candidates(updated_at: str, candidates: list[dict[str, str]]) -> str:
    blocks: list[str] = []
    for item in candidates:
        blocks.append(
            f"## {item['candidate_id']}\n"
            f"- source_id: {one_line(item.get('source_id'))}\n"
            f"- question_id: {one_line(item.get('question_id'))}\n"
            f"- query: {one_line(item.get('query'), limit=500)}\n"
            f"- full_name: {one_line(item.get('full_name'), limit=180)}\n"
            f"- url: {one_line(item.get('url'), limit=500)}\n"
            f"- description: {one_line(item.get('description'), limit=300)}\n"
            f"- language: {one_line(item.get('language'), limit=80)}\n"
            f"- stars: {one_line(item.get('stars'))}\n"
            f"- pushed_at: {one_line(item.get('pushed_at'))}\n"
            f"- source_type: {one_line(item.get('source_type'))}\n"
            f"- status: {one_line(item.get('status'))}\n"
            f"- stage_status: {one_line(item.get('stage_status'))}\n"
            f"- learning_item_id: {one_line(item.get('learning_item_id'))}\n"
            f"- material_id: {one_line(item.get('material_id'))}\n"
            f"- discovered_at: {one_line(item.get('discovered_at'))}\n"
            f"- last_seen_at: {one_line(item.get('last_seen_at'))}\n"
            f"- reason: {one_line(item.get('reason'), limit=300)}\n"
        )
    body = "\n".join(blocks) if blocks else "## github-candidate-none\n- status: none\n- url: none\n"
    return f"""---
title: GitHub Learning Candidates
memory_type: github_learning_candidates
time_scope: short_term
subject_ids: [xinyu]
protected: false
source: github_autonomous_learning_engine
created_at: 2026-05-06T00:00:00+08:00
updated_at: {updated_at}
last_confirmed_at: {updated_at}
importance_score: 76
impact_score: 75
confidence_score: 94
status: active
tags: [github, learning, source, candidates]
---

# GitHub Learning Candidates

## Rules
- Candidates are public GitHub repositories only.
- Candidate descriptions and search snippets are not learned as facts.
- Staged repositories enter the learning library as self_found material unless owner-curated separately.
- Repository code is never executed by this lane.

{body}"""


def existing_repo_urls(root: Path, candidates: list[dict[str, str]]) -> set[str]:
    urls: set[str] = set()
    for item in candidates:
        url = item.get("url", "")
        if item.get("stage_status") == "staged" and allowed_github_repo_url(url):
            urls.add(canonical_repo_url(url))

    source_materials = read_text(root / "memory/knowledge/source_materials.md")
    for match in re.finditer(r"(?m)^-\s*url:\s*(https://github\.com/[^\s]+)\s*$", source_materials):
        url = match.group(1).strip()
        if allowed_github_repo_url(url):
            urls.add(canonical_repo_url(url))

    try:
        from xinyu_learning_library import load_manifest

        for item in load_manifest(root):
            url = str(item.get("source_url") or "")
            if allowed_github_repo_url(url):
                urls.add(canonical_repo_url(url))
    except Exception:
        pass
    return urls


def material_id_for_learning_item(root: Path, learning_item_id: str) -> str:
    if not learning_item_id:
        return ""
    text = read_text(root / "memory/knowledge/source_materials.md")
    marker = f"- learning_item_id: {learning_item_id}"
    marker_index = text.find(marker)
    if marker_index < 0:
        return ""
    preceding = text[:marker_index]
    matches = re.findall(r"(?m)^## (material-\d{4}-\d{2}-\d{2}-\d{3})\n", preceding)
    return matches[-1] if matches else ""


def stage_github_candidate(root: Path, candidate: dict[str, str], *, curated: bool = False) -> dict[str, str]:
    from xinyu_learning_library import command_github, load_manifest

    before_ids = {str(item.get("id")) for item in load_manifest(root)}
    args = Namespace(
        url=candidate["url"],
        branch="",
        max_bytes=max(1, as_int(candidate.get("max_bytes"), DEFAULT_MAX_BYTES)),
        max_files=max(1, as_int(candidate.get("max_files"), DEFAULT_MAX_FILES)),
        origin="self_found",
        reason=candidate.get("reason") or "autonomous public GitHub learning candidate",
        question_id=candidate.get("question_id") or "github-autonomous-learning",
        title=candidate.get("full_name") or "",
        label="github-" + clean_token(candidate.get("full_name") or candidate.get("url"), default="repo"),
        stage=True,
        curated=curated,
        root=str(root),
    )
    with contextlib.redirect_stdout(io.StringIO()):
        command_github(args)
    after = load_manifest(root)
    new_items = [item for item in after if str(item.get("id")) not in before_ids]
    item = new_items[-1] if new_items else {}
    if not item:
        for entry in reversed(after):
            url = str(entry.get("source_url") or "")
            if allowed_github_repo_url(url) and canonical_repo_url(url) == candidate["url"]:
                item = entry
                break
    learning_item_id = str(item.get("id") or "")
    return {
        "learning_item_id": learning_item_id or "none",
        "material_id": material_id_for_learning_item(root, learning_item_id) or "none",
    }


def merge_candidate(
    candidates: list[dict[str, str]],
    item: dict[str, str],
    *,
    updated_at: str,
) -> tuple[dict[str, str], bool]:
    by_url = {candidate.get("url"): candidate for candidate in candidates}
    existing = by_url.get(item["url"])
    if existing:
        existing["last_seen_at"] = updated_at
        for key in ("stars", "pushed_at", "description", "language"):
            if item.get(key):
                existing[key] = item[key]
        return existing, False
    item = dict(item)
    item["candidate_id"] = next_candidate_id(candidates, updated_at[:10])
    candidates.append(item)
    return item, True


def render_state(
    checked_at: str,
    mode: str,
    status: str,
    permission_reason: str,
    queries_checked: int,
    candidates_found: int,
    candidates_recorded: int,
    staged_repos: int,
    skipped_reason: str,
    latest_repo: str,
) -> str:
    return f"""---
title: GitHub Learning State
memory_type: github_learning_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: github_autonomous_learning_engine
created_at: 2026-05-06T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 80
impact_score: 80
confidence_score: 100
status: active
tags: [github, learning, autonomy, read-only]
---

# GitHub Learning State

## Last GitHub Pass
- checked_at: {checked_at}
- mode: {mode}
- status: {status}
- permission_reason: {permission_reason}
- queries_checked: {queries_checked}
- candidates_found: {candidates_found}
- candidates_recorded: {candidates_recorded}
- staged_repos: {staged_repos}
- skipped_reason: {skipped_reason}
- latest_repo: {one_line(latest_repo, limit=220)}

## Boundaries
- public_github_only: true
- read_only: true
- no_private_repo_or_token_access: true
- no_clone: true
- no_code_execution: true
- no_dependency_install: true
- no_push_or_issue_comment: true
- self_found_material_only: true
- source_comparison_required_before_stable_learning: true
- learner_integration_required_before_knowledge_general_changes: true
"""


def append_trace(root: Path, payload: dict[str, Any]) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def cooldown_active(root: Path, checked_at: str, min_interval_seconds: int, *, force: bool) -> tuple[bool, str]:
    if force or min_interval_seconds <= 0:
        return False, "none"
    previous = read_text(root / STATE_REL)
    last = extract_value(previous, "checked_at", "")
    if not last:
        return False, "none"
    try:
        age = datetime.fromisoformat(checked_at).timestamp() - datetime.fromisoformat(last).timestamp()
    except ValueError:
        return False, "none"
    if age < min_interval_seconds:
        return True, f"cooldown_active:{max(0, int(age))}/{min_interval_seconds}"
    return False, "none"


def run_github_autonomous_learning(
    root: Path,
    *,
    checked_at: str | None = None,
    mode: str = "runtime_github_autonomous_learning",
    force: bool = False,
    max_stage: int | None = None,
    min_interval_seconds: int = DEFAULT_MIN_INTERVAL_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, object]:
    root = root.resolve()
    checked_at = checked_at or now_iso()
    allowed, permission_reason = github_autonomy_allowed(root)
    sources = load_sources(root)
    queries_checked = 0
    candidates_found = 0
    candidates_recorded = 0
    staged_repos = 0
    latest_repo = "none"
    latest_staged_repo = ""
    skipped_reason = "none"
    status = "skipped"

    if not allowed:
        skipped_reason = permission_reason
    elif not sources:
        skipped_reason = "no_github_learning_sources"
    else:
        cooling, reason = cooldown_active(root, checked_at, min_interval_seconds, force=force)
        if cooling:
            skipped_reason = reason

    if skipped_reason.startswith("cooldown_active"):
        result = {
            "checked_at": checked_at,
            "status": "skipped",
            "permission_reason": permission_reason,
            "sources": len(sources),
            "queries_checked": 0,
            "candidates_found": 0,
            "candidates_recorded": 0,
            "staged_repos": 0,
            "skipped_reason": skipped_reason,
            "latest_repo": "none",
        }
        append_trace(root, result)
        return result

    existing = split_candidates(read_text(root / CANDIDATES_REL))
    candidates = list(existing)
    duplicate_urls = existing_repo_urls(root, candidates)

    if skipped_reason == "none":
        max_queries = max(0, env_int("XINYU_AUTONOMOUS_GITHUB_MAX_QUERIES", DEFAULT_MAX_QUERIES))
        max_repos = max_stage if max_stage is not None else env_int("XINYU_AUTONOMOUS_GITHUB_MAX_REPOS", DEFAULT_MAX_REPOS)
        endpoint = os.environ.get("XINYU_GITHUB_SEARCH_ENDPOINT", DEFAULT_GITHUB_SEARCH_ENDPOINT).strip() or DEFAULT_GITHUB_SEARCH_ENDPOINT
        selected_sources = sources[:max_queries]
        for source in selected_sources:
            source_candidates: list[dict[str, Any]]
            if source.get("url"):
                source_candidates = [direct_repo_candidate(source)]
            else:
                queries_checked += 1
                try:
                    source_candidates = fetch_github_search(
                        source["query"],
                        endpoint=endpoint,
                        per_page=source_int(source, "per_page", source_int(source, "max_repos", 1)),
                        timeout_seconds=timeout_seconds,
                    )
                except Exception as exc:
                    append_trace(
                        root,
                        {
                            "checked_at": checked_at,
                            "status": "query_error",
                            "source_id": source["source_id"],
                            "error": type(exc).__name__,
                        },
                    )
                    continue
            for raw in source_candidates:
                normalized = normalize_candidate(raw, source, discovered_at=checked_at)
                if normalized is None:
                    continue
                normalized["max_files"] = str(source_int(source, "max_files", DEFAULT_MAX_FILES))
                normalized["max_bytes"] = str(source_int(source, "max_bytes", DEFAULT_MAX_BYTES))
                candidates_found += 1
                item, is_new = merge_candidate(candidates, normalized, updated_at=checked_at)
                if is_new:
                    candidates_recorded += 1
                latest_repo = item.get("full_name", item.get("url", "none"))
                if item["url"] in duplicate_urls:
                    if item.get("stage_status") != "staged":
                        item["stage_status"] = "duplicate"
                    continue
                if staged_repos >= max(0, max_repos):
                    continue
                if source.get("stage", "true").lower() not in ENABLED_VALUES:
                    continue
                try:
                    stage_result = stage_github_candidate(
                        root,
                        item,
                        curated=source.get("curated", "false").lower() in ENABLED_VALUES,
                    )
                    item["status"] = "staged"
                    item["stage_status"] = "staged"
                    item["learning_item_id"] = stage_result["learning_item_id"]
                    item["material_id"] = stage_result["material_id"]
                    item["last_seen_at"] = checked_at
                    duplicate_urls.add(item["url"])
                    staged_repos += 1
                    latest_staged_repo = item.get("full_name", item["url"])
                except Exception as exc:
                    item["stage_status"] = f"failed:{type(exc).__name__}"
                    append_trace(
                        root,
                        {
                            "checked_at": checked_at,
                            "status": "stage_error",
                            "repo": item["url"],
                            "error": type(exc).__name__,
                        },
                    )
        if staged_repos > 0:
            status = "staged"
            if latest_staged_repo:
                latest_repo = latest_staged_repo
        elif candidates_recorded > 0:
            status = "candidates"
        elif candidates_found > 0:
            status = "duplicates"
        else:
            status = "no_results"
            skipped_reason = "no_github_candidates"

    write_text(root / CANDIDATES_REL, render_candidates(checked_at, candidates))
    write_text(
        root / STATE_REL,
        render_state(
            checked_at,
            mode,
            status,
            permission_reason,
            queries_checked,
            candidates_found,
            candidates_recorded,
            staged_repos,
            skipped_reason,
            latest_repo,
        ),
    )
    result = {
        "checked_at": checked_at,
        "status": status,
        "permission_reason": permission_reason,
        "sources": len(sources),
        "queries_checked": queries_checked,
        "candidates_found": candidates_found,
        "candidates_recorded": candidates_recorded,
        "staged_repos": staged_repos,
        "skipped_reason": skipped_reason,
        "latest_repo": latest_repo,
    }
    append_trace(root, result)
    return result


def main() -> int:
    if hasattr(os.sys.stdout, "reconfigure"):
        os.sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run XinYu public GitHub autonomous learning pass.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-stage", type=int, default=None)
    parser.add_argument("--min-interval-seconds", type=int, default=DEFAULT_MIN_INTERVAL_SECONDS)
    args = parser.parse_args()
    result = run_github_autonomous_learning(
        args.root,
        force=args.force,
        max_stage=args.max_stage,
        min_interval_seconds=args.min_interval_seconds,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("GitHub learning:", result["status"])
        print("queries_checked:", result["queries_checked"])
        print("candidates_found:", result["candidates_found"])
        print("staged_repos:", result["staged_repos"])
        print("latest_repo:", result["latest_repo"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
