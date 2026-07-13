# TTS 情绪声学杠杆 —— 拿"认知层情绪"+"参考音/解码声学情绪"两边的好处

- **日期**: 2026-06-18
- **作者**: Claude (Opus 4.8)
- **状态**: 已落地（代码+测试完成；参考音素材与 live 调参为 Ops 待办）
- **涉及仓库**:
  - `D:\XinYu`（主项目，live 机）
  - `E:\TTS_ASMR\alexandria-audiobook`（独立分出的 TTS/有声书项目，同步更新）

## 0. 背景与动机

参考项目 **Genie-TTS (GPT-SoVITS)** 把情绪做在**声学层**：靠"情绪参考音"克隆韵律，按情绪切参考音（离散情绪桶）。

XinYu 现状把情绪做在**认知层**：
- 21 维情绪向量状态机（`xinyu_v1/emotion/`）+ emotion council 7 个 lens，产出 `output_bias` 注入 LLM prompt（`xinyu_emotion_council.py`）。
- 情绪只通过"带情绪的文本"外溢，**合成层完全不知道情绪**。

证据链（实读代码）：
- `xinyu_tts_output.py::_request_genie_tts` 只发 `{character_name, text, split_sentence}` → 纯文本。
- `runtime/deps/higgs-audio/higgs_v3_genie_adapter.py` 用**固定**参考音 + 固定 `temperature=0.5` 合成；`HIGGS_INPUT_PREFIX` 情绪钩子注释在册但**默认空、从未接线**。
- `_normalize_text` 把 `~`、`……`、拉长音全抹平 —— 恰好削掉文本携带的韵律线索（自伤）。
- 两处 adapter（XinYu 与 alexandria）**字节一致**。
- alexandria 在输入端**反而更超前**：每行台词已带自然语言 `instruct`（如 "Firm quiet authority, voice tight with restrained anger"），且 `HIGGS_SETUP.md` 明确 TODO：让 adapter 接 per-call prefix/prosody、`_higgs_generate_clone` 传 `instruct`。但它的 Higgs 后端目前同样**丢弃** instruct。

### 结论
- 两边**思路不同**：Genie 把情绪做进"声音"，我们做进"脑子"。论智能/连续性我们强，论声音里听得见的情绪强度，参考音方案更猛。
- **最优解 = 把脑子里的情绪状态接回那条没启用的声学杠杆**，同时不丢掉认知层的连续性。

## 1. 目标（拿两边好处）

1. **保留**认知层（情绪向量 + council），不动其逻辑。
2. **共用的 Higgs adapter 升级为"每请求情绪感知"**，提供三条声学杠杆：
   - (a) **per-emotion 解码参数**（temperature / top_k / max_new）——无需任何新素材，保证有声学差异。
   - (b) **per-emotion 参考音切换**（Genie 的机制）——纯配置查表（容器路径，不做 host 存在性检查），缺素材时优雅回退到默认参考音。
   - (c) **per-emotion 归一化模式**（full / soft）——soft 保留单个 `…` 停顿与单个 `~` 拉长，修掉"自伤"；runaway 由已有的时长重采样独立兜底。
   - 可选 (d) **per-profile inline prefix**——显式 opt-in，默认空（避免被读出来）。
3. **情绪喂入**：
   - XinYu：从认知层（`emotion_state.json` 向量 + council `strongest_lens`）派生 delivery 类别，flag 控制，发 `emotion`。
   - alexandria：把现成 per-line `instruct` 透传给 adapter，由 adapter 关键词分类成类别。
4. **同步**两处 adapter，逻辑一致。
5. 全程**加法式、flag/env 受控、向后兼容**（不传情绪 → 行为与今日逐字节等价）。

## 2. 架构

### 2.1 新增纯逻辑模块 `higgs_emotion.py`（无 fastapi/requests 依赖，可单测）
落两份：`runtime/deps/higgs-audio/` 与 `E:\TTS_ASMR\alexandria-audiobook\higgs_adapter\`。

API：
- `DELIVERY_CATEGORIES`：neutral/warm/tender/playful/hurt/cold/angry/tense/tired
- `DEFAULT_PROFILES`：类别 → {temperature?, top_k?, max_new_tokens?, normalize?, ref_key?, prefix?}（仅写差异，其余继承 defaults）
- `load_profiles(path)` / `load_ref_bank(path)`：env 指向的 JSON 覆盖默认
- `classify_instruct(text) -> category`：自由文本（中/英）关键词 → 类别，默认 neutral
- `resolve_delivery(emotion, instruct, *, profiles, defaults) -> dict`：emotion 优先；否则分类 instruct；叠加 profile
- `select_reference(ref_key, ref_bank, default_path, default_text) -> (path, text)`：纯查表 + 回退
- `normalize_text(t, mode)`：full=现行；soft=保留单个 `…`/`~`，仍收敛 3+ 重复与多重 `？！`

### 2.2 升级两处 `higgs_v3_genie_adapter.py`
- 模块级：`PROFILES/REF_BANK/DEFAULTS` 从 env 装载；`HIGGS_EMOTION`（默认 1）、`HIGGS_NORMALIZE_MODE`（默认 full）、`HIGGS_EMOTION_MAP`、`HIGGS_REF_MAP`、`HIGGS_INSTRUCT_AS_PREFIX`（默认 0）。
- `/tts` 读取 `text` + 可选 `emotion`、`instruct`。
- `synth/_synth_one/_post` 串入解析出的 temp/top_k/max_new/ref/prefix/normalize。
- **向后兼容**：无 emotion/instruct → neutral → defaults → 与今日一致。

### 2.3 XinYu 客户端
- 新模块 `xinyu_tts_emotion.py`（纯）：`derive_delivery(vector, strongest_lens, *, threshold) -> category`，lens 映射优先，向量兜底，弱情绪回 neutral 防过度表演。
- `xinyu_tts_output.py`：新 flag `XINYU_TTS_EMOTION`（默认 off）。on 时读 `runtime/emotion_state.json` 向量 + `memory/context/emotion_council_state.md` 的 `strongest_lens`/`status`，派生类别，加进 genie `/tts` payload 的 `emotion`。读盘有大小保护、异常吞掉 → 无情绪。off → payload 不变。

### 2.4 alexandria 客户端
- `app/tts.py::_higgs_generate_clone` 增加可选 `instruct_text`，非空则 payload 带 `instruct`；`_external_generate_custom/_clone` 调用处透传。

## 3. 类别 → 参数（起点，按耳朵再调）
| 类别 | temperature | normalize | 说明 |
|---|---|---|---|
| neutral | 0.5 | full | 等同今日 |
| warm | 0.52 | soft | 温暖 |
| tender | 0.50 (top_k40) | soft | 轻柔/亲密 |
| playful | 0.62 | soft | 俏皮/撒娇 |
| hurt | 0.45 | soft | 委屈/难过 |
| cold | 0.40 | full | 冷淡/疏离 |
| angry | 0.60 | soft | 生气 |
| tense | 0.52 | soft | 紧张/被吓 |
| tired | 0.45 | soft | 疲惫 |

参考音库（可选，需素材）：`HIGGS_REF_MAP` JSON `{ref_key: {audio_path, text}}`；profile 的 `ref_key` 命中则切，否则默认 `bartender_long.wav`。

## 4. 测试
- XinYu pytest：
  - `tests/test_higgs_emotion.py`：normalize 两模式、classify_instruct、resolve_delivery 叠加与回退、select_reference 回退。
  - `tests/test_tts_emotion_mapping.py`：derive_delivery（lens/向量/阈值/neutral 兜底）。
  - 运行 `pytest`。
- alexandria（无 pytest）：`python higgs_adapter/higgs_emotion.py --selftest`（模块内 `__main__` 自检）跑通纯逻辑。

## 5. 需在 live 机/人工完成的 Ops（本会话不执行，仅交付步骤）
1. 录制/裁剪 bartender 同音色的情绪变体参考音（warm/hurt/playful/...），写 `HIGGS_REF_MAP`（容器内路径）。
2. 设 `XINYU_TTS_EMOTION=1`、`HIGGS_NORMALIZE_MODE=soft`（或保持 full 由 profile 控制），重启 :8001 adapter 与 :8000 sgl-omni。
3. A/B 试听：同一句在 neutral vs hurt/playful 下的差异，回填表 3 的参数。
4. self_code_watchdog：本次仅加法式改 `xinyu_tts_output.py`（核心受监控文件），新增模块不在摘要白名单内属正常开发；如触发 digest 复核按既有 playbook 放行。

## 6. 验收
- [x] `higgs_emotion.py` 落两处且单测通过（两处 `--selftest` OK，逐字节一致）
- [x] 两处 adapter 升级且逐字节逻辑一致（除路径）；live 机 import OK、neutral=0.5 向后兼容
- [x] XinYu 客户端 flag 受控、off 时 payload 不变（新增 on/off payload 测试各 1）
- [x] alexandria 透传 instruct（`_higgs_generate_clone` + 调用点）
- [x] pytest 通过（关联面 132 passed）+ alexandria 自检通过
- [x] worklog 记录（`worklog/tts-emotion-acoustic-lever-2026-06-18.md`）+ 本 plan 勾选
- [x] 情绪参考音库（**声学情绪识别自动建库**，非重录）：emotion2vec 跑 227 个 LoRA 切片 → 选出 warm/tender/playful/tense/hurt 5 类 24kHz 参考音 + `HIGGS_REF_MAP.json`；angry/cold 无样本回退默认。脚本 `runtime/voice-training/myvoice/ser_emotion_refbank.py`
- [x] 两处 launcher + `xinyu.local.env` 接好 `HIGGS_EMOTION` / `HIGGS_REF_MAP` / `XINYU_TTS_EMOTION`
- [x] live A/B（两轮）：短单片 + ~32s 拼长，owner 均判**不如 neutral**。**定论：Higgs v3 上 reference-swap 换情绪是死路**，永久退回干净中性。情绪保留：soft 归一化 + 轻解码 + 认知层带情绪文本。代码/素材留盘备查。
