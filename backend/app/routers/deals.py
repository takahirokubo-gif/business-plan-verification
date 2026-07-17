"""案件（S1/S2）と資料アップロード・AI解析のAPI。"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR
from ..database import get_db
from ..extractors import get_extractor
from ..extractors.base import UnknownSampleFileError
from ..models import (Deal, Document, ExtractedItem, HistoryEvent, KpiNode,
                      Scenario, User)

router = APIRouter(prefix="/api", tags=["deals"])


def add_history(db: Session, deal: Deal, user: str | None, action: str, detail: str = ""):
    db.add(HistoryEvent(deal_id=deal.id, at=datetime.now(), user_key=user,
                        action=action, detail=detail))
    deal.updated_at = datetime.now()


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [u.to_dict() for u in db.query(User).all()]


@router.get("/deals")
def list_deals(review_status: str | None = None, work_status: str | None = None,
               db: Session = Depends(get_db)):
    deals = db.query(Deal).order_by(Deal.updated_at.desc()).all()
    out = [d.to_list_dict() for d in deals]
    if review_status:
        out = [d for d in out if d["review_status"] == review_status]
    if work_status:
        out = [d for d in out if d["work_status"] == work_status]
    counts = {}
    for d in deals:
        counts[d.review_status] = counts.get(d.review_status, 0) + 1
    return dict(deals=out, counts=counts, total=len(deals))


class DealCreate(BaseModel):
    name: str
    deal_type: str
    borrower: str
    target: str
    industry: str | None = None
    sponsor: str | None = None
    close_date: str | None = None
    next_meeting_date: str | None = None
    ev_mm: int | None = None
    senior_mm: int | None = None
    our_commitment_mm: int | None = None
    equity_mm: int | None = None
    tenor_years: int | None = None
    sponsor_ebitda_mm: int | None = None
    summary: str | None = None
    user: str | None = None


@router.post("/deals")
def create_deal(body: DealCreate, db: Session = Depends(get_db)):
    deal = Deal(**body.model_dump(exclude={"user"}), owner=body.user,
                review_status="検討中")
    db.add(deal)
    db.flush()
    add_history(db, deal, body.user, "案件登録", "基本情報を登録")
    db.commit()
    return deal.to_dict()


class DraftBody(BaseModel):
    user: str | None = None


@router.post("/deals/draft")
def create_draft(body: DraftBody, db: Session = Depends(get_db)):
    """資料アップロード起点の登録フロー用の下書き案件。"""
    deal = Deal(name="（下書き）新規案件", deal_type="LBO", borrower="", target="",
                owner=body.user, review_status="検討中")
    db.add(deal)
    db.flush()
    add_history(db, deal, body.user, "案件登録（下書き）", "資料アップロードを開始")
    db.commit()
    return deal.to_dict()


class DealPatch(BaseModel):
    name: str | None = None
    deal_type: str | None = None
    borrower: str | None = None
    target: str | None = None
    industry: str | None = None
    sponsor: str | None = None
    close_date: str | None = None
    next_meeting_date: str | None = None
    ev_mm: int | None = None
    senior_mm: int | None = None
    our_commitment_mm: int | None = None
    equity_mm: int | None = None
    tenor_years: int | None = None
    sponsor_ebitda_mm: int | None = None
    summary: str | None = None
    owner: str | None = None
    user: str | None = None


@router.patch("/deals/{deal_id}")
def update_deal(deal_id: int, body: DealPatch, db: Session = Depends(get_db)):
    deal = _get_deal(db, deal_id)
    data = body.model_dump(exclude_unset=True, exclude={"user"})
    for k, v in data.items():
        setattr(deal, k, v)
    add_history(db, deal, body.user, "案件情報を更新",
                "登録内容を確定" if "name" in data else "")
    db.commit()
    return deal.to_dict()


@router.delete("/deals/{deal_id}")
def delete_deal(deal_id: int, db: Session = Depends(get_db)):
    deal = _get_deal(db, deal_id)
    db.delete(deal)
    db.commit()
    return dict(deleted=deal_id)


@router.post("/deals/{deal_id}/extract-info")
def extract_deal_info(deal_id: int, user: str | None = None,
                      db: Session = Depends(get_db)):
    """アップロード済み資料から案件基本情報をAIで読み取る（フォームへの自動入力用）。"""
    deal = _get_deal(db, deal_id)
    if not deal.documents:
        raise HTTPException(400, "資料がアップロードされていません")
    docs = [dict(filename=d.filename, slot=d.slot, stored_path=d.stored_path)
            for d in deal.documents]
    result = get_extractor().extract_deal_info(docs)
    add_history(db, deal, user, "案件情報の自動読み取り",
                f"{len(result.get('fields', {}))}フィールドを資料から抽出")
    db.commit()
    return result


def _get_deal(db: Session, deal_id: int) -> Deal:
    deal = db.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404, "案件が見つかりません")
    return deal


@router.get("/deals/{deal_id}/full")
def deal_full(deal_id: int, db: Session = Depends(get_db)):
    deal = _get_deal(db, deal_id)
    extractor = get_extractor()
    findings = []
    for m in deal.memos:
        findings.extend(f.to_dict() for f in m.findings)
    return dict(
        deal=deal.to_dict(),
        documents=[d.to_dict() for d in deal.documents],
        items=[i.to_dict() for i in deal.items],
        kpi_nodes=[n.to_dict() for n in deal.kpi_nodes],
        scenarios=[s.to_dict() for s in deal.scenarios],
        memos=[m.to_dict() for m in reversed(deal.memos)],
        history=[h.to_dict() for h in reversed(deal.history)],
        exports=[e.to_dict() for e in deal.exports],
        findings=findings,
        chat_suggestions=dict(kpi=extractor.chat_suggestions("kpi"),
                              scenario=extractor.chat_suggestions("scenario")),
    )


@router.get("/deals/{deal_id}/documents/{doc_id}/file")
def document_file(deal_id: int, doc_id: int, db: Session = Depends(get_db)):
    """アップロード済み資料の実ファイルを返す（根拠パネルの参照元リンク用）。

    PDFはブラウザ内で開く（inline・#page=N アンカー対応）。Excelはダウンロード。
    """
    deal = _get_deal(db, deal_id)
    doc = next((d for d in deal.documents if d.id == doc_id), None)
    if not doc:
        raise HTTPException(404, "資料が見つかりません")
    # シードデータ等では stored_path が無い（実ファイル未添付）ことがある
    if not doc.stored_path:
        raise HTTPException(404, "この資料は実ファイルが保存されていません（デモ用メタデータのみ）")
    path = Path(doc.stored_path)
    if not path.exists():
        raise HTTPException(404, "ファイルが移動または削除されています")
    is_pdf = path.suffix.lower() == ".pdf"
    return FileResponse(
        path,
        media_type="application/pdf" if is_pdf
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=doc.filename,
        content_disposition_type="inline" if is_pdf else "attachment",
    )


@router.post("/deals/{deal_id}/documents")
def upload_document(deal_id: int, slot: str = Form(...), user: str = Form(None),
                    file: UploadFile = File(...), db: Session = Depends(get_db)):
    deal = _get_deal(db, deal_id)
    dest_dir = UPLOAD_DIR / str(deal_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        info = get_extractor().identify_document(file.filename, dest)
    except UnknownSampleFileError as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, e.message)

    # 同一スロットは上書き
    for d in list(deal.documents):
        if d.slot == slot:
            db.delete(d)
    doc = Document(deal_id=deal.id, slot=slot, filename=file.filename,
                   stored_path=str(dest), status="uploaded",
                   identified_company=info.get("company"),
                   identified_label=info.get("label"),
                   identified_detail=info.get("detail"))
    db.add(doc)
    db.flush()
    add_history(db, deal, user, "資料アップロード", f"{file.filename}（{slot}）")
    db.commit()
    result = doc.to_dict()
    # 案件照合（社名の一致チェック）。対象会社が未設定（下書き）の場合は判定しない
    company = info.get("company") or ""
    if company and deal.target:
        result["company_match"] = company in deal.target or deal.target in company
    else:
        result["company_match"] = None
    return result


@router.post("/deals/{deal_id}/analyze")
def analyze(deal_id: int, user: str | None = None, db: Session = Depends(get_db)):
    """AI解析の実行：抽出項目・KPIツリー提案・AI推奨シナリオを一括生成する。"""
    deal = _get_deal(db, deal_id)
    if not deal.documents:
        raise HTTPException(400, "資料がアップロードされていません")
    extractor = get_extractor()
    deal_info = dict(name=deal.name, deal_type=deal.deal_type, borrower=deal.borrower,
                     target=deal.target, sponsor=deal.sponsor,
                     ev_mm=deal.ev_mm, senior_mm=deal.senior_mm)
    docs = [dict(filename=d.filename, slot=d.slot, stored_path=d.stored_path)
            for d in deal.documents]

    items = extractor.extract_items(deal_info, docs)
    tree = extractor.propose_kpi_tree(deal_info, docs)
    cards = extractor.propose_scenarios(deal_info, docs)

    # 再解析時は既存の提案をリセット（確定済み案件の再解析はデモでは想定しない）
    for coll in (deal.items, deal.kpi_nodes, deal.scenarios):
        for row in list(coll):
            db.delete(row)
    db.flush()

    for idx, it in enumerate(items):
        db.add(ExtractedItem(
            deal_id=deal.id, key=it["key"], section=it["section"], label=it["label"],
            unit=it.get("unit", "百万円"), case_name=it.get("case"),
            values_json=json.dumps(it.get("values"), ensure_ascii=False) if it.get("values") else None,
            text_value=it.get("text_value"), required=it.get("required", True),
            evidence_json=json.dumps(it.get("evidence"), ensure_ascii=False),
            mismatch_json=json.dumps(it.get("mismatch"), ensure_ascii=False) if it.get("mismatch") else None,
            status="proposed", order_index=idx))
    for idx, n in enumerate(tree["nodes"]):
        db.add(KpiNode(
            deal_id=deal.id, node_id=n["id"], parent_id=n.get("parent"),
            label=n["label"], origin=n.get("origin", "model"), star=n.get("star", False),
            formula=n.get("formula"), value_text=n.get("value_text"), badge=n.get("badge"),
            evidence_json=json.dumps(n.get("evidence"), ensure_ascii=False),
            order_index=idx))
    for idx, c in enumerate(cards):
        db.add(Scenario(
            deal_id=deal.id, key=c["key"], origin=c.get("origin", "ai"),
            type_label=c.get("type_label"), title=c["title"], cause=c.get("cause"),
            affected_kpis_json=json.dumps(c.get("affected_kpis", []), ensure_ascii=False),
            change_text=c.get("change"), change_basis=c.get("change_basis"),
            impact=c.get("impact"), safeguards=c.get("safeguards"),
            questions=c.get("questions"), adopted=False, order_index=idx))
    deal.kpi_status = "proposed"
    for d in deal.documents:
        d.status = "analyzed"
    add_history(db, deal, user, "AI解析完了",
                f"{len(items)}項目を抽出・KPIツリー{len(tree['nodes'])}ノード・"
                f"推奨シナリオ{len(cards)}件を提案")
    db.commit()
    return dict(items=len(items), kpi_nodes=len(tree["nodes"]), scenarios=len(cards))
