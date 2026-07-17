"""EXTRACTOR_MODE（mock | anthropic）による実装の切り替え。

- 起動時のデフォルトは環境変数 EXTRACTOR_MODE（backend/.env）
- 実行中はUI（PUT /api/extract/mode）からいつでも切り替えられる
- 呼び出し側（ルーター等）は get_extractor() を使うだけで、
  どちらの実装かを意識しない

APIキーはサーバー側の .env（ANTHROPIC_API_KEY）からのみ読み込み、
フロントエンドには一切渡さない。
"""
from ..config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, EXTRACTOR_MODE
from .base import Extractor

VALID_MODES = ("mock", "anthropic")

_current_mode = EXTRACTOR_MODE if EXTRACTOR_MODE in VALID_MODES else "mock"
_current_model = ANTHROPIC_MODEL  # 起動時の既定値は backend/.env の ANTHROPIC_MODEL
_models_cache: list[dict] | None = None
_instances: dict[str, Extractor] = {}


def anthropic_available() -> bool:
    """AnthropicモードにするためのAPIキーが設定されているか。"""
    return bool(ANTHROPIC_API_KEY)


def get_model() -> str:
    return _current_model


def list_models() -> list[dict]:
    """選択可能なモデル一覧（{id, display_name}）。

    Anthropic APIから動的取得し、プロセス生存中はキャッシュする。
    キー未設定・API失敗時は現在のモデルのみのリストにフォールバックする。
    """
    global _models_cache
    if _models_cache is not None:
        return _models_cache
    if anthropic_available():
        try:
            import anthropic

            # 設定画面のリクエストパスで呼ばれるため、短いタイムアウト・リトライなしで
            # ブロックを防ぐ（失敗時は下のフォールバック一覧で画面は動く）
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY,
                                         timeout=5.0, max_retries=0)
            _models_cache = [
                dict(id=m.id, display_name=m.display_name or m.id)
                for m in client.models.list(limit=50)
            ]
            return _models_cache
        except Exception:
            pass  # フォールバックへ（一覧が取れなくても設定画面は動かす）
    return [dict(id=_current_model, display_name=_current_model)]


def set_model(model: str) -> str:
    """AIモードで使うモデルを実行時に切り替える。"""
    global _current_model
    model = (model or "").strip()
    if not model:
        raise ValueError("モデルIDが空です")
    known = {m["id"] for m in list_models()}
    # 一覧が取得できている場合はその中のIDのみ許可（タイポで抽出が全滅するのを防ぐ）
    if _models_cache is not None and model not in known:
        raise ValueError(f"利用できないモデルです: {model}")
    _current_model = model
    return _current_model


def get_mode() -> str:
    return _current_mode


def set_mode(mode: str) -> str:
    """抽出モードを実行時に切り替える。

    anthropic への切替はAPIキーが設定されている場合のみ許可する。
    """
    global _current_mode
    if mode not in VALID_MODES:
        raise ValueError(f"不明なモードです: {mode}")
    if mode == "anthropic" and not anthropic_available():
        raise ValueError(
            "ANTHROPIC_API_KEY が設定されていません。"
            "backend/.env に ANTHROPIC_API_KEY を設定してサーバーを再起動してください。"
        )
    _current_mode = mode
    return _current_mode


def get_extractor() -> Extractor:
    mode = _current_mode
    if mode not in _instances:
        if mode == "anthropic":
            from .anthropic_extractor import AnthropicExtractor

            _instances[mode] = AnthropicExtractor()
        else:
            from .mock import MockExtractor

            _instances[mode] = MockExtractor()
    return _instances[mode]
