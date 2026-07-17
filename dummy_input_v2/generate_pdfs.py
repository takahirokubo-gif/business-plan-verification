# -*- coding: utf-8 -*-
"""DDレポートPDF 4種の生成（v2・ルミエールボーテ）。

- ページ単位の明示レイアウト（1要素=1ページ）でキーファクトのページ位置を構成的に保証する
- 日本語TTFフォントを埋め込む（pypdfでのテキスト抽出＝実AI抽出・validate.pyの検証が可能）
- ページに収まらない場合は警告を出して失敗させる（黙って崩れない）
"""
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import spec
from dd_content import DOCS

OUT_DIR = Path(__file__).parent

PAGE_W, PAGE_H = A4
MARGIN_L = 55
MARGIN_R = 55
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R
CONTENT_TOP = 775
CONTENT_BOTTOM = 72

PRIMARY = (0x1A / 255, 0x4F / 255, 0x8B / 255)
BODY_COLOR = (0.13, 0.14, 0.16)
GRAY = (0.45, 0.47, 0.51)
LIGHT = (0.76, 0.78, 0.82)
FILL_HEADER = (0.93, 0.93, 0.95)
FILL_CALLOUT = (0.95, 0.97, 1.0)

FONT = "JPFont"

_FONT_CANDIDATES = [
    str(Path(__file__).parent.parent / "backend" / "app" / "assets"
        / "NotoSansJP-VariableFont_wght.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def register_font():
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(FONT, path))
                return path
            except Exception:
                continue
    raise RuntimeError("日本語TTFフォントが見つかりません")


def _wrap(text: str, size: float, width: float) -> list[str]:
    """幅に収まるように折り返す（日本語は文字単位、英数字は塊を保つ）。"""
    lines = []
    line = ""
    for ch in text:
        if pdfmetrics.stringWidth(line + ch, FONT, size) <= width:
            line += ch
        else:
            lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return lines or [""]


class Page:
    """1ページ分の描画コンテキスト。yカーソルを持ち、オーバーフローを検知する。"""

    def __init__(self, c: canvas.Canvas, doc_title: str, page_no: int, label: str):
        self.c = c
        self.y = CONTENT_TOP
        self.page_no = page_no
        self.label = label
        self.overflow = False
        # ヘッダー
        c.setFont(FONT, 7.5)
        c.setFillColorRGB(*GRAY)
        c.drawString(MARGIN_L, PAGE_H - 38, doc_title)
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 38, spec.PROJECT_NAME)
        c.setStrokeColorRGB(*LIGHT)
        c.setLineWidth(0.5)
        c.line(MARGIN_L, PAGE_H - 44, PAGE_W - MARGIN_R, PAGE_H - 44)
        # フッター
        c.setFont(FONT, 7.5)
        c.drawString(MARGIN_L, 40, "Confidential — 取扱厳重注意")
        c.drawRightString(PAGE_W - MARGIN_R, 40, f"{page_no}")

    def _need(self, h: float):
        if self.y - h < CONTENT_BOTTOM:
            self.overflow = True

    def spacer(self, h: float):
        self.y -= h

    def h1(self, text: str):
        self._need(30)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, 14)
        self.c.drawString(MARGIN_L, self.y - 16, text)
        self.c.setStrokeColorRGB(*PRIMARY)
        self.c.setLineWidth(1.2)
        self.c.line(MARGIN_L, self.y - 22, MARGIN_L + CONTENT_W, self.y - 22)
        self.y -= 34

    def h2(self, text: str):
        self._need(24)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, 11)
        self.c.drawString(MARGIN_L, self.y - 13, text)
        self.y -= 22

    def para(self, text: str, size=9.3, color=BODY_COLOR, leading=15.5, indent=0.0):
        lines = _wrap(text, size, CONTENT_W - indent)
        self._need(len(lines) * leading + 4)
        self.c.setFillColorRGB(*color)
        self.c.setFont(FONT, size)
        for ln in lines:
            self.c.drawString(MARGIN_L + indent, self.y - size, ln)
            self.y -= leading
        self.y -= 5

    def note(self, text: str):
        self.para("※ " + text if not text.startswith("※") else text,
                  size=8, color=GRAY, leading=12.5)

    def bullets(self, items: list[str]):
        for it in items:
            lines = _wrap(it, 9.3, CONTENT_W - 14)
            self._need(len(lines) * 15.5)
            self.c.setFillColorRGB(*BODY_COLOR)
            self.c.setFont(FONT, 9.3)
            self.c.drawString(MARGIN_L + 2, self.y - 9.3, "・")
            for ln in lines:
                self.c.drawString(MARGIN_L + 14, self.y - 9.3, ln)
                self.y -= 15.5
        self.y -= 5

    def callout(self, text: str):
        size, leading, pad = 9.3, 15.5, 10
        lines = _wrap(text, size, CONTENT_W - pad * 2)
        h = len(lines) * leading + pad * 2
        self._need(h + 6)
        self.c.setFillColorRGB(*FILL_CALLOUT)
        self.c.setStrokeColorRGB(*PRIMARY)
        self.c.setLineWidth(0.9)
        self.c.rect(MARGIN_L, self.y - h, CONTENT_W, h, stroke=1, fill=1)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, size)
        ty = self.y - pad
        for ln in lines:
            self.c.drawString(MARGIN_L + pad, ty - size + 2, ln)
            ty -= leading
        self.y -= h + 10

    def kv(self, pairs: list[tuple[str, str]]):
        key_w = CONTENT_W * 0.32
        for k, v in pairs:
            v_lines = _wrap(v, 9.0, CONTENT_W - key_w - 8)
            row_h = max(len(v_lines), 1) * 14 + 6
            self._need(row_h)
            self.c.setStrokeColorRGB(*LIGHT)
            self.c.setLineWidth(0.5)
            self.c.line(MARGIN_L, self.y - row_h, MARGIN_L + CONTENT_W, self.y - row_h)
            self.c.setFont(FONT, 9.0)
            self.c.setFillColorRGB(*GRAY)
            self.c.drawString(MARGIN_L + 2, self.y - 13, k)
            self.c.setFillColorRGB(*BODY_COLOR)
            ty = self.y
            for ln in v_lines:
                self.c.drawString(MARGIN_L + key_w + 8, ty - 13, ln)
                ty -= 14
            self.y -= row_h
        self.y -= 8

    def table(self, rows: list[list[str]]):
        size, pad = 8.4, 4
        ncols = len(rows[0])
        widths = []
        for j in range(ncols):
            w = max(pdfmetrics.stringWidth(str(r[j]), FONT, size) for r in rows) + pad * 2
            widths.append(max(min(w, CONTENT_W * 0.5), 42))
        scale = CONTENT_W / sum(widths)
        widths = [w * scale for w in widths]

        for i, row in enumerate(rows):
            cell_lines = []
            row_h = 0
            for j, val in enumerate(row):
                lines = _wrap(str(val), size, widths[j] - pad * 2)
                cell_lines.append(lines)
                row_h = max(row_h, len(lines) * 12 + 7)
            self._need(row_h)
            x = MARGIN_L
            if i == 0:
                self.c.setFillColorRGB(*FILL_HEADER)
                self.c.rect(MARGIN_L, self.y - row_h, CONTENT_W, row_h, stroke=0, fill=1)
            self.c.setStrokeColorRGB(*LIGHT)
            self.c.setLineWidth(0.5)
            self.c.line(MARGIN_L, self.y - row_h, MARGIN_L + CONTENT_W, self.y - row_h)
            if i == 0:
                self.c.line(MARGIN_L, self.y, MARGIN_L + CONTENT_W, self.y)
            self.c.setFont(FONT, size)
            self.c.setFillColorRGB(*(PRIMARY if i == 0 else BODY_COLOR))
            for j, lines in enumerate(cell_lines):
                ty = self.y
                for ln in lines:
                    if i > 0 and j > 0 and ln and all(
                            ch in "0123456789,.%△+－-()倍年月日hx人店回円▲" for ch in ln):
                        self.c.drawRightString(x + widths[j] - pad, ty - 11, ln)
                    else:
                        self.c.drawString(x + pad, ty - 11, ln)
                    ty -= 12
                x += widths[j]
            self.y -= row_h
        self.y -= 10


BLOCK_RENDERERS = {
    "h1": lambda pg, arg: pg.h1(arg),
    "h2": lambda pg, arg: pg.h2(arg),
    "p": lambda pg, arg: pg.para(arg),
    "note": lambda pg, arg: pg.note(arg),
    "bullets": lambda pg, arg: pg.bullets(arg),
    "callout": lambda pg, arg: pg.callout(arg),
    "kv": lambda pg, arg: pg.kv(arg),
    "table": lambda pg, arg: pg.table(arg),
}

DISCLAIMER = [
    f"本報告書は、{spec.DEAL['sponsor']}（以下「依頼者」）の依頼に基づき、"
    f"{spec.DEAL['target']}に関するデューデリジェンスの結果を取りまとめたものであり、"
    "依頼者による本件取引の検討以外の目的で使用することはできません。",
    "本報告書は、対象会社から開示を受けた資料および対象会社の役職員に対する"
    "インタビューの内容に依拠して作成されています。当職らは、開示資料の真実性・"
    "網羅性について独自の検証を行っておらず、これらを保証するものではありません。",
    "本報告書の記載内容は調査基準日時点の情報に基づくものであり、その後の状況の変化に"
    "より影響を受ける可能性があります。当職らは、本報告書の交付後に判明した事実に基づき"
    "本報告書を更新する義務を負いません。",
    "本報告書は法律・会計・税務その他の専門的判断のすべてを網羅するものではなく、"
    "依頼者の意思決定はご自身の判断と責任において行われるものとします。",
    "本報告書の全部または一部を、当職らの事前の書面による同意なく第三者に開示・"
    "引用・複製することはできません。ただし、依頼者が本件のファイナンスを検討する"
    "金融機関に対して守秘義務を条件に開示することを妨げません。",
]


def render_doc(doc_key: str) -> tuple[Path, int]:
    meta = DOCS[doc_key]
    filename = spec.DD_FILES[doc_key]
    path = OUT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(meta["title"])
    c.setAuthor(meta["firm"])
    overflow_pages = []

    doc_header = f"{meta['title']}（{meta['subtitle']}）"

    # ---- p.1 表紙
    c.setFillColorRGB(*PRIMARY)
    c.setFont(FONT, 22)
    c.drawCentredString(PAGE_W / 2, 560, meta["title"])
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(FONT, 15)
    c.drawCentredString(PAGE_W / 2, 520, meta["subtitle"])
    c.setFont(FONT, 10)
    c.setFillColorRGB(*GRAY)
    c.drawCentredString(PAGE_W / 2, 470, f"（{spec.PROJECT_NAME}）")
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(FONT, 11)
    c.drawCentredString(PAGE_W / 2, 300, meta["firm"])
    c.drawCentredString(PAGE_W / 2, 280, meta["date"])
    c.setFont(FONT, 9)
    c.setFillColorRGB(0.72, 0.11, 0.11)
    c.drawCentredString(PAGE_W / 2, 160, "Confidential — 取扱厳重注意")
    c.setFont(FONT, 8)
    c.setFillColorRGB(*GRAY)
    c.drawCentredString(PAGE_W / 2, 140,
                        "本資料は依頼者の本件検討のためにのみ作成されたものです")
    c.showPage()

    # ---- p.2 免責事項
    pg = Page(c, doc_header, 2, "免責事項")
    pg.h1("本報告書の利用に関する重要な注意事項")
    for para in DISCLAIMER:
        pg.para(para)
    if pg.overflow:
        overflow_pages.append(2)
    c.showPage()

    # ---- p.3 目次
    pg = Page(c, doc_header, 3, "目次")
    pg.h1("目次")
    c.setFont(FONT, 9.5)
    for idx, page_def in enumerate(meta["pages"]):
        if "toc" in page_def:
            page_no = 4 + idx
            title = page_def["toc"]
            c.setFillColorRGB(*BODY_COLOR)
            c.drawString(MARGIN_L + 4, pg.y - 10, title)
            c.drawRightString(PAGE_W - MARGIN_R - 4, pg.y - 10, str(page_no))
            c.setStrokeColorRGB(*LIGHT)
            c.setLineWidth(0.4)
            c.line(MARGIN_L + 4, pg.y - 14, PAGE_W - MARGIN_R - 4, pg.y - 14)
            pg.y -= 22
    c.setFillColorRGB(*GRAY)
    c.setFont(FONT, 8)
    c.drawString(MARGIN_L + 4, pg.y - 14, "※ 表紙・免責事項・目次はページ1〜3。")
    c.showPage()

    # ---- p.4以降 本文
    for idx, page_def in enumerate(meta["pages"]):
        page_no = 4 + idx
        pg = Page(c, doc_header, page_no, "")
        for block in page_def["blocks"]:
            kind, arg = block[0], block[1]
            BLOCK_RENDERERS[kind](pg, arg)
        if pg.overflow:
            overflow_pages.append(page_no)
        c.showPage()

    c.save()
    total = 3 + len(meta["pages"])
    if overflow_pages:
        raise RuntimeError(f"{filename}: ページ{overflow_pages} がオーバーフロー")
    return path, total


def main():
    font_path = register_font()
    print(f"font: {font_path}")
    for key in DOCS:
        path, total = render_doc(key)
        print(f"generated: {path.name} ({total} pages)")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
