# Codex 任务交接：开启并通电 XinYu Private Ecosystem

date: 2026-06-02
from: Atimea（owner）/ Claude（executor）
to: Codex（director/operator）
repo: D:\XinYu
app root: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
venv python: `.\.venv\Scripts\python.exe`
背景: Private Ecosystem 自主层已由 Claude 实现并通过测试，详见
`docs/plans/CLAUDE-HANDOFF-BACK-PRIVATE-ECOSYSTEM-2026-06-02.md`。现在 owner 授权
你做两件事：开启 owner-private 主动私聊，安装并接上真实浏览器/截图引擎。

代码标识符、路径、命令、报告用英文；说明可中文（dossier §13）。

---

## 红线（dossier §2、§8.3、§19，违反即停手并回报）

- 不绕过：bridge auth、owner-private 检查、QQ outbox claim/ack、self-action 审批
  队列、external plugin runtime gate、stable memory 审核。
- 不让自主循环直接调用 Codex/MCP/HTTP/QQ send/浏览器/OS/文件写——必须经既有
  typed adapter 与 grants。
- 不复制 Super-Agent-Party 代码（AGPL）。
- owner-private 只对 owner；不接触 group/public/第三方。
- 不削弱任何现有测试或门禁来让活儿看起来完成。
- 依赖必须 pin 版本 + 供应链审查；禁止 `@latest` 运行期漂移。

---

## 任务 A：开启 owner-private 主动私聊（低风险，先做）

事实：`memory/context/private_ecosystem_grants.json` 尚不存在（默认全关）；
owner_user_id 已在 `xinyu_qq_gateway.config.json` 配好。

步骤：
1. 生成/更新 grants（用现成 helper，别手抖写坏 JSON）：
   ```
   .\.venv\Scripts\python.exe -c "from pathlib import Path; import xinyu_private_ecosystem_grants as g; g.save_grants_patch(Path('.'), {'owner_private_autonomous_share': {'enabled': True, 'paused': False, 'daily_limit': 8, 'cooldown_minutes': 30, 'max_message_chars': 800, 'quiet_hours': '00:00-06:00'}})"
   ```
2. 核实出站真实发送姿态。历史上运行时是 dry-run（`real_qq_send=false`、claim/ack
   dry_run）。`enqueue` 会成功入队，但只有 dispatcher/gateway 真发时 owner 才会
   真的收到。确认 QQ gateway 在线且非 dry-run，否则在回报里写明“入队成功但未真发，
   原因=dry-run 姿态”，不要假装已送达。
3. 验证（不手发，只验证闸门）：
   ```
   .\.venv\Scripts\python.exe xinyu_owner_private_share.py --kind self_reflection --summary "test" --json
   ```
   期望 `delivery_level=send_owner_private`、`queued=true`、outbox 队列多一条；
   再跑一次同 dedupe 应 `duplicate_finding`。
   再看 `.\.venv\Scripts\python.exe xinyu_status.py --json` 中
   `private_ecosystem_owner_share_enabled=true`。
4. kill switch 验证：把 grant `paused` 设 `true`，确认 share 立即 `share_paused`
   阻断。回报里写明 owner 可用 `paused:true` 随时一键停。

不要做：把 daily_limit 调到 >8、把 quiet_hours 关掉、给非 owner 频道开权限。

---

## 任务 B：安装并接上真实浏览器/截图引擎（中风险，需保安全姿态）

现状：Playwright 未装；截图后端 mss/pyautogui 未装（PIL/numpy 有）。
`xinyu_browser_control.py` / `xinyu_computer_control.py` 已预留真引擎接线点
（搜 `# pragma: no cover` 的分支与 `engine=` / `backend=` 参数）。

### B1 安装（pin 版本）
```
.\.venv\Scripts\python.exe -m pip install "playwright==<选定稳定版>"
.\.venv\Scripts\python.exe -m playwright install chromium
```
把选定版本写进 `requirements-*.txt`，做供应链审查。截图后端二选一并 pin
（建议 `mss`；若用 PIL.ImageGrab 注意它截的是真桌面，必须走 owner-approved 模式）。

### B2 浏览器真引擎适配器
实现一个满足 `xinyu_browser_control.BrowserEngine` Protocol 的类
（`navigate/snapshot_dom/screenshot/extract_text`），用 Playwright **持久化
context** 指向隔离 profile `runtime/private_ecosystem/browser_profile`，传给
`run_browser_action(..., engine=<adapter>, execute=True)`。

硬性安全（dossier §8.3，务必全部满足）：
- CDP 绑 loopback；随机端口 + per-session auth token。
- 保留 `contextIsolation` / `sandbox` / `webSecurity`（Electron 处）。
- 隔离 profile；cookie 绝不写入共享或 owner profile。
- 保留既有 `is_sensitive_url` 拦截；表单提交/凭证/支付页保持 block。
- 截图 TTL 清理（`cleanup_screenshots`）保持启用。
- 禁止：开放调试端口、`remote-allow-origins=*`、禁 `webSecurity`、禁 sandbox、
  任意 `executeJavaScript`、stealth/反爬注入、未 pin 包。

### B3 计算机控制真后端
实现满足 `xinyu_computer_control.CaptureBackend` Protocol 的类
（`screenshot(region)`），传给 `run_computer_action(..., backend=<x>, execute=True)`。
单步执行（click/type/hotkey）只在 owner-approved 模式 + 敏感窗口拦截下放行；
multi-step 任意控制保持 disabled。

### B4 验证 + 补测试
- 只读：`run_browser_action(action_kind="snapshot_dom", url=<本地静态页或 about:blank>,
  grant={"enabled":True}, execute=True, engine=<adapter>)` 应 `engine=live`、产物是
  真 DOM/截图，落在 `runtime/private_ecosystem/browser_artifacts|browser_screenshots`。
- 给 `pragma: no cover` 的真引擎分支补 pytest（对 localhost / about:blank，**禁外网**，
  避免不稳定）。不要改动现有测试断言。
- 跑 dossier §16.1 焦点回归 + 新 private-ecosystem 测试，全绿才算完成。

### B5（可选）bridge 接线
若要从 bridge 触发：在 `xinyu_bridge_external_plugin_routes.py::external_plugin_call`
为 `xinyu_private_browser` / `xinyu_computer_control` 的 native transport 加 executor
分支；按需加路由 `/desktop/private-browser/action`、`/desktop/private-browser/snapshot`、
`/desktop/private-ecosystem/{snapshot,grant,pause}`（dossier §11）。默认 `execute=false`，
高风险动作需 `approved=true` 或 scoped grant。改 live bridge 后重启并复核
`xinyu_status` 的 core_bridge source-digest 检查。

---

## 完成定义（Codex 回报需覆盖）

- 改了哪些文件、跑了哪些命令、装了哪些 pin 版本。
- share 开启前/后验证输出；dry-run 姿态是否真发。
- 浏览器/电脑 `engine=live` 的只读验证产物路径。
- 安全姿态逐条勾选（B2 硬性清单）。
- 回归测试结果（焦点集 + 新增）。
- 残留风险与回滚路径。
- 不得隐藏任何运行期 blocker；门禁挡住就保留门禁并回报。
