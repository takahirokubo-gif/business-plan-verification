"""MockExtractor：fixtures/ のJSONを返す。APIキー不要で全フローが動く。

- 解析実行時に疑似ディレイ（MOCK_DELAY_SECONDS）を入れ、実際にAIが
  動いているように見せる
- fixtureに対応が無いファイルは UnknownSampleFileError
  （「デモモードではサンプルファイルのみ解析できます」）
"""
import json
import time
from pathlib import Path

from ..config import FIXTURES_DIR, MOCK_DELAY_SECONDS
from .base import Extractor, UnknownSampleFileError


def _load(name: str):
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class MockExtractor(Extractor):
    def __init__(self):
        self._identify = _load("identify.json")["files"]
        self._extraction = _load("extraction_autostaff.json")
        self._kpi_tree = _load("kpi_tree_autostaff.json")
        self._scenarios = _load("scenarios_autostaff.json")
        self._chat = _load("chat_scripts.json")

    # ---- 案件照合
    def identify_document(self, filename: str, path: Path | None) -> dict:
        info = self._identify.get(filename)
        if not info:
            raise UnknownSampleFileError()
        return info

    # ---- 抽出（数値確定タブの入力）
    def extract_items(self, deal: dict, documents: list[dict]) -> list[dict]:
        time.sleep(MOCK_DELAY_SECONDS)
        return self._extraction["items"]

    # ---- KPIツリー提案
    def propose_kpi_tree(self, deal: dict, documents: list[dict]) -> dict:
        return dict(nodes=self._kpi_tree["nodes"])

    # ---- シナリオ提案
    def propose_scenarios(self, deal: dict, documents: list[dict]) -> list[dict]:
        return self._scenarios["cards"]

    # ---- チャット（台本方式）
    def chat(self, context: str, message: str, state: dict) -> dict:
        conf = self._chat.get(context) or {}
        time.sleep(min(MOCK_DELAY_SECONDS, 1.5))
        for script in conf.get("scripts", []):
            if any(t in message for t in script["triggers"]):
                diff = script.get("diff")
                # 適用済みの差分には「適用済み」の応答を返す（例：追加済みノード）
                if diff and diff.get("type") == "add_node":
                    existing = state.get("node_ids") or []
                    if diff["node"]["id"] in existing:
                        return dict(reply="「大口派遣先への売上依存度」は既にKPIツリーに"
                                          "追加されています。", diff=None)
                if diff and diff.get("type") == "add_card":
                    existing = state.get("card_keys") or []
                    if diff["card"]["key"] in existing:
                        return dict(reply="このシナリオは既に追加されています。", diff=None)
                return dict(reply=script["reply"], diff=diff)
        return dict(reply=conf.get("fallback", "対応できませんでした。"), diff=None)

    def chat_suggestions(self, context: str) -> list[str]:
        conf = self._chat.get(context) or {}
        return conf.get("suggestions", [])
