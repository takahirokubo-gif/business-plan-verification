"""FastAPI エントリポイント。

- 初回起動時にDBが空ならシードデータを自動投入する（デモをすぐ動かせるように）
- SHARE_PASSWORD 設定時は全アクセスにBasic認証を要求（公開デモ用。localhostは免除）
- frontend/dist があれば同一オリジンでSPAを配信する（Vercelは全リクエストを
  この1関数にルーティングする構成）
"""
import base64
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .config import IS_SERVERLESS, SHARE_PASSWORD, SHARE_USER
from .database import Base, SessionLocal, engine
from .extractors.factory import (
    anthropic_available,
    get_mode,
    get_model,
    list_models,
    set_mode,
    set_model,
)
from .models import Deal
from .routers import deals, output, review

app = FastAPI(title="事業計画検証ソリューション Lv1", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 簡易パスワード保護（公開デモ用・SHARE_PASSWORD設定時のみ有効） ---
@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    if not SHARE_PASSWORD:
        return await call_next(request)
    # ローカル開発（localhost直アクセス・Vite devプロキシ）は認証免除
    host = request.headers.get("host", "").split(":")[0]
    if host in ("localhost", "127.0.0.1"):
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
        except Exception:
            decoded = ""
        user, _, password = decoded.partition(":")
        if secrets.compare_digest(user, SHARE_USER) and secrets.compare_digest(
            password, SHARE_PASSWORD
        ):
            return await call_next(request)
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="business-plan-verification-demo"'},
        content="認証が必要です",
    )


def _seed_if_empty():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Deal).count() == 0:
            from .seed import run_seed
            run_seed(db)
    finally:
        db.close()


# サーバーレス環境ではコールドスタートごとに /tmp が空になるため、
# インポート時（初回リクエスト前）にシードする
if IS_SERVERLESS:
    _seed_if_empty()


@app.on_event("startup")
def startup():
    _seed_if_empty()


app.include_router(deals.router)
app.include_router(review.router)
app.include_router(output.router)


@app.get("/api/health")
def health():
    return dict(status="ok", extractor_mode=get_mode())


# --- 抽出エンジンの実行時切替（設定モーダルから使用） ---
def _engine_state() -> dict:
    return dict(
        mode=get_mode(),
        anthropic_available=anthropic_available(),
        model=get_model(),
        models=list_models(),
    )


@app.get("/api/extract/mode")
def extractor_mode():
    return _engine_state()


class ModeRequest(BaseModel):
    mode: str | None = None
    model: str | None = None


@app.put("/api/extract/mode")
def update_extractor_mode(body: ModeRequest):
    # 片方の検証エラーでもう片方だけ切り替わった中途半端な状態にしない
    old_mode, old_model = get_mode(), get_model()
    try:
        if body.mode is not None:
            set_mode(body.mode)
        if body.model is not None:
            set_model(body.model)
    except ValueError as e:
        try:
            set_mode(old_mode)
            set_model(old_model)
        except ValueError:
            pass  # 元の値の復元に失敗しても、エラー応答自体は返す
        raise HTTPException(400, str(e))
    return _engine_state()


# フロントエンドのビルド成果物（frontend/dist）があれば同一ポートで配信する。
# 開発時は従来どおり Vite (5173) + プロキシでも動く。
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file() and candidate.resolve().is_relative_to(_FRONTEND_DIST):
            return FileResponse(candidate)
        # React Router のディープリンク（/deals/1 等）は index.html にフォールバック
        return FileResponse(_FRONTEND_DIST / "index.html")
