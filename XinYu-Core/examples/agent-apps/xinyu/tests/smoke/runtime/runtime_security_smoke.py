from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import os
from contextlib import contextmanager

from xinyu_runtime_security import enforce_bridge_token_guard, enforce_llm_http_guard


@contextmanager
def env_patch(**values: str):
    old = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value == "":
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def expect_error(func, label: str, failures: list[str]) -> None:
    try:
        func()
    except RuntimeError:
        return
    failures.append(f"{label} did not fail")


def main() -> int:
    failures: list[str] = []
    with env_patch(
        XINYU_API_KEY="test-key",
        XINYU_BASE_URL="http://example.test/v1",
        XINYU_ALLOW_INSECURE_LLM_HTTP="",
    ):
        expect_error(enforce_llm_http_guard, "http+api-key without override", failures)
    with env_patch(
        XINYU_API_KEY="test-key",
        XINYU_BASE_URL="http://example.test/v1",
        XINYU_ALLOW_INSECURE_LLM_HTTP="1",
    ):
        enforce_llm_http_guard()
    with env_patch(
        XINYU_API_KEY="test-key",
        XINYU_BASE_URL="https://example.test/v1",
        XINYU_ALLOW_INSECURE_LLM_HTTP="",
    ):
        enforce_llm_http_guard()

    enforce_bridge_token_guard("127.0.0.1", "")
    enforce_bridge_token_guard("localhost", "")
    enforce_bridge_token_guard("0.0.0.0", "token")
    expect_error(lambda: enforce_bridge_token_guard("0.0.0.0", ""), "non-loopback no token", failures)

    if failures:
        print("runtime_security_smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("runtime_security_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
