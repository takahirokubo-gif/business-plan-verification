# -*- coding: utf-8 -*-
"""ダミーインプット一式（v2・ルミエールボーテ）の一括生成＋整合チェック。

順序:
 1. spec.py の主要ピン検証
 2. 財務モデルExcel 2ケース（LibreOfficeで再計算しキャッシュ値を付与）
 3. DDレポートPDF 4種
 4. 期待アウトプット（expected_output.json / GROUND_TRUTH.md）
 5. validate.py による全体整合チェック
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

STEPS = [
    ("spec 検証", [sys.executable, "spec.py"]),
    ("財務モデル生成", [sys.executable, "generate_model.py"]),
    ("DDレポートPDF生成", [sys.executable, "generate_pdfs.py"]),
    ("期待アウトプット生成", [sys.executable, "generate_expected.py"]),
    ("模範解答生成", [sys.executable, "generate_reference.py"]),
    ("整合チェック", [sys.executable, "validate.py"]),
]


def main():
    for name, cmd in STEPS:
        print(f"==== {name} ====")
        r = subprocess.run(cmd, cwd=HERE)
        if r.returncode != 0:
            print(f"FAILED: {name}", file=sys.stderr)
            sys.exit(1)
    print("\n生成完了。実AIテストは run_ai_test.py を参照。")


if __name__ == "__main__":
    main()
