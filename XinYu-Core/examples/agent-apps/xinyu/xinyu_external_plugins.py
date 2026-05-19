from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import Request, urlopen
import zipfile


PROTOCOL_VERSION = "xinyu.external.v1"

TRANSPORT_NATIVE_BRIDGE = "native_bridge"
TRANSPORT_HTTP = "http"
TRANSPORT_WEBSOCKET = "websocket"
TRANSPORT_HTTP_WS = "http_ws"
TRANSPORT_MCP = "mcp"
SUPPORTED_TRANSPORTS = (
    TRANSPORT_NATIVE_BRIDGE,
    TRANSPORT_HTTP,
    TRANSPORT_WEBSOCKET,
    TRANSPORT_HTTP_WS,
    TRANSPORT_MCP,
)

RISK_READ_ONLY = "read_only"
RISK_EXTERNAL_RUNTIME = "external_runtime"
RISK_DELEGATED_LOCAL = "delegated_local"
DEFAULT_HTTP_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RESPONSE_BYTES = 1024 * 1024
CONTROL_REL = Path("config/external_plugins.json")
DOWNLOAD_REL = Path("runtime/external_plugin_downloads")
INSTALL_REL = Path("runtime/external_plugins")


@dataclass(frozen=True)
class ExternalCapability:
    name: str
    transport: str
    risk: str
    proactive: bool = False
    requires_owner_private: bool = True
    requires_approval: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalPluginSpec:
    plugin_id: str
    title: str
    kind: str
    transport: str
    capabilities: dict[str, ExternalCapability]
    default_base_url: str = ""
    endpoint_env: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["capabilities"] = {
            name: capability.to_dict()
            for name, capability in self.capabilities.items()
        }
        return data


@dataclass(frozen=True)
class ExternalCallContext:
    source: str
    owner_private: bool
    reason: str = ""
    proactive: bool = False
    approved: bool = False


@dataclass(frozen=True)
class ExternalCallDecision:
    ok: bool
    reason: str
    risk: str = RISK_READ_ONLY
    requires_approval: bool = False
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalPreparedCall:
    protocol: str
    plugin_id: str
    capability: str
    decision: ExternalCallDecision
    request: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "plugin_id": self.plugin_id,
            "capability": self.capability,
            "decision": self.decision.to_dict(),
            "request": dict(self.request),
        }


def _env_get(env: Mapping[str, str] | None, key: str, default: str = "") -> str:
    source = os.environ if env is None else env
    value = source.get(key, default)
    return str(value or default).strip()


def _capability(
    name: str,
    *,
    transport: str,
    risk: str,
    proactive: bool,
    requires_owner_private: bool = True,
    requires_approval: bool = False,
    description: str = "",
) -> ExternalCapability:
    return ExternalCapability(
        name=name,
        transport=transport,
        risk=risk,
        proactive=proactive,
        requires_owner_private=requires_owner_private,
        requires_approval=requires_approval,
        description=description,
    )


def default_external_plugins(env: Mapping[str, str] | None = None) -> dict[str, ExternalPluginSpec]:
    kohaku_base_url = (
        _env_get(env, "XINYU_KOHAKU_BASE_URL")
        or _env_get(env, "KOHAKU_TERRARIUM_BASE_URL")
        or "http://127.0.0.1:8001"
    )
    return {
        "codex": ExternalPluginSpec(
            plugin_id="codex",
            title="Codex delegate",
            kind="operator",
            transport=TRANSPORT_NATIVE_BRIDGE,
            endpoint_env="",
            capabilities={
                "delegate_task": _capability(
                    "delegate_task",
                    transport=TRANSPORT_NATIVE_BRIDGE,
                    risk=RISK_DELEGATED_LOCAL,
                    proactive=True,
                    description="Delegate a bounded local investigation or implementation task through the existing Core Bridge Codex runner.",
                ),
                "local_write": _capability(
                    "local_write",
                    transport=TRANSPORT_NATIVE_BRIDGE,
                    risk=RISK_DELEGATED_LOCAL,
                    proactive=False,
                    requires_approval=True,
                    description="Owner-approved local file changes through the existing Codex self-code approval path.",
                ),
            },
            notes=(
                "Codex is a native bridge plugin, not a raw MCP tool.",
                "Writes stay behind the existing owner/self-code approval boundary.",
            ),
        ),
        "kohaku_terrarium": ExternalPluginSpec(
            plugin_id="kohaku_terrarium",
            title="KohakuTerrarium",
            kind="ecosystem_runtime",
            transport=TRANSPORT_HTTP_WS,
            default_base_url=kohaku_base_url,
            endpoint_env="XINYU_KOHAKU_BASE_URL",
            capabilities={
                "chat_creature": _capability(
                    "chat_creature",
                    transport=TRANSPORT_HTTP,
                    risk=RISK_EXTERNAL_RUNTIME,
                    proactive=True,
                    description="Send a non-streaming HTTP message to one Kohaku creature.",
                ),
                "ws_chat": _capability(
                    "ws_chat",
                    transport=TRANSPORT_WEBSOCKET,
                    risk=RISK_EXTERNAL_RUNTIME,
                    proactive=True,
                    description="Attach to Kohaku's bidirectional creature chat websocket.",
                ),
                "history": _capability(
                    "history",
                    transport=TRANSPORT_HTTP,
                    risk=RISK_READ_ONLY,
                    proactive=True,
                    description="Read one Kohaku creature's conversation history.",
                ),
                "command": _capability(
                    "command",
                    transport=TRANSPORT_HTTP,
                    risk=RISK_EXTERNAL_RUNTIME,
                    proactive=False,
                    requires_approval=True,
                    description="Execute a Kohaku slash command for one creature.",
                ),
            },
            notes=(
                "Kohaku already exposes FastAPI and websocket session surfaces.",
                "Its MCP package is a client manager for Kohaku agents to call external MCP servers.",
            ),
        ),
        "mcp_gateway": ExternalPluginSpec(
            plugin_id="mcp_gateway",
            title="MCP gateway",
            kind="protocol_adapter",
            transport=TRANSPORT_MCP,
            capabilities={
                "list_tools": _capability(
                    "list_tools",
                    transport=TRANSPORT_MCP,
                    risk=RISK_READ_ONLY,
                    proactive=True,
                    description="List tools exposed by a configured MCP server.",
                ),
                "call_tool": _capability(
                    "call_tool",
                    transport=TRANSPORT_MCP,
                    risk=RISK_EXTERNAL_RUNTIME,
                    proactive=False,
                    requires_approval=True,
                    description="Call a configured MCP server tool through a typed adapter.",
                ),
            },
            notes=(
                "MCP is a tool/resource transport, not XinYu's autonomy policy.",
                "Use MCP behind this gateway when a plugin already speaks MCP.",
            ),
        ),
    }


def external_plugin_manifest(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    registry = default_external_plugins(env)
    return {
        "protocol": PROTOCOL_VERSION,
        "supported_transports": list(SUPPORTED_TRANSPORTS),
        "plugins": [spec.to_dict() for spec in registry.values()],
    }


def _control_defaults(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    kohaku_path = (
        _env_get(env, "XINYU_KOHAKU_HOME")
        or _env_get(env, "KOHAKU_TERRARIUM_HOME")
        or _first_existing_path(
            [
                "E:\\KohakuTerrarium",
                "D:\\KohakuTerrarium",
                str(root / INSTALL_REL / "kohaku_terrarium"),
            ]
        )
    )
    return {
        "version": 1,
        "plugins": {
            "codex": {
                "enabled": True,
                "proactive_enabled": True,
                "config": {
                    "install_command": "npm.cmd",
                    "install_args": ["install", "-g", "@openai/codex"],
                },
            },
            "kohaku_terrarium": {
                "enabled": True,
                "proactive_enabled": False,
                "config": {
                    "base_url": _env_get(env, "XINYU_KOHAKU_BASE_URL") or "http://127.0.0.1:8001",
                    "install_path": kohaku_path,
                    "install_source_path": _env_get(env, "XINYU_KOHAKU_INSTALL_SOURCE"),
                    "download_url": _env_get(env, "XINYU_KOHAKU_DOWNLOAD_URL"),
                    "session_id": _env_get(env, "XINYU_KOHAKU_SESSION_ID"),
                    "creature_id": _env_get(env, "XINYU_KOHAKU_CREATURE_ID"),
                },
            },
            "mcp_gateway": {
                "enabled": False,
                "proactive_enabled": False,
                "config": {},
            },
        },
    }


def _first_existing_path(candidates: list[str]) -> str:
    for item in candidates:
        if item and Path(item).exists():
            return item
    return candidates[-1] if candidates else ""


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json_file(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def _merge_plugin_control(defaults: dict[str, Any], saved: Mapping[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(defaults, ensure_ascii=False))
    saved_plugins = saved.get("plugins") if isinstance(saved.get("plugins"), dict) else {}
    for plugin_id, saved_entry in saved_plugins.items():
        if not isinstance(saved_entry, dict):
            continue
        current = merged["plugins"].setdefault(plugin_id, {"enabled": False, "proactive_enabled": False, "config": {}})
        if "enabled" in saved_entry:
            current["enabled"] = bool(saved_entry.get("enabled"))
        if "proactive_enabled" in saved_entry:
            current["proactive_enabled"] = bool(saved_entry.get("proactive_enabled"))
        saved_config = saved_entry.get("config") if isinstance(saved_entry.get("config"), dict) else {}
        current_config = current.setdefault("config", {})
        for key, value in saved_config.items():
            if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                current_config[key] = value
    return merged


def load_external_plugin_control(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    defaults = _control_defaults(root, env)
    saved = _read_json_file(root / CONTROL_REL)
    return _merge_plugin_control(defaults, saved)


def save_external_plugin_control_patch(
    root: Path,
    patch: Mapping[str, Any],
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    control = load_external_plugin_control(root, env)
    plugin_id = str(patch.get("plugin_id") or patch.get("pluginId") or "").strip()
    if not plugin_id:
        raise ValueError("plugin_id is required")
    entry = control["plugins"].setdefault(plugin_id, {"enabled": False, "proactive_enabled": False, "config": {}})
    if "enabled" in patch:
        entry["enabled"] = bool(patch.get("enabled"))
    if "proactive_enabled" in patch or "proactiveEnabled" in patch:
        entry["proactive_enabled"] = bool(patch.get("proactive_enabled", patch.get("proactiveEnabled")))
    config_patch = patch.get("config") if isinstance(patch.get("config"), dict) else {}
    config = entry.setdefault("config", {})
    for key, value in config_patch.items():
        if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
            config[key] = value
    _write_json_file(root / CONTROL_REL, control)
    return external_plugin_status(root, env)


def _codex_install_status(config: Mapping[str, Any]) -> dict[str, Any]:
    path = shutil.which("codex") or shutil.which("codex.cmd") or ""
    npm = shutil.which(str(config.get("install_command") or "npm.cmd")) or shutil.which("npm.cmd") or shutil.which("npm") or ""
    return {
        "installed": bool(path),
        "installable": bool(npm),
        "path": path,
        "installer": npm,
        "missing_reason": "" if path else ("npm_missing" if not npm else "codex_cli_missing"),
    }


def _kohaku_install_status(config: Mapping[str, Any]) -> dict[str, Any]:
    install_path = str(config.get("install_path") or "").strip()
    path = Path(install_path) if install_path else Path()
    exe = path / "KohakuTerrarium.exe" if install_path else Path()
    app_route = path / "app" / "kohakuterrarium" / "api" / "app.py" if install_path else Path()
    installed = bool(install_path) and (exe.exists() or app_route.exists())
    source_path = str(config.get("install_source_path") or "").strip()
    download_url = str(config.get("download_url") or "").strip()
    source_ready = bool(source_path) and Path(source_path).exists()
    return {
        "installed": installed,
        "installable": source_ready or bool(download_url),
        "path": str(path) if install_path else "",
        "installer": source_path or download_url,
        "missing_reason": "" if installed else ("install_source_missing" if not source_ready and not download_url else "kohaku_missing"),
    }


def _plugin_install_status(plugin_id: str, config: Mapping[str, Any]) -> dict[str, Any]:
    if plugin_id == "codex":
        return _codex_install_status(config)
    if plugin_id == "kohaku_terrarium":
        return _kohaku_install_status(config)
    if plugin_id == "mcp_gateway":
        return {
            "installed": True,
            "installable": False,
            "path": "builtin",
            "installer": "",
            "missing_reason": "",
        }
    return {
        "installed": False,
        "installable": False,
        "path": "",
        "installer": "",
        "missing_reason": "unknown_plugin",
    }


def external_plugin_status(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    manifest = external_plugin_manifest(env)
    registry = {item["plugin_id"]: item for item in manifest["plugins"] if isinstance(item, dict) and item.get("plugin_id")}
    control = load_external_plugin_control(root, env)
    items: list[dict[str, Any]] = []
    for plugin_id, spec in registry.items():
        entry = control["plugins"].get(plugin_id, {}) if isinstance(control.get("plugins"), dict) else {}
        config = entry.get("config") if isinstance(entry.get("config"), dict) else {}
        install = _plugin_install_status(plugin_id, config)
        items.append(
            {
                **spec,
                "enabled": bool(entry.get("enabled")),
                "proactive_enabled": bool(entry.get("proactive_enabled")),
                "installed": bool(install.get("installed")),
                "installable": bool(install.get("installable")),
                "install": install,
                "config": config,
                "available": bool(entry.get("enabled")) and bool(install.get("installed")),
            }
        )
    return {
        "ok": True,
        "protocol": PROTOCOL_VERSION,
        "config_path": str(root / CONTROL_REL),
        "manifest": manifest,
        "plugins": items,
        "notes": ["external_plugin_status"],
    }


def external_plugin_runtime_allowed(
    root: Path,
    plugin_id: str,
    *,
    proactive: bool = False,
    env: Mapping[str, str] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    status = external_plugin_status(root, env)
    for item in status.get("plugins", []):
        if isinstance(item, dict) and item.get("plugin_id") == plugin_id:
            if not bool(item.get("enabled")):
                return False, "plugin_disabled", item
            if proactive and not bool(item.get("proactive_enabled")):
                return False, "plugin_proactive_disabled", item
            if not bool(item.get("installed")):
                return False, "plugin_not_installed", item
            return True, "allowed", item
    return False, "plugin_not_registered", {}


def _copytree_replace(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


def _download_plugin_archive(url: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    name = Path(urlparse(url).path).name or "plugin-download"
    path = target_dir / name
    with urlopen(url, timeout=120) as response:
        path.write_bytes(response.read())
    return path


def install_external_plugin(root: Path, plugin_id: str, options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    options = options or {}
    status = external_plugin_status(root)
    plugin = next((item for item in status.get("plugins", []) if isinstance(item, dict) and item.get("plugin_id") == plugin_id), None)
    if not isinstance(plugin, dict):
        raise ValueError(f"plugin not registered: {plugin_id}")
    if bool(plugin.get("installed")):
        return {"ok": True, "installed": True, "plugin_id": plugin_id, "status": external_plugin_status(root), "notes": ["already_installed"]}
    config = plugin.get("config") if isinstance(plugin.get("config"), dict) else {}

    if plugin_id == "codex":
        command = str(config.get("install_command") or "npm.cmd")
        args = [str(item) for item in config.get("install_args", ["install", "-g", "@openai/codex"]) if str(item)]
        executable = shutil.which(command) or shutil.which("npm.cmd") or shutil.which("npm")
        if not executable:
            return {"ok": False, "installed": False, "plugin_id": plugin_id, "error_code": "npm_missing", "notes": ["codex_installer_missing"]}
        completed = subprocess.run(
            [executable, *args],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10 * 60,
        )
        return {
            "ok": completed.returncode == 0,
            "installed": completed.returncode == 0 and bool(shutil.which("codex") or shutil.which("codex.cmd")),
            "plugin_id": plugin_id,
            "exit_code": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "status": external_plugin_status(root),
            "notes": ["codex_install_command_finished"],
        }

    if plugin_id == "kohaku_terrarium":
        target = Path(str(options.get("install_path") or config.get("install_path") or root / INSTALL_REL / "kohaku_terrarium"))
        source = Path(str(options.get("source_path") or config.get("install_source_path") or ""))
        url = str(options.get("download_url") or config.get("download_url") or "").strip()
        if source.exists():
            _copytree_replace(source, target)
        elif url:
            archive = _download_plugin_archive(url, root / DOWNLOAD_REL)
            if archive.suffix.lower() == ".zip":
                if target.exists():
                    shutil.rmtree(target)
                target.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(archive) as handle:
                    handle.extractall(target)
            else:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(archive, target / archive.name)
        else:
            return {
                "ok": False,
                "installed": False,
                "plugin_id": plugin_id,
                "error_code": "missing_install_source",
                "status": status,
                "notes": ["kohaku_install_source_required"],
            }
        save_external_plugin_control_patch(
            root,
            {
                "plugin_id": plugin_id,
                "enabled": True,
                "config": {"install_path": str(target)},
            },
        )
        return {"ok": True, "installed": True, "plugin_id": plugin_id, "status": external_plugin_status(root), "notes": ["kohaku_installed"]}

    return {"ok": False, "installed": False, "plugin_id": plugin_id, "error_code": "no_installer", "notes": ["plugin_has_no_installer"]}


def evaluate_external_call(
    registry: Mapping[str, ExternalPluginSpec],
    plugin_id: str,
    capability_name: str,
    context: ExternalCallContext,
) -> ExternalCallDecision:
    spec = registry.get(plugin_id)
    if spec is None:
        return ExternalCallDecision(
            ok=False,
            reason="plugin_not_registered",
            notes=(f"plugin_id:{plugin_id}",),
        )
    capability = spec.capabilities.get(capability_name)
    if capability is None:
        return ExternalCallDecision(
            ok=False,
            reason="capability_not_registered",
            notes=(f"plugin_id:{plugin_id}", f"capability:{capability_name}"),
        )
    if capability.requires_owner_private and not context.owner_private:
        return ExternalCallDecision(
            ok=False,
            reason="owner_private_required",
            risk=capability.risk,
            notes=(f"plugin_id:{plugin_id}", f"capability:{capability_name}"),
        )
    if context.proactive and not capability.proactive:
        return ExternalCallDecision(
            ok=False,
            reason="proactive_not_allowed_for_capability",
            risk=capability.risk,
            notes=(f"plugin_id:{plugin_id}", f"capability:{capability_name}"),
        )
    if context.proactive and not context.reason.strip():
        return ExternalCallDecision(
            ok=False,
            reason="concrete_reason_required",
            risk=capability.risk,
            notes=(f"plugin_id:{plugin_id}", f"capability:{capability_name}"),
        )
    if capability.requires_approval and not context.approved:
        return ExternalCallDecision(
            ok=False,
            reason="approval_required",
            risk=capability.risk,
            requires_approval=True,
            notes=(f"plugin_id:{plugin_id}", f"capability:{capability_name}"),
        )
    return ExternalCallDecision(
        ok=True,
        reason="allowed",
        risk=capability.risk,
        requires_approval=False,
        notes=(f"transport:{capability.transport}", f"source:{context.source}"),
    )


def _path_part(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return quote(text, safe="")


def _http_base(base_url: str) -> str:
    base = str(base_url or "").strip() or "http://127.0.0.1:8001"
    return base.rstrip("/")


def _ws_base(base_url: str) -> str:
    parsed = urlparse(_http_base(base_url))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", "")).rstrip("/")


def build_kohaku_request(
    spec: ExternalPluginSpec,
    capability_name: str,
    args: Mapping[str, Any],
) -> dict[str, Any]:
    base_url = _http_base(str(args.get("base_url") or spec.default_base_url))
    session_id = _path_part(args.get("session_id"), "session_id")
    creature_id = _path_part(args.get("creature_id"), "creature_id")
    path = f"/api/sessions/{session_id}/creatures/{creature_id}"
    if capability_name == "chat_creature":
        body: dict[str, Any] = {}
        if "content" in args:
            body["content"] = args.get("content")
        else:
            body["message"] = str(args.get("message") or "")
        return {
            "transport": TRANSPORT_HTTP,
            "method": "POST",
            "url": f"{base_url}{path}/chat",
            "json": body,
        }
    if capability_name == "history":
        return {
            "transport": TRANSPORT_HTTP,
            "method": "GET",
            "url": f"{base_url}{path}/history",
        }
    if capability_name == "command":
        return {
            "transport": TRANSPORT_HTTP,
            "method": "POST",
            "url": f"{base_url}{path}/command",
            "json": {
                "command": str(args.get("command") or "").strip(),
                "args": str(args.get("args") or ""),
            },
        }
    if capability_name == "ws_chat":
        frame: dict[str, Any] = {"type": "input"}
        if "content" in args:
            frame["content"] = args.get("content")
        else:
            frame["message"] = str(args.get("message") or "")
        if args.get("target"):
            frame["target"] = str(args.get("target"))
        return {
            "transport": TRANSPORT_WEBSOCKET,
            "url": f"{_ws_base(base_url)}/ws/sessions/{session_id}/creatures/{creature_id}/chat",
            "send_frame": frame,
        }
    raise ValueError(f"unsupported Kohaku capability: {capability_name}")


def build_codex_request(capability_name: str, args: Mapping[str, Any]) -> dict[str, Any]:
    task_text = str(args.get("task_text") or args.get("message") or "").strip()
    if not task_text:
        raise ValueError("task_text is required")
    payload = {
        "text": task_text,
        "raw_owner_task": task_text,
        "source": str(args.get("source") or "external_plugin_gateway"),
        "background": bool(args.get("background", True)),
        "auto_study": bool(args.get("auto_study", capability_name == "delegate_task")),
    }
    metadata = args.get("metadata")
    if isinstance(metadata, dict):
        payload["metadata"] = dict(metadata)
    return {
        "transport": TRANSPORT_NATIVE_BRIDGE,
        "bridge_method": "codex_execute",
        "payload": payload,
    }


def build_mcp_gateway_request(capability_name: str, args: Mapping[str, Any]) -> dict[str, Any]:
    if capability_name == "list_tools":
        return {
            "transport": TRANSPORT_MCP,
            "server": str(args.get("server") or "").strip(),
            "operation": "list_tools",
        }
    if capability_name == "call_tool":
        return {
            "transport": TRANSPORT_MCP,
            "server": str(args.get("server") or "").strip(),
            "operation": "call_tool",
            "tool": str(args.get("tool") or "").strip(),
            "args": args.get("args") if isinstance(args.get("args"), dict) else {},
        }
    raise ValueError(f"unsupported MCP gateway capability: {capability_name}")


def prepare_external_call(
    plugin_id: str,
    capability_name: str,
    args: Mapping[str, Any],
    context: ExternalCallContext,
    *,
    registry: Mapping[str, ExternalPluginSpec] | None = None,
) -> ExternalPreparedCall:
    active_registry = default_external_plugins() if registry is None else registry
    decision = evaluate_external_call(active_registry, plugin_id, capability_name, context)
    if not decision.ok:
        return ExternalPreparedCall(PROTOCOL_VERSION, plugin_id, capability_name, decision)

    spec = active_registry[plugin_id]
    try:
        if plugin_id == "kohaku_terrarium":
            request = build_kohaku_request(spec, capability_name, args)
        elif plugin_id == "codex":
            request = build_codex_request(capability_name, args)
        elif plugin_id == "mcp_gateway":
            request = build_mcp_gateway_request(capability_name, args)
        else:
            request = {
                "transport": spec.capabilities[capability_name].transport,
                "args": dict(args),
            }
    except ValueError as exc:
        decision = ExternalCallDecision(
            ok=False,
            reason="invalid_arguments",
            risk=spec.capabilities[capability_name].risk,
            notes=(str(exc),),
        )
        return ExternalPreparedCall(PROTOCOL_VERSION, plugin_id, capability_name, decision)

    return ExternalPreparedCall(
        PROTOCOL_VERSION,
        plugin_id,
        capability_name,
        decision,
        request=request,
    )


def _safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _decode_response(data: bytes) -> tuple[Any, str]:
    text = data.decode("utf-8", errors="replace")
    parsed = _safe_json_loads(text)
    if parsed is not None:
        return parsed, text
    return None, text


def execute_http_prepared_call(
    prepared: ExternalPreparedCall | Mapping[str, Any],
    *,
    timeout_seconds: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    value = prepared.to_dict() if isinstance(prepared, ExternalPreparedCall) else dict(prepared)
    request = value.get("request") if isinstance(value.get("request"), dict) else {}
    if request.get("transport") != TRANSPORT_HTTP:
        return {
            "ok": False,
            "executed": False,
            "transport": request.get("transport", ""),
            "error_code": "transport_not_http",
            "notes": ["execute_http_prepared_call only handles HTTP prepared calls"],
        }

    method = str(request.get("method") or "GET").upper()
    url = str(request.get("url") or "").strip()
    if not url:
        return {
            "ok": False,
            "executed": False,
            "transport": TRANSPORT_HTTP,
            "error_code": "missing_url",
            "notes": ["prepared HTTP call has no URL"],
        }

    body = None
    headers = {"Accept": "application/json, text/plain;q=0.9, */*;q=0.5"}
    if "json" in request:
        body = json.dumps(request.get("json"), ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    started = time.perf_counter()
    try:
        http_request = Request(url, data=body, method=method, headers=headers)
        with urlopen(http_request, timeout=max(1, int(timeout_seconds))) as response:
            status_code = int(getattr(response, "status", 0) or response.getcode())
            raw = response.read(max(1, int(max_response_bytes)))
        parsed, text = _decode_response(raw)
        return {
            "ok": 200 <= status_code < 300,
            "executed": True,
            "transport": TRANSPORT_HTTP,
            "method": method,
            "url": url,
            "status_code": status_code,
            "json": parsed,
            "text_preview": text[:4000],
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error_code": "" if 200 <= status_code < 300 else "http_status_error",
            "notes": [],
        }
    except HTTPError as exc:
        raw = exc.read(max(1, int(max_response_bytes)))
        parsed, text = _decode_response(raw)
        return {
            "ok": False,
            "executed": True,
            "transport": TRANSPORT_HTTP,
            "method": method,
            "url": url,
            "status_code": int(exc.code),
            "json": parsed,
            "text_preview": text[:4000],
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error_code": "http_error",
            "notes": [str(exc.reason)],
        }
    except (TimeoutError, URLError, OSError) as exc:
        return {
            "ok": False,
            "executed": False,
            "transport": TRANSPORT_HTTP,
            "method": method,
            "url": url,
            "status_code": 0,
            "json": None,
            "text_preview": "",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error_code": type(exc).__name__,
            "notes": [str(exc)],
        }
