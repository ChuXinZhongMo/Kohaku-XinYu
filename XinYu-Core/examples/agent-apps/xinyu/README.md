# XinYu App

这个目录是 XinYu 的主开发入口：提示词、运行入口、记忆引擎、bridge、QQ gateway、状态检查、v1 重构骨架和 smoke 测试都在这里。

XinYu 的目标不是“回答得像人”这么简单，而是让一个 AI 系统在长期交互中维持连续性：记住关系、调整表达、审查自身变化，并在被允许时主动联系 owner。

## 当前运行链路

```text
NapCatQQ
  -> ws://127.0.0.1:6199/ws
  -> xinyu_qq_gateway.py
  -> http://127.0.0.1:8765/chat
  -> xinyu_core_bridge.py
  -> XinYu Core
```

AstrBot 已经不是当前运行链路的一部分。当前 QQ 侧由仓库内的原生 `xinyu_qq_gateway.py` 处理：白名单、群触发、消息归一化、OneBot 回复和转发到 Core。

## 目录内容

核心运行文件：

- `config.yaml` - XinYu 运行时配置
- `run_local_xinyu.py` / `run_local_xinyu.ps1` - 本地运行入口
- `xinyu_core_bridge.py` - 给外部 shell / gateway 使用的 HTTP bridge
- `xinyu_qq_gateway.py` - 原生 NapCat / OneBot QQ gateway
- `xinyu_proactive_presence.py` - 主动 QQ 候选、claim、ack 逻辑
- `xinyu_learning_library.py` - 下载、登记、分桶保存学习资料并接入 source materials
- `xinyu_status.py` - 整体系统只读状态检查

v1 重构骨架：

- `xinyu_v1/gateway/`
- `xinyu_v1/routing/`
- `xinyu_v1/memory/`
- `xinyu_v1/emotion/`
- `xinyu_v1/response/`
- `xinyu_v1/autonomy/`
- `xinyu_v1/observability/`
- `xinyu_v1/storage/`

当前重构边界：

- `CURRENT-REFACTOR-PLAN.md` 是当前阶段的结构重构源文件。
- `xinyu_v1/` 仍处于 shadow / canary 路径；只有 owner 显式开启窄范围 canary 时，v1 才能处理 owner 私聊的简单文本。
- `xinyu_core_bridge.py` 是运行合同入口，应继续变薄；新的大块行为不要直接堆回这个文件。
- `xinyu_qq_gateway.py` 是 NapCat / OneBot transport adapter，不承载人格、记忆策略或 action 决策。

提示词和行为模块：

- `prompts/system.md`
- `prompts/output.md`
- `prompts/*_writer.md`
- `custom/*_bridge_plugin.py`
- `custom/*_engine.py`

验证脚本和测试：

- `xinyu_qq_gateway_smoke.py`
- `runtime_readiness_smoke.py`
- `deployment_status_smoke.py`
- `runtime_security_smoke.py`
- `memory_event_sourcing_smoke.py`
- `persona_state_flow_smoke.py`
- `tests/`

本地私有运行状态：

- `xinyu.local.env`
- `xinyu_qq_gateway.config.json`
- `logs/`
- `memory/`
- `runtime/`
- `learning/self_found/`
- `learning/owner_supplied/`

这些路径已被 Git 忽略，不应该上传。

## 当前能力

已经实现并在本地验证：

- 本地 XinYu runtime launcher
- Core bridge health、chat、probe、proactive、ack、learning、Codex 相关接口
- 原生 QQ gateway 与 NapCat / OneBot 反向 WebSocket 链路
- 记忆导向的 prompt / writer 结构
- 关系、反思、梦境、归档、上下文、学习和事件 sourcing 层
- AI self-iteration gate、learning quality gate、memory consistency gate、summary coverage gate
- 主动 QQ 候选消息生成和明确的 claim / ack dispatch 状态
- 检查 Core、QQ gateway、NapCat、主动发送、review、runtime readiness 的能力

## 本地启动

进入目录：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
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

启动 Core bridge：

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
```

启动原生 QQ gateway：

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
```

给程序读取：

```powershell
python xinyu_status.py --json
```

查看最近一轮 turn 由哪些拆分后的 live module 影响：

```powershell
python xinyu_live_module_diagnostics.py --json
```

当 QQ 发送、主动消息、Core bridge 或 NapCat 连接看起来不对时，先跑这个命令。

## Smoke 测试

改行为前后建议跑：

```powershell
python xinyu_qq_gateway_smoke.py
python deployment_status_smoke.py
python runtime_readiness_smoke.py
python runtime_security_smoke.py
python memory_event_sourcing_smoke.py
python persona_state_flow_smoke.py
python seed_memory_packaging_smoke.py
```

改 Python bridge / gateway 后跑：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_qq_gateway.py xinyu_status.py
```

pytest 测试：

```powershell
python -m pytest tests -q
```

## 学习资料库

学习资料库在：

```text
learning/
  self_found/
  owner_supplied/
```

常用命令：

```powershell
python xinyu_learning_library.py init
python xinyu_learning_library.py url "https://example.com/paper.pdf" --origin owner_supplied --reason "owner 要求学习这篇论文"
python xinyu_learning_library.py github "https://github.com/user/repo" --origin owner_supplied --reason "学习这个插件结构"
python xinyu_learning_library.py add "D:\path\to\file-or-folder" --origin owner_supplied --reason "owner 手动放入的资料"
python xinyu_learning_library.py list
python xinyu_learning_library.py stage --id learn-...
```

`owner_supplied` 会作为 curated material 进入学习管道；`self_found` 默认需要比较或审查，不能直接冒充已经学会。

## 运维文档

- `DEPLOYMENT-STATUS-RUNBOOK.md` - 当前原生 QQ 链路部署说明
- `RUNBOOK.md` - 启动、状态检查、链路恢复
- `LEARNING-LIBRARY.md` - 学习资料库和下载 / stage 流程
- `STATE-OF-XINYU.md` - 当前工程状态
- `VALIDATION-INDEX.md` - 验证地图
- `CHANGELOG-XINYU.md` - 演进记录
- `FAILURE-MODES.md` - 已知失败模式
- `CURRENT-REFACTOR-PLAN.md` - 当前结构重构计划与验收顺序
