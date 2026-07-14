"""オートスタッフ中部LBO デモデータの正本（Single Source of Truth）。

すべてのダミーインプット（財務モデルExcel・DDレポートPDF）、mockフィクスチャ、
GROUND_TRUTH.md はこのファイルの定義から生成する。
数値を変更する場合は必ずここを変更し、generate_all.py → validate.py を実行すること。

単位規約:
- Excel財務モデル内の金額はすべて千円（各シートに「（単位：千円）」を明記）
- UI・フィクスチャの表示は百万円（display = excel_round(千円 / 1000)）
"""
import math

# ---------------------------------------------------------------- 基本規約


def excel_round(x: float, digits: int = 0) -> float:
    """ExcelのROUND（0.5は0から遠い方へ）。Pythonのroundは銀行丸めのため使わない。"""
    factor = 10 ** digits
    v = x * factor
    if v >= 0:
        r = math.floor(v + 0.5)
    else:
        r = math.ceil(v - 0.5)
    return r / factor if digits else int(r)


def to_mm(thousand_yen: float) -> int:
    """千円 → 百万円（表示用丸め）。"""
    return int(excel_round(thousand_yen / 1000))


YEARS = ["FY24", "FY25", "FY26", "FY27", "FY28", "FY29", "FY30", "FY31"]
ACTUAL_YEARS = ["FY24", "FY25", "FY26"]
PLAN_YEARS = ["FY27", "FY28", "FY29", "FY30", "FY31"]
# 年度→Excel列（B=項目名、C以降が年度）
COL = {y: chr(ord("C") + i) for i, y in enumerate(YEARS)}

CASES = ["sponsor", "base"]
CASE_LABEL = {"sponsor": "Sponsor Case", "base": "Base Case"}
CASE_LABEL_JA = {"sponsor": "スポンサーケース", "base": "ベースケース"}

# ---------------------------------------------------------------- 案件基本情報

DEAL = {
    "name": "オートスタッフ中部 LBOファイナンス",
    "deal_type": "LBO",
    "borrower": "株式会社ASホールディングス",  # SPC
    "target": "株式会社オートスタッフ中部",
    "industry": "自動車製造派遣（東海地盤）",
    "sponsor": "日本橋キャピタルパートナーズ株式会社",
    "close_date": "2026-09-30",
    "next_meeting_date": "2026-07-18",
    "ev_mm": 12000,            # EV 12,000百万円
    "senior_mm": 6500,         # シニアローン総額
    "our_commitment_mm": 2500,  # 本行取組額
    "equity_mm": 5500,         # エクイティ
    "tenor_years": 7,
    "sponsor_ebitda_mm": 1585,  # スポンサー提示EBITDA（速報値）→ 初期レバレッジ自動算出用
    "summary": (
        "日本橋キャピタルパートナーズによる自動車製造派遣大手・オートスタッフ中部のLBO。"
        "東海地区の完成車・部品メーカー向け製造派遣で地盤を持ち、稼働率88%と業界高水準。"
        "オーナー創業者の事業承継ニーズを背景としたスポンサー主導の買収案件。"
    ),
}
# 自動算出（四則演算のみ・再計算エンジンには該当しない）
DEAL["initial_leverage"] = round(DEAL["senior_mm"] / DEAL["sponsor_ebitda_mm"], 1)  # 4.1x
DEAL["ltv_pct"] = round(DEAL["senior_mm"] / DEAL["ev_mm"] * 100)  # 54%

# ---------------------------------------------------------------- KPIドライバー
# 行キー: enrolled(在籍登録スタッフ数・名), util(稼働率), active(稼働人数・名=ROUND(enrolled*util)),
# hours(月間平均稼働時間 h/名), bill(派遣単価 円/h), wage(スタッフ平均時給 円/h),
# welfare(法定福利費率), hires(新規採用人数・名), cpa(採用単価 千円/名), attrition(年間離職率)

_ACTUAL_DRIVERS = {
    "FY24": dict(enrolled=3560, util=0.865, hours=165, bill=2020, wage=1400,
                 welfare=0.14, hires=1050, cpa=225, attrition=0.24),
    "FY25": dict(enrolled=3690, util=0.872, hours=166, bill=2060, wage=1425,
                 welfare=0.14, hires=1120, cpa=238, attrition=0.23),
    "FY26": dict(enrolled=3800, util=0.880, hours=166, bill=2100, wage=1450,
                 welfare=0.14, hires=1180, cpa=250, attrition=0.22),
}

_PLAN_DRIVERS = {
    "base": {
        "FY27": dict(enrolled=3950, util=0.880, hours=166, bill=2125, wage=1465,
                     welfare=0.14, hires=1220, cpa=255, attrition=0.22),
        "FY28": dict(enrolled=4060, util=0.880, hours=166, bill=2146, wage=1480,
                     welfare=0.14, hires=1240, cpa=260, attrition=0.215),
        "FY29": dict(enrolled=4165, util=0.880, hours=166, bill=2167, wage=1495,
                     welfare=0.14, hires=1255, cpa=264, attrition=0.21),
        "FY30": dict(enrolled=4270, util=0.880, hours=166, bill=2189, wage=1510,
                     welfare=0.14, hires=1270, cpa=268, attrition=0.21),
        "FY31": dict(enrolled=4375, util=0.880, hours=166, bill=2211, wage=1525,
                     welfare=0.14, hires=1285, cpa=272, attrition=0.205),
    },
    "sponsor": {
        "FY27": dict(enrolled=4000, util=0.885, hours=166, bill=2140, wage=1465,
                     welfare=0.14, hires=1260, cpa=252, attrition=0.22),
        "FY28": dict(enrolled=4180, util=0.890, hours=166, bill=2180, wage=1482,
                     welfare=0.14, hires=1300, cpa=254, attrition=0.21),
        "FY29": dict(enrolled=4350, util=0.895, hours=167, bill=2222, wage=1500,
                     welfare=0.14, hires=1340, cpa=256, attrition=0.20),
        "FY30": dict(enrolled=4520, util=0.900, hours=167, bill=2264, wage=1518,
                     welfare=0.14, hires=1375, cpa=258, attrition=0.195),
        "FY31": dict(enrolled=4690, util=0.900, hours=167, bill=2308, wage=1536,
                     welfare=0.14, hires=1410, cpa=260, attrition=0.19),
    },
}


def drivers(case: str) -> dict:
    """ケース別の全年度ドライバー（実績3年は両ケース共通）。activeを計算して付与。"""
    d = {}
    for y in ACTUAL_YEARS:
        d[y] = dict(_ACTUAL_DRIVERS[y])
    for y in PLAN_YEARS:
        d[y] = dict(_PLAN_DRIVERS[case][y])
    for y, row in d.items():
        row["active"] = int(excel_round(row["enrolled"] * row["util"]))
    return d


# ---------------------------------------------------------------- ハードコード行（千円）
# PLの非ドライバー行。実績年は両ケース共通、計画年はケース別。
# FY27ベースの other_sga はEBITDA=1,750,000千円ぴったりに合わせるためのプラグ値。

_HARD_ACTUAL = {
    "FY24": dict(other_revenue=145_232, other_cogs=282_000, hq_cost=585_000,
                 other_sga=398_000, depreciation=92_000, interest=14_000, non_op=4_800),
    "FY25": dict(other_revenue=158_000, other_cogs=290_000, hq_cost=600_000,
                 other_sga=405_000, depreciation=98_000, interest=13_000, non_op=5_200),
    "FY26": dict(other_revenue=171_379, other_cogs=300_000, hq_cost=620_000,
                 other_sga=419_000, depreciation=105_043, interest=12_000, non_op=5_500),
}

_HARD_PLAN = {
    "base": {
        "FY27": dict(other_revenue=176_092, other_cogs=310_000, hq_cost=640_000,
                     other_sga=428_507, depreciation=113_700, non_op=6_000),
        "FY28": dict(other_revenue=180_000, other_cogs=318_000, hq_cost=652_000,
                     other_sga=433_000, depreciation=115_700, non_op=6_000),
        "FY29": dict(other_revenue=184_000, other_cogs=326_000, hq_cost=664_000,
                     other_sga=437_500, depreciation=117_700, non_op=6_000),
        "FY30": dict(other_revenue=188_000, other_cogs=334_000, hq_cost=676_000,
                     other_sga=442_000, depreciation=119_700, non_op=6_000),
        "FY31": dict(other_revenue=192_000, other_cogs=342_000, hq_cost=688_000,
                     other_sga=446_500, depreciation=121_700, non_op=6_000),
    },
    "sponsor": {
        "FY27": dict(other_revenue=176_092, other_cogs=310_000, hq_cost=645_000,
                     other_sga=432_000, depreciation=113_700, non_op=6_000),
        "FY28": dict(other_revenue=182_000, other_cogs=322_000, hq_cost=658_000,
                     other_sga=436_000, depreciation=117_700, non_op=6_000),
        "FY29": dict(other_revenue=188_000, other_cogs=334_000, hq_cost=672_000,
                     other_sga=440_000, depreciation=121_700, non_op=6_000),
        "FY30": dict(other_revenue=194_000, other_cogs=346_000, hq_cost=686_000,
                     other_sga=444_000, depreciation=125_700, non_op=6_000),
        "FY31": dict(other_revenue=200_000, other_cogs=358_000, hq_cost=700_000,
                     other_sga=448_000, depreciation=129_700, non_op=6_000),
    },
}

TAX_RATE = 0.31

# ---------------------------------------------------------------- デットスケジュール（千円）

SENIOR_TOTAL = 6_500_000          # シニアローン 6,500百万円
ANNUAL_REPAYMENT = 650_000        # 約定弁済（年）。最終回は残額一括（モデル期間外）
INTEREST_RATE = 0.022             # TIBOR + 200bp 想定


def debt_schedule() -> dict:
    """FY27〜FY31のシニアローン残高・支払利息（千円）。"""
    sched = {}
    opening = SENIOR_TOTAL
    for y in PLAN_YEARS:
        closing = opening - ANNUAL_REPAYMENT
        avg = (opening + closing) / 2
        sched[y] = dict(
            opening=opening,
            repayment=ANNUAL_REPAYMENT,
            closing=closing,
            interest=int(excel_round(avg * INTEREST_RATE)),
        )
        opening = closing
    return sched


# 実績年の既存借入（BS用・千円）
EXISTING_DEBT = {"FY24": 400_000, "FY25": 350_000, "FY26": 300_000}

# ---------------------------------------------------------------- PL計算（千円）


def compute_pl(case: str) -> dict:
    """ケース別PL。Excelに書き込む数式とまったく同じロジック（ROUND位置も揃える）。"""
    drv = drivers(case)
    sched = debt_schedule()
    pl = {}
    for y in YEARS:
        d = drv[y]
        hard = _HARD_ACTUAL[y] if y in ACTUAL_YEARS else _HARD_PLAN[case][y]
        staffing_rev = int(excel_round(d["active"] * d["hours"] * d["bill"] * 12 / 1000))
        revenue = staffing_rev + hard["other_revenue"]
        labor = int(excel_round(
            d["active"] * d["hours"] * d["wage"] * (1 + d["welfare"]) * 12 / 1000))
        cogs = labor + hard["other_cogs"]
        gross = revenue - cogs
        recruiting = d["hires"] * d["cpa"]  # 名 × 千円/名 = 千円
        sga = recruiting + hard["hq_cost"] + hard["other_sga"]
        op = gross - sga
        ebitda = op + hard["depreciation"]
        interest = hard["interest"] if y in ACTUAL_YEARS else sched[y]["interest"]
        ordinary = op - interest + hard["non_op"]
        tax = int(excel_round(ordinary * TAX_RATE))
        ni = ordinary - tax
        pl[y] = dict(
            staffing_rev=staffing_rev, other_revenue=hard["other_revenue"], revenue=revenue,
            labor=labor, other_cogs=hard["other_cogs"], cogs=cogs,
            gross=gross, gross_margin=gross / revenue,
            recruiting=recruiting, hq_cost=hard["hq_cost"], other_sga=hard["other_sga"],
            sga=sga, op=op, op_margin=op / revenue,
            depreciation=hard["depreciation"], ebitda=ebitda, ebitda_margin=ebitda / revenue,
            interest=interest, non_op=hard["non_op"], ordinary=ordinary, tax=tax, ni=ni,
        )
    return pl


# ---------------------------------------------------------------- BS / CF（千円）

GOODWILL = 5_500_000            # モデル上ののれん想定額（買収時）
GOODWILL_DD = 5_280_000         # 財務DDレポート記載ののれん想定額（意図的不整合）
POST_CLOSE_CASH = 1_100_000     # FY27期首現金（買収時調整後：取引費用等控除）

_BS_ACTUAL = {
    # 現預金 / 売上債権 / その他流動 / 有形固定 / 無形その他 / 仕入債務等 / 純資産
    "FY24": dict(cash=1_420_000, ar=1_540_000, oca=180_000, ppe=820_000, intangible=260_000,
                 ap=1_080_000, net_assets=1_950_000),
    "FY25": dict(cash=1_640_000, ar=1_650_000, oca=190_000, ppe=840_000, intangible=270_000,
                 ap=1_130_000, net_assets=2_560_000),
    "FY26": dict(cash=1_850_000, ar=1_750_000, oca=200_000, ppe=860_000, intangible=280_000,
                 ap=1_180_000, net_assets=3_150_000),
}

_CF_ACTUAL = {
    # 営業CF / 投資CF / 財務CF（配当・返済等）
    "FY24": dict(op_cf=1_150_000, inv_cf=-100_000, fin_cf=-930_000),
    "FY25": dict(op_cf=1_290_000, inv_cf=-110_000, fin_cf=-960_000),
    "FY26": dict(op_cf=1_420_000, inv_cf=-115_000, fin_cf=-1_095_000),
}

_PLAN_AP = {
    "base": {"FY27": 1_240_000, "FY28": 1_265_000, "FY29": 1_290_000,
             "FY30": 1_315_000, "FY31": 1_340_000},
    "sponsor": {"FY27": 1_270_000, "FY28": 1_320_000, "FY29": 1_375_000,
                "FY30": 1_430_000, "FY31": 1_485_000},
}
_PLAN_CAPEX = {"base": 120_000, "sponsor": 140_000}
_PLAN_OTHER_LIAB = 320_000  # 計画期間のその他負債（固定）
_PLAN_INTANGIBLE = 290_000
AR_DAYS = 45  # 売上債権回転日数


def compute_bs_cf(case: str) -> tuple[dict, dict]:
    """計画BS・CF。CFの積み上げで現金を決め、BSは恒等式で自動的にバランスする。"""
    pl = compute_pl(case)
    sched = debt_schedule()
    bs = {y: dict(_BS_ACTUAL[y]) for y in ACTUAL_YEARS}
    cf = {}
    for y in ACTUAL_YEARS:
        c = dict(_CF_ACTUAL[y])
        c["fcf"] = c["op_cf"] + c["inv_cf"]
        c["net_change"] = c["op_cf"] + c["inv_cf"] + c["fin_cf"]
        cf[y] = c
    # 実績年のBS付随項目
    for y in ACTUAL_YEARS:
        b = bs[y]
        b["goodwill"] = 0
        b["debt"] = EXISTING_DEBT[y]
        b["total_assets"] = b["cash"] + b["ar"] + b["oca"] + b["ppe"] + b["intangible"]
        b["other_liab"] = b["total_assets"] - b["ap"] - b["debt"] - b["net_assets"]
        assert b["other_liab"] > 0, f"BS実績 {y}: その他負債が負"

    prev_bs = None
    prev_cash = POST_CLOSE_CASH
    prev_na = DEAL["equity_mm"] * 1000  # エクイティ出資 5,500,000千円
    for y in PLAN_YEARS:
        p = pl[y]
        b = dict(
            ar=int(excel_round(p["revenue"] * AR_DAYS / 365 / 1000) * 1000),
            oca=210_000 + 5_000 * PLAN_YEARS.index(y),
            goodwill=GOODWILL,
            intangible=_PLAN_INTANGIBLE,
            ap=_PLAN_AP[case][y],
            debt=sched[y]["closing"],
            other_liab=_PLAN_OTHER_LIAB,
        )
        if prev_bs is None:
            b["ppe"] = _BS_ACTUAL["FY26"]["ppe"] + _PLAN_CAPEX[case] - p["depreciation"]
            d_ar = b["ar"] - _BS_ACTUAL["FY26"]["ar"]
            d_oca = b["oca"] - _BS_ACTUAL["FY26"]["oca"]
            d_ap = b["ap"] - _BS_ACTUAL["FY26"]["ap"]
            d_ol = b["other_liab"] - bs["FY26"]["other_liab"]
        else:
            b["ppe"] = prev_bs["ppe"] + _PLAN_CAPEX[case] - p["depreciation"]
            d_ar = b["ar"] - prev_bs["ar"]
            d_oca = b["oca"] - prev_bs["oca"]
            d_ap = b["ap"] - prev_bs["ap"]
            d_ol = b["other_liab"] - prev_bs["other_liab"]
        wc_change = d_ar + d_oca - d_ap
        op_cf = p["ni"] + p["depreciation"] - wc_change
        inv_cf = -_PLAN_CAPEX[case]
        fin_cf = -sched[y]["repayment"] + d_ol
        net_change = op_cf + inv_cf + fin_cf
        b["cash"] = prev_cash + net_change
        b["net_assets"] = prev_na + p["ni"]
        b["total_assets"] = (b["cash"] + b["ar"] + b["oca"] + b["ppe"]
                             + b["goodwill"] + b["intangible"])
        balance = b["total_assets"] - (b["ap"] + b["debt"] + b["other_liab"] + b["net_assets"])
        # 買収時調整（FY27期首の現金減・取引費用）ぶんは純資産側の調整に含める
        if y == "FY27":
            adj = _BS_ACTUAL["FY26"]["cash"] - POST_CLOSE_CASH  # 750,000
            # のれん計上と旧純資産消去のネット差額もここで吸収する（簡略化モデルの明示的調整）
            b["purchase_adj"] = balance
            b["net_assets"] += balance
            _ = adj
        else:
            b["net_assets"] += prev_purchase_adj
            b["purchase_adj"] = prev_purchase_adj
        # 再計算
        balance2 = b["total_assets"] - (b["ap"] + b["debt"] + b["other_liab"] + b["net_assets"])
        assert abs(balance2) < 1, f"BS計画 {case} {y}: バランス不一致 {balance2}"
        cf[y] = dict(op_cf=op_cf, inv_cf=inv_cf, fcf=op_cf + inv_cf,
                     fin_cf=fin_cf, net_change=net_change,
                     opening_cash=prev_cash, closing_cash=b["cash"])
        prev_purchase_adj = b["purchase_adj"]
        prev_bs = b
        prev_cash = b["cash"]
        prev_na = prev_na + p["ni"]
        bs[y] = b
    return bs, cf


# ---------------------------------------------------------------- DDレポート キーファクト

DD_FILES = {
    "business": "DD_Business_オートスタッフ中部.pdf",
    "financial": "DD_Financial_オートスタッフ中部.pdf",
    "legal": "DD_Legal_オートスタッフ中部.pdf",
    "tax": "DD_Tax_オートスタッフ中部.pdf",
}

MODEL_FILES = {
    "sponsor": "AutostaffChubu_Model_Sponsor.xlsx",
    "base": "AutostaffChubu_Model_Base.xlsx",
}

# ページ番号は「PDFの通しページ（表紙=1ページ目）」。
# check はそのページに一字一句存在すべき照合フレーズ（validate.pyが検証）。
DD_KEY_FACTS = [
    dict(id="customer_concentration", file="business", page=18,
         text="上位3社への売上依存度は62%（うち最大手A社28%）",
         check=["上位3社への売上依存度は62%（うち最大手A社28%）"],
         value="62%（最大手28%）"),
    dict(id="normalized_ebitda", file="financial", page=34,
         text="正常収益力ベースのEBITDAは1,620百万円（16.2億円）",
         check=["正常収益力ベースのEBITDAは1,620百万円（16.2億円）"],
         value="1,620百万円"),
    dict(id="goodwill_dd", file="financial", page=31,
         text="のれん想定額は5,280百万円（スポンサーモデルは5,500百万円・220百万円の差異）",
         check=["のれん想定額は5,280百万円", "5,500百万円が計上されており", "220百万円の差異"],
         value="5,280百万円"),
    dict(id="overtime_liability", file="legal", page=12,
         text="未払残業代に係る潜在債務は最大300百万円（3億円）",
         check=["未払残業代", "最大300百万円（3億円）"],
         value="最大300百万円"),
    dict(id="haken_license", file="legal", page=5,
         text="労働者派遣事業許可（派23-301456）は2028年3月まで有効",
         check=["派23-301456", "2028年3月まで"],
         value="派23-301456"),
    dict(id="nol", file="tax", page=6,
         text="繰越欠損金は存在しない（直近10年間、課税所得を計上）",
         check=["繰越欠損金は存在しない"],
         value="なし"),
]

# ---------------------------------------------------------------- 検証用サマリー


def summary_check():
    """正本数値の主要ピンが成立していることを確認する（validate.pyから呼ぶ）。"""
    pl_base = compute_pl("base")
    assert to_mm(pl_base["FY26"]["revenue"]) == 14160, to_mm(pl_base["FY26"]["revenue"])
    assert to_mm(pl_base["FY26"]["ebitda"]) == 1620, to_mm(pl_base["FY26"]["ebitda"])
    assert to_mm(pl_base["FY27"]["revenue"]) == 14890, to_mm(pl_base["FY27"]["revenue"])
    assert to_mm(pl_base["FY27"]["ebitda"]) == 1750, to_mm(pl_base["FY27"]["ebitda"])
    d = drivers("base")["FY26"]
    assert d["active"] == 3344 and d["util"] == 0.88 and d["bill"] == 2100 and d["cpa"] == 250
    assert DEAL["initial_leverage"] == 4.1 and DEAL["ltv_pct"] == 54
    for case in CASES:
        compute_bs_cf(case)  # バランスチェック（assert内蔵）
    return True


if __name__ == "__main__":
    summary_check()
    pl = compute_pl("base")
    print("=== Base case PL（百万円） ===")
    for y in YEARS:
        p = pl[y]
        print(f"{y}: 売上 {to_mm(p['revenue']):,} / 営業利益 {to_mm(p['op']):,} "
              f"/ EBITDA {to_mm(p['ebitda']):,} / 純利益 {to_mm(p['ni']):,}")
    pl_s = compute_pl("sponsor")
    print("=== Sponsor case PL（百万円） ===")
    for y in PLAN_YEARS:
        p = pl_s[y]
        print(f"{y}: 売上 {to_mm(p['revenue']):,} / EBITDA {to_mm(p['ebitda']):,}")
    for case in CASES:
        bs, cf = compute_bs_cf(case)
        print(f"=== {case} 現預金推移（百万円） ===")
        print({y: to_mm(bs[y]["cash"]) for y in YEARS})
    print("summary_check OK")
