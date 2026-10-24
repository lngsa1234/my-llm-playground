"""
Download public agent-evaluation benchmarks (or samples of them) to
benchmark/public/downloads/. That folder is git-ignored: datasets have
their own licenses and some ask not to be republished.

Standard library only. Run from the repo root or this folder:

    python3 benchmark/public/fetch_benchmarks.py --list
    python3 benchmark/public/fetch_benchmarks.py bfcl tau2 hotpotqa
    python3 benchmark/public/fetch_benchmarks.py all --limit 100

Hugging Face datasets are fetched through the Hugging Face dataset viewer
API, --limit rows at a time (default 50). Gated datasets (GAIA) need a
Hugging Face token with access approved: export HF_TOKEN=hf_...
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "downloads")

BFCL_RAW = ("https://raw.githubusercontent.com/ShishirPatil/gorilla/main/"
            "berkeley-function-call-leaderboard/bfcl_eval/data/")
TAU2_RAW = "https://raw.githubusercontent.com/sierra-research/tau2-bench/main/data/tau2/domains/"

BFCL_FILES = ["simple_python", "multiple", "parallel", "parallel_multiple",
              "irrelevance", "live_simple", "live_multiple", "live_irrelevance"]

# name: (kind, source, details)
BENCHMARKS = {
    # --- Tool calling ---------------------------------------------------
    "bfcl": ("github", "BFCL (Berkeley Function Calling Leaderboard), Apache-2.0",
             [(f"{BFCL_RAW}BFCL_v4_{f}.json", f"{f}.jsonl") for f in BFCL_FILES]
             + [(f"{BFCL_RAW}possible_answer/BFCL_v4_{f}.json", f"{f}_answers.jsonl")
                for f in BFCL_FILES if "irrelevance" not in f]),
    "tau2": ("github", "tau2-bench retail + airline tasks and policies, MIT",
             [(f"{TAU2_RAW}{d}/{f}", f"{d}_{f}") for d in ("retail", "airline")
              for f in ("tasks.json", "policy.md")]),
    # --- General agents -------------------------------------------------
    "gaia": ("hf", "gaia-benchmark/GAIA  (gated: needs HF_TOKEN and accepted terms; do not republish)",
             {"prefer_config": "2023_all", "prefer_split": "validation"}),
    "swebench-lite": ("hf", "princeton-nlp/SWE-bench_Lite  (task list only; running needs Docker)",
                      {"prefer_split": "test"}),
    # --- RAG ------------------------------------------------------------
    "hotpotqa": ("hf", "hotpotqa/hotpot_qa", {"prefer_config": "distractor", "prefer_split": "validation"}),
    "frames": ("hf", "google/frames-benchmark", {"prefer_split": "test"}),
    "nq-open": ("hf", "google-research-datasets/nq_open", {"prefer_split": "validation"}),
    "msmarco": ("hf", "microsoft/ms_marco", {"prefer_config": "v2.1", "prefer_split": "validation"}),
    "beir-scifact": ("hf", "BeIR/scifact", {"prefer_config": "queries"}),
    # --- Judge calibration ----------------------------------------------
    "mt-bench-judgments": ("hf", "lmsys/mt_bench_human_judgments", {"prefer_split": "human"}),
    "judgebench": ("hf", "ScalerLab/JudgeBench", {"prefer_split": "gpt"}),
}

MANUAL = {
    "ToolBench": "https://github.com/OpenBMB/ToolBench  (data download link in its README)",
    "API-Bank": "https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank",
    "AgentBench": "https://github.com/THUDM/AgentBench  (runs in Docker)",
    "AppWorld": "https://github.com/StonyBrookNLP/appworld  (pip install appworld; appworld download data)",
    "WebArena": "https://github.com/web-arena-x/webarena  (self-hosted websites in Docker)",
    "OSWorld": "https://github.com/xlang-ai/OSWorld  (needs a virtual machine)",
}

HF_API = "https://datasets-server.huggingface.co"


def _get(url, as_json=True):
    headers = {"User-Agent": "agent-eval-circle/1.0"}
    if "huggingface" in url and os.environ.get("HF_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['HF_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        data = r.read()
    return json.loads(data) if as_json else data


def fetch_github(name, files, limit):
    folder = os.path.join(OUT, name)
    os.makedirs(folder, exist_ok=True)
    for url, fname in files:
        data = _get(url, as_json=False)
        if limit and fname.endswith(".jsonl"):        # BFCL: one JSON object per line
            data = b"\n".join(data.splitlines()[:limit]) + b"\n"
        with open(os.path.join(folder, fname), "wb") as f:
            f.write(data)
    return f"{len(files)} files"


def fetch_hf(name, dataset, opts, limit):
    q = urllib.parse.quote
    splits = _get(f"{HF_API}/splits?dataset={q(dataset)}")["splits"]
    configs = [s for s in splits if s["config"] == opts.get("prefer_config")] or splits
    chosen = next((s for s in configs if s["split"] == opts.get("prefer_split")), configs[0])
    config, split = chosen["config"], chosen["split"]

    rows, offset = [], 0
    while len(rows) < limit:
        n = min(100, limit - len(rows))
        page = _get(f"{HF_API}/rows?dataset={q(dataset)}&config={q(config)}"
                    f"&split={q(split)}&offset={offset}&length={n}")
        batch = [r["row"] for r in page.get("rows", [])]
        if not batch:
            break
        rows += batch
        offset += len(batch)

    folder = os.path.join(OUT, name)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{config}_{split}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return f"{len(rows)} rows ({config}/{split})"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="benchmarks to fetch, or 'all'")
    ap.add_argument("--limit", type=int, default=50, help="rows per dataset (default 50; 0 = full BFCL files)")
    ap.add_argument("--list", action="store_true", help="list available benchmarks")
    args = ap.parse_args()

    if args.list or not args.names:
        print("Downloadable:")
        for k, (kind, src, _) in BENCHMARKS.items():
            print(f"  {k:<20} {src if kind == 'github' else 'huggingface: ' + src}")
        print("\nSet up from their own repos:")
        for k, v in MANUAL.items():
            print(f"  {k:<20} {v}")
        return

    names = list(BENCHMARKS) if args.names == ["all"] else args.names
    unknown = [n for n in names if n not in BENCHMARKS]
    if unknown:
        sys.exit(f"Unknown benchmark(s): {', '.join(unknown)}. Run with --list.")

    print(f"Saving to {os.path.relpath(OUT)}/\n")
    failures = 0
    for name in names:
        kind, src, details = BENCHMARKS[name]
        try:
            if kind == "github":
                result = fetch_github(name, details, args.limit if args.limit else None)
            else:
                result = fetch_hf(name, src.split()[0], details, args.limit or 50)
            print(f"  ✓ {name:<20} {result}")
        except urllib.error.HTTPError as e:
            failures += 1
            hint = " (gated: set HF_TOKEN and accept the dataset's terms on huggingface.co)" if e.code in (401, 403) else ""
            print(f"  ✗ {name:<20} HTTP {e.code}{hint}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  ✗ {name:<20} {type(e).__name__}: {e}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
