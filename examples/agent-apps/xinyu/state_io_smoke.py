from __future__ import annotations

import tempfile
from pathlib import Path

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

    if failures:
        print("state_io_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("state_io_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
