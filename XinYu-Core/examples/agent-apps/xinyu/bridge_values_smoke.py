from __future__ import annotations

from xinyu_bridge_values import as_bool, as_int, as_str_set, optional_int
from xinyu_core_bridge import _as_bool, _as_int, _as_str_set, _optional_int


def main() -> int:
    failures: list[str] = []

    if as_bool("yes") is not True or as_bool("false", default=True) is not False:
        failures.append("bridge bool parsing changed")
    if as_bool(None, default=True) is not True:
        failures.append("bridge bool default changed")
    if as_int(" 42 ", 0) != 42 or as_int("bad", 7) != 7:
        failures.append("bridge int parsing changed")
    if optional_int("") is not None or optional_int("12") != 12 or optional_int("bad") is not None:
        failures.append("bridge optional int parsing changed")
    if as_str_set(" a,b; c ,,") != {"a", "b", "c"}:
        failures.append("bridge string set parsing changed")

    if _as_bool("on") is not True or _as_int("5", 0) != 5:
        failures.append("core bridge value aliases no longer delegate")
    if _optional_int("9") != 9 or _as_str_set(["x", " y "]) != {"x", "y"}:
        failures.append("core bridge collection aliases no longer delegate")

    if failures:
        print("XinYu bridge values smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge values smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
