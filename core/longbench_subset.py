"""On-demand loader for a small, attributable official LongBench subset."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ARCHIVE_URL = "https://huggingface.co/datasets/THUDM/LongBench/resolve/main/data.zip"
CACHE_PATH = Path("data/longbench_hotpotqa_subset.json")
MEMBER = "data/hotpotqa.jsonl"


def load_cached_cases() -> list[dict] | None:
    if not CACHE_PATH.exists():
        return None
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))["cases"]


def download_subset(case_count: int = 3) -> list[dict]:
    """Download the official archive once, then persist only the first few HotpotQA cases."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    archive_path = CACHE_PATH.parent / "_longbench_official.zip"
    try:
        urlretrieve(ARCHIVE_URL, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open(MEMBER) as handle:
                cases = [json.loads(handle.readline()) for _ in range(case_count)]
        payload = {
            "source": "THUDM/LongBench, HotpotQA test split",
            "source_url": "https://github.com/THUDM/LongBench",
            "cases": cases,
        }
        CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return cases
    finally:
        if archive_path.exists():
            archive_path.unlink()
