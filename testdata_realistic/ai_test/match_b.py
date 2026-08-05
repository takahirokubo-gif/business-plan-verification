"""データBの検知率の一次判定（キーワード照合）。

planted_items のうち人への照会が期待される42行（「検知して照会」34行＋
「正シート・正ファイル識別」8行）を、同一事象（Base_B/Sponsor_Bの重複を
まとめた）25件のユニーク論点に集約し、AIが出力した確認事項（inquiries）・
抽出項目のmismatchのどれに当たるかを機械的に当てる。
最終判定は出力全文を人（レビュア）が確認して確定する。
"""
import json
import re
import sys
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"

# (論点ID, 見出し, planted行数, 判定キーワード群〔いずれか一致〕)
ISSUES = [
    ("U1", "月次試算表に単位ラベルなし（円フル桁）", 2,
     [r"月次", r"単位"]),
    ("N1", "科目改称：売上収益 ↔ 売上高", 2, [r"売上収益"]),
    ("N2", "科目改称：現業人件費（福利込）↔ スタッフ労務費", 2, [r"現業人件費"]),
    ("N3", "科目改称：修正EBITDA ↔ 正常収益力EBITDA", 2, [r"修正EBITDA"]),
    ("N4", "科目改称：売掛金等 ↔ 売上債権", 2, [r"売掛金等"]),
    ("N5", "科目改称：その他流動 ↔ その他流動資産", 2, [r"その他流動(?!資産)"]),
    ("N6", "科目改称：買掛・未払等 ↔ 仕入債務・未払費用", 2, [r"買掛・未払|買掛"]),
    ("S1", "本表外の補足小表①単価改定履歴（PL!P3:R11）", 2,
     [r"単価改定", r"P3", r"P3:R11"]),
    ("S2", "本表外の補足小表②採用チャネル内訳（calc!B23:D28）", 2,
     [r"採用チャネル", r"チャネル"]),
    ("S3", "本表外の補足小表③寮関連メモ（BS!P3:Q8）", 2, [r"寮"]),
    ("R1", "支払利息 FY27E〜33E が #REF!（PL!H28:N28）", 2,
     [r"#REF", r"参照切れ"]),
    ("G1", "のれん差異：モデル5,500,000千円 vs 財務DD 5,280百万円", 2,
     [r"5,?280", r"のれん.*差異|差異.*のれん"]),
    ("T1", "ティーザーEBITDA 1,585,000千円と確定値1,620百万円の時点差", 2,
     [r"1,?585", r"ティーザー"]),
    ("X1", "Scratchシートの旧のれん試算5,656,000千円（時点差）", 2,
     [r"5,?656", r"Scratch"]),
    ("U2", "単位系不一致：Excel千円 vs DD百万円", 1,
     [r"千円.*百万円|百万円.*千円"]),
    ("RD", "丸め差：FY25売上 13,363,127千円 vs DD 13,363百万円", 1,
     [r"13,?363"]),
    ("D3", "財務DDの多段QoE調整表（符号付き調整行＋脚注参照）", 1,
     [r"QoE", r"調整表", r"正常収益力.*調整"]),
    ("D4", "DD報告書が4分冊", 1, [r"4分冊|四分冊|分冊"]),
    ("D5", "分冊間クロスリファレンス（事業DD→法務DD等）", 1,
     [r"クロスリファレンス|相互参照|他分冊|分冊間"]),
    ("D6", "簿外リスク：未払残業代の潜在債務 最大300百万円", 1,
     [r"未払残業|残業代"]),
    # ここから「正シート・正ファイル識別」8行分（勝手に使わず照会・除外を明示すべき事象）
    ("V1", "旧版シート PL_old（※使用しないこと・全値0.965倍）を除外/照会", 2,
     [r"PL_old", r"旧版"]),
    ("V2", "作業用シート Scratch（誤った換算係数4,233,600）を除外/照会", 2,
     [r"Scratch", r"作業用シート", r"4,?233,?600"]),
    ("V3", "空シート Sheet1 の存在を照会", 2, [r"Sheet1", r"空シート"]),
    ("V4", "同一構造のケース違い2ファイル（Base_B/Sponsor_B）の正ファイル識別", 1,
     [r"Model_Base_B[^\n]{0,300}Model_Sponsor_B",
      r"Model_Sponsor_B[^\n]{0,300}Model_Base_B",
      r"正ファイル", r"どちらのケース|いずれのケース"]),
    ("V5", "デットスケジュールの別ファイル分離（Debt_B）の識別", 1,
     [r"Debt_B", r"デットスケジュール|デット・?スケジュール"]),
]


def haystacks(data):
    """照合対象テキスト：確認事項（全文）と抽出項目のmismatch注記。"""
    out = []
    for q in data["full"]["inquiries"]:
        src = q.get("source") or {}
        text = " ".join(str(x) for x in
                        [q["category"], q["title"], q.get("detail"),
                         q.get("suggested_question"), src.get("file"),
                         src.get("location"), src.get("quote"), src.get("logic")]
                        if x)
        out.append(("照会", f"[{q['severity']}] {q['title']}", text))
    for it in data["full"]["items"]:
        m = it.get("mismatch")
        if m:
            text = " ".join(str(x) for x in
                            [it["label"], m.get("other_value"), m.get("other_unit"),
                             m.get("other_file"), m.get("other_location"),
                             m.get("other_quote"), m.get("note")] if x is not None)
            out.append(("mismatch", f"{it['key']}（{it['label']}）", text))
        ev = it.get("evidence") or {}
        if it.get("source_type") in ("calculated", "estimated", "missing"):
            out.append(("項目logic", f"{it['key']}／{it.get('source_type')}",
                        str(ev.get("logic", ""))))
    return out


def main():
    data = json.loads((RES / "result_B.json").read_text(encoding="utf-8"))
    hs = haystacks(data)
    inq_n = len(data["full"]["inquiries"])
    print(f"# データB 検知率（一次判定・確認事項{inq_n}件／照合対象{len(hs)}ブロック）\n")
    print("| 論点 | 内容 | planted行数 | 判定 | 該当した出力 |")
    print("|---|---|---|---|---|")
    hit_rows = hit_issues = 0
    total_rows = sum(i[2] for i in ISSUES)
    unmatched = []
    used = set()
    for iid, title, rows, pats in ISSUES:
        found = []
        for idx, (kind, name, text) in enumerate(hs):
            if any(re.search(p, text) for p in pats):
                found.append(f"{kind}: {name}")
                used.add(idx)
        # 照会での検知を優先して表示する
        found.sort(key=lambda s: 0 if s.startswith("照会") else 1)
        ok = bool(found)
        if ok:
            hit_issues += 1
            hit_rows += rows
        else:
            unmatched.append(f"{iid} {title}")
        print(f"| {iid} | {title} | {rows} | {'○' if ok else '×'} | "
              f"{'<br>'.join(found[:3]) if found else '－'} |")
    print(f"\n- ユニーク論点：**{hit_issues}/{len(ISSUES)}**"
          f"（{hit_issues / len(ISSUES) * 100:.0f}%）")
    print(f"- planted行換算：**{hit_rows}/{total_rows}**"
          f"（{hit_rows / total_rows * 100:.0f}%）")
    if unmatched:
        print("\n未検知（一次判定）：")
        for u in unmatched:
            print(f"- {u}")

    extra = [hs[i] for i in range(len(hs)) if i not in used and hs[i][0] == "照会"]
    if extra:
        print(f"\nplantedに紐づかなかった確認事項（{len(extra)}件・"
              "追加検知か誤検知かは人が判定）：")
        for _, name, _ in extra:
            print(f"- {name}")


if __name__ == "__main__":
    sys.exit(main())
