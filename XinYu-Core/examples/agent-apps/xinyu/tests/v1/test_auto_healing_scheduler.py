from __future__ import annotations

from pathlib import Path

from xinyu_v1.autonomy.scheduler import AutoHealingScheduler
from xinyu_v1.config import XinYuV1Config


async def test_auto_healing_refuses_active_request(tmp_path, monkeypatch) -> None:
    root = tmp_path / "xinyu"
    (root / "prompts").mkdir(parents=True)
    (root / "memory").mkdir()
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    monkeypatch.setenv("XINYU_V1_RUNTIME_MODE", "test")

    config = XinYuV1Config.load(Path(root))
    scheduler = AutoHealingScheduler(config.paths, config.maintenance)
    scheduler.idle.request_started()
    report = await scheduler.run_once_if_idle()

    assert report.ran is False
    assert "not_idle" in report.notes

