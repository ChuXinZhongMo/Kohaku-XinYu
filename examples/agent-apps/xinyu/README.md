# XinYu App

这个目录是 XinYu 的核心 app：提示词、运行入口、记忆相关引擎、bridge 接口、状态检查和 smoke 测试都在这里。

XinYu 的目标不是“回答得像人”这么简单，而是让一个 AI 系统能在长期交互中维持连续性：记住关系、调整表达、审查自身变化，并在被允许时主动联系主人。

## 目录内容

核心运行文件：

- `config.yaml` - XinYu 的 KohakuTerrarium app 配置
- `run_local_xinyu.py` / `run_local_xinyu.ps1` - 本地运行入口
- `xinyu_core_bridge.py` - 给外部 shell 使用的 HTTP bridge
- `xinyu_proactive_presence.py` - 主动 QQ 候选、claim、ack 逻辑
- `xinyu_status.py` - 整体系统只读状态检查

提示词和行为模块：

- `prompts/system.md`
- `prompts/output.md`
- `prompts/*_writer.md`
- `custom/*_bridge_plugin.py`
- `custom/*_engine.py`

验证脚本：

- `validate_scaffold.py`
- `validate_inner_framework.py`
- `proactive_presence_smoke.py`
- `ai_self_iteration_review_bridge_smoke.py`
- `bridge_probe_smoke.py`
- `capability_zones_smoke.py`
- `long_run_status.py`

本地私有运行状态：

- `xinyu.local.env`
- `logs/`
- `memory/`

这些路径已被 Git 忽略，不应该上传。

## 当前能力

已经实现并在本地验证：

- 本地 XinYu runtime launcher
- 记忆导向的 prompt / writer 结构
- 关系、反思、梦境、归档、上下文层
- AI self-iteration gate 与 review bridge
- 主动 QQ 候选消息生成
- 明确的 proactive claim / ack dispatch 状态
- Core bridge health、chat、probe、proactive、ack 接口
- 通过外部 AstrBot shell 插件接入 NapCat / QQ
- 检查 Core、AstrBot、NapCat、OneBot、主动发送、review 状态的工具

## 本地启动

进入目录：

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

运行本地 app：

```powershell
.\run_local_xinyu.ps1
```

启动 Core bridge：

```powershell
.\start_xinyu_core_bridge.ps1
```

停止 Core bridge：

```powershell
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

当 QQ 发送、主动消息、Core bridge 或 AstrBot 插件看起来不对时，先跑这个命令。

## Smoke 测试

改行为前后建议跑：

```powershell
python validate_scaffold.py
python validate_inner_framework.py
python proactive_presence_smoke.py
python ai_self_iteration_review_bridge_smoke.py
python bridge_probe_smoke.py
python capability_zones_smoke.py
```

改 Python bridge 后跑：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_proactive_presence.py xinyu_status.py
```

## QQ 集成

QQ 发送由仓库内的 AstrBot shell 插件源码负责，安装后运行在本地 AstrBot 环境里。

源码路径：

```text
integrations/astrbot/
```

本机运行路径：

```text
D:/XinYu/AstrBot/                AstrBot 运行环境
D:/XinYu/NapCatQQ/               NapCat 运行环境
```

Shell 会轮询 Core bridge。只有 shell 明确 claim 到候选消息后，Core 才会返回可发送的 `reply`；发送完成后 shell 必须回报 `sent` 或 `failed`。

## 运维文档

- `RUNBOOK.md` - 启动、状态检查、QQ 链路恢复
- `STATE-OF-XINYU.md` - 当前工程状态
- `VALIDATION-INDEX.md` - 验证地图
- `CHANGELOG-XINYU.md` - 演进记录
- `FAILURE-MODES.md` - 已知失败模式
- `STRUCTURE-NOTES.md` - 文件结构说明
