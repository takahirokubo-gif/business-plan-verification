# manifest_A — テストデータA（標準ケース）

- 作成日：2026-07-24　／　作成：Claude Code（claude_code_prompt_テストデータAB作成_v2 準拠）
- 目的：実務で平均的な複雑性のもとで「ユーザーに意識させず自動で正しく処理できるか」＝**自動化の性能**を測る。デモにも使用。
- 題材：株式会社オートスタッフ中部（東海地区の製造派遣業・事業承継型LBO「Project Gear」）。
  数値骨格はデータBと同一（`testdata/ground_truth/ground_truth.xlsx` を共用）。

## ファイル一覧（SHA-256先頭16桁は2026-07-24ビルド時点）

| ファイル | 内容 | SHA-256（先頭16桁） |
|---|---|---|
| `AutostaffChubu_Model_A.xlsx` | 財務モデル（Base派生・クリーン版・12期） | `16969354a0d68e79` |
| `DD_Report_統合版_オートスタッフ中部_A.pdf` | 統合版DD報告書（単一分冊・横置きスライド形式・73ページ・図表68点・千円統一） | `0256c4fb0c86e3c7` |

※ Excel/PDFを再生成するとメタデータによりハッシュは変わる。検収はハッシュではなく
`validation/checks.py`・`validation/review.py` の全項目passで行うこと。

## Excelの仕様（AutostaffChubu_Model_A.xlsx）

- シート：Cover / Assumptions / PL / BS / CF / KPI_Drivers / Debt_Schedule / 月次試算表_FY26（Cover除き7枚）
- 期間：**FY22〜FY33の12期**（実績5期＋計画7期）。FY24〜FY31の数値は `dummy_input` の既存モデルと完全一致。
  - FY22〜23実績（新規作成）：全期黒字・売上CAGR（FY22→26）6.37%・貸借一致
  - FY32〜33計画（新規作成）：稼働率88%維持・派遣単価改定+1.0%/年前後・FY33残額一括弁済2,600,000千円
- 月次試算表_FY26：2025/04〜2026/03。**単位は円（フル桁・1,000円グリッド）でA2に「（単位：円）」を明記**。
  12ヶ月合計＝年次PL FY26（誤差0）・3月末残高＝年次BS FY26。季節性は5月△6.0%・8月△6.5%・1月△7.0%。
- 単位表記の位置ゆれ（E3・4パターン）：PL!N2「単位:千円」／CF!A1タイトル内「…C/F・千円」／BS!A2「（単位：千円）」／Debt_Schedule!A2「(Unit: JPY thousands)」
- 英語要素（E4）：Debt_Scheduleの行ラベル100%英語（Beginning Balance等）・英語併記科目5件・年次ヘッダーFY表記100%
- 実績年＝値・計画年＝数式（KPIツリー：売上高＝稼働人数×月間平均稼働時間×派遣単価×12＋その他営業収入）
- 体裁：タブ色・フリーズペイン（C6/C5）・負数の△表記・横向き印刷設定（実務モデルの標準的な見せ方）

## 統合版DDの仕様（DD_Report_統合版_オートスタッフ中部_A.pdf）

- 形式：横置きスライド形式（FAS実務のデッキ型レポートを再現。章扉・章タイトルバンド・
  リード文・図表番号・ページ跨ぎ表のヘッダー再掲）
- 構成：事業編（1.会社概要／2.市場環境／3.競合環境／4.事業モデルとKPI／5.顧客分析）＋
  財務編（6.収益性分析（P/L）／7.B/S分析／8.CF分析／9.計画前提の評価）＋
  付属資料（データブック：三表12期明細・月次明細・用語集・実施手続・開示資料リスト）＝計73ページ
- 単位：**千円で統一**（Excel Aと同一単位系。財務数値はExcelのセル値と完全一致し丸め差ゼロ）
- D2：計画前提（稼働率・単価改定・CPA・採用人数）を複数章に分散（各3章以上。詳細は review_report.md M3）
- フォント：Noto Sans JP埋め込み（ページ視覚レンダリング確認済み・豆腐/文字化けなし）

## 負条件（B専用要素の非混入）— 確認済み

旧版・作業用・空シートなし／ファイル1本のみ／散在KPI補足表なし／リンク切れ（#REF!）なし／
ティーザーEBITDA行・旧前提v2.1注記なし／統合版DDに法務・税務・簿外債務・のれん差異・
符号付き多段調整表・脚注参照・他分冊参照なし／科目名の不一致0件／数値の食い違い0件
（のれんは両資料とも5,500,000千円）。機械判定は `validation/checks.py`（負条件・X2(A)）でpass。

## 期待動作（planted_items 抜粋）

データAに仕込んだ複雑性はすべて**期待動作＝自動処理**（18件）。全量は
`ground_truth/ground_truth.xlsx` の planted_items シート（データセット=A）を参照。

## 目視チェック記録（checks.pyのmanual項目）

| 項目 | 結果 | 確認者・日付 |
|---|---|---|
| D2分散の質（表の再掲でなく実質的な記述か） | 合格（2章=単価動向、4章=KPI・採用、5章=契約条件、6章=販管費・月次、9章=前提評価に実質記述） | Claude Code／2026-07-24 |
| 統合版DDの負条件の最終確認（多段表・他分冊参照なし等） | 合格（禁止文字列走査＋サンプル10ページ通読＋ページ視覚レンダリング確認） | Claude Code／2026-07-24 |
| M1〜M4（数値整合・文章品質・分散の質・フォント） | 全項目合格 | `validation/review_report.md` ③参照 |

## 再生成・検証手順

```
backend/.venv/bin/python testdata/generator/build_models.py      # Excel群（A・B）
backend/.venv/bin/python testdata/generator/build_dd_pdf.py      # 統合版DD PDF
backend/.venv/bin/python testdata/generator/build_ground_truth.py
backend/.venv/bin/python testdata/validation/checks.py           # 第4章 定量条件（全pass必須）
backend/.venv/bin/python testdata/validation/review.py           # 第9章 受入レビュー（全指標達成必須）
```

数値の正本は `testdata/generator/spec12.py`（`dummy_input/spec.py` の12期拡張）。
