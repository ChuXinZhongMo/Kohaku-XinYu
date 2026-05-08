from __future__ import annotations

import xinyu_qq_attachment_resolver
import xinyu_qq_config
import xinyu_qq_gateway


def main() -> int:
    failures: list[str] = []

    if xinyu_qq_gateway.COMMAND_PREFIX_CHARS != xinyu_qq_config.COMMAND_PREFIX_CHARS:
        failures.append("gateway command prefix constant no longer re-exports config owner")
    if xinyu_qq_gateway.SUPPORTED_IMAGE_SUFFIXES != xinyu_qq_attachment_resolver.SUPPORTED_IMAGE_SUFFIXES:
        failures.append("gateway image suffix constant no longer re-exports attachment owner")

    if failures:
        print("XinYu QQ gateway constants smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ gateway constants smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
