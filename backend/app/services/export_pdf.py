"""PDF出力（補助）。Excelエクスポートと同じ確定データを1〜3ページのPDFに転記する。"""
import json
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ..config import EXPORT_DIR
from ..models import Deal

FONT = "JPExport"
_FONT_CANDIDATES = [
    os.path.expanduser("~/Library/Fonts/NotoSansJP-VariableFont_wght.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

PAGE_W, PAGE_H = A4
ML, MR = 50, 50
PRIMARY = (0x1A / 255, 0x4F / 255, 0x8B / 255)
GRAY = (0.45, 0.47, 0.51)
AMBER = (0.71, 0.28, 0.03)

AI_DISCLAIMER = "※ インパクト数値はAIによる推定であり、財務モデルの再計算値ではありません。"


def _font():
    try:
        pdfmetrics.getFont(FONT)
        return
    except KeyError:
        pass
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(FONT, path))
            return
    raise RuntimeError("日本語フォントが見つかりません")


def _wrap(text: str, size: float, width: float) -> list[str]:
    lines, line = [], ""
    for ch in text or "":
        if pdfmetrics.stringWidth(line + ch, FONT, size) <= width:
            line += ch
        else:
            lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return lines or [""]


class W:
    """簡易ライター（自動改ページ）。"""

    def __init__(self, c: canvas.Canvas, deal_name: str):
        self.c = c
        self.deal_name = deal_name
        self.page = 0
        self.y = 0.0
        self._new_page()

    def _new_page(self):
        if self.page:
            self.c.showPage()
        self.page += 1
        self.c.setFont(FONT, 7.5)
        self.c.setFillColorRGB(*GRAY)
        self.c.drawString(ML, 30, "Confidential — 審査相談用（確定データのみ）")
        self.c.drawRightString(PAGE_W - MR, 30, str(self.page))
        self.y = PAGE_H - 50

    def need(self, h: float):
        if self.y - h < 55:
            self._new_page()

    def heading(self, text: str):
        self.need(28)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, 12)
        self.c.drawString(ML, self.y - 12, text)
        self.c.setStrokeColorRGB(*PRIMARY)
        self.c.setLineWidth(1)
        self.c.line(ML, self.y - 17, PAGE_W - MR, self.y - 17)
        self.y -= 28

    def text(self, s: str, size=9, color=(0.1, 0.11, 0.13), indent=0.0, leading=14.0):
        width = PAGE_W - ML - MR - indent
        for ln in _wrap(s, size, width):
            self.need(leading)
            self.c.setFillColorRGB(*color)
            self.c.setFont(FONT, size)
            self.c.drawString(ML + indent, self.y - size, ln)
            self.y -= leading
        self.y -= 2

    def kv(self, k: str, v: str):
        self.need(14)
        self.c.setFont(FONT, 9)
        self.c.setFillColorRGB(*GRAY)
        self.c.drawString(ML, self.y - 9, k)
        self.c.setFillColorRGB(0.1, 0.11, 0.13)
        self.c.drawString(ML + 130, self.y - 9, v)
        self.y -= 14

    def table(self, rows: list[list[str]]):
        col_w = (PAGE_W - ML - MR) / len(rows[0])
        for i, row in enumerate(rows):
            self.need(15)
            self.c.setFont(FONT, 8.5)
            self.c.setFillColorRGB(*(PRIMARY if i == 0 else (0.1, 0.11, 0.13)))
            for j, val in enumerate(row):
                x = ML + j * col_w
                if j == 0:
                    self.c.drawString(x, self.y - 9, str(val))
                else:
                    self.c.drawRightString(x + col_w - 6, self.y - 9, str(val))
            self.c.setStrokeColorRGB(0.85, 0.86, 0.89)
            self.c.setLineWidth(0.4)
            self.c.line(ML, self.y - 12, PAGE_W - MR, self.y - 12)
            self.y -= 15
        self.y -= 6


def build_export_pdf(deal: Deal) -> tuple[str, int]:
    _font()
    confirmed = {i.key: i for i in deal.items if i.status == "confirmed"}
    held = [i for i in deal.items if i.status == "held"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"審査サマリー_{deal.target}_{ts}.pdf"
    path = EXPORT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    w = W(c, deal.name)

    c.setFillColorRGB(*PRIMARY)
    c.setFont(FONT, 15)
    c.drawString(ML, w.y - 15, "審査相談資料（事業計画検証）")
    w.y -= 22
    c.setFillColorRGB(0.1, 0.11, 0.13)
    c.setFont(FONT, 11)
    c.drawString(ML, w.y - 11, deal.name)
    w.y -= 16
    c.setFillColorRGB(*GRAY)
    c.setFont(FONT, 8)
    c.drawString(ML, w.y - 8, f"作成 {datetime.now().strftime('%Y/%m/%d %H:%M')}／確定データのみを転記")
    w.y -= 24

    w.heading("01｜案件概要")
    w.kv("案件スキーム", deal.deal_type)
    w.kv("借入人（SPC）", deal.borrower)
    w.kv("対象会社", f"{deal.target}（{deal.industry or '－'}）")
    w.kv("スポンサー", deal.sponsor or "－")
    if deal.ev_mm:
        w.kv("ストラクチャー", f"EV {deal.ev_mm:,}百万円／シニア {deal.senior_mm:,}百万円"
                            f"（本行 {deal.our_commitment_mm:,}百万円）／エクイティ {deal.equity_mm:,}百万円")
    if deal.initial_leverage:
        w.kv("レバレッジ・LTV", f"{deal.initial_leverage}x／{deal.ltv_pct}%（登録情報からの自動算出）")
    if deal.summary:
        w.text(deal.summary, size=8.5, color=GRAY)

    w.heading("02｜確定財務ハイライト（百万円）")
    years_a = ["FY24", "FY25", "FY26"]
    years_p = ["FY27", "FY28", "FY29", "FY30", "FY31"]

    def row(label, key, years):
        item = confirmed.get(key)
        vals = item.effective_values() if item else None
        return [label] + [f"{vals.get(y):,}" if vals and vals.get(y) is not None else "－" for y in years]

    w.table([["実績", *years_a],
             row("売上高", "act_revenue", years_a),
             row("EBITDA", "act_ebitda", years_a),
             row("純資産", "act_net_assets", years_a)])
    w.table([["計画（Base）", *years_p],
             row("売上高", "base_revenue", years_p),
             row("EBITDA", "base_ebitda", years_p),
             row("FCF", "base_fcf", years_p)])

    w.heading("03｜重要KPI（★）")
    for n in deal.kpi_nodes:
        if n.star:
            w.kv(n.label, n.value_text or "－")

    w.heading("04｜ストレスシナリオ")
    w.text(AI_DISCLAIMER, size=8, color=AMBER)
    node_labels = {n.node_id: n.label for n in deal.kpi_nodes}
    for sc in deal.scenarios:
        if not sc.adopted:
            continue
        origin = "AI推奨" if sc.origin == "ai" else "自分の仮説"
        w.text(f"S{sc.key}｜{sc.title}（{origin}／{sc.type_label}）", size=9.5, color=PRIMARY)
        kpis = "、".join(node_labels.get(k, k) for k in json.loads(sc.affected_kpis_json or "[]"))
        w.text(f"発生要因：{sc.cause}", size=8.5, indent=10)
        w.text(f"影響KPI：{kpis or '－'}／変化幅：{sc.change_text}（根拠：{sc.change_basis}）",
               size=8.5, indent=10)
        w.text(f"影響（AI推定）：{sc.impact}", size=8.5, color=AMBER, indent=10)
        w.text(f"保全策：{sc.safeguards}／確認事項：{sc.questions}", size=8.5, indent=10)
        w.y -= 4
    rejected = [s for s in deal.scenarios if not s.adopted]
    for sc in rejected:
        w.text(f"（参考・不採用）S{sc.key}｜{sc.title}"
               + (f"　※{sc.rejection_note}" if sc.rejection_note else ""),
               size=8, color=GRAY, indent=10)

    # ---- 前提・定性情報（全文・出典付き）
    w.heading("05｜前提・定性情報（確定済み）")
    for item in deal.items:
        if item.status != "confirmed":
            continue
        if item.unit != "テキスト" and item.key not in ("normalized_ebitda", "goodwill"):
            continue
        ev = json.loads(item.evidence_json) if item.evidence_json else {}
        text = item.effective_text()
        if item.key == "normalized_ebitda":
            v = (item.effective_values() or {}).get("FY26")
            text = f"{v:,}百万円（FY26）。モデルFY26実績と一致。" if v else "－"
        if item.key == "goodwill":
            v = (item.effective_values() or {}).get("FY27")
            text = f"{v:,}百万円。{item.resolution_note or ''}" if v else "－"
        w.text(f"■ {item.label}", size=9, color=PRIMARY)
        w.text(text or "－", size=8.5, indent=10)
        w.text(f"出典：{ev.get('file', '')}｜{ev.get('location', '')}", size=7.5, color=GRAY, indent=10)

    # ---- 審査相談メモ
    if deal.memos:
        w.heading("06｜審査相談の記録")
        for m in reversed(list(deal.memos)):
            attendees = "、".join(json.loads(m.attendees_json or "[]"))
            w.text(f"{m.meeting_date}　結論：{m.conclusion}（出席：{attendees}）",
                   size=9, color=PRIMARY)
            for i, f in enumerate(m.findings, 1):
                link = {"scenario": f"シナリオ{f.target_key}", "kpi": "KPI構造",
                        "item": f"数値：{f.target_key}"}.get(f.target_type or "", "")
                w.text(f"指摘{i}{f'【{link}】' if link else ''}：{f.text}", size=8, indent=10)
            if m.note:
                w.text(f"メモ：{m.note}", size=8, color=GRAY, indent=10)
            w.y -= 3

    if held:
        w.text(f"※ 保留中の{len(held)}項目（{'、'.join(i.label for i in held)}）は本資料から除外しています。",
               size=8, color=GRAY)

    c.save()
    return str(path), len(held)
