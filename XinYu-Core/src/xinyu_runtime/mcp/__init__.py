"""MCP (Model Context Protocol) client integration.

Provides meta-tools (mcp_list, mcp_call, mcp_connect, mcp_disconnect)
for agents to interact with external MCP servers. MCP tools are NOT
injected as direct agent tools — the agent calls them through meta-tools.
"""
