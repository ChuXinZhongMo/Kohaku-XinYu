# Kohaku-XinYu

<p align="center">
  <img src="images/xinyu-repository-banner.jpg" alt="XinYu repository banner" width="100%">
</p>

<p align="center">
  <strong>記憶、関係性、感情の軌跡、学習、自己点検、制御された能動性のための、長期稼働型の個人 AI コンパニオンシステム。</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-local_runtime_active-2f855a" alt="Local runtime active">
  <img src="https://img.shields.io/badge/QQ-NapCat%20%2B%20native%20gateway-2563eb" alt="NapCat native gateway">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/privacy-runtime_files_ignored-6b7280" alt="Runtime files ignored">
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README.zh.md">繁體中文</a> · <a href="README.en.md">English</a> · <strong>日本語</strong>
</p>

---

## リポジトリのお知らせ

このリポジトリは現在、汎用 KohakuTerrarium フレームワークではなく、**XinYu** を中心に見せる構成になっています。KohakuTerrarium は下層の実行フレームワークのスナップショットであり、XinYu はその上に構築された長期稼働型 AI システムです。

公開リポジトリに含まれるもの:

- XinYu core app、プロンプト、writer、bridge、状態確認、smoke テスト
- ネイティブ QQ gateway: `NapCatQQ -> xinyu_qq_gateway.py -> xinyu_core_bridge.py`
- v1 core リファクタ骨格: routing、memory、emotion、response、gateway、observability、storage
- 移植可能な seed memory、学習資料パイプライン、memory event sourcing、人格安定性と安全境界の検査
- デプロイと検証のドキュメント

公開リポジトリに含まれないもの:

- ローカル QQ アカウント設定
- 実行時の記憶、ログ、runtime trace
- 私的な会話、私的な学習資料、実トークン、ローカル環境ファイル

古い AstrBot 統合経路は、現在の実行チェーンから削除されています。現在のローカル QQ 経路は、このリポジトリ内のネイティブな `xinyu_qq_gateway.py` を使用します。

## 現在の実行チェーン

```text
NapCatQQ
  -> ws://127.0.0.1:6199/ws
  -> examples/agent-apps/xinyu/xinyu_qq_gateway.py
  -> http://127.0.0.1:8765/chat
  -> examples/agent-apps/xinyu/xinyu_core_bridge.py
  -> XinYu Kohaku agent runtime
```

このチェーンでは、通信プラットフォーム側の殻と人格コアを分離しています。

| 層 | 役割 |
| --- | --- |
| NapCatQQ | QQ クライアントと OneBot イベントソース |
| `xinyu_qq_gateway.py` | ホワイトリスト、グループトリガー、メッセージ正規化、Core への転送 |
| `xinyu_core_bridge.py` | HTTP bridge、セッション、学習入口、能動候補、メンテナンスタスク |
| Kohaku runtime | XinYu prompt、writer、プラグイン lifecycle、振る舞いの実行 |
| Memory / learning layers | 長期記憶、seed memory、学習資料、イベント記録、品質ゲート |

アーキテクチャ図: [`XINYU-ARCHITECTURE-DIAGRAM.svg`](examples/agent-apps/xinyu/XINYU-ARCHITECTURE-DIAGRAM.svg)

## プロジェクト状態

このリポジトリに実装済みの主な機能:

- `/health`、`/probe`、`/chat`、`/proactive`、`/proactive/ack`、学習、Codex 委任入口を持つローカル XinYu Core bridge
- ホワイトリスト、私聊、グループトリガー接頭辞、タイムアウト制御、OneBot 送信に対応したネイティブ QQ gateway
- 能動メッセージ候補、claim、ack の制御された状態機械
- 人格、関係、感情、反省、夢、アーカイブ、学習、文脈の構造化レイヤー
- memory event sourcing、seed memory のパッケージ化と同期、persona state、life-month slots
- 対話好奇心、可視的な語調、中国語表現、人格安定性、実行安全性、デプロイ可用性の smoke guard
- gateway、routing、memory、emotion、response、autonomy、observability、storage を含む v1 リファクタ骨格

ローカル実行状態として扱うもの:

- 実モデルキーと `xinyu.local.env`
- `xinyu_qq_gateway.config.json`
- `logs/`、`memory/`、`runtime/`
- `learning/self_found/` と `learning/owner_supplied/`

これらのパスはデフォルトで Git から除外されています。

## クイックスタート

XinYu app ディレクトリへ移動します。

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
```

ローカル環境ファイルを作成します。

```powershell
copy xinyu.local.env.example xinyu.local.env
```

最低限、次を設定します。

```text
XINYU_API_KEY=
XINYU_BASE_URL=
XINYU_LLM_MODEL=
```

最小依存をインストールします。

```powershell
python -m pip install -r requirements-minimal.txt
```

Core bridge を起動します。

```powershell
.\start_xinyu_core_bridge.ps1 -AllowInsecureLlmHttp
```

ネイティブ QQ gateway を起動します。

```powershell
.\start_xinyu_qq_gateway.ps1
```

詳細なデプロイ手順は [`DEPLOYMENT-STATUS-RUNBOOK.md`](examples/agent-apps/xinyu/DEPLOYMENT-STATUS-RUNBOOK.md) を参照してください。

## 状態確認

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python xinyu_status.py
python deployment_status_smoke.py
python runtime_readiness_smoke.py
```

スクリプト向けの JSON 出力:

```powershell
python xinyu_status.py --json
```

## プライバシー境界

次のパスは公開リポジトリにアップロードしないでください。

```text
examples/agent-apps/xinyu/xinyu.local.env
examples/agent-apps/xinyu/xinyu_qq_gateway.config.json
examples/agent-apps/xinyu/logs/
examples/agent-apps/xinyu/memory/
examples/agent-apps/xinyu/runtime/
examples/agent-apps/xinyu/learning/self_found/
examples/agent-apps/xinyu/learning/owner_supplied/
```

公開リポジトリには、再現可能なコード、構造、ドキュメント、テスト、移植可能な seed のみを保存します。実際の実行残留はローカルに残します。

## License

このリポジトリには XinYu プロジェクトコードと、下層依存として利用する KohakuTerrarium ソーススナップショットが含まれます。ライセンスは [`LICENSE`](LICENSE) を参照してください。
