from __future__ import annotations

from xinyu_bridge_stores import desktop_service_path_exists


def test_desktop_service_status_store_checks_path_existence(tmp_path) -> None:
    path = tmp_path / "memory"

    assert desktop_service_path_exists(path) is False

    path.mkdir()

    assert desktop_service_path_exists(path) is True
