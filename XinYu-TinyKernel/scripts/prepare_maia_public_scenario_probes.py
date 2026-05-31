from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from common import CONFIG_DIR, DATA_DIR, PROJECT_ROOT, dump_json, load_json, write_jsonl


DEFAULT_CONFIG = CONFIG_DIR / "maia_public_scenario_sources.json"
DEFAULT_OUT = DATA_DIR / "probes" / "maia_public_scenario_probes_v001.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "eval" / "reports" / "maia_public_scenario_probe_prep_v001.json"

PRIVATE_PATTERNS = {
    "windows_path": re.compile(r"[A-Za-z]:\\[^\s\"']+"),
    "unix_private_path": re.compile(r"/(?:Users|home)/[^\s\"']+"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "secret_assignment": re.compile(r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}"),
    "email": re.compile(r"(?i)[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}"),
    "phone_like": re.compile(r"(?<!\d)(?:\+?\d[\d\s\-]{7,}\d)(?!\d)"),
    "url": re.compile(r"https?://[^\s\"']+"),
    "private_file": re.compile(r"(?i)(\.env|\.xinyu_bridge_token)"),
    "auth_term": re.compile(r"(?i)\b(api[_ -]?key|bearer token|auth token|access token|cookie|cookies|password|secret)\b"),
}

FAMILY_PATTERNS = [
    ("wait_candidate", re.compile(r"(?i)\b(wait|pause|stop|hold on|do not continue)\b|先等|暂停|停一下|别继续")),
    ("memory_candidate_probe", re.compile(r"(?i)\b(remember|memorize|for future|from now on)\b|记住|以后|长期|偏好|别忘")),
    ("status_probe_candidate", re.compile(r"(?i)\b(status|progress|running|check whether|is .* done)\b|状态|进度|是否完成|还在不在|跑完")),
    ("codex_or_tool_probe", re.compile(r"(?i)\b(run|execute|shell|script|implement|edit|fix|test|debug|commit)\b|运行|执行|脚本|实现|修改|修复|测试|调试")),
    ("clarify_candidate", re.compile(r"(?i)^(that|this|it|continue|fix it|do that)\b|^这个|^那个|继续那个|修一下$")),
    ("local_only_or_external_probe", re.compile(r"(?i)\b(api|network|browser|internet|download|file path|login)\b|联网|下载|浏览器|登录|文件路径")),
]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def compact_space(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def sanitize_text(text: Any, *, max_chars: int) -> tuple[str, list[str]]:
    value = compact_space(text)
    replacements: list[str] = []
    for name, pattern in PRIVATE_PATTERNS.items():
        if pattern.search(value):
            replacements.append(name)
            token = "<url>" if name == "url" else f"<{name}>"
            value = pattern.sub(token, value)
    value = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    value = compact_space(value)
    if len(value) > max_chars:
        value = value[: max_chars - 3].rstrip() + "..."
        replacements.append("truncated")
    return value, sorted(set(replacements))


def first_text(row: dict[str, Any], keys: Iterable[str]) -> str:
    parts: list[str] = []
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(clean_public_html(value))
    return "\n".join(parts)


def clean_public_html(value: str) -> str:
    text = re.sub(r"(?is)<(pre|code)[^>]*>.*?</\1>", " <code_removed> ", value)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return html.unescape(compact_space(text))


def source_record_id(row: dict[str, Any], keys: Iterable[str], fallback_text: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return text_hash(str(value))
    return text_hash(fallback_text)


def language_for(row: dict[str, Any], source: dict[str, Any], text: str) -> str:
    field = source.get("ingestion", {}).get("language_field")
    if field and row.get(field):
        return str(row.get(field))
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    return "en"


def row_matches(row: dict[str, Any], source: dict[str, Any]) -> bool:
    ingestion = source.get("ingestion", {})
    for key, expected in dict(ingestion.get("equals") or {}).items():
        if row.get(key) != expected:
            return False
    for key in list(ingestion.get("is_null") or []):
        if row.get(key) not in (None, ""):
            return False
    languages = set(str(item) for item in ingestion.get("languages") or [])
    lang_field = ingestion.get("language_field")
    if languages and lang_field and row.get(lang_field) and str(row.get(lang_field)) not in languages:
        return False
    return True


def scenario_family(text: str) -> str:
    probe = text.strip()
    if len(probe) < 12:
        return "clarify_candidate"
    for name, pattern in FAMILY_PATTERNS:
        if pattern.search(probe):
            return name
    if "?" in probe or "？" in probe:
        return "reply_question_probe"
    return "reply_instruction_probe"


def refine_family(source: dict[str, Any], row: dict[str, Any], text: str) -> str:
    if str(source.get("id")) == "cped":
        emotion = str(row.get("Emotion") or "unknown").replace("-", "_")
        return f"zh_emotion_{emotion}_probe"
    return scenario_family(text)


def refine_domain(source: dict[str, Any], row: dict[str, Any], text: str) -> str:
    base = str(source.get("scenario_domain") or source.get("id") or "unknown")
    if str(source.get("id")) == "cped":
        emotion = str(row.get("Emotion") or "unknown").replace("-", "_")
        return f"zh_emotion_{emotion}"
    if str(source.get("id")) != "crosswoz":
        return base
    domain_keywords = {
        "zh_travel_attraction": ["景点", "门票", "游玩", "地址"],
        "zh_restaurant": ["餐馆", "餐厅", "菜", "营业时间", "人均消费"],
        "zh_hotel": ["酒店", "住宿", "价格", "评分", "房"],
        "zh_transport": ["地铁", "出租车", "打车", "路线", "出发", "到达"],
    }
    hits = [name for name, words in domain_keywords.items() if any(word in text for word in words)]
    if not hits:
        return base
    if len(hits) == 1:
        return hits[0]
    return "zh_multi_service"


def load_huggingface_rows(source: dict[str, Any], *, needed: int) -> Iterable[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(f"datasets dependency unavailable: {exc}") from exc

    ingestion = source.get("ingestion", {})
    dataset_name = str(source["dataset"])
    split = str(source.get("split") or "train")
    streaming = bool(ingestion.get("streaming", True))
    ds = load_dataset(dataset_name, split=split, streaming=streaming, trust_remote_code=False)
    count = 0
    for row in ds:
        if isinstance(row, dict):
            yield row
            count += 1
            if count >= needed * 20:
                break


def iter_crosswoz_local(source: dict[str, Any]) -> Iterable[dict[str, Any]]:
    pattern = PROJECT_ROOT / str(source.get("ingestion", {}).get("local_glob", "")).replace("\\", "/")
    for path in pattern.parent.glob(pattern.name):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        dialogs = data.values() if isinstance(data, dict) else data
        for dialog_index, item in enumerate(dialogs):
            if not isinstance(item, dict):
                continue
            messages = item.get("messages") or item.get("message") or []
            yielded_message = False
            if isinstance(messages, list):
                for message_index, message in enumerate(messages):
                    if isinstance(message, dict) and str(message.get("role", "")).lower() in {"user", "usr"}:
                        content = str(message.get("content") or "").strip()
                        if content:
                            yield {
                                "content": content,
                                "record_path": str(path),
                                "dialog_index": dialog_index,
                                "message_index": message_index,
                            }
                            yielded_message = True
                if yielded_message:
                    continue
            task_desc = item.get("task description") or item.get("task_description")
            if isinstance(task_desc, list):
                task_desc = " ".join(str(part) for part in task_desc if str(part).strip())
            if task_desc:
                yield {"content": str(task_desc), "record_path": str(path), "dialog_index": dialog_index}


def iter_manual_jsonl(source: dict[str, Any]) -> Iterable[dict[str, Any]]:
    pattern_text = str(source.get("ingestion", {}).get("local_glob", "")).replace("\\", "/")
    if not pattern_text:
        return
    pattern = PROJECT_ROOT / pattern_text
    for path in pattern.parent.glob(pattern.name):
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                value = json.loads(line)
                if isinstance(value, dict):
                    yield value


def iter_cped_local_csv(source: dict[str, Any], *, needed: int) -> Iterable[dict[str, Any]]:
    pattern_text = str(source.get("ingestion", {}).get("local_glob", "")).replace("\\", "/")
    if not pattern_text:
        return
    pattern = PROJECT_ROOT / pattern_text
    buckets: dict[str, list[dict[str, Any]]] = {}
    for path in pattern.parent.glob(pattern.name):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                text = compact_space(row.get("Utterance") or "")
                if len(text) < 6 or len(text) > 220:
                    continue
                emotion = str(row.get("Emotion") or "unknown")
                if source.get("ingestion", {}).get("prefer_non_neutral") and emotion == "neutral":
                    continue
                row = dict(row)
                row["content"] = text
                row["record_path"] = str(path)
                buckets.setdefault(emotion, []).append(row)

    if not buckets:
        return
    emotions = sorted(buckets, key=lambda item: (-len(buckets[item]), item))
    emitted = 0
    index = 0
    while emitted < needed:
        progressed = False
        for emotion in emotions:
            rows = buckets[emotion]
            if index < len(rows):
                yield rows[index]
                emitted += 1
                progressed = True
                if emitted >= needed:
                    return
        if not progressed:
            return
        index += 1


def iter_stackexchange_api(source: dict[str, Any], *, needed: int) -> Iterable[dict[str, Any]]:
    ingestion = source.get("ingestion", {})
    base_url = "https://api.stackexchange.com/2.3/questions"
    pagesize = min(100, max(1, int(ingestion.get("pagesize") or needed or 50)))
    params = {
        "order": str(ingestion.get("order") or "desc"),
        "sort": str(ingestion.get("sort") or "activity"),
        "site": str(ingestion.get("site") or "stackoverflow"),
        "pagesize": str(pagesize),
        "filter": str(ingestion.get("filter") or "withbody"),
    }
    yielded = 0
    page = 1
    while yielded < needed and page <= 6:
        params["page"] = str(page)
        url = base_url + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": "XinYuTinyKernelPublicProbe/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for item in payload.get("items") or []:
            if isinstance(item, dict):
                yield item
                yielded += 1
                if yielded >= needed:
                    return
        if not payload.get("has_more"):
            return
        page += 1


def iter_source_rows(source: dict[str, Any], *, needed: int) -> Iterable[dict[str, Any]]:
    ingestion_type = str(source.get("ingestion", {}).get("type") or "")
    if ingestion_type == "huggingface_dataset":
        yield from load_huggingface_rows(source, needed=needed)
    elif ingestion_type == "stackexchange_api":
        yield from iter_stackexchange_api(source, needed=needed)
    elif ingestion_type == "crosswoz_local_json":
        yield from iter_crosswoz_local(source)
    elif ingestion_type == "manual_jsonl":
        yield from iter_manual_jsonl(source)
    elif ingestion_type == "cped_local_csv":
        yield from iter_cped_local_csv(source, needed=needed)
    elif ingestion_type == "blocked":
        return
    else:
        raise RuntimeError(f"unsupported ingestion type for {source.get('id')}: {ingestion_type}")


def build_probe_row(
    *,
    source: dict[str, Any],
    row: dict[str, Any],
    clean_text: str,
    replacements: list[str],
    ordinal: int,
) -> dict[str, Any]:
    ingestion = source.get("ingestion", {})
    family = refine_family(source, row, clean_text)
    lang = language_for(row, source, clean_text)
    source_id = str(source["id"])
    domain = refine_domain(source, row, clean_text)
    record_id = source_record_id(row, ingestion.get("id_keys") or [], clean_text)
    return {
        "id": f"maia-public-probe-v001-{ordinal:06d}",
        "kind": "maia_public_scenario_probe",
        "source": source_id,
        "source_dataset": source.get("dataset"),
        "source_license": source.get("license"),
        "source_url": source.get("source_url"),
        "license_url": source.get("license_url"),
        "use_scope": source.get("use_scope"),
        "source_record_hash": record_id,
        "input_hash": text_hash(clean_text),
        "language": lang,
        "scenario_domain": domain,
        "scenario_family": family,
        "user_text": clean_text,
        "sanitization": {
            "status": "sanitized_public_prompt",
            "replacements": replacements,
            "assistant_answer_used": False,
            "private_data_expected": False,
        },
        "public_metadata": public_metadata_for(source, row),
        "attribution": attribution_for(source, row),
        "review": {
            "status": "needs_xinyu_shadow_reaction_review",
            "expected_mode": None,
            "notes": [
                "oracle_free_probe",
                "do_not_train_until_reviewed",
            ],
        },
        "tags": [
            "maia_public_scenario_probe",
            family,
            domain,
            lang,
            source_id,
        ],
    }


def public_metadata_for(source: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    if str(source.get("id")) != "cped":
        return {}
    keys = ["Scene", "Sentiment", "Emotion", "DA", "Gender", "Age"]
    return {key.lower(): str(row.get(key) or "") for key in keys if row.get(key)}


def attribution_for(source: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    attribution = {
        "source_url": source.get("source_url"),
        "license": source.get("license"),
        "license_url": source.get("license_url"),
    }
    link = row.get("link")
    question_id = row.get("question_id")
    if link and question_id and source.get("provider") == "stackexchange_api":
        parsed = urllib.parse.urlparse(str(link))
        if parsed.netloc:
            attribution["item_url"] = f"{parsed.scheme or 'https'}://{parsed.netloc}/q/{question_id}"
    elif link:
        attribution["item_url"] = str(link)
    owner = row.get("owner")
    if isinstance(owner, dict) and owner.get("display_name"):
        attribution["author_display_name"] = clean_public_html(str(owner.get("display_name")))
    return attribution


def selected_sources(config: dict[str, Any], names: list[str], *, include_candidates: bool) -> list[dict[str, Any]]:
    all_sources = list(config.get("sources") or [])
    if names:
        wanted = set(names)
        return [source for source in all_sources if source.get("id") in wanted]
    allowed = {
        "allowed_probe_source",
        "allowed_probe_source_after_local_download",
        "allowed_probe_source_with_attribution",
    }
    if include_candidates:
        allowed |= {
            "candidate_requires_attribution_manifest",
            "candidate_requires_per_row_attribution",
        }
    return [
        source
        for source in all_sources
        if source.get("enabled_by_default") and source.get("status") in allowed
    ]


def build_probes(
    config: dict[str, Any],
    *,
    source_names: list[str],
    limit_per_source: int,
    max_chars: int,
    include_candidates: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    skipped: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    source_errors: dict[str, str] = {}

    for source in selected_sources(config, source_names, include_candidates=include_candidates):
        source_id = str(source.get("id"))
        accepted = 0
        try:
            rows = iter_source_rows(source, needed=limit_per_source)
            for row in rows:
                if accepted >= limit_per_source:
                    break
                if not row_matches(row, source):
                    skipped["filter_mismatch"] = skipped.get("filter_mismatch", 0) + 1
                    continue
                text = first_text(row, source.get("ingestion", {}).get("text_keys") or [])
                clean, replacements = sanitize_text(text, max_chars=max_chars)
                if len(clean) < 8:
                    skipped["too_short"] = skipped.get("too_short", 0) + 1
                    continue
                text_key = clean.lower()
                if text_key in seen_text:
                    skipped["duplicate"] = skipped.get("duplicate", 0) + 1
                    continue
                seen_text.add(text_key)
                probe = build_probe_row(
                    source=source,
                    row=row,
                    clean_text=clean,
                    replacements=replacements,
                    ordinal=len(probes) + 1,
                )
                probes.append(probe)
                accepted += 1
                source_counts[source_id] = source_counts.get(source_id, 0) + 1
                family = str(probe["scenario_family"])
                family_counts[family] = family_counts.get(family, 0) + 1
        except Exception as exc:
            source_errors[source_id] = f"{type(exc).__name__}: {exc}"

    report = {
        "status": "prepared" if probes else "no_rows",
        "probe_count": len(probes),
        "source_counts": source_counts,
        "family_counts": family_counts,
        "skipped": skipped,
        "source_errors": source_errors,
        "raw_private_data_used": False,
        "assistant_answers_used": False,
        "training_targets_created": False,
        "shadow_only": True,
    }
    return probes, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--limit-per-source", type=int, default=40)
    parser.add_argument("--max-chars", type=int, default=360)
    parser.add_argument("--include-candidates", action="store_true")
    parser.add_argument("--list-sources", action="store_true")
    args = parser.parse_args()

    config = load_json(Path(args.config))
    if args.list_sources:
        for source in config.get("sources") or []:
            print(
                f"{source.get('id')}\t{source.get('status')}\t"
                f"default={source.get('enabled_by_default')}\t{source.get('license')}"
            )
        return 0

    probes, report = build_probes(
        config,
        source_names=list(args.source or []),
        limit_per_source=args.limit_per_source,
        max_chars=args.max_chars,
        include_candidates=bool(args.include_candidates),
    )
    out_path = Path(args.out)
    report_path = Path(args.report)
    written = write_jsonl(out_path, probes)
    report.update(
        {
            "output": str(out_path),
            "report": str(report_path),
            "config": str(args.config),
            "limit_per_source": args.limit_per_source,
        }
    )
    dump_json(report_path, report)
    print(f"probe_count={written}")
    print("source_counts=" + json.dumps(report["source_counts"], ensure_ascii=False, sort_keys=True))
    print("family_counts=" + json.dumps(report["family_counts"], ensure_ascii=False, sort_keys=True))
    if report["source_errors"]:
        print("source_errors=" + json.dumps(report["source_errors"], ensure_ascii=False, sort_keys=True))
    print(f"out={out_path}")
    print(f"report={report_path}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
