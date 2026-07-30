"""Excel数式のシステム側評価エンジン。

目的（仕様 ③1「数値取得の3段フォールバック」の②を担保する）:
- Excelにキャッシュ値（Excel保存時の計算結果）が無い数式セルについて、
  資料内の数式から一意に定まる値をシステム側で計算し「計算値」としてAIに渡す。
- AI自身には再計算をさせない原則は維持したまま、
  「記載あり or 一意に計算可能 → 抽出扱い」というプロダクト仕様を実現する。

対応する数式: 四則演算・括弧・単項マイナス・SUM(範囲)・ROUND(x, n)・シート間参照。
#REF! を含む数式は「参照切れ」として明示的に区別する（照会の材料になる）。
"""
import math
import re


def excel_round(x: float, digits: int = 0) -> float:
    """ExcelのROUND（0.5は0から遠い方へ）。Pythonのroundは銀行丸めのため使わない。"""
    factor = 10 ** digits
    v = x * factor
    r = math.floor(v + 0.5) if v >= 0 else math.ceil(v - 0.5)
    return r / factor if digits else float(int(r))


BROKEN = "#REF!"

_REF_RE = re.compile(r"(?:(?P<sheet>[^\s!+\-*/(),:'\"]+)!)?\$?(?P<col>[A-Z]{1,2})\$?(?P<row>\d+)")


class XlEvaluator:
    """openpyxlワークブック（数式モード）を受け取り、セル値を遅延評価する。"""

    def __init__(self, wb):
        self.wb = wb
        self.memo: dict[tuple[str, str], object] = {}
        self.broken: set[tuple[str, str]] = set()

    def value(self, sheet: str, coord: str):
        """セルの評価値を返す。数式エラー・参照切れ・評価不能は None。"""
        key = (sheet, coord)
        if key in self.memo:
            v = self.memo[key]
            return None if v == "#CYCLE#" else v
        self.memo[key] = "#CYCLE#"
        try:
            cell = self.wb[sheet][coord]
        except KeyError:
            self.memo[key] = None
            return None
        v = cell.value
        if isinstance(v, str) and v.startswith("="):
            if BROKEN in v:
                self.broken.add(key)
                self.memo[key] = None
                return None
            try:
                result = self._eval_expr(v[1:], sheet)
            except Exception:
                result = None
            self.memo[key] = result
            return result
        self.memo[key] = v
        return v

    def is_broken(self, sheet: str, coord: str) -> bool:
        cell_v = None
        try:
            cell_v = self.wb[sheet][coord].value
        except KeyError:
            return False
        return isinstance(cell_v, str) and BROKEN in cell_v

    # ---- パーサ（再帰下降・再入可能） ----
    def _eval_expr(self, s: str, sheet: str) -> float:
        saved = (getattr(self, "_s", None), getattr(self, "_pos", None),
                 getattr(self, "_sheet", None))
        self._s, self._pos, self._sheet = s, 0, sheet
        try:
            v = self._expr()
            if self._pos != len(self._s):
                raise ValueError(f"parse error at {self._pos}: {s}")
            return v
        finally:
            self._s, self._pos, self._sheet = saved

    def _peek(self) -> str:
        # 終端は "\0"（空文字だと `"" in "+-"` がTrueになり誤動作する）
        return self._s[self._pos] if self._pos < len(self._s) else "\0"

    def _expr(self) -> float:
        v = self._term()
        while self._peek() in "+-":
            op = self._s[self._pos]
            self._pos += 1
            rhs = self._term()
            v = v + rhs if op == "+" else v - rhs
        return v

    def _term(self) -> float:
        v = self._factor()
        while self._peek() in "*/":
            op = self._s[self._pos]
            self._pos += 1
            rhs = self._factor()
            v = v * rhs if op == "*" else v / rhs
        return v

    def _factor(self) -> float:
        ch = self._peek()
        if ch == "-":
            self._pos += 1
            return -self._factor()
        if ch == "+":
            self._pos += 1
            return self._factor()
        if ch == "(":
            self._pos += 1
            v = self._expr()
            if self._peek() != ")":
                raise ValueError("missing )")
            self._pos += 1
            return v
        m = re.match(r"(SUM|ROUND)\(", self._s[self._pos:])
        if m:
            fname = m.group(1)
            self._pos += len(fname) + 1
            if fname == "SUM":
                return self._sum_range(self._read_until_close())
            inner = self._read_until_close()
            expr, _, digits = inner.rpartition(",")
            x = self._eval_expr(expr, self._sheet)
            return excel_round(x, int(digits))
        num_m = re.match(r"\d+(\.\d+)?", self._s[self._pos:])
        ref_m = _REF_RE.match(self._s, self._pos)
        if ref_m and (not num_m or ref_m.end() > self._pos + num_m.end()):
            self._pos = ref_m.end()
            sheet = ref_m.group("sheet") or self._sheet
            sheet = sheet.strip("'")
            v = self.value(sheet, f"{ref_m.group('col')}{ref_m.group('row')}")
            if v is None or isinstance(v, str):
                raise ValueError(f"unresolved ref {sheet}!{ref_m.group('col')}{ref_m.group('row')}")
            return float(v)
        if num_m:
            self._pos += num_m.end()
            return float(num_m.group(0))
        raise ValueError(f"unexpected char at {self._pos}: {self._s}")

    def _read_until_close(self) -> str:
        start = self._pos
        depth = 1
        while depth:
            if self._pos >= len(self._s):
                raise ValueError("missing )")
            c = self._s[self._pos]
            depth += 1 if c == "(" else (-1 if c == ")" else 0)
            self._pos += 1
        return self._s[start:self._pos - 1]

    def _sum_range(self, rng: str) -> float:
        from openpyxl.utils import column_index_from_string, get_column_letter
        from openpyxl.utils.cell import coordinate_from_string
        sheet = self._sheet
        if "!" in rng:
            sheet, rng = rng.split("!", 1)
            sheet = sheet.strip("'")
        a, _, b = rng.partition(":")
        if not b:
            b = a
        c1, r1 = coordinate_from_string(a.replace("$", ""))
        c2, r2 = coordinate_from_string(b.replace("$", ""))
        i1, i2 = column_index_from_string(c1), column_index_from_string(c2)
        total = 0.0
        for r in range(min(r1, r2), max(r1, r2) + 1):
            for i in range(min(i1, i2), max(i1, i2) + 1):
                v = self.value(sheet, f"{get_column_letter(i)}{r}")
                if isinstance(v, (int, float)):
                    total += float(v)
        return total
