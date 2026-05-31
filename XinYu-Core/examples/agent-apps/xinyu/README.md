# XinYu App

Language: [中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

Research package: [INTERACTIVITY-RESEARCH.md](INTERACTIVITY-RESEARCH.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [TRACE-SCHEMA.md](TRACE-SCHEMA.md) | [FAILURE-SCENARIOS.md](FAILURE-SCENARIOS.md)

XinYu 是一个本地 owner 运营的长期交互 agent 项目。目标不是做一个只会单轮回答的聊天机器人，而是让系统在长期互动中保持连续性：能观察自己卡在哪、能通过审查边界沉淀记忆、能调整表达，并且只在明确授权和可审计的情况下主动联系 owner。

## 必读目标锚点

继续修改主动性、记忆、自行动作、表达层或运行时之前，先读项目根目录的 `docs/system/心玉最终目标.md`。该文件定义最终目标：让 XinYu 形成有边界、可验证、能被反馈修正的自我生成闭环，而不是只增加更像人的话术或更多主动消息。

## 当前运行链路

```text
NapCat QQ
  -> ws://127.0.0.1:6199/ws
  -> xinyu_qq_gateway.py
  -> http://127.0.0.1:8765/chat
  -> xinyu_core_bridge.py
  -> XinYu runtime
```

`xinyu_qq_gateway.py` 只负责 transport：白名单、群触发、消息归一化、OneBot 回复、outbox claim/ack。人格、记忆、主动性、回复策略和干预状态都在 core bridge/runtime 侧。

## 主要入口

- `xinyu_core_bridge.py`：HTTP bridge，提供 `/chat`、`/health`、`/turn/*`、learning、Codex、proactive 等接口。
- `xinyu_qq_gateway.py`：NapCat / OneBot QQ gateway。
- `xinyu_local_inspector.py`：本地只读 inspector，可查看 turn、route timeline、gateway、proactive、memory candidate 和 stale warnings。
- `xinyu_status.py`：运行状态检查。
- `xinyu_proactive_request_loop.py` / `xinyu_proactive_presence.py`：主动候选、claim、ack、冷却和生命周期 trace。
- `xinyu_memory_candidate_review_cli.py`：候选记忆审查 CLI。
- `xinyu_v1/`：v1 shadow/canary 骨架，不是默认全量主路径。

## 本地启动

进入目录：

```powershell
cd path\to\XinYu-Core\examples\agent-apps\xinyu
```

创建本地环境文件：

```powershell
copy xinyu.local.env.example xinyu.local.env
```

至少填写：

```text
XINYU_API_KEY=
XINYU_BASE_URL=
XINYU_LLM_MODEL=
```

安装最小依赖：

```powershell
python -m pip install -r requirements-minimal.txt
```

启动 core bridge：

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
```

启动 QQ gateway：

```powershell
.\start_xinyu_qq_gateway.ps1
```

停止：

```powershell
.\stop_xinyu_qq_gateway.ps1
.\stop_xinyu_core_bridge.ps1
```

## 状态检查

```powershell
python xinyu_status.py
python xinyu_status.py --json
```

本地 inspector：

```powershell
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network --json
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network dashboard
```

常用 turn intervention：

```powershell
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene current
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene status-message
.\.venv\Scripts\python.exe xinyu_local_inspector.py intervene cancel
```

## 测试

全量 pytest：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

关键 smoke：

```powershell
.\.venv\Scripts\python.exe tests\smoke\initiative\proactive_presence_smoke.py
.\.venv\Scripts\python.exe tests\smoke\initiative\proactive_request_loop_smoke.py
.\.venv\Scripts\python.exe tests\smoke\desktop\xinyu_desktop_proactive_smoke.py
.\.venv\Scripts\python.exe tests\smoke\qq\integration\xinyu_qq_gateway_smoke.py
```

语法检查：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_qq_gateway.py xinyu_status.py xinyu_local_inspector.py
```

## 研究与公开材料

- `INTERACTIVITY-RESEARCH.md`：项目研究问题、证据和限制。
- `ARCHITECTURE.md`：当前架构与干预 API 图。
- `TRACE-SCHEMA.md`：可公开 trace 字段说明。
- `FAILURE-SCENARIOS.md` / `failure-scenarios/`：脱敏 failure scenario 包。
- `LOCAL-INSPECTOR-DEMO.md`：截图/演示边界。
- `GRANT-PROGRESS-REPORT-TEMPLATE.md`：研究进度报告模板。
- `MEMORY-LAYERS.md` / `PRIVACY-BOUNDARY.md`：记忆与隐私边界。
- `EXPRESSION-STABILITY.md`：表达稳定性回归边界。

## 本地私有状态

这些路径是本地运行状态，不应上传公开仓库：

- `xinyu.local.env`
- `xinyu_qq_gateway.config.json`
- `logs/`
- `memory/`
- `runtime/`
- `learning/self_found/`
- `learning/owner_supplied/`

公开报告、截图和 trace 示例必须避免包含原始 owner 聊天、完整 QQ ID、token、cookie、API key 和本地绝对路径。
