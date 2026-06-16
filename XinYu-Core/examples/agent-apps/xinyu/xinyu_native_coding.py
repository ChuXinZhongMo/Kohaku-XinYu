"""Native coding capability — XinYu runs its own agentic tool loop instead of
delegating to the external ``codex`` CLI.

When a turn is classified as a coding/tool task, a dedicated in-process agent is
built with code-execution tools (bash/python/edit/...) and native OpenAI
tool-calling, on a stronger model (mimo-v2.5-pro by default), runs the task to
completion, and writes its result where the existing codex finalize/outbox path
already reads it. The live chat agent is untouched (still MiMo, no tools).

Owner decision (2026-06-15): execution is intentionally NOT sandboxed — full
filesystem, inherited environment, all contexts. The owner accepted that risk.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_codex_delegate import CodexDelegateResult

CODING_TOOLS = ("bash", "python", "read", "write", "edit", "multi_edit", "grep", "glob", "tree")
DEFAULT_CODING_MODEL = "mimo-v2.5-pro"
_FALSE_VALUES = {"0", "false", "no", "off"}

CODING_SYSTEM_PROMPT = (
    "你是心语的编码分身，负责在主人的机器上真正完成编码与工具任务。"
    "你可以调用 bash、python、读写/编辑文件、grep、glob 等工具来实际执行，而不是只口头描述。"
    "请先理解任务，再用工具一步步完成；完成后用简洁中文说明：你做了什么、结果如何、改动或产物在哪里。"
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def native_coding_enabled() -> bool:
    return os.environ.get("XINYU_NATIVE_CODING", "").strip().lower() not in _FALSE_VALUES


def coding_model() -> str:
    return os.environ.get("XINYU_CODING_MODEL", "").strip() or DEFAULT_CODING_MODEL


def build_coding_agent_config(
    xinyu_dir: Path,
    *,
    model: str | None = None,
    tools: tuple[str, ...] | None = None,
    max_iterations: int = 40,
) -> Any:
    from xinyu_runtime.core.config_types import AgentConfig, InputConfig, ToolConfigItem

    return AgentConfig(
        name="xinyu-native-coder",
        model=model or coding_model(),
        provider=os.environ.get("XINYU_LLM_PROVIDER", "").strip() or "ciallo",
        api_key_env="XINYU_API_KEY",
        base_url=os.environ.get("XINYU_BASE_URL", "").strip(),
        temperature=0.3,
        max_tokens=4096,
        tool_format="native",
        system_prompt=CODING_SYSTEM_PROMPT,
        tools=[ToolConfigItem(name=name) for name in (tools or CODING_TOOLS)],
        input=InputConfig(type="none"),
        max_iterations=max_iterations,
        ephemeral=True,
        agent_path=Path(xinyu_dir),
    )


async def run_native_coding_agent(
    xinyu_dir: Path,
    task_text: str,
    *,
    model: str | None = None,
    tools: tuple[str, ...] | None = None,
    max_iterations: int = 40,
    timeout: float = 900.0,
) -> tuple[str, bool]:
    """Build a one-shot coding agent, run the task to completion, return
    (final_text, timed_out)."""

    import xinyu_runtime.builtins.tools  # noqa: F401 — fires @register_builtin for bash/python/edit/...
    from xinyu_runtime.core.agent import Agent

    config = build_coding_agent_config(xinyu_dir, model=model, tools=tools, max_iterations=max_iterations)
    agent = Agent(config, pwd=str(xinyu_dir))
    timed_out = False
    await agent.start()
    try:
        try:
            await asyncio.wait_for(agent.inject_input(task_text), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            try:
                agent.interrupt()
            except Exception:
                pass
        text = "".join(getattr(agent, "_last_turn_text", []) or []).strip()
    finally:
        try:
            await agent.stop()
        except Exception:
            pass
    return text, timed_out


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


async def run_native_coding_delegate(
    xinyu_dir: Path,
    payload: dict[str, Any],
    *,
    task_text: str | None = None,
    model: str | None = None,
    tools: tuple[str, ...] | None = None,
    max_iterations: int = 40,
    timeout: float = 900.0,
    runner: Any = run_native_coding_agent,
) -> CodexDelegateResult:
    """Run native coding and shape the outcome as a CodexDelegateResult, writing the
    output where codex_completion_summary reads it (last_message_path/report_path),
    so the existing finalize + outbox path delivers the result to the owner."""

    root = Path(xinyu_dir)
    text = _safe_str(task_text if task_text is not None else payload.get("text")).strip()
    out_dir = root / "runtime" / "native_coding"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()

    try:
        reply, timed_out = await runner(
            root, text, model=model, tools=tools, max_iterations=max_iterations, timeout=timeout
        )
        accepted = True
        exit_code: int | None = 0 if not timed_out else None
        notes = ["native_coding_delegate"]
        if timed_out:
            notes.append("native_coding_timeout")
    except Exception as exc:
        reply = f"native coding failed: {exc!r}"
        timed_out = False
        accepted = False
        exit_code = 1
        notes = ["native_coding_error", repr(exc)]

    body = reply or "(native coding produced no output)"
    report_path = out_dir / f"native-coding-report-{stamp}.md"
    last_path = out_dir / f"native-coding-last-{stamp}.txt"
    report_path.write_text(f"# Native Coding Report {stamp}\n\n## Task\n{text}\n\n## Result\n{body}\n", encoding="utf-8")
    last_path.write_text(body, encoding="utf-8")

    return CodexDelegateResult(
        accepted=accepted,
        reply=body,
        request_path="",
        workspace_path=str(root),
        report_path=str(report_path),
        last_message_path=str(last_path),
        exit_code=exit_code,
        timed_out=timed_out,
        stdout_tail=body[-2000:],
        stderr_tail="",
        notes=notes,
    )
