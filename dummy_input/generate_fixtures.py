# -*- coding: utf-8 -*-
"""mockモード用フィクスチャ（backend/app/fixtures/）と GROUND_TRUTH.md の生成。

すべての数値・参照は spec.py / xl_layout.py から導出するため、
Excel・PDF・フィクスチャ・GROUND_TRUTH の整合が構成的に保証される。
"""
import json
from pathlib import Path

import spec
import xl_layout as L
from spec import ACTUAL_YEARS, PLAN_YEARS, to_mm

OUT_FIXTURES = Path(__file__).parent.parent / "backend" / "app" / "fixtures"
OUT_GT = Path(__file__).parent / "GROUND_TRUTH.md"

BASE_XLSX = spec.MODEL_FILES["base"]
SPONSOR_XLSX = spec.MODEL_FILES["sponsor"]
DD = {k: spec.DD_FILES[k] for k in spec.DD_FILES}


def _mm_series(values: dict, years) -> dict:
    return {y: to_mm(values[y]) for y in years}


def _fmt_series(pl_key_values: dict, years) -> str:
    return " / ".join(f"{to_mm(pl_key_values[y]):,}" for y in years)


# ---------------------------------------------------------------- 抽出項目（数値確定タブ）

def build_extraction() -> dict:
    pl_b = spec.compute_pl("base")
    pl_s = spec.compute_pl("sponsor")
    bs_b, cf_b = spec.compute_bs_cf("base")
    _, cf_s = spec.compute_bs_cf("sponsor")
    facts = {f["id"]: f for f in spec.DD_KEY_FACTS}

    items = []

    def add(key, section, label, *, unit="百万円", case=None, values=None, text_value=None,
            required=True, evidence=None, mismatch=None):
        items.append(dict(
            key=key, section=section, label=label, unit=unit, case=case,
            values=values, text_value=text_value, required=required,
            evidence=evidence, mismatch=mismatch,
        ))

    # ---- 前提・定性情報
    sec = "前提・定性情報"
    add("business_summary", sec, "事業要約", unit="テキスト",
        text_value=("自動車製造派遣の東海地場大手。在籍登録スタッフ約3,800名、稼働率88%と"
                    "業界高水準。寮・送迎インフラと自動車工程ノウハウが競争優位。"
                    "創業者の事業承継を背景としたスポンサー主導のLBO。"),
        evidence=dict(
            file=DD["business"], location="p.4〜5（1. エグゼクティブサマリー）",
            quote="東海地区において、自動車完成車メーカーおよび部品メーカー向けの製造派遣・"
                  "製造請負を主力事業とする人材サービス会社である。",
            logic="事業DDのエグゼクティブサマリーから事業内容・競争優位・案件背景を要約。"))
    add("risk_concentration", sec, "主要リスク①：顧客集中", unit="テキスト",
        text_value="上位3社への売上依存度62%（うち最大手A社28%）。A社は内製化・工程再編を検討中。",
        evidence=dict(
            file=DD["business"], location=f"p.{facts['customer_concentration']['page']}（6.2 顧客集中度）",
            quote=facts["customer_concentration"]["text"] + "に達しており、特定顧客の生産動向・"
                  "調達方針変更が業績に与える影響は大きい。",
            logic="発見事項6-2の記載を主要リスクとして採用。最大手A社の基本契約残存2年も併記。"))
    add("risk_overtime", sec, "主要リスク②：未払残業代", unit="テキスト",
        text_value="固定残業代制度の運用不備により、未払残業代の潜在債務は最大300百万円（3億円）。",
        evidence=dict(
            file=DD["legal"], location=f"p.{facts['overtime_liability']['page']}（4.3 未払残業代に係る潜在債務）",
            quote="未払残業代に係る潜在債務は、賃金請求権の消滅時効（3年）の範囲で"
                  "最大300百万円（3億円）と試算される。",
            logic="法務DDの重要指摘事項。買収契約での特別補償・エスクローによる手当てが推奨されている。"))
    add("risk_recruiting", sec, "主要リスク③：採用競争の激化", unit="テキスト", required=False,
        text_value="採用単価CPAが225→250千円（FY24→FY26）と年率5%超で上昇。計画達成の主要コストリスク。",
        evidence=dict(
            file=DD["business"], location="p.16（5.3 採用とスタッフ定着）",
            quote="採用単価（CPA：採用費÷採用人数）はFY24の225千円からFY26には250千円へと"
                  "年率5%超のペースで上昇しており、採用市場の競争激化が今後の計画達成における"
                  "主要なコスト上振れリスクである。",
            logic="事業DDのKPI分析から、計画期間のコスト上振れ要因として抽出。"))
    add("normalized_ebitda", sec, "正常収益力EBITDA（FY26）",
        values={"FY26": 1620},
        evidence=dict(
            file=DD["financial"], location=f"p.{facts['normalized_ebitda']['page']}（8.2 結論：正常収益力EBITDA）",
            quote="FY26（2026年3月期）における正常収益力ベースのEBITDAは1,620百万円（16.2億円）と評価する。",
            logic="財務DDの結論数値。モデルFY26実績EBITDA（1,620百万円）と一致することを確認済み。"))

    # ---- 実績（過去3期）
    sec = "実績（FY24〜FY26）"
    P = L.PL_ROWS

    def model_ev(row_key, sheet="PL", label_key=None):
        rows = {"PL": L.PL_ROWS, "BS": L.BS_ROWS, "CF": L.CF_ROWS}[sheet]
        label = rows[row_key][1]
        return dict(
            file=BASE_XLSX,
            location=f"{sheet}シート {L.cell_range(sheet, row_key, 'FY24', 'FY26').split('!')[1]}"
                     f"（{rows[row_key][0]}行・FY24〜FY26列）",
            quote=None,  # 呼び出し側で組み立て
            logic=f"行ラベル『{label}』を標準項目にマッピング。"
                  "シート冒頭の単位注記（単位：千円）に基づき百万円へ換算。")

    ev = model_ev("revenue")
    ev["quote"] = f"売上高（Net Sales）　{_fmt_series({y: pl_b[y]['revenue'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    ev["logic"] = ("行ラベル『売上高（Net Sales）』を『売上高』にマッピング。単位注記（千円）に基づき百万円へ換算。"
                   "財務DD p.4 財務ハイライトの売上高とも一致。")
    add("act_revenue", sec, "売上高", values=_mm_series({y: pl_b[y]["revenue"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("op")
    ev["quote"] = f"営業利益（Operating Profit）　{_fmt_series({y: pl_b[y]['op'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    add("act_op", sec, "営業利益", values=_mm_series({y: pl_b[y]["op"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("ebitda")
    ev["quote"] = f"Adj. EBITDA　{_fmt_series({y: pl_b[y]['ebitda'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    ev["logic"] = ("行ラベル『Adj. EBITDA』を『EBITDA』にマッピング。営業利益＋減価償却費の構造を"
                   "シート数式から確認。財務DD p.34 の正常収益力EBITDA（FY26: 1,620百万円）と一致。")
    add("act_ebitda", sec, "EBITDA", values=_mm_series({y: pl_b[y]["ebitda"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("ni")
    ev["quote"] = f"当期純利益　{_fmt_series({y: pl_b[y]['ni'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    add("act_ni", sec, "当期純利益", required=False,
        values=_mm_series({y: pl_b[y]["ni"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("cash", "BS")
    ev["quote"] = f"現金及び預金　{_fmt_series({y: bs_b[y]['cash'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    add("act_cash", sec, "現預金", values=_mm_series({y: bs_b[y]["cash"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("net_assets", "BS")
    ev["quote"] = f"純資産（Net Assets）　{_fmt_series({y: bs_b[y]['net_assets'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    add("act_net_assets", sec, "純資産", values=_mm_series({y: bs_b[y]["net_assets"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("debt", "BS")
    ev["quote"] = f"有利子負債　{_fmt_series({y: bs_b[y]['debt'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    ev["logic"] += "クロージング時に全額返済予定（財務DD p.25）。"
    add("act_debt", sec, "有利子負債", values=_mm_series({y: bs_b[y]["debt"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    ev = model_ev("fcf", "CF")
    ev["quote"] = f"フリー・キャッシュフロー（FCF）　{_fmt_series({y: cf_b[y]['fcf'] for y in ACTUAL_YEARS}, ACTUAL_YEARS)}（百万円換算）"
    add("act_fcf", sec, "フリー・キャッシュフロー", required=False,
        values=_mm_series({y: cf_b[y]["fcf"] for y in ACTUAL_YEARS}, ACTUAL_YEARS), evidence=ev)

    # ---- 計画（ベース／スポンサー）
    for case, pl_c, cf_c, xlsx, sec in (
        ("base", pl_b, cf_b, BASE_XLSX, "計画：ベースケース（FY27〜FY31）"),
        ("sponsor", pl_s, cf_s, SPONSOR_XLSX, "計画：スポンサーケース（FY27〜FY31）"),
    ):
        case_ja = spec.CASE_LABEL_JA[case]
        for row_key, label, req in (
            ("revenue", "売上高", True), ("op", "営業利益", True),
            ("ebitda", "EBITDA", True), ("fcf", "フリー・キャッシュフロー", case == "base"),
        ):
            sheet = "CF" if row_key == "fcf" else "PL"
            rows = L.CF_ROWS if sheet == "CF" else L.PL_ROWS
            src = cf_c if row_key == "fcf" else pl_c
            ev = dict(
                file=xlsx,
                location=f"{sheet}シート {L.cell_range(sheet, row_key, 'FY27', 'FY31').split('!')[1]}"
                         f"（{rows[row_key][0]}行・FY27〜FY31列）",
                quote=f"{rows[row_key][1]}　{_fmt_series({y: src[y][row_key] for y in PLAN_YEARS}, PLAN_YEARS)}（百万円換算）",
                logic=(f"Assumptionsシートのケース表記『{spec.CASE_LABEL[case]}』により{case_ja}と判定。"
                       f"行ラベル『{rows[row_key][1]}』を標準項目にマッピングし、単位注記（千円）に基づき百万円へ換算。"))
            add(f"{case}_{row_key}", sec, label, case=case, required=req,
                values=_mm_series({y: src[y][row_key] for y in PLAN_YEARS}, PLAN_YEARS), evidence=ev)

    # ---- ストラクチャー・B/S項目
    sec = "ストラクチャー・B/S項目"
    gw = facts["goodwill_dd"]
    add("goodwill", sec, "のれん（買収想定額）", values={"FY27": to_mm(spec.GOODWILL)},
        evidence=dict(
            file=BASE_XLSX,
            location=f"BSシート {spec.COL['FY27']}{L.BS_ROWS['goodwill'][0]}（FY27列）"
                     "／Assumptionsシート D21",
            quote=f"のれん（Goodwill）　{spec.GOODWILL:,}（千円）＝{to_mm(spec.GOODWILL):,}百万円",
            logic="モデルBSのFY27以降に計上されたのれん想定額（暫定PPA前）。"),
        mismatch=dict(
            other_value=to_mm(spec.GOODWILL_DD),
            other_file=DD["financial"],
            other_location=f"p.{gw['page']}（7.2 のれん想定額の試算）",
            other_quote="当法人の試算によるのれん想定額は5,280百万円である。スポンサー提出の"
                        "財務モデルにはのれん5,500百万円が計上されており、220百万円の差異がある。",
            note="モデル（5,500）と財務DD（5,280）で220百万円の差異。取引費用の取扱い・"
                 "無形資産評価の前提差。最終PPAで確定予定。どちらを採用するか選択が必要。"))
    add("ev", sec, "エンタープライズ・バリュー（EV）", values={"FY27": spec.DEAL["ev_mm"]},
        evidence=dict(
            file=BASE_XLSX, location="Assumptionsシート D8",
            quote="エンタープライズ・バリュー（EV）　12,000,000（千円）",
            logic="Assumptionsシートのストラクチャー前提から取得。財務DD p.30の記載とも一致。"))
    add("senior_loan", sec, "シニアローン総額", values={"FY27": spec.DEAL["senior_mm"]},
        evidence=dict(
            file=BASE_XLSX, location="Assumptionsシート D10／Debt_Scheduleシート F7",
            quote="シニアローン総額　6,500,000（千円）／期間7年・年650,000千円約定弁済",
            logic="Assumptionsシートおよびデットスケジュールから取得。案件登録情報と一致。"))

    return dict(
        deal_key="autostaff",
        company="株式会社オートスタッフ中部",
        items=items,
    )


# ---------------------------------------------------------------- KPIツリー

def build_kpi_tree() -> dict:
    d = spec.drivers("base")["FY26"]
    pl = spec.compute_pl("base")["FY26"]
    K = L.KPI_ROWS

    def kev(row_key, extra=""):
        return dict(
            file=BASE_XLSX,
            location=f"KPI_Driversシート {L.cell_range('KPI_Drivers', row_key, 'FY24', 'FY31').split('!')[1]}",
            quote=f"{K[row_key][1]}",
            logic=("PLシートの計画年数式（FY27列以降）を構文解析し、"
                   f"KPI_Driversシート{K[row_key][0]}行への参照から親子関係を判定。" + extra))

    nodes = [
        dict(id="rev", parent=None, label="売上高", origin="model", star=False,
             formula="= 派遣事業売上 + その他営業収入",
             value_text=f"{to_mm(pl['revenue']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX, location="PLシート 9行（=SUM(C7:C8)）",
                           quote="売上高（Net Sales）",
                           logic="PLシートの売上高行の数式（=SUM）から構成要素を特定。")),
        dict(id="staffing_rev", parent="rev", label="派遣事業売上", origin="model", star=False,
             formula="= 稼働人数 × 月間平均稼働時間 × 派遣単価 × 12",
             value_text=f"{to_mm(pl['staffing_rev']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX,
                           location="PLシート 7行（FY27列の数式）",
                           quote="=ROUND(KPI_Drivers!F9*KPI_Drivers!F10*KPI_Drivers!F11*12/1000,0)",
                           logic="計画年の数式を構文解析し、KPI_Driversシートの3変数（稼働人数・"
                                 "月間平均稼働時間・派遣単価）の積で構成されることを確認。")),
        dict(id="active", parent="staffing_rev", label="稼働人数", origin="model", star=False,
             formula="= 在籍登録スタッフ数 × 稼働率",
             value_text=f"{d['active']:,}名（FY26実績）",
             evidence=kev("active", "KPI_Drivers 9行の数式 =ROUND(E7*E8,0) から分解。")),
        dict(id="enrolled", parent="active", label="在籍登録スタッフ数", origin="model", star=False,
             formula=None, value_text=f"{d['enrolled']:,}名（FY26実績）",
             evidence=kev("enrolled")),
        dict(id="util", parent="active", label="稼働率", origin="model", star=True,
             formula=None, value_text=f"{d['util']:.0%}（FY26実績）",
             evidence=kev("util", "事業DD p.15でも業界水準を上回る最重要KPIとして分析されている。")),
        dict(id="hires", parent="active", label="新規採用人数", origin="model", star=False,
             formula=None, value_text=f"{d['hires']:,}名/年（FY26実績）",
             evidence=kev("hires")),
        dict(id="attrition", parent="active", label="離職率", origin="model", star=False,
             formula=None, value_text=f"{d['attrition']:.0%}/年（FY26実績）",
             evidence=kev("attrition")),
        dict(id="hours", parent="staffing_rev", label="月間平均稼働時間", origin="model", star=False,
             formula=None, value_text=f"{d['hours']}h/名（FY26実績）",
             evidence=kev("hours")),
        dict(id="bill", parent="staffing_rev", label="派遣単価", origin="model", star=True,
             formula=None, value_text=f"{d['bill']:,}円/h（FY26実績）",
             evidence=kev("bill", "毎年4月改定・過去3年平均+2.0%（事業DD p.19）。")),
        dict(id="cogs", parent=None, label="売上原価", origin="model", star=False,
             formula="= スタッフ労務費 + その他売上原価",
             value_text=f"{to_mm(pl['cogs']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX, location="PLシート 13行",
                           quote="売上原価 合計", logic="PLシートの数式（=C11+C12）から構成を特定。")),
        dict(id="labor", parent="cogs", label="スタッフ労務費", origin="model", star=False,
             formula="= 稼働人数 × 月間平均稼働時間 × スタッフ平均時給 × (1+法定福利費率) × 12",
             value_text=f"{to_mm(pl['labor']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX, location="PLシート 11行（FY27列の数式）",
                           quote="=ROUND(KPI_Drivers!F9*KPI_Drivers!F10*KPI_Drivers!F12*(1+KPI_Drivers!F13)*12/1000,0)",
                           logic="計画年の数式を構文解析。時給と法定福利費率の2変数に依存。")),
        dict(id="wage", parent="labor", label="スタッフ平均時給", origin="model", star=False,
             formula=None, value_text=f"{d['wage']:,}円/h（FY26実績）",
             evidence=kev("wage")),
        dict(id="welfare", parent="labor", label="法定福利費率", origin="model", star=False,
             formula=None, value_text=f"{d['welfare']:.0%}", evidence=kev("welfare")),
        dict(id="sga", parent=None, label="販売費及び一般管理費", origin="model", star=False,
             formula="= 採用費 + 本社人件費 + その他販管費",
             value_text=f"{to_mm(pl['sga']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX, location="PLシート 20行",
                           quote="販売費及び一般管理費 合計",
                           logic="PLシートの数式（=SUM）から構成を特定。")),
        dict(id="recruiting", parent="sga", label="採用費", origin="model", star=False,
             formula="= 新規採用人数 × 採用単価CPA",
             value_text=f"{to_mm(pl['recruiting']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX, location="PLシート 17行（FY27列の数式）",
                           quote="=KPI_Drivers!F14*KPI_Drivers!F15",
                           logic="計画年の数式を構文解析。採用人数×CPAの積。")),
        dict(id="cpa", parent="recruiting", label="採用単価CPA", origin="model", star=True,
             formula=None, value_text=f"{d['cpa']}千円/名（FY26実績）",
             evidence=kev("cpa", "事業DD p.16で年率5%超の上昇傾向が指摘されている。")),
        dict(id="hq", parent="sga", label="本社人件費（固定費）", origin="model", star=False,
             formula=None, value_text=f"{to_mm(pl['hq_cost']):,}百万円（FY26実績）",
             evidence=dict(file=BASE_XLSX, location="PLシート 18行",
                           quote="本社人件費", logic="PLシートのハードコード行（固定費）。")),
    ]
    # チャットで追加されるモデル外ノード（提案ツリーには含まれない）
    concentration_node = dict(
        id="concentration", parent="rev", label="大口派遣先への売上依存度", origin="dd",
        star=False, formula=None, value_text="上位3社62%・最大手A社28%（FY26実績）",
        badge="モデル外・定性",
        evidence=dict(file=DD["business"], location="p.18（6.2 顧客集中度）",
                      quote="上位3社への売上依存度は62%（うち最大手A社28%）",
                      logic="財務モデルの数式には存在しないが、売上高の重要なリスクドライバーで"
                            "あるため事業DDの定性情報からモデル外KPIとして追加。"))
    return dict(nodes=nodes, concentration_node=concentration_node,
                star_summary="★＝重要KPI（リスクドライバー）：稼働率・派遣単価・採用単価CPA")


# ---------------------------------------------------------------- シナリオカード

def build_scenarios() -> dict:
    cards = [
        dict(
            key="A", origin="ai", type_label="トップライン",
            title="トップライン悪化（稼働率低下・採用未達）",
            cause="景気後退による自動車減産。派遣契約は30日前通知で解約可能なため、"
                  "顧客の生産調整が短期間で稼働率低下に直結する（2009年に売上約4割減の先例）。",
            affected_kpis=["util", "hires"],
            change="稼働率 88%→75%（相対▲15%）、新規採用人数 ▲20%（1,220→976名）",
            change_basis="リーマンショック時の製造派遣稼働率下落幅（業界平均▲14〜18%・外部データ）"
                         "および事業DD p.19の需要調整弁構造の分析",
            impact="FY28（Year 2）にEBITDAが約1,100百万円まで低下し、約定弁済650百万円＋"
                   "支払利息約122百万円に対しDSCRは0.9倍前後まで低下すると推定。"
                   "Net Debt/EBITDAは約4.6xへ上昇。",
            safeguards="キャッシュスイープ条項、DSCRコベナンツ（1.05x）の設定、"
                       "スポンサーのエクイティサポートレター",
            questions="大口3社の契約更改時期と更改条件／採用チャネル別の依存度と代替可能性",
            adopted=True,
        ),
        dict(
            key="B", origin="ai", type_label="コスト",
            title="コスト上昇（採用単価・時給の上振れ）",
            cause="採用市場の競争激化と最低賃金改定の加速。単価転嫁には最大6ヶ月の遅れがあり"
                  "（事業DD p.19）、コスト上昇局面ではスプレッドが一時的に縮小する。",
            affected_kpis=["cpa", "wage"],
            change="採用単価CPA +30%（255→332千円）、スタッフ平均時給 +5%（転嫁は半年遅れ）",
            change_basis="採用CPAの実績上昇率（年5%超・事業DD p.16）のストレス倍率、"
                         "最低賃金の直近改定率（+5.0%）",
            impact="転嫁ラグにより粗利率が約1.5pt悪化。FY29以降のNet Debt/EBITDAが"
                   "5.0x超（4.1x→5.2x）に上昇すると推定。EBITDAはベース比▲約280百万円/年。",
            safeguards="レバレッジ・コベナンツの設定、単価改定条項の顧客契約への織込み状況の確認",
            questions="顧客との単価改定サイクルの実効性／最低賃金改定の自動転嫁条項の有無",
            adopted=True,
        ),
        dict(
            key="C", origin="ai", type_label="イベント",
            title="偶発債務の顕在化（未払残業代の特別損失）",
            cause="法務DDで指摘された未払残業代の潜在債務（拠点コーディネーター職の"
                  "固定残業代運用不備）が、退職者からの請求等によりYear 1に顕在化する。",
            affected_kpis=[],
            change="FY27に特別損失300百万円（最大想定額）を一括計上",
            change_basis="法務DD p.12の試算最大値（消滅時効3年分の保守的外挿）",
            impact="FY27の税前利益を300百万円押し下げ、期末現預金は約1,460→約1,160百万円へ。"
                   "月間給与支払約900百万円に対する手元流動性が薄くなり、"
                   "翌期の約定弁済650百万円を考慮すると現預金枯渇リスクがあると推定。",
            safeguards="表明保証・特別補償（Specific Indemnity）の設定",
            questions="対象期間・対象者範囲の確定状況／和解方針と概算スケジュール",
            adopted=False,
            rejection_note="特別補償＋エスクローでのカバーを前提に現時点では不採用（7/5審査相談で整理）",
        ),
    ]
    human_card = dict(
        key="D", origin="human", type_label="自分の仮説",
        title="大口派遣先（構成比28%）の契約終了",
        cause="最大手A社（売上構成比28%）が電動化に伴う工程再編・内製化により、"
              "基本契約満了（残存2年）を機に派遣契約を段階的に終了する。",
        affected_kpis=["active", "util", "concentration"],
        change="FY28期首よりA社向け売上（構成比28%）が消失、スタッフ再配置率60%と仮定",
        change_basis="事業DD p.18（A社の内製化・工程再編の検討）、法務DD p.7"
                     "（A社基本契約のチェンジ・オブ・コントロール条項）",
        impact="FY28売上▲約1,670百万円（▲11%）、EBITDA▲約400百万円→約1,350百万円と推定。"
               "DSCRは1.1倍近傍まで低下。再配置率が40%まで悪化した場合はDSCR1.0倍割れリスク。",
        safeguards="A社との中期契約化の交渉、クロージング前のA社への事前説明（CoC条項対応）、"
                   "キャッシュスイープ条項",
        questions="A社の内製化計画の具体的スケジュール／再配置可能な代替顧客の需要見込み",
        adopted=True,
    )
    return dict(cards=cards, human_card=human_card,
                ai_note="インパクト数値はAIによる定性推定であり、財務モデルの再計算値ではありません。")


# ---------------------------------------------------------------- チャット台本

def build_chat_scripts(kpi_tree: dict, scenarios: dict) -> dict:
    return dict(
        kpi=dict(
            suggestions=[
                "大口派遣先への売上依存度をKPIに追加して",
                "重要KPIの★を稼働率から採用単価CPAに変更して",
            ],
            scripts=[
                dict(id="add_concentration",
                     triggers=["大口", "依存度", "集中"],
                     reply="事業DDレポート p.18 で指摘されている顧客集中"
                           "（上位3社62%・うち最大手A社28%）を、売上高配下のKPIとして追加します。"
                           "財務モデルの数式には存在しない項目のため「モデル外・定性」バッジを付与します。"
                           "以下の差分を確認して適用してください。",
                     diff=dict(type="add_node", node=kpi_tree["concentration_node"])),
                dict(id="move_star",
                     triggers=["★", "スター", "重要KPI"],
                     reply="重要KPI（★）を「稼働率」から「採用単価CPA」へ変更します。"
                           "稼働率は引き続きツリーに残ります（★のみ外れます）。"
                           "以下の差分を確認して適用してください。",
                     diff=dict(type="star_change", remove=["util"], add=["cpa"])),
            ],
            fallback="（デモモード）このリクエストに対応する修正シナリオが登録されていません。"
                     "入力欄のプレースホルダーに表示されている候補フレーズをお試しください。",
        ),
        scenario=dict(
            suggestions=[
                "大口派遣先（構成比28%）が契約終了したら",
                "シナリオAで稼働率▲18%のケースも見たい",
                "シナリオCの保全策にエスクローを追加して",
            ],
            scripts=[
                dict(id="human_scenario",
                     triggers=["大口", "契約終了", "撤退"],
                     reply="「大口派遣先の契約終了」を標準5部構成のシナリオに展開しました。"
                           "根拠として事業DD p.18（顧客集中62%・A社28%）と法務DD p.7"
                           "（A社基本契約の支配権変動条項）を紐付けています。"
                           "内容を確認のうえ適用してください。",
                     diff=dict(type="add_card", card=scenarios["human_card"])),
                dict(id="deeper_stress",
                     triggers=["18%", "▲18", "-18"],
                     applies_to="A",
                     reply="シナリオAのストレス幅を稼働率▲15%から▲18%へ深掘りします。"
                           "変化幅と返済能力への影響（AI推定）を更新します。差分を確認してください。",
                     diff=dict(type="update_card", card_key="A", fields=dict(
                         change="稼働率 88%→72%（相対▲18%）、新規採用人数 ▲20%（1,220→976名）",
                         impact="FY28（Year 2）にEBITDAが約950百万円まで低下し、"
                                "DSCRは0.8倍前後まで低下すると推定。約定弁済の一部リスケジュール"
                                "またはエクイティサポートの発動が必要な水準。"))),
                dict(id="add_escrow",
                     triggers=["エスクロー"],
                     applies_to="C",
                     reply="シナリオCの保全策にエスクローの設定を追加します。"
                           "法務DD p.14 の提言（150〜300百万円・期間3年）を反映します。"
                           "差分を確認してください。",
                     diff=dict(type="update_card", card_key="C", fields=dict(
                         safeguards="表明保証・特別補償（Specific Indemnity）の設定に加え、"
                                    "エスクロー（150〜300百万円・期間3年）の設定"))),
            ],
            fallback="（デモモード）このリクエストに対応する修正シナリオが登録されていません。"
                     "入力欄のプレースホルダーに表示されている候補フレーズをお試しください。",
        ),
    )


# ---------------------------------------------------------------- 案件基本情報の自動抽出

def build_deal_info() -> dict:
    """案件登録（S2）の自動抽出：アップロード資料から基本情報を読み取る（値の拾い上げのみ）。"""
    return dict(
        fields=dict(
            name=spec.DEAL["name"],
            deal_type=spec.DEAL["deal_type"],
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
            summary=spec.DEAL["summary"],
        ),
        sources=dict(
            name="対象会社名＋案件スキームから自動生成",
            deal_type="財務DDレポート p.30（LBOストラクチャーの概要）",
            borrower="財務DDレポート p.30（SPC：株式会社ASホールディングス）",
            target="財務モデル Coverシート／各DDレポート表紙",
            industry="事業DDレポート p.4（1.1 対象会社の概要）",
            sponsor="財務モデル Coverシート（作成者）",
            close_date="Assumptionsシート（クローズ想定：2026年9月末）",
            ev_mm="Assumptionsシート D8",
            senior_mm="Assumptionsシート D10／Debt_Scheduleシート",
            equity_mm="Assumptionsシート D9",
            tenor_years="Assumptionsシート D12",
            sponsor_ebitda_mm="Assumptionsシート D23（スポンサー提示・ティーザー速報値）",
            summary="事業DDレポート p.4〜5（エグゼクティブサマリー）から要約",
        ),
        note="本行取組額・担当者・審査相談予定日は行内情報のため自動抽出の対象外です。"
             "内容を確認・修正のうえ登録を確定してください。",
    )


# ---------------------------------------------------------------- ファイル識別（案件照合）

def build_identify() -> dict:
    company = "株式会社オートスタッフ中部"
    files = {
        spec.MODEL_FILES["sponsor"]: dict(
            company=company, doc_type="model_sponsor",
            label="財務モデル（スポンサーケース）",
            detail="Coverシートの社名・Assumptionsシートのケース表記（Sponsor Case）から判定"),
        spec.MODEL_FILES["base"]: dict(
            company=company, doc_type="model_base",
            label="財務モデル（ベースケース）",
            detail="Coverシートの社名・Assumptionsシートのケース表記（Base Case）から判定"),
        spec.DD_FILES["business"]: dict(
            company=company, doc_type="dd_business", label="事業DDレポート",
            detail="表紙の表題『事業デューデリジェンス報告書』と対象会社名から判定"),
        spec.DD_FILES["financial"]: dict(
            company=company, doc_type="dd_financial", label="財務DDレポート",
            detail="表紙の表題『財務デューデリジェンス報告書』と対象会社名から判定"),
        spec.DD_FILES["legal"]: dict(
            company=company, doc_type="dd_legal", label="法務DDレポート",
            detail="表紙の表題『法務デューデリジェンス報告書』と対象会社名から判定"),
        spec.DD_FILES["tax"]: dict(
            company=company, doc_type="dd_tax", label="税務DDレポート",
            detail="表紙の表題『税務デューデリジェンス報告書』と対象会社名から判定"),
    }
    return dict(files=files)


# ---------------------------------------------------------------- シードデータ

def build_seed(extraction, kpi_tree, scenarios) -> dict:
    deal1 = dict(
        key="autostaff",
        name=spec.DEAL["name"],
        deal_type=spec.DEAL["deal_type"],
        borrower=spec.DEAL["borrower"],
        target=spec.DEAL["target"],
        industry=spec.DEAL["industry"],
        sponsor=spec.DEAL["sponsor"],
        close_date=spec.DEAL["close_date"],
        next_meeting_date=spec.DEAL["next_meeting_date"],
        ev_mm=spec.DEAL["ev_mm"],
        senior_mm=spec.DEAL["senior_mm"],
        our_commitment_mm=spec.DEAL["our_commitment_mm"],
        equity_mm=spec.DEAL["equity_mm"],
        tenor_years=spec.DEAL["tenor_years"],
        sponsor_ebitda_mm=spec.DEAL["sponsor_ebitda_mm"],
        summary=spec.DEAL["summary"],
        owner="tanaka",
        review_status="再検討中",
        work_status="シナリオ検討中",
        updated_at="2026-07-12T15:30:00",
        created_at="2026-07-02T10:05:00",
    )
    other_deals = [
        dict(key="sunmedix", name="サンメディクス事業承継ファイナンス",
             deal_type="事業承継", borrower="株式会社SMD承継",
             target="株式会社サンメディクス", industry="医療機器卸・メンテナンス",
             sponsor="三田キャピタル株式会社", close_date="2026-11-30",
             next_meeting_date=None,
             ev_mm=9800, senior_mm=5600, our_commitment_mm=2800, equity_mm=4200,
             tenor_years=7, sponsor_ebitda_mm=1310,
             summary="医療機器卸・保守の地域大手。創業家の事業承継に伴うスポンサー買収。",
             owner="tanaka", review_status="検討中", work_status="数値確定中",
             updated_at="2026-07-10T11:20:00", created_at="2026-07-08T09:30:00"),
        dict(key="tokai_process", name="東海プロセス機器 MBOファイナンス",
             deal_type="MBO", borrower="株式会社TPKホールディングス",
             target="東海プロセス機器株式会社", industry="産業機械（化学プラント向け）",
             sponsor="経営陣（MBO）／静岡成長投資株式会社", close_date="2026-08-31",
             next_meeting_date=None,
             ev_mm=7200, senior_mm=3800, our_commitment_mm=1800, equity_mm=3400,
             tenor_years=7, sponsor_ebitda_mm=980,
             summary="化学プラント向けバルブ・計装機器メーカーのMBO。",
             owner="takahashi", review_status="推進", work_status="出力済",
             updated_at="2026-07-03T17:45:00", created_at="2026-06-12T10:00:00"),
        dict(key="hokusei", name="北勢運輸 リファイナンス",
             deal_type="リファイナンス", borrower="株式会社北勢運輸",
             target="株式会社北勢運輸", industry="貨物運送（中部地盤）",
             sponsor="－（既存株主継続）", close_date="2026-09-30",
             next_meeting_date=None,
             ev_mm=None, senior_mm=1200, our_commitment_mm=1200, equity_mm=None,
             tenor_years=5, sponsor_ebitda_mm=310,
             summary="2019年LBOの既存シニアローンのリファイナンス案件。",
             owner="takahashi", review_status="見送り", work_status="出力済",
             updated_at="2026-06-20T14:00:00", created_at="2026-06-02T13:15:00"),
    ]

    memos = [
        dict(deal_key="autostaff", meeting_date="2026-07-05",
             attendees=["田中（稟議担当）", "佐藤（部長）"],
             conclusion="続行",
             note="ストレス仮説の方向性は概ね妥当。シナリオC（未払残業代）は特別補償＋"
                  "エスクローでのカバーを前提に不採用として整理。次回までにA社依存"
                  "（構成比28%）の独自シナリオを検討すること。",
             findings=[],
             created_by="tanaka", created_at="2026-07-05T13:00:00"),
        dict(deal_key="autostaff", meeting_date="2026-07-12",
             attendees=["田中（稟議担当）", "佐藤（部長）"],
             conclusion="再検討",
             note="シナリオの深掘りが必要。下記3点を持ち帰り、再検討のうえ次回7/18に再相談。",
             findings=[
                 dict(target_type="scenario", target_key="A",
                      text="稼働率▲15%の根拠が業界平均のみ。対象会社の2009年実績"
                           "（売上約4割減）を踏まえた深掘りケース（▲18%）を検討すること。"),
                 dict(target_type="scenario", target_key="D",
                      text="A社契約終了シナリオの再配置率60%の根拠が弱い。"
                           "営業本部長ヒアリングの結果を反映すること。"),
                 dict(target_type="item", target_key="goodwill",
                      text="のれん想定額の不整合（モデル5,500 vs 財務DD5,280）の扱いを"
                           "スポンサーに確認し、採用値の根拠を明記すること。"),
             ],
             created_by="tanaka", created_at="2026-07-12T15:30:00",
             status_change=dict(from_status="検討中", to_status="再検討中")),
        dict(deal_key="tokai_process", meeting_date="2026-07-03",
             attendees=["高橋（稟議担当）", "佐藤（部長）"],
             conclusion="推進",
             note="ストレスシナリオ2件のヘッドルームを確認。正式稟議手続へ移行する。",
             findings=[], created_by="takahashi", created_at="2026-07-03T17:45:00",
             status_change=dict(from_status="検討中", to_status="推進")),
        dict(deal_key="hokusei", meeting_date="2026-06-20",
             attendees=["高橋（稟議担当）", "佐藤（部長）"],
             conclusion="見送り",
             note="足元の収益性低下傾向と再レバレッジの正当化が困難なため見送り。",
             findings=[], created_by="takahashi", created_at="2026-06-20T14:00:00",
             status_change=dict(from_status="検討中", to_status="見送り")),
    ]

    history = [
        dict(deal_key="autostaff", at="2026-07-02T10:05:00", user="tanaka",
             action="案件登録", detail="基本情報を登録"),
        dict(deal_key="autostaff", at="2026-07-02T10:07:00", user="tanaka",
             action="資料アップロード", detail="財務モデル2件・DDレポート4件をアップロード"),
        dict(deal_key="autostaff", at="2026-07-02T10:12:00", user="tanaka",
             action="AI解析完了", detail="24項目を抽出（財務モデル・DDレポート4種）"),
        dict(deal_key="autostaff", at="2026-07-03T15:40:00", user="tanaka",
             action="数値確定", detail="22項目確定・2項目保留（当期純利益／FCF実績）"),
        dict(deal_key="autostaff", at="2026-07-03T16:10:00", user="tanaka",
             action="KPI修正（チャット適用）", detail="「大口派遣先への売上依存度」をモデル外KPIとして追加"),
        dict(deal_key="autostaff", at="2026-07-04T11:00:00", user="tanaka",
             action="KPI構造確定", detail="16ノード・★3件で確定"),
        dict(deal_key="autostaff", at="2026-07-04T14:30:00", user="tanaka",
             action="シナリオ確定", detail="A・B・D採用／C不採用（特別補償前提）"),
        dict(deal_key="autostaff", at="2026-07-05T09:15:00", user="tanaka",
             action="Excel出力", detail="審査相談用サマリーを出力（保留2項目を除く）"),
        dict(deal_key="autostaff", at="2026-07-05T13:00:00", user="tanaka",
             action="審査相談メモ登録", detail="7/5 審査相談：続行"),
        dict(deal_key="autostaff", at="2026-07-12T15:30:00", user="tanaka",
             action="審査相談メモ登録", detail="7/12 審査相談：再検討（指摘3件）・ステータスを再検討中へ変更"),
    ]

    # サンメディクス（背景案件）の未確定抽出アイテム（少量）
    sunmedix_items = [
        dict(key="sm_revenue", section="実績（FY24〜FY26）", label="売上高", unit="百万円",
             case=None, values={"FY24": 9820, "FY25": 10150, "FY26": 10480},
             text_value=None, required=True,
             evidence=dict(file="SunMedix_Model_Base.xlsx",
                           location="PLシート C9:E9",
                           quote="売上高　9,820 / 10,150 / 10,480（百万円）",
                           logic="行ラベル『売上高』を標準項目にマッピング。"),
             mismatch=None),
        dict(key="sm_ebitda", section="実績（FY24〜FY26）", label="EBITDA", unit="百万円",
             case=None, values={"FY24": 1110, "FY25": 1180, "FY26": 1240},
             text_value=None, required=True,
             evidence=dict(file="SunMedix_Model_Base.xlsx",
                           location="PLシート C22:E22",
                           quote="EBITDA　1,110 / 1,180 / 1,240（百万円）",
                           logic="営業利益＋減価償却費の構造をシート数式から確認。"),
             mismatch=None),
        dict(key="sm_net_assets", section="実績（FY24〜FY26）", label="純資産", unit="百万円",
             case=None, values={"FY24": 3650, "FY25": 3980, "FY26": 4310},
             text_value=None, required=True,
             evidence=dict(file="SunMedix_Model_Base.xlsx",
                           location="BSシート C23:E23",
                           quote="純資産　3,650 / 3,980 / 4,310（百万円）",
                           logic="行ラベル『純資産』を標準項目にマッピング。"),
             mismatch=None),
        dict(key="sm_summary", section="前提・定性情報", label="事業要約", unit="テキスト",
             case=None, values=None,
             text_value="医療機器の卸売と保守サービスの地域大手。保守契約による"
                        "ストック収益が売上の約4割を占める。",
             required=True,
             evidence=dict(file="DD_Business_サンメディクス.pdf",
                           location="p.4（エグゼクティブサマリー）",
                           quote="医療機器の販売および保守サービスを主力事業とする。",
                           logic="事業DDのエグゼクティブサマリーから要約。"),
             mismatch=None),
    ]

    return dict(
        users=[
            dict(key="tanaka", name="田中", role="稟議担当"),
            dict(key="sato", name="佐藤", role="部長"),
            dict(key="takahashi", name="高橋", role="稟議担当"),
        ],
        deals=[deal1] + other_deals,
        memos=memos,
        history=history,
        sunmedix_items=sunmedix_items,
    )


# ---------------------------------------------------------------- GROUND_TRUTH.md

def build_ground_truth(extraction) -> str:
    pl_b = spec.compute_pl("base")
    pl_s = spec.compute_pl("sponsor")
    d26 = spec.drivers("base")["FY26"]
    lines = []
    w = lines.append
    w("# GROUND_TRUTH — オートスタッフ中部LBO デモデータの正本")
    w("")
    w("このファイルは `spec.py` から自動生成される（手編集禁止）。")
    w("再生成: `python generate_all.py` ／ 整合チェック: `python validate.py`")
    w("")
    w("## 1. 案件基本情報")
    w("")
    w("| 項目 | 値 |")
    w("|---|---|")
    w(f"| 案件名 | {spec.DEAL['name']} |")
    w(f"| 案件種別 | {spec.DEAL['deal_type']} |")
    w(f"| 借入人（SPC） | {spec.DEAL['borrower']} |")
    w(f"| 対象会社 | {spec.DEAL['target']}（{spec.DEAL['industry']}） |")
    w(f"| スポンサー | {spec.DEAL['sponsor']} |")
    w(f"| EV | {spec.DEAL['ev_mm']:,}百万円 |")
    w(f"| シニアローン | {spec.DEAL['senior_mm']:,}百万円（本行取組 {spec.DEAL['our_commitment_mm']:,}百万円・期間{spec.DEAL['tenor_years']}年） |")
    w(f"| エクイティ | {spec.DEAL['equity_mm']:,}百万円 |")
    w(f"| スポンサー提示EBITDA（速報） | {spec.DEAL['sponsor_ebitda_mm']:,}百万円 |")
    w(f"| 初期レバレッジ（自動算出） | {spec.DEAL['initial_leverage']}x ＝ シニア6,500 ÷ 提示EBITDA1,585 |")
    w(f"| LTV（自動算出） | {spec.DEAL['ltv_pct']}% ＝ シニア6,500 ÷ EV12,000 |")
    w("")
    w("## 2. DDレポートのキーファクト（ページ位置固定）")
    w("")
    w("| ID | ファイル | ページ | 内容 |")
    w("|---|---|---|---|")
    for f in spec.DD_KEY_FACTS:
        w(f"| {f['id']} | {spec.DD_FILES[f['file']]} | p.{f['page']} | {f['text']} |")
    w("")
    w("※ 財務DDは キーファクトのページ指定（p.34）に合わせて全36ページ構成"
      "（他は事業20p・法務14p・税務10p）。")
    w("")
    w("## 3. 財務モデルの主要数値（百万円・Excel内は千円）")
    w("")
    w("### 実績（両ケース共通）")
    w("")
    w("| 項目 | FY24 | FY25 | FY26 | 参照セル |")
    w("|---|---|---|---|---|")
    for key, label in (("revenue", "売上高"), ("op", "営業利益"), ("ebitda", "EBITDA"),
                       ("ni", "当期純利益")):
        w(f"| {label} | {to_mm(pl_b['FY24'][key]):,} | {to_mm(pl_b['FY25'][key]):,} "
          f"| {to_mm(pl_b['FY26'][key]):,} | {L.cell_range('PL', key, 'FY24', 'FY26')} |")
    w("")
    w("### 計画")
    w("")
    w("| ケース | 項目 | FY27 | FY28 | FY29 | FY30 | FY31 |")
    w("|---|---|---|---|---|---|---|")
    for case, pl_c in (("Base", pl_b), ("Sponsor", pl_s)):
        for key, label in (("revenue", "売上高"), ("ebitda", "EBITDA")):
            vals = " | ".join(f"{to_mm(pl_c[y][key]):,}" for y in PLAN_YEARS)
            w(f"| {case} | {label} | {vals} |")
    w("")
    w("### KPI（FY26実績）")
    w("")
    w("| KPI | 値 | 参照セル |")
    w("|---|---|---|")
    w(f"| 稼働率 | {d26['util']:.0%} | {L.cell('KPI_Drivers', 'util', 'FY26')} |")
    w(f"| 稼働人数 | {d26['active']:,}名 | {L.cell('KPI_Drivers', 'active', 'FY26')}（=在籍×稼働率） |")
    w(f"| 在籍登録スタッフ数 | {d26['enrolled']:,}名 | {L.cell('KPI_Drivers', 'enrolled', 'FY26')} |")
    w(f"| 派遣単価 | {d26['bill']:,}円/h | {L.cell('KPI_Drivers', 'bill', 'FY26')} |")
    w(f"| 採用単価CPA | {d26['cpa']}千円/名 | {L.cell('KPI_Drivers', 'cpa', 'FY26')} |")
    w(f"| 月間平均稼働時間 | {d26['hours']}h | {L.cell('KPI_Drivers', 'hours', 'FY26')} |")
    w("")
    w("## 4. 意図的な不整合（デモ用）")
    w("")
    w(f"- のれん想定額：モデル {to_mm(spec.GOODWILL):,}百万円（{L.cell('BS', 'goodwill', 'FY27')}・"
      f"Assumptions D21）vs 財務DD {to_mm(spec.GOODWILL_DD):,}百万円（p.31）→ 数値確定タブで不整合警告を表示")
    w("- PL_oldシート（旧版・全値0.965倍）とScratchシートはノイズであり抽出対象外")
    w("")
    w("## 5. 抽出項目一覧（mockフィクスチャと1:1対応）")
    w("")
    w("| key | セクション | 項目 | 必須 | 参照 |")
    w("|---|---|---|---|---|")
    for it in extraction["items"]:
        loc = f"{it['evidence']['file']} {it['evidence']['location']}"
        req = "必須" if it["required"] else "任意"
        w(f"| {it['key']} | {it['section']} | {it['label']} | {req} | {loc} |")
    w("")
    w("## 6. シナリオ・審査相談メモの正本")
    w("")
    w("- シナリオA（AI推奨・トップライン）：稼働率▲15%・採用▲20% → Year 2 DSCR 0.9倍前後（AI推定）→ 採用")
    w("- シナリオB（AI推奨・コスト）：CPA+30%・時給+5% → Year 3以降レバレッジ5.0x超（AI推定）→ 採用")
    w("- シナリオC（AI推奨・イベント）：未払残業代300百万円特損 → Year 1現預金枯渇リスク（AI推定）→ 不採用")
    w("- シナリオD（人の仮説）：大口派遣先（構成比28%）の契約終了 → 採用")
    w("- 審査相談メモ：7/5 続行 ／ 7/12 再検討（指摘3件）→ 検討ステータス「再検討中」")
    w("")
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main():
    OUT_FIXTURES.mkdir(parents=True, exist_ok=True)
    extraction = build_extraction()
    kpi_tree = build_kpi_tree()
    scenarios = build_scenarios()
    chat = build_chat_scripts(kpi_tree, scenarios)
    identify = build_identify()
    seed = build_seed(extraction, kpi_tree, scenarios)

    outputs = {
        "identify.json": identify,
        "deal_info_autostaff.json": build_deal_info(),
        "extraction_autostaff.json": extraction,
        "kpi_tree_autostaff.json": kpi_tree,
        "scenarios_autostaff.json": scenarios,
        "chat_scripts.json": chat,
        "seed_data.json": seed,
    }
    for name, data in outputs.items():
        path = OUT_FIXTURES / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"generated: fixtures/{name}")

    OUT_GT.write_text(build_ground_truth(extraction), encoding="utf-8")
    print(f"generated: {OUT_GT.name}")


if __name__ == "__main__":
    main()
