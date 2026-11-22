"""
Run all the automated tests and save the results to tests_log.txt.

Run from the backend folder:   python run_tests.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

result = subprocess.run([sys.executable, "-m", "pytest", "-v"], cwd=HERE,
                        capture_output=True, text=True)
report = f"Test run - {datetime.now():%Y-%m-%d %H:%M:%S}\n\n" + result.stdout + result.stderr
print(report)
(HERE / "tests_log.txt").write_text(report, encoding="utf-8")
print(f"Saved to {HERE / 'tests_log.txt'}")
sys.exit(result.returncode)
