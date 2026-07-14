# -*- coding: utf-8 -*-
"""ダミーインプット一式の生成＋検証のオーケストレーター。

usage: python generate_all.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

STEPS = [
    ("財務モデルExcel（2ケース）", "generate_model.py"),
    ("DDレポートPDF（4種）", "generate_pdfs.py"),
    ("mockフィクスチャ＋GROUND_TRUTH.md", "generate_fixtures.py"),
    ("整合チェック", "validate.py"),
]


def main():
    for label, script in STEPS:
        print(f"=== {label} ({script}) ===")
        result = subprocess.run([sys.executable, str(HERE / script)], cwd=HERE)
        if result.returncode != 0:
            print(f"FAILED: {script}")
            sys.exit(result.returncode)
        print()


if __name__ == "__main__":
    main()
