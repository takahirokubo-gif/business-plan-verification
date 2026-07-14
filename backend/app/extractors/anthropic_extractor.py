"""AnthropicExtractor：Anthropic API による実抽出の実装。

コベナンツ・モニタリングと同方針：プロンプト・JSONスキーマ・レスポンス整形まで
実装するが、動作確認はmockモードで行う（Lv1の検証対象は業務フローのリアリティ）。

設計原則:
- LLMには「どこに何があるか」の構造化情報と定性推定のみをさせる。
  数値の再計算・閾値判定はさせない
- すべての出力に根拠（参照ファイル・箇所・論理）を必須とするスキーマを強制する
- 構造化出力は tool_use（input_schema強制）で受け取る
"""
import json
from pathlib import Path

from ..config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from .base import Extractor

EVIDENCE_SCHEMA = {
    "type": "object",
    "description": "根拠3点セット。すべての抽出値に必須。",
    "properties": {
        "file": {"type": "string", "description": "参照ファイル名"},
        "location": {"type": "string",
                     "description": "箇所（Excelはシート・セル番地、PDFはページ番号）"},
        "quote": {"type": "string", "description": "該当箇所の原文抜粋"},
        "logic": {"type": "string",
                  "description": "抽出の論理（なぜこの箇所をこの項目にマッピングしたか）"},
    },
    "required": ["file", "location", "quote", "logic"],
}

ITEMS_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "section": {"type": "string"},
                    "label": {"type": "string"},
                    "unit": {"type": "string"},
                    "case": {"type": ["string", "null"], "enum": ["base", "sponsor", None]},
                    "values": {"type": ["object", "null"],
                               "description": "年度→数値（表示単位に換算済み）。定性項目はnull"},
                    "text_value": {"type": ["string", "null"]},
                    "required": {"type": "boolean"},
                    "evidence": EVIDENCE_SCHEMA,
                    "mismatch": {"type": ["object", "null"],
                                 "description": "資料間で値が食い違う場合の相手側情報"},
                },
                "required": ["key", "section", "label", "unit", "values",
                             "text_value", "required", "evidence"],
            },
        }
    },
    "required": ["items"],
}

KPI_TREE_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "parent": {"type": ["string", "null"]},
                    "label": {"type": "string"},
                    "origin": {"type": "string", "enum": ["model", "dd", "manual"]},
                    "star": {"type": "boolean"},
                    "formula": {"type": ["string", "null"],
                                "description": "数式の構造（人が読める形）。再計算はしない"},
                    "value_text": {"type": ["string", "null"]},
                    "badge": {"type": ["string", "null"]},
                    "evidence": EVIDENCE_SCHEMA,
                },
                "required": ["id", "parent", "label", "origin", "star", "evidence"],
            },
        }
    },
    "required": ["nodes"],
}

SCENARIOS_SCHEMA = {
    "type": "object",
    "properties": {
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "origin": {"type": "string", "enum": ["ai", "human"]},
                    "type_label": {"type": "string",
                                   "enum": ["トップライン", "コスト", "イベント", "自分の仮説"]},
                    "title": {"type": "string"},
                    "cause": {"type": "string", "description": "シナリオ名・発生要因"},
                    "affected_kpis": {"type": "array", "items": {"type": "string"},
                                      "description": "確定KPIツリーのノードID"},
                    "change_text": {"type": "string", "description": "KPIの変化幅"},
                    "change_basis": {"type": "string", "description": "変化幅の根拠"},
                    "impact": {"type": "string",
                               "description": "返済能力への影響。DSCR・レバレッジ・現預金等への"
                                              "影響を具体的数値を含む定性推定で記述する。"
                                              "判定ラベル（問題なし等）は出さない"},
                    "safeguards": {"type": "string", "description": "保全策・構造"},
                    "questions": {"type": "string", "description": "スポンサー等への確認事項"},
                },
                "required": ["key", "origin", "type_label", "title", "cause",
                             "affected_kpis", "change_text", "change_basis",
                             "impact", "safeguards", "questions"],
            },
        }
    },
    "required": ["cards"],
}

IDENTIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string", "description": "対象会社名"},
        "doc_type": {"type": "string",
                     "enum": ["model_sponsor", "model_base", "dd_business",
                              "dd_financial", "dd_legal", "dd_tax", "unknown"]},
        "label": {"type": "string"},
        "detail": {"type": "string", "description": "判定根拠"},
    },
    "required": ["company", "doc_type", "label", "detail"],
}

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "diff": {"type": ["object", "null"],
                 "description": "適用可能な変更差分。add_node / star_change / "
                                "add_card / update_card のいずれか。変更が無ければnull"},
    },
    "required": ["reply", "diff"],
}

SYSTEM_PROMPT = """あなたは銀行の融資審査部門を支援する抽出・解釈エンジンです。
LBO等のストラクチャードファイナンス案件の資料（財務モデルExcel・DDレポートPDF）から、
審査相談の叩き台となる情報を抽出します。

絶対に守るルール:
1. 数値の再計算をしない。資料に書かれている値をそのまま拾う（単位換算のみ可。換算根拠を明記）
2. すべての出力に根拠3点セット（参照ファイル・箇所・抽出の論理）を付ける
3. 資料間で値が食い違う場合は、どちらかに寄せず mismatch として両方を報告する
4. シナリオのインパクトは定性推定であり、モデルの再計算値ではないことを前提に記述する。
   「問題なし／問題あり」等の判定ラベルは出さない（推定値と含意の記述まで）
5. 推測で値を作らない。資料に無い項目は values を null にして理由を logic に書く"""


def _excel_digest(path: Path) -> str:
    """Excelのシート構造・ラベル・数式をLLM入力用のテキストに要約する（値の再計算はしない）。"""
    from openpyxl import load_workbook
    wb = load_workbook(path)
    out = []
    for ws in wb.worksheets:
        out.append(f"=== シート: {ws.title} ===")
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 60),
                                max_col=min(ws.max_column, 12)):
            cells = []
            for c in row:
                if c.value is None:
                    continue
                cells.append(f"{c.coordinate}: {c.value!r}")
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)


def _pdf_digest(path: Path, max_pages: int = 40) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    out = []
    for i, page in enumerate(reader.pages[:max_pages]):
        out.append(f"=== p.{i + 1} ===")
        out.append(page.extract_text() or "")
    return "\n".join(out)


class AnthropicExtractor(Extractor):
    def __init__(self):
        import anthropic
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("EXTRACTOR_MODE=anthropic には ANTHROPIC_API_KEY が必要です")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _call(self, prompt: str, schema: dict, tool_name: str) -> dict:
        resp = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            tools=[dict(name=tool_name, description="構造化された抽出結果を返す",
                        input_schema=schema)],
            tool_choice=dict(type="tool", name=tool_name),
            messages=[dict(role="user", content=prompt)],
        )
        for block in resp.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("構造化出力が得られませんでした")

    def identify_document(self, filename: str, path: Path | None) -> dict:
        digest = ""
        if path and path.suffix == ".pdf":
            digest = _pdf_digest(path, max_pages=3)
        elif path:
            digest = _excel_digest(path)[:8000]
        prompt = (f"次のファイルの社名と資料種別を判定してください。\n"
                  f"ファイル名: {filename}\n先頭部分の内容:\n{digest[:8000]}")
        return self._call(prompt, IDENTIFY_SCHEMA, "identify_document")

    def extract_items(self, deal: dict, documents: list[dict]) -> list[dict]:
        parts = [f"案件情報: {json.dumps(deal, ensure_ascii=False)}", ""]
        for doc in documents:
            p = Path(doc["stored_path"])
            parts.append(f"--- ファイル: {doc['filename']}（{doc['slot']}）---")
            parts.append(_excel_digest(p) if p.suffix == ".xlsx" else _pdf_digest(p))
        parts.append(
            "\n上記資料から以下を抽出してください：\n"
            "1. 定性情報：事業要約・主要リスク（DDレポート群から。ページ番号を根拠に）\n"
            "2. 過去実績：直近3期のPL（売上高・営業利益・EBITDA・当期純利益）、"
            "BS（現預金・純資産・有利子負債）、CF（FCF）\n"
            "3. 予測数値：モデル内の各ケース（Sponsor/Base）のFY計画値（売上・営業利益・EBITDA・FCF）。"
            "ケースの判定根拠（シート・セル）を明記\n"
            "4. ストラクチャー：のれん・EV・シニアローン。資料間で値が食い違う場合はmismatchに両方を記載\n"
            "表記揺れ（Net Sales / Adj. EBITDA等）は名寄せし、マッピングの論理をlogicに書くこと。"
            "旧版シート（PL_old等）・作業用シートは抽出対象外。"
            "金額はシートの単位注記に基づき百万円に換算し、換算した旨をlogicに含めること。")
        result = self._call("\n".join(parts), ITEMS_SCHEMA, "extract_items")
        return result["items"]

    def propose_kpi_tree(self, deal: dict, documents: list[dict]) -> dict:
        parts = []
        for doc in documents:
            p = Path(doc["stored_path"])
            if p.suffix == ".xlsx" and doc["slot"] == "model_base":
                parts.append(f"--- 財務モデル: {doc['filename']} ---")
                parts.append(_excel_digest(p))
            if doc["slot"] == "dd_business":
                parts.append(f"--- 事業DD: {doc['filename']} ---")
                parts.append(_pdf_digest(p))
        parts.append(
            "\n財務モデルの計画年の数式を構文解析し（再計算はしない）、変数の連動関係を"
            "ツリー構造（nodes）にしてください。売上高・売上原価・販管費を頂点とし、"
            "KPIドライバーシートの変数まで分解します。"
            "事業DDの定性情報と照合し、リスクドライバーとして重要なKPIに star=true を付けてください。"
            "各ノードの evidence には参照シート・行と、数式のどの部分から親子関係を"
            "判定したかを書いてください。")
        return self._call("\n".join(parts), KPI_TREE_SCHEMA, "propose_kpi_tree")

    def propose_scenarios(self, deal: dict, documents: list[dict]) -> list[dict]:
        parts = [f"案件情報: {json.dumps(deal, ensure_ascii=False)}"]
        for doc in documents:
            p = Path(doc["stored_path"])
            parts.append(f"--- {doc['filename']} ---")
            parts.append(_pdf_digest(p) if p.suffix == ".pdf" else _excel_digest(p)[:12000])
        parts.append(
            "\n3類型（トップライン悪化／コスト上昇／イベント）のストレスシナリオを"
            "標準5部構成で生成してください（key: A/B/C、origin: ai）。"
            "インパクトはDSCR・レバレッジ・現預金への影響を具体的数値を含めて定性推定しますが、"
            "モデルの再計算はせず、判定ラベルは出さないこと。"
            "変化幅には外部データや資料内の根拠を紐付けること。")
        result = self._call("\n".join(parts), SCENARIOS_SCHEMA, "propose_scenarios")
        return result["cards"]

    def chat(self, context: str, message: str, state: dict) -> dict:
        prompt = (
            f"コンテキスト: {context}（kpi=KPIツリーの修正 / scenario=シナリオカードの修正）\n"
            f"現在の状態: {json.dumps(state, ensure_ascii=False)}\n"
            f"ユーザーの指示: {message}\n\n"
            "指示に対応する変更差分（diff）を返してください。diffの形式:\n"
            "- ノード追加: {type:'add_node', node:{id,parent,label,origin,star,badge,evidence,...}}\n"
            "- ★変更: {type:'star_change', remove:[nodeId], add:[nodeId]}\n"
            "- カード追加: {type:'add_card', card:{key,origin,title,...標準5部構成}}\n"
            "- カード修正: {type:'update_card', card_key:'A', fields:{変更するフィールドのみ}}\n"
            "変更を直接適用してはいけません。人が差分プレビューを確認して適用します。"
            "対応できない指示の場合は diff=null で、replyに理由を書いてください。")
        return self._call(prompt, CHAT_SCHEMA, "chat_diff")

    def chat_suggestions(self, context: str) -> list[str]:
        if context == "kpi":
            return ["（例）重要なKPIを追加・変更したい内容を入力してください"]
        return ["（例）シナリオの深掘り・保全策の追加などを入力してください"]
