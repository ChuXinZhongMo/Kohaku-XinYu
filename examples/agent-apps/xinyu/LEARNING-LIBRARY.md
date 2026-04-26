# XinYu Learning Library

XinYu 的学习资料库位于：

```text
examples/agent-apps/xinyu/learning/
```

里面只有两个顶层资料桶：

- `self_found/`：XinYu 自己通过受控搜索、下载、仓库学习流程找到的资料。
- `owner_supplied/`：主人给她、让她去找、或者手动放进去的资料。

实际下载的网页、文件、论文 PDF、GitHub 仓库快照、抽取文本和 manifest 都是本地运行资料，默认不提交到 Git。

## 初始化

```powershell
cd D:\XinYu\KohakuTerrarium-main\examples\agent-apps\xinyu
python xinyu_learning_library.py init
```

## 下载网页、文件或论文

主人指定的资料：

```powershell
python xinyu_learning_library.py url "https://example.com/paper.pdf" --origin owner_supplied --reason "主人要求学习这篇论文"
```

XinYu 自己找到的资料：

```powershell
python xinyu_learning_library.py url "https://example.com/article" --origin self_found --reason "自主搜索得到的候选资料"
```

## 下载 GitHub 仓库

```powershell
python xinyu_learning_library.py github "https://github.com/user/repo" --origin owner_supplied --reason "学习这个插件的结构"
```

GitHub 仓库下载会保存 zip 快照，并抽取 README、metadata、配置 schema、主插件代码和常见源码文件，形成 `extracted_text.md`。

## 登记本地文件或文件夹

```powershell
python xinyu_learning_library.py add "D:\path\to\file-or-folder" --origin owner_supplied --reason "主人手动放入的资料"
```

## 进入学习管道

下载或登记后，只是“资料入库”。要进入现有 `source_materials` 学习管道，需要 stage：

```powershell
python xinyu_learning_library.py list
python xinyu_learning_library.py stage --id learn-...
```

也可以下载后直接 stage：

```powershell
python xinyu_learning_library.py github "https://github.com/user/repo" --origin owner_supplied --reason "学习这个插件" --stage
```

## 安全边界

- `owner_supplied` 默认作为 curated material，可以进入 learner integration。
- `self_found` 默认只作为待比较资料，`comparison_status` 是 `not_compared`。
- 自己找到的资料不能直接冒充“已学会”，必须经过比较、审查或显式 curated。
- 学习资料只进入知识层，不直接改写人格、关系、主人记忆或情绪状态。
