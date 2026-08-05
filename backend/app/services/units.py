"""金額単位の正規化（仕様 ③4）。

- AIは元資料の単位のまま値を返す（unitに元単位を記載）
- システム側で表示単位（百万円）へ換算して保持する。元単位は source_unit に残す
- 金額以外の単位（%・名・円/h・h 等）は換算しない
"""

# 金額単位 → 百万円への換算係数
_MONEY_FACTORS = {
    "円": 1 / 1_000_000,
    "千円": 1 / 1_000,
    "万円": 1 / 100,
    "百万円": 1.0,
    "百万": 1.0,
    "億円": 100.0,
    "億": 100.0,
    "十億円": 1_000.0,
}

DISPLAY_MONEY_UNIT = "百万円"


def is_money_unit(unit: str | None) -> bool:
    return (unit or "").strip() in _MONEY_FACTORS


def normalize_values(values: dict | None, unit: str | None) -> tuple[dict | None, str, str | None]:
    """values（年度→数値）を表示単位へ正規化する。

    戻り値: (正規化後values, 表示unit, source_unit)
    - 金額単位: 百万円へ換算。source_unit に元単位を記録
    - 非金額単位（%・名・円/h等）: 換算せずそのまま
    """
    unit = (unit or "").strip()
    if not values or not is_money_unit(unit):
        return values, unit, None
    factor = _MONEY_FACTORS[unit]
    if factor == 1.0:
        return values, DISPLAY_MONEY_UNIT, unit if unit != DISPLAY_MONEY_UNIT else None
    out = {}
    for year, v in values.items():
        if isinstance(v, (int, float)):
            converted = v * factor
            # 浮動小数の表示ノイズを防ぐ（小数6桁あれば円→百万円でも1円単位まで可逆）
            out[year] = round(converted, 6)
        else:
            out[year] = v
    return out, DISPLAY_MONEY_UNIT, unit
