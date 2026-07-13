# TTS 情绪声学杠杆 —— 落地记录 (2026-06-18)

Plan: `docs/plans/CLAUDE-TASK-TTS-EMOTION-ACOUSTIC-LEVER-2026-06-18.md`

## 背景
对比参考项目 Genie-TTS（GPT-SoVITS，情绪做在声学层=参考音风格迁移）后确认：XinYu 情绪只做在认知层（21维向量 + emotion council），合成层完全不知道情绪；`HIGGS_INPUT_PREFIX` 情绪钩子注释在册但从未接线；`_normalize_text` 把 `~`/`…`/拉长音抹平=自伤。独立项目 alexandria-audiobook 输入端反而更超前（每行带自然语言 `instruct`），但 Higgs 后端同样丢弃 instruct。

目标=拿两边好处：保留认知层连续性，把情绪接回那条没启用的声学杠杆，并同步到 alexandria。

## 改动
共用纯逻辑（无 fastapi/requests，可单测），两处字节一致：
- `runtime/deps/higgs-audio/higgs_emotion.py`（新）
- `E:\TTS_ASMR\alexandria-audiobook\higgs_adapter\higgs_emotion.py`（新，同上）
  - `classify_instruct`（中/英关键词→类别）、`resolve_delivery`（emotion 优先，否则分类 instruct，叠加 profile）、`select_reference`（纯查表+回退，不做 host 存在性检查，因容器路径）、`normalize_text(mode)`（soft 保留单个 `…`/`~`）。
  - 9 类：neutral/warm/tender/playful/hurt/cold/angry/tense/tired，per-类别给 temperature/normalize 起点。

适配器升级（两处字节一致）：
- `higgs_v3_genie_adapter.py`：`/tts` 接受可选 `emotion`/`instruct`；`synth/_synth_one/_post` 串入解析出的 temp/top_k/max_new/ref/prefix/normalize。新 env：`HIGGS_EMOTION`(默认 on)、`HIGGS_NORMALIZE_MODE`(默认 full)、`HIGGS_EMOTION_MAP`、`HIGGS_REF_MAP`。**无情绪→neutral→与今日逐字节等价**（live 机实测 neutral 解析 temp=0.5）。

XinYu 客户端：
- `xinyu_tts_emotion.py`（新，纯）：`derive_delivery(vector, strongest_lens)` —— 向量优先，弱情绪回退 council `strongest_lens`，再弱=neutral 防过度表演；warmth+attachment→tender。
- `xinyu_tts_output.py`：新 flag `XINYU_TTS_EMOTION`(默认 off)。on 时读 `runtime/emotion_state.json` 向量 + `memory/context/emotion_council_state.md` 的 active/strongest_lens，派生类别加进 genie payload 的 `emotion`。读盘有大小上限+异常吞掉。off→payload 不变。

alexandria 客户端：
- `app/tts.py::_higgs_generate_clone(..., instruct_text=None)`：非空 instruct（或 voice 的 character_style/default_style）透传到 POST body；custom 调用点传 instruct_text。
- `HIGGS_SETUP.md`：TODO「Emotion → voice」标记 DONE。

## 测试（全绿）
- `higgs_emotion.py --selftest`：两处均 OK。
- `tests/test_higgs_emotion.py`（新，11 例）+ `tests/test_tts_emotion_mapping.py`（新，8 例）+ `tests/test_xinyu_tts_output.py`（含 2 个新增 emotion on/off payload 例）。
- 关联面 `-k "tts or emotion or speech or voice"`：**132 passed**。
- 顺手修复 stale 断言：`test_xinyu_tts_output.py` 采样率 32000→24000（与已发布 commit 0c2e13c 对齐，非本次引入）。

发现 bug 并修：`classify_instruct` 的 `"ache"` 子串误命中 `det-ache-d`、`"rage"/"irate"` 误命中 `storage/desperate` → 收紧关键词。

## 声学情绪识别 → 参考音库（2026-06-18 已自动完成）
没重录——直接用之前 LoRA 的 227 个切片（`runtime/voice-training/myvoice/dataset/myvoice/`，配 `myvoice.list` 转写，同音色），跑**声学情绪识别**自动建库。
- 隔离 venv：`runtime/deps/ser-venv`（funasr 1.3.10 + emotion2vec_plus_large，CPU，不污染 adapter venv）；模型缓存 `runtime/deps/modelscope-cache`（1.8GB，走 ModelScope，HF 被墙）。
- 脚本：`runtime/voice-training/myvoice/ser_emotion_refbank.py`（emotion2vec→9类映射→稀缺类优先的贪心去重选片→重采样到 24kHz 对齐 bartender_long→生成 `HIGGS_REF_MAP.json`；`--select` 可跳过推理只重建）。
- SER 分布（227 片）：neutral 101 / sad 76 / surprised 25 / happy 22 / fearful 3（无 angry/disgust——酒保独白本就没有）。
- 选出参考音库（落在容器挂载的 `refs/emo_*.wav`，24kHz）：
  - warm ← "来尝尝看。闻起来"（happy 1.00）
  - tender ← "看看月亮呢…往左上角仔细看"（happy 1.00）
  - playful ← "所有人都可以自由恋爱"（happy 1.00）
  - tense ← "你刚才说的思路是什么来着"（surprised 1.00）
  - hurt ← "不好意思！！刚刚说错话了"（sad 1.00，最弱：源无真悲，是窘迫/柔化的替代）
  - **angry / cold：无声学样本 → 回退默认 bartender_long.wav**（仍有解码+归一化杠杆）
- 端到端校验：adapter `load_ref_bank`+`resolve_delivery`+`select_reference` 5 类命中各自 emo 片、angry/cold/neutral 回退默认；全绿。

## 接线（已完成，live 生效需重启）
- adapter `ref_key` 默认取类别名 → `HIGGS_REF_MAP` 按类别 key 即自动接上，无需逐 profile 改。
- `Start-Higgs-v3-Full.ps1`（:8001 启动处）+ alexandria `start_adapter.ps1`：均设 `HIGGS_EMOTION=1` + `HIGGS_REF_MAP`（指向共享的 D 盘 refs json；两边同一 docker `/refs` 挂载）。
- `xinyu.local.env`：`XINYU_TTS_EMOTION=1`（客户端才会发 emotion）。
- docker `refs:/refs:ro` 是实时挂载，新 emo 片无需重启 docker；**只需重启 :8001 adapter** + reload xinyu app。

## A/B 结论与最终决定（2026-06-18，owner 试听）
重启 :8001 后实测：emotion 字段被接受、各类合成正常（字节各异=确实在切）。但 **owner A/B 判定：最好的仍是 `ab_neutral.wav`**，5 个情绪片都不如默认音。
- 根因：Higgs v3 克隆音质强依赖参考音长度+干净度。默认 `bartender_long.wav`=25.9s 连续干净；SER 选出的情绪片仅 6–9s 且是声学离群片（正因离群才被标非中性）。**reference-swap = 拿音质换情绪，这批素材上亏**。
- **决定：停在干净中性。** 退回 reference-swap：两个 launcher 的 `HIGGS_REF_MAP` 注释掉（emo 片+json 留盘、代码能力保留待后用）；`HIGGS_EMOTION`/`XINYU_TTS_EMOTION` 保持开 → 只剩**不动音色**的 soft 归一化（保留 `…`/`~` 气口，纯增益）+ 极轻 temperature 微调。情绪主要靠认知层"带情绪文本"让 Higgs 读语气。
- 已重启 adapter，live = 干净中性。

## 备查 / 可回收
- 实验产物保留：`refs/emo_*.wav`、`refs/HIGGS_REF_MAP.json`、`ser_results.json`、`refbank_selection.json`、`emo_ab/ab_*.wav`。
- 拼长实验（已验证、失败）：同情绪多片拼 ~32s（`HIGGS_REF_MAP_LONG.json`、`emoL_*.wav`、脚本 `--concat`），owner A/B 仍判不如 neutral。**定论：Higgs v3 上 reference-swap 换情绪是死路**——短片/拼长都输给单条干净锚点，克隆死守音色，任何偏离丢的音质 > 换来的情绪。已永久退回干净中性（launcher 两个 `HIGGS_REF_MAP` 均注释，素材留盘备查）。
- 若仍想重启 reference-swap：取消注释 + 重启；但据两次 A/B 不建议。
- 可回收磁盘（owner 决定）：`runtime/deps/ser-venv` + `runtime/deps/modelscope-cache`（合计 ~2GB+，仅 SER 用，运行期不需要）。
- self_code_watchdog：加法式改 `xinyu_tts_output.py`（受监控），如触发 digest 复核按既有 playbook 放行。
