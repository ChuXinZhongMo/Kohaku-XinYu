"""CLI MCP commands -- list MCP server configs from agent config."""

from pathlib import Path

import yaml

from kohakuterrarium.utils.logging import get_logger

logger = get_logger(__name__)


def mcp_list_cli(agent_path: str) -> int:
    """List MCP servers configured in an agent config.

    Args:
        agent_path: Path to the agent config folder.

    Returns:
        Exit code (0 on success, 1 on error).
    """
    path = Path(agent_path)
    if not path.exists():
        print(f"Error: Agent path not found: {agent_path}")
        return 1

    config_file = None
    for name in ("config.yaml", "config.yml"):
        candidate = path / name
        if candidate.exists():
            config_file = candidate
            break

    if config_file is None:
        print(f"Error: No config.yaml found in {agent_path}")
        return 1

    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error reading config: {e}")
        return 1

    mcp_servers = config.get("mcp_servers", [])
    if not mcp_servers:
        print(f"No MCP servers configured in {config_file}")
        return 0

    print(f"MCP servers in {config_file.name}:")
    print("-" * 50)
    for i, server in enumerate(mcp_servers, 1):
        if isinstance(server, dict):
            server_name = server.get("name", f"server-{i}")
            server_type = server.get("transport", server.get("type", "?"))
            command = server.get("command", "")
            url = server.get("url", "")
            print(f"  {i}. {server_name}")
            print(f"     Type: {server_type}")
            if command:
                print(f"     Command: {command}")
            if url:
                print(f"     URL: {url}")
            args = server.get("args", [])
            if args:
                print(f"     Args: {args}")
            env = server.get("env", {})
            if env:
                print(f"     Env vars: {', '.join(env.keys())}")
        else:
            print(f"  {i}. {server}")
        print()

    return 0
