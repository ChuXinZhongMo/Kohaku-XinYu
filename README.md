# XinYu

<p align="center">
  <img src="images/xinyu-repository-banner.jpg" alt="心玉の疗养室" width="100%">
</p>

<p align="center">
  <strong>长期运行型个人 AI 伴随系统：记忆、关系、情绪轨迹、学习、自检与受控主动性。</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-local_runtime_active-2f855a" alt="Local runtime active">
  <img src="https://img.shields.io/badge/QQ-NapCat%20%2B%20native%20gateway-2563eb" alt="NapCat native gateway">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/privacy-runtime_files_ignored-6b7280" alt="Runtime files ignored">
</p>

<p align="center">
  <strong>简体中文</strong> · <a href="README.zh.md">繁體中文</a>
</p>

---

## 仓库公告

这个仓库现在以 **XinYu** 为核心展示对象，不再作为通用 KohakuTerrarium 框架仓库展示。KohakuTerrarium 仍是底层运行框架快照，XinYu 是建立在它之上的长期运行 AI 系统。

当前公开仓库包含：

- XinYu 核心 app、提示词、writer、bridge、状态检查与 smoke 测试
- 原生 QQ gateway：`NapCatQQ -> xinyu_qq_gateway.py -> xinyu_core_bridge.py`
- v1 核心重构骨架：路由、记忆、情绪、响应、网关、观测、存储模块
- 可移植 seed memory、学习资料管线、记忆事件 sourcing、人格稳定性与安全边界检查
- 部署和验证文档

当前公开仓库不包含：

- 本地 QQ 账号配置
- 运行期记忆、日志、runtime trace
- 私有聊天、私有学习资料、真实 token 或本地环境文件

旧的 AstrBot 集成链路已经从当前运行链中移除。现在的本地 QQ 链路使用仓库内的原生 `xinyu_qq_gateway.py`。

## 当前运行链路

```text
NapCatQQ
  -> ws://127.0.0.1:6199/ws
  -> examples/agent-apps/xinyu/xinyu_qq_gateway.py
  -> http://127.0.0.1:8765/chat
  -> examples/agent-apps/xinyu/xinyu_core_bridge.py
  -> XinYu Kohaku agent runtime
```

这条链路把平台壳和人格核心分开：

| 层 | 责任 |
| --- | --- |
| NapCatQQ | QQ 客户端与 OneBot 事件来源 |
| `xinyu_qq_gateway.py` | 白名单、群触发、消息归一化、转发到 Core |
| `xinyu_core_bridge.py` | HTTP bridge、会话、学习入口、主动候选、维护任务 |
| Kohaku runtime | XinYu prompt、writer、插件生命周期与行为执行 |
| Memory / learning layers | 长期记忆、seed memory、学习资料、事件记录和质量门 |

架构图：[`XINYU-ARCHITECTURE-DIAGRAM.svg`](examples/agent-apps/xinyu/XINYU-ARCHITECTURE-DIAGRAM.svg)

## 项目状态

已经落地并纳入仓库的主要能力：

- 本地 XinYu Core bridge，提供 `/health`、`/probe`、`/chat`、`/proactive`、`/proactive/ack`、学习与 Codex 委托相关入口
- 原生 QQ gateway，支持白名单、私聊、群触发前缀、超时控制和 OneBot 发送
- 主动消息候选、claim、ack 的受控状态机
- 结构化人格、关系、情绪、反思、梦境、归档、学习和上下文层
- 记忆事件 sourcing、seed memory 打包与同步、persona state 与 life-month slots
- 对话好奇心、可见语气、中文表达、人格稳定性、运行安全和部署可用性的 smoke guard
- v1 重构骨架，覆盖 gateway、routing、memory、emotion、response、autonomy、observability、storage

仍然按本地运行系统处理的内容：

- 真实模型密钥和 `xinyu.local.env`
- `xinyu_qq_gateway.config.json`
- `logs/`、`memory/`、`runtime/`
- `learning/self_found/` 和 `learning/owner_supplied/`

这些路径默认被 Git 忽略。

## 快速启动

进入 XinYu app：

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

更多部署步骤见 [`DEPLOYMENT-STATUS-RUNBOOK.md`](examples/agent-apps/xinyu/DEPLOYMENT-STATUS-RUNBOOK.md)。

## 状态检查

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
python xinyu_status.py
python deployment_status_smoke.py
python runtime_readiness_smoke.py
```

给脚本读取：

```powershell
python xinyu_status.py --json
```

## 常用验证

轻量语法检查：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_qq_gateway.py xinyu_status.py
```

核心 smoke：

```powershell
python xinyu_qq_gateway_smoke.py
python runtime_security_smoke.py
python state_io_smoke.py
python memory_event_sourcing_smoke.py
python persona_state_flow_smoke.py
python dialogue_curiosity_review.py
```

pytest 测试入口：

```powershell
python -m pytest tests -q
```

## 目录地图

```text
examples/agent-apps/xinyu/
  README.md                         app 级说明
  DEPLOYMENT-STATUS-RUNBOOK.md      当前本地 QQ 链路部署说明
  STATE-OF-XINYU.md                 当前工程状态
  VALIDATION-INDEX.md               验证地图
  CHANGELOG-XINYU.md                演进记录
  config.yaml                       Kohaku agent 配置
  xinyu_core_bridge.py              XinYu HTTP core bridge
  xinyu_qq_gateway.py               原生 NapCat / OneBot QQ gateway
  xinyu_v1/                         v1 核心重构骨架
  custom/                           Kohaku lifecycle 插件和引擎
  prompts/                          system/output/writer prompt
  tests/                            pytest 测试
  memory-seeds/                     可移植 seed memory
```

根目录里的 `src/`、`docs/`、`tests/` 保留了 KohakuTerrarium 底层框架快照；XinYu 的主开发入口在 `examples/agent-apps/xinyu/`。

## 隐私边界

不要把下面内容上传到公开仓库：

```text
examples/agent-apps/xinyu/xinyu.local.env
examples/agent-apps/xinyu/xinyu_qq_gateway.config.json
examples/agent-apps/xinyu/logs/
examples/agent-apps/xinyu/memory/
examples/agent-apps/xinyu/runtime/
examples/agent-apps/xinyu/learning/self_found/
examples/agent-apps/xinyu/learning/owner_supplied/
```

公开仓库只保存可复现的代码、结构、文档、测试和可移植 seed；真实运行残留保留在本地。

## License

本仓库包含 XinYu 项目代码，以及作为底层依赖使用的 KohakuTerrarium 源码快照。许可证见 [`LICENSE`](LICENSE)。

