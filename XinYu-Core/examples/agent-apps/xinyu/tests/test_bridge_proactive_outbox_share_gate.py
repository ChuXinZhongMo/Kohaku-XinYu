from __future__ import annotations

from pathlib import Path

from xinyu_bridge_proactive_delivery_routes import claim_proactive_for_qq_outbox_sync
from xinyu_private_ecosystem_grants import save_grants_patch


class FakeRuntime:
    proactive_min_interval_seconds = 0
    memory_root = None

    def __init__(self, root: Path) -> None:
        self.xinyu_dir = root

    def _ready_proactive_outbox_candidate(self) -> dict[str, object]:
        return {"candidateId": "candidate-1"}

    def _owner_private_user_id(self) -> str:
        return "owner-1"


def test_qq_outbox_proactive_fallback_blocks_when_owner_private_share_paused(tmp_path: Path) -> None:
    save_grants_patch(tmp_path, {"owner_private_autonomous_share": {"enabled": True, "paused": True}})
    runtime = FakeRuntime(tmp_path)

    result = claim_proactive_for_qq_outbox_sync(runtime, {"claim_id": "claim-paused"})

    assert result is None
