"""財務モデルExcel（v2・ルミエールボーテ）のシート・行レイアウト定義。

generate_model.py（Excel生成）と generate_expected.py（期待値の参照セル）が共有する。
ここを変えたら両方が自動的に追随する。

実在のLBOモデルテンプレート（Cover / inp / calc / debt 構成・百万円単位）の
慣行に寄せたシート構成とし、既存デモ（Assumptions / KPI_Drivers 構成・千円単位）
とは意図的に様式を変えている。
"""
from spec import COL

# シート名（実在テンプレートは小文字の inp / debt 等を使う）
SHEET_COVER = "Cover"
SHEET_INP = "inp"
SHEET_PL = "PL"
SHEET_BS = "BS"
SHEET_CF = "CF"
SHEET_DEBT = "debt"
# ノイズシート（成果物ではない作業メモ）
SHEET_MEMO = "memo"

HEADER_ROW = 4       # 年度ヘッダー行（2024/3期 …）
KIND_ROW = 5         # 実績/計画 行
DATA_START = 7

# inp シート：ストラクチャー（B列=ラベル, D列=値）
INP_STRUCT_ROWS = {
    "ev": (8, "エンタープライズ・バリュー（EV）"),
    "ev_multiple": (9, "EV/EBITDA倍率（2026/3期実績対比）"),
    "equity_value": (10, "株式対価（想定）"),
    "senior": (11, "シニアタームローンA"),
    "equity": (12, "スポンサーエクイティ"),
    "refi": (13, "既存借入リファイナンス"),
    "fees": (14, "アドバイザリー・取引費用等"),
    "cash_used": (15, "対象会社手元現金の活用"),
    "goodwill": (16, "のれん想定額（暫定PPA前）"),
    "tenor": (17, "ローン期間（年）"),
    "rate": (18, "適用金利（TIBOR+230bp想定）"),
    "repayment": (19, "約定弁済（年・最終回残額一括）"),
    "sponsor_ebitda": (21, "スポンサー提示EBITDA（2026/3期実績・速報）"),
    "close": (22, "クローズ予定日"),
    "borrower": (23, "借入人（SPC）"),
}

# inp シート：KPIドライバー表（年度列 C〜J）
INP_DRIVER_HEADER_ROW = 27
INP_DRIVER_KIND_ROW = 28
INP_DRIVER_ROWS = {
    "member": (30, "アクティブ会員数（人）"),
    "repeat": (31, "リピート率（既存会員残存率）"),
    "new": (32, "新規獲得会員数（人）"),
    "freq": (33, "年間平均購入回数（回）"),
    "aov": (34, "平均注文単価（AOV・円）"),
    "doors": (35, "卸取扱店舗数（店）"),
    "perdoor": (36, "店舗あたり年間出荷額（千円）"),
    "cogs_rate": (37, "売上原価率（対売上）"),
    "ad_rate": (38, "広告宣伝費率（対売上）"),
    "log_rate": (39, "物流費率（対売上）"),
    "capex": (41, "設備投資（年間）"),
}

# PL 行番号
PL_ROWS = {
    "ec_rev": (7, "EC売上（自社EC・モール計）"),
    "ws_rev": (8, "卸売上（ドラッグストア・バラエティ）"),
    "other_revenue": (9, "その他売上（百貨店・海外）"),
    "revenue": (10, "売上収益 合計"),
    "cogs": (12, "売上原価（OEM仕入・資材）"),
    "gross": (13, "売上総利益"),
    "gross_margin": (14, "売上総利益率"),
    "ad": (16, "広告宣伝費"),
    "logistics": (17, "物流費（配送・倉庫）"),
    "personnel": (18, "人件費"),
    "other_sga": (19, "その他販管費"),
    "sga": (20, "販売費及び一般管理費 合計"),
    "op": (21, "営業利益（EBIT）"),
    "op_margin": (22, "営業利益率"),
    "depreciation": (24, "減価償却費及び償却費"),
    "ebitda": (25, "EBITDA"),
    "ebitda_margin": (26, "EBITDAマージン"),
    "interest": (28, "支払利息"),
    "non_op": (29, "営業外損益（純額）"),
    "ordinary": (30, "経常利益"),
    "tax": (31, "法人税等（実効税率30.5%）"),
    "ni": (32, "当期純利益"),
}

# BS 行番号
BS_ROWS = {
    "cash": (7, "現金及び現金同等物"),
    "ar": (8, "営業債権（売掛金）"),
    "inv": (9, "棚卸資産"),
    "oca": (10, "その他流動資産"),
    "ppe": (11, "有形固定資産"),
    "goodwill": (12, "のれん"),
    "intangible": (13, "無形固定資産・その他"),
    "total_assets": (14, "資産合計"),
    "ap": (16, "営業債務（買掛金・未払費用）"),
    "other_liab": (17, "その他負債"),
    "debt": (18, "有利子負債"),
    "total_liab": (19, "負債合計"),
    "net_assets": (21, "純資産"),
    "total_le": (22, "負債純資産合計"),
}

# CF 行番号
CF_ROWS = {
    "ni": (7, "税引後当期純利益"),
    "depreciation": (8, "減価償却費及び償却費"),
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

# debt 行番号
DEBT_ROWS = {
    "opening": (7, "期初残高"),
    "repayment": (8, "約定弁済"),
    "closing": (9, "期末残高"),
    "avg": (10, "平均残高"),
    "rate": (11, "適用金利（TIBOR+230bp想定）"),
    "interest": (12, "支払利息"),
}

_ROWMAP = {"PL": PL_ROWS, "BS": BS_ROWS, "CF": CF_ROWS, "debt": DEBT_ROWS,
           "inp": INP_DRIVER_ROWS}


def cell(sheet: str, row_key: str, year: str) -> str:
    """例: cell('PL', 'revenue', 'FY26') -> 'PL!E10'"""
    return f"{sheet}!{COL[year]}{_ROWMAP[sheet][row_key][0]}"


def cell_range(sheet: str, row_key: str, year_from: str, year_to: str) -> str:
    """例: cell_range('PL', 'revenue', 'FY24', 'FY26') -> 'PL!C10:E10'"""
    r = _ROWMAP[sheet][row_key][0]
    return f"{sheet}!{COL[year_from]}{r}:{COL[year_to]}{r}"
