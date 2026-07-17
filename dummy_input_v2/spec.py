"""ルミエールボーテLBO テストデータ（v2・実AI精度検証用）の正本（Single Source of Truth）。

目的:
  EXTRACTOR_MODE=anthropic（実生成AI）の動作・精度テスト用「理想的なインプット」。
  - 必要な情報がすべて資料内に揃っている
  - 実際に想定されるインプット（実在のLBOモデル・DD報告書サンプル）の様式に十分近い
  既存デモデータ（dummy_input/ オートスタッフ中部）とは独立。mockモードでは解析できない。

すべてのダミーインプット（財務モデルExcel・DDレポートPDF）、GROUND_TRUTH.md、
expected_output.json はこのファイルの定義から生成する。
数値を変更する場合は必ずここを変更し、generate_all.py → validate.py を実行すること。

単位規約:
  - Excel財務モデル内の金額はすべて百万円（実在LBOモデルテンプレートの慣行に合わせる。
    Coverシートに「単位：百万円」を明記）
  - DDレポートの財務数値表は千円（実在の財務DD報告書サンプルの慣行）。
    千円の値は ROUND(千円/1000)=百万円 が成立するよう生成し、丸め整合を保証する
  - UI・期待値の表示は百万円
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


YEARS = ["FY24", "FY25", "FY26", "FY27", "FY28", "FY29", "FY30", "FY31"]
ACTUAL_YEARS = ["FY24", "FY25", "FY26"]
PLAN_YEARS = ["FY27", "FY28", "FY29", "FY30", "FY31"]
# 表示用の年度ラベル（既存デモの「FY26」表記とあえて変える＝表記揺れテスト）
YEAR_LABEL = {y: f"20{y[2:]}/3期" for y in YEARS}  # FY26 -> 2026/3期
# 年度→Excel列（B=項目名、C以降が年度）
COL = {y: chr(ord("C") + i) for i, y in enumerate(YEARS)}

CASES = ["sponsor", "base"]
CASE_LABEL = {"sponsor": "Sponsor Case", "base": "Bank Base Case"}
CASE_LABEL_JA = {"sponsor": "スポンサーケース", "base": "ベースケース（銀行調整）"}

# ---------------------------------------------------------------- 案件基本情報

PROJECT_NAME = "Project Bloom"

DEAL = {
    "name": "ルミエールボーテ LBOファイナンス",
    "deal_type": "LBO",
    "borrower": "株式会社ブルームホールディングス",  # SPC
    "target": "株式会社ルミエールボーテ",
    "industry": "化粧品・スキンケアの企画販売（D2C・卸）",
    "sponsor": "大手町プリンシパルパートナーズ株式会社",
    "close_date": "2026-11-30",
    "ev_mm": 9000,             # EV 9,000百万円（FY26実績EBITDA 1,120の約8.0x）
    "equity_value_mm": 9220,   # 株式対価（EV + ネットキャッシュ220）
    "senior_mm": 4800,         # シニアタームローンA
    "our_commitment_mm": 2000,  # 本行取組額（行内情報：資料には书かない）
    "equity_mm": 4620,         # スポンサーエクイティ
    "tenor_years": 7,
    "sponsor_ebitda_mm": 1120,  # スポンサー提示EBITDA（FY26実績・速報値）
    "summary": (
        "大手町プリンシパルパートナーズによるスキンケアD2C・卸の中堅、ルミエールボーテのLBO。"
        "自社EC（定期会員22.8万人・リピート率76%）とドラッグストア卸の2チャネルを持ち、"
        "製造は全量OEM委託のファブレス経営。創業者（67歳・株式90%保有）の"
        "事業承継ニーズを背景としたスポンサー主導の買収案件。"
    ),
}
# 自動算出（四則演算のみ・再計算エンジンには該当しない）
DEAL["initial_leverage"] = round(DEAL["senior_mm"] / DEAL["sponsor_ebitda_mm"], 1)  # 4.3x
DEAL["ltv_pct"] = round(DEAL["senior_mm"] / DEAL["ev_mm"] * 100)  # 53%

# Sources & Uses（百万円）
SOURCES_USES = {
    "senior": 4800,
    "equity": 4620,
    "sources_total": 9420,
    "equity_value": 9220,      # 株式対価
    "refi": 400,               # 既存借入リファイナンス
    "fees": 180,               # 取引費用等
    "cash_used": 380,          # 対象会社手元現金の活用
    "uses_total": 9420,        # 9,220+400+180-380
}
assert (SOURCES_USES["senior"] + SOURCES_USES["equity"]
        == SOURCES_USES["equity_value"] + SOURCES_USES["refi"]
        + SOURCES_USES["fees"] - SOURCES_USES["cash_used"]
        == SOURCES_USES["sources_total"])

# のれん（百万円）
GOODWILL = 6100       # モデル記載（暫定PPA前）: 対価9,220 - 時価純資産2,655 - 識別無形465
GOODWILL_DD = 5950    # 財務DD報告書記載ののれん試算額（意図的不整合・150百万円差異）
FAIR_NET_ASSETS = 2655   # 財務DDの時価純資産（簿価2,850 - 在庫評価損120 - その他75）
IDENTIFIED_INTANGIBLE = 465  # 識別無形資産（商標・顧客関連）
INVENTORY_WRITEDOWN = 120    # 滞留在庫評価損（財務DD）
NORMALIZED_EBITDA = 1036     # 正常収益力EBITDA（FY26・財務DD結論）

# 正常収益力ブリッジ（財務DD p.33）: 報告EBITDA 1,120 → 1,036
QOE_BRIDGE = [
    ("役員報酬の適正化（過大分の加算）", 48),
    ("本社移転に伴う一時費用の加算", 22),
    ("ポイント引当金の過小計上（減算）", -58),
    ("返品調整引当の期間帰属修正（減算）", -36),
    ("EC配送料の翌期計上分の期間帰属修正（減算）", -60),
]
assert DEAL["sponsor_ebitda_mm"] + sum(v for _, v in QOE_BRIDGE) == NORMALIZED_EBITDA

# ---------------------------------------------------------------- KPIドライバー
# 行キー:
#   member(アクティブ会員数・人)  = ROUND(前期member×repeat + new)
#   repeat(リピート率)  new(新規獲得会員数・人)
#   freq(年間平均購入回数・回)  aov(平均注文単価・円)
#   doors(卸取扱店舗数・店)  perdoor(店舗あたり年間出荷額・千円)
#   cogs_rate(売上原価率)  ad_rate(広告宣伝費率・対売上)  log_rate(物流費率・対売上)

_ACTUAL_DRIVERS = {
    "FY24": dict(member=196_000, repeat=0.74, new=58_000, freq=2.45, aov=6_400,
                 doors=3_980, perdoor=930, cogs_rate=0.420, ad_rate=0.170, log_rate=0.082),
    "FY25": dict(member=212_000, repeat=0.75, new=65_000, freq=2.52, aov=6_520,
                 doors=4_060, perdoor=975, cogs_rate=0.415, ad_rate=0.175, log_rate=0.081),
    "FY26": dict(member=228_000, repeat=0.76, new=69_000, freq=2.60, aov=6_650,
                 doors=4_150, perdoor=1_010, cogs_rate=0.410, ad_rate=0.180, log_rate=0.080),
}

_PLAN_DRIVERS = {
    "base": {
        "FY27": dict(repeat=0.76, new=66_000, freq=2.60, aov=6_720,
                     doors=4_200, perdoor=1_020, cogs_rate=0.410, ad_rate=0.180, log_rate=0.080),
        "FY28": dict(repeat=0.76, new=66_000, freq=2.61, aov=6_790,
                     doors=4_240, perdoor=1_028, cogs_rate=0.410, ad_rate=0.180, log_rate=0.080),
        "FY29": dict(repeat=0.76, new=66_000, freq=2.62, aov=6_860,
                     doors=4_280, perdoor=1_035, cogs_rate=0.410, ad_rate=0.180, log_rate=0.080),
        "FY30": dict(repeat=0.76, new=66_000, freq=2.64, aov=6_930,
                     doors=4_320, perdoor=1_043, cogs_rate=0.410, ad_rate=0.180, log_rate=0.080),
        "FY31": dict(repeat=0.76, new=66_000, freq=2.65, aov=7_000,
                     doors=4_350, perdoor=1_050, cogs_rate=0.410, ad_rate=0.180, log_rate=0.080),
    },
    "sponsor": {
        "FY27": dict(repeat=0.770, new=68_000, freq=2.68, aov=6_750,
                     doors=4_250, perdoor=1_040, cogs_rate=0.405, ad_rate=0.185, log_rate=0.079),
        "FY28": dict(repeat=0.775, new=70_000, freq=2.70, aov=6_850,
                     doors=4_340, perdoor=1_068, cogs_rate=0.402, ad_rate=0.183, log_rate=0.078),
        "FY29": dict(repeat=0.780, new=72_000, freq=2.72, aov=6_950,
                     doors=4_430, perdoor=1_095, cogs_rate=0.399, ad_rate=0.182, log_rate=0.077),
        "FY30": dict(repeat=0.785, new=75_000, freq=2.74, aov=7_050,
                     doors=4_520, perdoor=1_123, cogs_rate=0.397, ad_rate=0.181, log_rate=0.077),
        "FY31": dict(repeat=0.790, new=78_000, freq=2.75, aov=7_150,
                     doors=4_600, perdoor=1_150, cogs_rate=0.395, ad_rate=0.180, log_rate=0.076),
    },
}


def drivers(case: str) -> dict:
    """ケース別の全年度ドライバー（実績3年は両ケース共通）。
    member（アクティブ会員数）は計画年について 前期×リピート率＋新規 で漸化計算する。
    """
    d = {}
    for y in ACTUAL_YEARS:
        d[y] = dict(_ACTUAL_DRIVERS[y])
    prev_member = d["FY26"]["member"]
    for y in PLAN_YEARS:
        row = dict(_PLAN_DRIVERS[case][y])
        row["member"] = int(excel_round(prev_member * row["repeat"] + row["new"]))
        prev_member = row["member"]
        d[y] = row
    return d


# ---------------------------------------------------------------- ハードコード行（百万円）
# PLの非ドライバー行。実績年は両ケース共通、計画年はケース別。

_HARD_ACTUAL = {
    "FY24": dict(other_revenue=1_014, personnel=870, other_sga=1_050,
                 depreciation=150, interest=28, non_op=6),
    "FY25": dict(other_revenue=1_058, personnel=905, other_sga=1_096,
                 depreciation=155, interest=25, non_op=7),
    "FY26": dict(other_revenue=1_106, personnel=950, other_sga=1_140,
                 depreciation=160, interest=22, non_op=8),
}

_HARD_PLAN = {
    "base": {
        "FY27": dict(other_revenue=1_130, personnel=975, other_sga=1_165,
                     depreciation=165, non_op=8),
        "FY28": dict(other_revenue=1_155, personnel=1_000, other_sga=1_190,
                     depreciation=168, non_op=8),
        "FY29": dict(other_revenue=1_180, personnel=1_025, other_sga=1_215,
                     depreciation=171, non_op=8),
        "FY30": dict(other_revenue=1_205, personnel=1_050, other_sga=1_240,
                     depreciation=174, non_op=8),
        "FY31": dict(other_revenue=1_230, personnel=1_075, other_sga=1_265,
                     depreciation=177, non_op=8),
    },
    "sponsor": {
        "FY27": dict(other_revenue=1_140, personnel=985, other_sga=1_175,
                     depreciation=170, non_op=8),
        "FY28": dict(other_revenue=1_180, personnel=1_020, other_sga=1_215,
                     depreciation=178, non_op=8),
        "FY29": dict(other_revenue=1_225, personnel=1_060, other_sga=1_255,
                     depreciation=186, non_op=8),
        "FY30": dict(other_revenue=1_270, personnel=1_100, other_sga=1_300,
                     depreciation=194, non_op=8),
        "FY31": dict(other_revenue=1_320, personnel=1_145, other_sga=1_345,
                     depreciation=202, non_op=8),
    },
}

TAX_RATE = 0.305

# ---------------------------------------------------------------- デットスケジュール（百万円）

SENIOR_TOTAL = 4_800          # シニアタームローンA
ANNUAL_REPAYMENT = 480        # 約定弁済（年）。最終回は残額一括（モデル期間外）
INTEREST_RATE = 0.023         # TIBOR + 230bp 想定


def debt_schedule() -> dict:
    """FY27〜FY31のシニアローン残高・支払利息（百万円）。"""
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


# 実績年の既存借入（BS用・百万円）
EXISTING_DEBT = {"FY24": 600, "FY25": 500, "FY26": 400}

# ---------------------------------------------------------------- PL計算（百万円）


def compute_pl(case: str) -> dict:
    """ケース別PL。Excelに書き込む数式とまったく同じロジック（ROUND位置も揃える）。"""
    drv = drivers(case)
    sched = debt_schedule()
    pl = {}
    for y in YEARS:
        d = drv[y]
        hard = _HARD_ACTUAL[y] if y in ACTUAL_YEARS else _HARD_PLAN[case][y]
        # EC売上 = 会員数×購入回数×AOV（円）→ 百万円
        ec_rev = int(excel_round(d["member"] * d["freq"] * d["aov"] / 1_000_000))
        # 卸売上 = 店舗数×店舗あたり年間出荷額（千円）→ 百万円
        ws_rev = int(excel_round(d["doors"] * d["perdoor"] / 1_000))
        revenue = ec_rev + ws_rev + hard["other_revenue"]
        cogs = int(excel_round(revenue * d["cogs_rate"]))
        gross = revenue - cogs
        ad = int(excel_round(revenue * d["ad_rate"]))
        logistics = int(excel_round(revenue * d["log_rate"]))
        sga = ad + logistics + hard["personnel"] + hard["other_sga"]
        op = gross - sga
        ebitda = op + hard["depreciation"]
        interest = hard["interest"] if y in ACTUAL_YEARS else sched[y]["interest"]
        ordinary = op - interest + hard["non_op"]
        tax = int(excel_round(ordinary * TAX_RATE))
        ni = ordinary - tax
        pl[y] = dict(
            ec_rev=ec_rev, ws_rev=ws_rev, other_revenue=hard["other_revenue"],
            revenue=revenue,
            cogs=cogs, gross=gross, gross_margin=gross / revenue,
            ad=ad, logistics=logistics, personnel=hard["personnel"],
            other_sga=hard["other_sga"], sga=sga,
            op=op, op_margin=op / revenue,
            depreciation=hard["depreciation"], ebitda=ebitda, ebitda_margin=ebitda / revenue,
            interest=interest, non_op=hard["non_op"], ordinary=ordinary, tax=tax, ni=ni,
        )
    return pl


# ---------------------------------------------------------------- BS / CF（百万円）

POST_CLOSE_CASH = 240     # FY27期首現金（買収時：手元現金380活用後）

_BS_ACTUAL = {
    # 現預金 / 売上債権 / 棚卸資産 / その他流動 / 有形固定 / 無形その他 / 仕入債務 / その他負債 / 純資産
    "FY24": dict(cash=380, ar=960, inv=1_050, oca=170, ppe=640, intangible=220,
                 ap=590, other_liab=180, net_assets=2_050),
    "FY25": dict(cash=500, ar=1_048, inv=1_140, oca=185, ppe=660, intangible=235,
                 ap=640, other_liab=198, net_assets=2_430),
    "FY26": dict(cash=620, ar=1_139, inv=1_230, oca=200, ppe=680, intangible=250,
                 ap=690, other_liab=179, net_assets=2_850),
}

_CF_ACTUAL = {
    # 営業CF / 投資CF / 財務CF（返済・配当等）
    "FY24": dict(op_cf=720, inv_cf=-140, fin_cf=-520),
    "FY25": dict(op_cf=810, inv_cf=-150, fin_cf=-540),
    "FY26": dict(op_cf=905, inv_cf=-160, fin_cf=-625),
}
OPENING_CASH_FY24 = 320   # FY24期首現金（=380-60）

_PLAN_AP = {
    "base": {"FY27": 720, "FY28": 740, "FY29": 760, "FY30": 780, "FY31": 800},
    "sponsor": {"FY27": 735, "FY28": 770, "FY29": 805, "FY30": 840, "FY31": 875},
}
_PLAN_CAPEX = {"base": 170, "sponsor": 200}
_PLAN_OTHER_LIAB = 190   # 計画期間のその他負債（固定）
_PLAN_OCA_BASE = 205     # FY27のその他流動資産（毎年+5）
_PLAN_INTANGIBLE = 715   # 買収後無形（既存250＋識別無形465）
AR_DAYS = 45   # 売上債権回転日数
INV_DAYS = 118  # 棚卸資産回転日数（対売上原価）


def compute_bs_cf(case: str) -> tuple[dict, dict]:
    """計画BS・CF。CFの積み上げで現金を決め、BSは恒等式で自動的にバランスする。
    買収時調整（のれん計上・旧純資産消去等のネット差額）はFY27の純資産側で吸収し、
    以降の年度へ同額を引き継ぐ（既存デモと同じ簡略化・Excelにも注記を書く）。
    """
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
        b["total_assets"] = (b["cash"] + b["ar"] + b["inv"] + b["oca"]
                             + b["ppe"] + b["goodwill"] + b["intangible"])
        balance = b["total_assets"] - (b["ap"] + b["other_liab"] + b["debt"] + b["net_assets"])
        assert balance == 0, f"BS実績 {y}: バランス不一致 {balance}"
    # 実績年の現金整合（CF→BS）
    prev = OPENING_CASH_FY24
    for y in ACTUAL_YEARS:
        prev = prev + cf[y]["net_change"]
        assert prev == bs[y]["cash"], f"CF実績 {y}: 期末現金不一致 {prev} != {bs[y]['cash']}"

    prev_bs = None
    prev_cash = POST_CLOSE_CASH
    prev_na = DEAL["equity_mm"]  # エクイティ出資 4,620
    prev_purchase_adj = 0
    for i, y in enumerate(PLAN_YEARS):
        p = pl[y]
        b = dict(
            ar=int(excel_round(p["revenue"] * AR_DAYS / 365)),
            inv=int(excel_round(p["cogs"] * INV_DAYS / 365)),
            oca=_PLAN_OCA_BASE + 5 * i,
            goodwill=GOODWILL,
            intangible=_PLAN_INTANGIBLE,
            ap=_PLAN_AP[case][y],
            debt=sched[y]["closing"],
            other_liab=_PLAN_OTHER_LIAB,
        )
        ref = _BS_ACTUAL["FY26"] if prev_bs is None else prev_bs
        b["ppe"] = ref["ppe"] + _PLAN_CAPEX[case] - p["depreciation"]
        d_ar = b["ar"] - ref["ar"]
        d_inv = b["inv"] - ref["inv"]
        d_oca = b["oca"] - ref["oca"]
        d_ap = b["ap"] - ref["ap"]
        d_ol = b["other_liab"] - (bs["FY26"]["other_liab"] if prev_bs is None
                                  else prev_bs["other_liab"])
        wc_change = d_ar + d_inv + d_oca - d_ap - d_ol
        op_cf = p["ni"] + p["depreciation"] - wc_change
        inv_cf = -_PLAN_CAPEX[case]
        fin_cf = -sched[y]["repayment"]
        net_change = op_cf + inv_cf + fin_cf
        b["cash"] = prev_cash + net_change
        b["net_assets"] = prev_na + p["ni"]
        b["total_assets"] = (b["cash"] + b["ar"] + b["inv"] + b["oca"]
                             + b["ppe"] + b["goodwill"] + b["intangible"])
        balance = b["total_assets"] - (b["ap"] + b["other_liab"] + b["debt"] + b["net_assets"])
        if y == "FY27":
            # のれん計上と旧純資産消去のネット差額（買収時調整）を純資産側で吸収
            b["purchase_adj"] = balance
            b["net_assets"] += balance
        else:
            b["purchase_adj"] = prev_purchase_adj
            b["net_assets"] += prev_purchase_adj
        balance2 = b["total_assets"] - (b["ap"] + b["other_liab"] + b["debt"] + b["net_assets"])
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


# ---------------------------------------------------------------- ファイル名

DD_FILES = {
    "business": "事業DD報告書_ルミエールボーテ_最終版.pdf",
    "financial": "財務DD報告書_ルミエールボーテ_最終版.pdf",
    "legal": "法務DD報告書_ルミエールボーテ_最終版.pdf",
    "tax": "税務DD報告書_ルミエールボーテ_最終版.pdf",
}

MODEL_FILES = {
    "sponsor": "LumiereBeaute_LBO_Model_v2.3_Sponsor.xlsx",
    "base": "LumiereBeaute_LBO_Model_v2.3_BankBase.xlsx",
}

DD_FIRMS = {
    "business": "青山ストラテジー＆パートナーズ株式会社",
    "financial": "八重洲FAS株式会社（八重洲監査法人グループ）",
    "legal": "丸の内総合法律事務所",
    "tax": "京橋税理士法人",
}

# ---------------------------------------------------------------- DDレポート キーファクト
# ページ番号は「PDFの通しページ（表紙=1ページ目）」。
# check はそのページに一字一句存在すべき照合フレーズ（validate.pyが検証）。

DD_KEY_FACTS = [
    dict(id="ec_repeat", file="business", page=15,
         text="EC定期会員のリピート率は76%（2026年3月期）",
         check=["EC定期会員のリピート率は76%"],
         value="76%"),
    dict(id="oem_dependency", file="business", page=17,
         text="最大委託先である三双化学工業への生産依存度は58%",
         check=["最大委託先である三双化学工業への生産依存度は58%"],
         value="58%"),
    dict(id="wholesale_concentration", file="business", page=18,
         text="卸売上の上位3チェーンへの売上依存度は45%（うち最大手マツヤドラッグ21%）",
         check=["上位3チェーンへの売上依存度は45%（うち最大手マツヤドラッグ21%）"],
         value="45%（最大手21%）"),
    dict(id="normalized_ebitda", file="financial", page=33,
         text="正常収益力ベースのEBITDAは1,036百万円",
         check=["正常収益力ベースのEBITDAは1,036百万円"],
         value="1,036百万円"),
    dict(id="goodwill_dd", file="financial", page=30,
         text="のれん想定額は5,950百万円（スポンサーモデルは6,100百万円・150百万円の差異）",
         check=["のれん想定額は5,950百万円", "6,100百万円が計上されており", "150百万円の差異"],
         value="5,950百万円"),
    dict(id="inventory_writedown", file="financial", page=21,
         text="滞留在庫に係る評価損は120百万円",
         check=["滞留在庫に係る評価損は120百万円"],
         value="120百万円"),
    dict(id="cosmetics_license", file="legal", page=5,
         text="化粧品製造販売業許可（13CZ200088）は2027年11月に更新期限",
         check=["13CZ200088", "2027年11月"],
         value="13CZ200088"),
    dict(id="coc_clause", file="legal", page=8,
         text="主要OEM委託契約2件にチェンジ・オブ・コントロール条項（事前書面同意）",
         check=["チェンジ・オブ・コントロール条項"],
         value="COC条項2件"),
    dict(id="trademark", file="legal", page=11,
         text="主力ブランド「Lumière Beauté」の商標権は代表者個人名義（クロージング前に会社への移転が必要）",
         check=["商標権は代表者個人名義"],
         value="個人名義・要移転"),
    dict(id="nol", file="tax", page=6,
         text="繰越欠損金は85百万円（2028年3月期まで繰越可能）",
         check=["繰越欠損金は85百万円"],
         value="85百万円"),
]

# ---------------------------------------------------------------- 検証用サマリー


def summary_check():
    """正本数値の主要ピンが成立していることを確認する（validate.pyから呼ぶ）。"""
    pl_base = compute_pl("base")
    # FY26実績（両ケース共通）
    assert pl_base["FY26"]["revenue"] == 9240, pl_base["FY26"]["revenue"]
    assert pl_base["FY26"]["ebitda"] == 1120, pl_base["FY26"]["ebitda"]
    assert pl_base["FY26"]["ec_rev"] == 3942, pl_base["FY26"]["ec_rev"]
    assert pl_base["FY26"]["ws_rev"] == 4192, pl_base["FY26"]["ws_rev"]
    # 計画ピン（Base FY27）
    assert pl_base["FY27"]["revenue"] == 9595, pl_base["FY27"]["revenue"]
    assert pl_base["FY27"]["ebitda"] == 1191, pl_base["FY27"]["ebitda"]
    # 自動算出
    assert DEAL["initial_leverage"] == 4.3 and DEAL["ltv_pct"] == 53
    # ドライバー
    d = drivers("base")["FY26"]
    assert d["member"] == 228_000 and d["repeat"] == 0.76 and d["aov"] == 6_650
    # 正常収益力ブリッジ
    assert NORMALIZED_EBITDA == 1036
    for case in CASES:
        compute_bs_cf(case)  # バランスチェック（assert内蔵）
    return True


if __name__ == "__main__":
    summary_check()
    for case in ("base", "sponsor"):
        pl = compute_pl(case)
        print(f"=== {case} PL（百万円） ===")
        for y in YEARS:
            p = pl[y]
            print(f"{y}: 売上 {p['revenue']:,} (EC {p['ec_rev']:,}/卸 {p['ws_rev']:,}) "
                  f"/ 営業利益 {p['op']:,} / EBITDA {p['ebitda']:,} "
                  f"({p['ebitda_margin']:.1%}) / 純利益 {p['ni']:,}")
    for case in CASES:
        bs, cf = compute_bs_cf(case)
        print(f"=== {case} 現預金・FCF（百万円） ===")
        print({y: (bs[y]["cash"], cf[y]["fcf"]) for y in YEARS})
    print("summary_check OK")
