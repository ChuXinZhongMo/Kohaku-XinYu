from __future__ import annotations

from xinyu_bridge_values import as_bool, as_int, as_str_set, compact_text, contains_any, dedupe, optional_int, safe_str
from xinyu_core_bridge import _as_bool, _as_int, _as_str_set, _compact_text, _contains_any, _dedupe, _optional_int, _safe_str


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
    if safe_str(None, "fallback") != "fallback":
        failures.append("bridge safe string default changed")
    if compact_text(" one   two three ", 10) != "one two...":
        failures.append("bridge compact text truncation changed")
    if dedupe(["a", " b ", "a", ""]) != ["a", "b"]:
        failures.append("bridge de-duplication changed")
    if not contains_any("hello world", ("absent", "world")):
        failures.append("bridge contains-any helper changed")

    if _as_bool("on") is not True or _as_int("5", 0) != 5:
        failures.append("core bridge value aliases no longer delegate")
    if _optional_int("9") != 9 or _as_str_set(["x", " y "]) != {"x", "y"}:
        failures.append("core bridge collection aliases no longer delegate")
    if _safe_str(None, "fallback") != "fallback" or _compact_text("abcdef", 5) != "ab...":
        failures.append("core bridge text aliases no longer delegate")
    if _dedupe(["x", "x", " y "]) != ["x", "y"] or not _contains_any("abc", ("z", "b")):
        failures.append("core bridge list aliases no longer delegate")

    if failures:
        print("XinYu bridge values smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge values smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
