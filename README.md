# 事業計画検証ソリューション Lv1 プロトタイプ

銀行の融資審査部門向け「LBO・MBO・事業承継等のストラクチャードファイナンス案件の
審査初期プロセス支援」のデモ用プロトタイプ。
数日かかっていた「資料読解→数値転記→ストレス仮説」の工程を数十分に圧縮し、
**案件受領後すぐに決裁者と審査相談（論点の擦り合わせ）ができる状態**を作る。

要件定義の正本：[docs/要件定義_事業計画検証Lv1_v5.md](docs/要件定義_事業計画検証Lv1_v5.md)
（UIリファレンスは `docs/ui_reference/`）

## 設計原則

1. **Lv1は再計算エンジンを持たない**。数値は資料からの「値の拾い上げ」のみ。
   KPI構造はExcel数式の構文解析のみ。シナリオのインパクトはLLMの定性推定で、
   UI上必ず「AI推定・モデル再計算なし」と明示する
2. **すべてのAI出力は「提案→人がレビュー→確定」**。確定データのみが下流の入力になる。
   上流の確定値が変更されたら下流は無効化せず警告バッジのみ（警告型）
3. **すべての抽出値に根拠3点セット**（①参照ファイル ②箇所〔シート・セル/ページ〕③抽出の論理）
4. **AI推定と抽出事実をUIで常に視覚的に区別する**

## セットアップ

```bash
# バックエンド（Python 3.12）
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                      # デフォルトで EXTRACTOR_MODE=mock
.venv/bin/python -m app.seed              # DB初期化＋デモデータ投入
.venv/bin/uvicorn app.main:app --port 8010   # http://localhost:8010

# フロントエンド（Node 20+）
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

- APIポートは **8010**（コベナンツ・モニタリングの8000と共存するため）。
  変更する場合は `frontend/vite.config.ts` のproxyも合わせる

## デプロイ（Vercel・Basic認証付き）

Vercel Python Serverless Function 1本（`api/index.py`）で画面・APIの全リクエストを
処理する構成（`vercel.json` の rewrites）。DBは `/tmp` のSQLiteで、コールドスタート
ごとに自動シードされる＝常にクリーンなデモ状態で立ち上がる。

```bash
cd frontend && npm run build     # dist を生成（.vercelignore が dist を含めて配信）
vercel --prod                    # デプロイ
```

環境変数（Vercelダッシュボード or `vercel env add`）:

- `SHARE_USER` / `SHARE_PASSWORD` … Basic認証のID・パスワード（必須。空だと認証なし）
- `EXTRACTOR_MODE=mock`（既定）
- PDF出力用の日本語フォントは `backend/app/assets/` に同梱（Noto Sans JP・SIL OFL）
- mockモードはAPIキー不要で全フローが動く。実API切替は `backend/.env` の
  `EXTRACTOR_MODE=anthropic` ＋ `ANTHROPIC_API_KEY`（プロンプト・スキーマ実装済み。
  動作確認はmockで実施）

## デモの流れ（mockモード）

シード済みの「オートスタッフ中部 LBOファイナンス」で全タブの完成状態を見せられる
（審査相談メモ2件・指摘3件・再検討中の状態）。一気通貫デモは新規登録から：

1. **S2 新規案件登録** — 基本情報を入力（EV/シニア/EBITDA から初期レバレッジ4.1x・LTV54%を自動表示）
2. `dummy_input/` の6ファイルをスロットにアップロード（AIが社名・資料種別を識別）
3. **AI解析を実行** →（擬似ディレイ）→ S3へ。24項目が根拠付きで抽出される
4. **S3 数値確定** — 行クリックで根拠3点セット。のれんは不整合警告
   （モデル5,500 vs 財務DD5,280）→どちらを採るか選択。任意項目は保留も可
5. **S4 KPI構造** — 数式パース由来のツリー。チャットに
   「大口派遣先への売上依存度をKPIに追加して」→差分プレビュー→適用→KPIを確定
6. **S5 シナリオ** — AI推奨3類型（A/B/C）。チャットに
   「大口派遣先（構成比28%)が契約終了したら」→5部構成に展開→採用。
   「シナリオAで稼働率▲18%のケースも見たい」→カード修正
7. **S6 エクスポート** — 保留N項目の確認→Excel/PDFダウンロード（AI推定注記付き）
8. **S7 審査相談メモ** — 結論「再検討」を記録→検討ステータス連動→指摘がカードに表示され
   再検討ループへ
9. 数値確定タブでEBITDA FY26を1,620→1,580に修正すると、KPI・シナリオに
   上流変更警告が出る（警告型・無効化しない）のも見せ場

チャットは台本方式：入力欄のプレースホルダー（候補ボタン）の文言に反応する。
対応外の入力には「デモモードでは〜」のフォールバックを返す。

## ダミーインプット（dummy_input/）

数値・ページ位置の正本は `dummy_input/spec.py`。変更時は必ず：

```bash
cd dummy_input
../backend/.venv/bin/python generate_all.py   # 生成＋整合チェック（validate.py）
```

- 財務モデルExcel 2ケース（千円単位・計画年は実数式・ノイズシート/表記揺れ入り）
- DDレポートPDF 4種（キーファクトのページ固定：事業p.18=依存度62%、
  財務p.34=正常収益力EBITDA 16.2億円・p.31=のれん5,280、法務p.12=未払残業代3億円）
- mockフィクスチャ（backend/app/fixtures/）とGROUND_TRUTH.mdも同時生成

## テスト

```bash
cd backend && .venv/bin/python -m pytest     # スモークテスト8件
cd dummy_input && ../backend/.venv/bin/python validate.py   # データ整合チェック
```

## 構成

```
backend/app/
  main.py routers/       # deals(S1/S2・解析) / review(S3-S5・チャット) / output(S6/S7)
  extractors/            # Extractor ABC / MockExtractor / AnthropicExtractor
  services/              # staleness(警告型巻き戻し) / export_xlsx / export_pdf
  fixtures/              # mock抽出結果（dummy_input/generate_fixtures.py が生成）
  seed.py                # デモ4案件の投入（python -m app.seed）
frontend/src/
  pages/                 # DealList(S1) / DealNew(S2) / DealDetail(S3-S7タブ)
  components/            # ChatPanel(差分適用) / EvidencePanel(根拠3点) / Badge等
dummy_input/             # デモ資料の生成スクリプトと成果物（spec.pyが正本）
```
