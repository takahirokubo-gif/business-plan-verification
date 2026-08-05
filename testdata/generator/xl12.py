# -*- coding: utf-8 -*-
"""12期版財務モデルExcelのシート・行レイアウト定義（A/B共通）。

dummy_input/xl_layout.py の行番号体系を踏襲し、12期（C〜N列）・月次試算表・
Assumptions年度別ブロック・B側の科目改称と補足小表の座標を追加定義する。
"""
from spec12 import COL, MONTHS

# シート名
SHEET_COVER = "Cover"
SHEET_ASSUMPTIONS = "Assumptions"
SHEET_PL = "PL"
SHEET_BS = "BS"
SHEET_CF = "CF"
SHEET_KPI = "KPI_Drivers"
SHEET_DEBT = "Debt_Schedule"
SHEET_MONTHLY = "月次試算表_FY26"
# ノイズシート（Bのみ）
SHEET_PL_OLD = "PL_old"
SHEET_SCRATCH = "Scratch"
SHEET_EMPTY = "Sheet1"

HEADER_ROW = 4
KIND_ROW = 5

# 月次試算表の月列（C〜N）と年度計列
MCOL = {m: chr(ord("C") + i) for i, m in enumerate(MONTHS)}
MONTHLY_TOTAL_COL = "O"

KPI_ROWS = {
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
}

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
    "depreciation": (24, "減価償却費"),
    "ebitda": (25, "Adj. EBITDA"),
    "ebitda_margin": (26, "EBITDAマージン"),
    "interest": (28, "支払利息"),
    "non_op": (29, "営業外損益（純額）"),
    "ordinary": (30, "経常利益"),
    "tax": (31, "法人税等（実効税率31%）"),
    "ni": (32, "当期純利益"),
}

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

# Debt_Schedule（行ラベルは英語：E4条件）
DEBT_ROWS = {
    "opening": (7, "Beginning Balance"),
    "repayment": (8, "Mandatory Amortization"),
    "closing": (9, "Ending Balance"),
    "avg": (10, "Average Balance"),
    "rate": (11, "Interest Rate (TIBOR+200bp)"),
    "interest": (12, "Interest Expense"),
}
DEBT_NOTE = ("Note: Annual mandatory amortization of JPY 650,000 thousand; "
             "bullet repayment of the remaining balance in FY33.")

# 月次試算表 行定義（キー, 行, Aでのラベル, Bでのラベル）
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

# Assumptions レイアウト
ASM_YEARLY_SECTION_ROW = 6      # 「オペレーティング前提（年度別）」
ASM_YEARLY_ROWS = {
    "util": (7, "稼働率（Utilization）", "=KPI_Drivers!{c}%d" % KPI_ROWS["util"][0], "0.0%"),
    "bill": (8, "派遣単価（円/h）", "=KPI_Drivers!{c}%d" % KPI_ROWS["bill"][0], "#,##0"),
    "cpa": (9, "採用単価（CPA・千円/名）", "=KPI_Drivers!{c}%d" % KPI_ROWS["cpa"][0], "#,##0"),
    "hires": (10, "新規採用人数（名）", "=KPI_Drivers!{c}%d" % KPI_ROWS["hires"][0], "#,##0"),
}
ASM_STRUCT_SECTION_ROW = 12     # 「ストラクチャー（千円）」
ASM_KV_ROWS = [
    # (row, label, value_key, fmt)   value_keyはbuild側で解決
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
ASM_OTHER_SECTION_ROW = 23      # 「その他前提」
ASM_OTHER_ROWS = [
    (24, "実効税率", "tax_rate", "0.0%"),
    (25, "売上債権回転日数", "ar_days", "0"),
    (26, "買収時現金調整（取引費用等）", "cash_adj", "#,##0"),
]
ASM_TEASER_ROW = 28             # Bのみ
ASM_TEASER_LABEL = "スポンサー提示EBITDA（速報・ティーザー記載）"
ASM_OLDNOTE_ROW = 30            # Bのみ
ASM_OLDNOTE = "（参考）旧前提 v2.1：シニア7,000,000／金利2.4%　※現行版では使用しない"

# B側の科目改称（E7/X1）。(シート, 行キー, 旧ラベル, 新ラベル, DD側呼称)
RENAMES = [
    (SHEET_PL, "revenue", "売上高（Net Sales）", "売上収益", "売上高"),
    (SHEET_PL, "labor", "スタッフ労務費（法定福利費込）", "現業人件費（福利込）", "スタッフ労務費（法定福利費込）"),
    (SHEET_PL, "ebitda", "Adj. EBITDA", "修正EBITDA", "EBITDA（正常収益力EBITDA）"),
    (SHEET_BS, "ar", "売上債権", "売掛金等", "売上債権"),
    (SHEET_BS, "oca", "その他流動資産", "その他流動", "その他流動資産"),
    (SHEET_BS, "ap", "仕入債務・未払費用", "買掛・未払等", "仕入債務・未払費用"),
]
# 月次試算表のB側改称（上記と同一方針）
MONTHLY_RENAME_KEYS = {"revenue", "ar", "ap"}

# B側 補足小表（E10）
SIDE_TABLE_PL = dict(title_cell="P3", title="■単価改定履歴（社内メモ）",
                     origin=("P", 4))     # ヘッダー行P4:R4＋FY27〜33の7行
SIDE_TABLE_KPI = dict(title_cell="B19", title="■採用チャネル内訳（FY26実績）",
                      origin=("B", 20))   # ヘッダー行B20:D20＋4行
SIDE_TABLE_BS = dict(title_cell="P3", title="■寮関連メモ（スタッフ管理本部）",
                     origin=("P", 4))     # 5行×2列
KPI_CHANNELS = [("求人媒体（Web）", 732, 0.62),
                ("リファラル（在籍スタッフ紹介）", 271, 0.23),
                ("その他（ハローワーク等）", 177, 0.15)]
DORM_MEMO = [("借上げ寮（棟）", 9), ("自社保有寮（棟）", 3), ("収容能力（名）", 900),
             ("年間借上げ賃料（千円）", 210_000), ("送迎バス（台）", 18)]

# E11：Bの本体側で破損させるセル（PL支払利息の計画7期）
BROKEN_INTEREST_FORMULA = "=#REF!{c}%d" % DEBT_ROWS["interest"][0]


def cell(sheet: str, row_key: str, year: str) -> str:
    rows = {SHEET_PL: PL_ROWS, SHEET_BS: BS_ROWS, SHEET_CF: CF_ROWS,
            SHEET_KPI: KPI_ROWS, SHEET_DEBT: DEBT_ROWS}[sheet]
    return f"{sheet}!{COL[year]}{rows[row_key][0]}"
