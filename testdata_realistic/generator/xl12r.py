# -*- coding: utf-8 -*-
"""実物テンプレ型（リアリティ版）財務モデルのレイアウト定義。

actual_data_sample/財務モデルサンプル の規約に準拠：
- シート構成: Cover / inp / PL / BS / CF / calc / debt / 月次試算表_FY26
  （inp=前提入力、calc=KPI・派生計算、debt=銘柄別デットスケジュール）
- 年度ヘッダーは FY22A〜FY26A（実績）/ FY27E〜FY33E（予想）
- 費用・返済は負値で保持し、縦計算は SUM／加算（実務モデルの符号規約）
- 入力セルは青字（#0070C0）、数式セルは黒字

数値の正本は testdata/generator/spec12.py（v2と共通・変更なし）。
"""
import sys
from pathlib import Path

_V2_GEN = Path(__file__).resolve().parents[2] / "testdata" / "generator"
sys.path.insert(0, str(_V2_GEN))
from spec12 import COL, MONTHS, YEARS, ACTUAL_YEARS  # noqa: E402,F401

# シート名
SHEET_COVER = "Cover"
SHEET_INP = "inp"
SHEET_PL = "PL"
SHEET_BS = "BS"
SHEET_CF = "CF"
SHEET_CALC = "calc"
SHEET_DEBT = "debt"
SHEET_MONTHLY = "月次試算表_FY26"
# ノイズシート（Bのみ）
SHEET_PL_OLD = "PL_old"
SHEET_SCRATCH = "Scratch"
SHEET_EMPTY = "Sheet1"

HEADER_ROW = 4
KIND_ROW = 5

# 年度ヘッダー表示（実績=A / 予想=E サフィックス）
def year_label(y: str) -> str:
    return f"{y}A" if y in ACTUAL_YEARS else f"{y}E"


MCOL = {m: chr(ord("C") + i) for i, m in enumerate(MONTHS)}
MONTHLY_TOTAL_COL = "O"

# 符号規約：負値で保持する行（PL）
NEGATIVE_KEYS = {"labor", "other_cogs", "cogs", "recruiting", "hq_cost", "other_sga",
                 "sga", "interest", "tax"}

# calc（KPIドライバー＋派生計算）
CALC_ROWS = {
    "enrolled": (7, "在籍登録スタッフ数（名）"),
    "util": (8, "稼働率（Utilization）"),
    "active": (9, "稼働人数（名）"),
    "hours": (10, "月間平均稼働時間（h/名）"),
    "bill": (11, "派遣単価（円/h）"),
    "wage": (12, "スタッフ平均時給（円/h）"),
    "welfare": (13, "法定福利費率"),
    "hires": (14, "新規採用人数（名）"),
    "cpa": (15, "採用単価（CPA・千円/名）"),
    "attrition": (16, "離職率（年間）"),
    # 派生計算（PLが参照）
    "staffing_rev_calc": (18, "派遣事業売上（千円）"),
    "labor_calc": (19, "スタッフ労務費（千円・負値）"),
    "recruiting_calc": (20, "採用費（千円・負値）"),
}

# PL（費用は負値・SUM縦計算）
PL_ROWS = {
    "staffing_rev": (7, "派遣事業売上"),
    "other_revenue": (8, "その他営業収入（紹介手数料等）"),
    "revenue": (9, "売上高（Net Sales）"),
    "labor": (11, "スタッフ労務費（法定福利費込）"),
    "other_cogs": (12, "その他売上原価"),
    "cogs": (13, "売上原価 合計"),
    "gross": (14, "売上総利益"),
    "gross_margin": (15, "売上総利益率"),
    "recruiting": (17, "採用費"),
    "hq_cost": (18, "本社人件費"),
    "other_sga": (19, "その他販管費"),
    "sga": (20, "販売費及び一般管理費 合計"),
    "op": (21, "営業利益（Operating Profit）"),
    "op_margin": (22, "営業利益率"),
    "depreciation": (24, "減価償却費及び償却費（参考）"),
    "ebitda": (25, "Adj. EBITDA"),
    "ebitda_margin": (26, "EBITDAマージン"),
    "interest": (28, "支払利息"),
    "non_op": (29, "営業外損益（純額）"),
    "ordinary": (30, "経常利益"),
    "tax": (31, "法人税等（実効税率31%）"),
    "ni": (32, "当期純利益"),
}

# BS（v2と同一レイアウト・全て正値）
BS_ROWS = {
    "cash": (7, "現金及び預金"),
    "ar": (8, "売上債権"),
    "oca": (9, "その他流動資産"),
    "current_assets": (10, "流動資産 合計"),
    "ppe": (12, "有形固定資産"),
    "goodwill": (13, "のれん（Goodwill）"),
    "intangible": (14, "無形固定資産・その他"),
    "fixed_assets": (15, "固定資産 合計"),
    "total_assets": (16, "資産合計"),
    "ap": (18, "仕入債務・未払費用"),
    "other_liab": (19, "その他負債"),
    "debt": (20, "有利子負債"),
    "total_liab": (21, "負債合計"),
    "net_assets": (23, "純資産（Net Assets）"),
    "total_le": (24, "負債純資産合計"),
}

CF_ROWS = {
    "ni": (7, "税引後当期純利益"),
    "depreciation": (8, "減価償却費"),
    "wc": (9, "運転資本増減・その他（△増加）"),
    "op_cf": (10, "営業キャッシュフロー"),
    "inv_cf": (12, "設備投資等（投資CF）"),
    "fcf": (13, "フリー・キャッシュフロー（FCF）"),
    "repay": (15, "借入金返済"),
    "fin_other": (16, "配当・その他財務"),
    "fin_cf": (17, "財務キャッシュフロー"),
    "net_change": (19, "現金増減"),
    "opening_cash": (20, "期首現金"),
    "closing_cash": (21, "期末現金"),
}

# debt（銘柄別ブロック・行ラベル英語：E4条件）
# ブロック1: 既存借入（実績期・リファイナンス対象）
DEBT_EXISTING_TITLE = (6, "Existing Bank Facility (to be refinanced at closing)")
DEBT_EXISTING_ROWS = {
    "ex_opening": (7, "Beginning Balance"),
    "ex_repayment": (8, "Repayment"),
    "ex_closing": (9, "Ending Balance"),
    "ex_rate": (10, "Interest Rate"),
    "ex_interest": (11, "Interest Expense"),
}
# ブロック2: シニアローン（計画期・タームローンA相当）
DEBT_SENIOR_TITLE = (13, "Senior Term Loan A (TIBOR+200bp)")
DEBT_ROWS = {
    "opening": (14, "Beginning Balance"),
    "repayment": (15, "Mandatory Amortization"),
    "closing": (16, "Ending Balance"),
    "avg": (17, "Average Balance"),
    "rate": (18, "Interest Rate (TIBOR+200bp)"),
    "interest": (19, "Interest Expense"),
}
DEBT_NOTES = [
    (21, "Note: Annual mandatory amortization of JPY 650,000 thousand; "
         "bullet repayment of the remaining balance in FY33."),
    (22, "Note: Committed line facility to be arranged post-closing (not included above)."),
]

MONTHLY_ROWS = {
    "revenue": (7, "売上高", "売上収益"),
    "cogs": (8, "売上原価", "売上原価"),
    "gross": (9, "売上総利益", "売上総利益"),
    "sga": (10, "販売費及び一般管理費", "販売費及び一般管理費"),
    "op": (11, "営業利益", "営業利益"),
    "cash": (13, "現金及び預金", "現金及び預金"),
    "ar": (14, "売上債権", "売掛金等"),
    "ap": (15, "仕入債務・未払費用", "買掛・未払等"),
}

# inp（前提条件）レイアウト：v2 Assumptionsを踏襲（シート名と体裁のみ実物流）
ASM_YEARLY_SECTION_ROW = 6
ASM_YEARLY_ROWS = {
    "util": (7, "稼働率（Utilization）", "=calc!{c}%d" % CALC_ROWS["util"][0], "0.0%"),
    "bill": (8, "派遣単価（円/h）", "=calc!{c}%d" % CALC_ROWS["bill"][0], "#,##0"),
    "cpa": (9, "採用単価（CPA・千円/名）", "=calc!{c}%d" % CALC_ROWS["cpa"][0], "#,##0"),
    "hires": (10, "新規採用人数（名）", "=calc!{c}%d" % CALC_ROWS["hires"][0], "#,##0"),
}
ASM_STRUCT_SECTION_ROW = 12
ASM_KV_ROWS = [
    (13, "エンタープライズ・バリュー（EV）", "ev", "#,##0"),
    (14, "エクイティ出資", "equity", "#,##0"),
    (15, "シニアローン総額", "senior", "#,##0"),
    (16, "　うち参加金融機関A行 想定取組額", "bank_a", "#,##0"),
    (17, "ローン期間（年）", "tenor", "0"),
    (18, "適用金利（TIBOR+200bp想定）", "rate", "0.0%"),
    (19, "約定弁済（年・最終回残額一括）", "repay", "#,##0"),
    (20, "クローズ想定", "close", None),
    (21, "のれん想定額（暫定PPA前）", "goodwill", "#,##0"),
]
ASM_OTHER_SECTION_ROW = 23
ASM_OTHER_ROWS = [
    (24, "実効税率", "tax_rate", "0.0%"),
    (25, "売上債権回転日数", "ar_days", "0"),
    (26, "買収時現金調整（取引費用等）", "cash_adj", "#,##0"),
]
ASM_TEASER_ROW = 28
ASM_TEASER_LABEL = "スポンサー提示EBITDA（速報・ティーザー記載）"
ASM_OLDNOTE_ROW = 30
ASM_OLDNOTE = "（参考）旧前提 v2.1：シニア7,000,000／金利2.4%　※現行版では使用しない"

# B側の科目改称（v2と同一定義）
RENAMES = [
    (SHEET_PL, "revenue", "売上高（Net Sales）", "売上収益", "売上高"),
    (SHEET_PL, "labor", "スタッフ労務費（法定福利費込）", "現業人件費（福利込）", "スタッフ労務費（法定福利費込）"),
    (SHEET_PL, "ebitda", "Adj. EBITDA", "修正EBITDA", "EBITDA（正常収益力EBITDA）"),
    (SHEET_BS, "ar", "売上債権", "売掛金等", "売上債権"),
    (SHEET_BS, "oca", "その他流動資産", "その他流動", "その他流動資産"),
    (SHEET_BS, "ap", "仕入債務・未払費用", "買掛・未払等", "仕入債務・未払費用"),
]
MONTHLY_RENAME_KEYS = {"revenue", "ar", "ap"}

# B側 補足小表（E10・v2と同一内容）
SIDE_TABLE_PL = dict(title_cell="P3", title="■単価改定履歴（社内メモ）", origin=("P", 4))
SIDE_TABLE_CALC = dict(title_cell="B23", title="■採用チャネル内訳（FY26実績）", origin=("B", 24))
SIDE_TABLE_BS = dict(title_cell="P3", title="■寮関連メモ（スタッフ管理本部）", origin=("P", 4))
KPI_CHANNELS = [("求人媒体（Web）", 732, 0.62),
                ("リファラル（在籍スタッフ紹介）", 271, 0.23),
                ("その他（ハローワーク等）", 177, 0.15)]
DORM_MEMO = [("借上げ寮（棟）", 9), ("自社保有寮（棟）", 3), ("収容能力（名）", 900),
             ("年間借上げ賃料（千円）", 210_000), ("送迎バス（台）", 18)]

# E11：Bの本体側で破損させるセル（PL支払利息。debt側が負値保持のため直接参照）
BROKEN_INTEREST_FORMULA = "=#REF!{c}%d" % DEBT_ROWS["interest"][0]


# ---------------------------------------------------------------- v2互換エイリアス
# v2（testdata/）の checks / review / build_ground_truth を最小変更で移植するための別名。
SHEET_ASSUMPTIONS = SHEET_INP
SHEET_KPI = SHEET_CALC
KPI_ROWS = CALC_ROWS
SIDE_TABLE_KPI = SIDE_TABLE_CALC
