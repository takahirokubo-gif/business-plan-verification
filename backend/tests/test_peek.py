"""根拠Excelのセル抜粋API（documents/{id}/peek）のテスト。

不正・極端な location でも500を返さないこと（画面が壊れないこと）を担保する。
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


def _excel_doc_id(client) -> int:
    docs = client.get("/api/deals/1/full").json()["documents"]
    return next(d["id"] for d in docs if d["filename"].endswith(".xlsx"))


def test_peek_returns_target_cell(client):
    doc_id = _excel_doc_id(client)
    r = client.get(f"/api/deals/1/documents/{doc_id}/peek", params={"location": "PL!G9"})
    assert r.status_code == 200
    body = r.json()
    assert body["sheet"] == "PL" and body["target"] == "G9"
    # 該当セルが1つだけ target=True で返る
    targets = [c for row in body["rows"] for c in row["cells"] if c["target"]]
    assert len(targets) == 1 and targets[0]["ref"] == "G9"
    # 行ラベル（科目名）が添えられている
    assert any(row["label"] for row in body["rows"])


@pytest.mark.parametrize("location", [
    "PLシート C9:E9（9行・FY24〜FY26列）",   # 日本語表記（fixture形式）
    "'PL'!G9",                              # 引用符付き
    "PL!G9:E9",                             # 範囲指定
    "PL_oldシート C9",                       # 短いシート名への誤マッチ回避
])
def test_peek_accepts_notation_variants(client, location):
    doc_id = _excel_doc_id(client)
    r = client.get(f"/api/deals/1/documents/{doc_id}/peek", params={"location": location})
    assert r.status_code == 200, r.text
    assert r.json()["target"]


@pytest.mark.parametrize("location", [
    "PL!ZZ1048576",                  # Excelの行上限
    "PL!G99999999999999999999",      # 桁あふれ
    "PL!A0",                         # 0行
    "PL!-1",
    "PL!",
    "!A1",
    "!!!",
    "",
    "p.16（5.3 採用とスタッフ定着）",   # PDFの箇所表記
    "../../etc/passwd!A1",           # パストラバーサル風
])
def test_peek_never_returns_server_error(client, location):
    doc_id = _excel_doc_id(client)
    r = client.get(f"/api/deals/1/documents/{doc_id}/peek", params={"location": location})
    assert r.status_code < 500, f"{location} -> {r.status_code} {r.text}"


def test_peek_rejects_pdf_and_missing_doc(client):
    docs = client.get("/api/deals/1/full").json()["documents"]
    pdf_id = next(d["id"] for d in docs if d["filename"].endswith(".pdf"))
    assert client.get(f"/api/deals/1/documents/{pdf_id}/peek",
                      params={"location": "PL!A1"}).status_code == 400
    assert client.get("/api/deals/1/documents/99999/peek",
                      params={"location": "PL!A1"}).status_code == 404
