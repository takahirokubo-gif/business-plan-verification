"""バックエンドのスモークテスト（mockモード・シードデータ前提）。

実行: cd backend && .venv/bin/python -m pytest
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["EXTRACTOR_MODE"] = "mock"
os.environ["MOCK_DELAY_SECONDS"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import run_seed  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    run_seed(db)
    db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auto_id(client):
    deals = client.get("/api/deals").json()["deals"]
    return next(d["id"] for d in deals if "オートスタッフ" in d["name"])


def test_deal_list_statuses(client):
    deals = client.get("/api/deals").json()["deals"]

    def find(prefix):
        d = next(d for d in deals if d["name"].startswith(prefix))
        return d["review_status"], d["work_status"]

    assert find("オートスタッフ") == ("再検討中", "シナリオ検討中")
    assert find("サンメディクス") == ("検討中", "数値確定中")
    assert find("東海プロセス") == ("推進", "出力済")
    assert find("北勢運輸") == ("見送り", "出力済")


def test_auto_derived_values(client, auto_id):
    deal = client.get(f"/api/deals/{auto_id}/full").json()["deal"]
    assert deal["initial_leverage"] == 4.1
    assert deal["ltv_pct"] == 54


def test_goodwill_mismatch(client, auto_id):
    items = client.get(f"/api/deals/{auto_id}/full").json()["items"]
    gw = next(i for i in items if i["key"] == "goodwill")
    assert gw["values"]["FY27"] == 5500
    assert gw["mismatch"]["other_value"] == 5280


def test_export_requires_confirmation_and_excludes_held(client, auto_id):
    preview = client.get(f"/api/deals/{auto_id}/export/preview").json()
    assert preview["can_export"] is True
    assert len(preview["held_items"]) == 2
    r = client.post(f"/api/deals/{auto_id}/export", json={"user": "tanaka"})
    assert r.status_code == 200
    assert len(r.content) > 5000


def test_chat_script_and_fallback(client, auto_id):
    r = client.post(f"/api/deals/{auto_id}/chat", json=dict(
        context="kpi", message="重要KPIの★を稼働率から採用単価CPAに変更して", user="tanaka"))
    assert r.json()["diff"]["type"] == "star_change"
    r = client.post(f"/api/deals/{auto_id}/chat", json=dict(
        context="kpi", message="全く関係ない指示", user="tanaka"))
    body = r.json()
    assert body["diff"] is None and "デモモード" in body["reply"]


def test_upstream_change_warns_downstream(client, auto_id):
    """確定値の修正 → KPI・シナリオに警告型のstaleが付く（無効化はしない）。"""
    full = client.get(f"/api/deals/{auto_id}/full").json()
    item = next(i for i in full["items"] if i["key"] == "act_ebitda")
    vals = dict(item["effective_values"])
    vals["FY26"] = 1580
    r = client.post(f"/api/deals/{auto_id}/items/{item['id']}/action", json=dict(
        action="confirm", user="tanaka", values=vals))
    assert "1,620 → 1,580" in r.json()["deal"]["kpi_stale_reason"]
    full = client.get(f"/api/deals/{auto_id}/full").json()
    assert all(s["stale_reason"] for s in full["scenarios"])
    # シナリオは無効化されず採用状態が維持される（警告型）
    assert any(s["adopted"] for s in full["scenarios"])
    # 警告の解除
    r = client.post(f"/api/deals/{auto_id}/kpi/clear-stale", json={"user": "tanaka"})
    assert r.json()["deal"]["kpi_stale_reason"] is None


def test_unknown_file_rejected_in_mock(client, auto_id):
    r = client.post(f"/api/deals/{auto_id}/documents",
                    data={"slot": "model_base", "user": "tanaka"},
                    files={"file": ("unknown.xlsx", b"dummy", "application/octet-stream")})
    assert r.status_code == 400
    assert "サンプルファイルのみ" in r.json()["detail"]


def test_memo_updates_review_status(client):
    """審査相談メモの結論に連動して検討ステータスが更新される。"""
    deals = client.get("/api/deals").json()["deals"]
    sun_id = next(d["id"] for d in deals if "サンメディ" in d["name"])
    r = client.post(f"/api/deals/{sun_id}/memos", json=dict(
        meeting_date="2026-07-14", attendees=["田中", "佐藤"], conclusion="保留",
        note="資料不足のため保留", findings=[], update_review_status=True, user="tanaka"))
    assert r.json()["deal"]["review_status"] == "保留"
