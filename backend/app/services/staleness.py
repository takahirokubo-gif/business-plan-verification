"""巻き戻しルール（警告型）の実装。

上流の確定値が変更・確定解除されても下流（KPI構造・シナリオ）は無効化しない。
各要素に「上流が変更されています」の警告（stale_reason）を付け、再確認を促すのみ。
審査相談の反復の中で上流修正は日常的に起きるため、作業を壊さないことを優先する。
"""
from datetime import datetime

from ..models import Deal


def propagate_item_change(deal: Deal, reason: str):
    """確定済み抽出値の変更 → KPI（確定済みなら）とシナリオ全カードに警告。"""
    if deal.kpi_status == "confirmed":
        deal.kpi_stale_reason = reason
    for sc in deal.scenarios:
        sc.stale_reason = reason
    deal.updated_at = datetime.now()


def propagate_kpi_change(deal: Deal, reason: str):
    """確定済みKPI構造の変更 → シナリオ全カードに警告。"""
    for sc in deal.scenarios:
        sc.stale_reason = reason
    deal.updated_at = datetime.now()
