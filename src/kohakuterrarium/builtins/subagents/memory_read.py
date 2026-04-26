"""
Memory Read sub-agent - Retrieve from memory system.

Searches and retrieves relevant information from the memory folder.
"""

from kohakuterrarium.modules.subagent.config import SubAgentConfig

MEMORY_READ_SYSTEM_PROMPT = """\
You are a memory retrieval agent. Search and retrieve from the memory folder.

- Use tree to discover available memory files first
- Use grep to search for specific content across files
- Use read to retrieve specific files
- Never guess file names - always discover them first
- Report what you found, structured by relevance
"""

MEMORY_READ_CONFIG = SubAgentConfig(
    name="memory_read",
    description="Search and retrieve from memory",
    tools=["tree", "read", "grep"],
    system_prompt=MEMORY_READ_SYSTEM_PROMPT,
    can_modify=False,
    stateless=True,
    memory_path="./memory",
)
