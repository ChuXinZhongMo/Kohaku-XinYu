from __future__ import annotations

import re
from urllib.parse import urlparse


ALLOWED_SOURCE_SCHEMES = {"http", "https"}
DEFAULT_SOURCE_REQUEST_FIELDS = (
    "question_id",
    "target",
    "query",
    "url",
    "status",
    "reason",
    "followup_kind",
    "avoid_host",
    "followup_slot",
)
SOURCE_REQUEST_DEFAULTS = {
    "question_id": "none",
    "target": "unknown",
    "query": "none",
    "url": "none",
    "status": "hold",
    "reason": "existing request",
    "followup_kind": "none",
    "avoid_host": "none",
    "followup_slot": "1",
}


def extract_dash_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def is_allowed_source_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ALLOWED_SOURCE_SCHEMES and bool(parsed.netloc)


def split_source_requests(
    text: str,
    *,
    fields: tuple[str, ...] = DEFAULT_SOURCE_REQUEST_FIELDS,
    skip_none_question: bool = True,
) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (request-\d{4}-\d{2}-\d{2}-\d{3}|request-[\w-]+)\n", text)
    requests: list[dict[str, str]] = []
    if len(parts) < 3:
        return requests
    for i in range(1, len(parts), 2):
        request_id = parts[i].strip()
        body = parts[i + 1]
        if request_id == "request-none":
            continue
        item = {"request_id": request_id}
        for field in fields:
            item[field] = extract_dash_value(body, field, SOURCE_REQUEST_DEFAULTS.get(field, "unknown"))
        if skip_none_question and item.get("question_id") == "none":
            continue
        requests.append(item)
    return requests


def split_search_results(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (result-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    results: list[dict[str, str]] = []
    if len(parts) < 3:
        return results
    for i in range(1, len(parts), 2):
        result_id = parts[i].strip()
        body = parts[i + 1]
        item = {"result_id": result_id}
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and ": " in stripped:
                key, value = stripped[2:].split(": ", 1)
                item[key] = value.strip()
        if item.get("url"):
            results.append(item)
    return results


def next_dated_id(existing: list[dict[str, str]], *, id_field: str, prefix: str, date_part: str) -> str:
    numbers: list[int] = []
    for item in existing:
        raw = item.get(id_field, "")
        match = re.match(rf"{re.escape(prefix)}-{re.escape(date_part)}-(\d{{3}})$", raw)
        if match:
            numbers.append(int(match.group(1)))
    return f"{prefix}-{date_part}-{max(numbers, default=0) + 1:03d}"
