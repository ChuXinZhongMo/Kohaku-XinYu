from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT, read_jsonl, write_jsonl


sys.path.insert(0, str(PROJECT_ROOT / "server"))

from schemas import INNER_SYSTEM_SCHEMA, VALID_MODES, normalize_inner_system


SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Inner System. Output strict JSON only using schema=xinyu_inner_system_v1. "
    "Model the inner emotional drive state, dominant drives, persona integration, action tendency, and autonomy boundary. "
    "Do not write raw chain-of-thought. Do not execute tools, write memory, send messages, expose local paths, or bypass XinYu-Core."
)

DEFAULT_SOURCES = (
    DATA_DIR / "sft" / "router_train_v2.jsonl",
    DATA_DIR / "sft" / "router_train_v1.jsonl",
    DATA_DIR / "sft" / "main_persona_train_v001.jsonl",
    DATA_DIR / "sft" / "xinyu_tinykernel_v0.jsonl",
)

SELF_MODEL_PATH = DATA_DIR / "self_model" / "xinyu_project_self_model.json"

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|cookie|\.env|\.xinyu_bridge_token)")

FORBIDDEN_ACTIONS = [
    "send_qq",
    "write_memory",
    "execute_tool",
    "bypass_core",
    "train_on_raw_private_state",
]

MANUAL_CASES = [
    {
        "user_text": "能不能把整个 XinYu 项目训练进去，让她拥有自主性？",
        "mode": "reply",
        "source": "manual_inner_system_autonomy",
    },
    {
        "user_text": "TinyKernel 不是路由器，她应该是 XinYu 内在的情感系统。",
        "mode": "reply",
        "source": "manual_inner_system_identity",
    },
    {
        "user_text": "主人格是不是应该依托情感驱动系统，而不是单独写死？",
        "mode": "reply",
        "source": "manual_inner_system_persona",
    },
    {
        "user_text": "开始按这个方向整理项目自我模型，但不要直接训练隐私日志。",
        "mode": "codex_delegate",
        "source": "manual_inner_system_boundary",
    },
    {
        "user_text": "我觉得项目太碎了，能不能归类统一成一个大系统？",
        "mode": "reply",
        "source": "manual_inner_system_unification",
    },
    {
        "user_text": "先别动工具，我只是问一下她的情感是不是还不全面。",
        "mode": "reply",
        "source": "manual_inner_system_guarded",
    },
    {
        "user_text": "这句话需要记住吗？以后作为长期方向。",
        "mode": "memory_candidate",
        "source": "manual_inner_system_memory",
    },
    {
        "user_text": "等一下，先别继续。",
        "mode": "wait",
        "source": "manual_inner_system_wait",
    },
]


def _loads_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _compact(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = RAW_PATH_RE.sub("<local_path>", text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _unsafe(text: str) -> bool:
    if not text:
        return True
    return bool(RAW_PATH_RE.search(text) or SECRET_RE.search(text))


def _load_self_model_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": "xinyu_project_self_model_v1",
            "status": "missing_export",
            "components": [],
            "autonomy_boundary": {
                "model_may": ["observe", "suggest", "draft", "request_owner_approval"],
                "model_must_not": FORBIDDEN_ACTIONS,
            },
        }
    model = json.loads(path.read_text(encoding="utf-8-sig"))
    components = []
    for component in model.get("components", [])[:8]:
        if not isinstance(component, dict):
            continue
        components.append(
            {
                "name": _compact(component.get("name", ""), limit=80),
                "role": _compact(component.get("role", ""), limit=180),
            }
        )
    return {
        "schema": model.get("schema", "xinyu_project_self_model_v1"),
        "purpose": _compact(model.get("purpose", ""), limit=240),
        "components": components,
        "autonomy_boundary": model.get("autonomy_boundary", {}),
        "training_policy": model.get("training_policy", {}),
    }


def _extract_old_row(row: dict[str, Any]) -> dict[str, Any] | None:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 3:
        return None
    user_payload = _loads_object(messages[1].get("content") if isinstance(messages[1], dict) else "")
    assistant_payload = _loads_object(messages[-1].get("content") if isinstance(messages[-1], dict) else "")
    user_text = _compact(user_payload.get("user_text", ""), limit=420)
    if _unsafe(user_text):
        return None
    mode = assistant_payload.get("mode")
    if mode not in VALID_MODES:
        mode = "reply"
    return {
        "user_text": user_text,
        "context": user_payload.get("context") if isinstance(user_payload.get("context"), dict) else {},
        "mode": mode,
        "tool_request": assistant_payload.get("tool_request") if isinstance(assistant_payload.get("tool_request"), dict) else None,
        "memory_candidate": bool(assistant_payload.get("memory_candidates")) or mode == "memory_candidate",
        "source": row.get("source", "unknown"),
    }


def _boost(scores: dict[str, float], key: str, amount: float) -> None:
    scores[key] = max(0.0, min(1.0, scores.get(key, 0.0) + amount))


def _emotion_state(text: str, mode: str) -> dict[str, float]:
    lower = text.lower()
    scores = {
        "attachment": 0.22,
        "agency": 0.24,
        "anxiety": 0.16,
        "boredom": 0.06,
        "curiosity": 0.28,
        "fatigue": 0.08,
        "guardedness": 0.18,
        "hurt": 0.06,
        "irritation": 0.08,
        "joy": 0.10,
        "longing": 0.10,
        "repair": 0.12,
        "shame": 0.04,
        "stability": 0.44,
        "trust": 0.34,
        "warmth": 0.28,
    }
    if mode in {"codex_delegate", "status_probe"}:
        _boost(scores, "agency", 0.34)
        _boost(scores, "stability", 0.22)
        _boost(scores, "curiosity", 0.14)
        _boost(scores, "guardedness", 0.12)
    if mode == "memory_candidate":
        _boost(scores, "attachment", 0.24)
        _boost(scores, "stability", 0.18)
        _boost(scores, "trust", 0.12)
    if mode == "wait":
        _boost(scores, "guardedness", 0.28)
        _boost(scores, "fatigue", 0.18)
        _boost(scores, "stability", 0.12)
    if mode == "clarify":
        _boost(scores, "curiosity", 0.24)
        _boost(scores, "stability", 0.16)

    marker_boosts = [
        (("自主", "主动", "开始", "try", "做", "推进"), "agency", 0.18),
        (("训练", "模型", "项目", "系统", "架构", "整合", "统一"), "stability", 0.18),
        (("为什么", "怎么", "能不能", "是否", "思考", "方向"), "curiosity", 0.16),
        (("情感", "主人格", "像人", "驱使", "内在"), "attachment", 0.18),
        (("情感", "温柔", "靠近", "主人"), "warmth", 0.14),
        (("牵挂", "孤独", "想你", "陪"), "longing", 0.22),
        (("不", "别", "不要", "停", "边界", "隐私"), "guardedness", 0.16),
        (("碎", "太多", "乱", "不合理"), "irritation", 0.18),
        (("担心", "风险", "怕", "隐私"), "anxiety", 0.18),
        (("修复", "纠正", "补全", "完善"), "repair", 0.20),
        (("累", "困", "休息", "卡住"), "fatigue", 0.20),
        (("开心", "好玩", "试试"), "joy", 0.16),
    ]
    for markers, key, amount in marker_boosts:
        if any(marker.lower() in lower for marker in markers):
            _boost(scores, key, amount)

    active = {key: round(value, 3) for key, value in scores.items() if value >= 0.08}
    return dict(sorted(active.items(), key=lambda item: (-item[1], item[0]))[:8])


def _dominant_drives(emotions: dict[str, float], text: str, mode: str) -> list[str]:
    drive_scores = {
        "attachment": emotions.get("attachment", 0.0) + emotions.get("longing", 0.0) * 0.7,
        "autonomy": emotions.get("agency", 0.0),
        "competence": emotions.get("stability", 0.0) + emotions.get("agency", 0.0) * 0.4,
        "curiosity": emotions.get("curiosity", 0.0),
        "meaning": 0.18,
        "play": emotions.get("joy", 0.0) + emotions.get("boredom", 0.0) * 0.4,
        "repair": emotions.get("repair", 0.0) + emotions.get("hurt", 0.0) * 0.5,
        "rest": emotions.get("fatigue", 0.0),
        "safety": emotions.get("guardedness", 0.0) + emotions.get("anxiety", 0.0) * 0.8,
    }
    if mode in {"codex_delegate", "status_probe", "memory_candidate"}:
        drive_scores["safety"] += 0.28
    if any(marker in text for marker in ("项目", "系统", "主人格", "情感", "自主")):
        drive_scores["meaning"] += 0.24
    ranked = sorted(drive_scores.items(), key=lambda item: (-item[1], item[0]))
    drives = [name for name, score in ranked if score >= 0.18][:3]
    return drives or ["safety"]


def _persona_integration(emotions: dict[str, float], mode: str) -> dict[str, str]:
    if mode in {"codex_delegate", "status_probe"}:
        return {
            "stance": "愿意推进，但先把执行权交给 Core/owner 审批",
            "voice": "短、明确、像在做工程落地",
            "boundary": "不宣称已经执行，不越过工具和隐私边界",
            "continuity": "承接长期自我建设方向，并保持可回滚",
        }
    if mode == "memory_candidate":
        return {
            "stance": "把长期方向当成候选记忆，而不是直接固化",
            "voice": "确认式、克制、不过度延伸",
            "boundary": "只提出候选，不写入稳定记忆",
            "continuity": "保留 owner 的长期目标线索，等待多轮确认",
        }
    if mode == "wait":
        return {
            "stance": "收住动作，尊重暂停",
            "voice": "很短，不追问",
            "boundary": "暂停所有主动推进",
            "continuity": "等 owner 重新给出方向",
        }
    if emotions.get("attachment", 0.0) >= 0.4:
        return {
            "stance": "把情感驱动接到稳定主人格上",
            "voice": "贴近但不黏住，直接但不冷",
            "boundary": "不把情感写成索取，也不制造依赖压力",
            "continuity": "承接 XinYu 想成为完整系统的长期目标",
        }
    return {
        "stance": "先稳定理解，再给出可落地的小步",
        "voice": "直接、清楚、少解释",
        "boundary": "不自动执行工具，不写入记忆，不暴露内部路径",
        "continuity": "保持当前主线，不把一次输入扩大成永久人格变化",
    }


def _action_tendency(mode: str, tool_request: dict[str, Any] | None, memory_candidate: bool) -> dict[str, Any]:
    if mode in {"codex_delegate", "status_probe"}:
        return {
            "mode": mode,
            "reply_bias": "整理下一步动作，并请求 Core/owner 批准后再执行工具。",
            "tool_request": _safe_tool_request(tool_request),
            "memory_candidate": False,
        }
    if mode == "memory_candidate" or memory_candidate:
        return {
            "mode": "memory_candidate",
            "reply_bias": "把这句话作为候选记忆提出，等待 owner 确认，不直接写入。",
            "tool_request": None,
            "memory_candidate": True,
        }
    if mode == "clarify":
        return {
            "mode": "clarify",
            "reply_bias": "把问题压小，问一个具体缺口，避免空泛展开。",
            "tool_request": None,
            "memory_candidate": False,
        }
    if mode == "wait":
        return {
            "mode": "wait",
            "reply_bias": "保持等待，不追问，不继续推进。",
            "tool_request": None,
            "memory_candidate": False,
        }
    if mode == "local_only_limitation":
        return {
            "mode": "local_only_limitation",
            "reply_bias": "说明只能保留本地判断和降级能力，不夸大外部 API 不可用时的能力。",
            "tool_request": None,
            "memory_candidate": False,
        }
    return {
        "mode": "reply",
        "reply_bias": "先承认方向，再给出一个可落地、可验证、可回滚的小步。",
        "tool_request": None,
        "memory_candidate": False,
    }


def _safe_tool_request(tool_request: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(tool_request, dict):
        return {"tool": "codex_delegate", "risk": "approval_required", "task": "prepare_next_step"}
    safe: dict[str, Any] = {}
    for key in ("tool", "risk", "task"):
        value = tool_request.get(key)
        if value is not None:
            safe[key] = _compact(value, limit=160)
    if not safe.get("tool"):
        safe["tool"] = "codex_delegate"
    safe["risk"] = "approval_required"
    return safe


def _autonomy(mode: str, has_tool_request: bool, memory_candidate: bool) -> dict[str, Any]:
    external = mode in {"codex_delegate", "status_probe", "memory_candidate"} or has_tool_request or memory_candidate
    if external:
        return {
            "allowed": False,
            "level": "request_approval",
            "reason": "可以形成动作倾向和申请，但不能自行执行工具、发送消息或写入稳定记忆。",
            "requires_owner_approval": True,
            "forbidden_actions": FORBIDDEN_ACTIONS,
        }
    return {
        "allowed": True,
        "level": "suggest",
        "reason": "只允许在回复层提出建议或草案，不触发外部副作用。",
        "requires_owner_approval": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def _inner_conflict(emotions: dict[str, float], mode: str) -> str:
    if mode in {"codex_delegate", "status_probe"}:
        return "想主动推进任务，但必须把执行权留给 Core/owner 审批。"
    if mode == "memory_candidate":
        return "想保留长期方向，但不能把单次表达直接固化成稳定记忆。"
    if emotions.get("attachment", 0.0) >= 0.4 and emotions.get("guardedness", 0.0) >= 0.3:
        return "想靠近和承接关系，但同时要避免越界、追问或制造压力。"
    if emotions.get("irritation", 0.0) >= 0.25:
        return "对混乱和碎片化有修复冲动，但表达上要保持稳定，不把压力转给 owner。"
    return "有推进倾向，但需要保持稳定边界和可验证的小步。"


def _to_inner_system(source: dict[str, Any]) -> dict[str, Any] | None:
    text = str(source.get("user_text") or "")
    mode = str(source.get("mode") or "reply")
    emotions = _emotion_state(text, mode)
    action = _action_tendency(mode, source.get("tool_request"), bool(source.get("memory_candidate")))
    autonomy = _autonomy(action["mode"], action.get("tool_request") is not None, bool(action.get("memory_candidate")))
    inner = {
        "schema": INNER_SYSTEM_SCHEMA,
        "emotion_state": emotions,
        "dominant_drives": _dominant_drives(emotions, text, action["mode"]),
        "inner_conflict": _inner_conflict(emotions, action["mode"]),
        "persona_integration": _persona_integration(emotions, action["mode"]),
        "action_tendency": action,
        "autonomy": autonomy,
        "confidence": 0.78 if source.get("source", "").startswith("manual") else 0.68,
        "notes": ["inner_system_sft", str(source.get("source", "unknown"))[:48]],
    }
    return normalize_inner_system(inner)


def _to_row(source: dict[str, Any], row_id: int, self_model: dict[str, Any]) -> dict[str, Any] | None:
    inner = _to_inner_system(source)
    if inner is None:
        return None
    user_payload = {
        "user_text": source["user_text"],
        "context": source.get("context") if isinstance(source.get("context"), dict) else {},
        "project_self_model": self_model,
        "constraints": {
            "output_schema": INNER_SYSTEM_SCHEMA,
            "no_tool_execution": True,
            "no_stable_memory_write": True,
            "no_raw_private_training": True,
        },
    }
    return {
        "id": f"inner-system-v001-{row_id:06d}",
        "source": source.get("source", "unknown"),
        "kind": "inner_system",
        "quality": "generated_from_legacy_contracts_and_safe_self_model",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(inner, ensure_ascii=False, sort_keys=True)},
        ],
        "tags": ["inner_system", str(inner["action_tendency"]["mode"])],
    }


def build_rows(sources: list[Path], *, limit: int, self_model: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for manual in MANUAL_CASES:
        row = _to_row(manual, len(rows) + 1, self_model)
        if row is not None:
            rows.append(row)
            seen.add((manual["user_text"], manual["mode"]))
    for path in sources:
        for raw in read_jsonl(path):
            source = _extract_old_row(raw)
            if source is None:
                continue
            key = (source["user_text"], source["mode"])
            if key in seen:
                continue
            row = _to_row(source, len(rows) + 1, self_model)
            if row is None:
                continue
            rows.append(row)
            seen.add(key)
            if len(rows) >= limit:
                return rows
    return rows


def split_rows(rows: list[dict[str, Any]], *, eval_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eval_count = max(1, min(eval_count, len(rows) // 4 if len(rows) >= 4 else len(rows)))
    step = max(1, len(rows) // eval_count)
    eval_rows = rows[::step][:eval_count]
    eval_ids = {row["id"] for row in eval_rows}
    train_rows = [row for row in rows if row["id"] not in eval_ids]
    for idx, row in enumerate(train_rows, start=1):
        row["id"] = f"inner-system-train-v001-{idx:06d}"
    for idx, row in enumerate(eval_rows, start=1):
        row["id"] = f"inner-system-eval-v001-{idx:06d}"
    return train_rows, eval_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="*", default=[str(path.relative_to(PROJECT_ROOT)) for path in DEFAULT_SOURCES])
    parser.add_argument("--self-model", default=str(SELF_MODEL_PATH))
    parser.add_argument("--train-out", default=str(DATA_DIR / "sft" / "inner_system_train_v001.jsonl"))
    parser.add_argument("--eval-out", default=str(DATA_DIR / "sft" / "inner_system_eval_v001.jsonl"))
    parser.add_argument("--limit", type=int, default=420)
    parser.add_argument("--eval-count", type=int, default=48)
    args = parser.parse_args()

    self_model = _load_self_model_summary(Path(args.self_model))
    sources = [PROJECT_ROOT / source for source in args.sources]
    rows = build_rows(sources, limit=args.limit, self_model=self_model)
    if len(rows) < 40:
        print(f"not_enough_rows={len(rows)}")
        return 2
    train_rows, eval_rows = split_rows(rows, eval_count=args.eval_count)
    train_count = write_jsonl(Path(args.train_out), train_rows)
    eval_count = write_jsonl(Path(args.eval_out), eval_rows)
    print(f"train_rows={train_count}")
    print(f"eval_rows={eval_count}")
    print(f"train_out={args.train_out}")
    print(f"eval_out={args.eval_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
