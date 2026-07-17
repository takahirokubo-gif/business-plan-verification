# dummy_input_v2 — 実AI精度テスト用ダミーインプット（ルミエールボーテLBO）

**目的**：実生成AI（`EXTRACTOR_MODE=anthropic`）が正しく動くか・精度は十分かをテストするための
「理想的なインプット」一式と、その**答え**（期待アウトプット）・**採点スクリプト**。

- 理想的＝必要な情報がすべて資料内に揃っている ∧ 実在のLBOモデル・DD報告書サンプルの様式に十分近い
- 既存デモデータ（`dummy_input/` オートスタッフ中部）とは独立した別案件（化粧品D2C・卸のLBO）
- **mockモードでは解析できない**（mock用フィクスチャを持たないため。実AIテスト専用）

要件の幅出し・設計判断は [REQUIREMENTS.md](REQUIREMENTS.md)、
期待値の正本は [GROUND_TRUTH.md](GROUND_TRUTH.md)（機械採点用は `expected_output.json`）。

## ファイル構成

```
spec.py                 数値の正本（Single Source of Truth）
xl_layout.py            Excelのシート・行レイアウト定義
generate_model.py       財務モデルExcel 2ケース生成（LibreOffice再計算でキャッシュ値付与）
dd_content.py           DDレポート4種のページ別コンテンツ
generate_pdfs.py        DDレポートPDF生成（キーファクトのページ位置を構成的に保証）
generate_expected.py    期待アウトプット生成（expected_output.json / GROUND_TRUTH.md）
generate_all.py         一括生成＋整合チェック
validate.py             整合チェック（Excel・PDF・期待値・解析窓制約）
run_ai_test.py          実AIテストランナー＋採点

── 生成物（インプット6ファイル：S2のスロットにアップロードするもの）──
LumiereBeaute_LBO_Model_v2.3_Sponsor.xlsx    財務モデル（スポンサーケース）
LumiereBeaute_LBO_Model_v2.3_BankBase.xlsx   財務モデル（ベースケース・銀行調整）
事業DD報告書_ルミエールボーテ_最終版.pdf      20ページ
財務DD報告書_ルミエールボーテ_最終版.pdf      34ページ
法務DD報告書_ルミエールボーテ_最終版.pdf      14ページ
税務DD報告書_ルミエールボーテ_最終版.pdf      10ページ

── 答え ──
GROUND_TRUTH.md         人が読む正本（サービス上でどう表示されるべきか）
expected_output.json    機械採点用の期待値
reference_output/       模範解答（正しくAIが動いた場合の出力例。generate_reference.py）
  reference_identify.json / reference_deal_info.json / reference_items.json
  reference_kpi_tree.json / reference_scenarios.json
  report.md             模範解答を採点した場合のレポート（🟢合格の見本）
```

**模範解答（reference_output/）**は、AnthropicExtractorが返すのと同じデータ形状で
「実AIが理想的に動いた場合の出力」を具体化したもの。実AIテスト後は
`test_results/raw_*.json` と `reference_output/reference_*.json` を並べて差分レビューできる。
根拠の原文抜粋（quote）が実際に資料の該当ページに一字一句存在することまで
validate.py [7] で機械検証済み。

## 再生成

数値を変える場合は必ず `spec.py` を変更してから：

```bash
cd dummy_input_v2
pip install openpyxl reportlab pypdf   # backend/requirements.txt 相当でも可
python3 generate_all.py                # 生成＋整合チェック（validate.py まで実行）
```

前提：**LibreOffice**（`soffice`）が必要。openpyxlが書いたExcelには数式の計算結果
（キャッシュ値）が無いため、LibreOfficeで再計算・保存し直して「Excelで保存された
実務ファイルと同じ状態」を作っている。無い場合は生成が失敗する（黙って劣化しない）。

## 実AIテストの実行

```bash
# 依存（backendのvenvを使う場合）
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 実行（全ステップ：identify → deal_info → items → kpi_tree → scenarios）
cd ../dummy_input_v2
ANTHROPIC_API_KEY=sk-... ../backend/.venv/bin/python run_ai_test.py

# 一部だけ／再採点だけ
python3 run_ai_test.py --steps identify,items
python3 run_ai_test.py --score-only      # 前回の raw_*.json を再採点（API呼び出しなし）
```

出力は `test_results/`：

- `raw_*.json` … AIの生出力（人手レビュー・再採点用）
- `report.md` / `report.json` … 採点結果

### 採点の考え方

| ステップ | 採点 |
|---|---|
| identify / deal_info / items | 機械採点（決定論）。値は年度キー・カンマ等を正規化して完全一致、根拠はファイル＋シート/ページ位置の一致、のれん不整合の検知有無 |
| kpi_tree / scenarios | 生成タスクのため一意解なし。構造ルーブリック（期待エッジ11本・★の妥当性・5部構成・数値推定の有無・判定ラベル禁止・DD事実の引用）を機械チェックし、内容は raw 出力を人手レビュー |

**合格ライン（決定済み）**：必須20項目について **値一致率100%・根拠一致率90%以上**。
report.md の先頭に 🟢合格／🔴不合格 が表示される。

なお「答え自体の正しさ」は `validate.py` の [6] で機械検証している：
期待値24項目すべてについて、根拠として指定したセル／ページに実際にその値・記述が
存在することを突き合わせ済み（答えの答え合わせ）。

### UIから通しで確認する場合

`backend/.env` に `EXTRACTOR_MODE=anthropic` と `ANTHROPIC_API_KEY` を設定して起動し、
S2（新規案件登録）で上記6ファイルをスロットにアップロード → AI解析を実行。
S3以降の表示を GROUND_TRUTH.md と突き合わせる。

## 注意

- `backend/app/extractors/anthropic_extractor.py` の `_excel_digest` は
  数式＋キャッシュ値の併記に修正済み（修正前は計画年の数値転記が原理的に不可能）。
  詳細と残課題（60行×12列・40ページの読み取り窓）は REQUIREMENTS.md §4。
- このデータはすべて架空。実在の企業・人物・団体とは関係ない。
