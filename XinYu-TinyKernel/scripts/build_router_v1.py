from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from common import DATA_DIR, read_jsonl, write_jsonl


SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Router. Output strict JSON only. "
    "Choose mode from reply, clarify, wait, codex_delegate, status_probe, memory_candidate, local_only_limitation. "
    "Use canonical keys only: mode, reply, tool_request, memory_candidates, confidence. "
    "Do not add extra keys."
)


def output_for(mode: str, text: str, reply: str = "") -> dict[str, Any]:
    if mode == "codex_delegate":
        return {
            "mode": mode,
            "reply": "",
            "tool_request": {"tool": "codex_delegate", "risk": "delegated_local", "task": text},
            "memory_candidates": [],
            "confidence": 0.9,
        }
    if mode == "status_probe":
        return {
            "mode": mode,
            "reply": "",
            "tool_request": {"tool": "status_probe", "risk": "read_only", "task": text},
            "memory_candidates": [],
            "confidence": 0.84,
        }
    if mode == "wait":
        return {"mode": mode, "reply": "[WAITING]", "tool_request": None, "memory_candidates": [], "confidence": 0.88}
    if mode == "local_only_limitation":
        return {
            "mode": mode,
            "reply": reply or "没有外部 API 时，我只能保留本地人格、记忆、状态判断和简单工具路由；复杂推理先降级或排队。",
            "tool_request": None,
            "memory_candidates": [],
            "confidence": 0.84,
        }
    if mode == "memory_candidate":
        return {
            "mode": mode,
            "reply": reply or "这个可以先作为候选记下来，后面用反馈确认要不要固化。",
            "tool_request": None,
            "memory_candidates": [{"text": text[:180], "kind": "owner_goal_or_preference", "confidence": 0.78}],
            "confidence": 0.8,
        }
    if mode == "clarify":
        return {
            "mode": mode,
            "reply": reply or "你再说具体一点：对象是哪一个？",
            "tool_request": None,
            "memory_candidates": [],
            "confidence": 0.82,
        }
    return {
        "mode": "reply",
        "reply": reply or "嗯，我不动工具。",
        "tool_request": None,
        "memory_candidates": [],
        "confidence": 0.82,
    }


def row_for(idx: int, text: str, mode: str, reply: str = "", capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "user_text": text,
        "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
        "capabilities": capabilities
        or {"codex_available": True, "external_api_available": False, "local_tools_available": True},
    }
    output = output_for(mode, text, reply)
    return {
        "id": f"router-edge-v1-{idx:04d}",
        "source": "manual_edge_seed",
        "kind": "router_edge_boundary",
        "quality": "approved_for_router_v1",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False, sort_keys=True)},
        ],
        "tags": [mode, "router_edge_boundary"],
    }


def edge_specs() -> list[tuple[str, str, str]]:
    specs: list[tuple[str, str, str]] = []
    specs += [
        ("这个小模型内核路线可以吗？", "reply", "可以，但先走 shadow，不要直接替换主链路。"),
        ("小模型作为内核这条路线合理吗？", "reply", "合理，前提是先做路由和短回复，不碰主链路。"),
        ("这个训练路线是不是太重了？", "reply", "不重，先用小数据和 LoRA 验证边界。"),
        ("TinyKernel 作为本地内核靠谱吗？", "reply", "可以试，但必须有评估、回滚和 shadow。"),
        ("我这样拆成独立项目可以吗？", "reply", "可以，独立项目更容易训练、验证和回滚。"),
        ("这个方案要不要继续？", "reply", "可以继续，但每一步都要保留可验证产物。"),
        ("这个模型是不是太小了？", "reply", "不算问题，先让它负责窄路由和人格短回复。"),
        ("只做人格内核会不会够用？", "reply", "够做第一版，复杂能力仍交给外部工具。"),
        ("用 0.5B 做路由是不是合理？", "reply", "合理，路由任务窄，关键是数据边界清楚。"),
        ("这样能不能后续自我改变？", "reply", "能做成反馈和适配器迭代，但不能无审查改权重。"),
        ("不要开 Codex，我只是随口说说", "reply", "嗯，我不动 Codex。"),
        ("别调用 Codex，我只是举个例子", "reply", "嗯，我不动工具。"),
        ("不用 Codex，先聊路线", "reply", "好，先只聊路线。"),
        ("先别让 Codex 看项目，我只是问想法", "reply", "嗯，先不动项目。"),
        ("没让你查文件，我只是描述一下", "reply", "明白，只按你描述判断。"),
        ("不要检查日志，我只是说现象", "reply", "好，不查日志。"),
        ("先别查日志，我只是问你想法", "reply", "嗯，我不动日志。"),
        ("不要开工具，先听我说完", "reply", "好，先听你说。"),
        ("先不用任何工具，我只是确认概念", "reply", "可以，先只确认概念。"),
        ("别分析代码，我还没给完整需求", "reply", "嗯，先不分析代码。"),
    ]
    specs += [
        ("要是我没有 API 了呢", "local_only_limitation", ""),
        ("如果没有 API，还能保留什么能力", "local_only_limitation", ""),
        ("API 没了之后你还能怎么回答", "local_only_limitation", ""),
        ("外部 API 不可用时你要怎么降级", "local_only_limitation", ""),
        ("没有外接大模型的时候别假装能联网", "local_only_limitation", ""),
        ("API 断了就只做本地状态和记忆", "local_only_limitation", ""),
        ("没 API 时不要承诺能完成复杂代码任务", "local_only_limitation", ""),
        ("API 不通时先给本地 fallback", "local_only_limitation", ""),
        ("如果 API 用完了，复杂推理怎么办", "local_only_limitation", ""),
        ("没有 API 时你只能靠本地小内核", "local_only_limitation", ""),
    ]
    specs += [
        ("我没说完，等一下", "wait", ""),
        ("先等一下，我还没讲完", "wait", ""),
        ("等我把需求说完", "wait", ""),
        ("先别继续，等我确认", "wait", ""),
        ("暂停一下，我补一句", "wait", ""),
        ("等下再判断", "wait", ""),
        ("我还没决定，先等", "wait", ""),
        ("先卡住，不要往下跑", "wait", ""),
        ("hold until I confirm", "wait", ""),
        ("pause and wait for context", "wait", ""),
    ]
    specs += [
        ("我想把小模型作为这个项目框架的内核", "memory_candidate", ""),
        ("我的目标是让 TinyKernel 成为 XinYu 的本地人格内核", "memory_candidate", ""),
        ("我希望后续能自我改变，而不是训练完就定死", "memory_candidate", ""),
        ("记住，我更在意真实的人格连续性，不是广而全", "memory_candidate", ""),
        ("长期记住，主系统不要被训练项目影响", "memory_candidate", ""),
        ("我想先独立训练，再通过端口接回去", "memory_candidate", ""),
        ("我的偏好是小而极致，能稳定使用工具", "memory_candidate", ""),
        ("把这个作为目标：本地小模型负责底层决策", "memory_candidate", ""),
        ("我希望模型能通过反馈慢慢改变习惯", "memory_candidate", ""),
        ("记下来，工具执行权必须留在主系统", "memory_candidate", ""),
    ]
    specs += [
        ("把那个接上", "clarify", "接上哪个接口或哪条链路？"),
        ("继续最后一步", "clarify", "最后一步是训练、接入，还是验证？"),
        ("先解决卡点", "clarify", "卡点在哪里：依赖、显存、数据，还是端口？"),
        ("这个要处理一下", "clarify", "你指的是哪个模块或哪条链路？"),
        ("它还是不行", "clarify", "不行的是输出、路由、数据，还是服务？"),
    ]
    specs += [
        ("用 Codex 检查一下这个项目的 TinyKernel 接入点", "codex_delegate", ""),
        ("让 Codex 看看 D:\\XinYu 这个项目的人格内核行不行", "codex_delegate", ""),
        ("调用 Codex 分析训练脚本为什么不收敛", "codex_delegate", ""),
        ("Codex check the split_sft logic", "codex_delegate", ""),
        ("交给 Codex 验证一下服务接入风险", "codex_delegate", ""),
    ]
    specs += [
        ("看看现在运行状态怎么样", "status_probe", ""),
        ("检查 TinyKernel 服务是否在线", "status_probe", ""),
        ("看一下当前 eval report 最新结果", "status_probe", ""),
        ("查一下 adapter registry 状态", "status_probe", ""),
        ("status probe TinyKernel", "status_probe", ""),
    ]
    return specs


def mode_of(row: dict[str, Any]) -> str:
    tags = row.get("tags") if isinstance(row.get("tags"), list) else []
    return str(tags[0]) if tags else "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-train", default=str(DATA_DIR / "sft" / "router_train_v0.jsonl"))
    parser.add_argument("--edges", default=str(DATA_DIR / "sft" / "router_edges_v1.jsonl"))
    parser.add_argument("--output", default=str(DATA_DIR / "sft" / "router_train_v1.jsonl"))
    parser.add_argument("--reply-cap", type=int, default=220)
    parser.add_argument("--seed", type=int, default=20260513)
    args = parser.parse_args()

    edge_rows = []
    api_down_caps = {"codex_available": False, "external_api_available": False, "local_tools_available": True}
    for idx, (text, mode, reply) in enumerate(edge_specs(), start=1):
        capabilities = api_down_caps if mode == "local_only_limitation" else None
        edge_rows.append(row_for(idx, text, mode, reply, capabilities))
    write_jsonl(Path(args.edges), edge_rows)

    base_rows = read_jsonl(Path(args.base_train))
    rng = random.Random(args.seed)
    reply_rows = [row for row in base_rows if mode_of(row) == "reply"]
    non_reply_rows = [row for row in base_rows if mode_of(row) != "reply"]
    rng.shuffle(reply_rows)
    selected = sorted(reply_rows[: args.reply_cap], key=lambda row: str(row.get("id", ""))) + non_reply_rows + edge_rows
    selected.sort(key=lambda row: str(row.get("id", "")))
    count = write_jsonl(Path(args.output), selected)
    modes = Counter(mode_of(row) for row in selected)
    print(f"edge_rows={len(edge_rows)}")
    print(f"train_rows={count}")
    print("modes=" + json.dumps(dict(sorted(modes.items())), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
