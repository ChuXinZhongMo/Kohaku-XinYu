# XinYu

XinYu 是一个基于 KohakuTerrarium 构建的长期运行型个人 AI 伴随系统。

它不是一次性问答机器人。这个项目的核心是连续性：记忆、关系状态、情绪轨迹、反思、自我审查、受控主动性，以及通过 QQ 抵达真实世界的消息闭环。

## 当前状态

XinYu 目前已经具备可运行的本地核心和已验证的 QQ 桥接路径：

- 本地 XinYu agent scaffold：`examples/agent-apps/xinyu/`
- 结构化记忆、关系、反思、梦境、归档与上下文层
- 中文人格与表达校准检查
- AI self-iteration review gate
- 主动 QQ 候选消息、claim、ack 状态机
- Core bridge HTTP 接口：health、probe、chat、proactive、ack
- AstrBot / NapCat QQ 发送适配路径
- 全局只读状态检查工具：`xinyu_status.py`

主动 QQ 链路已经在本地跑通过：Core 生成候选消息，AstrBot shell 领取真实发送权，NapCat / OneBot 完成发送，Core 记录发送回执。

## 架构

XinYu 当前分成三层：

| 层 | 作用 |
| --- | --- |
| XinYu Core | 人格、提示词、记忆、审查门、主动状态、HTTP bridge |
| AstrBot Shell | QQ 侧适配器，轮询 XinYu 并发送消息 |
| NapCat / OneBot | QQ 客户端桥接层 |

仓库内主要路径：

```text
examples/agent-apps/xinyu/       XinYu 核心 app、提示词、检查脚本、bridge
docs/xinyu/                      XinYu 相关设计文档
```

本机集成路径：

```text
D:/XinYu/XinYu-AstrBot-Shell/    AstrBot 插件源码
D:/XinYu/AstrBot/                AstrBot 运行环境
D:/XinYu/NapCatQQ/               NapCat 运行环境
```

这个仓库只保存 XinYu 核心和文档；AstrBot、NapCat 的实际运行目录属于本地集成环境。

## 快速启动

进入 XinYu 目录：

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
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

运行本地 XinYu：

```powershell
.\run_local_xinyu.ps1
```

启动 Core bridge：

```powershell
.\start_xinyu_core_bridge.ps1
```

## 状态检查

优先使用：

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
python xinyu_status.py
```

给脚本读取：

```powershell
python xinyu_status.py --json
```

状态工具会检查：

- Core bridge 是否健康
- AstrBot dashboard 端口是否可达
- OneBot WebSocket 端口是否可达
- NapCat WebUI 端口是否可达
- NapCat 到 AstrBot 的 WebSocket 是否建立
- AstrBot 插件版本与配置
- 主动 QQ dispatch 状态
- AI self-iteration review 状态
- capability zones 状态

## QQ 主动发送机制

XinYu 的主动 QQ 发送不是直接把预览内容发出去，而是两阶段模型：

1. Shell 向 Core 查询 proactive candidate。
2. 预览请求只能拿到 `preview_reply`，不能真实发送。
3. Shell 使用 `claim=true` 领取真实发送权。
4. Shell 通过 AstrBot / NapCat 发送 QQ 消息。
5. Shell 调用 `/proactive/ack` 回报 `sent` 或 `failed`。
6. Core 记录 dispatch 状态，避免重复发送同一个候选消息。

这个设计的目的很简单：预览不是发送，真实发送必须被明确领取，并且必须有回执。

## 常用验证

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
python validate_scaffold.py
python validate_inner_framework.py
python proactive_presence_smoke.py
python ai_self_iteration_review_bridge_smoke.py
python bridge_probe_smoke.py
python capability_zones_smoke.py
```

改 Python bridge 后建议跑：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_proactive_presence.py xinyu_status.py
```

## 隐私边界

这些本地运行文件不会提交到 Git：

```text
examples/agent-apps/xinyu/xinyu.local.env
examples/agent-apps/xinyu/logs/
examples/agent-apps/xinyu/memory/
```

它们可能包含密钥、QQ 状态、关系记忆、运行痕迹或私人对话上下文。保留在本地。

## 文档入口

- `examples/agent-apps/xinyu/README.md`
- `examples/agent-apps/xinyu/RUNBOOK.md`
- `examples/agent-apps/xinyu/STATE-OF-XINYU.md`
- `examples/agent-apps/xinyu/VALIDATION-INDEX.md`
- `examples/agent-apps/xinyu/CHANGELOG-XINYU.md`
- `docs/xinyu/memory-system-v0.1.md`
- `docs/xinyu/memory-schema-v0.1.md`

KohakuTerrarium 是底层框架，XinYu 是建立在它之上的长期运行 AI 系统。

## License

本仓库包含 XinYu 项目代码，以及作为底层依赖使用的 KohakuTerrarium 源码快照。许可证见 `LICENSE`。
