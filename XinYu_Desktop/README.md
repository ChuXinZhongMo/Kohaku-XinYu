# XinYu Desktop

`XinYu_Desktop` 是心玉的本机桌面壳。它只负责本机界面、状态呈现和桌面侧交互，
不保存核心人格、QQ gateway 或长期记忆。

核心运行时在：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

## 命令

```powershell
npm run typecheck
npm run build
```

开发模式：

```powershell
npm run dev
```

也可以从根目录双击或执行：

```powershell
cd D:\XinYu
.\Start-XinYu-Frontend.bat
```

## 边界

- `src/` 是桌面壳源码。
- `out/` 是构建产物，可以重新生成。
- `node_modules/` 是依赖目录，不属于项目源码。
- 桌面壳通过本地 bridge 读取心玉状态，不直接改核心运行时身份。
