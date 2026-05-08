from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import xinyu_bridge_action_routes
import xinyu_bridge_learning
import xinyu_bridge_proactive
import xinyu_bridge_v1_routes
from xinyu_bridge_memory_snapshot import memory_snapshot
from xinyu_core_bridge import _memory_snapshot


def main() -> int:
    failures: list[str] = []

    with TemporaryDirectory() as raw_root:
        root = Path(raw_root)
        (root / "nested").mkdir()
        (root / "a.txt").write_text("alpha", encoding="utf-8")
        (root / "nested" / "b.txt").write_text("beta", encoding="utf-8")

        snapshot = memory_snapshot(root)
        if set(snapshot) != {"a.txt", "nested/b.txt"}:
            failures.append(f"memory snapshot keys changed: {sorted(snapshot)}")
        for key, (_, size) in snapshot.items():
            if size <= 0:
                failures.append(f"memory snapshot size missing for {key}")

        missing = memory_snapshot(root / "missing")
        if missing != {}:
            failures.append("memory snapshot missing-root fallback changed")

    aliases = (
        _memory_snapshot,
        xinyu_bridge_action_routes._memory_snapshot,
        xinyu_bridge_learning._memory_snapshot,
        xinyu_bridge_proactive._memory_snapshot,
        xinyu_bridge_v1_routes._memory_snapshot,
    )
    if any(alias is not memory_snapshot for alias in aliases):
        failures.append("bridge memory snapshot aliases no longer delegate")

    if failures:
        print("XinYu bridge memory snapshot smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge memory snapshot smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
