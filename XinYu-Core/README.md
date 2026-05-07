# XinYu Core

`D:\XinYu\XinYu-Core` 是心玉核心运行目录。

主要入口：

- `src/xinyu_runtime/`：XinYu Runtime 主实现包。
- `examples/agent-apps/xinyu/`：心玉本地核心 app、QQ gateway、memory、runtime、learning 数据和 smoke 脚本。
- `examples/agent-apps/xinyu/.venv/`：当前运行用 Python 环境。

运行约束：

- 新代码优先写入 `xinyu_runtime` 或 `examples/agent-apps/xinyu`。
- 不再依赖旧框架目录作为运行路径。
- `LICENSE` 保留来源和授权信息；日常运行只使用当前目录。

状态检查：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py
```
