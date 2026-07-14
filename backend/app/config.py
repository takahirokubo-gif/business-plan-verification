"""アプリ設定。環境変数（backend/.env）で切替える。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR / ".env")

# mock | anthropic
EXTRACTOR_MODE = os.getenv("EXTRACTOR_MODE", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# mockモードの疑似ディレイ（秒）。解析実行時に「AIが動いている」見せ方をする
MOCK_DELAY_SECONDS = float(os.getenv("MOCK_DELAY_SECONDS", "2.8"))

DB_PATH = BASE_DIR / "app.db"
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
