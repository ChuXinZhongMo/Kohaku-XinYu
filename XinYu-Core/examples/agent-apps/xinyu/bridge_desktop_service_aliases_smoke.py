from __future__ import annotations

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_desktop_service import desktop_limit


def main() -> int:
    failures: list[str] = []

    cases = [
        (None, 7, 20),
        ("999", 7, 20),
        ("0", 7, 20),
        (" 12 ", 7, 20),
    ]
    for value, default, maximum in cases:
        runtime_value = XinYuBridgeRuntime._desktop_limit(value, default=default, maximum=maximum)
        service_value = desktop_limit(value, default=default, maximum=maximum)
        if runtime_value != service_value:
            failures.append(f"desktop limit alias changed for {value!r}: {runtime_value} != {service_value}")

    if failures:
        print("XinYu bridge desktop service aliases smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge desktop service aliases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
