# XinYu Workspace

`D:\XinYu` 是心玉的本地项目根目录。日常运行入口、桌面端、QQ/NapCat 接入、运行数据和本地工作区都在这里。

## 入口

- `Start-XinYu-Desktop.bat`：日常入口。后台启动 XinYu Core、QQ gateway 和 NapCat，再打开生产版 XinYu Desktop。
- `Start-XinYu-Frontend.bat`：只启动 `XinYu_Desktop` 前端开发模式，不启动 QQ/NapCat/后端。
- `Stop-XinYu-Desktop.bat`：停止 XinYu Desktop、core、gateway 和 NapCat；不会停止系统里正常安装的 QQ。
- `Start-XinYu-QQ.ps1`：调试 QQ 栈时使用，启动 `XinYu-Core`、QQ gateway 和 NapCat。
- `XinYu-Core/`：新的 XinYu 核心运行目录，主运行包是 `xinyu_runtime`。
- `XinYu_Desktop/`：本机桌面壳。
- `NapCatQQ/`：独立 QQ/NapCat 运行环境。
- `XinYu-Autonomy/`：owner 可见的自主性表面和导出区。
- `XinYu-Local-Scope/`：本地请求、工作材料、inbox/outbox 的受控区域。
- 旧运行目录已经移除；日常启动只走 `XinYu-Core/`。

## 边界

当前运行路径已经迁到 `XinYu-Core/`。不要再把新功能写进旧框架目录或历史归档。

`XinYu-Core/src/xinyu_runtime/` 是主实现包；旧兼容包没有复制到新核心目录。许可证和来源记录保留在 `LICENSE`，不是运行依赖。

## 私有状态

不要上传或公开真实本地状态：

- `.xinyu_bridge_token`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.config.json`
- `XinYu-Core/examples/agent-apps/xinyu/logs/`
- `XinYu-Core/examples/agent-apps/xinyu/memory/`
- `XinYu-Core/examples/agent-apps/xinyu/runtime/`
- `XinYu-Core/examples/agent-apps/xinyu/learning/self_found/`
- `XinYu-Core/examples/agent-apps/xinyu/learning/owner_supplied/`

## 常用命令

日常启动：

```powershell
cd D:\XinYu
.\Start-XinYu-Desktop.bat
```

只启动前端：

```powershell
cd D:\XinYu
.\Start-XinYu-Frontend.bat
```

保留 NapCat/QQ，只重启 XinYu 桌面和核心时：

```powershell
cd D:\XinYu
.\Stop-XinYu-Desktop.ps1 -KeepNapCat
.\Start-XinYu-Desktop.ps1
```

状态检查：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py
```

桌面端构建：

```powershell
cd D:\XinYu\XinYu_Desktop
npm run build
```
