"""Procedural skill system (Cluster 4, Wave 2-未).

A **procedural skill** is a reusable markdown how-to bundle that lives
in a folder such as ``.kt/skills/<name>/SKILL.md`` or
``~/.xinyu/skills/<name>/SKILL.md``. Skills are model-readable
procedural knowledge  - the framework does **not** execute scripts for
the model; it merely renders the skill body into the conversation when
the skill is invoked.

Three distinct invocation routes (triple-invocation, Qd in the locked
spec):

1. ``paths:`` frontmatter  - auto-activates a hint when the cwd contains
   files matching its globs (:mod:`xinyu_runtime.skills.paths`).
2. The built-in ``skill`` tool  - model-invoked, returns the SKILL.md body
   as a tool response. A legacy text-format controller command remains for
   non-native tool formats (:mod:`xinyu_runtime.skills.command`).
3. ``/<skill-name> [args]`` user slash command  - injects a user-turn
   preamble that asks the model to follow the skill
   (:mod:`xinyu_runtime.skills.user_slash`).

Vocabulary distinction (Qc): *tool references* live in
``builtin_skills/tools/<name>.md`` and document registered
:class:`BaseTool` / :class:`BaseSubAgent` classes; they are read via the
``info`` tool. *Skills* are procedural bundles and are
**never** shipped as built-ins  - only via user/project dirs or
third-party packages.
"""

from xinyu_runtime.skills.command import SkillCommand
from xinyu_runtime.skills.discovery import (
    PROJECT_SKILL_ROOTS,
    USER_SKILL_ROOTS,
    discover_skills,
    load_skill_from_path,
)
from xinyu_runtime.skills.index import (
    DEFAULT_SKILL_INDEX_BUDGET_BYTES,
    build_skill_index,
)
from xinyu_runtime.skills.paths import SkillPathScanner
from xinyu_runtime.skills.registry import SCRATCHPAD_ENABLED_KEY, Skill, SkillRegistry
from xinyu_runtime.skills.user_slash import build_user_skill_turn

__all__ = (
    "DEFAULT_SKILL_INDEX_BUDGET_BYTES",
    "PROJECT_SKILL_ROOTS",
    "SCRATCHPAD_ENABLED_KEY",
    "USER_SKILL_ROOTS",
    "Skill",
    "SkillCommand",
    "SkillPathScanner",
    "SkillRegistry",
    "build_skill_index",
    "build_user_skill_turn",
    "discover_skills",
    "load_skill_from_path",
)

