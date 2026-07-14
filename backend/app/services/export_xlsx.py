"""ステージ4：Excelエクスポート。

確定データのみ（案件基礎情報＋確定財務数値＋確定KPI構造＋採用シナリオ）を
行内標準フォーマットに近いテンプレートに値転記して .xlsx を生成する。
AI推定値には必ず注記を付す。保留項目は除外（件数は呼び出し側でダイアログ確認）。
"""
import json
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from ..config import EXPORT_DIR
from ..models import Deal

TITLE = Font(name="Yu Gothic", size=14, bold=True, color="1A4F8B")
H2 = Font(name="Yu Gothic", size=11, bold=True, color="1A4F8B")
HEAD = Font(name="Yu Gothic", size=9.5, bold=True)
BODY = Font(name="Yu Gothic", size=9.5)
NOTE = Font(name="Yu Gothic", size=8.5, color="737781")
AI_NOTE = Font(name="Yu Gothic", size=8.5, color="B54708")
FILL = PatternFill("solid", fgColor="EDEDF3")
AI_FILL = PatternFill("solid", fgColor="FFFAEB")
THIN = Side(style="thin", color="C2C6D1")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

AI_DISCLAIMER = "※ インパクト数値はAIによる推定であり、財務モデルの再計算値ではありません。"

YEARS_ACT = ["FY24", "FY25", "FY26"]
YEARS_PLAN = ["FY27", "FY28", "FY29", "FY30", "FY31"]


def _set(ws, addr, value, font=BODY, fill=None, num=None, align=None, border=False):
    c = ws[addr]
    c.value = value
    c.font = font
    if fill:
        c.fill = fill
    if num:
        c.number_format = num
    if align:
        c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    if border:
        c.border = BOX
    return c


def build_export(deal: Deal) -> tuple[str, int]:
    """確定データからエクスポートExcelを生成。returns (filepath, excluded_held_count)."""
    confirmed = [i for i in deal.items if i.status == "confirmed"]
    held = [i for i in deal.items if i.status == "held"]
    by_key = {i.key: i for i in confirmed}

    wb = Workbook()

    # ================= シート1：審査サマリー =================
    ws = wb.active
    ws.title = "審査サマリー"
    ws.sheet_view.showGridLines = False
    for col, w in dict(A=3, B=22, C=15, D=15, E=15, F=15, G=15, H=15).items():
        ws.column_dimensions[col].width = w

    _set(ws, "B2", "審査相談用サマリー（事業計画検証）", TITLE)
    _set(ws, "B3", f"作成日時：{datetime.now().strftime('%Y/%m/%d %H:%M')}　"
                   f"／　出典：事業計画検証システム（確定データのみを転記）", NOTE)

    # ---- 案件基礎情報
    _set(ws, "B5", "1. 案件基礎情報", H2)
    rows = [
        ("案件名", deal.name), ("案件種別", deal.deal_type),
        ("借入人（SPC）", deal.borrower), ("対象会社", f"{deal.target}（{deal.industry or '－'}）"),
        ("スポンサー", deal.sponsor or "－"), ("クローズ予定", deal.close_date or "－"),
        ("EV", f"{deal.ev_mm:,}百万円" if deal.ev_mm else "－"),
        ("シニアローン", f"{deal.senior_mm:,}百万円（本行取組 {deal.our_commitment_mm:,}百万円"
                        f"・期間{deal.tenor_years}年）" if deal.senior_mm else "－"),
        ("エクイティ", f"{deal.equity_mm:,}百万円" if deal.equity_mm else "－"),
        ("初期レバレッジ（自動算出）",
         f"{deal.initial_leverage}x（シニア{deal.senior_mm:,} ÷ 提示EBITDA{deal.sponsor_ebitda_mm:,}）"
         if deal.initial_leverage else "－"),
        ("LTV（自動算出）",
         f"{deal.ltv_pct}%（シニア{deal.senior_mm:,} ÷ EV{deal.ev_mm:,}）" if deal.ltv_pct else "－"),
    ]
    r = 6
    for k, v in rows:
        _set(ws, f"B{r}", k, HEAD, FILL, border=True)
        ws.merge_cells(f"C{r}:H{r}")
        _set(ws, f"C{r}", v, BODY, border=True)
        r += 1

    # ---- 確定財務数値
    r += 1
    _set(ws, f"B{r}", "2. 確定財務数値（単位：百万円）", H2)
    r += 1
    _set(ws, f"B{r}", "確定済みの抽出値のみを転記。各数値の根拠（参照ファイル・箇所）は"
                      "システム上で確認可能。", NOTE)
    r += 1

    def fin_table(title, keys, years, start_row):
        rr = start_row
        _set(ws, f"B{rr}", title, HEAD, FILL, border=True)
        for ci, y in enumerate(years):
            _set(ws, f"{chr(ord('C') + ci)}{rr}", y, HEAD, FILL, align="center", border=True)
        rr += 1
        for key, label in keys:
            item = by_key.get(key)
            if not item:
                continue
            _set(ws, f"B{rr}", label + ("（修正済）" if item.edited else ""), BODY, border=True)
            values = item.effective_values() or {}
            for ci, y in enumerate(years):
                v = values.get(y)
                _set(ws, f"{chr(ord('C') + ci)}{rr}", v if v is not None else "－",
                     BODY, num="#,##0", align="right", border=True)
            rr += 1
        return rr

    r = fin_table("実績", [("act_revenue", "売上高"), ("act_op", "営業利益"),
                           ("act_ebitda", "EBITDA"), ("act_ni", "当期純利益"),
                           ("act_cash", "現預金"), ("act_net_assets", "純資産"),
                           ("act_debt", "有利子負債"), ("act_fcf", "FCF")],
                  YEARS_ACT, r) + 1
    r = fin_table("計画（ベースケース）",
                  [("base_revenue", "売上高"), ("base_op", "営業利益"),
                   ("base_ebitda", "EBITDA"), ("base_fcf", "FCF")], YEARS_PLAN, r) + 1
    r = fin_table("計画（スポンサーケース）",
                  [("sponsor_revenue", "売上高"), ("sponsor_op", "営業利益"),
                   ("sponsor_ebitda", "EBITDA"), ("sponsor_fcf", "FCF")], YEARS_PLAN, r) + 1

    # ---- 前提・定性情報
    _set(ws, f"B{r}", "3. 前提・定性情報（確定済み）", H2)
    r += 1
    for item in confirmed:
        if item.unit != "テキスト" and item.key not in ("goodwill", "normalized_ebitda"):
            continue
        text = item.effective_text()
        if item.key == "goodwill":
            v = (item.effective_values() or {}).get("FY27")
            text = f"{v:,}百万円" if v else "－"
            if item.resolution_note:
                text += f"（{item.resolution_note}）"
        if item.key == "normalized_ebitda":
            v = (item.effective_values() or {}).get("FY26")
            text = f"{v:,}百万円（FY26・財務DD p.34）" if v else "－"
        _set(ws, f"B{r}", item.label, HEAD, FILL, border=True)
        ws.merge_cells(f"C{r}:H{r}")
        _set(ws, f"C{r}", text, BODY, align="left", border=True)
        ws.row_dimensions[r].height = max(16, 13 * (len(str(text)) // 55 + 1))
        r += 1

    if held:
        r += 1
        _set(ws, f"B{r}", f"※ 保留中の{len(held)}項目（{'、'.join(i.label for i in held)}）は"
                          "本サマリーから除外しています。", NOTE)

    # ================= シート2：KPI構造 =================
    ws2 = wb.create_sheet("KPI構造")
    ws2.sheet_view.showGridLines = False
    for col, w in dict(A=3, B=44, C=16, D=22, E=26).items():
        ws2.column_dimensions[col].width = w
    _set(ws2, "B2", "確定KPI構造", TITLE)
    _set(ws2, "B3", "★＝重要KPI（リスクドライバー）。出典：財務モデルの数式解析（再計算なし）"
                    "およびDDレポートの定性情報。", NOTE)
    _set(ws2, "B5", "KPI（階層）", HEAD, FILL, border=True)
    _set(ws2, "C5", "出典", HEAD, FILL, border=True)
    _set(ws2, "D5", "値（FY26実績）", HEAD, FILL, border=True)
    _set(ws2, "E5", "構造（数式）", HEAD, FILL, border=True)
    nodes = list(deal.kpi_nodes)
    children = {}
    for n in nodes:
        children.setdefault(n.parent_id, []).append(n)
    origin_label = {"model": "モデル数式", "dd": "DD由来", "manual": "手動追加"}
    r2 = [6]

    def walk(parent, depth):
        for n in children.get(parent, []):
            label = ("　" * depth) + ("★ " if n.star else "") + n.label
            if n.badge:
                label += f"〔{n.badge}〕"
            _set(ws2, f"B{r2[0]}", label, BODY, border=True)
            _set(ws2, f"C{r2[0]}", origin_label.get(n.origin, n.origin), BODY, border=True)
            _set(ws2, f"D{r2[0]}", n.value_text or "－", BODY, border=True)
            _set(ws2, f"E{r2[0]}", n.formula or "", NOTE, border=True)
            r2[0] += 1
            walk(n.node_id, depth + 1)

    walk(None, 0)

    # ================= シート3：シナリオ =================
    ws3 = wb.create_sheet("シナリオ分析")
    ws3.sheet_view.showGridLines = False
    for col, w in dict(A=3, B=18, C=60, D=30).items():
        ws3.column_dimensions[col].width = w
    _set(ws3, "B2", "採用シナリオ（審査相談用）", TITLE)
    _set(ws3, "B3", AI_DISCLAIMER, AI_NOTE, AI_FILL)
    r3 = 5
    adopted = [s for s in deal.scenarios if s.adopted]
    node_labels = {n.node_id: n.label for n in nodes}
    for sc in adopted:
        origin = "AI推奨" if sc.origin == "ai" else "自分の仮説"
        _set(ws3, f"B{r3}", f"シナリオ{sc.key}", HEAD, FILL, border=True)
        ws3.merge_cells(f"C{r3}:D{r3}")
        _set(ws3, f"C{r3}", f"{sc.title}　〔{origin}／{sc.type_label}〕", HEAD, FILL, border=True)
        r3 += 1
        kpis = "、".join(node_labels.get(k, k) for k in json.loads(sc.affected_kpis_json or "[]"))
        for k, v in [("① 発生要因", sc.cause),
                     ("② 影響KPI", kpis or "－"),
                     ("③ 変化幅と根拠", f"{sc.change_text}\n根拠：{sc.change_basis}"),
                     ("④ 返済能力への影響（AI推定・モデル再計算なし）", sc.impact),
                     ("⑤ 保全策・確認事項", f"{sc.safeguards}\n確認事項:{sc.questions}")]:
            _set(ws3, f"B{r3}", k, BODY, border=True, align="left")
            ws3.merge_cells(f"C{r3}:D{r3}")
            cell = _set(ws3, f"C{r3}", v, BODY, border=True, align="left")
            if "AI推定" in k:
                cell.fill = AI_FILL
            ws3.row_dimensions[r3].height = max(16, 13 * (len(str(v)) // 55 + 1))
            r3 += 1
        r3 += 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"審査サマリー_{deal.target}_{ts}.xlsx"
    path = EXPORT_DIR / filename
    wb.save(path)
    return str(path), len(held)
