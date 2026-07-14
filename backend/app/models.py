"""SQLAlchemyモデル。

状態遷移の原則（要件定義2章）:
- すべてのAI出力（抽出項目・KPI・シナリオ）は「AI提案 → 人がレビュー → 確定」の状態を持つ
- 確定データのみが下流ステージの入力になる
- 上流の確定値が変更されても下流は無効化せず、警告バッジ（stale）のみ付ける（警告型）
"""
import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# 案件検討ステータス（人が設定・審査相談メモの結論と連動）
REVIEW_STATUSES = ["検討中", "再検討中", "推進", "保留", "見送り"]
# 作業ステータス（ステージ進捗・自動遷移）
WORK_STATUSES = ["資料解析中", "数値確定中", "KPI確定中", "シナリオ検討中", "出力済"]

DOCUMENT_SLOTS = {
    "model_sponsor": "財務モデル（スポンサーケース）",
    "model_base": "財務モデル（ベースケース）",
    "dd_business": "DDレポート（事業）",
    "dd_financial": "DDレポート（財務）",
    "dd_legal": "DDレポート（法務）",
    "dd_tax": "DDレポート（税務・任意）",
}


def _j(v):
    return json.loads(v) if v else None


class User(Base):
    __tablename__ = "users"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)

    def to_dict(self):
        return dict(key=self.key, name=self.name, role=self.role,
                    display=f"{self.name}（{self.role}）")


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed_key: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String)
    deal_type: Mapped[str] = mapped_column(String)  # LBO/MBO/事業承継/リファイナンス
    borrower: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    sponsor: Mapped[str | None] = mapped_column(String, nullable=True)
    close_date: Mapped[str | None] = mapped_column(String, nullable=True)
    next_meeting_date: Mapped[str | None] = mapped_column(String, nullable=True)
    ev_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    senior_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    our_commitment_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equity_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tenor_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sponsor_ebitda_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String, ForeignKey("users.key"), nullable=True)

    review_status: Mapped[str] = mapped_column(String, default="検討中")
    work_status_override: Mapped[str | None] = mapped_column(String, nullable=True)

    # ステージ2（KPI構造）の状態
    kpi_status: Mapped[str] = mapped_column(String, default="none")  # none/proposed/confirmed
    kpi_confirmed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    kpi_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    kpi_stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    documents = relationship("Document", back_populates="deal", cascade="all, delete-orphan")
    items = relationship("ExtractedItem", back_populates="deal",
                         cascade="all, delete-orphan", order_by="ExtractedItem.order_index")
    kpi_nodes = relationship("KpiNode", back_populates="deal",
                             cascade="all, delete-orphan", order_by="KpiNode.order_index")
    scenarios = relationship("Scenario", back_populates="deal",
                             cascade="all, delete-orphan", order_by="Scenario.order_index")
    memos = relationship("Memo", back_populates="deal", cascade="all, delete-orphan",
                         order_by="Memo.meeting_date")
    history = relationship("HistoryEvent", back_populates="deal",
                           cascade="all, delete-orphan", order_by="HistoryEvent.at")
    exports = relationship("ExportRecord", back_populates="deal", cascade="all, delete-orphan")

    # ---- 導出値（四則演算のみ。再計算エンジンには該当しない）
    @property
    def initial_leverage(self):
        if self.senior_mm and self.sponsor_ebitda_mm:
            return round(self.senior_mm / self.sponsor_ebitda_mm, 1)
        return None

    @property
    def ltv_pct(self):
        if self.senior_mm and self.ev_mm:
            return round(self.senior_mm / self.ev_mm * 100)
        return None

    def required_items_confirmed(self):
        req = [i for i in self.items if i.required]
        return bool(req) and all(i.status == "confirmed" for i in req)

    def work_status(self):
        """作業ステータスの自動導出（背景案件のみoverride）。"""
        if self.work_status_override:
            return self.work_status_override
        if not self.items:
            return "資料解析中"
        if not self.required_items_confirmed():
            return "数値確定中"
        if self.kpi_status != "confirmed":
            return "KPI確定中"
        last_export = max((e.at for e in self.exports), default=None)
        if not last_export:
            return "シナリオ検討中"
        # 出力後に「再検討」の審査相談が入ったらシナリオ検討へ巻き戻す（再検討ループ）
        rework = [m for m in self.memos
                  if m.conclusion == "再検討" and m.created_at and m.created_at > last_export]
        return "シナリオ検討中" if rework else "出力済"

    def progress(self):
        req = [i for i in self.items if i.required]
        done = len([i for i in req if i.status == "confirmed"])
        return dict(required=len(req), confirmed=done,
                    held=len([i for i in self.items if i.status == "held"]),
                    total=len(self.items))

    def to_list_dict(self):
        return dict(
            id=self.id, name=self.name, deal_type=self.deal_type,
            borrower=self.borrower, target=self.target,
            our_commitment_mm=self.our_commitment_mm,
            review_status=self.review_status, work_status=self.work_status(),
            owner=self.owner,
            next_meeting_date=self.next_meeting_date,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
        )

    def to_dict(self):
        d = self.to_list_dict()
        d.update(
            industry=self.industry, sponsor=self.sponsor, close_date=self.close_date,
            ev_mm=self.ev_mm, senior_mm=self.senior_mm, equity_mm=self.equity_mm,
            tenor_years=self.tenor_years, sponsor_ebitda_mm=self.sponsor_ebitda_mm,
            summary=self.summary, initial_leverage=self.initial_leverage,
            ltv_pct=self.ltv_pct, kpi_status=self.kpi_status,
            kpi_confirmed_by=self.kpi_confirmed_by,
            kpi_confirmed_at=self.kpi_confirmed_at.isoformat() if self.kpi_confirmed_at else None,
            kpi_stale_reason=self.kpi_stale_reason,
            progress=self.progress(),
            created_at=self.created_at.isoformat() if self.created_at else None,
        )
        return d


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    slot: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="uploaded")  # uploaded/analyzed
    identified_company: Mapped[str | None] = mapped_column(String, nullable=True)
    identified_label: Mapped[str | None] = mapped_column(String, nullable=True)
    identified_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    deal = relationship("Deal", back_populates="documents")

    def to_dict(self):
        return dict(id=self.id, slot=self.slot, slot_label=DOCUMENT_SLOTS.get(self.slot, self.slot),
                    filename=self.filename, status=self.status,
                    identified_company=self.identified_company,
                    identified_label=self.identified_label,
                    identified_detail=self.identified_detail,
                    uploaded_at=self.uploaded_at.isoformat() if self.uploaded_at else None)


class ExtractedItem(Base):
    __tablename__ = "extracted_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    key: Mapped[str] = mapped_column(String)
    section: Mapped[str] = mapped_column(String)
    label: Mapped[str] = mapped_column(String)
    unit: Mapped[str] = mapped_column(String, default="百万円")
    case_name: Mapped[str | None] = mapped_column(String, nullable=True)  # base/sponsor
    values_json: Mapped[str | None] = mapped_column(Text, nullable=True)   # AI抽出値（年度→値）
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)    # 定性テキスト
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 根拠3点セット
    mismatch_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 不整合情報
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # レビュー状態
    status: Mapped[str] = mapped_column(String, default="proposed")  # proposed/confirmed/held
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    deal = relationship("Deal", back_populates="items")

    def effective_values(self):
        return _j(self.confirmed_values_json) if self.edited else _j(self.values_json)

    def effective_text(self):
        return self.confirmed_text if (self.edited and self.confirmed_text) else self.text_value

    def to_dict(self):
        return dict(
            id=self.id, key=self.key, section=self.section, label=self.label,
            unit=self.unit, case_name=self.case_name,
            values=_j(self.values_json), text_value=self.text_value,
            effective_values=self.effective_values(), effective_text=self.effective_text(),
            required=self.required, evidence=_j(self.evidence_json),
            mismatch=_j(self.mismatch_json), status=self.status, edited=self.edited,
            resolution_note=self.resolution_note,
            confirmed_by=self.confirmed_by,
            confirmed_at=self.confirmed_at.isoformat() if self.confirmed_at else None,
        )


class KpiNode(Base):
    __tablename__ = "kpi_nodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    node_id: Mapped[str] = mapped_column(String)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    label: Mapped[str] = mapped_column(String)
    origin: Mapped[str] = mapped_column(String, default="model")  # model/dd/manual
    star: Mapped[bool] = mapped_column(Boolean, default=False)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String, nullable=True)
    badge: Mapped[str | None] = mapped_column(String, nullable=True)  # 例: モデル外・定性
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_via_chat: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    deal = relationship("Deal", back_populates="kpi_nodes")

    def to_dict(self):
        return dict(id=self.id, node_id=self.node_id, parent_id=self.parent_id,
                    label=self.label, origin=self.origin, star=self.star,
                    formula=self.formula, value_text=self.value_text, badge=self.badge,
                    evidence=_j(self.evidence_json), added_via_chat=self.added_via_chat)


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    key: Mapped[str] = mapped_column(String)
    origin: Mapped[str] = mapped_column(String, default="ai")  # ai/human
    type_label: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_kpis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    safeguards: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    adopted: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    deal = relationship("Deal", back_populates="scenarios")

    def to_dict(self):
        return dict(id=self.id, key=self.key, origin=self.origin, type_label=self.type_label,
                    title=self.title, cause=self.cause,
                    affected_kpis=_j(self.affected_kpis_json) or [],
                    change_text=self.change_text, change_basis=self.change_basis,
                    impact=self.impact, safeguards=self.safeguards, questions=self.questions,
                    adopted=self.adopted, rejection_note=self.rejection_note,
                    stale_reason=self.stale_reason,
                    updated_at=self.updated_at.isoformat() if self.updated_at else None)


class Memo(Base):
    __tablename__ = "memos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    meeting_date: Mapped[str] = mapped_column(String)
    attendees_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str] = mapped_column(String)  # 続行/再検討/推進/保留/見送り
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    deal = relationship("Deal", back_populates="memos")
    findings = relationship("MemoFinding", back_populates="memo", cascade="all, delete-orphan")

    def to_dict(self):
        return dict(id=self.id, meeting_date=self.meeting_date,
                    attendees=_j(self.attendees_json) or [], conclusion=self.conclusion,
                    note=self.note, created_by=self.created_by,
                    created_at=self.created_at.isoformat() if self.created_at else None,
                    findings=[f.to_dict() for f in self.findings])


class MemoFinding(Base):
    __tablename__ = "memo_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memo_id: Mapped[int] = mapped_column(ForeignKey("memos.id"))
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    target_type: Mapped[str | None] = mapped_column(String, nullable=True)  # scenario/item/kpi
    target_key: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)

    memo = relationship("Memo", back_populates="findings")

    def to_dict(self):
        return dict(id=self.id, target_type=self.target_type,
                    target_key=self.target_key, text=self.text,
                    meeting_date=self.memo.meeting_date if self.memo else None)


class HistoryEvent(Base):
    __tablename__ = "history_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    user_key: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    deal = relationship("Deal", back_populates="history")

    def to_dict(self):
        return dict(id=self.id, at=self.at.isoformat() if self.at else None,
                    user=self.user_key, action=self.action, detail=self.detail)


class ExportRecord(Base):
    __tablename__ = "export_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    user_key: Mapped[str | None] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String)
    excluded_held: Mapped[int] = mapped_column(Integer, default=0)

    deal = relationship("Deal", back_populates="exports")

    def to_dict(self):
        return dict(id=self.id, at=self.at.isoformat() if self.at else None,
                    user=self.user_key, filename=self.filename,
                    excluded_held=self.excluded_held)
