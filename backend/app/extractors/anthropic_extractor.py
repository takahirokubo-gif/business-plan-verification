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

from ..config import ANTHROPIC_API_KEY
from .base import Extractor
from .factory import get_model

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
                    "mismatch": {
                        "type": ["object", "null"],
                        "description": "資料間で値が食い違う場合の相手側情報。無ければnull",
                        "properties": {
                            "other_value": {
                                "type": ["number", "null"],
                                "description": "相手資料側の数値（表示単位に換算済み）。"
                                               "単一の数値で表せない差異はnull"},
                            "other_file": {"type": "string"},
                            "other_location": {"type": "string"},
                            "other_quote": {"type": "string"},
                            "note": {"type": "string",
                                     "description": "差異の内容と審査上の論点（どちらを採用すべきか等）"},
                        },
                        "required": ["other_value", "other_file",
                                     "other_location", "other_quote", "note"],
                    },
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
                    "value_text": {"type": ["string", "null"],
                                   "description": "最新の値（例: '88%（FY26実績）'）。"
                                                  "数式はここに入れず formula に書く"},
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
                                      "description": "確定KPIツリーのノードIDのみを入れる"
                                                     "（ラベルや括弧書きを付けない。例: 'B31'）"},
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

DEAL_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "案件名（対象会社名＋スキーム）"},
                "deal_type": {"type": "string", "enum": ["LBO", "MBO", "事業承継", "リファイナンス"]},
                "borrower": {"type": "string", "description": "借入人（SPC）"},
                "target": {"type": "string", "description": "対象会社"},
                "industry": {"type": ["string", "null"]},
                "sponsor": {"type": ["string", "null"]},
                "close_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                "ev_mm": {"type": ["number", "null"], "description": "EV（百万円）"},
                "senior_mm": {"type": ["number", "null"]},
                "equity_mm": {"type": ["number", "null"]},
                "tenor_years": {"type": ["number", "null"]},
                "sponsor_ebitda_mm": {"type": ["number", "null"],
                                      "description": "スポンサー提示EBITDA（速報値・百万円）"},
                "summary": {"type": ["string", "null"], "description": "案件概要の要約（3文程度）"},
            },
            "required": ["name", "deal_type", "borrower", "target"],
        },
        "sources": {"type": "object",
                    "description": "各フィールドの出典（ファイル・シート/セルまたはページ）"},
        "note": {"type": "string"},
    },
    "required": ["fields", "sources"],
}

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "diff": {
            "type": ["object", "null"],
            "description": "適用可能な変更差分。変更が無ければnull",
            "properties": {
                "type": {"type": "string",
                         "enum": ["add_node", "star_change", "add_card", "update_card"]},
                "node": {"type": ["object", "null"],
                         "description": "add_node時に必須: "
                                        "{id, parent, label, origin:'manual', star, "
                                        "badge, value_text, evidence}"},
                "remove": {"type": ["array", "null"], "items": {"type": "string"},
                           "description": "star_change時: ★を外すノードID"},
                "add": {"type": ["array", "null"], "items": {"type": "string"},
                        "description": "star_change時: ★を付けるノードID"},
                "card": {"type": ["object", "null"],
                         "description": "add_card時に必須: 標準5部構成のカード"
                                        "（key, origin:'human', type_label, title, cause, "
                                        "affected_kpis, change_text, change_basis, impact, "
                                        "safeguards, questions）"},
                "card_key": {"type": ["string", "null"],
                             "description": "update_card時に必須: 対象カードのkey"},
                "fields": {"type": ["object", "null"],
                           "description": "update_card時に必須: 変更するフィールドのみ"},
            },
            "required": ["type"],
        },
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
    """Excelのシート構造・ラベル・数式をLLM入力用のテキストに要約する（値の再計算はしない）。

    数式セルは「数式＋Excel保存時のキャッシュ値」の両方を出す。数式はKPIツリーの
    構文解析に、キャッシュ値は数値の拾い上げ（転記）に必要（再計算はしない）。
    Excelで保存されたファイルは計算結果をキャッシュ値として保持している。
    キャッシュ値が無い場合（Excel以外で生成された未計算ファイル）は数式のみになる。
    """
    from openpyxl import load_workbook
    wb = load_workbook(path)                    # 数式
    wbv = load_workbook(path, data_only=True)   # キャッシュ値（Excel保存時の計算結果）
    out = []
    for ws in wb.worksheets:
        wsv = wbv[ws.title]
        out.append(f"=== シート: {ws.title} ===")
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 60),
                                max_col=min(ws.max_column, 12)):
            cells = []
            for c in row:
                if c.value is None:
                    continue
                if isinstance(c.value, str) and c.value.startswith("="):
                    cached = wsv[c.coordinate].value
                    if cached is not None:
                        cells.append(f"{c.coordinate}: {c.value!r} → 値 {cached!r}")
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
        # 根拠3点セット付きの抽出項目一覧は長くなる。8192では途中で切れて
        # tool入力のJSONが不完全になる（実APIで確認済み）ため大きめに取る。
        # 大きなmax_tokensはSDKがストリーミングを要求するためstreamで受ける
        with self.client.messages.stream(
            model=get_model(),  # 設定UIから実行時に切替可能
            max_tokens=32000,
            system=SYSTEM_PROMPT,
            tools=[dict(name=tool_name, description="構造化された抽出結果を返す",
                        input_schema=schema)],
            tool_choice=dict(type="tool", name=tool_name),
            messages=[dict(role="user", content=prompt)],
        ) as stream:
            resp = stream.get_final_message()
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(
                "AI応答が最大出力長に達して打ち切られました。資料の分量を減らして再実行してください")
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

    def extract_deal_info(self, documents: list[dict]) -> dict:
        parts = []
        for doc in documents:
            p = Path(doc["stored_path"])
            parts.append(f"--- ファイル: {doc['filename']}（{doc['slot']}）---")
            if p.suffix == ".xlsx":
                parts.append(_excel_digest(p)[:12000])
            else:
                parts.append(_pdf_digest(p, max_pages=8))
        parts.append(
            "\n上記資料から案件の基本情報（案件名・案件種別・借入人SPC・対象会社・業種・"
            "スポンサー・クローズ予定日・EV・シニアローン総額・エクイティ・期間・"
            "スポンサー提示EBITDA・案件概要）を読み取ってください。"
            "各フィールドの出典（ファイル＋シート/セルまたはページ）を sources に必ず記載すること。"
            "本行取組額・担当者・審査相談予定日は行内情報のため対象外。"
            "資料に無い項目は null にすること（推測しない）。")
        return self._call("\n".join(parts), DEAL_INFO_SCHEMA, "extract_deal_info")

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
            "金額はシートの単位注記に基づき百万円に換算し、換算した旨をlogicに含めること。\n"
            "keyの命名規則：以下に該当する項目は必ずこの標準キーを使うこと（帳票出力が参照する）。"
            "実績: act_revenue／act_op（営業利益）／act_ebitda／act_ni（当期純利益）／"
            "act_cash（現預金）／act_net_assets（純資産）／act_debt（有利子負債）／act_fcf。"
            "Baseケース計画: base_revenue／base_op／base_ebitda／base_fcf。"
            "Sponsorケース計画: sponsor_revenue／sponsor_op／sponsor_ebitda／sponsor_fcf。"
            "ストラクチャー: ev／senior_loan／goodwill。その他: normalized_ebitda（正常収益力EBITDA）。"
            "該当しない項目は内容がわかる英小文字スネークケースで命名。\n"
            "valuesの年度キーは『FY+西暦下2桁』（例: FY24, FY27）で統一すること"
            "（『2027/3期』のような決算期表記は使わない。決算期はlogicに記す）。")
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
