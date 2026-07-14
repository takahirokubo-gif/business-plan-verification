"""アプリ設定。環境変数（backend/.env）で切替える。

Vercel等のサーバーレス環境では書き込み可能なのは /tmp のみ。
DBは初回リクエスト時に自動シードされる（デモ用途：常にクリーンな初期状態）。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")

# mock | anthropic
EXTRACTOR_MODE = os.getenv("EXTRACTOR_MODE", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# mockモードの疑似ディレイ（秒）。解析実行時に「AIが動いている」見せ方をする
MOCK_DELAY_SECONDS = float(os.getenv("MOCK_DELAY_SECONDS", "2.8"))

IS_SERVERLESS = bool(os.getenv("VERCEL"))

DB_PATH = Path("/tmp/app.db") if IS_SERVERLESS else BASE_DIR / "app.db"
UPLOAD_DIR = Path("/tmp/uploads") if IS_SERVERLESS else BASE_DIR / "uploads"
EXPORT_DIR = Path("/tmp/exports") if IS_SERVERLESS else BASE_DIR / "exports"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# 公開デモの簡易パスワード保護（Basic認証）。
# SHARE_PASSWORD を設定すると全アクセスにID/パスワードを要求する。空なら無効（ローカル開発）
SHARE_USER = os.getenv("SHARE_USER", "demo")
SHARE_PASSWORD = os.getenv("SHARE_PASSWORD", "")
