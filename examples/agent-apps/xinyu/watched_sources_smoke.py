from __future__ import annotations

import functools
import http.server
import tempfile
import threading
from pathlib import Path

from xinyu_watched_sources import run_watched_source_check


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


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-watch-sources-") as tmp:
        tmp_path = Path(tmp)
        fixture = tmp_path / "fixture"
        root = tmp_path / "root"
        fixture.mkdir(parents=True)
        server, thread, base_url = _start_fixture_server(fixture)
        source_url = base_url + "/latest"
        feed_url = base_url + "/latest.rss"
        (fixture / "latest.rss").write_text(
            f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
<title>Fixture Latest</title>
<item>
<title>Agent memory design for LLM tools</title>
<link>{base_url}/t/first-topic/1</link>
<category>AI</category>
<pubDate>Sat, 02 May 2026 07:40:00 GMT</pubDate>
<description><![CDATA[<p>Readable Agent and tool use fixture summary.</p>]]></description>
</item>
<item>
<title>Wireless mouse battery complaint</title>
<link>{base_url}/t/second-topic/2</link>
<category>Community</category>
<pubDate>Sat, 02 May 2026 07:30:00 GMT</pubDate>
<description><![CDATA[<p>Readable non-AI fixture summary.</p>]]></description>
</item>
<item>
<title>RAG context window tuning with OpenAI API</title>
<link>{base_url}/t/third-topic/3</link>
<category>Development</category>
<pubDate>Sat, 02 May 2026 07:20:00 GMT</pubDate>
<description><![CDATA[<p>Readable vector retrieval and API fixture summary.</p>]]></description>
</item>
</channel>
</rss>
""",
            encoding="utf-8",
        )
        try:
            _write(
                root / "memory/context/watch_sources.md",
                f"""# Watch Sources

## linux-do-latest
- enabled: true
- url: {source_url}
- feed_url: {feed_url}
- source_kind: discourse_latest
- topic_filter: ai_related
- include_keywords: AI|LLM|OpenAI|Agent|RAG|API|人工智能|大模型|智能体|工具调用
- cadence_seconds: 1800
- max_items: 8
- read_only: true
- no_posting: true
- site_policy: read_only_no_posting_no_ai_generated_forum_content
""",
            )
            protected = [
                root / "memory/self/core.md",
                root / "memory/people/owner.md",
                root / "memory/relationships/index.md",
                root / "memory/emotions/current_state.md",
            ]
            for path in protected:
                _write(path, f"stable {path.name}")
            before = {path: _read(path) for path in protected}

            result = run_watched_source_check(
                root,
                checked_at="2026-05-02T16:30:00+08:00",
                force=True,
            )
            state = _read(root / "memory/context/watched_source_state.md")
            trace = _read(root / "runtime/watched_source_trace.jsonl")
            if result["status"] != "fetched":
                failures.append(f"watcher did not fetch fixture source: {result}")
            if result["scanned_items"] != 3 or result["matched_items"] != 2 or result["ignored_items"] != 1:
                failures.append(f"unexpected filter counts: {result}")
            if result["fetched_items"] != 2 or result["new_items"] != 2:
                failures.append(f"unexpected item counts: {result}")
            for marker in (
                "source_id: linux-do-latest",
                f"source_url: {source_url}",
                "feed_url:",
                "filter_topic: ai_related",
                "scanned_items: 3",
                "matched_items: 2",
                "ignored_items: 1",
                "Agent memory design for LLM tools",
                "RAG context window tuning with OpenAI API",
                "read_only: true",
                "no_posting: true",
                "no_ai_generated_forum_content: true",
                "no_stable_memory_write: true",
                "no_qq_message_from_watcher: true",
                "candidate_learning_only: true",
                "learning_gate_required: true",
            ):
                if marker not in state:
                    failures.append(f"watched source state missing marker: {marker}")
            if "Wireless mouse battery complaint" in state:
                failures.append("non-AI topic leaked into prompt-visible watched items")
            if "Agent memory design for LLM tools" not in trace:
                failures.append("watched source trace missing latest title")
            for path, text in before.items():
                if _read(path) != text:
                    failures.append(f"watcher changed protected file: {path}")
            if (root / "memory/context/qq_outbox_queue.json").exists():
                failures.append("watcher created QQ outbox")

            second = run_watched_source_check(
                root,
                checked_at="2026-05-02T16:40:00+08:00",
                force=True,
            )
            if second["status"] != "fetched" or second["new_items"] != 0:
                failures.append(f"second force run should see no new fixture items: {second}")

            skipped = run_watched_source_check(
                root,
                checked_at="2026-05-02T16:45:00+08:00",
                force=False,
            )
            if skipped["status"] != "skipped_cooldown":
                failures.append(f"cooldown skip did not trigger: {skipped}")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    source_root = Path(__file__).resolve().parent
    core_text = _read(source_root / "xinyu_core_bridge.py")
    context_text = _read(source_root / "xinyu_runtime_context.py")
    if "run_watched_source_check(" not in core_text:
        failures.append("xinyu_core_bridge.py does not run watched source sidecar")
    if "memory/context/watched_source_state.md" not in context_text:
        failures.append("runtime context does not include watched_source_state")

    if failures:
        print("Watched sources smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Watched sources smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
