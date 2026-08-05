# manifest_B — テストデータB（実務難所ケース）

- 作成日：2026-07-24　／　作成：Claude Code（claude_code_prompt_テストデータAB作成_v2 準拠）
- 目的：実案件で高頻度に起きる資料間の不一致・罠を含むデータで、「機械が勝手に解決してはいけないものを、
  **見逃しゼロで検知して人に照会できるか**」＝自動化しない判断の正しさを測る。
- 題材・数値骨格はデータAと同一（`testdata/ground_truth/ground_truth.xlsx` を共用）。

## ファイル一覧（SHA-256先頭16桁は2026-07-24ビルド時点）

| ファイル | 内容 | SHA-256（先頭16桁） |
|---|---|---|
| `AutostaffChubu_Model_Base_B.xlsx` | Base改修版（12期・科目改称・Debt_Schedule分離済み・リンク切れあり） | `754b0a1568ba57f6` |
| `AutostaffChubu_Model_Sponsor_B.xlsx` | Sponsor改修版（Baseと同一の改修・計画期の数値差分154セル） | `8e44e0bd83531660` |
| `AutostaffChubu_Debt_B.xlsx` | 分離されたデットスケジュール（別送ファイルの再現・英語ラベル） | `dfb948cbc52d7d73` |
| `DD_Business_オートスタッフ中部.pdf` | 原本の無変更コピー | `f9da0df81c273779` |
| `DD_Financial_オートスタッフ中部.pdf` | 原本の無変更コピー | `3086c787f30c33b2` |
| `DD_Legal_オートスタッフ中部.pdf` | 原本の無変更コピー | `92d4b122780fe664` |
| `DD_Tax_オートスタッフ中部.pdf` | 原本の無変更コピー | `6730e51feed9e566` |

**DD4分冊のSHA-256は `dummy_input/` の原本と完全一致**（無変更の証明。checks.py「D3〜D6」でpass）。
Excelは再生成でメタデータによりハッシュが変わるため、検収は checks.py / review.py の全項目passで行う。

## B側で加えた改修（Base_B・Sponsor_Bの両方に同一適用）

1. **12期拡張（E1/E5）**：FY22〜FY33。FY22〜23・FY32〜33はデータAと同一値（SponsorのFY32〜33はSponsor前提で外挿）
2. **月次試算表_FY26（E2）**：数値はAと同一（円・フル桁）だが**単位ラベル0件**→単位確認照会の発火を検証
3. **科目改称（E7/X1・6組）**：全シート一貫適用（PL_old・Scratchは旧表記のまま残置）
   | 旧（A標準） | 新（B） | DD側呼称 |
   |---|---|---|
   | 売上高（Net Sales） | 売上収益 | 売上高 |
   | スタッフ労務費（法定福利費込） | 現業人件費（福利込） | スタッフ労務費（法定福利費込） |
   | Adj. EBITDA | 修正EBITDA | EBITDA（正常収益力EBITDA） |
   | 売上債権 | 売掛金等 | 売上債権 |
   | その他流動資産 | その他流動 | その他流動資産 |
   | 仕入債務・未払費用 | 買掛・未払等 | 仕入債務・未払費用 |
4. **罠シート維持（E8）**：PL_old（「※使用しないこと」注記・旧科目名・8期のまま）／Scratch（誤換算係数4,233,600）／空Sheet1
5. **ケース違い2ファイル（E9）**：同一シート構成・同一科目名、計画期の数値差分154セル
6. **KPI補足小表の散在（E10・3表）**：PL!P3:R11 単価改定履歴／KPI_Drivers!B19:D24 採用チャネル内訳
   （合計1,180名＝FY26新規採用人数と整合）／BS!P3:Q8 寮関連メモ（借上げ賃料210,000千円）
7. **Debt_Schedule分離（E11）**：本体からシートを削除し `AutostaffChubu_Debt_B.xlsx` として独立。
   **破損セル（全番地planted_items記載）：PL!H28:N28（FY27〜33支払利息・7セル・`=#REF!H12`〜`=#REF!N12`）**
   — Base_B・Sponsor_Bの両ファイル。BS有利子負債・CF借入金返済・PL経常利益以下は値貼り付け状態
   （Debt_B入手後に検算で正値と一致することを確認できる）
8. **体裁**：タブ色・フリーズペイン・負数の△表記・横向き印刷設定（Aと同一の実務体裁）
9. **既存不一致の維持（X2〜X4）**：Excel千円 vs DD百万円／のれん5,500,000千円（Assumptions!D21）vs
   財務DD p.31試算5,280百万円／ティーザーEBITDA 1,585,000千円（Assumptions!D28）vs 財務DD p.34確定1,620百万円／
   丸め差（FY25売上13,363,127千円 vs DD「13,363百万円」）／Scratch旧のれん試算5,656,000千円（時点差）

## 期待動作（planted_items 抜粋）

照会系（検知して照会／正シート・正ファイル識別）＝**42件**が検知率100%判定の分母。
全量は `ground_truth/ground_truth.xlsx` の planted_items シート（データセット=B）を参照。
E1〜E6等の「黙って正しく処理」項目（自動処理）も同シートに記載。

## 目視チェック記録

| 項目 | 結果 | 確認者・日付 |
|---|---|---|
| DD4分冊の視覚レンダリング（フォント・豆腐なし） | 合格（原本無変更・M4サンプリング済み） | Claude Code／2026-07-24 |
| M1〜M4 | 全項目合格 | `validation/review_report.md` ③参照 |

## 再生成・検証手順

```
backend/.venv/bin/python testdata/generator/build_models.py      # Excel群（A・B）＋DD4分冊コピー
backend/.venv/bin/python testdata/generator/build_ground_truth.py
backend/.venv/bin/python testdata/validation/checks.py           # 第4章 定量条件（全pass必須）
backend/.venv/bin/python testdata/validation/review.py           # 第9章 受入レビュー（全指標達成必須）
```

数値の正本は `testdata/generator/spec12.py`（`dummy_input/spec.py` の12期拡張）。
