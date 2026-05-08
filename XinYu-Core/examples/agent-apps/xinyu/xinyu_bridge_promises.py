from __future__ import annotations

import re

from xinyu_bridge_values import safe_str


_PROMISE_TEXT_SEPARATORS_RE = re.compile(
    r"[\s\uFF0C\u3002\uFF01\uFF1F\u3001\uFF1B\uFF1A,.!?;:<>\u300A\u300B\"'`]+"
)


def compact_promise_text(text: str) -> str:
    return _PROMISE_TEXT_SEPARATORS_RE.sub("", safe_str(text).lower())
