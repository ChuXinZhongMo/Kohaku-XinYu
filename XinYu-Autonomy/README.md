# XinYu Autonomy

这个目录是 `D:\XinYu` 工作区里 owner 可见的自主性表面。

- `thoughts/`：桌面侧可见的私有时间想法。
- `dreams/`：梦境日志导出和最新梦境视图。
- `journal/`：较早的自主性审计导出，保留用于连续性。
- `system/`：指向实时自主性状态 `memory/self/autonomy/` 的 junction。

实时状态来自 XinYu 核心运行时：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\memory\self\autonomy
```

编辑 `system/` 里的文件，会直接编辑实时自主性状态。

这个目录放在 `D:\XinYu` 根下，而不是塞进桌面壳里，是为了让运行时、导出和实时状态保持在同一个本地项目树中。
