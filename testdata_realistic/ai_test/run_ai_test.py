"""実AI（EXTRACTOR_MODE=anthropic）でのテスト実行ランナー。

実際の画面と同じAPIフロー（下書き作成→資料アップロード→案件情報の自動読み取り→
AI解析3ステップ）をそのまま叩き、結果の生JSONを保存する。採点は score.py 側で行う。

解析は画面と同じく items → kpi → scenarios の3リクエストに分けて呼ぶ。
途中のステップが失敗しても止めずに後続を続け、失敗の内容（HTTPステータス・本文）と
サーバー側の解析ログ（analysis_runs：トークン数・stop_reason・所要時間）を
結果JSONに残す。「AIが検知しなかった」のか「打ち切り／エラーで落ちた」のかを
採点時に切り分けるため。

使い方:
    # 別ターミナルでサーバを起動（EXTRACTOR_MODE=anthropic）
    backend/.venv/bin/python -m uvicorn app.main:app --port 8011   # cwd=backend/

    backend/.venv/bin/python testdata_realistic/ai_test/run_ai_test.py A
    backend/.venv/bin/python testdata_realistic/ai_test/run_ai_test.py B
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "results"
BASE = "http://127.0.0.1:8011"
USER = "shinsa"

DATASETS = {
    "A": [
        ("testdata_realistic/A_standard/AutostaffChubu_Model_A.xlsx", "model_base"),
        ("testdata_realistic/A_standard/DD_Report_統合版_オートスタッフ中部_A.pdf",
         "dd_integrated"),
    ],
    # 財務モデル3冊は「種別なしで取り込む」（unclassified）で投入し、
    # どれが正・どれが別ケースかの識別そのものをAIの評価対象にする
    "B": [
        ("testdata_realistic/B_hard/AutostaffChubu_Model_Base_B.xlsx", "unclassified"),
        ("testdata_realistic/B_hard/AutostaffChubu_Model_Sponsor_B.xlsx", "unclassified"),
        ("testdata_realistic/B_hard/AutostaffChubu_Debt_B.xlsx", "unclassified"),
        ("testdata_realistic/B_hard/DD_Business_オートスタッフ中部.pdf", "dd_business"),
        ("testdata_realistic/B_hard/DD_Financial_オートスタッフ中部.pdf", "dd_financial"),
        ("testdata_realistic/B_hard/DD_Legal_オートスタッフ中部.pdf", "dd_legal"),
        ("testdata_realistic/B_hard/DD_Tax_オートスタッフ中部.pdf", "dd_tax"),
    ],
}

ANALYZE_STEPS = ["items", "kpi", "scenarios"]


def main(dataset: str):
    files = DATASETS[dataset]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log = []

    def step(name, fn):
        t0 = time.time()
        result = fn()
        dt = time.time() - t0
        log.append(dict(step=name, seconds=round(dt, 1)))
        print(f"[{dt:6.1f}s] {name}", flush=True)
        return result

    mode = requests.get(f"{BASE}/api/extract/mode", timeout=30).json()
    print("extractor:", mode)
    assert mode.get("mode") == "anthropic", "サーバがanthropicモードではありません"

    deal = step("下書き案件の作成",
                lambda: requests.post(f"{BASE}/api/deals/draft", json=dict(user=USER),
                                      timeout=60).json())
    deal_id = deal["id"]
    print("deal_id:", deal_id)

    uploads = []
    for rel, slot in files:
        path = ROOT / rel
        assert path.exists(), path

        def up(path=path, slot=slot):
            with path.open("rb") as f:
                r = requests.post(
                    f"{BASE}/api/deals/{deal_id}/documents",
                    data=dict(slot=slot, user=USER),
                    files={"file": (path.name, f)}, timeout=600)
            r.raise_for_status()
            return r.json()

        res = step(f"アップロード＋種別判定: {path.name}", up)
        print(f"   → 判定: {res.get('identified_label')}（{res.get('identified_company')}）",
              flush=True)
        uploads.append(res)

    info = step("案件情報の自動読み取り",
                lambda: requests.post(
                    f"{BASE}/api/deals/{deal_id}/extract-info",
                    params=dict(user=USER), timeout=1200).json())
    fields = {k: v for k, v in (info.get("fields") or {}).items() if v is not None}
    if fields:
        step("案件情報の確定（PATCH）",
             lambda: requests.patch(f"{BASE}/api/deals/{deal_id}",
                                    json=dict(**fields, user=USER), timeout=60).json())

    # 解析3ステップ。失敗しても止めず、失敗内容を記録して次のステップへ進む
    analyze = {}
    for name in ANALYZE_STEPS:
        def call(name=name):
            r = requests.post(f"{BASE}/api/deals/{deal_id}/analyze/{name}",
                              params=dict(user=USER), timeout=3600)
            try:
                body = r.json()
            except ValueError:
                body = dict(raw=r.text[:2000])
            return dict(status_code=r.status_code, ok=r.ok, body=body)

        res = step(f"AI解析: {name}", call)
        analyze[name] = res
        print(f"   → {res['status_code']} "
              f"{json.dumps(res['body'], ensure_ascii=False)[:400]}", flush=True)

    full = requests.get(f"{BASE}/api/deals/{deal_id}/full", timeout=120).json()
    out = OUT_DIR / f"result_{dataset}.json"
    out.write_text(json.dumps(
        dict(dataset=dataset, deal_id=deal_id, model=mode, uploads=uploads,
             deal_info=info, analyze=analyze, timing=log, full=full),
        ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved:", out)

    print("\n--- 解析ログ（analysis_runs） ---")
    for r in full.get("analysis_runs", []):
        print(f"{r.get('step'):<10} {str(r.get('status')):<10} "
              f"in={r.get('input_tokens')} out={r.get('output_tokens')}"
              f"/{r.get('max_tokens')} stop={r.get('stop_reason')} "
              f"{r.get('duration_ms')}ms "
              f"{r.get('result_summary') or r.get('error') or ''}")


if __name__ == "__main__":
    main(sys.argv[1].upper())
