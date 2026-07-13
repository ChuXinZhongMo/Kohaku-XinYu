"""Owner-facing control panel for the human-voice language flags.

A self-contained "extension panel" (扩展栏位) served same-origin by the bridge
HTTP server, with three toggles that flip the human-voice feature flags at
runtime (they are read live from ``os.environ``) and optionally persist them to
``xinyu.local.env`` for the next launch.

Routes (wired in xinyu_bridge_http_handler):
- GET  /extension/voice-flags        -> the HTML panel (text/html)
- GET  /extension/voice-flags/state  -> current flag state (JSON)
- POST /extension/voice-flags/update -> set flags, return new state (JSON)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_stores import (
    read_voice_flag_env,
    read_voice_flags_env_file_lines,
    write_voice_flag_env,
    write_voice_flags_env_file_lines,
)

VOICE_FLAGS_PANEL_ROUTE = "/extension/voice-flags"
VOICE_FLAGS_STATE_ROUTE = "/extension/voice-flags/state"
VOICE_FLAGS_UPDATE_ROUTE = "/extension/voice-flags/update"

# key -> (env var, label, description)
_FLAG_SPECS: tuple[tuple[str, str, str, str], ...] = (
    (
        "unified_voice",
        "XINYU_HUMAN_VOICE_UNIFIED_PROMPT",
        "统一声音（阶段1）",
        "让主路、渲染器、慢推理共用同一份人格之声 + 薄表达契约：厚思考、薄表达，不复盘不念状态。风险最低，建议先开。",
    ),
    (
        "bypass_model",
        "XINYU_HUMAN_VOICE_BYPASS_MODEL",
        "旁路改模型生成（阶段2/5）",
        "owner 私聊的快速旁路不再吐写死固定串，先走模型生成，失败才退回固定串；功能型通知打标记保留。影响最直接。",
    ),
    (
        "regen_pipeline",
        "XINYU_HUMAN_VOICE_REGEN_PIPELINE",
        "后处理重写（阶段3/4）",
        "后处理里那些把模型原话换成固定串的步骤改为清空→模型重生成，固定串只作最后保险。",
    ),
    (
        "group_social",
        "XINYU_GROUP_SOCIAL_ENABLED",
        "群聊社会记忆",
        "记住群里共同经历、每个群友在本群的身份和称呼；B/C 提到 A 时知道 A 是谁、按群内真实叫法称呼，不串群、不输出 QQ 号。",
    ),
    (
        "qq_voice_private",
        "XINYU_QQ_VOICE_REPLY_PRIVATE",
        "QQ private voice reply",
        "Send private-chat replies as QQ voice clips when synthesis succeeds; fall back to text on failure.",
    ),
    (
        "qq_voice_group",
        "XINYU_QQ_VOICE_REPLY_GROUP",
        "QQ group voice reply",
        "Send group-chat replies as QQ voice clips when synthesis succeeds; fall back to text on failure.",
    ),
)

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_true(name: str) -> bool:
    return read_voice_flag_env(name).strip().lower() in _TRUE_VALUES


def read_voice_flags_state() -> dict[str, Any]:
    """Current flag state read live from os.environ."""

    flags = {key: _env_true(env) for key, env, _label, _desc in _FLAG_SPECS}
    return {"ok": True, "flags": flags}


def apply_voice_flags_update(payload: dict[str, Any], *, env_file: Path | None = None) -> dict[str, Any]:
    """Set provided flags in os.environ (takes effect immediately) and, when
    ``persist`` is truthy, upsert them into xinyu.local.env for the next launch.
    """

    requested = payload.get("flags")
    if not isinstance(requested, dict):
        # Allow flat {key: bool} payloads too.
        requested = {key: payload[key] for key, *_ in _FLAG_SPECS if key in payload}
    persist = bool(payload.get("persist"))

    changed: dict[str, str] = {}
    for key, env, _label, _desc in _FLAG_SPECS:
        if key not in requested:
            continue
        value = "1" if _coerce_bool(requested[key]) else "0"
        write_voice_flag_env(env, value)
        changed[env] = value

    if persist and changed and env_file is not None:
        _persist_env(env_file, changed)

    state = read_voice_flags_state()
    state["changed"] = sorted(changed)
    state["persisted"] = bool(persist and changed)
    return state


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in _TRUE_VALUES


def _persist_env(env_file: Path, changed: dict[str, str]) -> None:
    """Upsert ``KEY=value`` lines into the env file without disturbing the rest."""

    lines = read_voice_flags_env_file_lines(env_file)
    remaining = dict(changed)
    out: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else ""
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(raw)
    out.extend(f"{key}={value}" for key, value in remaining.items())
    try:
        write_voice_flags_env_file_lines(env_file, out)
    except OSError as exc:
        print(f"[xinyu_core_bridge] voice flags persist failed: {exc}", flush=True)


def render_voice_flags_panel_html() -> str:
    """Self-contained HTML panel; fetches state/update same-origin (no CORS)."""

    state = read_voice_flags_state()["flags"]
    rows = "\n".join(
        f"""
      <div class="row">
        <label class="switch">
          <input type="checkbox" data-key="{key}" {"checked" if state[key] else ""}>
          <span class="slider"></span>
        </label>
        <div class="meta">
          <div class="title">{label}</div>
          <div class="desc">{desc}</div>
          <code class="env">{env}</code>
        </div>
      </div>"""
        for key, env, label, desc in _FLAG_SPECS
    )
    return _PANEL_TEMPLATE.replace("{{ROWS}}", rows)


_PANEL_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XinYu · 语言语句控制</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
         background:#15171c; color:#e8eaed; padding:24px; }
  .card { max-width:680px; margin:0 auto; background:#1d2026; border:1px solid #2a2e36;
          border-radius:14px; padding:22px 24px; }
  h1 { font-size:18px; margin:0 0 4px; }
  .sub { color:#9aa0a6; font-size:13px; margin:0 0 18px; }
  .row { display:flex; gap:16px; align-items:flex-start; padding:16px 0; border-top:1px solid #2a2e36; }
  .meta .title { font-weight:600; font-size:15px; }
  .meta .desc { color:#b6bbc2; font-size:13px; line-height:1.6; margin:4px 0 6px; }
  .meta .env { color:#7f8896; font-size:11px; background:#14161a; padding:2px 6px; border-radius:5px; }
  .switch { position:relative; display:inline-block; width:46px; height:26px; flex:0 0 auto; margin-top:2px; }
  .switch input { opacity:0; width:0; height:0; }
  .slider { position:absolute; inset:0; cursor:pointer; background:#3a3f49; border-radius:26px; transition:.2s; }
  .slider:before { content:""; position:absolute; height:20px; width:20px; left:3px; bottom:3px;
                   background:#fff; border-radius:50%; transition:.2s; }
  input:checked + .slider { background:#4f8cff; }
  input:checked + .slider:before { transform:translateX(20px); }
  .foot { display:flex; align-items:center; gap:14px; margin-top:20px; padding-top:16px; border-top:1px solid #2a2e36; }
  .persist { display:flex; align-items:center; gap:7px; color:#b6bbc2; font-size:13px; }
  .status { margin-left:auto; font-size:13px; color:#9aa0a6; min-height:18px; }
  .status.ok { color:#5ad27e; } .status.err { color:#ff6b6b; }
</style>
</head>
<body>
  <div class="card">
    <h1>语言语句控制</h1>
    <p class="sub">控制 XinYu 对话"像不像人"的三个开关。改动即时生效（运行时读取）；勾选"写入本地配置"可在重启后保留。</p>
    {{ROWS}}
    <div class="foot">
      <label class="persist"><input type="checkbox" id="persist"> 写入本地配置（重启后保留）</label>
      <span class="status" id="status"></span>
    </div>
  </div>
<script>
  const statusEl = document.getElementById("status");
  function setStatus(msg, cls) { statusEl.textContent = msg; statusEl.className = "status " + (cls || ""); }
  async function save(key, value) {
    const persist = document.getElementById("persist").checked;
    try {
      const res = await fetch("/extension/voice-flags/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ flags: { [key]: value }, persist }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setStatus((value ? "已开启 " : "已关闭 ") + key + (data.persisted ? "（已写入配置）" : "（仅本次运行）"), "ok");
    } catch (e) {
      setStatus("保存失败：" + e.message, "err");
    }
  }
  document.querySelectorAll('input[type=checkbox][data-key]').forEach(cb => {
    cb.addEventListener("change", () => save(cb.dataset.key, cb.checked));
  });
</script>
</body>
</html>
"""
