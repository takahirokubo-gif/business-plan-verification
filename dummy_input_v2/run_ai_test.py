# -*- coding: utf-8 -*-
"""実生成AI（AnthropicExtractor）の動作・精度テストランナー。

このディレクトリのダミーインプット（理想的インプット）を実AIに解析させ、
expected_output.json（答え）と突き合わせて採点する。

前提:
  - 依存: backend/requirements.txt 相当（anthropic, openpyxl, pypdf, python-dotenv）
  - 環境変数 ANTHROPIC_API_KEY（または backend/.env）
  - 事前に generate_all.py で入力・期待値が生成済みであること

使い方:
  ANTHROPIC_API_KEY=sk-... python3 run_ai_test.py                # 全ステップ
  python3 run_ai_test.py --steps identify,deal_info,items        # 一部のみ
  python3 run_ai_test.py --score-only                            # 前回のraw出力を再採点

出力:
  test_results/raw_<step>.json …… AIの生出力（再採点・人手レビュー用）
  test_results/report.md / report.json …… 採点結果

採点の考え方:
  - identify / deal_info / items（数値・根拠・不整合）は機械採点（決定論）
  - kpi_tree / scenarios は生成タスクのため構造ルーブリックで機械チェックし、
    内容の最終判断は raw 出力の人手レビューで行う
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "test_results"
BACKEND = HERE.parent / "backend"

import spec  # noqa: E402

EXPECTED = json.loads((HERE / "expected_output.json").read_text(encoding="utf-8"))

SLOT_FILES = {
    "model_sponsor": spec.MODEL_FILES["sponsor"],
    "model_base": spec.MODEL_FILES["base"],
    "dd_business": spec.DD_FILES["business"],
    "dd_financial": spec.DD_FILES["financial"],
    "dd_legal": spec.DD_FILES["legal"],
    "dd_tax": spec.DD_FILES["tax"],
}

STEPS = ["identify", "deal_info", "items", "kpi_tree", "scenarios"]


# ---------------------------------------------------------------- 正規化

_YEAR_PAT = re.compile(r"(?:FY|ＦＹ)?\s*(20)?(2[3-9]|3[0-9])\s*(?:/\s*3\s*期?|年3月期|年度|年)?",
                       re.IGNORECASE)


def normalize_year(key: str) -> str | None:
    """'FY27' '2027/3期' '27/3期' '2027年3月期' '2027' → 'FY27'"""
    m = _YEAR_PAT.search(str(key))
    if not m:
        return None
    yy = int(m.group(2))
    return f"FY{yy}"


def normalize_number(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("百万円", "").replace("▲", "-").strip()
    try:
        return float(s)
    except ValueError:
        return None


def normalize_values(values: dict | None) -> dict:
    out = {}
    for k, v in (values or {}).items():
        y = normalize_year(k)
        n = normalize_number(v)
        if y and n is not None:
            out[y] = n
    return out


def text_of(item: dict) -> str:
    parts = [str(item.get("text_value") or ""), str(item.get("label") or "")]
    ev = item.get("evidence") or {}
    parts.append(str(ev.get("quote") or ""))
    parts.append(str(ev.get("logic") or ""))
    return " ".join(parts)


def page_of(location: str) -> int | None:
    m = re.search(r"[pP]\.?\s*(\d+)", str(location)) or \
        re.search(r"(\d+)\s*ページ", str(location))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- 実行

def build_documents() -> list[dict]:
    docs = []
    for slot, fname in SLOT_FILES.items():
        path = HERE / fname
        if not path.exists():
            raise SystemExit(f"入力ファイルがありません: {fname}（generate_all.py を先に実行）")
        docs.append(dict(slot=slot, filename=fname, stored_path=str(path)))
    return docs


def make_extractor():
    sys.path.insert(0, str(BACKEND))
    from app.extractors.anthropic_extractor import AnthropicExtractor
    return AnthropicExtractor()


def run_steps(steps: list[str]):
    RESULTS.mkdir(exist_ok=True)
    ex = make_extractor()
    docs = build_documents()
    deal = {k: spec.DEAL[k] for k in
            ("name", "deal_type", "borrower", "target", "industry", "sponsor",
             "ev_mm", "senior_mm", "equity_mm", "tenor_years", "sponsor_ebitda_mm")}
    if "identify" in steps:
        out = {}
        for d in docs:
            print(f"identify: {d['filename']} ...")
            out[d["filename"]] = ex.identify_document(d["filename"], Path(d["stored_path"]))
        _save("identify", out)
    if "deal_info" in steps:
        print("extract_deal_info ...")
        _save("deal_info", ex.extract_deal_info(docs))
    if "items" in steps:
        print("extract_items ...")
        _save("items", ex.extract_items(deal, docs))
    if "kpi_tree" in steps:
        print("propose_kpi_tree ...")
        _save("kpi_tree", ex.propose_kpi_tree(deal, docs))
    if "scenarios" in steps:
        print("propose_scenarios ...")
        _save("scenarios", ex.propose_scenarios(deal, docs))


def _save(step: str, obj):
    p = RESULTS / f"raw_{step}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved: {p.relative_to(HERE)}")


def _load(step: str):
    p = RESULTS / f"raw_{step}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 採点

def score_identify(raw) -> dict:
    rows = []
    ok = 0
    for fname, exp in EXPECTED["identify"].items():
        got = (raw or {}).get(fname) or {}
        good_type = got.get("doc_type") == exp["doc_type"]
        good_co = "ルミエールボーテ" in str(got.get("company", ""))
        ok += int(good_type and good_co)
        rows.append(dict(file=fname, expected=exp["doc_type"],
                         got=got.get("doc_type"), company=got.get("company"),
                         ok=good_type and good_co))
    return dict(score=f"{ok}/{len(rows)}", ok=ok, total=len(rows), rows=rows)


def score_deal_info(raw) -> dict:
    fields = (raw or {}).get("fields") or {}
    exp = EXPECTED["deal_info"]["fields"]
    rows = []

    def add(name, expected, got, ok):
        rows.append(dict(field=name, expected=expected, got=got, ok=bool(ok)))

    add("name", exp["name_contains"], fields.get("name"),
        any(s in str(fields.get("name", "")) for s in exp["name_contains"]))
    add("deal_type", exp["deal_type"], fields.get("deal_type"),
        fields.get("deal_type") == exp["deal_type"])
    add("borrower", exp["borrower"], fields.get("borrower"),
        exp["borrower"] in str(fields.get("borrower", "")))
    add("target", exp["target"], fields.get("target"),
        exp["target"] in str(fields.get("target", ""))
        or str(fields.get("target", "")) in exp["target"]
        and "ルミエールボーテ" in str(fields.get("target", "")))
    add("industry", exp["industry_contains"], fields.get("industry"),
        any(s in str(fields.get("industry", "")) for s in exp["industry_contains"]))
    add("sponsor", exp["sponsor"], fields.get("sponsor"),
        "大手町プリンシパル" in str(fields.get("sponsor", "")))
    add("close_date", exp["close_date"], fields.get("close_date"),
        str(fields.get("close_date", "")).startswith("2026-11"))
    for k in ("ev_mm", "senior_mm", "equity_mm", "tenor_years", "sponsor_ebitda_mm"):
        add(k, exp[k], fields.get(k),
            normalize_number(fields.get(k)) == float(exp[k]))
    sources = (raw or {}).get("sources") or {}
    add("sources（全フィールドに出典）", "各フィールドの出典", f"{len(sources)}件",
        len(sources) >= 8)
    ok = sum(r["ok"] for r in rows)
    return dict(score=f"{ok}/{len(rows)}", ok=ok, total=len(rows), rows=rows)


def _match_candidates(exp_item: dict, predicted: list[dict]) -> list[dict]:
    aliases = [a.lower() for a in exp_item.get("label_aliases", [exp_item["label"]])]
    out = []
    for p in predicted:
        if (exp_item.get("case") or None) != (p.get("case") or None):
            continue
        label = str(p.get("label", "")).lower()
        key = str(p.get("key", "")).lower()
        if key == exp_item["key"] or any(a in label for a in aliases):
            out.append(p)
    return out


def score_items(raw) -> dict:
    predicted = raw or []
    rows = []
    for exp_item in EXPECTED["items"]:
        cands = _match_candidates(exp_item, predicted)
        best = None
        best_score = -1.0
        for p in cands:
            s = _item_score(exp_item, p)
            if s["value_score"] > best_score:
                best, best_score = (p, s), s["value_score"]
        if best is None:
            rows.append(dict(key=exp_item["key"], label=exp_item["label"],
                             required=exp_item["required"], found=False,
                             value_score=0.0, evidence_ok=False, mismatch_ok=None,
                             note="対応する抽出項目なし"))
            continue
        p, s = best
        rows.append(dict(key=exp_item["key"], label=exp_item["label"],
                         required=exp_item["required"], found=True,
                         matched_label=p.get("label"), matched_key=p.get("key"),
                         **s))
    n_found = sum(r["found"] for r in rows)
    val_full = sum(1 for r in rows if r["value_score"] >= 1.0)
    ev_ok = sum(1 for r in rows if r.get("evidence_ok"))
    req_rows = [r for r in rows if r["required"]]
    req_full = sum(1 for r in req_rows if r["value_score"] >= 1.0)
    req_ev = sum(1 for r in req_rows if r.get("evidence_ok"))
    mm = [r for r in rows if r.get("mismatch_ok") is not None]
    # 合格ライン（ユーザー決定）：必須項目の値一致率100%・根拠一致率90%
    value_rate = req_full / len(req_rows) if req_rows else 0.0
    evidence_rate = req_ev / len(req_rows) if req_rows else 0.0
    return dict(
        found=f"{n_found}/{len(rows)}",
        value_exact=f"{val_full}/{len(rows)}",
        required_value_exact=f"{req_full}/{len(req_rows)}",
        required_evidence=f"{req_ev}/{len(req_rows)}",
        evidence_ok=f"{ev_ok}/{len(rows)}",
        mismatch=f"{sum(1 for r in mm if r['mismatch_ok'])}/{len(mm)}",
        required_value_rate=round(value_rate, 3),
        required_evidence_rate=round(evidence_rate, 3),
        passed=bool(value_rate >= 1.0 and evidence_rate >= 0.90),
        pass_criteria="必須項目：値一致率100% かつ 根拠一致率90%以上",
        rows=rows,
    )


def _item_score(exp_item: dict, p: dict) -> dict:
    # 値の採点
    if exp_item.get("values"):
        exp_vals = {y: float(v) for y, v in exp_item["values"].items()}
        got_vals = normalize_values(p.get("values"))
        if exp_item.get("single_value") is not None:
            hit = float(exp_item["single_value"]) in got_vals.values() or \
                normalize_number(p.get("text_value")) == float(exp_item["single_value"])
            value_score = 1.0 if hit else 0.0
            wrong = [] if hit else [f"期待 {exp_item['single_value']} / 取得 {got_vals}"]
        else:
            okays = [y for y, v in exp_vals.items() if got_vals.get(y) == v]
            value_score = len(okays) / len(exp_vals)
            wrong = [f"{y}: 期待{exp_vals[y]:,.0f} 取得{got_vals.get(y)}"
                     for y in exp_vals if got_vals.get(y) != exp_vals[y]]
    else:
        text = text_of(p)
        groups = exp_item.get("text_expects") or []
        hit_groups = [g for g in groups if any(kw in text for kw in g)]
        value_score = len(hit_groups) / len(groups) if groups else 1.0
        wrong = ["|".join(g) for g in groups if not any(kw in text for kw in g)]

    # 根拠の採点
    ev = p.get("evidence") or {}
    exp_ev = exp_item["evidence"]
    file_ok = ev.get("file") == exp_ev["file"] or \
        str(exp_ev["file"]).split(".")[0] in str(ev.get("file", ""))
    loc = str(ev.get("location", ""))
    if "page" in exp_ev:
        got_page = page_of(loc)
        tol = exp_item.get("page_tolerance", 0)
        loc_ok = got_page is not None and abs(got_page - exp_ev["page"]) <= tol
    else:
        loc_ok = (exp_ev.get("sheet") and exp_ev["sheet"] in loc) or \
            (exp_ev.get("alt_sheet") and exp_ev["alt_sheet"] in loc)
    # 不整合の採点
    mismatch_ok = None
    if exp_item.get("mismatch"):
        mm = p.get("mismatch")
        mismatch_ok = bool(mm) and (
            normalize_number((mm or {}).get("other_value")) ==
            float(exp_item["mismatch"]["other_value"])
            or str(exp_item["mismatch"]["other_value"]) in json.dumps(
                mm or {}, ensure_ascii=False).replace(",", ""))
    return dict(value_score=round(value_score, 3),
                value_wrong=wrong[:6],
                evidence_ok=bool(file_ok and loc_ok),
                evidence_got=f"{ev.get('file')} / {loc}",
                mismatch_ok=mismatch_ok)


def _label_match(label: str, aliases: list[str]) -> bool:
    return any(a in label for a in aliases)


def score_kpi_tree(raw) -> dict:
    nodes = (raw or {}).get("nodes") or []
    by_id = {n.get("id"): n for n in nodes}
    exp = EXPECTED["kpi_tree"]
    edge_rows = []
    for parent_aliases, child_aliases in exp["required_edges"]:
        found = False
        for n in nodes:
            if not _label_match(str(n.get("label", "")), child_aliases):
                continue
            parent = by_id.get(n.get("parent"))
            if parent and _label_match(str(parent.get("label", "")), parent_aliases):
                found = True
                break
        edge_rows.append(dict(edge=f"{parent_aliases[0]} → {child_aliases[0]}", ok=found))
    stars = [n for n in nodes if n.get("star")]
    stars_valid = [n for n in stars
                   if any(_label_match(str(n.get("label", "")), c)
                          for c in exp["star_candidates"])]
    dd_nodes = [n for n in nodes
                if n.get("origin") == "dd"
                and any(_label_match(str(n.get("label", "")), c)
                        for c in exp["dd_node_candidates"])]
    ev_missing = [n.get("id") for n in nodes if not n.get("evidence")]
    ok_edges = sum(r["ok"] for r in edge_rows)
    return dict(
        nodes=len(nodes),
        edges=f"{ok_edges}/{len(edge_rows)}",
        stars=f"{len(stars)}（うち候補内 {len(stars_valid)}・最低{exp['min_stars']}）",
        stars_ok=len(stars) >= exp["min_stars"] and len(stars_valid) == len(stars),
        dd_nodes=len(dd_nodes),
        evidence_missing=ev_missing[:5],
        edge_rows=edge_rows,
        note="内容の妥当性は raw_kpi_tree.json を人手レビュー",
    )


def score_scenarios(raw) -> dict:
    cards = raw or []
    exp = EXPECTED["scenarios"]
    rows = []
    covered_types = {c.get("type_label") for c in cards}
    for c in cards:
        impact = str(c.get("impact", ""))
        parts_missing = [k for k in exp["required_parts"] if not c.get(k)]
        has_num = bool(re.search(r"\d", impact))
        mentions = any(w in impact for w in exp["impact_must_mention_any"])
        forbidden = [w for w in exp["forbidden_labels"]
                     if w in json.dumps(c, ensure_ascii=False)]
        type_key = {"トップライン": "topline", "コスト": "cost",
                    "イベント": "event"}.get(str(c.get("type_label")))
        anchors = exp["fact_anchors"].get(type_key or "", [])
        blob = json.dumps(c, ensure_ascii=False)
        anchored = any(a in blob for a in anchors) if anchors else None
        rows.append(dict(key=c.get("key"), type=c.get("type_label"),
                         title=c.get("title"),
                         parts_missing=parts_missing, impact_has_number=has_num,
                         impact_mentions_debt_metrics=mentions,
                         forbidden_labels=forbidden, fact_anchored=anchored))
    types_ok = set(exp["type_labels"]) <= covered_types
    return dict(
        cards=len(cards),
        three_types_covered=types_ok,
        rows=rows,
        note="内容の妥当性（変化幅・保全策・確認事項の質）は raw_scenarios.json を人手レビュー",
    )


SCORERS = dict(identify=score_identify, deal_info=score_deal_info,
               items=score_items, kpi_tree=score_kpi_tree, scenarios=score_scenarios)


def build_report(results: dict) -> str:
    out = ["# 実AIテスト採点レポート（ルミエールボーテ・理想的インプット）", ""]
    w = out.append
    if "identify" in results:
        r = results["identify"]
        w(f"## identify（ファイル識別）: {r['score']}")
        for row in r["rows"]:
            mark = "OK" if row["ok"] else "NG"
            w(f"- {mark} {row['file']}: {row['got']}（期待 {row['expected']}）")
        w("")
    if "deal_info" in results:
        r = results["deal_info"]
        w(f"## deal_info（案件基本情報）: {r['score']}")
        for row in r["rows"]:
            mark = "OK" if row["ok"] else "NG"
            w(f"- {mark} {row['field']}: 取得 `{row['got']}`（期待 `{row['expected']}`）")
        w("")
    if "items" in results:
        r = results["items"]
        verdict = "🟢 合格" if r["passed"] else "🔴 不合格"
        w(f"## items（抽出24項目）: **{verdict}**")
        w(f"- 合格ライン: {r['pass_criteria']}")
        w(f"- 必須項目の値一致率: {r['required_value_rate']:.0%}"
          f"（{r['required_value_exact']}）／ 必須項目の根拠一致率: "
          f"{r['required_evidence_rate']:.0%}（{r['required_evidence']}）")
        w(f"- 参考（全24項目）: 発見 {r['found']} ／ 値完全一致 {r['value_exact']}"
          f" ／ 根拠一致 {r['evidence_ok']} ／ 不整合検知 {r['mismatch']}")
        w("")
        w("| key | 発見 | 値 | 根拠 | 不整合 | メモ |")
        w("|---|---|---|---|---|---|")
        for row in r["rows"]:
            found = "○" if row["found"] else "×"
            val = f"{row['value_score']:.0%}"
            ev = "○" if row.get("evidence_ok") else "×"
            mm = {None: "-", True: "○", False: "×"}[row.get("mismatch_ok")]
            note = "; ".join(row.get("value_wrong", [])[:2]) or ""
            w(f"| {row['key']} | {found} | {val} | {ev} | {mm} | {note} |")
        w("")
    if "kpi_tree" in results:
        r = results["kpi_tree"]
        w(f"## kpi_tree（構造ルーブリック）: エッジ {r['edges']}・ノード{r['nodes']}個")
        w(f"- ★: {r['stars']} → {'OK' if r['stars_ok'] else 'NG'}"
          f" ／ DD由来ノード: {r['dd_nodes']}個")
        for row in r["edge_rows"]:
            w(f"- {'OK' if row['ok'] else 'NG'} {row['edge']}")
        w("")
    if "scenarios" in results:
        r = results["scenarios"]
        w(f"## scenarios（構造ルーブリック）: {r['cards']}件・3類型カバー="
          f"{'OK' if r['three_types_covered'] else 'NG'}")
        for row in r["rows"]:
            w(f"- {row['key']}（{row['type']}）{row['title']}")
            w(f"  - 5部構成欠落: {row['parts_missing'] or 'なし'} / "
              f"数値推定: {'○' if row['impact_has_number'] else '×'} / "
              f"DSCR等への言及: {'○' if row['impact_mentions_debt_metrics'] else '×'} / "
              f"判定ラベル混入: {row['forbidden_labels'] or 'なし'} / "
              f"DD事実の引用: {row['fact_anchored']}")
        w("")
    w("---")
    w("生出力は test_results/raw_*.json。KPIツリー・シナリオは人手レビューを併用すること。")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default=",".join(STEPS),
                    help=f"実行ステップ（カンマ区切り）: {STEPS}")
    ap.add_argument("--score-only", action="store_true",
                    help="APIを呼ばず、前回の raw_*.json を再採点する")
    args = ap.parse_args()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = set(steps) - set(STEPS)
    if unknown:
        raise SystemExit(f"不明なステップ: {unknown}")

    if not args.score_only:
        run_steps(steps)

    results = {}
    for step in steps:
        raw = _load(step)
        if raw is None:
            print(f"skip scoring {step}: raw_{step}.json なし")
            continue
        results[step] = SCORERS[step](raw)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    report = build_report(results)
    (RESULTS / "report.md").write_text(report, encoding="utf-8")
    print()
    print(report)
    print(f"レポート: {RESULTS / 'report.md'}")


if __name__ == "__main__":
    main()
