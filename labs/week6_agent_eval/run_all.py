"""Run the whole lab end to end:  python3 run_all.py  (from any folder)"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ["lab/step1_golden.py"],
    ["lab/step2_task_success.py", "v1"],
    ["lab/step2_task_success.py", "v2"],
    ["lab/step3_tool_eval.py", "v2"],
    ["lab/step4_llm_judge.py", "v2"],
    ["lab/step5_regression.py", "--baseline", "v1"],
    ["lab/step5_regression.py", "v2"],
]

for step in STEPS:
    print(f"\n\n>>> python {' '.join(step)}")
    code = subprocess.call([sys.executable, *step], cwd=HERE)
    if code and "step5" not in step[0]:
        sys.exit(code)
print("\n\nDone. The regression gate returning 'BLOCK RELEASE' for v2 is the expected result.")
