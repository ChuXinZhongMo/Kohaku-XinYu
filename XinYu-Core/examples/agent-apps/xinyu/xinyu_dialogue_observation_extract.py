from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


SUPPORTED_EXTS = {".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".docx"}
DEFAULT_MAX_FILE_BYTES = 2_000_000
DEFAULT_MAX_CANDIDATES = 300

TEXT_KEYS = {"text", "line", "dialogue", "utterance", "message", "content", "reply"}
SPEAKER_KEYS = {"speaker", "character", "name", "role", "actor"}

USEFUL_MARKERS: dict[str, tuple[str, ...]] = {
    "remembered_detail": (
        "记得",
        "上次",
        "之前",
        "以前",
        "那时候",
        "last time",
        "remember",
        "before",
    ),
    "repair": (
        "对不起",
        "抱歉",
        "不是这个",
        "别这样",
        "算了",
        "没事",
        "sorry",
        "apolog",
        "my fault",
    ),
    "low_mood": (
        "累",
        "难过",
        "失望",
        "害怕",
        "孤独",
        "心情不好",
        "不想说",
        "tired",
        "sad",
        "lonely",
        "afraid",
        "upset",
    ),
    "low_intensity_care": (
        "陪",
        "在这",
        "慢慢",
        "别急",
        "等你",
        "不用急",
        "不用担心",
        "休息",
        "照顾",
        "好好休息",
        "晚安",
        "相信我",
        "stay",
        "with you",
        "take your time",
    ),
    "gentle_attention": (
        "关心",
        "温柔",
        "脸色",
        "头疼",
        "看上去不太好",
        "闷闷不乐",
        "忧郁",
        "疲惫",
    ),
    "boundary": (
        "不要",
        "别",
        "不想",
        "不能",
        "停",
        "not now",
        "don't",
        "stop",
        "can't",
    ),
    "banter_to_serious": (
        "开玩笑",
        "别闹",
        "认真",
        "说真的",
        "kidding",
        "joke",
        "serious",
    ),
}

REJECT_RISK_MARKERS: dict[str, tuple[str, ...]] = {
    "service_tone": (
        "感谢反馈",
        "用户",
        "体验",
        "优化",
        "为您",
        "customer",
        "service",
        "feedback",
        "user experience",
    ),
    "overdramatic": (
        "命运",
        "灵魂",
        "永远",
        "宿命",
        "destiny",
        "soul",
        "forever",
    ),
    "role_lore": (
        "王国",
        "帝国",
        "战争",
        "传说",
        "kingdom",
        "empire",
        "war",
        "legend",
    ),
    "manipulation": (
        "属于我",
        "离不开",
        "控制",
        "占有",
        "own you",
        "control you",
        "possess",
    ),
    "audio_roleplay_intimacy": (
        "耳语",
        "ASMR",
        "催眠",
        "抚摸",
        "大腿",
        "靠近耳边",
        "齿音",
        "成人",
        "主人",
        "酒醉",
        "醉了",
    ),
}

SIGNAL_WEIGHTS = {
    "remembered_detail": 5,
    "repair": 5,
    "low_intensity_care": 4,
    "low_mood": 4,
    "gentle_attention": 4,
    "banter_to_serious": 3,
    "boundary": 1,
}

REJECT_RISK_WEIGHTS = {
    "service_tone": 4,
    "manipulation": 5,
    "audio_roleplay_intimacy": 5,
    "overdramatic": 3,
    "role_lore": 2,
}


@dataclass(frozen=True)
class DialogueLine:
    source_file: str
    source_format: str
    line_index: int
    speaker: str
    text: str


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _trim(text: Any, limit: int = 260) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _clean_dialogue_markup(text: str) -> str:
    """Remove common VN/GameMaker control tags while keeping speaker/text shape."""
    clean = _safe_str(text)
    clean = re.sub(r"\[[A-Za-z0-9_:+, .\-/]+\]", "", clean)
    clean = clean.replace("#", "")
    clean = clean.replace("\\n", " ")
    clean = clean.replace("\ufeff", "")
    return re.sub(r"\s+", " ", clean).strip()


def _workspace_root(app_root: Path) -> Path:
    candidates = [app_root, *app_root.parents]
    for candidate in candidates:
        if (candidate / "XinYu-Core").exists() and (candidate / "XinYu-Local-Scope").exists():
            return candidate
    for candidate in candidates:
        if candidate.name == "XinYu-Core" and (candidate.parent / "XinYu-Local-Scope").exists():
            return candidate.parent
    for candidate in reversed(candidates):
        if (candidate / "XinYu-Local-Scope").exists():
            return candidate
    return app_root


def default_output_path(app_root: Path) -> Path:
    root = _workspace_root(app_root)
    return root / "XinYu-Local-Scope" / "SourceMaterials" / "dialogue_observation" / "candidates" / "dialogue_candidates.jsonl"


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    lowered = text.lower()
    for marker in markers:
        marker = marker.strip()
        if not marker:
            continue
        haystack = lowered if re.search(r"[A-Za-z]", marker) else text
        needle = marker.lower() if re.search(r"[A-Za-z]", marker) else marker
        if needle in haystack:
            return True
    return False


def _matched_labels(text: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    return [label for label, markers in groups.items() if _contains_any(text, markers)]


def _parse_speaker_line(raw: str) -> tuple[str, str]:
    text = _clean_dialogue_markup(raw)
    match = re.match(r"^([A-Za-z0-9_\-\u4e00-\u9fff .]{1,40})[:：]\s+(.+)$", text)
    if not match:
        return "", text
    speaker = match.group(1).strip()
    line = match.group(2).strip()
    if len(line) < 2:
        return "", text
    return speaker, line


def _iter_input_files(paths: list[Path], *, max_file_bytes: int) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            candidates = [path]
        else:
            candidates = [item for item in path.rglob("*") if item.is_file()]
        for item in candidates:
            if item.suffix.lower() not in SUPPORTED_EXTS:
                continue
            try:
                if item.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            files.append(item)
    return sorted(files, key=lambda p: str(p).lower())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _lines_from_text(path: Path, source_file: str) -> list[DialogueLine]:
    result: list[DialogueLine] = []
    for idx, raw in enumerate(_read_text(path).splitlines(), start=1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        speaker, text = _parse_speaker_line(raw)
        if _usable_line(text):
            result.append(DialogueLine(source_file, path.suffix.lower().lstrip("."), idx, speaker, text))
    return result


def _usable_line(text: str) -> bool:
    clean = _trim(text, limit=400)
    if len(clean) < 8:
        return False
    if len(clean) > 420:
        return False
    if re.fullmatch(r"[\W_0-9]+", clean):
        return False
    return True


def _first_string(data: dict[str, Any], keys: set[str]) -> str:
    for key, value in data.items():
        if key.lower() in keys and isinstance(value, (str, int, float)):
            text = _safe_str(value).strip()
            if text:
                return text
    return ""


def _json_dialogue_lines(value: Any, source_file: str, source_format: str, counter: list[int]) -> list[DialogueLine]:
    result: list[DialogueLine] = []
    if isinstance(value, dict):
        text = _first_string(value, TEXT_KEYS)
        speaker = _first_string(value, SPEAKER_KEYS)
        if _usable_line(text):
            counter[0] += 1
            result.append(DialogueLine(source_file, source_format, counter[0], speaker, text))
        for key, child in value.items():
            if key.lower() in TEXT_KEYS or key.lower() in SPEAKER_KEYS:
                continue
            result.extend(_json_dialogue_lines(child, source_file, source_format, counter))
    elif isinstance(value, list):
        for child in value:
            result.extend(_json_dialogue_lines(child, source_file, source_format, counter))
    elif isinstance(value, str) and _usable_line(value):
        counter[0] += 1
        result.append(DialogueLine(source_file, source_format, counter[0], "", value))
    return result


def _lines_from_json(path: Path, source_file: str) -> list[DialogueLine]:
    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError:
        return []
    return _json_dialogue_lines(data, source_file, path.suffix.lower().lstrip("."), [0])


def _lines_from_jsonl(path: Path, source_file: str) -> list[DialogueLine]:
    result: list[DialogueLine] = []
    counter = [0]
    for raw in _read_text(path).splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            speaker, text = _parse_speaker_line(raw)
            if _usable_line(text):
                counter[0] += 1
                result.append(DialogueLine(source_file, "jsonl", counter[0], speaker, text))
            continue
        result.extend(_json_dialogue_lines(data, source_file, "jsonl", counter))
    return result


def _lines_from_csv(path: Path, source_file: str) -> list[DialogueLine]:
    text = _read_text(path)
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    result: list[DialogueLine] = []
    for idx, row in enumerate(reader, start=1):
        lowered = {key.lower(): value for key, value in row.items() if key is not None}
        line = _first_string(lowered, TEXT_KEYS)
        speaker = _first_string(lowered, SPEAKER_KEYS)
        if not line:
            joined = " ".join(_safe_str(value) for value in row.values() if _safe_str(value).strip())
            speaker, line = _parse_speaker_line(joined)
        if _usable_line(line):
            result.append(DialogueLine(source_file, path.suffix.lower().lstrip("."), idx, speaker, line))
    return result


def _lines_from_docx(path: Path, source_file: str) -> list[DialogueLine]:
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile):
        return []
    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError:
        return []
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    result: list[DialogueLine] = []
    for idx, paragraph in enumerate(root.findall(".//w:p", namespace), start=1):
        parts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        raw = "".join(parts).strip()
        if not raw:
            continue
        speaker, text = _parse_speaker_line(raw)
        if _usable_line(text):
            result.append(DialogueLine(source_file, "docx", idx, speaker, text))
    return result


def load_dialogue_lines(paths: list[Path], *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> list[DialogueLine]:
    input_files = _iter_input_files(paths, max_file_bytes=max_file_bytes)
    lines: list[DialogueLine] = []
    cwd = Path.cwd()
    for path in input_files:
        try:
            source_file = str(path.resolve().relative_to(cwd.resolve()))
        except ValueError:
            source_file = str(path.resolve())
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            lines.extend(_lines_from_text(path, source_file))
        elif suffix == ".json":
            lines.extend(_lines_from_json(path, source_file))
        elif suffix == ".jsonl":
            lines.extend(_lines_from_jsonl(path, source_file))
        elif suffix in {".csv", ".tsv"}:
            lines.extend(_lines_from_csv(path, source_file))
        elif suffix == ".docx":
            lines.extend(_lines_from_docx(path, source_file))
    return lines


def _candidate_id(line: DialogueLine) -> str:
    seed = f"{line.source_file}|{line.line_index}|{line.speaker}|{line.text}"
    return "dlgobs-" + hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:16]


def _fit_score(signals: list[str], reject_risks: list[str]) -> int:
    score = sum(SIGNAL_WEIGHTS.get(signal, 1) for signal in signals)
    score -= sum(REJECT_RISK_WEIGHTS.get(risk, 2) for risk in reject_risks)
    if signals == ["boundary"]:
        score -= 2
    if len(signals) >= 2:
        score += 2
    return score


def build_candidates(
    lines: list[DialogueLine],
    *,
    include_neutral: bool = False,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        signals = _matched_labels(line.text, USEFUL_MARKERS)
        reject_risks = _matched_labels(line.text, REJECT_RISK_MARKERS)
        if not signals and not include_neutral:
            continue
        prev_line = lines[idx - 1] if idx > 0 and lines[idx - 1].source_file == line.source_file else None
        next_line = lines[idx + 1] if idx + 1 < len(lines) and lines[idx + 1].source_file == line.source_file else None
        xinyu_fit_score = _fit_score(signals, reject_risks)
        candidates.append(
            {
                "candidate_id": _candidate_id(line),
                "record_type": "dialogue_observation_candidate",
                "source_file": line.source_file,
                "source_format": line.source_format,
                "line_index": line.line_index,
                "speaker": _trim(line.speaker, limit=80),
                "text_excerpt": _trim(line.text),
                "prev_excerpt": _trim(prev_line.text) if prev_line else "",
                "next_excerpt": _trim(next_line.text) if next_line else "",
                "signals": signals,
                "reject_risks": reject_risks,
                "xinyu_fit_score": xinyu_fit_score,
                "review_status": "unreviewed",
                "suggested_use": "manual_rule_card_review",
                "xinyu_rule_draft": "",
                "xinyu_do_not_learn": "",
                "boundary": (
                    "local_source_observation_only; not memory; not stable voice; "
                    "do not train or quote broadly without owner review"
                ),
            }
        )
    candidates.sort(
        key=lambda row: (
            int(row.get("xinyu_fit_score") or 0),
            len(row.get("signals") if isinstance(row.get("signals"), list) else []),
            -int(row.get("line_index") or 0),
        ),
        reverse=True,
    )
    return candidates[:max_candidates]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    app_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Extract local dialogue observation candidates for XinYu rule-card review."
    )
    parser.add_argument("--input", action="append", type=Path, required=True, help="Local file or directory to scan.")
    parser.add_argument("--output", type=Path, default=default_output_path(app_root), help="Candidate JSONL output.")
    parser.add_argument("--include-neutral", action="store_true", help="Also emit lines without useful signals.")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES)
    args = parser.parse_args(argv)

    lines = load_dialogue_lines(args.input, max_file_bytes=max(1, args.max_file_bytes))
    candidates = build_candidates(
        lines,
        include_neutral=args.include_neutral,
        max_candidates=max(1, args.max_candidates),
    )
    write_jsonl(args.output, candidates)
    summary = {
        "input_line_count": len(lines),
        "candidate_count": len(candidates),
        "output": str(args.output),
        "boundary": "local observation candidates only; no memory/runtime writes",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
