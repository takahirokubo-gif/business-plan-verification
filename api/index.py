"""Vercel Serverless Function エントリポイント。

すべてのリクエスト（画面・API）をこの関数にルーティングし、
FastAPI アプリ（Basic認証ミドルウェア・SPA配信込み）で処理する。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402,F401  Vercel が ASGI アプリとして検出する
