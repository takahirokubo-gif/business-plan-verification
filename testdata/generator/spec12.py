# -*- coding: utf-8 -*-
"""テストデータA/B（12期拡張版）の数値正本（Single Source of Truth）。

dummy_input/spec.py（8期版の正本）を取り込み、以下を追加定義する：
- FY22〜FY23 実績（新規作成・両ケース共通）
- FY32〜FY33 計画（Base / Sponsor 各ケースで外挿）
- 月次試算表_FY26 の月次按分（単位：円・1,000円グリッド）

制約（claude_code_prompt v2 第4章）：
- 既存FY24〜FY31の数値は dummy_input/spec.py と完全一致（self_check()で保証）
- FY22〜23は全期黒字・売上CAGR(FY22→26)が5〜8%・貸借一致
- FY32〜33は稼働率88%維持(Base)・派遣単価改定+1%/年前後・FY33残額一括弁済
- 月次は12ヶ月合計が年次FY26と一致（±1千円）・5/8/1月が他9ヶ月平均比△5〜8%
"""
import sys
from pathlib import Path

_DUMMY_INPUT = Path(__file__).resolve().parents[2] / "dummy_input"
sys.path.insert(0, str(_DUMMY_INPUT))
import spec as spec8  # noqa: E402  dummy_input/spec.py（8期版正本）

excel_round = spec8.excel_round

# ---------------------------------------------------------------- 期間定義
YEARS = ["FY22", "FY23", "FY24", "FY25", "FY26",
         "FY27", "FY28", "FY29", "FY30", "FY31", "FY32", "FY33"]
ACTUAL_YEARS = YEARS[:5]     # FY22〜FY26（実績5期）
PLAN_YEARS = YEARS[5:]       # FY27〜FY33（計画7期）
COL = {y: chr(ord("C") + i) for i, y in enumerate(YEARS)}   # C〜N

CASES = spec8.CASES
CASE_LABEL = spec8.CASE_LABEL
CASE_LABEL_JA = spec8.CASE_LABEL_JA
DEAL = spec8.DEAL
TAX_RATE = spec8.TAX_RATE
GOODWILL = spec8.GOODWILL
GOODWILL_DD = spec8.GOODWILL_DD
POST_CLOSE_CASH = spec8.POST_CLOSE_CASH
SENIOR_TOTAL = spec8.SENIOR_TOTAL
ANNUAL_REPAYMENT = spec8.ANNUAL_REPAYMENT
INTEREST_RATE = spec8.INTEREST_RATE
AR_DAYS = spec8.AR_DAYS

# ---------------------------------------------------------------- KPIドライバー
# FY22〜23実績（新規）。FY24〜26は spec8 と同一値。
_ACTUAL_DRIVERS = {
    "FY22": dict(enrolled=3350, util=0.850, hours=164, bill=1950, wage=1350,
                 welfare=0.14, hires=920, cpa=205, attrition=0.250),
    "FY23": dict(enrolled=3460, util=0.858, hours=165, bill=1985, wage=1375,
                 welfare=0.14, hires=980, cpa=215, attrition=0.245),
    **spec8._ACTUAL_DRIVERS,
}

# FY32〜33計画（新規外挿）。FY27〜31は spec8 と同一値。
_PLAN_DRIVERS = {
    "base": {
        **spec8._PLAN_DRIVERS["base"],
        # 稼働率88%維持・単価改定+1.0%/年前後（2211→2233→2255）
        "FY32": dict(enrolled=4480, util=0.880, hours=166, bill=2233, wage=1540,
                     welfare=0.14, hires=1300, cpa=276, attrition=0.205),
        "FY33": dict(enrolled=4585, util=0.880, hours=166, bill=2255, wage=1555,
                     welfare=0.14, hires=1315, cpa=280, attrition=0.200),
    },
    "sponsor": {
        **spec8._PLAN_DRIVERS["sponsor"],
        # Sponsor前提（稼働率0.90上限・単価+2%/年）で外挿
        "FY32": dict(enrolled=4860, util=0.900, hours=167, bill=2354, wage=1554,
                     welfare=0.14, hires=1445, cpa=262, attrition=0.185),
        "FY33": dict(enrolled=5030, util=0.900, hours=167, bill=2401, wage=1572,
                     welfare=0.14, hires=1480, cpa=264, attrition=0.180),
    },
}


def drivers(case: str) -> dict:
    d = {}
    for y in ACTUAL_YEARS:
        d[y] = dict(_ACTUAL_DRIVERS[y])
    for y in PLAN_YEARS:
        d[y] = dict(_PLAN_DRIVERS[case][y])
    for row in d.values():
        row["active"] = int(excel_round(row["enrolled"] * row["util"]))
    return d


# ---------------------------------------------------------------- ハードコード行（千円）
_HARD_ACTUAL = {
    "FY22": dict(other_revenue=130_000, other_cogs=265_000, hq_cost=555_000,
                 other_sga=385_000, depreciation=84_000, interest=16_000, non_op=4_200),
    "FY23": dict(other_revenue=138_000, other_cogs=272_000, hq_cost=570_000,
                 other_sga=391_000, depreciation=88_000, interest=15_000, non_op=4_500),
    **spec8._HARD_ACTUAL,
}

_HARD_PLAN = {
    "base": {
        **spec8._HARD_PLAN["base"],
        "FY32": dict(other_revenue=196_000, other_cogs=350_000, hq_cost=700_000,
                     other_sga=451_000, depreciation=123_700, non_op=6_000),
        "FY33": dict(other_revenue=200_000, other_cogs=358_000, hq_cost=712_000,
                     other_sga=455_500, depreciation=125_700, non_op=6_000),
    },
    "sponsor": {
        **spec8._HARD_PLAN["sponsor"],
        "FY32": dict(other_revenue=206_000, other_cogs=370_000, hq_cost=714_000,
                     other_sga=452_000, depreciation=133_700, non_op=6_000),
        "FY33": dict(other_revenue=212_000, other_cogs=382_000, hq_cost=728_000,
                     other_sga=456_000, depreciation=137_700, non_op=6_000),
    },
}

# ---------------------------------------------------------------- デットスケジュール
# FY27〜FY32：約定弁済650,000千円/年、FY33：残額一括弁済（2,600,000千円）


def debt_schedule() -> dict:
    sched = {}
    opening = SENIOR_TOTAL
    for y in PLAN_YEARS:
        repayment = ANNUAL_REPAYMENT if y != "FY33" else opening  # 最終回残額一括
        closing = opening - repayment
        avg = (opening + closing) / 2
        sched[y] = dict(opening=opening, repayment=repayment, closing=closing,
                        interest=int(excel_round(avg * INTEREST_RATE)))
        opening = closing
    assert sched["FY33"]["closing"] == 0
    return sched


EXISTING_DEBT = {"FY22": 500_000, "FY23": 450_000, **spec8.EXISTING_DEBT}

# CFシートの期首現金ハードコード（FY22＝モデル起点、FY27＝買収時調整後）
OPENING_CASH_FY22 = 1_020_000

# ---------------------------------------------------------------- PL計算（千円）


def compute_pl(case: str) -> dict:
    """Excelに書く数式と同一ロジック（ROUND位置も一致）。"""
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
        recruiting = d["hires"] * d["cpa"]
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
# 実績5期：BSは現預金〜純資産を明示し、その他負債をプラグとして算出（spec8と同方式）
_BS_ACTUAL = {
    "FY22": dict(cash=1_150_000, ar=1_365_000, oca=160_000, ppe=780_000, intangible=240_000,
                 ap=980_000, net_assets=945_000),
    "FY23": dict(cash=1_300_000, ar=1_455_000, oca=170_000, ppe=800_000, intangible=250_000,
                 ap=1_030_000, net_assets=1_465_000),
    **spec8._BS_ACTUAL,
}

_CF_ACTUAL = {
    "FY22": dict(op_cf=980_000, inv_cf=-90_000, fin_cf=-760_000),
    "FY23": dict(op_cf=1_065_000, inv_cf=-95_000, fin_cf=-820_000),
    **spec8._CF_ACTUAL,
}

_PLAN_AP = {
    "base": {**spec8._PLAN_AP["base"], "FY32": 1_365_000, "FY33": 1_390_000},
    "sponsor": {**spec8._PLAN_AP["sponsor"], "FY32": 1_540_000, "FY33": 1_595_000},
}
_PLAN_CAPEX = spec8._PLAN_CAPEX
_PLAN_OTHER_LIAB = spec8._PLAN_OTHER_LIAB
_PLAN_INTANGIBLE = spec8._PLAN_INTANGIBLE


def compute_bs_cf(case: str) -> tuple[dict, dict]:
    """計画BS・CF（spec8のロジックを7年に拡張）。CF積み上げで現金を決めBSは恒等式で一致。"""
    pl = compute_pl(case)
    sched = debt_schedule()
    bs = {y: dict(_BS_ACTUAL[y]) for y in ACTUAL_YEARS}
    cf = {}
    prev_cash_actual = {"FY22": OPENING_CASH_FY22}
    for i, y in enumerate(ACTUAL_YEARS):
        c = dict(_CF_ACTUAL[y])
        c["fcf"] = c["op_cf"] + c["inv_cf"]
        c["net_change"] = c["op_cf"] + c["inv_cf"] + c["fin_cf"]
        opening = prev_cash_actual[y] if y in prev_cash_actual else _BS_ACTUAL[ACTUAL_YEARS[i - 1]]["cash"]
        c["opening_cash"] = opening
        c["closing_cash"] = opening + c["net_change"]
        assert c["closing_cash"] == _BS_ACTUAL[y]["cash"], f"CF実績 {y}: 期末現金不一致 {c['closing_cash']}"
        cf[y] = c
    for y in ACTUAL_YEARS:
        b = bs[y]
        b["goodwill"] = 0
        b["debt"] = EXISTING_DEBT[y]
        b["total_assets"] = b["cash"] + b["ar"] + b["oca"] + b["ppe"] + b["intangible"]
        b["other_liab"] = b["total_assets"] - b["ap"] - b["debt"] - b["net_assets"]
        assert b["other_liab"] > 0, f"BS実績 {y}: その他負債が負"

    prev_bs = None
    prev_cash = POST_CLOSE_CASH
    prev_na = DEAL["equity_mm"] * 1000
    prev_purchase_adj = None
    for idx, y in enumerate(PLAN_YEARS):
        p = pl[y]
        b = dict(
            ar=int(excel_round(p["revenue"] * AR_DAYS / 365 / 1000) * 1000),
            oca=210_000 + 5_000 * idx,
            goodwill=GOODWILL,
            intangible=_PLAN_INTANGIBLE,
            ap=_PLAN_AP[case][y],
            debt=sched[y]["closing"],
            other_liab=_PLAN_OTHER_LIAB,
        )
        ref = _BS_ACTUAL["FY26"] if prev_bs is None else prev_bs
        b["ppe"] = ref["ppe"] + _PLAN_CAPEX[case] - p["depreciation"]
        d_ar = b["ar"] - ref["ar"]
        d_oca = b["oca"] - ref["oca"]
        d_ap = b["ap"] - ref["ap"]
        ref_ol = bs["FY26"]["other_liab"] if prev_bs is None else prev_bs["other_liab"]
        d_ol = b["other_liab"] - ref_ol
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
        if y == "FY27":
            b["purchase_adj"] = balance
            b["net_assets"] += balance
        else:
            b["net_assets"] += prev_purchase_adj
            b["purchase_adj"] = prev_purchase_adj
        balance2 = b["total_assets"] - (b["ap"] + b["debt"] + b["other_liab"] + b["net_assets"])
        assert abs(balance2) < 1, f"BS計画 {case} {y}: バランス不一致 {balance2}"
        assert b["cash"] > 0, f"BS計画 {case} {y}: 現金がマイナス {b['cash']}"
        cf[y] = dict(op_cf=op_cf, inv_cf=inv_cf, fcf=op_cf + inv_cf,
                     fin_cf=fin_cf, net_change=net_change,
                     opening_cash=prev_cash, closing_cash=b["cash"])
        prev_purchase_adj = b["purchase_adj"]
        prev_bs = b
        prev_cash = b["cash"]
        prev_na = prev_na + p["ni"]
        bs[y] = b
    return bs, cf


# ---------------------------------------------------------------- 月次試算表_FY26
# 単位：円。全値1,000円グリッド（千円換算が丸めなしで成立し、A統合DDとの完全一致を保つ）。
MONTHS = ["2025/04", "2025/05", "2025/06", "2025/07", "2025/08", "2025/09",
          "2025/10", "2025/11", "2025/12", "2026/01", "2026/02", "2026/03"]
LOW_MONTHS = {"2025/05": 0.060, "2025/08": 0.065, "2026/01": 0.070}  # 対他9ヶ月平均の低下率

# 通常9ヶ月の微小ジッター（合計ゼロ・平均を動かさない）
_JITTER = {"2025/04": +0.004, "2025/06": -0.003, "2025/07": +0.002, "2025/09": -0.004,
           "2025/10": +0.005, "2025/11": -0.002, "2025/12": +0.003,
           "2026/02": -0.005, "2026/03": 0.000}
assert abs(sum(_JITTER.values())) < 1e-12

# 販管費の月次ウェイト（採用費の4月・10月ピークを反映、合計12.0）
_SGA_W = {"2025/04": 1.060, "2025/05": 0.980, "2025/06": 0.990, "2025/07": 1.000,
          "2025/08": 0.970, "2025/09": 0.995, "2025/10": 1.050, "2025/11": 0.995,
          "2025/12": 1.005, "2026/01": 0.975, "2026/02": 0.985, "2026/03": 0.995}
assert abs(sum(_SGA_W.values()) - 12.0) < 1e-9


def _alloc_grid(total_yen: int, weights: dict) -> dict:
    """月次配分。1,000円グリッドに丸め、端数は3月に寄せて合計を厳密一致させる。"""
    total_w = sum(weights.values())
    out = {}
    acc = 0
    for m in MONTHS[:-1]:
        v = int(excel_round(total_yen * weights[m] / total_w / 1000)) * 1000
        out[m] = v
        acc += v
    out[MONTHS[-1]] = total_yen - acc
    assert out[MONTHS[-1]] % 1000 == 0
    return out


def _rev_weights() -> dict:
    w = {}
    for m in MONTHS:
        if m in LOW_MONTHS:
            w[m] = 1.0 - LOW_MONTHS[m]
        else:
            w[m] = 1.0 + _JITTER[m]
    return w


def compute_monthly() -> dict:
    """月次試算表_FY26（単位：円）。keys: revenue/cogs/gross/sga/op/cash/ar/ap → {month: yen}"""
    pl = compute_pl("base")["FY26"]
    bs26 = _BS_ACTUAL["FY26"]
    bs25 = _BS_ACTUAL["FY25"]
    rev_y = pl["revenue"] * 1000
    cogs_y = pl["cogs"] * 1000
    sga_y = pl["sga"] * 1000

    w = _rev_weights()
    revenue = _alloc_grid(rev_y, w)
    cogs = _alloc_grid(cogs_y, w)          # 労務費は稼働連動＝売上と同ウェイト
    sga = _alloc_grid(sga_y, _SGA_W)
    gross = {m: revenue[m] - cogs[m] for m in MONTHS}
    op = {m: gross[m] - sga[m] for m in MONTHS}

    # B/S残高（円・1,000円グリッド）。3月末は年次BSのFY26と厳密一致。
    ar = {}
    for m in MONTHS[:-1]:
        ar[m] = int(excel_round(revenue[m] * 1.48 / 1000)) * 1000
    ar[MONTHS[-1]] = bs26["ar"] * 1000

    cash, ap = {}, {}
    cash_start, cash_end = bs25["cash"] * 1000, bs26["cash"] * 1000
    ap_start, ap_end = bs25["ap"] * 1000, bs26["ap"] * 1000
    _wobble = [+12, -8, +20, -15, +6, -18, +14, -5, +9, -12, +7, 0]  # 千円単位の揺らぎ×1000円
    for i, m in enumerate(MONTHS):
        t = (i + 1) / 12
        cash[m] = int(excel_round((cash_start + (cash_end - cash_start) * t) / 1000)) * 1000 \
            + _wobble[i] * 1000 * 100
        ap[m] = int(excel_round((ap_start + (ap_end - ap_start) * t) / 1000)) * 1000 \
            - _wobble[i] * 1000 * 40
    cash[MONTHS[-1]] = cash_end
    ap[MONTHS[-1]] = ap_end

    return dict(revenue=revenue, cogs=cogs, gross=gross, sga=sga, op=op,
                cash=cash, ar=ar, ap=ap)


def monthly_seasonality(revenue: dict) -> dict:
    """低調月ごとの「他9ヶ月平均に対する低下率」を返す（検証用）。"""
    normal = [revenue[m] for m in MONTHS if m not in LOW_MONTHS]
    avg = sum(normal) / len(normal)
    return {m: 1.0 - revenue[m] / avg for m in LOW_MONTHS}


# ---------------------------------------------------------------- 自己検証


def self_check() -> bool:
    # 1) FY24〜31が8期版spec.pyと完全一致（PL・BS・CF・デット）
    for case in CASES:
        pl12, pl8 = compute_pl(case), spec8.compute_pl(case)
        bs12, cf12 = compute_bs_cf(case)
        bs8, cf8 = spec8.compute_bs_cf(case)
        for y in spec8.YEARS:
            for k, v in pl8[y].items():
                assert pl12[y][k] == v, f"PL不一致 {case} {y} {k}: {pl12[y][k]} != {v}"
            for k, v in bs8[y].items():
                assert bs12[y][k] == v, f"BS不一致 {case} {y} {k}"
            for k in ("op_cf", "inv_cf", "fcf", "fin_cf", "net_change"):
                assert cf12[y][k] == cf8[y][k], f"CF不一致 {case} {y} {k}"
        sched12, sched8 = debt_schedule(), spec8.debt_schedule()
        for y in spec8.PLAN_YEARS:
            assert sched12[y] == sched8[y], f"Debt不一致 {y}"

    pl = compute_pl("base")
    # 2) FY22〜23 全期黒字（経常・純利益とも）
    for y in ("FY22", "FY23"):
        assert pl[y]["ordinary"] > 0 and pl[y]["ni"] > 0, f"{y} が赤字"
    # 3) 売上CAGR（FY22→FY26）が5〜8%
    cagr = (pl["FY26"]["revenue"] / pl["FY22"]["revenue"]) ** 0.25 - 1
    assert 0.05 <= cagr <= 0.08, f"CAGR範囲外: {cagr:.4f}"
    # 4) 滑らかな接続（各年成長率4〜9%）
    for i in range(1, 5):
        g = pl[YEARS[i]]["revenue"] / pl[YEARS[i - 1]]["revenue"] - 1
        assert 0.04 <= g <= 0.09, f"{YEARS[i]} 成長率が不連続: {g:.4f}"
    # 5) FY32〜33（Base）：稼働率88%・単価+1%/年前後・FY33一括弁済
    d = drivers("base")
    assert d["FY32"]["util"] == 0.88 and d["FY33"]["util"] == 0.88
    for prev, cur in (("FY31", "FY32"), ("FY32", "FY33")):
        r = d[cur]["bill"] / d[prev]["bill"] - 1
        assert 0.005 <= r <= 0.015, f"単価改定率が+1%前後でない: {cur} {r:.4f}"
    sched = debt_schedule()
    assert sched["FY33"]["repayment"] == 2_600_000 and sched["FY33"]["closing"] == 0
    # 6) 月次：合計一致（グリッド上厳密）・季節性5〜8%・3月末B/S一致
    mon = compute_monthly()
    pl26 = pl["FY26"]
    assert sum(mon["revenue"].values()) == pl26["revenue"] * 1000
    assert sum(mon["cogs"].values()) == pl26["cogs"] * 1000
    assert sum(mon["sga"].values()) == pl26["sga"] * 1000
    assert sum(mon["op"].values()) == pl26["op"] * 1000
    for m, drop in monthly_seasonality(mon["revenue"]).items():
        assert 0.05 <= drop <= 0.08, f"季節性範囲外 {m}: {drop:.4f}"
    assert mon["cash"]["2026/03"] == _BS_ACTUAL["FY26"]["cash"] * 1000
    assert mon["ar"]["2026/03"] == _BS_ACTUAL["FY26"]["ar"] * 1000
    assert mon["ap"]["2026/03"] == _BS_ACTUAL["FY26"]["ap"] * 1000
    for v in [x for row in mon.values() for x in row.values()]:
        assert v % 1000 == 0, "1,000円グリッド違反"
    # 7) スポンサーFY32〜33も貸借一致・現金プラス（compute_bs_cf内のassertで担保）
    return True


if __name__ == "__main__":
    self_check()
    pl = compute_pl("base")
    print("=== Base PL（千円） ===")
    for y in YEARS:
        p = pl[y]
        print(f"{y}: 売上 {p['revenue']:>12,} / OP {p['op']:>11,} / EBITDA {p['ebitda']:>11,}"
              f" / NI {p['ni']:>11,}")
    cagr = (pl["FY26"]["revenue"] / pl["FY22"]["revenue"]) ** 0.25 - 1
    print(f"CAGR FY22->26: {cagr:.2%}")
    mon = compute_monthly()
    print("月次売上（千円換算）:", {m: v // 1000 for m, v in mon['revenue'].items()})
    print("季節性:", {m: f"{d:.2%}" for m, d in monthly_seasonality(mon['revenue']).items()})
    for case in CASES:
        bs, _ = compute_bs_cf(case)
        print(f"{case} FY33 cash: {bs['FY33']['cash']:,} / debt: {bs['FY33']['debt']:,}")
    print("self_check OK")
