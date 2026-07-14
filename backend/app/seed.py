"""シードスクリプト：DB初期化＋デモデータ投入。

usage: python -m app.seed

投入内容（fixtures/seed_data.json 等から）:
- ユーザー3名（田中 稟議担当／佐藤 部長／高橋）
- オートスタッフ中部LBO：全ステージ完了済み・審査相談メモ2件（7/5続行・7/12再検討＋指摘3件）
  → 検討ステータス「再検討中」・作業ステータス「シナリオ検討中」（再検討ループ中）
- 背景案件3件（サンメディクス＝数値確定中／東海プロセス機器＝推進／北勢運輸＝見送り）
"""
import json
from datetime import datetime
from pathlib import Path

from .config import FIXTURES_DIR
from .database import Base, SessionLocal, engine
from .models import (Deal, Document, ExportRecord, ExtractedItem, HistoryEvent,
                     KpiNode, Memo, MemoFinding, Scenario, User)

DUMMY_INPUT = Path(__file__).resolve().parent.parent.parent / "dummy_input"


def _load(name):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _dt(s):
    return datetime.fromisoformat(s) if s else None


def run_seed(db):
    seed = _load("seed_data.json")
    extraction = _load("extraction_autostaff.json")
    kpi_tree = _load("kpi_tree_autostaff.json")
    scenarios = _load("scenarios_autostaff.json")
    identify = _load("identify.json")["files"]

    for u in seed["users"]:
        db.add(User(key=u["key"], name=u["name"], role=u["role"]))

    deals_by_key = {}
    for d in seed["deals"]:
        deal = Deal(
            seed_key=d["key"], name=d["name"], deal_type=d["deal_type"],
            borrower=d["borrower"], target=d["target"], industry=d.get("industry"),
            sponsor=d.get("sponsor"), close_date=d.get("close_date"),
            next_meeting_date=d.get("next_meeting_date"),
            ev_mm=d.get("ev_mm"), senior_mm=d.get("senior_mm"),
            our_commitment_mm=d.get("our_commitment_mm"), equity_mm=d.get("equity_mm"),
            tenor_years=d.get("tenor_years"), sponsor_ebitda_mm=d.get("sponsor_ebitda_mm"),
            summary=d.get("summary"), owner=d.get("owner"),
            review_status=d["review_status"],
            created_at=_dt(d.get("created_at")), updated_at=_dt(d.get("updated_at")),
        )
        # 背景案件（詳細データ未投入）は作業ステータスを固定表示
        if d["key"] in ("tokai_process", "hokusei"):
            deal.work_status_override = d["work_status"]
        db.add(deal)
        db.flush()
        deals_by_key[d["key"]] = deal

    # ---------------- オートスタッフ中部（主役・全ステージ完了）
    auto = deals_by_key["autostaff"]

    for slot, filename in (
        ("model_sponsor", "AutostaffChubu_Model_Sponsor.xlsx"),
        ("model_base", "AutostaffChubu_Model_Base.xlsx"),
        ("dd_business", "DD_Business_オートスタッフ中部.pdf"),
        ("dd_financial", "DD_Financial_オートスタッフ中部.pdf"),
        ("dd_legal", "DD_Legal_オートスタッフ中部.pdf"),
        ("dd_tax", "DD_Tax_オートスタッフ中部.pdf"),
    ):
        info = identify.get(filename, {})
        stored = DUMMY_INPUT / filename
        db.add(Document(
            deal_id=auto.id, slot=slot, filename=filename,
            stored_path=str(stored) if stored.exists() else None,
            status="analyzed", identified_company=info.get("company"),
            identified_label=info.get("label"), identified_detail=info.get("detail"),
            uploaded_at=_dt("2026-07-02T10:07:00")))

    held_keys = {"act_ni", "act_fcf"}
    confirm_at = _dt("2026-07-03T15:40:00")
    for idx, it in enumerate(extraction["items"]):
        item = ExtractedItem(
            deal_id=auto.id, key=it["key"], section=it["section"], label=it["label"],
            unit=it.get("unit", "百万円"), case_name=it.get("case"),
            values_json=json.dumps(it.get("values"), ensure_ascii=False) if it.get("values") else None,
            text_value=it.get("text_value"), required=it.get("required", True),
            evidence_json=json.dumps(it.get("evidence"), ensure_ascii=False),
            mismatch_json=json.dumps(it.get("mismatch"), ensure_ascii=False) if it.get("mismatch") else None,
            order_index=idx)
        if it["key"] in held_keys:
            item.status = "held"
        else:
            item.status = "confirmed"
            item.confirmed_by = "tanaka"
            item.confirmed_at = confirm_at
            if it["key"] == "goodwill":
                item.resolution_note = ("モデル値5,500百万円を採用（モデル内の整合を優先）。"
                                        "財務DDとの差異220百万円はスポンサーに確認中（7/12指摘）")
        db.add(item)

    for idx, n in enumerate(kpi_tree["nodes"]):
        db.add(KpiNode(
            deal_id=auto.id, node_id=n["id"], parent_id=n.get("parent"), label=n["label"],
            origin=n.get("origin", "model"), star=n.get("star", False),
            formula=n.get("formula"), value_text=n.get("value_text"), badge=n.get("badge"),
            evidence_json=json.dumps(n.get("evidence"), ensure_ascii=False), order_index=idx))
    cn = kpi_tree["concentration_node"]
    db.add(KpiNode(
        deal_id=auto.id, node_id=cn["id"], parent_id=cn.get("parent"), label=cn["label"],
        origin=cn.get("origin", "dd"), star=cn.get("star", False), formula=cn.get("formula"),
        value_text=cn.get("value_text"), badge=cn.get("badge"),
        evidence_json=json.dumps(cn.get("evidence"), ensure_ascii=False),
        added_via_chat=True, order_index=len(kpi_tree["nodes"])))
    auto.kpi_status = "confirmed"
    auto.kpi_confirmed_by = "tanaka"
    auto.kpi_confirmed_at = _dt("2026-07-04T11:00:00")

    for idx, c in enumerate(scenarios["cards"] + [scenarios["human_card"]]):
        db.add(Scenario(
            deal_id=auto.id, key=c["key"], origin=c.get("origin", "ai"),
            type_label=c.get("type_label"), title=c["title"], cause=c.get("cause"),
            affected_kpis_json=json.dumps(c.get("affected_kpis", []), ensure_ascii=False),
            change_text=c.get("change") or c.get("change_text"),
            change_basis=c.get("change_basis"), impact=c.get("impact"),
            safeguards=c.get("safeguards"), questions=c.get("questions"),
            adopted=c.get("adopted", False), rejection_note=c.get("rejection_note"),
            order_index=idx, updated_at=_dt("2026-07-04T14:30:00")))

    db.add(ExportRecord(deal_id=auto.id, at=_dt("2026-07-05T09:15:00"),
                        user_key="tanaka",
                        filename="審査サマリー_株式会社オートスタッフ中部_20260705.xlsx",
                        excluded_held=2))

    # ---------------- サンメディクス（数値確定中の背景案件）
    sun = deals_by_key["sunmedix"]
    db.add(Document(deal_id=sun.id, slot="model_base", filename="SunMedix_Model_Base.xlsx",
                    status="analyzed", identified_company="株式会社サンメディクス",
                    identified_label="財務モデル（ベースケース）",
                    uploaded_at=_dt("2026-07-08T09:35:00")))
    db.add(Document(deal_id=sun.id, slot="dd_business", filename="DD_Business_サンメディクス.pdf",
                    status="analyzed", identified_company="株式会社サンメディクス",
                    identified_label="事業DDレポート",
                    uploaded_at=_dt("2026-07-08T09:35:00")))
    for idx, it in enumerate(seed["sunmedix_items"]):
        db.add(ExtractedItem(
            deal_id=sun.id, key=it["key"], section=it["section"], label=it["label"],
            unit=it.get("unit", "百万円"), case_name=it.get("case"),
            values_json=json.dumps(it.get("values"), ensure_ascii=False) if it.get("values") else None,
            text_value=it.get("text_value"), required=it.get("required", True),
            evidence_json=json.dumps(it.get("evidence"), ensure_ascii=False),
            status="proposed", order_index=idx))
    sun.kpi_status = "proposed"

    # ---------------- メモ・指摘・履歴
    for m in seed["memos"]:
        deal = deals_by_key[m["deal_key"]]
        memo = Memo(deal_id=deal.id, meeting_date=m["meeting_date"],
                    attendees_json=json.dumps(m.get("attendees", []), ensure_ascii=False),
                    conclusion=m["conclusion"], note=m.get("note"),
                    created_by=m.get("created_by"), created_at=_dt(m.get("created_at")))
        db.add(memo)
        db.flush()
        for f in m.get("findings", []):
            db.add(MemoFinding(memo_id=memo.id, deal_id=deal.id,
                               target_type=f.get("target_type"),
                               target_key=f.get("target_key"), text=f["text"]))

    for h in seed["history"]:
        deal = deals_by_key[h["deal_key"]]
        db.add(HistoryEvent(deal_id=deal.id, at=_dt(h["at"]), user_key=h.get("user"),
                            action=h["action"], detail=h.get("detail")))

    # updated_at はシード値を優先（add_historyで上書きされないようここで再設定）
    for d in seed["deals"]:
        deals_by_key[d["key"]].updated_at = _dt(d.get("updated_at"))

    db.commit()
    print(f"seeded: {len(seed['deals'])} deals / {len(extraction['items'])} items "
          f"/ {len(kpi_tree['nodes']) + 1} kpi nodes / "
          f"{len(scenarios['cards']) + 1} scenarios / {len(seed['memos'])} memos")


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
