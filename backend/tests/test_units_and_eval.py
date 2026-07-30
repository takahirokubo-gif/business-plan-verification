"""単位正規化（services/units）と数式評価エンジン（services/xl_eval）のテスト。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook  # noqa: E402

from app.services.units import normalize_values  # noqa: E402
from app.services.xl_eval import XlEvaluator, excel_round  # noqa: E402


def test_normalize_thousand_yen_to_million():
    values, unit, source_unit = normalize_values({"FY26": 14_160_000}, "千円")
    assert values == {"FY26": 14_160.0}
    assert unit == "百万円"
    assert source_unit == "千円"


def test_normalize_million_passthrough():
    values, unit, source_unit = normalize_values({"FY26": 14_160}, "百万円")
    assert values == {"FY26": 14_160}
    assert unit == "百万円"
    assert source_unit is None


def test_normalize_non_money_unchanged():
    values, unit, source_unit = normalize_values({"FY26": 88}, "%")
    assert values == {"FY26": 88}
    assert unit == "%"
    assert source_unit is None


def test_excel_round_half_away_from_zero():
    assert excel_round(0.5) == 1
    assert excel_round(-0.5) == -1
    assert excel_round(2.345, 2) == 2.35


def _wb():
    wb = Workbook()
    ws = wb.active
    ws.title = "PL"
    ws["C7"] = 100
    ws["C8"] = 23
    ws["C9"] = "=SUM(C7:C8)"
    ws["C10"] = "=-ROUND(C9*0.31,0)"
    ws["C11"] = "=C9+C10"
    ws2 = wb.create_sheet("calc")
    ws2["C5"] = "=PL!C9*2"
    ws["D9"] = "=#REF!D12"
    return wb


def test_evaluator_computes_formula_chain():
    ev = XlEvaluator(_wb())
    assert ev.value("PL", "C9") == 123
    assert ev.value("PL", "C10") == -38          # ROUND(123*0.31)=38 → 負値
    assert ev.value("PL", "C11") == 85
    assert ev.value("calc", "C5") == 246         # シート間参照


def test_evaluator_marks_broken_ref():
    ev = XlEvaluator(_wb())
    assert ev.value("PL", "D9") is None
    assert ev.is_broken("PL", "D9")
    assert ("PL", "D9") in ev.broken
