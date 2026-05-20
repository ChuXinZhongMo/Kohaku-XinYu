from __future__ import annotations

import json
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "failure-scenarios" / "generate_sanitized_trace_examples.py"


spec = importlib.util.spec_from_file_location("generate_sanitized_trace_examples", GENERATOR_PATH)
assert spec is not None and spec.loader is not None
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_research_docs_exist_and_cross_link() -> None:
    required = [
        "INTERACTIVITY-RESEARCH.md",
        "TRACE-SCHEMA.md",
        "FAILURE-SCENARIOS.md",
        "ARCHITECTURE.md",
        "LOCAL-INSPECTOR-DEMO.md",
        "GRANT-PROGRESS-REPORT-TEMPLATE.md",
        "README.en.md",
        "README.ja.md",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel

    readme = _read("README.md")
    assert "README.en.md" in readme
    assert "README.ja.md" in readme
    assert "INTERACTIVITY-RESEARCH.md" in readme
    assert "/turn/current" in _read("ARCHITECTURE.md")
    assert "proactive_ack_recorded" in _read("TRACE-SCHEMA.md")
    assert "failure-scenarios/" in _read("FAILURE-SCENARIOS.md")


def test_generated_sanitized_trace_examples_are_current_and_private_safe() -> None:
    generated = generator.generate_rows(ROOT / "failure-scenarios" / "scenarios")
    existing = [
        json.loads(line)
        for line in (ROOT / "failure-scenarios/examples/sanitized_trace_examples.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    assert existing == generated
    assert len(existing) >= 7
    text = json.dumps(existing, ensure_ascii=False)
    for forbidden in ("26921", "ChuXinZhongMo", "D:\\", "C:\\Users"):
        assert forbidden not in text
