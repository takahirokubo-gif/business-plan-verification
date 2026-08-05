# -*- coding: utf-8 -*-
"""統合版DD報告書PDF（データA用）— 横置きスライド形式（FAS実務標準のデッキ型）。

実際のLBO案件でやり取りされるDD報告書（財務アドバイザリーファームのスライド型
レポート）に見た目を寄せる：
- 横A4・1論点=1スライド（h2がスライドタイトル）。収まらない場合は「（続き）」スライド
- 章（h1）は章扉スライド。全スライド上部に章名の小見出し（アイブロウ）を表示
- 表はスライドを跨ぐ場合にヘッダー行を再掲して分割
- 図表番号の自動採番／目次は2パスレンダリングで実ページを反映
- 生成前の禁止文字列自己検査（BANNED_STRINGS）／planted_items_dd.json 出力
"""
import io
import json
import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import dd_a_content as C

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(__file__).resolve().parent / "build"
OUT_PATH = ROOT / "A_standard" / "DD_Report_統合版_オートスタッフ中部_A.pdf"

PAGE_W, PAGE_H = landscape(A4)          # 842 x 595
MARGIN_L = 42
MARGIN_R = 42
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R
BAND_TITLE_Y = PAGE_H - 52              # スライドタイトルの基準線
BODY_TOP = PAGE_H - 88
BODY_BOTTOM = 58

PRIMARY = (0x1A / 255, 0x4F / 255, 0x8B / 255)
BODY_COLOR = (0.13, 0.14, 0.16)
GRAY = (0.45, 0.47, 0.51)
LIGHT = (0.76, 0.78, 0.82)
FILL_HEADER = (0.93, 0.93, 0.95)
FILL_CALLOUT = (0.95, 0.97, 1.0)

FONT = "JPFont"
_FONT_CANDIDATES = [
    os.path.expanduser("~/Library/Fonts/NotoSansJP-VariableFont_wght.ttf"),
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


def _wrap(text, size, width):
    lines = []
    line = ""
    for ch in str(text):
        if pdfmetrics.stringWidth(line + ch, FONT, size) <= width:
            line += ch
        else:
            lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return lines or [""]


class Deck:
    """スライド型ドキュメント。h2ごとに新スライド、あふれたら（続き）スライド。"""

    def __init__(self, c, first_page_no):
        self.c = c
        self.page_no = first_page_no - 1
        self.y = BODY_BOTTOM
        self.chapter = None          # 現在の章（スライドバンドに表示）
        self.part = None             # 事業編／財務編／付属資料
        self.slide_title = None
        self.chapter_pages = []      # (toc, part, page_no)
        self.table_count = 0
        self._started = False
        self._lead_pending = False

    # ---- スライド管理
    def _chrome(self, title, eyebrow, cont=False):
        c = self.c
        if self._started:
            c.showPage()
        self._started = True
        self.page_no += 1
        # アイブロウ（章名）
        if eyebrow:
            c.setFont(FONT, 8)
            c.setFillColorRGB(*GRAY)
            c.drawString(MARGIN_L, PAGE_H - 26, eyebrow)
        c.setFont(FONT, 8)
        c.setFillColorRGB(*GRAY)
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 26, "Project Gear／Confidential")
        # スライドタイトル
        if title:
            c.setFillColorRGB(*PRIMARY)
            c.setFont(FONT, 16)
            c.drawString(MARGIN_L, BAND_TITLE_Y, title + ("（続き）" if cont else ""))
            c.setStrokeColorRGB(*PRIMARY)
            c.setLineWidth(1.4)
            c.line(MARGIN_L, BAND_TITLE_Y - 10, PAGE_W - MARGIN_R, BAND_TITLE_Y - 10)
        # フッター
        c.setFont(FONT, 7.5)
        c.setFillColorRGB(*GRAY)
        c.drawString(MARGIN_L, 26, "Confidential — 取扱厳重注意")
        c.drawRightString(PAGE_W - MARGIN_R, 26, f"{self.page_no}")
        self.y = BODY_TOP

    def h2(self, text):
        """節見出し。章スライドに流し込み、空きが少なければ新スライドを開始する。"""
        if self.slide_title != self.chapter or self.y - 150 < BODY_BOTTOM:
            self.slide_title = self.chapter
            self._chrome(self.chapter, f"【{self.part}】" if self.part else None)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.setFont(FONT, 13)
        self.c.drawString(MARGIN_L, self.y - 15, text)
        self.c.setStrokeColorRGB(*LIGHT)
        self.c.setLineWidth(0.8)
        self.c.line(MARGIN_L, self.y - 21, MARGIN_L + CONTENT_W, self.y - 21)
        self.y -= 34
        self._lead_pending = True

    def cont_slide(self):
        self.slide_title = self.chapter
        self._chrome(self.chapter, f"【{self.part}】" if self.part else None)

    def need(self, h):
        if self.y - h < BODY_BOTTOM:
            self.cont_slide()

    # ---- ブロック描画
    def chapter_divider(self, text, toc, part):
        self.slide_title = "__divider__"
        self._chrome(None, None)
        self.chapter = text
        if part:
            self.part = part
        self.chapter_pages.append((toc or text, part, self.page_no))
        c = self.c
        if part:
            c.setFillColorRGB(*GRAY)
            c.setFont(FONT, 13)
            c.drawString(MARGIN_L, PAGE_H / 2 + 64, f"【{part}】")
        c.setFillColorRGB(*PRIMARY)
        c.setFont(FONT, 26)
        c.drawString(MARGIN_L, PAGE_H / 2 + 20, text)
        c.setStrokeColorRGB(*PRIMARY)
        c.setLineWidth(2.0)
        c.line(MARGIN_L, PAGE_H / 2 + 4, MARGIN_L + 320, PAGE_H / 2 + 4)
        self.y = PAGE_H / 2 - 24     # 章扉に導入文を置けるようにする

    def lead_or_para(self, text):
        """スライド最初の段落はリード文（左アクセントバー付きキーメッセージ）として描く。"""
        if not self._lead_pending:
            self.para(text)
            return
        self._lead_pending = False
        size, leading, indent = 11.0, 18.0, 14
        lines = _wrap(text, size, CONTENT_W - indent)
        h = len(lines) * leading
        self.need(h + 8)
        self.c.setFillColorRGB(*PRIMARY)
        self.c.rect(MARGIN_L, self.y - h + 3, 3.5, h - 4, stroke=0, fill=1)
        self.c.setFillColorRGB(0.10, 0.11, 0.13)
        self.c.setFont(FONT, size)
        for ln in lines:
            self.c.drawString(MARGIN_L + indent, self.y - size, ln)
            self.y -= leading
        self.y -= 10

    def para(self, text, size=10.4, color=BODY_COLOR, leading=17.2, indent=0.0):
        lines = _wrap(text, size, CONTENT_W - indent)
        for ln in lines:
            if self.y - leading < BODY_BOTTOM:
                self.cont_slide()
            self.c.setFillColorRGB(*color)
            self.c.setFont(FONT, size)
            self.c.drawString(MARGIN_L + indent, self.y - size, ln)
            self.y -= leading
        self.y -= 6

    def note(self, text):
        self.para("※ " + text if not text.startswith("※") else text,
                  size=8.6, color=GRAY, leading=13.0)

    def bullets(self, items):
        for it in items:
            lines = _wrap(it, 10.4, CONTENT_W - 16)
            self.need(17.2)
            self.c.setFillColorRGB(*BODY_COLOR)
            self.c.setFont(FONT, 10.4)
            self.c.drawString(MARGIN_L + 2, self.y - 10.4, "・")
            for ln in lines:
                if self.y - 17.2 < BODY_BOTTOM:
                    self.cont_slide()
                    self.c.setFillColorRGB(*BODY_COLOR)
                    self.c.setFont(FONT, 10.4)
                self.c.drawString(MARGIN_L + 16, self.y - 10.4, ln)
                self.y -= 17.2
        self.y -= 5

    def callout(self, text):
        size, leading, pad = 10.2, 16.5, 11
        lines = _wrap(text, size, CONTENT_W - pad * 2)
        h = len(lines) * leading + pad * 2
        self.need(h + 6)
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

    def captable(self, caption, rows):
        self.table_count += 1
        self.table(rows, caption=f"図表{self.table_count}　{caption}")

    def table(self, rows, caption=None):
        size, pad = 9.4, 5
        ncols = len(rows[0])
        widths = []
        for j in range(ncols):
            w = max(pdfmetrics.stringWidth(str(r[j]), FONT, size) for r in rows) + pad * 2
            widths.append(max(min(w, CONTENT_W * 0.55), 48))
        scale = CONTENT_W / sum(widths)
        widths = [w * scale for w in widths]

        def row_height(row):
            h = 0
            for j, val in enumerate(row):
                lines = _wrap(str(val), size, widths[j] - pad * 2)
                h = max(h, len(lines) * 13.5 + 8.0)
            return h

        header = rows[0]
        head_h = (18 if caption else 0) + row_height(header) \
            + sum(row_height(r) for r in rows[1:3])
        self.need(head_h)
        if caption:
            self.c.setFillColorRGB(*PRIMARY)
            self.c.setFont(FONT, 9.0)
            self.c.drawString(MARGIN_L, self.y - 10, caption)
            self.y -= 18

        def draw_row(row, is_header):
            h = row_height(row)
            x = MARGIN_L
            if is_header:
                self.c.setFillColorRGB(*FILL_HEADER)
                self.c.rect(MARGIN_L, self.y - h, CONTENT_W, h, stroke=0, fill=1)
                self.c.setStrokeColorRGB(*LIGHT)
                self.c.setLineWidth(0.5)
                self.c.line(MARGIN_L, self.y, MARGIN_L + CONTENT_W, self.y)
            self.c.setStrokeColorRGB(*LIGHT)
            self.c.setLineWidth(0.5)
            self.c.line(MARGIN_L, self.y - h, MARGIN_L + CONTENT_W, self.y - h)
            self.c.setFont(FONT, size)
            self.c.setFillColorRGB(*(PRIMARY if is_header else BODY_COLOR))
            for j, val in enumerate(row):
                lines = _wrap(str(val), size, widths[j] - pad * 2)
                ty = self.y
                for ln in lines:
                    if not is_header and j > 0 and ln and all(
                            ch in "0123456789,.%△+－-()倍年hx約" for ch in ln):
                        self.c.drawRightString(x + widths[j] - pad, ty - 12.1, ln)
                    else:
                        self.c.drawString(x + pad, ty - 12.1, ln)
                    ty -= 13.5
                x += widths[j]
            self.y -= h

        draw_row(header, True)
        for row in rows[1:]:
            h = row_height(row)
            if self.y - h < BODY_BOTTOM:
                self.cont_slide()
                draw_row(header, True)
            draw_row(row, False)
        self.y -= 10


DISCLAIMER = [
    "本報告書は、日本橋キャピタルパートナーズ株式会社（以下「依頼者」）の依頼に基づき、"
    "株式会社オートスタッフ中部に関する事業面および財務面のデューデリジェンスの結果を"
    "単一の報告書として取りまとめたものであり、依頼者による本件取引の検討以外の目的で"
    "使用することはできません。",
    "本報告書は、対象会社から開示を受けた資料および対象会社の役職員に対する"
    "インタビューの内容に依拠して作成されています。当社は、開示資料の真実性・"
    "網羅性について独自の検証を行っておらず、これらを保証するものではありません。",
    "本報告書の記載内容は調査基準日（2026年5月31日）時点の情報に基づくものであり、"
    "その後の状況の変化により影響を受ける可能性があります。",
    "本報告書に記載する財務数値の単位は、注記のない限りすべて千円です。"
    "対象会社の財務モデル（Excel）と同一の単位系を採用しています。",
    "本報告書の全部または一部を、当社の事前の書面による同意なく第三者に開示・"
    "引用・複製することはできません。ただし、依頼者が本件のファイナンスを検討する"
    "金融機関に対して守秘義務を条件に開示することを妨げません。",
]


def check_banned():
    def walk(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, (list, tuple)):
            for x in obj:
                yield from walk(x)
        elif isinstance(obj, dict):
            for x in obj.values():
                yield from walk(x)
    hits = []
    for text in walk(C.PAGES):
        for b in C.BANNED_STRINGS:
            if b in text:
                hits.append((b, text[:60]))
    for text in DISCLAIMER + list(C.DOC_META.values()):
        for b in C.BANNED_STRINGS:
            if b in text:
                hits.append((b, text[:60]))
    if hits:
        raise RuntimeError(f"禁止文字列が混入: {hits[:5]}")


def render_body(c, first_page_no):
    deck = Deck(c, first_page_no)
    for section in C.PAGES:
        for block in section["blocks"]:
            kind, arg = block[0], block[1]
            if kind == "h1":
                deck.chapter_divider(arg, section.get("toc"), section.get("part"))
            elif kind == "h2":
                deck.h2(arg)
            elif kind == "p":
                deck.lead_or_para(arg)
            elif kind == "note":
                deck.note(arg)
            elif kind == "bullets":
                deck.bullets(arg)
            elif kind == "callout":
                deck.callout(arg)
            elif kind == "captable":
                deck.captable(arg[0], arg[1])
            elif kind == "table":
                deck.table(arg)
            else:
                raise ValueError(f"unknown block: {kind}")
    return deck


def render() -> tuple[int, int]:
    meta = C.DOC_META
    # ---- パス1：章の実ページ・総ページ数・図表数を確定
    dummy = canvas.Canvas(io.BytesIO(), pagesize=landscape(A4))
    probe = render_body(dummy, first_page_no=4)
    chapter_pages = probe.chapter_pages
    total_pages = probe.page_no
    table_count = probe.table_count

    # ---- パス2：本描画
    c = canvas.Canvas(str(OUT_PATH), pagesize=landscape(A4))
    c.setTitle(meta["title"])
    c.setAuthor(meta["firm"])

    # p.1 表紙
    c.setFillColorRGB(*PRIMARY)
    c.setFont(FONT, 24)
    c.drawCentredString(PAGE_W / 2, 380, meta["title"])
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(FONT, 16)
    c.drawCentredString(PAGE_W / 2, 344, meta["subtitle"])
    c.setFont(FONT, 10.5)
    c.setFillColorRGB(*GRAY)
    c.drawCentredString(PAGE_W / 2, 306, "（Project Gear）　事業編・財務編 合冊　／　金額単位：千円")
    c.setFillColorRGB(*BODY_COLOR)
    c.setFont(FONT, 11)
    c.drawCentredString(PAGE_W / 2, 180, meta["firm"])
    c.drawCentredString(PAGE_W / 2, 160, meta["date"])
    c.setFont(FONT, 9)
    c.setFillColorRGB(0.72, 0.11, 0.11)
    c.drawCentredString(PAGE_W / 2, 96, "Confidential — 取扱厳重注意")
    c.showPage()

    # p.2 免責事項
    deck2 = Deck(c, 2)
    deck2._started = True
    deck2.page_no = 1
    deck2._chrome("本報告書の利用に関する重要な注意事項", None)
    for para in DISCLAIMER:
        deck2.para(para)
    c.showPage()

    # p.3 目次
    deck3 = Deck(c, 3)
    deck3._started = True
    deck3.page_no = 2
    deck3._chrome("目次", None)
    col_x = [MARGIN_L, PAGE_W / 2 + 10]
    col_w = PAGE_W / 2 - MARGIN_L - 30
    y_start = deck3.y
    col, y = 0, y_start
    for toc, part, page_no in chapter_pages:
        if y < BODY_BOTTOM + 40:
            col, y = 1, y_start
        x = col_x[col]
        if part:
            c.setFillColorRGB(*PRIMARY)
            c.setFont(FONT, 10.5)
            c.drawString(x, y - 12, f"【{part}】")
            y -= 22
        c.setFillColorRGB(*BODY_COLOR)
        c.setFont(FONT, 9.8)
        c.drawString(x + 8, y - 10, toc)
        c.drawRightString(x + col_w, y - 10, str(page_no))
        c.setStrokeColorRGB(*LIGHT)
        c.setLineWidth(0.4)
        c.line(x + 8, y - 14, x + col_w, y - 14)
        y -= 24
    c.setFillColorRGB(*GRAY)
    c.setFont(FONT, 8)
    c.drawString(MARGIN_L, BODY_BOTTOM - 8,
                 "※ 表紙・注意事項・目次はページ1〜3。金額単位は注記のない限り千円。")
    c.showPage()

    # p.4〜 本文
    body = render_body(c, first_page_no=4)
    assert body.page_no == total_pages and body.table_count == table_count
    c.save()
    return total_pages, table_count


def register_planted(total, table_count):
    fname = "A_standard/DD_Report_統合版_オートスタッフ中部_A.pdf"
    planted = [
        dict(id="D1", dataset="A", file=fname, sheet="-", cell=f"全{total}ページ",
             desc=f"統合版DD（単一分冊・{total}ページ・図表{table_count}点・横置きスライド形式）",
             expect="自動処理"),
        dict(id="D2", dataset="A", file=fname, sheet="2章/4章/5章/6章/9章", cell="-",
             desc="計画前提（稼働率・単価改定・CPA・採用人数）が複数章に分散して記載", expect="自動処理"),
        dict(id="E6", dataset="A", file=fname, sheet="全編", cell="-",
             desc="業界用語15語（稼働率・派遣単価・スプレッド・在籍登録スタッフ・稼働人数・"
                  "採用単価（CPA）・リファラル・離職率・法定福利費率・労使協定方式・構内請負・"
                  "コーディネーター・寮・送迎・早期離職率）", expect="自動処理"),
        dict(id="X2", dataset="A", file=fname, sheet="-", cell="-",
             desc="単位系の統一：DD・Excelとも千円（月次試算表のみ円・ラベル明記）→資料間不一致0件",
             expect="自動処理"),
        dict(id="X3", dataset="A", file=fname, sheet="7.6節", cell="-",
             desc="のれん想定額はExcel・DDとも5,500,000千円で一致（数値の食い違いなし）",
             expect="自動処理"),
    ]
    BUILD.mkdir(exist_ok=True)
    (BUILD / "planted_items_dd.json").write_text(
        json.dumps(planted, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    font = register_font()
    print(f"font: {font}")
    check_banned()
    total, tables = render()
    register_planted(total, tables)
    print(f"generated: {OUT_PATH.name} ({total} pages, {tables} tables)")
    if total < 60:
        raise RuntimeError(f"ページ数不足: {total} < 60")
    if tables < 30:
        raise RuntimeError(f"表数不足: {tables} < 30")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
