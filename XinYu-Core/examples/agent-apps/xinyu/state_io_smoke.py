from __future__ import annotations

import tempfile
from pathlib import Path

from state_service import append_jsonl, atomic_write_json, atomic_write_text, read_json
from xinyu_state_io import append_section, extract_value, one_line, read_text, replace_field, write_text_atomic


def main() -> int:
    failures: list[str] = []
    text = "# State\n- status: old\n"
    if extract_value(text, "status") != "old":
        failures.append("extract_value did not read existing field")
    replaced = replace_field(text, "status", "new value")
    if "- status: new value" not in replaced:
        failures.append("replace_field did not replace existing field")
    added = replace_field(replaced, "mode", "runtime")
    if "- mode: runtime" not in added:
        failures.append("replace_field did not append missing field")
    sectioned = append_section(added, "## Notes", "- checked")
    if "## Notes\n- checked" not in sectioned:
        failures.append("append_section did not append body")
    if one_line("a\n  b\tc") != "a b c":
        failures.append("one_line did not normalize whitespace")

    with tempfile.TemporaryDirectory(prefix="xinyu-state-io-smoke-") as tmp:
        target = Path(tmp) / "state.md"
        write_text_atomic(target, sectioned)
        if read_text(target) != sectioned:
            failures.append("write_text_atomic/read_text round trip failed")

        service_text = Path(tmp) / "service" / "state.md"
        atomic_write_text(service_text, "status: ok")
        if service_text.read_text(encoding="utf-8") != "status: ok\n":
            failures.append("state_service atomic_write_text failed")

        service_json = Path(tmp) / "service" / "state.json"
        atomic_write_json(service_json, {"b": 2, "a": 1})
        if read_json(service_json) != {"a": 1, "b": 2}:
            failures.append("state_service atomic_write_json/read_json failed")

        service_jsonl = Path(tmp) / "service" / "trace.jsonl"
        append_jsonl(service_jsonl, {"event": "one", "value": 1})
        append_jsonl(service_jsonl, {"event": "two", "value": 2})
        rows = [line for line in service_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(rows) != 2 or '"event":"one"' not in rows[0] or '"event":"two"' not in rows[1]:
            failures.append("state_service append_jsonl failed")

    if failures:
        print("state_io_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("state_io_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
