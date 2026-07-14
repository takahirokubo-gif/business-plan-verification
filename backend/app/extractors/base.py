"""Extractor インターフェース。

AI（またはそのモック）に許される役割は「抽出・マッピング・解釈・仮説生成」のみ。
数値の再計算・判定は行わない（Lv1は再計算エンジンを持たない）。
実装は環境変数 EXTRACTOR_MODE（mock | anthropic）で切り替え、
呼び出し側は切替えを一切意識しない。

メソッドが返すデータ形状は backend/app/fixtures/*.json と同一。
"""
from abc import ABC, abstractmethod
from pathlib import Path


class UnknownSampleFileError(Exception):
    """モックモードで対応フィクスチャが無いファイルがアップロードされた場合。"""

    message = "デモモードではサンプルファイルのみ解析できます"


class Extractor(ABC):
    @abstractmethod
    def identify_document(self, filename: str, path: Path | None) -> dict:
        """ファイルから社名・資料種別を読み取る（案件照合用）。
        returns: {company, doc_type, label, detail}
        """

    @abstractmethod
    def extract_items(self, deal: dict, documents: list[dict]) -> list[dict]:
        """財務モデル・DDレポート群から、定性情報・実績・予測数値を抽出する。
        すべての項目に根拠3点セット（参照ファイル・箇所・論理）を付ける。
        """

    @abstractmethod
    def propose_kpi_tree(self, deal: dict, documents: list[dict]) -> dict:
        """財務モデルの数式構造の解析（再計算なし）とDD定性情報の照合により
        KPIツリーを提案する。returns: {nodes: [...]}
        """

    @abstractmethod
    def propose_scenarios(self, deal: dict, documents: list[dict]) -> list[dict]:
        """3類型（トップライン／コスト／イベント）のAI推奨シナリオを標準5部構成で生成する。
        インパクトは定性推定（モデル再計算なし）であり、その旨を明示する。
        """

    @abstractmethod
    def chat(self, context: str, message: str, state: dict) -> dict:
        """チャット修正。変更は差分（diff）として返し、直接反映はしない。
        returns: {reply, diff|None}
        """

    @abstractmethod
    def chat_suggestions(self, context: str) -> list[str]:
        """チャット入力欄のプレースホルダー候補。"""
