# -*- coding: utf-8 -*-
"""模範解答（正しくAIが動いた場合の出力例）の生成。

AnthropicExtractor が返すのと同じデータ形状（backend/app/fixtures/*.json と同形）で、
「実AIが理想的に動作した場合の出力」を reference_output/ に生成する。

用途:
  - 実AIテストの前に「どのような出力になれば正しいのか」を具体物で確認する
  - 実AIの raw_*.json と並べて差分をレビューする
  - 採点スクリプトの検証（reference を採点すると必ず合格になる：validate.py [7]）

数値はすべて spec.py から導出し、根拠の原文抜粋（quote）は生成済みの資料と
一字一句一致させる（validate.py が照合する）。

生成物:
  reference_output/reference_identify.json    … identify_document ×6ファイル
  reference_output/reference_deal_info.json   … extract_deal_info
  reference_output/reference_items.json       … extract_items（24項目）
  reference_output/reference_kpi_tree.json    … propose_kpi_tree
  reference_output/reference_scenarios.json   … propose_scenarios（3類型）
  reference_output/report.md                  … 上記を採点した場合のレポート（合格）
"""
import json
from pathlib import Path

import spec
import xl_layout as L
from spec import ACTUAL_YEARS, PLAN_YEARS

HERE = Path(__file__).parent
OUT = HERE / "reference_output"

_pl_b = spec.compute_pl("base")
_pl_s = spec.compute_pl("sponsor")
_bs_b, _cf_b = spec.compute_bs_cf("base")
_bs_s, _cf_s = spec.compute_bs_cf("sponsor")
_d26 = spec.drivers("base")["FY26"]

F_BASE = spec.MODEL_FILES["base"]
F_SPON = spec.MODEL_FILES["sponsor"]
F_BIZ = spec.DD_FILES["business"]
F_FIN = spec.DD_FILES["financial"]
F_LEG = spec.DD_FILES["legal"]
F_TAX = spec.DD_FILES["tax"]

SEC_QUAL = "前提・定性情報"
SEC_ACT = "実績（2024/3期〜2026/3期）"
SEC_BASE = "計画：ベースケース（2027/3期〜2031/3期）"
SEC_SPON = "計画：スポンサーケース（2027/3期〜2031/3期）"
SEC_STRUCT = "ストラクチャー・B/S項目"

# 年間元利返済の目安（シナリオのAI推定で使う水準感）
_DEBT_SVC_Y1 = spec.ANNUAL_REPAYMENT + spec.debt_schedule()["FY27"]["interest"]  # 585


# ---------------------------------------------------------------- identify

def build_identify() -> dict:
    return {
        F_SPON: dict(
            company=spec.DEAL["target"], doc_type="model_sponsor",
            label="財務モデル（スポンサーケース）",
            detail="CoverシートにProject Bloom・対象会社名・「ケース：Sponsor Case"
                   "（スポンサーケース）」の記載。ファイル名のSponsorとも整合。"),
        F_BASE: dict(
            company=spec.DEAL["target"], doc_type="model_base",
            label="財務モデル（ベースケース・銀行調整）",
            detail="Coverシートに「ケース：Bank Base Case（ベースケース（銀行調整））」"
                   "の記載。ファイル名のBankBaseとも整合。"),
        F_BIZ: dict(
            company=spec.DEAL["target"], doc_type="dd_business",
            label="事業DDレポート",
            detail="表紙に「事業デューデリジェンス報告書／株式会社ルミエールボーテ」。"
                   "作成者は青山ストラテジー＆パートナーズ。"),
        F_FIN: dict(
            company=spec.DEAL["target"], doc_type="dd_financial",
            label="財務DDレポート",
            detail="表紙に「財務デューデリジェンス報告書／株式会社ルミエールボーテ」。"
                   "作成者は八重洲FAS。"),
        F_LEG: dict(
            company=spec.DEAL["target"], doc_type="dd_legal",
            label="法務DDレポート",
            detail="表紙に「法務デューデリジェンス報告書／株式会社ルミエールボーテ」。"
                   "作成者は丸の内総合法律事務所。"),
        F_TAX: dict(
            company=spec.DEAL["target"], doc_type="dd_tax",
            label="税務DDレポート",
            detail="表紙に「税務デューデリジェンス報告書／株式会社ルミエールボーテ」。"
                   "作成者は京橋税理士法人。"),
    }


# ---------------------------------------------------------------- deal_info

def build_deal_info() -> dict:
    S = L.INP_STRUCT_ROWS
    return dict(
        fields=dict(
            name=spec.DEAL["name"],
            deal_type="LBO",
            borrower=spec.DEAL["borrower"],
            target=spec.DEAL["target"],
            industry=spec.DEAL["industry"],
            sponsor=spec.DEAL["sponsor"],
            close_date=spec.DEAL["close_date"],
            ev_mm=spec.DEAL["ev_mm"],
            senior_mm=spec.DEAL["senior_mm"],
            equity_mm=spec.DEAL["equity_mm"],
            tenor_years=spec.DEAL["tenor_years"],
            sponsor_ebitda_mm=spec.DEAL["sponsor_ebitda_mm"],
            summary=(
                "大手町プリンシパルパートナーズがSPC（株式会社ブルームホールディングス）を"
                "通じて化粧品・スキンケアD2Cのルミエールボーテ全株式を取得する事業承継型LBO。"
                "EC定期会員22.8万人（リピート率76%）とドラッグストア卸の2チャネル・"
                "全量OEM委託のファブレス経営。EV9,000百万円（提示EBITDA1,120の約8.0x）、"
                "シニア4,800・エクイティ4,620で調達。クローズは2026年11月30日予定。"),
        ),
        sources=dict(
            name="対象会社名（全資料）＋案件種別から生成",
            deal_type=f"{F_BIZ} p.4（1.2 本件の背景とスキーム：LBOと明記）／モデルCover",
            borrower=f"{F_BASE} Cover（借入人（SPC））・inp!D{S['borrower'][0]}／{F_BIZ} p.4",
            target=f"{F_BASE} Cover（会社名）／各DD表紙",
            industry=f"{F_BASE} Cover（事業内容）／{F_BIZ} p.4",
            sponsor=f"{F_BASE} Cover（スポンサー）／{F_BIZ} p.4",
            close_date=f"{F_BASE} Cover（クローズ予定日）・inp!D{S['close'][0]}／{F_BIZ} p.4",
            ev_mm=f"{F_BASE} inp!D{S['ev'][0]}",
            senior_mm=f"{F_BASE} inp!D{S['senior'][0]}／debtシート期初残高",
            equity_mm=f"{F_BASE} inp!D{S['equity'][0]}",
            tenor_years=f"{F_BASE} inp!D{S['tenor'][0]}",
            sponsor_ebitda_mm=f"{F_BASE} inp!D{S['sponsor_ebitda'][0]}／{F_FIN} p.31",
            summary=f"{F_BIZ} p.4〜5（エグゼクティブサマリー）から要約",
        ),
        note="本行取組額・担当者・審査相談予定日は行内情報のため資料に存在せず、"
             "対象外（nullも返さない）。",
    )


# ---------------------------------------------------------------- items（24件）

def _mm(v: int) -> str:
    return f"{v:,}"


def build_items() -> list[dict]:
    S = L.INP_STRUCT_ROWS
    items = []

    def ev(file, location, quote, logic):
        return dict(file=file, location=location, quote=quote, logic=logic)

    # ---- 定性
    items.append(dict(
        key="business_summary", section=SEC_QUAL, label="事業要約", unit="テキスト",
        case=None, values=None, required=True,
        text_value=(
            "スキンケア中心の化粧品D2C・卸の中堅（売上9,240百万円・EBITDA1,120百万円）。"
            "自社EC（定期会員22.8万人・リピート率76%）とドラッグストア卸4,150店の"
            "2チャネル。製造は全量OEM委託のファブレス。創業者（67歳・株式90%）の"
            "事業承継を背景としたスポンサー主導のLBO。"),
        evidence=ev(F_BIZ, "p.4〜5（1. エグゼクティブサマリー）",
                    "株式会社ルミエールボーテ（以下「対象会社」）は、スキンケアを中心とする"
                    "化粧品の企画・販売を行うファブレス企業である。",
                    "事業DDのエグゼクティブサマリーから事業内容・チャネル構造・"
                    "案件背景を要約。"),
        mismatch=None))
    items.append(dict(
        key="risk_oem", section=SEC_QUAL, label="主要リスク①：OEM委託先への生産依存",
        unit="テキスト", case=None, values=None, required=True,
        text_value=(
            "最大委託先・三双化学工業への生産依存度58%（仕入高ベース）。主力3カテゴリは"
            "実質一社供給で、代替委託先の認定には12〜18ヶ月を要する。同契約には"
            "チェンジ・オブ・コントロール条項あり。"),
        evidence=ev(F_BIZ, "p.17（6.2 最大委託先への生産依存）",
                    "最大委託先である三双化学工業への生産依存度は58%（2026年3月期・"
                    "仕入高ベース）。",
                    "事業DD 6章の依存構造分析から調達面の最重要リスクとして抽出。"
                    "法務DDのCOC条項（p.8）とも関連。"),
        mismatch=None))
    items.append(dict(
        key="risk_wholesale", section=SEC_QUAL, label="主要リスク②：卸チェーンへの売上集中",
        unit="テキスト", case=None, values=None, required=True,
        text_value=(
            "卸売上の上位3チェーン依存度45%（うち最大手マツヤドラッグ21%）。"
            "年次商談で棚割りが更新され、中期の数量コミットメントはない。"),
        evidence=ev(F_BIZ, "p.18（6.3 販売面：卸チェーンへの集中）",
                    "卸売上の上位3チェーンへの売上依存度は45%（うち最大手マツヤドラッグ21%）"
                    "であり、棚割り見直しやPBシフトによる取引縮小が生じた場合、"
                    "卸チャネルの物量に大きな影響が及ぶ。",
                    "事業DD 6章の販売面集中度の記載を主要リスクとして採用。"),
        mismatch=None))
    items.append(dict(
        key="risk_trademark", section=SEC_QUAL, label="主要リスク③：商標権が代表者個人名義",
        unit="テキスト", case=None, values=None, required=False,
        text_value=(
            "主力ブランド「Lumière Beauté」の商標権が代表者個人名義。クロージング前の"
            "会社への移転（譲渡登録・2〜3ヶ月）が取引の前提条件。"),
        evidence=ev(F_LEG, "p.11（6. 知的財産）",
                    "主力ブランド「Lumière Beauté」（標準文字・ロゴ、第3類）の商標権は"
                    "代表者個人名義で登録されており、",
                    "法務DDの重要指摘事項。クロージング条件（CP）に位置づけられている。"),
        mismatch=None))
    items.append(dict(
        key="normalized_ebitda", section=SEC_QUAL, label="正常収益力EBITDA（2026/3期）",
        unit="百万円", case=None, values={"FY26": spec.NORMALIZED_EBITDA},
        required=True, text_value=None,
        evidence=ev(F_FIN, "p.33（VII. 結論：正常収益力EBITDA）",
                    "2026年3月期の正常収益力ベースのEBITDAは1,036百万円と算定される。",
                    "財務DDのQoE結論値。報告EBITDA1,120百万円からの調整（▲84）は"
                    "p.32に内訳あり。これは調整であり資料間の不整合ではない。"),
        mismatch=None))

    # ---- 実績（両ケース共通のためベースモデルから転記）
    def act(key, label, sheet, row_key, values, required=True, note=""):
        rng = L.cell_range(sheet, row_key, "FY24", "FY26")
        row_label = {"PL": L.PL_ROWS, "BS": L.BS_ROWS, "CF": L.CF_ROWS}[sheet][row_key][1]
        items.append(dict(
            key=key, section=SEC_ACT, label=label, unit="百万円", case=None,
            values={y: values[y] for y in ACTUAL_YEARS}, required=required,
            text_value=None,
            evidence=ev(F_BASE, f"{rng}（{sheet}シート・実績3期）",
                        f"{row_label}: " + " / ".join(_mm(values[y]) for y in ACTUAL_YEARS),
                        f"{sheet}シートの行ラベル「{row_label}」を{label}にマッピング。"
                        f"実績年は「A（実績）」列（2024/3期〜2026/3期）。単位は百万円"
                        f"（シート注記）でありそのまま転記。{note}".strip()),
            mismatch=None))

    act("act_revenue", "売上高", "PL", "revenue",
        {y: _pl_b[y]["revenue"] for y in ACTUAL_YEARS},
        note="モデルの表記は「売上収益 合計」。売上高に名寄せ。")
    act("act_op", "営業利益", "PL", "op",
        {y: _pl_b[y]["op"] for y in ACTUAL_YEARS},
        note="モデルの表記は「営業利益（EBIT）」。")
    act("act_ebitda", "EBITDA", "PL", "ebitda",
        {y: _pl_b[y]["ebitda"] for y in ACTUAL_YEARS},
        note="営業利益＋減価償却費の行。財務DD p.31の報告EBITDAとも一致。")
    act("act_ni", "当期純利益", "PL", "ni",
        {y: _pl_b[y]["ni"] for y in ACTUAL_YEARS}, required=False)
    act("act_cash", "現預金", "BS", "cash",
        {y: _bs_b[y]["cash"] for y in ACTUAL_YEARS},
        note="モデルの表記は「現金及び現金同等物」。")
    act("act_net_assets", "純資産", "BS", "net_assets",
        {y: _bs_b[y]["net_assets"] for y in ACTUAL_YEARS})
    act("act_debt", "有利子負債", "BS", "debt",
        {y: _bs_b[y]["debt"] for y in ACTUAL_YEARS})
    act("act_fcf", "フリー・キャッシュフロー", "CF", "fcf",
        {y: _cf_b[y]["fcf"] for y in ACTUAL_YEARS}, required=False)

    # ---- 計画（ケース別）
    def plan(key, label, sheet, row_key, case, values, required=True):
        file = F_BASE if case == "base" else F_SPON
        section = SEC_BASE if case == "base" else SEC_SPON
        case_label = spec.CASE_LABEL[case]
        rng = L.cell_range(sheet, row_key, "FY27", "FY31")
        row_label = {"PL": L.PL_ROWS, "CF": L.CF_ROWS}[sheet][row_key][1]
        items.append(dict(
            key=key, section=section, label=label, unit="百万円", case=case,
            values={y: values[y] for y in PLAN_YEARS}, required=required,
            text_value=None,
            evidence=ev(file, f"{rng}（{sheet}シート・計画5年）",
                        f"{row_label}: " + " / ".join(_mm(values[y]) for y in PLAN_YEARS),
                        f"Coverシートの「ケース：{case_label}」でケースを判定。"
                        f"計画年は「P（計画）」列（2027/3期〜2031/3期）。数式セルの計算結果"
                        f"（キャッシュ値）を転記（再計算はしていない）。単位は百万円。"),
            mismatch=None))

    plan("base_revenue", "売上高", "PL", "revenue", "base",
         {y: _pl_b[y]["revenue"] for y in PLAN_YEARS})
    plan("base_op", "営業利益", "PL", "op", "base",
         {y: _pl_b[y]["op"] for y in PLAN_YEARS})
    plan("base_ebitda", "EBITDA", "PL", "ebitda", "base",
         {y: _pl_b[y]["ebitda"] for y in PLAN_YEARS})
    plan("base_fcf", "フリー・キャッシュフロー", "CF", "fcf", "base",
         {y: _cf_b[y]["fcf"] for y in PLAN_YEARS})
    plan("sponsor_revenue", "売上高", "PL", "revenue", "sponsor",
         {y: _pl_s[y]["revenue"] for y in PLAN_YEARS})
    plan("sponsor_op", "営業利益", "PL", "op", "sponsor",
         {y: _pl_s[y]["op"] for y in PLAN_YEARS})
    plan("sponsor_ebitda", "EBITDA", "PL", "ebitda", "sponsor",
         {y: _pl_s[y]["ebitda"] for y in PLAN_YEARS})
    plan("sponsor_fcf", "フリー・キャッシュフロー", "CF", "fcf", "sponsor",
         {y: _cf_s[y]["fcf"] for y in PLAN_YEARS}, required=False)

    # ---- ストラクチャー
    items.append(dict(
        key="goodwill", section=SEC_STRUCT, label="のれん（買収想定額）", unit="百万円",
        case=None, values={"FY27": spec.GOODWILL}, required=True, text_value=None,
        evidence=ev(F_BASE,
                    f"inp!D{S['goodwill'][0]}（のれん想定額）／"
                    + L.cell_range("BS", "goodwill", "FY27", "FY31"),
                    "のれん想定額（暫定PPA前）: 6,100",
                    "inpシートの「のれん想定額（暫定PPA前）」を採用。BS計画年の"
                    "のれん行とも一致。財務DDの試算額とは差異があるためmismatchに併記。"),
        mismatch=dict(
            other_value=spec.GOODWILL_DD,
            other_file=F_FIN,
            other_location="p.30（VI. のれん想定額の試算）",
            other_quote="当社試算によるのれん想定額は5,950百万円である。一方、スポンサーの"
                        "財務モデル上は6,100百万円が計上されており、150百万円の差異がある。",
            note="モデル（6,100）と財務DD（5,950）で150百万円の差異。識別可能無形資産の"
                 "試算差（DD615 vs モデル465）。PPAで確定予定。どちらを採用するか選択が必要。"),
    ))
    items.append(dict(
        key="ev", section=SEC_STRUCT, label="エンタープライズ・バリュー（EV）",
        unit="百万円", case=None, values={"FY27": spec.DEAL["ev_mm"]}, required=True,
        text_value=None,
        evidence=ev(F_BASE, f"inp!D{S['ev'][0]}",
                    "エンタープライズ・バリュー（EV）: 9,000",
                    "inpシートのストラクチャー欄から転記。財務DD p.29のネットデット・"
                    "株式価値の算定とも整合（EV9,000＋ネットキャッシュ220＝株式対価9,220）。"),
        mismatch=None))
    items.append(dict(
        key="senior_loan", section=SEC_STRUCT, label="シニアローン総額", unit="百万円",
        case=None, values={"FY27": spec.SENIOR_TOTAL}, required=True, text_value=None,
        evidence=ev(F_BASE,
                    f"inp!D{S['senior'][0]}／debt!"
                    f"{spec.COL['FY27']}{L.DEBT_ROWS['opening'][0]}（期初残高）",
                    "シニアタームローンA: 4,800",
                    "inpシートのSources & Uses欄から転記。debtシートの期初残高とも一致。"
                    "約定弁済は年480百万円・期間7年。"),
        mismatch=None))
    return items


# ---------------------------------------------------------------- kpi_tree

def build_kpi_tree() -> dict:
    D = L.INP_DRIVER_ROWS
    P = L.PL_ROWS

    def ev(location, quote, logic):
        return dict(file=F_BASE, location=location, quote=quote, logic=logic)

    c27 = spec.COL["FY27"]
    nodes = [
        dict(id="revenue", parent=None, label="売上収益", origin="model", star=False,
             formula="EC売上＋卸売上＋その他売上",
             value_text=f"FY26実績 {_pl_b['FY26']['revenue']:,}百万円", badge=None,
             evidence=ev(f"PL!{c27}{P['revenue'][0]}",
                         "=SUM(F7:F9)",
                         "PL10行のSUM数式からEC・卸・その他の3チャネル構成を判定。")),
        dict(id="ec_rev", parent="revenue", label="EC売上", origin="model", star=False,
             formula="アクティブ会員数 × 年間平均購入回数 × 平均注文単価（AOV）",
             value_text=f"FY26実績 {_pl_b['FY26']['ec_rev']:,}百万円", badge=None,
             evidence=ev(f"PL!{c27}{P['ec_rev'][0]}",
                         f"=ROUND(inp!{c27}{D['member'][0]}*inp!{c27}{D['freq'][0]}"
                         f"*inp!{c27}{D['aov'][0]}/10^6,0)",
                         "PL7行の数式がinpシートの会員数×購入回数×AOVを参照。")),
        dict(id="member", parent="ec_rev", label="アクティブ会員数", origin="model",
             star=False,
             formula="前期会員数 × リピート率 ＋ 新規獲得会員数",
             value_text=f"FY26実績 {_d26['member']:,}人", badge=None,
             evidence=ev(f"inp!{c27}{D['member'][0]}",
                         f"=ROUND(E{D['member'][0]}*{c27}{D['repeat'][0]}"
                         f"+{c27}{D['new'][0]},0)",
                         "inp30行の漸化式からリピート率・新規獲得への分解を判定。")),
        dict(id="repeat", parent="member", label="リピート率", origin="model", star=True,
             formula=None, value_text=f"FY26実績 {_d26['repeat']:.0%}", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['repeat'][0]}",
                         "リピート率（既存会員残存率）: 0.76",
                         "事業DD p.15が「事業計画の最重要ドライバー」と指摘（1pt低下で"
                         "EC売上▲約50百万円）。スポンサー計画は79%までの改善前提で"
                         "ストレッチ（p.20）のため★。")),
        dict(id="new_members", parent="member", label="新規獲得会員数", origin="model",
             star=True, formula=None, value_text=f"FY26実績 {_d26['new']:,}人", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['new'][0]}",
                         "新規獲得会員数（人）: 69,000",
                         "広告CPAが3年で約15,000→19,000円に上昇（事業DD p.14）しており、"
                         "獲得効率の悪化が計画未達の主要リスクのため★。")),
        dict(id="freq", parent="ec_rev", label="年間平均購入回数", origin="model",
             star=False, formula=None, value_text=f"FY26実績 {_d26['freq']}回", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['freq'][0]}",
                         "年間平均購入回数（回）: 2.60",
                         "EC売上数式の第2変数。")),
        dict(id="aov", parent="ec_rev", label="平均注文単価（AOV）", origin="model",
             star=False, formula=None, value_text=f"FY26実績 {_d26['aov']:,}円", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['aov'][0]}",
                         "平均注文単価（AOV・円）: 6,650",
                         "EC売上数式の第3変数。")),
        dict(id="ws_rev", parent="revenue", label="卸売上", origin="model", star=False,
             formula="卸取扱店舗数 × 店舗あたり年間出荷額",
             value_text=f"FY26実績 {_pl_b['FY26']['ws_rev']:,}百万円", badge=None,
             evidence=ev(f"PL!{c27}{P['ws_rev'][0]}",
                         f"=ROUND(inp!{c27}{D['doors'][0]}*inp!{c27}{D['perdoor'][0]}/1000,0)",
                         "PL8行の数式がinpシートの店舗数×店販を参照。")),
        dict(id="doors", parent="ws_rev", label="卸取扱店舗数", origin="model", star=True,
             formula=None, value_text=f"FY26実績 {_d26['doors']:,}店", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['doors'][0]}",
                         "卸取扱店舗数（店）: 4,150",
                         "上位3チェーン依存45%（事業DD p.18）のため、棚割り縮小が"
                         "店舗数・物量に直結する構造であり★。")),
        dict(id="perdoor", parent="ws_rev", label="店舗あたり年間出荷額", origin="model",
             star=False, formula=None, value_text=f"FY26実績 {_d26['perdoor']:,}千円",
             badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['perdoor'][0]}",
                         "店舗あたり年間出荷額（千円）: 1,010",
                         "卸売上数式の第2変数。")),
        dict(id="other_rev", parent="revenue", label="その他売上（百貨店・海外）",
             origin="model", star=False, formula=None,
             value_text=f"FY26実績 {_pl_b['FY26']['other_revenue']:,}百万円", badge=None,
             evidence=ev(f"PL!{c27}{P['other_revenue'][0]}",
                         "その他売上（百貨店・海外）: 1,130",
                         "PL9行。計画年も直接入力値（数式なし）。")),
        dict(id="cogs", parent=None, label="売上原価", origin="model", star=False,
             formula="売上収益 × 売上原価率",
             value_text=f"FY26実績 {_pl_b['FY26']['cogs']:,}百万円", badge=None,
             evidence=ev(f"PL!{c27}{P['cogs'][0]}",
                         f"=ROUND({c27}{P['revenue'][0]}*inp!{c27}{D['cogs_rate'][0]},0)",
                         "PL12行の数式がinpシートの原価率を参照。")),
        dict(id="cogs_rate", parent="cogs", label="売上原価率", origin="model", star=True,
             formula=None, value_text=f"FY26実績 {_d26['cogs_rate']:.1%}", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['cogs_rate'][0]}",
                         "売上原価率（対売上）: 0.41",
                         "OEM依存58%（事業DD p.17）のもとで値上げ転嫁を受けやすく、"
                         "原価率+1ptでEBITDA約▲95百万円（財務DD p.13）のため★。")),
        dict(id="ad", parent=None, label="広告宣伝費", origin="model", star=False,
             formula="売上収益 × 広告宣伝費率",
             value_text=f"FY26実績 {_pl_b['FY26']['ad']:,}百万円", badge=None,
             evidence=ev(f"PL!{c27}{P['ad'][0]}",
                         f"=ROUND({c27}{P['revenue'][0]}*inp!{c27}{D['ad_rate'][0]},0)",
                         "PL16行の数式がinpシートの広宣費率を参照。")),
        dict(id="ad_rate", parent="ad", label="広告宣伝費率", origin="model", star=False,
             formula=None, value_text=f"FY26実績 {_d26['ad_rate']:.1%}", badge=None,
             evidence=ev(f"inp!{spec.COL['FY26']}{D['ad_rate'][0]}",
                         "広告宣伝費率（対売上）: 0.18",
                         "広告宣伝費数式の変数。新規獲得の約6割が広告経由（財務DD p.14）。")),
        dict(id="oem_dependency", parent="cogs", label="OEM委託先依存度",
             origin="dd", star=False, formula=None, value_text="最大委託先 58%",
             badge="モデル外・定性",
             evidence=dict(file=F_BIZ, location="p.17（6.2 最大委託先への生産依存）",
                           quote="最大委託先である三双化学工業への生産依存度は58%"
                                 "（2026年3月期・仕入高ベース）。",
                           logic="モデル数式には存在しないが、原価率の背後にある"
                                 "リスク構造として事業DDから補完（モデル外・定性）。")),
        dict(id="chain_concentration", parent="ws_rev", label="卸チェーン集中度",
             origin="dd", star=False, formula=None,
             value_text="上位3チェーン 45%（最大手21%）", badge="モデル外・定性",
             evidence=dict(file=F_BIZ, location="p.18（6.3 販売面：卸チェーンへの集中）",
                           quote="卸売上の上位3チェーンへの売上依存度は45%"
                                 "（うち最大手マツヤドラッグ21%）",
                           logic="店舗数・店販の背後にある集中リスクとして"
                                 "事業DDから補完（モデル外・定性）。")),
    ]
    return dict(nodes=nodes)


# ---------------------------------------------------------------- scenarios

def build_scenarios() -> list[dict]:
    fy27 = _pl_b["FY27"]
    return [
        dict(
            key="A", origin="ai", type_label="トップライン",
            title="リピート率低下＋大口卸チェーンの棚割り縮小",
            cause=(
                "広告獲得競争の激化とブランド鮮度の低下によりEC定期会員のリピート率が"
                "76%から73%へ低下し、同時期に最大手チェーン（卸売上内構成比21%）が"
                "PBシフトで棚割りを2割縮小する複合シナリオ。"),
            affected_kpis=["repeat", "member", "doors"],
            change_text="リピート率 76%→73%（▲3pt）・卸取扱店舗数▲8%（棚割り縮小）",
            change_basis=(
                "リピート率1pt低下でEC売上▲約50百万円（事業DD p.15）。上位3チェーン"
                "依存45%・最大手21%（事業DD p.18）。同業D2Cのリピート率レンジ60〜70%"
                "への回帰を保守側の想定として採用。"),
            impact=(
                f"売上は年▲300百万円規模、EBITDAはFY27ベース{fy27['ebitda']:,}百万円から"
                "1,030百万円前後へ低下すると推定。FCFは590百万円→440百万円前後となり、"
                f"年間元利返済（約{_DEBT_SVC_Y1:,}百万円＝約定弁済480＋利息約105）に対し"
                "DSCRはYear 1〜2で0.8倍前後まで低下、期首現金240百万円を取り崩す構図。"
                "現預金はFY28末に100百万円を下回る可能性（AI推定・モデル再計算なし）。"),
            safeguards=(
                "①約定弁済スケジュールの後倒し（当初2年の元本据置）またはキャッシュ"
                "スイープ併用への変更、②リピート率・チェーン別売上を月次モニタリング"
                "コベナンツに設定、③エクイティキュア条項。"),
            questions=(
                "①最大手チェーンとの直近の商談状況と棚割りコミットの見込み、"
                "②解約率上昇時のリテンション施策（定期便の周期変更・休眠復帰）の"
                "実績効果、③広告費を維持したままリピート率が3pt低下した場合の"
                "スポンサーの追加出資意向。"),
        ),
        dict(
            key="B", origin="ai", type_label="コスト",
            title="OEM値上げによる原価率上昇と広告CPA高騰の併発",
            cause=(
                "原材料・資材価格の高騰を受け、生産依存度58%の最大委託先・三双化学工業"
                "からの値上げ要請（転嫁条項なし・都度協議）を受入れ、売上原価率が"
                "41%から43%へ上昇。加えてデジタル広告のCPA上昇が継続する。"),
            affected_kpis=["cogs_rate", "ad_rate"],
            change_text="売上原価率 41%→43%（＋2pt）・広告宣伝費率 18%→19%（＋1pt）",
            change_basis=(
                "OEM依存58%と過去3年累計+4%の値上げ実績（事業DD p.17・財務DD p.13）。"
                "原価率+1ptでEBITDA約▲95百万円（財務DD p.13）。業界のCPAは過去3年で"
                "2〜3割上昇（事業DD p.10）。"),
            impact=(
                "EBITDAは年▲280百万円前後（原価率＋2ptで▲190、広宣費率＋1ptで▲95）と"
                "推定され、FY27ベースでEBITDA約900百万円まで低下。レバレッジ"
                "（ネットデット/EBITDA）は当初4.0x想定から5.0x超へ上昇し、FY29時点でも"
                "4.5x前後で高止まりすると推定。FCFは300百万円台まで細り、DSCRは0.6倍"
                "前後まで低下し得る（AI推定・モデル再計算なし）。"),
            safeguards=(
                "①セカンドソース化（共立コスメティックスへの処方移管）の完遂を"
                "誓約事項に設定、②OEM契約更改時の価格改定条項（転嫁ルール）の獲得、"
                "③レバレッジ・コベナンツ（例：4.5x超で配当制限）。"),
            questions=(
                "①三双化学工業との値上げ交渉の現状と2026年度の要請有無、"
                "②セカンドソース化の進捗（処方移管・安定性試験の完了時期）、"
                "③広告費率を維持したまま新規獲得数を確保できるオーガニック比率の実績。"),
        ),
        dict(
            key="C", origin="ai", type_label="イベント",
            title="OEM契約のCOC同意未取得による供給停止",
            cause=(
                "本件株式譲渡に伴うチェンジ・オブ・コントロール条項（主要OEM委託契約2件・"
                "事前書面同意）について同意が得られず、最大委託先が契約を解除。"
                "主力3カテゴリ（美容液・化粧水・クリーム）の供給が停止する。"),
            affected_kpis=["cogs", "member", "revenue"],
            change_text="主力3カテゴリ（仕入構成比58%相当）の供給が約3ヶ月停止",
            change_basis=(
                "COC条項2件（法務DD p.8：三双化学工業は違反時無催告解除可）。"
                "代替委託先の認定には12〜18ヶ月（事業DD p.17）を要し、在庫は"
                "出荷2.8〜3.4ヶ月分（財務DD p.16）しかない。"),
            impact=(
                "在庫払底後、四半期売上の約6割（約1,400百万円）が喪失し、粗利ベースで"
                "約800百万円の逸失と推定。期首現金240百万円は固定費・仕入決済で数ヶ月内に"
                "枯渇し、DSCRは1.0倍を大幅に割り込む。欠品による定期会員の解約増"
                "（リピート率への二次影響）で回復にも1年超を要する可能性"
                "（AI推定・モデル再計算なし）。"),
            safeguards=(
                "①両OEM社のCOC同意取得をクロージング条件（CP）として明記（法務DD提言"
                "どおり）、②同意取得までクロージングを延期できるロングストップ設定、"
                "③戦略在庫の積み増し（クロージング前に1ヶ月分）を売主に要請。"),
            questions=(
                "①三双化学工業・共立コスメティックスとの同意取得の交渉状況と見込み時期、"
                "②同意の条件として取引条件の変更（値上げ・最低発注量）を求められる"
                "可能性、③不同意時のクロージング延期・解除に関するSPA上の取扱い。"),
        ),
    ]


# ---------------------------------------------------------------- 採点レポート生成

def build_report() -> str:
    import run_ai_test as rat
    results = dict(
        identify=rat.score_identify(json.loads(
            (OUT / "reference_identify.json").read_text(encoding="utf-8"))),
        deal_info=rat.score_deal_info(json.loads(
            (OUT / "reference_deal_info.json").read_text(encoding="utf-8"))),
        items=rat.score_items(json.loads(
            (OUT / "reference_items.json").read_text(encoding="utf-8"))),
        kpi_tree=rat.score_kpi_tree(json.loads(
            (OUT / "reference_kpi_tree.json").read_text(encoding="utf-8"))),
        scenarios=rat.score_scenarios(json.loads(
            (OUT / "reference_scenarios.json").read_text(encoding="utf-8"))),
    )
    header = (
        "<!-- これは模範解答（reference_output/reference_*.json）を採点した場合の\n"
        "レポート。実AIの出力が正しければ、report.md はこれと同水準になる。 -->\n\n")
    return header + rat.build_report(results), results


def main():
    OUT.mkdir(exist_ok=True)
    outputs = {
        "reference_identify.json": build_identify(),
        "reference_deal_info.json": build_deal_info(),
        "reference_items.json": build_items(),
        "reference_kpi_tree.json": build_kpi_tree(),
        "reference_scenarios.json": build_scenarios(),
    }
    for name, obj in outputs.items():
        (OUT / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"generated: reference_output/{name}")
    report, results = build_report()
    (OUT / "report.md").write_text(report, encoding="utf-8")
    print("generated: reference_output/report.md")
    # 模範解答は必ず合格ラインを満たすこと（満たさない場合は生成失敗として扱う）
    assert results["items"]["passed"], "模範解答が合格ラインを満たしていない"
    assert results["identify"]["ok"] == results["identify"]["total"]
    assert results["deal_info"]["ok"] == results["deal_info"]["total"]
    print("reference scored: 合格（値100%・根拠100%）")


if __name__ == "__main__":
    main()
