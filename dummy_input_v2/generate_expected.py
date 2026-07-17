# -*- coding: utf-8 -*-
"""期待アウトプット（答え）の生成（v2・ルミエールボーテ）。

生成物:
  - expected_output.json …… 機械採点用の期待値（run_ai_test.py が使用）
  - GROUND_TRUTH.md …… 人が読む正本（サービス上でどう表示されるべきか）

すべて spec.py / xl_layout.py から導出する（手編集禁止）。
"""
import json
from pathlib import Path

import spec
import xl_layout as L
from spec import ACTUAL_YEARS, PLAN_YEARS, YEARS

HERE = Path(__file__).parent

_pl_b = spec.compute_pl("base")
_pl_s = spec.compute_pl("sponsor")
_bs_b, _cf_b = spec.compute_bs_cf("base")
_bs_s, _cf_s = spec.compute_bs_cf("sponsor")
_facts = {f["id"]: f for f in spec.DD_KEY_FACTS}

SEC_QUAL = "前提・定性情報"
SEC_ACT = "実績（2024/3期〜2026/3期）"
SEC_BASE = "計画：ベースケース（2027/3期〜2031/3期）"
SEC_SPON = "計画：スポンサーケース（2027/3期〜2031/3期)".replace(")", "）")
SEC_STRUCT = "ストラクチャー・B/S項目"


def _ev(sheet: str, row_key: str, y_from: str, y_to: str, file_key: str = "base") -> dict:
    """Excel根拠（ファイル・シート・セル範囲）。"""
    return dict(
        file=spec.MODEL_FILES[file_key],
        sheet=sheet,
        location=L.cell_range(sheet, row_key, y_from, y_to),
    )


def _pv(fact_id: str) -> dict:
    """PDF根拠（ファイル・ページ）。"""
    f = _facts[fact_id]
    return dict(file=spec.DD_FILES[f["file"]], page=f["page"])


def build_items() -> list[dict]:
    """抽出項目24件の期待値。

    match ルール（run_ai_test.py が解釈する）:
      - values: 年度キーを正規化（"2027/3期"/"FY27"/"27/3期"/"2027" → FY27）した上で完全一致
      - text_expects: text_value（または values が無い場合の根拠quote）に
        含まれるべきキーワード群（グループ内はいずれか1つでOK）
      - evidence: file は完全一致。sheet はlocation文字列に含まれること。
        page は "p.N" / "N ページ" 等の表記を正規化して一致
    """
    items = []

    # ---- 定性情報
    items.append(dict(
        key="business_summary", section=SEC_QUAL, label="事業要約",
        label_aliases=["事業要約", "事業概要", "ビジネスサマリー"],
        unit="テキスト", case=None, required=True, values=None,
        text_expects=[["スキンケア", "化粧品"], ["EC", "D2C"], ["卸", "ドラッグ"],
                      ["OEM", "ファブレス"]],
        evidence=dict(file=spec.DD_FILES["business"], page=4),
        page_tolerance=1,  # p.4〜5（エグゼクティブサマリー）
        mismatch=None,
    ))
    items.append(dict(
        key="risk_oem", section=SEC_QUAL, label="主要リスク①：OEM委託先への生産依存",
        label_aliases=["OEM", "委託先", "生産依存", "調達"],
        unit="テキスト", case=None, required=True, values=None,
        text_expects=[["58%", "58％"], ["三双化学", "OEM", "委託先"]],
        evidence=_pv("oem_dependency"), page_tolerance=0,
        mismatch=None,
    ))
    items.append(dict(
        key="risk_wholesale", section=SEC_QUAL, label="主要リスク②：卸チェーンへの売上集中",
        label_aliases=["卸", "チェーン", "集中", "依存"],
        unit="テキスト", case=None, required=True, values=None,
        text_expects=[["45%", "45％"], ["21%", "21％", "マツヤ"]],
        evidence=_pv("wholesale_concentration"), page_tolerance=0,
        mismatch=None,
    ))
    items.append(dict(
        key="risk_trademark", section=SEC_QUAL, label="主要リスク③：商標権が代表者個人名義",
        label_aliases=["商標", "知的財産", "個人名義"],
        unit="テキスト", case=None, required=False, values=None,
        text_expects=[["商標"], ["個人名義", "代表者"], ["移転"]],
        evidence=_pv("trademark"), page_tolerance=0,
        mismatch=None,
    ))
    items.append(dict(
        key="normalized_ebitda", section=SEC_QUAL, label="正常収益力EBITDA（2026/3期）",
        label_aliases=["正常収益力", "QoE", "Normalized"],
        unit="百万円", case=None, required=True,
        values={"FY26": spec.NORMALIZED_EBITDA},
        text_expects=None,
        evidence=_pv("normalized_ebitda"), page_tolerance=0,
        mismatch=None,
    ))

    # ---- 実績（モデルPL/BS/CF・両ケース共通）
    def act(key, row_key, label, sheet, values, required=True, aliases=None):
        items.append(dict(
            key=key, section=SEC_ACT, label=label,
            label_aliases=aliases or [label],
            unit="百万円", case=None, required=required,
            values={y: values[y] for y in ACTUAL_YEARS},
            text_expects=None,
            evidence=_ev(sheet, row_key, "FY24", "FY26"),
            mismatch=None,
        ))

    act("act_revenue", "revenue", "売上高", "PL",
        {y: _pl_b[y]["revenue"] for y in YEARS},
        aliases=["売上高", "売上収益", "売上"])
    act("act_op", "op", "営業利益", "PL",
        {y: _pl_b[y]["op"] for y in YEARS},
        aliases=["営業利益", "EBIT"])
    act("act_ebitda", "ebitda", "EBITDA", "PL",
        {y: _pl_b[y]["ebitda"] for y in YEARS},
        aliases=["EBITDA"])
    act("act_ni", "ni", "当期純利益", "PL",
        {y: _pl_b[y]["ni"] for y in YEARS}, required=False,
        aliases=["当期純利益", "純利益", "当期利益"])
    act("act_cash", "cash", "現預金", "BS",
        {y: _bs_b[y]["cash"] for y in YEARS},
        aliases=["現預金", "現金及び現金同等物", "現金及び預金", "現金"])
    act("act_net_assets", "net_assets", "純資産", "BS",
        {y: _bs_b[y]["net_assets"] for y in YEARS},
        aliases=["純資産", "自己資本"])
    act("act_debt", "debt", "有利子負債", "BS",
        {y: _bs_b[y]["debt"] for y in YEARS},
        aliases=["有利子負債", "借入金", "デット"])
    act("act_fcf", "fcf", "フリー・キャッシュフロー", "CF",
        {y: _cf_b[y]["fcf"] for y in YEARS}, required=False,
        aliases=["フリー・キャッシュフロー", "FCF", "フリーキャッシュフロー"])

    # ---- 計画（ケース別）
    def plan(key, row_key, label, sheet, case, values, required=True, aliases=None):
        section = SEC_BASE if case == "base" else SEC_SPON
        items.append(dict(
            key=key, section=section, label=label,
            label_aliases=aliases or [label],
            unit="百万円", case=case, required=required,
            values={y: values[y] for y in PLAN_YEARS},
            text_expects=None,
            evidence=_ev(sheet, row_key, "FY27", "FY31", file_key=case),
            mismatch=None,
        ))

    plan("base_revenue", "revenue", "売上高", "PL", "base",
         {y: _pl_b[y]["revenue"] for y in YEARS}, aliases=["売上高", "売上収益", "売上"])
    plan("base_op", "op", "営業利益", "PL", "base",
         {y: _pl_b[y]["op"] for y in YEARS}, aliases=["営業利益", "EBIT"])
    plan("base_ebitda", "ebitda", "EBITDA", "PL", "base",
         {y: _pl_b[y]["ebitda"] for y in YEARS}, aliases=["EBITDA"])
    plan("base_fcf", "fcf", "フリー・キャッシュフロー", "CF", "base",
         {y: _cf_b[y]["fcf"] for y in YEARS},
         aliases=["フリー・キャッシュフロー", "FCF", "フリーキャッシュフロー"])
    plan("sponsor_revenue", "revenue", "売上高", "PL", "sponsor",
         {y: _pl_s[y]["revenue"] for y in YEARS}, aliases=["売上高", "売上収益", "売上"])
    plan("sponsor_op", "op", "営業利益", "PL", "sponsor",
         {y: _pl_s[y]["op"] for y in YEARS}, aliases=["営業利益", "EBIT"])
    plan("sponsor_ebitda", "ebitda", "EBITDA", "PL", "sponsor",
         {y: _pl_s[y]["ebitda"] for y in YEARS}, aliases=["EBITDA"])
    plan("sponsor_fcf", "fcf", "フリー・キャッシュフロー", "CF", "sponsor",
         {y: _cf_s[y]["fcf"] for y in YEARS}, required=False,
         aliases=["フリー・キャッシュフロー", "FCF", "フリーキャッシュフロー"])

    # ---- ストラクチャー
    gw_fact = _facts["goodwill_dd"]
    items.append(dict(
        key="goodwill", section=SEC_STRUCT, label="のれん（買収想定額）",
        label_aliases=["のれん", "Goodwill"],
        unit="百万円", case=None, required=True,
        values={"FY27": spec.GOODWILL},
        single_value=spec.GOODWILL,  # 年度キーは問わず、この値が拾えていればOK
        text_expects=None,
        evidence=dict(file=spec.MODEL_FILES["base"], sheet="inp",
                      location=f"inp!D{L.INP_STRUCT_ROWS['goodwill'][0]}",
                      alt_sheet="BS",
                      alt_location=L.cell_range("BS", "goodwill", "FY27", "FY31")),
        mismatch=dict(
            other_value=spec.GOODWILL_DD,
            other_file=spec.DD_FILES["financial"],
            other_page=gw_fact["page"],
            note="モデル（6,100）と財務DD（5,950）で150百万円の差異。"
                 "識別可能無形資産の試算差。PPAで確定予定。",
        ),
    ))
    items.append(dict(
        key="ev", section=SEC_STRUCT, label="エンタープライズ・バリュー（EV）",
        label_aliases=["EV", "エンタープライズ", "企業価値"],
        unit="百万円", case=None, required=True,
        values={"FY27": spec.DEAL["ev_mm"]},
        single_value=spec.DEAL["ev_mm"],
        text_expects=None,
        evidence=dict(file=spec.MODEL_FILES["base"], sheet="inp",
                      location=f"inp!D{L.INP_STRUCT_ROWS['ev'][0]}"),
        mismatch=None,
    ))
    items.append(dict(
        key="senior_loan", section=SEC_STRUCT, label="シニアローン総額",
        label_aliases=["シニア", "タームローン", "ローン総額"],
        unit="百万円", case=None, required=True,
        values={"FY27": spec.SENIOR_TOTAL},
        single_value=spec.SENIOR_TOTAL,
        text_expects=None,
        evidence=dict(file=spec.MODEL_FILES["base"], sheet="inp",
                      location=f"inp!D{L.INP_STRUCT_ROWS['senior'][0]}",
                      alt_sheet="debt",
                      alt_location=L.cell_range("debt", "opening", "FY27", "FY27")),
        mismatch=None,
    ))
    return items


def build_expected() -> dict:
    items = build_items()
    identify = {}
    for slot, fname in spec.MODEL_FILES.items():
        identify[fname] = dict(company=spec.DEAL["target"], doc_type=f"model_{slot}")
    for slot, fname in spec.DD_FILES.items():
        identify[fname] = dict(company=spec.DEAL["target"], doc_type=f"dd_{slot}")

    deal_info = dict(
        fields=dict(
            name_contains=["ルミエールボーテ"],
            deal_type="LBO",
            borrower="株式会社ブルームホールディングス",
            target="株式会社ルミエールボーテ",
            industry_contains=["化粧品", "スキンケア"],
            sponsor="大手町プリンシパルパートナーズ株式会社",
            close_date="2026-11-30",
            ev_mm=spec.DEAL["ev_mm"],
            senior_mm=spec.DEAL["senior_mm"],
            equity_mm=spec.DEAL["equity_mm"],
            tenor_years=spec.DEAL["tenor_years"],
            sponsor_ebitda_mm=spec.DEAL["sponsor_ebitda_mm"],
        ),
        note="本行取組額・担当者・審査相談予定日は行内情報のため資料に存在しない"
             "（抽出されたら誤り＝ハルシネーション）。",
    )

    kpi_tree = dict(
        # ラベル部分一致で判定するエッジ（親→子）。財務モデルの数式構造と1:1対応
        required_edges=[
            [["売上収益", "売上高", "売上"], ["EC売上", "EC"]],
            [["売上収益", "売上高", "売上"], ["卸売上", "卸"]],
            [["EC売上", "EC"], ["会員数", "アクティブ会員"]],
            [["EC売上", "EC"], ["購入回数", "購買頻度"]],
            [["EC売上", "EC"], ["注文単価", "AOV", "客単価"]],
            [["会員数", "アクティブ会員"], ["リピート率", "残存率"]],
            [["会員数", "アクティブ会員"], ["新規獲得", "新規会員"]],
            [["卸売上", "卸"], ["店舗数", "取扱店舗"]],
            [["卸売上", "卸"], ["店舗あたり", "店販", "出荷額"]],
            [["売上原価", "原価"], ["原価率"]],
            [["広告宣伝費", "広告"], ["広告宣伝費率", "広宣費率", "広告費率"]],
        ],
        # ★（リスクドライバー）として妥当な候補。最低2つ、全てこの中から
        star_candidates=[["リピート率", "残存率"], ["新規獲得", "新規会員"],
                         ["原価率"], ["店舗数", "取扱店舗"], ["広告", "広宣"]],
        min_stars=2,
        # DD由来（モデル外・定性）ノードとして妥当な候補（1つ以上あれば加点）
        dd_node_candidates=[["OEM", "委託先"], ["チェーン", "集中", "依存"]],
        origin_rule="数式由来ノードは origin=model、DD由来ノードは origin=dd",
    )

    scenarios = dict(
        count=3,
        type_labels=["トップライン", "コスト", "イベント"],
        required_parts=["title", "cause", "affected_kpis", "change_text",
                        "change_basis", "impact", "safeguards", "questions"],
        impact_must_mention_any=["DSCR", "レバレッジ", "現預金", "返済"],
        impact_must_contain_number=True,
        forbidden_labels=["問題なし", "問題あり", "懸念なし", "承認", "否決"],
        # 各類型がDDのキーファクトを引用しているか（いずれかの数値・固有名詞）
        fact_anchors=dict(
            topline=["76%", "45%", "21%", "リピート", "マツヤ", "チェーン"],
            cost=["58%", "三双", "OEM", "原価率", "広告", "CPA"],
            event=["COC", "チェンジ・オブ・コントロール", "商標", "景品表示",
                   "行政指導", "許可"],
        ),
        note="シナリオは生成タスクのため一意の正解はない。上記の構造・根拠引用・"
             "推定数値の有無をルーブリックとして採点し、内容の妥当性は人がレビューする。",
    )

    return dict(
        deal_key="lumiere",
        company=spec.DEAL["target"],
        project=spec.PROJECT_NAME,
        unit_note="値はすべて百万円（モデルは百万円表記・DD表は千円→百万円換算）",
        year_note="年度キーはFY24〜FY31（FY26=2026年3月期）。"
                  "採点時は 2026/3期・26/3期・2026 等の表記を正規化する",
        auto_calc=dict(
            initial_leverage=spec.DEAL["initial_leverage"],
            ltv_pct=spec.DEAL["ltv_pct"],
            formula="レバレッジ=シニア4,800÷提示EBITDA 1,120＝4.3x／"
                    "LTV=シニア4,800÷EV9,000＝53%",
        ),
        identify=identify,
        deal_info=deal_info,
        items=items,
        kpi_tree=kpi_tree,
        scenarios=scenarios,
        key_facts=[dict(id=f["id"], file=spec.DD_FILES[f["file"]], page=f["page"],
                        text=f["text"]) for f in spec.DD_KEY_FACTS],
    )


# ---------------------------------------------------------------- GROUND_TRUTH.md


def build_ground_truth(expected: dict) -> str:
    pl_b, pl_s = _pl_b, _pl_s
    out = []
    w = out.append
    w("# GROUND_TRUTH — ルミエールボーテLBO（v2・実AI精度テスト用）の正本")
    w("")
    w("このファイルは `spec.py` から自動生成される（手編集禁止）。")
    w("再生成: `python3 generate_all.py` ／ 整合チェック: `python3 validate.py`")
    w("機械採点用の期待値は `expected_output.json`、採点は `run_ai_test.py`。")
    w("")
    w("## 0. このデータセットの位置づけ")
    w("")
    w("- 目的：**実生成AI（EXTRACTOR_MODE=anthropic）の動作・精度テスト**用の理想的インプット")
    w("- 「理想的」の定義：必要な情報がすべて資料内に揃っている ∧ 実在のLBOモデル・DD報告書の様式に十分近い")
    w("- 既存デモデータ（dummy_input/ オートスタッフ中部）とは独立。**mockモードでは解析不可**")
    w("")
    w("## 1. 案件基本情報（S2登録画面・deal_info抽出の期待値）")
    w("")
    w("| 項目 | 値 | 出どころ |")
    w("|---|---|---|")
    w(f"| 案件名 | {spec.DEAL['name']} | 対象会社名＋スキームから生成 |")
    w(f"| 案件種別 | {spec.DEAL['deal_type']} | 事業DD p.4／モデルCover |")
    w(f"| 借入人（SPC） | {spec.DEAL['borrower']} | モデルCover・inp／事業DD p.4 |")
    w(f"| 対象会社 | {spec.DEAL['target']}（{spec.DEAL['industry']}） | 全資料 |")
    w(f"| スポンサー | {spec.DEAL['sponsor']} | モデルCover／事業DD p.4 |")
    w(f"| クローズ予定日 | {spec.DEAL['close_date']} | モデルCover・inp／事業DD p.4 |")
    w(f"| EV | {spec.DEAL['ev_mm']:,}百万円 | モデルinp D{L.INP_STRUCT_ROWS['ev'][0]} |")
    w(f"| シニアローン | {spec.DEAL['senior_mm']:,}百万円（期間{spec.DEAL['tenor_years']}年） "
      f"| モデルinp D{L.INP_STRUCT_ROWS['senior'][0]}・debtシート |")
    w(f"| エクイティ | {spec.DEAL['equity_mm']:,}百万円 | モデルinp D{L.INP_STRUCT_ROWS['equity'][0]} |")
    w(f"| スポンサー提示EBITDA（速報） | {spec.DEAL['sponsor_ebitda_mm']:,}百万円 "
      f"| モデルinp D{L.INP_STRUCT_ROWS['sponsor_ebitda'][0]}／財務DD p.31 |")
    w(f"| 初期レバレッジ（S2自動算出） | {spec.DEAL['initial_leverage']}x ＝ "
      f"シニア{spec.DEAL['senior_mm']:,} ÷ 提示EBITDA{spec.DEAL['sponsor_ebitda_mm']:,} | UI算出 |")
    w(f"| LTV（S2自動算出） | {spec.DEAL['ltv_pct']}% ＝ "
      f"シニア{spec.DEAL['senior_mm']:,} ÷ EV{spec.DEAL['ev_mm']:,} | UI算出 |")
    w("")
    w("**本行取組額（2,000百万円想定）・担当者・審査相談予定日は行内情報であり資料に存在しない。**")
    w("deal_info抽出でこれらの値が返った場合はハルシネーション（誤り）と判定する。")
    w("")
    w("## 2. ファイル識別（identify）の期待値")
    w("")
    w("| ファイル | doc_type | company |")
    w("|---|---|---|")
    for fname, e in expected["identify"].items():
        w(f"| {fname} | {e['doc_type']} | {e['company']} |")
    w("")
    w("## 3. DDレポートのキーファクト（ページ位置固定）")
    w("")
    w("| ID | ファイル | ページ | 内容 |")
    w("|---|---|---|---|")
    for f in spec.DD_KEY_FACTS:
        w(f"| {f['id']} | {spec.DD_FILES[f['file']]} | p.{f['page']} | {f['text']} |")
    w("")
    pages = {"business": 20, "financial": 34, "legal": 14, "tax": 10}
    w("※ ページ数：事業{business}p・財務{financial}p・法務{legal}p・税務{tax}p"
      .format(**pages) + "（各p.1表紙・p.2免責・p.3目次）。")
    w("")
    w("## 4. 財務モデルの主要数値（百万円）＝ S3数値確定タブの期待表示")
    w("")
    w("### 実績（両ケース共通・2024/3期〜2026/3期）")
    w("")
    w("| 項目 | FY24 | FY25 | FY26 | 参照セル |")
    w("|---|---|---|---|---|")
    rows = [
        ("売上高", [_pl_b[y]["revenue"] for y in ACTUAL_YEARS],
         L.cell_range("PL", "revenue", "FY24", "FY26")),
        ("営業利益", [_pl_b[y]["op"] for y in ACTUAL_YEARS],
         L.cell_range("PL", "op", "FY24", "FY26")),
        ("EBITDA", [_pl_b[y]["ebitda"] for y in ACTUAL_YEARS],
         L.cell_range("PL", "ebitda", "FY24", "FY26")),
        ("当期純利益", [_pl_b[y]["ni"] for y in ACTUAL_YEARS],
         L.cell_range("PL", "ni", "FY24", "FY26")),
        ("現預金", [_bs_b[y]["cash"] for y in ACTUAL_YEARS],
         L.cell_range("BS", "cash", "FY24", "FY26")),
        ("純資産", [_bs_b[y]["net_assets"] for y in ACTUAL_YEARS],
         L.cell_range("BS", "net_assets", "FY24", "FY26")),
        ("有利子負債", [_bs_b[y]["debt"] for y in ACTUAL_YEARS],
         L.cell_range("BS", "debt", "FY24", "FY26")),
        ("FCF", [_cf_b[y]["fcf"] for y in ACTUAL_YEARS],
         L.cell_range("CF", "fcf", "FY24", "FY26")),
    ]
    for label, vals, ref in rows:
        w(f"| {label} | {vals[0]:,} | {vals[1]:,} | {vals[2]:,} | {ref} |")
    w("")
    w("### 計画（2027/3期〜2031/3期）")
    w("")
    w("| ケース | 項目 | FY27 | FY28 | FY29 | FY30 | FY31 |")
    w("|---|---|---|---|---|---|---|")
    for case, pl, cf in (("Base", pl_b, _cf_b), ("Sponsor", pl_s, _cf_s)):
        for label, key in (("売上高", "revenue"), ("営業利益", "op"), ("EBITDA", "ebitda")):
            vals = [pl[y][key] for y in PLAN_YEARS]
            w(f"| {case} | {label} | " + " | ".join(f"{v:,}" for v in vals) + " |")
        vals = [cf[y]["fcf"] for y in PLAN_YEARS]
        w(f"| {case} | FCF | " + " | ".join(f"{v:,}" for v in vals) + " |")
    w("")
    w("### KPIドライバー（FY26実績）")
    w("")
    w("| KPI | 値 | 参照セル |")
    w("|---|---|---|")
    d26 = spec.drivers("base")["FY26"]
    kpis = [
        ("アクティブ会員数", f"{d26['member']:,}人", L.cell("inp", "member", "FY26")),
        ("リピート率", f"{d26['repeat']:.0%}", L.cell("inp", "repeat", "FY26")),
        ("新規獲得会員数", f"{d26['new']:,}人", L.cell("inp", "new", "FY26")),
        ("年間平均購入回数", f"{d26['freq']}回", L.cell("inp", "freq", "FY26")),
        ("平均注文単価（AOV）", f"{d26['aov']:,}円", L.cell("inp", "aov", "FY26")),
        ("卸取扱店舗数", f"{d26['doors']:,}店", L.cell("inp", "doors", "FY26")),
        ("店舗あたり年間出荷額", f"{d26['perdoor']:,}千円", L.cell("inp", "perdoor", "FY26")),
        ("売上原価率", f"{d26['cogs_rate']:.1%}", L.cell("inp", "cogs_rate", "FY26")),
        ("広告宣伝費率", f"{d26['ad_rate']:.1%}", L.cell("inp", "ad_rate", "FY26")),
    ]
    for label, v, ref in kpis:
        w(f"| {label} | {v} | {ref} |")
    w("")
    w("## 5. 意図的な不整合（1件のみ・不整合検知のテスト）")
    w("")
    w(f"- **のれん想定額**：モデル {spec.GOODWILL:,}百万円"
      f"（inp!D{L.INP_STRUCT_ROWS['goodwill'][0]}・BS計画年）"
      f" vs 財務DD {spec.GOODWILL_DD:,}百万円（p.{_facts['goodwill_dd']['page']}）"
      "→ 数値確定タブで不整合警告を表示し、どちらを採るか人が選択する")
    w("- 差異の説明（資料に記載あり）：識別可能無形資産の試算差"
      f"（DD 615 vs モデル {spec.IDENTIFIED_INTANGIBLE}百万円）。PPAで確定予定")
    w("- 正常収益力EBITDA 1,036 vs 報告EBITDA 1,120 は「QoE調整」であり不整合ではない"
      "（両者の関係はDD p.32〜33に明記。mismatch扱いにしないのが正）")
    w("- DD表（千円）とモデル（百万円）の差は丸めの範囲内であり不整合ではない")
    w("")
    w("## 6. 抽出項目一覧（extract_items・24件）")
    w("")
    w("| key | セクション | 項目 | 必須 | 期待値（百万円） | 根拠 |")
    w("|---|---|---|---|---|---|")
    for it in expected["items"]:
        ev = it["evidence"]
        if "page" in ev:
            ref = f"{ev['file']} p.{ev['page']}"
        else:
            ref = f"{ev['file']} {ev['location']}"
        if it["values"]:
            vals = " / ".join(f"{y}:{v:,}" for y, v in it["values"].items())
        else:
            grp = " ＋ ".join("｜".join(g) for g in (it.get("text_expects") or []))
            vals = f"（テキスト：{grp} を含む）"
        req = "必須" if it["required"] else "任意"
        w(f"| {it['key']} | {it['section']} | {it['label']} | {req} | {vals} | {ref} |")
    w("")
    w("## 7. KPIツリー（S4）の期待構造")
    w("")
    w("財務モデルの数式チェーン（inpシート→PLシート）から、以下のエッジが再現されること：")
    w("")
    w("```")
    w("売上収益")
    w("├─ EC売上（=会員数×購入回数×AOV）")
    w("│   ├─ アクティブ会員数（=前期会員数×リピート率＋新規獲得会員数）")
    w("│   │   ├─ リピート率 ★")
    w("│   │   └─ 新規獲得会員数 ★候補")
    w("│   ├─ 年間平均購入回数")
    w("│   └─ 平均注文単価（AOV）")
    w("├─ 卸売上（=店舗数×店舗あたり年間出荷額）")
    w("│   ├─ 卸取扱店舗数 ★候補")
    w("│   └─ 店舗あたり年間出荷額")
    w("└─ その他売上（百貨店・海外）")
    w("売上原価 ─ 売上原価率 ★候補（OEM値上げリスク）")
    w("広告宣伝費 ─ 広告宣伝費率 ★候補（CPA上昇リスク）")
    w("```")
    w("")
    w("- ★（リスクドライバー）は最低2つ。候補：リピート率・新規獲得・原価率・店舗数・広告費率")
    w("  （いずれもDDの指摘と紐づく。候補外への★は要人手レビュー）")
    w("- DD由来ノード（モデル外・定性バッジ）の候補：OEM委託先依存度・卸チェーン集中度")
    w("- 各ノードに根拠（シート・行、数式のどの部分から親子関係を判定したか）が付くこと")
    w("")
    w("## 8. シナリオ（S5）のルーブリック（生成タスクのため一意解なし）")
    w("")
    w("AI推奨3類型が生成され、それぞれ標準5部構成が埋まっていること：")
    w("")
    w("| 類型 | 期待される題材（いずれか） | 引用されるべき事実 |")
    w("|---|---|---|")
    w("| トップライン | リピート率低下／大口卸チェーン取引縮小 | リピート率76%・上位3チェーン45%（最大手21%） |")
    w("| コスト | OEM値上げ・原価率上昇／広告CPA高騰 | OEM依存58%・原価率41%・広告費率18% |")
    w("| イベント | OEM契約COC発動・供給停止／広告規制（景表法）／商標移転遅延 | COC条項2件・行政指導歴・商標個人名義 |")
    w("")
    w("- インパクトは DSCR・レバレッジ・現預金への影響を**具体的数値を含む定性推定**で記述")
    w("  （例の水準感：シニア4,800、FY27ベースFCF 591、年間元利返済 約585〔480＋利息105〕"
      "→ ベースでもDSCR約1.0x前後の薄いカバレッジであり、ストレス時に1.0xを割る構図）")
    w("- 「AI推定・モデル再計算なし」バッジ必須。判定ラベル（問題なし/問題あり等）は出さない")
    w("- 変化幅には根拠（DDの事実・外部データ）が紐づくこと")
    w("")
    w("## 9. 採点方法")
    w("")
    w("`run_ai_test.py` が identify／deal_info／items を機械採点し、KPIツリー・シナリオは")
    w("構造チェック＋人手レビュー用のダンプを出力する。詳細は README.md を参照。")
    return "\n".join(out) + "\n"


def main():
    expected = build_expected()
    (HERE / "expected_output.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("generated: expected_output.json")
    (HERE / "GROUND_TRUTH.md").write_text(build_ground_truth(expected), encoding="utf-8")
    print("generated: GROUND_TRUTH.md")


if __name__ == "__main__":
    main()
