# XinYu Runbook

这份文档是当前本地 XinYu 栈的运行手册。

当前 QQ 链路：

```text
NapCatQQ -> ws://127.0.0.1:6199/ws -> xinyu_qq_gateway.py -> http://127.0.0.1:8765/chat -> XinYu Core
```

AstrBot 已经不是当前运行链路的一部分。需要部署和端口细节时，优先看
`DEPLOYMENT-STATUS-RUNBOOK.md`。

## 1. 本地路径

仓库内核心 app：

```text
D:/XinYu/XinYu-Core/examples/agent-apps/xinyu/
```

仓库外 QQ 运行环境：

```text
D:/XinYu/NapCatQQ/
```

本地私有 gateway 配置：

```text
D:/XinYu/XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.config.json
```

这个配置文件被 Git 忽略，不应该上传。

## 2. 第一条命令

优先跑整体状态检查：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python xinyu_status.py
```

健康状态通常应该看到：

- Core bridge health 正常
- Core bridge 运行版本与源码版本一致
- native QQ gateway 源码存在
- native QQ gateway 配置存在且已启用
- `6199` gateway 端口可达
- NapCat WebUI `6099` 可达
- NapCat 到 native QQ gateway 的 WebSocket 已建立
- 本地私有文件没有进入 Git

给脚本读取：

```powershell
python xinyu_status.py --json
```

## 3. 启动

从 `D:\XinYu` 使用一键脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-XinYu-QQ.ps1
```

该脚本负责启动：

- XinYu Core bridge: `127.0.0.1:8765`
- native QQ gateway: `127.0.0.1:6199`
- NapCat WebUI: `127.0.0.1:6099`

也可以在 app 目录内分开启动：

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
.\start_xinyu_qq_gateway.ps1
```

停止：

```powershell
.\stop_xinyu_qq_gateway.ps1
.\stop_xinyu_core_bridge.ps1
```

## 4. 验证 Core 和 Gateway

改 bridge、gateway 或 proactive 逻辑后跑：

```powershell
python tests/smoke/runtime/integration/deployment_status_smoke.py
python tests/smoke/runtime/integration/runtime_readiness_smoke.py
python tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py
python tests/smoke/bridge/integration/bridge_probe_smoke.py
python tests/smoke/bridge/bridge_session_cleanup_smoke.py
python tests/smoke/runtime/runtime_security_smoke.py
```

Python 语法检查：

```powershell
python -m py_compile xinyu_core_bridge.py xinyu_qq_gateway.py xinyu_status.py
```

## 5. 学习资料库

XinYu 的学习资料库：

```text
D:/XinYu/XinYu-Core/examples/agent-apps/xinyu/learning/
```

两个资料桶：

- `self_found/`：XinYu 自己找的资料。
- `owner_supplied/`：owner 给她、让她找、或手动放进去的资料。

初始化：

```powershell
python xinyu_learning_library.py init
```

下载论文 / 文件 / 网页：

```powershell
python xinyu_learning_library.py url "https://example.com/paper.pdf" --origin owner_supplied --reason "owner 要求学习这篇论文"
```

下载 GitHub 仓库用于学习：

```powershell
python xinyu_learning_library.py github "https://github.com/user/repo" --origin owner_supplied --reason "学习这个插件结构"
```

登记 owner 手动放入的文件或文件夹：

```powershell
python xinyu_learning_library.py add "D:\path\to\file-or-folder" --origin owner_supplied --reason "owner 手动放入的资料"
```

进入学习管道：

```powershell
python xinyu_learning_library.py list
python xinyu_learning_library.py stage --id learn-...
```

原则：

- 入库只是保存资料，不等于已经学会。
- `owner_supplied` 默认按 curated material stage。
- `self_found` 默认 `comparison_status: not_compared`，必须经过比较或审查。
- 学习资料不能直接改写人格、关系、owner 记忆或情绪状态。

## 6. QQ 发送模型

普通 QQ 回复链路：

1. NapCat 通过 OneBot 反向 WebSocket 把消息送到 `xinyu_qq_gateway.py`。
2. native gateway 检查白名单、群触发和消息类型。
3. native gateway 把规范化后的 payload 发到 Core `/chat`。
4. Core 生成回复。
5. native gateway 通过 OneBot `send_private_msg` 或 `send_group_msg` 发回 QQ。

主动 QQ 发送仍使用 claim / ack：

1. 发送方查询 `/proactive`。
2. 预览请求不会拿到可发送的 `reply`。
3. 真实发送必须使用 `claim=true`。
4. 发送完成后调用 `/proactive/ack` 回报 `sent` 或 `failed`。
5. Core 写入 dispatch 状态，避免重复发送。

所以：预览不是发送，只有 claim 才能领取真实发送权。

## 7. QQ 没发出去时

先跑：

```powershell
python xinyu_status.py
python tests/smoke/runtime/integration/deployment_status_smoke.py
```

然后按顺序检查：

1. Core bridge 是否运行。
2. native QQ gateway 是否运行。
3. NapCat 是否运行。
4. `6199` 端口是否开放。
5. NapCat 是否连接到 `ws://127.0.0.1:6199/ws`。
6. `xinyu_qq_gateway.config.json` 是否启用并包含正确白名单。
7. Core `/chat` 是否能返回普通回复。
8. dispatch 状态是否已经把当前主动候选标记为 `sent`。

如果 NapCat 显示 `ECONNREFUSED 127.0.0.1:6199`，通常是 native QQ
gateway 没启动，或端口被占用。先重启 gateway：

```powershell
.\stop_xinyu_qq_gateway.ps1
.\start_xinyu_qq_gateway.ps1
```

## 8. 主动消息重复时

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

## 9. 本地秘密

不要提交：

```text
xinyu.local.env
xinyu_qq_gateway.config.json
logs/
memory/
runtime/
learning/self_found/
learning/owner_supplied/
```

`xinyu.local.env.example` 可以提交，因为它只放占位值。

## 10. 提交前检查

提交前看：

```powershell
git status --short
git diff --cached --name-only
```

这些路径不能出现：

```text
examples/agent-apps/xinyu/xinyu.local.env
examples/agent-apps/xinyu/xinyu_qq_gateway.config.json
examples/agent-apps/xinyu/logs/
examples/agent-apps/xinyu/memory/
examples/agent-apps/xinyu/runtime/
examples/agent-apps/xinyu/learning/self_found/
examples/agent-apps/xinyu/learning/owner_supplied/
```
