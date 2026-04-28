from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_local_env(xinyu_dir: Path) -> None:
    env_path = xinyu_dir / "xinyu.local.env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_repo_src(xinyu_dir: Path) -> None:
    src_root = xinyu_dir.parents[2] / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


class NullInput:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def get_input(self):
        return None

    def set_user_commands(self, commands, context) -> None:
        self.commands = commands
        self.context = context


def _contains(prompt: str, needle: str) -> str:
    return "yes" if needle in prompt else "no"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-system-prompt", default="")
    args = parser.parse_args()

    xinyu_dir = Path(__file__).resolve().parent
    _load_local_env(xinyu_dir)
    _ensure_repo_src(xinyu_dir)

    from kohakuterrarium.core.agent import Agent

    agent = Agent.from_path(str(xinyu_dir), input_module=NullInput(), pwd=str(xinyu_dir))
    prompt = agent.get_system_prompt()
    unresolved = [name for name in agent.config.prompt_context_files if "{{ " + name + " }}" in prompt]

    print("=== CONFIG ===")
    print(f"agent_name: {agent.config.name}")
    print(f"model: {getattr(agent.llm, 'config', None).model if getattr(agent, 'llm', None) else ''}")
    print(f"provider_name: {getattr(agent.llm, 'provider_name', '')}")
    print(f"controller_direct: {agent.config.output.controller_direct}")
    print(f"prompt_context_files: {len(agent.config.prompt_context_files)}")
    print(f"system_prompt_chars: {len(prompt)}")
    print(f"unresolved_prompt_context_vars: {unresolved}")

    print("=== SYSTEM_PROMPT_MARKERS ===")
    for label, needle in [
        ("live_voice_card", "# XinYu Live Voice Card"),
        ("self_core", "memory_type: self_core"),
        ("personality_profile", "# 心玉人格细节画像"),
        ("persona_life_anchors", "# 心玉人格生活锚点"),
        ("emotion_state", "# 当前状态"),
        ("relationship_index", "# 关系索引"),
        ("owner_profile", "# owner"),
        ("output_layer_prompt_not_in_controller", "# Xinyu Output Layer"),
    ]:
        print(f"{label}: {_contains(prompt, needle)}")

    print("=== RUNTIME_REGISTRY ===")
    print("tools:", ", ".join(agent.tools))
    print("subagents:", ", ".join(agent.subagents))
    print("known_outputs:", ", ".join(sorted(getattr(agent, "_known_outputs", set()))))

    print("=== CONFIGURED_PLUGINS ===")
    for plugin in agent.config.plugins:
        print(f"{plugin.get('name')} -> {plugin.get('module')}::{plugin.get('class')}")

    if args.write_system_prompt:
        Path(args.write_system_prompt).write_text(prompt, encoding="utf-8")
        print(f"wrote_system_prompt: {args.write_system_prompt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
