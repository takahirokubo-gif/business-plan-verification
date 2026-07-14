"""FastAPI エントリポイント。

初回起動時にDBが空ならシードデータを自動投入する（デモをすぐ動かせるように）。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .models import Deal
from .routers import deals, output, review

app = FastAPI(title="事業計画検証ソリューション Lv1", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals.router)
app.include_router(review.router)
app.include_router(output.router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Deal).count() == 0:
            from .seed import run_seed
            run_seed(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    from .config import EXTRACTOR_MODE
    return dict(status="ok", extractor_mode=EXTRACTOR_MODE)
