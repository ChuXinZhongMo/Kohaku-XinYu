# XinYu Runbook

这份文档是当前本地 XinYu 栈的运行手册。

当你需要启动 XinYu、检查 QQ 主动发送是否正常，或者恢复 Core / AstrBot / NapCat 链路时，从这里开始。

## 1. 本地路径

仓库内核心 app：

```text
D:/XinYu/KohakuTerrarium-main/examples/agent-apps/xinyu/
```

仓库外 QQ 集成：

```text
D:/XinYu/AstrBot/
D:/XinYu/NapCatQQ/
```

仓库内 AstrBot 插件源码：

```text
D:/XinYu/KohakuTerrarium-main/integrations/astrbot/
```

这个仓库保存插件源码，但不保存 live AstrBot 和 NapCat 运行目录。

## 2. 第一条命令

优先跑整体状态检查：

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
python xinyu_status.py
```

健康状态通常应该看到：

- Core bridge health 正常
- AstrBot dashboard 端口 `6185` 可达
- OneBot WebSocket 端口 `6199` 可达
- NapCat WebUI 端口 `6099` 可达
- NapCat 到 AstrBot 的 `6199` WebSocket 已建立
- `xinyu_bridge` 插件已安装
- proactive QQ 配置符合预期
- proactive claim / ack 没有当前 adapter error

给脚本读取：

```powershell
python xinyu_status.py --json
```

## 3. 启动 Core Bridge

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
.\start_xinyu_core_bridge.ps1
```

检查：

```powershell
python xinyu_status.py
```

停止：

```powershell
.\stop_xinyu_core_bridge.ps1
```

## 4. 验证 Core 行为

改 bridge 或 proactive 逻辑后跑：

```powershell
python proactive_presence_smoke.py
python bridge_probe_smoke.py
python bridge_session_cleanup_smoke.py
python ai_self_iteration_review_bridge_smoke.py
python capability_zones_smoke.py
```

Python 语法检查：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_proactive_presence.py xinyu_status.py
```

## 5. QQ 发送模型

XinYu 的主动 QQ 发送使用 claim / ack：

1. AstrBot shell 轮询 `/proactive`。
2. 预览请求不会拿到可发送的 `reply`。
3. 真实发送必须使用 `claim=true`。
4. Shell 通过 AstrBot / NapCat 发送消息。
5. Shell 调用 `/proactive/ack` 回报 `sent` 或 `failed`。
6. Core 写入 dispatch 状态，避免重复发送。

所以：预览不是发送，只有 claim 才能领取真实发送权。

## 6. QQ 没发出去时

先跑：

```powershell
python xinyu_status.py
```

然后按顺序检查：

1. Core bridge 是否运行。
2. AstrBot 是否运行。
3. NapCat 是否运行。
4. `6199` 端口是否开放。
5. NapCat 到 AstrBot 的 WebSocket 是否 established。
6. AstrBot 是否安装了 `xinyu_bridge` 插件。
7. 插件配置里的 `proactive_enabled` 是否符合预期。
8. 插件配置里的目标 session 是否正确。
9. dispatch 状态是否已经把当前候选标记为 `sent`。

如果 NapCat 显示 `ECONNREFUSED 127.0.0.1:6199`，通常是 AstrBot 的 OneBot server 还没准备好，或者 AstrBot 没启动。先启动 / 重启 AstrBot，再让 NapCat 重连。

## 7. 主动消息重复时

查看：

```powershell
python xinyu_status.py --json
```

重点看 proactive dispatch 字段：

- `last_claim_status`
- `last_ack_status`
- `last_claim_id`
- `last_ack_id`
- `adapter_error`

预期规则：

- `sent` 会阻止同一候选重复发送
- `failed` 允许重试
- preview 不会 claim，也不会获得真实发送权

## 8. 本地秘密

不要提交：

```text
xinyu.local.env
logs/
memory/
```

`xinyu.local.env.example` 可以提交，因为它只放占位值。

## 9. 提交前检查

提交前看：

```powershell
git status --short
git diff --cached --name-only
```

这些路径不能出现：

```text
examples/agent-apps/xinyu/xinyu.local.env
examples/agent-apps/xinyu/logs/
examples/agent-apps/xinyu/memory/
```
