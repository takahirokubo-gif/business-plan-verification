"""出力系API：Excelエクスポート（S6）・審査相談メモ（S7）。"""
import urllib.parse
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Deal, ExportRecord, Memo, MemoFinding, REVIEW_STATUSES
from ..services.export_xlsx import build_export
from .deals import add_history

router = APIRouter(prefix="/api/deals/{deal_id}", tags=["output"])


def _deal(db: Session, deal_id: int) -> Deal:
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404, "案件が見つかりません")
    return deal


@router.get("/export/preview")
def export_preview(deal_id: int, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    held = [i for i in deal.items if i.status == "held"]
    return dict(
        can_export=deal.required_items_confirmed() and deal.kpi_status == "confirmed",
        required_confirmed=deal.required_items_confirmed(),
        kpi_confirmed=deal.kpi_status == "confirmed",
        adopted_scenarios=len([s for s in deal.scenarios if s.adopted]),
        held_items=[dict(key=i.key, label=i.label) for i in held],
        stale_warnings=bool(deal.kpi_stale_reason)
        or any(s.stale_reason for s in deal.scenarios if s.adopted),
    )


class ExportBody(BaseModel):
    user: str


@router.post("/export")
def export(deal_id: int, body: ExportBody, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    if not deal.required_items_confirmed():
        raise HTTPException(400, "必須項目がすべて確定されていません")
    if deal.kpi_status != "confirmed":
        raise HTTPException(400, "KPI構造が確定されていません")
    path, excluded = build_export(deal)
    filename = Path(path).name
    db.add(ExportRecord(deal_id=deal.id, at=datetime.now(), user_key=body.user,
                        filename=filename, excluded_held=excluded))
    add_history(db, deal, body.user, "Excel出力",
                f"{filename}" + (f"（保留{excluded}項目を除外）" if excluded else ""))
    db.commit()
    quoted = urllib.parse.quote(filename)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


class FindingBody(BaseModel):
    target_type: str | None = None  # scenario / item / kpi
    target_key: str | None = None
    text: str


class MemoBody(BaseModel):
    meeting_date: str
    attendees: list[str] = []
    conclusion: str  # 続行 / 再検討 / 推進 / 保留 / 見送り
    note: str | None = None
    findings: list[FindingBody] = []
    update_review_status: bool = False  # 結論に連動して検討ステータスを更新（確認ダイアログ済み）
    user: str


CONCLUSION_TO_STATUS = {
    "再検討": "再検討中",
    "推進": "推進",
    "保留": "保留",
    "見送り": "見送り",
    # 「続行」はステータス変更なし
}


@router.post("/memos")
def create_memo(deal_id: int, body: MemoBody, db: Session = Depends(get_db)):
    deal = _deal(db, deal_id)
    import json as _json
    memo = Memo(deal_id=deal.id, meeting_date=body.meeting_date,
                attendees_json=_json.dumps(body.attendees, ensure_ascii=False),
                conclusion=body.conclusion, note=body.note,
                created_by=body.user, created_at=datetime.now())
    db.add(memo)
    db.flush()
    for f in body.findings:
        db.add(MemoFinding(memo_id=memo.id, deal_id=deal.id,
                           target_type=f.target_type, target_key=f.target_key,
                           text=f.text))
    detail = f"{body.meeting_date} 審査相談：{body.conclusion}"
    if body.findings:
        detail += f"（指摘{len(body.findings)}件）"
    status_changed = None
    if body.update_review_status:
        new_status = CONCLUSION_TO_STATUS.get(body.conclusion)
        if new_status and new_status in REVIEW_STATUSES and new_status != deal.review_status:
            old = deal.review_status
            deal.review_status = new_status
            status_changed = dict(from_status=old, to_status=new_status)
            detail += f"／ステータスを{old}→{new_status}へ変更"
    add_history(db, deal, body.user, "審査相談メモ登録", detail)
    db.commit()
    return dict(memo=memo.to_dict(), deal=deal.to_dict(), status_changed=status_changed)
