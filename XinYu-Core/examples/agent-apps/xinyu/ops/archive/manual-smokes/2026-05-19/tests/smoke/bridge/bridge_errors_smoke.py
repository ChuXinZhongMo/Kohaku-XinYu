from __future__ import annotations

from http import HTTPStatus

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_errors import BridgeRequestError
from xinyu_core_bridge import BridgeRequestError as CoreBridgeRequestError


def main() -> int:
    failures: list[str] = []

    error = BridgeRequestError(HTTPStatus.BAD_REQUEST, "bad payload")
    if error.status is not HTTPStatus.BAD_REQUEST:
        failures.append("bridge request error status changed")
    if error.message != "bad payload" or str(error) != "bad payload":
        failures.append("bridge request error message changed")
    if CoreBridgeRequestError is not BridgeRequestError:
        failures.append("core bridge request error alias no longer delegates")

    if failures:
        print("XinYu bridge errors smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge errors smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
