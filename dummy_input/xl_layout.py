"""財務モデルExcelのシート・行レイアウト定義。

generate_model.py（Excel生成）と generate_fixtures.py（mock抽出結果の参照セル）が
共有する。ここを変えたら両方が自動的に追随する。
"""
from spec import COL

# シート名
SHEET_COVER = "Cover"
SHEET_ASSUMPTIONS = "Assumptions"
SHEET_PL = "PL"
SHEET_BS = "BS"
SHEET_CF = "CF"
SHEET_KPI = "KPI_Drivers"
SHEET_DEBT = "Debt_Schedule"
# ノイズシート
SHEET_PL_OLD = "PL_old"
SHEET_SCRATCH = "Scratch"
SHEET_EMPTY = "Sheet1"

HEADER_ROW = 4       # 年度ヘッダー行
KIND_ROW = 5         # 実績/計画 行
DATA_START = 7

# KPI_Drivers 行番号
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

# PL 行番号
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

# BS 行番号
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

# CF 行番号
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

# Debt_Schedule 行番号
DEBT_ROWS = {
    "opening": (7, "期首残高"),
    "repayment": (8, "約定弁済"),
    "closing": (9, "期末残高"),
    "avg": (10, "平均残高"),
    "rate": (11, "適用金利（TIBOR+200bp想定）"),
    "interest": (12, "支払利息"),
}


def cell(sheet: str, row_key: str, year: str) -> str:
    """例: cell('PL', 'revenue', 'FY26') -> 'PL!E9'"""
    rows = {"PL": PL_ROWS, "BS": BS_ROWS, "CF": CF_ROWS,
            "KPI_Drivers": KPI_ROWS, "Debt_Schedule": DEBT_ROWS}[sheet]
    return f"{sheet}!{COL[year]}{rows[row_key][0]}"


def cell_range(sheet: str, row_key: str, year_from: str, year_to: str) -> str:
    """例: cell_range('PL', 'revenue', 'FY24', 'FY26') -> 'PL!C9:E9'"""
    rows = {"PL": PL_ROWS, "BS": BS_ROWS, "CF": CF_ROWS,
            "KPI_Drivers": KPI_ROWS, "Debt_Schedule": DEBT_ROWS}[sheet]
    r = rows[row_key][0]
    return f"{sheet}!{COL[year_from]}{r}:{COL[year_to]}{r}"
