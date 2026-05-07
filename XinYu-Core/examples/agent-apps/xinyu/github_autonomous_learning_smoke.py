from __future__ import annotations

import functools
import http.server
import os
import sys
import tempfile
import threading
import zipfile
from pathlib import Path


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def _start_fixture_server(root: Path):
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return server, thread, base_url


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _prepare_root(root: Path, search_url: str) -> None:
    _write(
        root / "memory/context/github_learning_sources.md",
        f"""# GitHub Learning Sources

## fixture-agent-memory
- enabled: true
- query: fixture agent memory language:Python
- question_id: github-fixture-agent-memory
- reason: smoke test public GitHub autonomous learning
- max_repos: 1
- per_page: 1
- min_stars: 0
- max_files: 20
- max_bytes: 5000000
- include_forks: false
- include_archived: false
- stage: true
- curated: false
- search_url: {search_url}
""",
    )
    _write(
        root / "memory/context/capability_zones_state.md",
        """# Capability Zones State

## Zone B Ask Or Thoughts First
- public_github_discovery: enabled_read_only_public_repos
- public_github_learning: enabled_self_found_staged_material_only
""",
    )
    _write(root / "memory/context/owner_permission_grants.md", "# Owner Permission Grants\n")
    _write(root / "memory/knowledge/github_learning_candidates.md", "# GitHub Learning Candidates\n")
    _write(root / "memory/knowledge/general.md", "# General Knowledge\n")
    for rel in (
        "memory/self/narrative.md",
        "memory/people/owner.md",
        "memory/relationships/index.md",
        "memory/emotions/current_state.md",
    ):
        _write(root / rel, f"protected {rel}")


def _write_repo_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "demo-agent-main/README.md",
            """# Demo Agent

This repository demonstrates an agent memory loop, tool routing, cautious source learning,
and public GitHub study material handling.
""",
        )
        archive.writestr(
            "demo-agent-main/main.py",
            "def route_tool(intent):\n    return 'memory' if intent == 'recall' else 'reply'\n",
        )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    failures: list[str] = []
    source_root = Path(__file__).resolve().parent
    custom_dir = source_root / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    with tempfile.TemporaryDirectory(prefix="xinyu-github-learning-") as tmp:
        tmp_path = Path(tmp)
        fixture = tmp_path / "fixture"
        root = tmp_path / "root"
        fixture.mkdir(parents=True)
        archive_path = fixture / "demo-agent.zip"
        _write_repo_zip(archive_path)
        search_payload = {
            "items": [
                {
                    "full_name": "example/demo-agent",
                    "html_url": "https://github.com/example/demo-agent",
                    "description": "Public demo agent memory and tool routing implementation.",
                    "language": "Python",
                    "stargazers_count": 42,
                    "fork": False,
                    "archived": False,
                    "private": False,
                    "pushed_at": "2026-05-01T00:00:00Z",
                }
            ]
        }
        import json

        (fixture / "search.json").write_text(json.dumps(search_payload), encoding="utf-8")
        server, thread, base_url = _start_fixture_server(fixture)
        search_url = base_url + "/search.json"
        archive_url = base_url + "/demo-agent.zip"
        _prepare_root(root, search_url)

        old_env = {
            key: os.environ.get(key)
            for key in (
                "XINYU_AUTONOMOUS_GITHUB",
                "XINYU_AUTONOMOUS_GITHUB_MAX_QUERIES",
                "XINYU_AUTONOMOUS_GITHUB_MAX_REPOS",
                "XINYU_GITHUB_SEARCH_ENDPOINT",
                "XINYU_ALLOW_INTERNAL_LEARNING_URLS",
            )
        }
        os.environ["XINYU_AUTONOMOUS_GITHUB"] = "enabled"
        os.environ["XINYU_AUTONOMOUS_GITHUB_MAX_QUERIES"] = "1"
        os.environ["XINYU_AUTONOMOUS_GITHUB_MAX_REPOS"] = "1"
        os.environ["XINYU_GITHUB_SEARCH_ENDPOINT"] = search_url
        os.environ["XINYU_ALLOW_INTERNAL_LEARNING_URLS"] = "1"

        try:
            import xinyu_learning_library
            from github_autonomous_learning_engine import run_github_autonomous_learning

            original_archives = xinyu_learning_library.github_archive_urls
            xinyu_learning_library.github_archive_urls = lambda owner, repo, branch: [("main", archive_url)]
            before_protected = {
                rel: _read(root / rel)
                for rel in (
                    "memory/self/narrative.md",
                    "memory/people/owner.md",
                    "memory/relationships/index.md",
                    "memory/emotions/current_state.md",
                )
            }
            try:
                result = run_github_autonomous_learning(
                    root,
                    checked_at="2026-05-06T07:00:00+08:00",
                    mode="github_autonomous_learning_smoke",
                    force=True,
                    min_interval_seconds=0,
                )
                first_state = _read(root / "memory/context/github_learning_state.md")
                second = run_github_autonomous_learning(
                    root,
                    checked_at="2026-05-06T07:05:00+08:00",
                    mode="github_autonomous_learning_smoke_second",
                    force=True,
                    min_interval_seconds=0,
                )
            finally:
                xinyu_learning_library.github_archive_urls = original_archives
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

        state = _read(root / "memory/context/github_learning_state.md")
        candidates = _read(root / "memory/knowledge/github_learning_candidates.md")
        source_materials = _read(root / "memory/knowledge/source_materials.md")
        manifest = _read(root / "learning/manifest.jsonl")
        if result["status"] != "staged" or int(result["staged_repos"]) != 1:
            failures.append(f"first run did not stage fixture repo: {result}")
        if int(second["staged_repos"]) != 0:
            failures.append(f"second run should not restage duplicate repo: {second}")
        for marker in (
            "status: staged",
        ):
            if marker not in first_state:
                failures.append(f"first github state missing marker: {marker}")
        for marker in (
            "public_github_only: true",
            "no_code_execution: true",
            "source_comparison_required_before_stable_learning: true",
        ):
            if marker not in state:
                failures.append(f"github state missing marker: {marker}")
        for marker in (
            "example/demo-agent",
            "https://github.com/example/demo-agent",
            "stage_status: staged",
            "learning_item_id: learn-",
            "material_id: material-",
        ):
            if marker not in candidates:
                failures.append(f"github candidates missing marker: {marker}")
        for marker in (
            "- source_type: github_repository",
            "- learning_origin: self_found",
            "- comparison_status: not_compared",
            "- extraction_status: readable_text",
            "Demo Agent",
        ):
            if marker not in source_materials:
                failures.append(f"source material missing marker: {marker}")
        if '"kind": "github_repo"' not in manifest:
            failures.append("learning manifest missing github_repo item")
        for rel, before in before_protected.items():
            if _read(root / rel) != before:
                failures.append(f"protected memory changed: {rel}")
        if (root / "memory/context/qq_outbox_queue.json").exists():
            failures.append("github learning created QQ outbox")

    if failures:
        print("GitHub autonomous learning smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("GitHub autonomous learning smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
