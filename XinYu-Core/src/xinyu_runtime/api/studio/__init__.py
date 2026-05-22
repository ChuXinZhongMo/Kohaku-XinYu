"""Studio backend  - embedded authoring studio for XinYu Runtime.

Exposes a composite FastAPI router mounted at /api/studio/* and
/ws/studio/* by the core api app. The whole subtree is isolated
from the rest of the framework: core code never imports from
``xinyu_runtime.api.studio`` (enforced by
``tests/unit/test_studio_independence.py``).

Modules here may import freely from ``xinyu_runtime.core``,
``xinyu_runtime.builtins``, ``xinyu_runtime.modules``,
``xinyu_runtime.packages``, ``xinyu_runtime.llm``, and
``xinyu_runtime.serving``  - read-only dependencies documented in
``plans/kt-studio/architecture.md section 9``.
"""

from xinyu_runtime.api.studio.app import build_studio_router

__all__ = ["build_studio_router"]

