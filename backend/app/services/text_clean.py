"""AI出力テキストの整形（人が読む文章から内部表現を除去する）。

プロンプトでも禁止しているが、稀に "values=null" や "source_type=missing" のような
スキーマ用語が説明文へ混入する。画面・帳票にそのまま出ると不自然なため、
保存前にここで自然な日本語へ置き換える。数値・出典の情報は壊さない。
"""
import re

# 置換規則（出現しやすい順）。値の意味を保ったまま日本語表現へ直す
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"（\s*values?\s*=\s*null\s*）"), "（資料に記載なし）"),
    (re.compile(r"\(\s*values?\s*=\s*null\s*\)"), "（資料に記載なし）"),
    (re.compile(r"、?\s*values?\s*=\s*null\s*"), "（資料に記載なし）"),
    (re.compile(r"（\s*source_type\s*=\s*missing\s*）"), "（未取得）"),
    (re.compile(r"source_type\s*=\s*missing"), "未取得"),
    (re.compile(r"source_type\s*=\s*estimated"), "AI推定"),
    (re.compile(r"source_type\s*=\s*calculated"), "資料内の数式からの計算値"),
    (re.compile(r"source_type\s*=\s*extracted"), "資料の記載値"),
    (re.compile(r"（\s*null\s*）"), "（該当なし）"),
    (re.compile(r"(?<![A-Za-z_])null(?![A-Za-z_])"), "該当なし"),
]

_SPACE = re.compile(r"[ \t]{2,}")


def clean_text(text: str | None) -> str | None:
    """人が読む文章から内部表現を除去する。Noneはそのまま返す。"""
    if not text:
        return text
    out = text
    for pattern, repl in _RULES:
        out = pattern.sub(repl, out)
    out = out.replace("（（", "（").replace("））", "）")
    out = _SPACE.sub(" ", out)
    return out.strip()


_HUMAN_KEYS = {"text_value", "detail", "note", "logic", "quote", "summary",
               "impact", "cause", "change_text", "change_basis", "safeguards",
               "questions", "title", "suggested_question", "value_text",
               "before", "after", "label"}


def _clean_human(v):
    """人が読むフィールドの値を整形する。文字列の配列（questions等）にも対応する。"""
    if isinstance(v, str):
        return clean_text(v)
    if isinstance(v, list):
        return [clean_text(x) if isinstance(x, str) else clean_obj(x) for x in v]
    return clean_obj(v)


def clean_obj(obj):
    """dict/list を再帰的に走査し、人が読むフィールドだけを整形する。"""
    if isinstance(obj, dict):
        return {k: (_clean_human(v) if k in _HUMAN_KEYS else clean_obj(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_obj(v) for v in obj]
    return obj
