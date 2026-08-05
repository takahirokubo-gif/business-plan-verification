# testdata_realistic — 実物テンプレ型テストデータA/B（リアリティ版）

- 作成日：2026-07-24　／　作成：Claude Code
- 位置づけ：`testdata/`（v2・現在テスト実施中）とは**独立した第2世代セット**。
  `actual_data_sample/`（実際にやり取りされる財務モデル・DD報告書のサンプル）の様式を分析し、
  **数値骨格とA/Bの複雑性定義はv2と同一のまま**、資料の「作り」を実物に寄せたもの。
- 数値の正本：`testdata/generator/spec12.py` を共有（オートスタッフ中部LBO・Project Gear）。

## v2からの変更点（actual_data_sample の実物規約を反映）

| 要素 | v2（testdata/） | リアリティ版（本セット） |
|---|---|---|
| シート構成 | Cover/Assumptions/PL/BS/CF/KPI_Drivers/Debt_Schedule/月次 | **Cover/inp/PL/BS/CF/calc/debt/月次**（前提・計算・デットを分離する実物テンプレ構成） |
| 入力セルの識別 | なし | **青字（#0070C0）＝入力・黒字＝数式**（Coverに凡例） |
| 符号規約 | 費用も正値（減算式） | **費用・返済・支払利息は負値＋SUM縦計算**（実務モデルの標準） |
| 年度ヘッダー | FY22〜FY33 | **FY22A〜FY26A／FY27E〜FY33E**（実績A・予想Eサフィックス） |
| デットスケジュール | 単一ブロック | **銘柄別2ブロック**（既存借入〔リファイナンス対象・インプライド金利〕＋シニアTLA）＋コミットメントライン注記 |
| 統合版DD（A） | 横置きスライド型デッキ（73p・図表68点） | 同一（実物の財務DD報告書サンプル①と同型式のため流用） |

**維持しているもの**：FY22〜FY33の12期・月次試算表（A=単位ラベルあり/B=なし）・単位表記の位置ゆれ・
科目改称6組・罠シート3枚・ケース違い2ファイル・補足小表3箇所・`=#REF!`リンク切れ7セル（PL!H28:N28）・
のれん/ティーザー不一致・DD4分冊の原本コピー（SHA-256一致）——A/Bの計画複雑性はすべてv2と同一。

新規の複雑性（planted追加済み・いずれも期待動作＝自動処理）：
**符号規約**（負値の正規化）・**入力色規約**（青字/黒字の識別）。

## ディレクトリ

```
testdata_realistic/
  A_standard/   AutostaffChubu_Model_A.xlsx ＋ DD_Report_統合版_オートスタッフ中部_A.pdf
  B_hard/       Base_B / Sponsor_B / Debt_B ＋ DD4分冊（原本コピー）
  ground_truth/ ground_truth.xlsx（facts 79行・planted 84行・新レイアウトのセル参照）
  validation/   checks.py（pass 56／fail 0）・review.py（総合判定 合格）・各レポート
  generator/    xl12r.py（レイアウト）・build_models_r.py・build_ground_truth_r.py
```

## 再生成・検証手順

```
backend/.venv/bin/python testdata_realistic/generator/build_models_r.py
backend/.venv/bin/python testdata_realistic/generator/build_ground_truth_r.py
backend/.venv/bin/python testdata_realistic/validation/checks.py
backend/.venv/bin/python testdata_realistic/validation/review.py
```

## 検収状況（2026-07-24）

- checks.py：**pass 56／fail 0**（manual 2件は目視実施済み）
- review.py：**総合判定 合格**（R1〜R9・強度指標・M1〜M4すべて達成）
- 主要ファイルSHA-256（先頭16桁）：Model_A `903e88dd820b1169`／Base_B `b078cc9727b0484c`／
  Sponsor_B `9b6ad1b5e9b8ecb0`／Debt_B `f6918029747953c3`／ground_truth `7e076b099715ec3e`

## 今後さらに実物へ寄せる場合の候補（未実装）

- `CHOOSE(case,強気,ベース,弱気)` のケース切替（実物サンプルの構造＝v2仕様のパターンC。スコープ外として未実装）
- 単一シート完結のLBOモデル（Sources & Uses〜リターン計算）
- 事業DDサンプルのような16:9スライド・グラフ入りDD
