"""PDF出力（補助）。概要タブと同じ構成（案件基本情報・事業要約 → KPIツリー →
財務情報 → ストレス仮説 → 前提・定性情報 → 審査相談メモ）で確定データをPDFに転記する。

デザイン：表紙ヘッダー帯・ストラクチャーのステータスボックス・番号チップ見出し・
色付きテーブルヘッダー＋ゼブラ行・シナリオの丸バッジ（画面のデザイントークンと共通の配色）。
"""
import json
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from ..config import ASSETS_DIR, EXPORT_DIR
from ..models import Deal

FONT = "JPExport"
# 同梱フォント（サーバーレス環境用）を最優先。ローカルのフォントはフォールバック
_FONT_CANDIDATES = [
    str(ASSETS_DIR / "NotoSansJP-VariableFont_wght.ttf"),
    os.path.expanduser("~/Library/Fonts/NotoSansJP-VariableFont_wght.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

PAGE_W, PAGE_H = A4
ML, MR = 50, 50

# 画面のデザイントークン（index.css）と共通の配色
PRIMARY = (0x1A / 255, 0x4F / 255, 0x8B / 255)          # primary-container
PRIMARY_DARK = (0x00 / 255, 0x38 / 255, 0x6C / 255)     # primary
PRIMARY_LIGHT = (0xD5 / 255, 0xE3 / 255, 0xFF / 255)    # primary-fixed
INK = (0.1, 0.11, 0.13)
GRAY = (0.45, 0.47, 0.51)
BORDER = (0.85, 0.86, 0.89)
ROW_ALT = (0.962, 0.968, 0.985)                          # ゼブラ行
BOX_BG = (0.972, 0.976, 0.99)                            # ステータスボックス
AMBER = (0.71, 0.28, 0.03)
AMBER_BG = (1.0, 0.98, 0.92)                             # ★KPI・AI注記の背景

SCENARIO_COLORS = {
    "A": PRIMARY,
    "B": (0.71, 0.33, 0.04),   # amber-700
    "C": (0.73, 0.10, 0.10),   # error
}

AI_DISCLAIMER = "※ インパクト数値はAIによる推定であり、財務モデルの再計算値ではありません。"

USER_NAMES = {"tanaka": "田中", "sato": "佐藤", "takahashi": "高橋"}


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
    """簡易ライター（自動改ページ・書式ヘルパー）。"""

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
        # フッター（罫線＋Confidential＋ページ番号）
        self.c.setStrokeColorRGB(*BORDER)
        self.c.setLineWidth(0.5)
        self.c.line(ML, 40, PAGE_W - MR, 40)
        self.c.setFont(FONT, 7.5)
        self.c.setFillColorRGB(*GRAY)
        self.c.drawString(ML, 29, "Confidential — 審査相談用（確定データのみ）")
        self.c.drawRightString(PAGE_W - MR, 29, str(self.page))
        if self.page > 1:
            # 2ページ目以降：小さなランニングヘッダー
            self.c.setFont(FONT, 7.5)
            self.c.setFillColorRGB(*GRAY)
            self.c.drawString(ML, PAGE_H - 32, "審査相談資料（事業計画検証）")
            self.c.drawRightString(PAGE_W - MR, PAGE_H - 32, self.deal_name)
            self.c.setStrokeColorRGB(*BORDER)
            self.c.setLineWidth(0.5)
            self.c.line(ML, PAGE_H - 38, PAGE_W - MR, PAGE_H - 38)
            self.y = PAGE_H - 54
        else:
            self.y = PAGE_H - 50

    def need(self, h: float):
        if self.y - h < 55:
            self._new_page()

    def banner(self, subtitle: str, meta: str):
        """1ページ目のヘッダー帯（プライマリ色ベタ＋白文字）。"""
        h = 88
        self.c.setFillColorRGB(*PRIMARY_DARK)
        self.c.rect(0, PAGE_H - h, PAGE_W, h, stroke=0, fill=1)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.rect(0, PAGE_H - h - 3, PAGE_W, 3, stroke=0, fill=1)
        self.c.setFillColorRGB(1, 1, 1)
        self.c.setFont(FONT, 9)
        self.c.drawString(ML, PAGE_H - 28, subtitle)
        self.c.setFont(FONT, 16)
        self.c.drawString(ML, PAGE_H - 52, self.deal_name)
        self.c.setFont(FONT, 8)
        self.c.setFillColorRGB(0.85, 0.9, 1.0)
        self.c.drawString(ML, PAGE_H - 70, meta)
        self.y = PAGE_H - h - 22

    def heading(self, num: str, text: str):
        """番号チップ付きセクション見出し。"""
        self.need(34)
        y = self.y
        self.c.setFillColorRGB(*PRIMARY)
        self.c.rect(ML, y - 15, 26, 15, stroke=0, fill=1)
        self.c.setFillColorRGB(1, 1, 1)
        self.c.setFont(FONT, 9)
        self.c.drawCentredString(ML + 13, y - 11.5, num)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, 11.5)
        self.c.drawString(ML + 34, y - 12, text)
        self.c.setStrokeColorRGB(*PRIMARY)
        self.c.setLineWidth(1)
        self.c.line(ML, y - 20, PAGE_W - MR, y - 20)
        self.y -= 32

    def text(self, s: str, size=9, color=INK, indent=0.0, leading=14.0, bg=None):
        width = PAGE_W - ML - MR - indent
        # 改行を含むテキスト（AI論述等）は段落ごとに折り返す（\nをそのまま描くと豆腐になる）
        for para in (s or "").replace("\r", "").split("\n"):
            for ln in _wrap(para, size, width):
                self.need(leading)
                if bg:
                    self.c.setFillColorRGB(*bg)
                    self.c.rect(ML + indent - 3, self.y - leading + 3.5,
                                width + 6, leading - 1, stroke=0, fill=1)
                self.c.setFillColorRGB(*color)
                self.c.setFont(FONT, size)
                self.c.drawString(ML + indent, self.y - size, ln)
                self.y -= leading
        self.y -= 2

    def kv(self, k: str, v: str):
        self.need(15)
        self.c.setFont(FONT, 9)
        self.c.setFillColorRGB(*GRAY)
        self.c.drawString(ML + 4, self.y - 9, k)
        self.c.setFillColorRGB(*INK)
        self.c.drawString(ML + 134, self.y - 9, v)
        self.c.setStrokeColorRGB(*BORDER)
        self.c.setLineWidth(0.35)
        self.c.line(ML, self.y - 12.5, PAGE_W - MR, self.y - 12.5)
        self.y -= 15

    def stat_row(self, stats: list[tuple[str, str]]):
        """EV・シニア・レバレッジ等のステータスボックス行（画面のStatカードと同じ見せ方）。"""
        n = len(stats)
        gap, h = 8.0, 36.0
        bw = (PAGE_W - ML - MR - gap * (n - 1)) / n
        self.need(h + 8)
        x = ML
        top = self.y
        for label, value in stats:
            self.c.setFillColorRGB(*BOX_BG)
            self.c.setStrokeColorRGB(*BORDER)
            self.c.setLineWidth(0.6)
            self.c.rect(x, top - h, bw, h, stroke=1, fill=1)
            self.c.setFillColorRGB(*GRAY)
            self.c.setFont(FONT, 6.8)
            self.c.drawCentredString(x + bw / 2, top - 12, label)
            self.c.setFillColorRGB(*PRIMARY)
            self.c.setFont(FONT, 11.5)
            self.c.drawCentredString(x + bw / 2, top - 27, value)
            x += bw + gap
        self.y -= h + 10

    def table(self, rows: list[list[str]], label_w: float = 130):
        """色付きヘッダー＋ゼブラ行のテーブル。先頭列はラベル固定幅、残りを等分。"""
        n_val = max(1, len(rows[0]) - 1)
        col_w = (PAGE_W - ML - MR - label_w) / n_val
        row_h = 15.0
        for i, row in enumerate(rows):
            self.need(row_h)
            top = self.y
            if i == 0:
                self.c.setFillColorRGB(*PRIMARY_LIGHT)
                self.c.rect(ML, top - row_h + 2, PAGE_W - ML - MR, row_h - 1, stroke=0, fill=1)
            elif i % 2 == 0:
                self.c.setFillColorRGB(*ROW_ALT)
                self.c.rect(ML, top - row_h + 2, PAGE_W - ML - MR, row_h - 1, stroke=0, fill=1)
            self.c.setFont(FONT, 8.5)
            self.c.setFillColorRGB(*(PRIMARY if i == 0 else INK))
            for j, val in enumerate(row):
                if j == 0:
                    self.c.drawString(ML + 4, top - 9.5, str(val))
                else:
                    x = ML + label_w + (j - 1) * col_w
                    self.c.drawRightString(x + col_w - 6, top - 9.5, str(val))
            self.c.setStrokeColorRGB(*BORDER)
            self.c.setLineWidth(0.35)
            self.c.line(ML, top - row_h + 1.5, PAGE_W - MR, top - row_h + 1.5)
            self.y -= row_h
        self.y -= 8

    def scenario_title(self, key: str, title: str, meta: str):
        """丸バッジ（シナリオキー）＋タイトル＋属性メタ。"""
        self.need(22)
        cy = self.y - 9
        color = SCENARIO_COLORS.get(key, GRAY)
        self.c.setFillColorRGB(*color)
        self.c.circle(ML + 7, cy + 2, 7, stroke=0, fill=1)
        self.c.setFillColorRGB(1, 1, 1)
        self.c.setFont(FONT, 8)
        self.c.drawCentredString(ML + 7, cy - 0.5, key)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, 9.5)
        self.c.drawString(ML + 20, cy - 1, title)
        tw = pdfmetrics.stringWidth(title, FONT, 9.5)
        self.c.setFillColorRGB(*GRAY)
        self.c.setFont(FONT, 8)
        self.c.drawString(ML + 24 + tw, cy - 1, meta)
        self.y -= 24

    def subheading(self, text: str):
        """「■ 見出し」の小見出し。"""
        self.need(18)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.rect(ML, self.y - 10, 6, 6, stroke=0, fill=1)
        self.c.setFont(FONT, 9)
        self.c.drawString(ML + 11, self.y - 10.5, text)
        self.y -= 18


def build_export_pdf(deal: Deal) -> tuple[str, int]:
    _font()
    confirmed = {i.key: i for i in deal.items if i.status == "confirmed"}
    held = [i for i in deal.items if i.status == "held"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"審査サマリー_{deal.target}_{ts}.pdf"
    path = EXPORT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    w = W(c, deal.name)

    owner = USER_NAMES.get(deal.owner or "", deal.owner) or "－"
    w.banner("審査相談資料（事業計画検証）",
             f"作成 {datetime.now().strftime('%Y/%m/%d %H:%M')}／担当 {owner}／確定データのみを転記"
             f"（AIによる推定値には注記）")

    # ---- 01 案件基本情報・事業要約（概要タブ①）
    w.heading("01", "案件基本情報・事業要約")

    def _mm(v):
        return f"{v:,}" if isinstance(v, (int, float)) else "－"

    if deal.ev_mm or deal.senior_mm or deal.initial_leverage:
        w.stat_row([
            ("EV（買収総額）", f"{_mm(deal.ev_mm)}百万円"),
            ("シニア（本行取組）", f"{_mm(deal.senior_mm)}（{_mm(deal.our_commitment_mm)}）百万円"),
            ("エクイティ", f"{_mm(deal.equity_mm)}百万円"),
            ("レバレッジ／LTV",
             f"{deal.initial_leverage or '－'}x／{deal.ltv_pct or '－'}%"),
        ])
    w.kv("案件スキーム", deal.deal_type)
    w.kv("借入人（SPC）", deal.borrower)
    w.kv("対象会社", f"{deal.target}（{deal.industry or '－'}）")
    w.kv("スポンサー", deal.sponsor or "－")
    if deal.close_date:
        w.kv("クローズ予定日", deal.close_date)
    w.y -= 4
    if deal.summary:
        w.text(f"事業要約：{deal.summary}", size=8.5, color=GRAY)

    # ---- 02 重要KPIとその構造（概要タブ②：ツリー＋数式）
    w.heading("02", "重要KPIとその構造（ツリー）")
    kpi_children: dict = {}
    for n in deal.kpi_nodes:
        kpi_children.setdefault(n.parent_id, []).append(n)

    def walk_kpi(parent, depth):
        for n in kpi_children.get(parent, []):
            mark = "★ " if n.star else "・"
            line = f"{mark}{n.label}"
            if n.formula:
                line += f" ＝ {n.formula.lstrip('=＝ ')}"
            elif n.value_text:
                line += f"（{n.value_text}）"
            w.text(line, size=8.5,
                   color=(0.55, 0.35, 0.0) if n.star else INK,
                   indent=10 + depth * 14, leading=13.5,
                   bg=AMBER_BG if n.star else None)
            walk_kpi(n.node_id, depth + 1)

    walk_kpi(None, 0)
    w.text("★＝最重要KPI（ストレスシナリオの起点）。数式は財務モデルの構文解析結果（再計算なし）。",
           size=7.5, color=GRAY)

    # ---- 03 財務情報（概要タブ③：実績・Base・Sponsorの全確定行＋論述）
    w.heading("03", "財務情報（百万円・確定値のみ）")

    metric_order = ["revenue", "gross", "op", "ordinary", "ni", "ebitda",
                    "utilization", "new_hires", "unit_price", "cpa",
                    "cash", "goodwill", "net_assets", "debt", "total_assets",
                    "op_cf", "inv_cf", "fin_cf", "fcf"]

    def case_rows(prefix):
        """確定済み項目からケースの全行を概要タブと同じ順で集める。"""
        found = []
        for key, item in confirmed.items():
            if not key.startswith(prefix + "_") or not item.effective_values():
                continue
            metric = key[len(prefix) + 1:]
            label = item.label + (f"（{item.unit}）" if item.unit != "百万円" else "")
            found.append((metric, key, label))
        order = {m: i for i, m in enumerate(metric_order)}
        found.sort(key=lambda t: order.get(t[0], len(metric_order)))
        return [(key, label) for _m, key, label in found]

    def years_for(keys, default):
        # 実AIは決算期表記（'2027/3期' 等）の年度キーを返すことがあるため、
        # 固定リストで捨てずに実データのキーから列を導出する（最大5列）
        order = ["FY24", "FY25", "FY26", "FY27", "FY28", "FY29", "FY30", "FY31"]
        found: set[str] = set()
        for k in keys:
            item = confirmed.get(k)
            if item:
                found.update((item.effective_values() or {}).keys())
        known = [y for y in order if y in found]
        unknown = sorted(y for y in found if y not in order)
        return (known + unknown)[:5] or default

    def row(label, key, years):
        item = confirmed.get(key)
        vals = item.effective_values() if item else None
        return [label] + [f"{vals.get(y):,}" if vals and vals.get(y) is not None else "－" for y in years]

    for case_title, prefix, default_years in (
        ("実績", "act", ["FY24", "FY25", "FY26"]),
        ("計画（ベースケース）", "base", ["FY27", "FY28", "FY29", "FY30", "FY31"]),
        ("計画（スポンサーケース）", "sponsor", ["FY27", "FY28", "FY29", "FY30", "FY31"]),
    ):
        keys = case_rows(prefix)
        if not keys:
            continue
        years = years_for([k for k, _l in keys], default_years)
        w.table([[case_title, *years]] + [row(label, key, years) for key, label in keys])

    # 財務ハイライト・ケース前提差異（AI論述・概要タブの財務情報直下と同じ）
    for item in deal.items:
        if item.status != "confirmed" or item.section != "財務ハイライト":
            continue
        w.subheading(f"{item.label}（AI推定・モデル再計算なし）")
        w.text(item.effective_text() or "－", size=8.5, indent=10)

    # ---- 04 ストレス仮説（概要タブ④と同じ5部構成）
    w.heading("04", "ストレス仮説とその根拠データ")
    w.text(AI_DISCLAIMER, size=8, color=AMBER, bg=AMBER_BG)
    w.y -= 2
    node_labels = {n.node_id: n.label for n in deal.kpi_nodes}
    for sc in deal.scenarios:
        if not sc.adopted:
            continue
        origin = "AI推奨" if sc.origin == "ai" else "自分の仮説"
        w.scenario_title(sc.key, sc.title, f"（{origin}／{sc.type_label}）")
        kpis = "、".join(node_labels.get(k, k) for k in json.loads(sc.affected_kpis_json or "[]"))
        w.text(f"・【KPIとリスク】{kpis or '－'}。{sc.cause}", size=8.5, indent=20)
        w.text(f"・【ストレスと根拠】{sc.change_text}（根拠：{sc.change_basis}）", size=8.5, indent=20)
        w.text(f"・【インパクト】{sc.impact}（AI推定・モデル再計算なし）", size=8.5, color=AMBER, indent=20)
        w.text(f"・【保全策・構造】{sc.safeguards}", size=8.5, indent=20)
        w.text(f"・【Q&A】{sc.questions}", size=8.5, indent=20)
        w.y -= 6
    rejected = [s for s in deal.scenarios if not s.adopted]
    for sc in rejected:
        w.text(f"（参考・不採用）S{sc.key}｜{sc.title}"
               + (f"　※{sc.rejection_note}" if sc.rejection_note else ""),
               size=8, color=GRAY, indent=20)

    # ---- 05 前提・定性情報（全文・出典付き。財務ハイライト系は03に掲載済み）
    w.heading("05", "前提・定性情報（確定済み）")
    for item in deal.items:
        if item.status != "confirmed":
            continue
        if item.unit != "テキスト" and item.key not in ("normalized_ebitda", "goodwill"):
            continue
        if item.section == "財務ハイライト":
            continue
        ev = json.loads(item.evidence_json) if item.evidence_json else {}
        text = item.effective_text()
        if item.key == "normalized_ebitda":
            v = (item.effective_values() or {}).get("FY26")
            text = f"{v:,}百万円（FY26）。モデルFY26実績と一致。" if v else "－"
        if item.key == "goodwill":
            v = (item.effective_values() or {}).get("FY27")
            text = f"{v:,}百万円。{item.resolution_note or ''}" if v else "－"
        w.subheading(item.label)
        w.text(text or "－", size=8.5, indent=11)
        w.text(f"出典：{ev.get('file', '')}｜{ev.get('location', '')}", size=7.5, color=GRAY, indent=11)

    # ---- 06 審査相談の記録（末尾）
    if deal.memos:
        w.heading("06", "審査相談の記録")
        for m in reversed(list(deal.memos)):
            attendees = "、".join(json.loads(m.attendees_json or "[]"))
            w.subheading(f"{m.meeting_date}　結論：{m.conclusion}（出席：{attendees}）")
            for i, f in enumerate(m.findings, 1):
                link = {"scenario": f"シナリオ{f.target_key}", "kpi": "KPI構造",
                        "item": f"数値：{f.target_key}"}.get(f.target_type or "", "")
                w.text(f"指摘{i}{f'【{link}】' if link else ''}：{f.text}", size=8, indent=11)
            if m.note:
                w.text(f"メモ：{m.note}", size=8, color=GRAY, indent=11)
            w.y -= 3

    if held:
        w.text(f"※ 保留中の{len(held)}項目（{'、'.join(i.label for i in held)}）は本資料から除外しています。",
               size=8, color=GRAY)

    c.save()
    return str(path), len(held)
