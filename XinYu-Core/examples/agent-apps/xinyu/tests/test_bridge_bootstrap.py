from __future__ import annotations

from types import SimpleNamespace

import xinyu_bridge_bootstrap


def test_runtime_load_runtime_short_circuits_when_loaded(tmp_path) -> None:
    calls: list[str] = []
    runtime = SimpleNamespace(_loaded=True, xinyu_dir=tmp_path)

    xinyu_bridge_bootstrap.runtime_load_runtime(
        runtime,
        chdir=lambda path: calls.append("chdir"),
        load_local_env_func=lambda path: calls.append("env"),
        enforce_llm_http_guard_func=lambda: calls.append("guard"),
        ensure_repo_src_func=lambda path: calls.append("src"),
        import_module=lambda name: calls.append(name),
    )

    assert calls == []


def test_runtime_load_runtime_wires_runtime_classes(tmp_path) -> None:
    calls: list[tuple[str, object]] = []

    class Agent:
        pass

    class TriggerEvent:
        pass

    def create_user_input_event():
        pass

    def fake_import(name: str):
        calls.append(("import", name))
        if name == "xinyu_runtime.core.agent":
            return SimpleNamespace(Agent=Agent)
        if name == "xinyu_runtime.core.events":
            return SimpleNamespace(
                TriggerEvent=TriggerEvent,
                create_user_input_event=create_user_input_event,
            )
        raise AssertionError(name)

    runtime = SimpleNamespace(
        _loaded=False,
        xinyu_dir=tmp_path,
        _agent_cls=None,
        _create_user_input_event=None,
        _trigger_event_cls=None,
    )

    xinyu_bridge_bootstrap.runtime_load_runtime(
        runtime,
        chdir=lambda path: calls.append(("chdir", path)),
        load_local_env_func=lambda path: calls.append(("env", path)),
        enforce_llm_http_guard_func=lambda: calls.append(("guard", "")),
        ensure_repo_src_func=lambda path: calls.append(("src", path)),
        import_module=fake_import,
    )

    assert calls == [
        ("chdir", tmp_path),
        ("env", tmp_path),
        ("guard", ""),
        ("src", tmp_path),
        ("import", "xinyu_runtime.core.agent"),
        ("import", "xinyu_runtime.core.events"),
    ]
    assert runtime._agent_cls is Agent
    assert runtime._create_user_input_event is create_user_input_event
    assert runtime._trigger_event_cls is TriggerEvent
    assert runtime._loaded is True
