# GROUND_TRUTH — オートスタッフ中部LBO デモデータの正本

このファイルは `spec.py` から自動生成される（手編集禁止）。
再生成: `python generate_all.py` ／ 整合チェック: `python validate.py`

## 1. 案件基本情報

| 項目 | 値 |
|---|---|
| 案件名 | オートスタッフ中部 LBOファイナンス |
| 案件種別 | LBO |
| 借入人（SPC） | 株式会社ASホールディングス |
| 対象会社 | 株式会社オートスタッフ中部（自動車製造派遣（東海地盤）） |
| スポンサー | 日本橋キャピタルパートナーズ株式会社 |
| EV | 12,000百万円 |
| シニアローン | 6,500百万円（本行取組 2,500百万円・期間7年） |
| エクイティ | 5,500百万円 |
| スポンサー提示EBITDA（速報） | 1,585百万円 |
| 初期レバレッジ（自動算出） | 4.1x ＝ シニア6,500 ÷ 提示EBITDA1,585 |
| LTV（自動算出） | 54% ＝ シニア6,500 ÷ EV12,000 |

## 2. DDレポートのキーファクト（ページ位置固定）

| ID | ファイル | ページ | 内容 |
|---|---|---|---|
| customer_concentration | DD_Business_オートスタッフ中部.pdf | p.18 | 上位3社への売上依存度は62%（うち最大手A社28%） |
| normalized_ebitda | DD_Financial_オートスタッフ中部.pdf | p.34 | 正常収益力ベースのEBITDAは1,620百万円（16.2億円） |
| goodwill_dd | DD_Financial_オートスタッフ中部.pdf | p.31 | のれん想定額は5,280百万円（スポンサーモデルは5,500百万円・220百万円の差異） |
| overtime_liability | DD_Legal_オートスタッフ中部.pdf | p.12 | 未払残業代に係る潜在債務は最大300百万円（3億円） |
| haken_license | DD_Legal_オートスタッフ中部.pdf | p.5 | 労働者派遣事業許可（派23-301456）は2028年3月まで有効 |
| nol | DD_Tax_オートスタッフ中部.pdf | p.6 | 繰越欠損金は存在しない（直近10年間、課税所得を計上） |

※ 財務DDは キーファクトのページ指定（p.34）に合わせて全36ページ構成（他は事業20p・法務14p・税務10p）。

## 3. 財務モデルの主要数値（百万円・Excel内は千円）

### 実績（両ケース共通）

| 項目 | FY24 | FY25 | FY26 | 参照セル |
|---|---|---|---|---|
| 売上高 | 12,460 | 13,363 | 14,160 | PL!C9:E9 |
| 営業利益 | 1,229 | 1,388 | 1,515 | PL!C21:E21 |
| EBITDA | 1,321 | 1,486 | 1,620 | PL!C25:E25 |
| 当期純利益 | 842 | 952 | 1,041 | PL!C32:E32 |

### 計画

| ケース | 項目 | FY27 | FY28 | FY29 | FY30 | FY31 |
|---|---|---|---|---|---|---|
| Base | 売上高 | 14,890 | 15,454 | 16,005 | 16,575 | 17,149 |
| Base | EBITDA | 1,750 | 1,836 | 1,921 | 2,016 | 2,111 |
| Sponsor | 売上高 | 15,267 | 16,336 | 17,523 | 18,651 | 19,723 |
| Sponsor | EBITDA | 1,899 | 2,188 | 2,515 | 2,838 | 3,168 |

### KPI（FY26実績）

| KPI | 値 | 参照セル |
|---|---|---|
| 稼働率 | 88% | KPI_Drivers!E8 |
| 稼働人数 | 3,344名 | KPI_Drivers!E9（=在籍×稼働率） |
| 在籍登録スタッフ数 | 3,800名 | KPI_Drivers!E7 |
| 派遣単価 | 2,100円/h | KPI_Drivers!E11 |
| 採用単価CPA | 250千円/名 | KPI_Drivers!E15 |
| 月間平均稼働時間 | 166h | KPI_Drivers!E10 |

## 4. 意図的な不整合（デモ用）

- のれん想定額：モデル 5,500百万円（BS!F13・Assumptions D21）vs 財務DD 5,280百万円（p.31）→ 数値確定タブで不整合警告を表示
- PL_oldシート（旧版・全値0.965倍）とScratchシートはノイズであり抽出対象外

## 5. 抽出項目一覧（mockフィクスチャと1:1対応）

| key | セクション | 項目 | 必須 | 参照 |
|---|---|---|---|---|
| business_summary | 前提・定性情報 | 事業要約 | 必須 | DD_Business_オートスタッフ中部.pdf p.4〜5（1. エグゼクティブサマリー） |
| risk_concentration | 前提・定性情報 | 主要リスク①：顧客集中 | 必須 | DD_Business_オートスタッフ中部.pdf p.18（6.2 顧客集中度） |
| risk_overtime | 前提・定性情報 | 主要リスク②：未払残業代 | 必須 | DD_Legal_オートスタッフ中部.pdf p.12（4.3 未払残業代に係る潜在債務） |
| risk_recruiting | 前提・定性情報 | 主要リスク③：採用競争の激化 | 任意 | DD_Business_オートスタッフ中部.pdf p.16（5.3 採用とスタッフ定着） |
| normalized_ebitda | 前提・定性情報 | 正常収益力EBITDA（FY26） | 必須 | DD_Financial_オートスタッフ中部.pdf p.34（8.2 結論：正常収益力EBITDA） |
| act_revenue | 実績（FY24〜FY26） | 売上高 | 必須 | AutostaffChubu_Model_Base.xlsx PLシート C9:E9（9行・FY24〜FY26列） |
| act_op | 実績（FY24〜FY26） | 営業利益 | 必須 | AutostaffChubu_Model_Base.xlsx PLシート C21:E21（21行・FY24〜FY26列） |
| act_ebitda | 実績（FY24〜FY26） | EBITDA | 必須 | AutostaffChubu_Model_Base.xlsx PLシート C25:E25（25行・FY24〜FY26列） |
| act_ni | 実績（FY24〜FY26） | 当期純利益 | 任意 | AutostaffChubu_Model_Base.xlsx PLシート C32:E32（32行・FY24〜FY26列） |
| act_cash | 実績（FY24〜FY26） | 現預金 | 必須 | AutostaffChubu_Model_Base.xlsx BSシート C7:E7（7行・FY24〜FY26列） |
| act_net_assets | 実績（FY24〜FY26） | 純資産 | 必須 | AutostaffChubu_Model_Base.xlsx BSシート C23:E23（23行・FY24〜FY26列） |
| act_debt | 実績（FY24〜FY26） | 有利子負債 | 必須 | AutostaffChubu_Model_Base.xlsx BSシート C20:E20（20行・FY24〜FY26列） |
| act_fcf | 実績（FY24〜FY26） | フリー・キャッシュフロー | 任意 | AutostaffChubu_Model_Base.xlsx CFシート C13:E13（13行・FY24〜FY26列） |
| base_revenue | 計画：ベースケース（FY27〜FY31） | 売上高 | 必須 | AutostaffChubu_Model_Base.xlsx PLシート F9:J9（9行・FY27〜FY31列） |
| base_op | 計画：ベースケース（FY27〜FY31） | 営業利益 | 必須 | AutostaffChubu_Model_Base.xlsx PLシート F21:J21（21行・FY27〜FY31列） |
| base_ebitda | 計画：ベースケース（FY27〜FY31） | EBITDA | 必須 | AutostaffChubu_Model_Base.xlsx PLシート F25:J25（25行・FY27〜FY31列） |
| base_fcf | 計画：ベースケース（FY27〜FY31） | フリー・キャッシュフロー | 必須 | AutostaffChubu_Model_Base.xlsx CFシート F13:J13（13行・FY27〜FY31列） |
| sponsor_revenue | 計画：スポンサーケース（FY27〜FY31） | 売上高 | 必須 | AutostaffChubu_Model_Sponsor.xlsx PLシート F9:J9（9行・FY27〜FY31列） |
| sponsor_op | 計画：スポンサーケース（FY27〜FY31） | 営業利益 | 必須 | AutostaffChubu_Model_Sponsor.xlsx PLシート F21:J21（21行・FY27〜FY31列） |
| sponsor_ebitda | 計画：スポンサーケース（FY27〜FY31） | EBITDA | 必須 | AutostaffChubu_Model_Sponsor.xlsx PLシート F25:J25（25行・FY27〜FY31列） |
| sponsor_fcf | 計画：スポンサーケース（FY27〜FY31） | フリー・キャッシュフロー | 任意 | AutostaffChubu_Model_Sponsor.xlsx CFシート F13:J13（13行・FY27〜FY31列） |
| goodwill | ストラクチャー・B/S項目 | のれん（買収想定額） | 必須 | AutostaffChubu_Model_Base.xlsx BSシート F13（FY27列）／Assumptionsシート D21 |
| ev | ストラクチャー・B/S項目 | エンタープライズ・バリュー（EV） | 必須 | AutostaffChubu_Model_Base.xlsx Assumptionsシート D8 |
| senior_loan | ストラクチャー・B/S項目 | シニアローン総額 | 必須 | AutostaffChubu_Model_Base.xlsx Assumptionsシート D10／Debt_Scheduleシート F7 |

## 6. シナリオ・審査相談メモの正本

- シナリオA（AI推奨・トップライン）：稼働率▲15%・採用▲20% → Year 2 DSCR 0.9倍前後（AI推定）→ 採用
- シナリオB（AI推奨・コスト）：CPA+30%・時給+5% → Year 3以降レバレッジ5.0x超（AI推定）→ 採用
- シナリオC（AI推奨・イベント）：未払残業代300百万円特損 → Year 1現預金枯渇リスク（AI推定）→ 不採用
- シナリオD（人の仮説）：大口派遣先（構成比28%）の契約終了 → 採用
- 審査相談メモ：7/5 続行 ／ 7/12 再検討（指摘3件）→ 検討ステータス「再検討中」
