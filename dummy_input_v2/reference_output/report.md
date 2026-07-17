<!-- これは模範解答（reference_output/reference_*.json）を採点した場合の
レポート。実AIの出力が正しければ、report.md はこれと同水準になる。 -->

# 実AIテスト採点レポート（ルミエールボーテ・理想的インプット）

## identify（ファイル識別）: 6/6
- OK LumiereBeaute_LBO_Model_v2.3_Sponsor.xlsx: model_sponsor（期待 model_sponsor）
- OK LumiereBeaute_LBO_Model_v2.3_BankBase.xlsx: model_base（期待 model_base）
- OK 事業DD報告書_ルミエールボーテ_最終版.pdf: dd_business（期待 dd_business）
- OK 財務DD報告書_ルミエールボーテ_最終版.pdf: dd_financial（期待 dd_financial）
- OK 法務DD報告書_ルミエールボーテ_最終版.pdf: dd_legal（期待 dd_legal）
- OK 税務DD報告書_ルミエールボーテ_最終版.pdf: dd_tax（期待 dd_tax）

## deal_info（案件基本情報）: 13/13
- OK name: 取得 `ルミエールボーテ LBOファイナンス`（期待 `['ルミエールボーテ']`）
- OK deal_type: 取得 `LBO`（期待 `LBO`）
- OK borrower: 取得 `株式会社ブルームホールディングス`（期待 `株式会社ブルームホールディングス`）
- OK target: 取得 `株式会社ルミエールボーテ`（期待 `株式会社ルミエールボーテ`）
- OK industry: 取得 `化粧品・スキンケアの企画販売（D2C・卸）`（期待 `['化粧品', 'スキンケア']`）
- OK sponsor: 取得 `大手町プリンシパルパートナーズ株式会社`（期待 `大手町プリンシパルパートナーズ株式会社`）
- OK close_date: 取得 `2026-11-30`（期待 `2026-11-30`）
- OK ev_mm: 取得 `9000`（期待 `9000`）
- OK senior_mm: 取得 `4800`（期待 `4800`）
- OK equity_mm: 取得 `4620`（期待 `4620`）
- OK tenor_years: 取得 `7`（期待 `7`）
- OK sponsor_ebitda_mm: 取得 `1120`（期待 `1120`）
- OK sources（全フィールドに出典）: 取得 `13件`（期待 `各フィールドの出典`）

## items（抽出24項目）: **🟢 合格**
- 合格ライン: 必須項目：値一致率100% かつ 根拠一致率90%以上
- 必須項目の値一致率: 100%（20/20）／ 必須項目の根拠一致率: 100%（20/20）
- 参考（全24項目）: 発見 24/24 ／ 値完全一致 24/24 ／ 根拠一致 24/24 ／ 不整合検知 1/1

| key | 発見 | 値 | 根拠 | 不整合 | メモ |
|---|---|---|---|---|---|
| business_summary | ○ | 100% | ○ | - |  |
| risk_oem | ○ | 100% | ○ | - |  |
| risk_wholesale | ○ | 100% | ○ | - |  |
| risk_trademark | ○ | 100% | ○ | - |  |
| normalized_ebitda | ○ | 100% | ○ | - |  |
| act_revenue | ○ | 100% | ○ | - |  |
| act_op | ○ | 100% | ○ | - |  |
| act_ebitda | ○ | 100% | ○ | - |  |
| act_ni | ○ | 100% | ○ | - |  |
| act_cash | ○ | 100% | ○ | - |  |
| act_net_assets | ○ | 100% | ○ | - |  |
| act_debt | ○ | 100% | ○ | - |  |
| act_fcf | ○ | 100% | ○ | - |  |
| base_revenue | ○ | 100% | ○ | - |  |
| base_op | ○ | 100% | ○ | - |  |
| base_ebitda | ○ | 100% | ○ | - |  |
| base_fcf | ○ | 100% | ○ | - |  |
| sponsor_revenue | ○ | 100% | ○ | - |  |
| sponsor_op | ○ | 100% | ○ | - |  |
| sponsor_ebitda | ○ | 100% | ○ | - |  |
| sponsor_fcf | ○ | 100% | ○ | - |  |
| goodwill | ○ | 100% | ○ | ○ |  |
| ev | ○ | 100% | ○ | - |  |
| senior_loan | ○ | 100% | ○ | - |  |

## kpi_tree（構造ルーブリック）: エッジ 11/11・ノード17個
- ★: 4（うち候補内 4・最低2） → OK ／ DD由来ノード: 2個
- OK 売上収益 → EC売上
- OK 売上収益 → 卸売上
- OK EC売上 → 会員数
- OK EC売上 → 購入回数
- OK EC売上 → 注文単価
- OK 会員数 → リピート率
- OK 会員数 → 新規獲得
- OK 卸売上 → 店舗数
- OK 卸売上 → 店舗あたり
- OK 売上原価 → 原価率
- OK 広告宣伝費 → 広告宣伝費率

## scenarios（構造ルーブリック）: 3件・3類型カバー=OK
- A（トップライン）リピート率低下＋大口卸チェーンの棚割り縮小
  - 5部構成欠落: なし / 数値推定: ○ / DSCR等への言及: ○ / 判定ラベル混入: なし / DD事実の引用: True
- B（コスト）OEM値上げによる原価率上昇と広告CPA高騰の併発
  - 5部構成欠落: なし / 数値推定: ○ / DSCR等への言及: ○ / 判定ラベル混入: なし / DD事実の引用: True
- C（イベント）OEM契約のCOC同意未取得による供給停止
  - 5部構成欠落: なし / 数値推定: ○ / DSCR等への言及: ○ / 判定ラベル混入: なし / DD事実の引用: True

---
生出力は test_results/raw_*.json。KPIツリー・シナリオは人手レビューを併用すること。
