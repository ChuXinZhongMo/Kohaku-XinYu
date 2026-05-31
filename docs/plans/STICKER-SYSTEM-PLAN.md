# XinYu 表情系统交接计划

日期：2026-05-06  
目标：把 XinYu 的表情包能力从“可用第一版”推进到“能理解语境、能学习纠错、能稳定发送”的系统。

## 0. 新窗口接手说明

工作根目录：

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

优先阅读本文件，然后检查这些文件：

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_sticker_pack.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_sticker_import.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_clip_command.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_core_bridge.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_qq_outbox.py
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_qq_gateway.py
D:\XinYu\assets\素材库\心玉\表情
```

不要覆盖 `D:\XinYu\plan.md`。那是主项目行动层计划，不是表情系统计划。

补充：素材库里给 owner 看的分类目录已经改成中文名，例如 `可爱/`、`调侃/`、`无语/`、`待确认/`。代码和 manifest 内部仍保留 `cute/tease/deadpan/unclear` 这类稳定 mood key，避免运行时规则和模型标签失效。

## 1. 当前状态

已经完成：

- 主素材库位置：`D:\XinYu\assets\素材库\心玉\表情`
- 未分类入口：`D:\XinYu\assets\素材库\心玉\表情\待分类`
- 支持 `manifest.generated.json`
- 支持从素材库读取表情候选
- 支持 QQ outbox 图片发送
- 已验证真实 `sticker_pack` 图片消息可以入队、claim、ack，并显示 `sent`
- 已安装本地 CLIP 环境：`D:\XinYu\vision-venv`
- CLIP 使用 `open_clip_torch`
- 导入器支持 `--use-clip`
- 导入器支持 AVIF 入库时自动转 PNG
- 导入器支持识别新语义时自动创建目录
- 导入器支持重分类：
  - `--reclassify-mood <mood>`
  - `--reclassify-all`
- Core Bridge 已接入 `maybe_enqueue_sticker_reply`

当前素材库大致分布：

```text
annoyed: 1
cheer: 1
comfort: 1
confused: 1
cute: 29
deadpan: 4
happy: 1
sad: 6
shy: 10
surprised: 10
tease: 19
tired: 4
unclear: 13
```

当前已知触发规则：

- 显式请求稳定触发：
  - `发个表情包`
  - `来张表情包`
  - `哈哈哈 来张表情包`
- 普通强情绪短句有概率自动触发。
- owner 私聊才自动发送。
- 群聊不自动乱发。
- 报错、日志、构建、严肃场景会被挡住。

## 2. 已验证命令

CLIP smoke：

```powershell
D:\XinYu\vision-venv\Scripts\python.exe xinyu_clip_smoke.py
```

表情导入 smoke：

```powershell
.\.venv\Scripts\python.exe xinyu_sticker_import_smoke.py
```

表情选择与 QQ outbox smoke：

```powershell
.\.venv\Scripts\python.exe xinyu_sticker_pack_smoke.py
```

运行时 readiness：

```powershell
.\.venv\Scripts\python.exe runtime_readiness_smoke.py
```

查看状态：

```powershell
.\.venv\Scripts\python.exe xinyu_status.py
```

重启 Core Bridge：

```powershell
.\start_xinyu_core_bridge.ps1 -ForceRestart -AllowInsecureLlmHttp
```

## 3. 日常使用命令

把新图包丢进：

```text
D:\XinYu\assets\素材库\心玉\表情\待分类
```

预览分类：

```powershell
.\.venv\Scripts\python.exe xinyu_sticker_import.py --use-clip
```

执行分类：

```powershell
.\.venv\Scripts\python.exe xinyu_sticker_import.py --use-clip --apply
```

重跑某个过度集中的目录：

```powershell
.\.venv\Scripts\python.exe xinyu_sticker_import.py --use-clip --reclassify-mood cute
.\.venv\Scripts\python.exe xinyu_sticker_import.py --use-clip --reclassify-mood cute --apply
```

只重建语义索引：

```powershell
.\.venv\Scripts\python.exe xinyu_sticker_import.py --write-semantics --apply
```

## 4. 当前问题

还不完善：

- CLIP 对二次元漫画表情的细语义识别仍然粗糙。
- `cute`、`tease` 仍可能成为新的堆积目录。
- OCR 尚未接入导入器，无法充分利用表情包文字。
- 用户手动纠错后，系统还不会形成稳定学习闭环。
- 自动发送策略仍偏关键词和规则，不是真正深层语境判断。
- `unclear` 目录需要人工处理。
- 当前发送的是 QQ 图片消息，不是 QQ 原生收藏表情/mface。
- 还没有前端管理界面。

## 5. 下一阶段目标

目标不是无限增加目录，而是建立闭环：

```text
图包进入
-> CLIP 粗分类
-> OCR 读文字
-> 语义融合
-> 自动入库
-> owner 手动纠错
-> 纠错样本进入 profile
-> 下一次分类更准
-> 聊天时按语境挑图
-> QQ 发送结果记录
```

## 6. Phase 1：OCR 接入导入器

已有 OCR 环境：

```text
D:\XinYu\ocr-venv
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu\xinyu_paddle_ocr_command.py
```

要做：

- 在 `xinyu_sticker_import.py` 增加参数：
  - `--use-ocr`
  - `--ocr-threshold` 可选
- 对待分类图片批量 OCR。
- 把 OCR 文本写入 `manifest.generated.json`：
  - `ocr_text`
  - `ocr_inferred`
  - `text_keywords`
- 语义融合规则：
  - OCR 有强关键词时优先 OCR。
  - OCR 弱时 CLIP 辅助。
  - OCR 和 CLIP 冲突时降低 confidence 或进 `unclear`。

建议先只对 `unclear` 和低置信度图片跑 OCR，避免全量很慢。

验收：

- `--use-ocr` 不影响旧命令。
- OCR 失败不会中断整个导入。
- manifest 能看到 OCR 文本。
- 带文字的表情不再只按画面分类。

## 7. Phase 2：纠错学习

用户会手动把图从错误目录拖到正确目录。系统应把这个动作当成训练信号。

要做：

- 新增纠错索引文件：

```text
D:\XinYu\assets\素材库\心玉\表情\corrections.generated.json
```

建议结构：

```json
{
  "version": 1,
  "items": [
    {
      "file": "无语/xxx.png",
      "confirmed_mood": "deadpan",
      "previous_mood": "cute",
      "source": "owner_folder_move",
      "updated_at": "..."
    }
  ]
}
```

- `--write-semantics --apply` 时检测 manifest 里旧路径和当前目录变化。
- 当前目录名优先于旧 CLIP 推断。
- 对 owner 确认过的图设置：
  - `confirmed: true`
  - `auto_send: true`
  - `weight: 3`

验收：

- 手动移动图片后，运行索引能更新 manifest。
- 后续重分类不能轻易覆盖 confirmed 图。

## 8. Phase 3：参考图相似度分类

CLIP 文本 prompt 不够稳定，应该支持每个目录放少量参考图。

建议目录：

```text
D:\XinYu\assets\素材库\心玉\表情\参考图\调侃
D:\XinYu\assets\素材库\心玉\表情\参考图\无语
D:\XinYu\assets\素材库\心玉\表情\参考图\慌张
```

要做：

- 新增 `xinyu_sticker_reference_index.py`
- 用 CLIP image embedding 建参考向量。
- 分类时同时计算：
  - image-to-text prompt score
  - image-to-reference similarity
- 参考图相似度高时优先目录标签。

验收：

- 给每类 3-5 张标准参考图后，分类稳定性明显提升。
- `shy/cute/tease/deadpan` 不再互相大量混淆。

## 9. Phase 4：发送策略优化

当前 `xinyu_sticker_pack.py` 的发送策略偏保守。

要做：

- 增加发送模式配置：
  - `XINYU_STICKER_AUTO_ENABLED`
  - `XINYU_STICKER_AUTO_MIN_SCORE`
  - `XINYU_STICKER_AUTO_RATE`
  - 可新增 `XINYU_STICKER_EXPLICIT_ONLY`
- 增加冷却：
  - 每个 session N 分钟最多自动发 1 张。
  - 显式请求不受冷却限制。
- 增加最近发送记录，避免连续发同一张。
- 根据 reply 和 user_text 合并判定 mood。

验收：

- 显式请求稳定发。
- 普通聊天偶尔自然发。
- 严肃、报错、日志场景不发。
- 不连续刷屏。

## 10. Phase 5：前端/管理界面

可选，但很有用。

目标：

- 显示所有分类目录。
- 显示每张图的 mood、OCR 文本、CLIP 分数、是否 confirmed。
- 支持拖拽纠错。
- 支持一键重建索引。
- 支持查看 `unclear` 队列。

如果做在前端，优先接入现有 XinYu Desktop，不要单独造一个复杂应用。

## 11. 安全边界

必须保持：

- 只扫描素材库和明确配置路径。
- 不自动删除素材库外文件。
- 不上传图片到外部服务。
- OCR/CLIP 都走本地环境。
- QQ 自动发送只限 owner 私聊。
- 群聊不自动发图。
- `unclear` 默认不自动发送。

## 12. 回归测试清单

每次改完至少跑：

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_sticker_pack.py xinyu_sticker_import.py xinyu_clip_command.py
D:\XinYu\vision-venv\Scripts\python.exe xinyu_clip_smoke.py
.\.venv\Scripts\python.exe xinyu_sticker_import_smoke.py
.\.venv\Scripts\python.exe xinyu_sticker_pack_smoke.py
.\.venv\Scripts\python.exe runtime_readiness_smoke.py
```

如果改了 runtime 调用链，重启：

```powershell
.\start_xinyu_core_bridge.ps1 -ForceRestart -AllowInsecureLlmHttp
.\.venv\Scripts\python.exe runtime_readiness_smoke.py
```

## 13. 成功标准

短期成功：

- 新图包丢进 `待分类` 后可自动分目录。
- 低置信度进入 `unclear`。
- 手动纠错后 manifest 能跟着更新。
- 显式请求能在 QQ 私聊发图。

中期成功：

- OCR 能让文字表情分类明显更准。
- `cute/shy/tease/deadpan` 不再大规模混淆。
- owner 手动纠错会影响后续分类。

长期成功：

- XinYu 不只是“按关键词发图”，而是能根据聊天语境、回复内容、owner 关系和当前状态，克制地挑一张合适的表情。

## 14. 2026-05-06 继续推进记录

已补齐：
- QQ 主人私聊表情自动入库：owner 私聊发来的 sticker-ish `image` / 可解析 `mface` 会走 `/sticker/import`，Core 只写入本地表情素材库。
- 安全边界：非 owner、群聊、自发消息不会触发导入；原始 QQ 缓存文件只读复制，不移动不删除。
- 导入闭环：新图先复制到 `待分类`，随后只对这一个文件跑分类、OCR/CLIP、写 `manifest.generated.json`。
- Desktop 表情管理入口：表情库面板支持刷新、整理待分类、重建语义索引、打开素材目录；列表优先显示待确认/待看项，并支持把表情记录拖到中文分类标签完成纠错。
- 运行时已加载：Core Bridge `/sticker/import` 路由 live probe 通过，Core Bridge 版本 `0.8.73`，QQ Gateway 版本 `0.1.14`。

使用方式：
```text
在 QQ 私聊里直接给心玉发一张表情/贴图图片。
心玉会自动收进本地表情库，并回复收到了。
如果分类不准，可以在 Desktop 表情库面板把那条记录拖到正确中文分类；也可以打开素材目录手动拖，再点“重建索引”。
```

新增回归：
```powershell
.\.venv\Scripts\python.exe xinyu_sticker_ingest_smoke.py
.\.venv\Scripts\python.exe xinyu_qq_gateway_smoke.py
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

## 15. 2026-05-06 完成状态

工程项已闭环：
- OCR 导入、CLIP 粗分类、参考图索引、手动纠错学习、发送冷却/避免重复、Desktop 管理面板、QQ owner 私聊直接入库都已接入。
- Desktop 面板现在可以直接把表情记录拖到中文分类标签完成纠错；主进程会校验路径，只在 `D:\XinYu\assets\素材库\心玉\表情` 内移动图片，并自动重建索引。
- QQ 直接添加只接受 owner 私聊图片/表情；群聊、非 owner、自发消息不会写入素材库。

还需要真实使用中确认：
- 用 QQ 私聊实际发 1 张表情给心玉，确认 NapCat 给到的 segment 带可下载 `url` 或本地 `file_path`。
- 参考图目录是否每类都有足够样本仍取决于 owner 后续筛选；代码会使用已有参考图，但不会凭空生成“标准答案”。
- 分类准确率需要靠真实表情包继续纠错，纠错后的样本会进入 `corrections.generated.json` 并影响后续索引。

## 16. 2026-05-06 表情感知闭环

已补齐：
- 心玉自己补发 QQ 表情后，会把 mood、文件名、发送模式写进短期对话尾巴；下一轮 owner 问“你刚发了什么”时，不再只记得文字回复。
- owner 发来的 QQ 表情现在先完成入库/分类，再把分类、OCR、CLIP、入库位置作为当轮 rich/image context 交给 Core 回复。
- `sticker_import_queued` 不再是默认状态；分类结果可用时会标成 `sticker_import_completed`，并附带 `sticker_mood`、`sticker_mood_label`、`sticker_confidence`、`sticker_destination`。

边界：
- 这仍然不是通用视觉大模型看图，只是用本地 OCR/CLIP 和表情库分类给心玉一个可用摘要。
- 如果 QQ/NapCat 没给可下载 URL、本地 path 或可解析 file_id，仍只能知道 owner 发了一个低信息表情，无法看到内容。

## 17. 2026-05-06 追问兜底修复

已补齐：
- QQ Gateway 会记录最近一张 owner 私聊表情的导入状态；如果导入遇到 core 502 或短暂失败，下一句 owner 问“我刚发的是什么”时会先重试导入，再把分类结果塞进当前 chat payload。
- Core Bridge 新增当前轮兜底：当前问题携带 `recent_sticker_question` 和 `sticker_import_completed` 时，直接回答“你刚发的是偏 X 的表情包”，不再交给模型泛泛回答“表情包”或“没看到”。
- 如果 QQ 这次确实只给了动画表情占位、没有可抓取图片，兜底会明确说“只拿到了动画表情占位”，不会反问 owner 是不是发了表情包。

验收：
- 截图里的路径应变为：owner 发 QQ 表情 -> owner 追问“我刚发的是什么” -> 心玉回答具体分类，例如“偏难过/开心/震惊的表情包”。
- 仍保持 owner 私聊限定；群聊、非 owner、自发消息不会触发表情入库。

