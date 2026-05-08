from __future__ import annotations

import os
import tempfile
from pathlib import Path

from xinyu_qq_config import (
    as_bool,
    as_float,
    as_int,
    as_str_list,
    env_str_list,
    load_json_object,
    merge_str_lists,
    with_required_prefixes,
)


def main() -> int:
    failures: list[str] = []

    if as_bool("yes") is not True or as_bool("0") is not False or as_bool(None, default=True) is not True:
        failures.append("as_bool compatibility changed")
    if as_int("42", 0) != 42 or as_int("bad", 7) != 7:
        failures.append("as_int compatibility changed")
    if as_float("1.25", 0.0) != 1.25 or as_float("bad", 0.5) != 0.5:
        failures.append("as_float compatibility changed")
    if as_str_list(" one, two ,, ") != ["one", "two"]:
        failures.append("comma string list parsing changed")
    if as_str_list((" a ", 2, "")) != ["a", "2"]:
        failures.append("iterable string list parsing changed")
    if merge_str_lists(["a", "b"], "b,c", None, ["a"]) != ["a", "b", "c"]:
        failures.append("merged string list de-duplication changed")
    if with_required_prefixes(["#"]) != ("#", "/", "!", "\uff01", "."):
        failures.append("required command prefixes changed")

    old_env = {
        "XINYU_QQ_HELPER_SMOKE_A": os.environ.get("XINYU_QQ_HELPER_SMOKE_A"),
        "XINYU_QQ_HELPER_SMOKE_B": os.environ.get("XINYU_QQ_HELPER_SMOKE_B"),
    }
    try:
        os.environ["XINYU_QQ_HELPER_SMOKE_A"] = "u1,u2"
        os.environ["XINYU_QQ_HELPER_SMOKE_B"] = "u2,u3"
        if env_str_list("XINYU_QQ_HELPER_SMOKE_A", "XINYU_QQ_HELPER_SMOKE_B") != ["u1", "u2", "u3"]:
            failures.append("environment string list parsing changed")
    finally:
        for name, value in old_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.json"
        if load_json_object(path) != {}:
            failures.append("missing JSON config should load as empty dict")
        path.write_text('{"enabled": true, "items": ["a"]}', encoding="utf-8")
        if load_json_object(path) != {"enabled": True, "items": ["a"]}:
            failures.append("JSON object loading changed")
        path.write_text('["not", "object"]', encoding="utf-8")
        if load_json_object(path) != {}:
            failures.append("non-object JSON config should load as empty dict")

    if failures:
        print("XinYu QQ config helper smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ config helper smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
