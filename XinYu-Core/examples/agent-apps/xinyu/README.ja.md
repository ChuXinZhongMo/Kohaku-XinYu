# XinYu

XinYu は、ローカルで owner が運用する対話エージェントの研究プロジェクトです。目的は一問一答の品質だけではなく、長期的な文脈の継続、観測可能な失敗復旧、レビュー可能な記憶境界、owner が制御できる能動的な連絡を扱うことです。

## 実行経路

```text
NapCat QQ -> xinyu_qq_gateway.py -> xinyu_core_bridge.py -> XinYu runtime
```

QQ gateway は transport のみを担当します。ルーティング、記憶、表現方針、能動連絡、介入 API は core bridge 側にあります。

## 運用ツール

```powershell
.\.venv\Scripts\python.exe xinyu_status.py
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network
.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network dashboard
```

## 研究資料

- `INTERACTIVITY-RESEARCH.md`
- `ARCHITECTURE.md`
- `TRACE-SCHEMA.md`
- `FAILURE-SCENARIOS.md`
- `LOCAL-INSPECTOR-DEMO.md`
- `MEMORY-LAYERS.md`
- `PRIVACY-BOUNDARY.md`
- `EXPRESSION-STABILITY.md`

## ローカル起動

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
.\start_xinyu_qq_gateway.ps1
```

停止:

```powershell
.\stop_xinyu_qq_gateway.ps1
.\stop_xinyu_core_bridge.ps1
```
