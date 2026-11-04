"""Record when each knowledge-base page last changed, for deployments without git history.

Writes knowledge_base/last-updated.json, mapping each page's path (relative to
knowledge_base/) to the date of the last commit that changed it. The app reads
git history directly when it has it, and falls back to this file otherwise.

Run from the repo root (needs full git history): python scripts/update_kb_dates.py
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_BASE = ROOT / "knowledge_base"
DATES_FILE = KNOWLEDGE_BASE / "last-updated.json"


def main() -> None:
    dates = {}
    for path in sorted(KNOWLEDGE_BASE.rglob("*.md")):
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        if out.stdout.strip():
            dates[path.relative_to(KNOWLEDGE_BASE).as_posix()] = out.stdout.strip()
    DATES_FILE.write_text(json.dumps(dates, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(dates)} dates to {DATES_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
