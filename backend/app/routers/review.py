"""レビュー系API：数値確定（S3）・KPI構造（S4）・シナリオ（S5）・チャット差分適用。"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..extractors import get_extractor
from ..models import Deal, ExtractedItem, KpiNode, Scenario
from ..services.staleness import propagate_item_change, propagate_kpi_change
from .deals import add_history

router = APIRouter(prefix="/api/deals/{deal_id}", tags=["review"])


def _deal(db: Session, deal_id: int) -> Deal:
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404, "案件が見つかりません")
    return deal


# ---------------------------------------------------------------- 数値確定（S3）

class ItemAction(BaseModel):
    action: str  # confirm / hold / unconfirm
    user: str
    values: dict | None = None       # 修正して確定する場合の値（年度→値）
    text_value: str | None = None    # 定性項目の修正
    resolution_note: str | None = None  # 不整合の解決メモ（どちらを採ったか）


class BulkConfirmBody(BaseModel):
    item_ids: list[int]
    user: str


@router.post("/items/bulk-confirm")
def items_bulk_confirm(deal_id: int, body: BulkConfirmBody,
                       db: Session = Depends(get_db)):
    """選択した抽出項目を「そのまま確定」で一括確定する。

    値の修正・不整合の値選択が必要な項目は対象外（個別確定を使う）。
    確定済みの項目はスキップする。初回確定のみなので下流への警告は出さない。
    """
    deal = _deal(db, deal_id)
    ids = set(body.item_ids)

    def _needs_choice(it: ExtractedItem) -> bool:
        """不整合の値選択（モデル値/DD値）が必要な項目か。フロントのUIガードと同条件をサーバー側でも担保"""
        if not it.mismatch_json:
            return False
        try:
            mm = json.loads(it.mismatch_json)
        except ValueError:
            return False
        if not isinstance(mm, dict):
            return False
        return (isinstance(mm.get("other_value"), (int, float))
                and len(it.effective_values() or {}) == 1)

    # 一括確定できるのは「提案中」のみ。保留（held）と不整合の値選択待ちは個別確定を使う
    targets = [it for it in deal.items
               if it.id in ids and it.status == "proposed" and not _needs_choice(it)]
    if not targets:
        raise HTTPException(400, "一括確定できる項目がありません"
                                 "（保留中・不整合の値選択待ちの項目は個別に確定してください）")
    now = datetime.now()
    for item in targets:
        item.status = "confirmed"
        item.confirmed_by = body.user
        item.confirmed_at = now
    labels = [it.label for it in targets]
    digest = "、".join(labels[:5]) + ("" if len(labels) <= 5 else f" ほか{len(labels) - 5}項目")
    add_history(db, deal, body.user, "抽出値をまとめて確定", f"{len(labels)}項目（{digest}）")
    db.commit()
    return dict(confirmed=len(targets), deal=deal.to_dict())


@router.post("/items/{item_id}/action")
def item_action(deal_id: int, item_id: int, body: ItemAction,
                db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    item: ExtractedItem | None = db.get(ExtractedItem, item_id)
    if not item or item.deal_id != deal.id:
        raise HTTPException(404, "抽出項目が見つかりません")

    downstream_exists = deal.kpi_status == "confirmed" or any(deal.scenarios)
    old_values = item.effective_values()
    old_text = item.effective_text()
    was_confirmed = item.status == "confirmed"

    if body.action == "confirm":
        edited = False
        if body.values is not None and body.values != (item.effective_values() or {}):
            item.confirmed_values_json = json.dumps(body.values, ensure_ascii=False)
            edited = True
        if body.text_value is not None and body.text_value != (item.effective_text() or ""):
            item.confirmed_text = body.text_value
            edited = True
        if edited:
            item.edited = True
        item.status = "confirmed"
        item.confirmed_by = body.user
        item.confirmed_at = datetime.now()
        if body.resolution_note is not None:
            item.resolution_note = body.resolution_note
        action_label = "修正して確定" if edited else "確定"
        add_history(db, deal, body.user, f"抽出値を{action_label}", item.label)
        # 確定済みの値を変更した場合のみ下流に警告（初回確定では警告しない）
        if was_confirmed and edited and downstream_exists:
            reason = _change_reason(item, old_values, old_text)
            propagate_item_change(deal, reason)
    elif body.action == "hold":
        item.status = "held"
        item.confirmed_by = None
        item.confirmed_at = None
        add_history(db, deal, body.user, "抽出値を保留", item.label)
        if was_confirmed and downstream_exists:
            propagate_item_change(deal, f"確定済みの「{item.label}」が保留に変更されました")
    elif body.action == "unconfirm":
        item.status = "proposed"
        item.confirmed_by = None
        item.confirmed_at = None
        add_history(db, deal, body.user, "抽出値の確定を解除", item.label)
        if was_confirmed and downstream_exists:
            propagate_item_change(deal, f"確定済みの「{item.label}」の確定が解除されました")
    else:
        raise HTTPException(400, f"不明なアクション: {body.action}")

    db.commit()
    return dict(item=item.to_dict(), deal=deal.to_dict())


def _change_reason(item: ExtractedItem, old_values, old_text) -> str:
    new_values = item.effective_values()
    if old_values and new_values:
        for y in new_values:
            if old_values.get(y) != new_values.get(y):
                return (f"上流の確定値が変更されています"
                        f"（{item.label} {y}：{old_values.get(y):,} → {new_values.get(y):,}）")
    return f"上流の確定値が変更されています（{item.label}）"


# ---------------------------------------------------------------- KPI構造（S4）

class UserBody(BaseModel):
    user: str


@router.post("/kpi/confirm")
def kpi_confirm(deal_id: int, body: UserBody, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    if not deal.required_items_confirmed():
        raise HTTPException(400, "必須項目がすべて確定されていません（ステージ1を完了してください）")
    deal.kpi_status = "confirmed"
    deal.kpi_confirmed_by = body.user
    deal.kpi_confirmed_at = datetime.now()
    deal.kpi_stale_reason = None
    stars = len([n for n in deal.kpi_nodes if n.star])
    add_history(db, deal, body.user, "KPI構造確定",
                f"{len(deal.kpi_nodes)}ノード・★{stars}件で確定")
    db.commit()
    return dict(deal=deal.to_dict())


@router.post("/kpi/clear-stale")
def kpi_clear_stale(deal_id: int, body: UserBody, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    deal.kpi_stale_reason = None
    add_history(db, deal, body.user, "KPIの上流変更警告を確認", "内容を再確認し警告を解除")
    db.commit()
    return dict(deal=deal.to_dict())


class DiffBody(BaseModel):
    diff: dict
    user: str


@router.post("/kpi/apply")
def kpi_apply(deal_id: int, body: DiffBody, db: Session = Depends(get_db)):
    """チャット差分の適用（人が「適用」を押した時のみ反映。直接反映はしない）。"""
    deal = _deal(db, deal_id)
    diff = body.diff
    was_confirmed = deal.kpi_status == "confirmed"
    if diff.get("type") == "add_node":
        n = diff.get("node")
        if not isinstance(n, dict) or not n.get("id") or not n.get("label"):
            raise HTTPException(400, "差分の形式が不正です（nodeにidとlabelが必要）。"
                                     "チャットで指示を言い換えて再生成してください")
        if any(k.node_id == n["id"] for k in deal.kpi_nodes):
            raise HTTPException(400, "同じKPIが既に存在します")
        db.add(KpiNode(
            deal_id=deal.id, node_id=n["id"], parent_id=n.get("parent"),
            label=n["label"], origin=n.get("origin", "manual"), star=n.get("star", False),
            formula=n.get("formula"), value_text=n.get("value_text"), badge=n.get("badge"),
            evidence_json=json.dumps(n.get("evidence"), ensure_ascii=False),
            added_via_chat=True,
            order_index=max([k.order_index for k in deal.kpi_nodes], default=0) + 1))
        detail = f"「{n['label']}」を追加（チャット適用）"
    elif diff.get("type") == "star_change":
        # スキーマ上 remove/add は null があり得る（in None は TypeError）
        remove = diff.get("remove") or []
        add = diff.get("add") or []
        for node in deal.kpi_nodes:
            if node.node_id in remove:
                node.star = False
            if node.node_id in add:
                node.star = True
        detail = "重要KPI（★）を変更（チャット適用）"
    else:
        raise HTTPException(400, f"不明な差分タイプ: {diff.get('type')}")
    add_history(db, deal, body.user, "KPI構造を修正", detail)
    if was_confirmed:
        propagate_kpi_change(deal, f"確定済みKPI構造が変更されました（{detail}）")
    db.commit()
    return dict(kpi_nodes=[n.to_dict() for n in deal.kpi_nodes], deal=deal.to_dict())


# ---------------------------------------------------------------- チャット

class ChatBody(BaseModel):
    context: str  # kpi / scenario
    message: str
    user: str
    target: str | None = None  # 対象（シナリオkey または KPIノードid）。未選択はNone


@router.post("/chat")
def chat(deal_id: int, body: ChatBody, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    state = dict(
        node_ids=[n.node_id for n in deal.kpi_nodes],
        card_keys=[s.key for s in deal.scenarios],
        stars=[n.node_id for n in deal.kpi_nodes if n.star],
        target=body.target,
    )
    result = get_extractor().chat(body.context, body.message, state)
    target_label = f"（対象: {body.target}）" if body.target else ""
    add_history(db, deal, body.user, "チャット指示",
                f"[{body.context}]{target_label} {body.message[:60]}")
    db.commit()
    return result


# ---------------------------------------------------------------- シナリオ（S5）

class AdoptBody(BaseModel):
    adopted: bool
    user: str
    rejection_note: str | None = None


@router.post("/scenarios/{key}/adopt")
def scenario_adopt(deal_id: int, key: str, body: AdoptBody, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    sc = next((s for s in deal.scenarios if s.key == key), None)
    if not sc:
        raise HTTPException(404, "シナリオが見つかりません")
    sc.adopted = body.adopted
    if body.rejection_note is not None:
        sc.rejection_note = body.rejection_note
    sc.updated_at = datetime.now()
    add_history(db, deal, body.user,
                "シナリオ採用" if body.adopted else "シナリオ不採用",
                f"シナリオ{sc.key}：{sc.title}")
    db.commit()
    return dict(scenario=sc.to_dict(), deal=deal.to_dict())


@router.post("/scenarios/{key}/clear-stale")
def scenario_clear_stale(deal_id: int, key: str, body: UserBody,
                         db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    sc = next((s for s in deal.scenarios if s.key == key), None)
    if not sc:
        raise HTTPException(404, "シナリオが見つかりません")
    sc.stale_reason = None
    add_history(db, deal, body.user, "シナリオの上流変更警告を確認",
                f"シナリオ{sc.key}を再確認し警告を解除")
    db.commit()
    return dict(scenario=sc.to_dict())


@router.post("/scenarios/apply")
def scenarios_apply(deal_id: int, body: DiffBody, db: Session = Depends(get_db)):
    """シナリオへのチャット差分適用（追加 or 修正）。"""
    deal = _deal(db, deal_id)
    diff = body.diff
    if diff.get("type") == "add_card":
        c = diff.get("card")
        if not isinstance(c, dict) or not c.get("key") or not c.get("title"):
            raise HTTPException(400, "差分の形式が不正です（cardにkeyとtitleが必要）。"
                                     "チャットで指示を言い換えて再生成してください")
        if any(s.key == c["key"] for s in deal.scenarios):
            raise HTTPException(400, "同じシナリオが既に存在します")
        sc = Scenario(
            deal_id=deal.id, key=c["key"], origin=c.get("origin", "human"),
            type_label=c.get("type_label"), title=c["title"], cause=c.get("cause"),
            affected_kpis_json=json.dumps(c.get("affected_kpis", []), ensure_ascii=False),
            change_text=c.get("change") or c.get("change_text"),
            change_basis=c.get("change_basis"), impact=c.get("impact"),
            safeguards=c.get("safeguards"), questions=c.get("questions"),
            adopted=False,
            order_index=max([s.order_index for s in deal.scenarios], default=0) + 1)
        db.add(sc)
        db.flush()
        add_history(db, deal, body.user, "シナリオ追加（チャット適用）",
                    f"シナリオ{sc.key}：{sc.title}")
        db.commit()
        return dict(scenario=sc.to_dict(), deal=deal.to_dict())
    if diff.get("type") == "update_card":
        sc = next((s for s in deal.scenarios if s.key == diff.get("card_key")), None)
        if not sc:
            raise HTTPException(404, "対象シナリオが見つかりません")
        fields = diff.get("fields") or {}
        mapping = dict(change="change_text", change_text="change_text", cause="cause",
                       change_basis="change_basis", impact="impact",
                       safeguards="safeguards", questions="questions", title="title")
        changed = []
        for k, v in fields.items():
            attr = mapping.get(k)
            if attr:
                setattr(sc, attr, v)
                changed.append(k)
        sc.updated_at = datetime.now()
        sc.stale_reason = None  # 修正＝再確認とみなし警告を解除
        add_history(db, deal, body.user, "シナリオ修正（チャット適用）",
                    f"シナリオ{sc.key}：{'、'.join(changed)}を更新")
        db.commit()
        return dict(scenario=sc.to_dict(), deal=deal.to_dict())
    raise HTTPException(400, f"不明な差分タイプ: {diff.get('type')}")
