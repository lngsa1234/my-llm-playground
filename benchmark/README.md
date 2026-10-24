# Benchmarks

Test sets for the circle's labs, in two parts:

```text
benchmark/
├── README.md
├── rag/                         # Week 3 RAG question sets (read by the Streamlit app)
│   ├── questions.json           # NovaTech questions, with expected answers and evidence files
│   └── hotpotqa_mini_questions.json   # HotpotQA subset, built by tools/build_hotpotqa_mini.py
└── public/                      # public agent-evaluation benchmarks (Week 6)
    ├── fetch_benchmarks.py      # downloads benchmarks into public/downloads/ (git-ignored)
    ├── run_bfcl.py              # scores a model on BFCL tool-calling cases
    └── samples/                 # small committed samples, with their licenses
        ├── bfcl/                # 70 cases: simple, multiple, parallel, irrelevance
        └── tau2-bench/          # 10 retail tasks + the retail agent policy
```

The documents the RAG questions are asked about live in [`rag_corpus/`](../rag_corpus/).

---

## `rag/` — Week 3 question sets

- `questions.json` — questions about the ten fictional NovaTech documents in [`rag_corpus/novatech/`](../rag_corpus/novatech/).
- `hotpotqa_mini_questions.json` — 50 HotpotQA development questions plus unanswerable checks, over the articles in [`rag_corpus/hotpotqa_mini/`](../rag_corpus/hotpotqa_mini/). Rebuild both with [`tools/build_hotpotqa_mini.py`](../tools/build_hotpotqa_mini.py).

## `public/` — Public agent-evaluation benchmarks

For what each benchmark tests and how it's graded, see [Public Benchmarks for Agent Evaluation](../knowledge_base/week-06-evals/concepts-benchmarks.md).

### Committed samples

| Sample | Source | License | Contents |
| --- | --- | --- | --- |
| `public/samples/bfcl/` | [BFCL](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard) v4, commit `6ea5797` | Apache-2.0 (copy in folder) | First 20 `simple_python`, 20 `multiple`, 10 `parallel` and 20 `irrelevance` cases, with answer files |
| `public/samples/tau2-bench/` | [τ²-bench](https://github.com/sierra-research/tau2-bench), commit `0c69df4` | MIT (copy in folder) | First 10 retail tasks and the retail policy |

Each BFCL case file has one JSON object per line: the user `question` and the `function` definitions offered to the model. The matching `*_answers.jsonl` file lists the acceptable calls (`""` means an argument may be left out). Irrelevance cases have no answer file: the right behavior is to call nothing.

Each τ²-bench task describes a simulated customer (`user_scenario`) and the actions the agent must end up taking (`evaluation_criteria.actions`), checked against a database. Running τ²-bench for real needs its own simulator; the sample is for reading how end-state checks and policies are written.

### Run a real tool-calling benchmark

```bash
python3 benchmark/public/run_bfcl.py                  # oracle: replays the answers, should score 100%
python3 benchmark/public/run_bfcl.py --model none     # baseline that never calls a tool
export ANTHROPIC_API_KEY=sk-ant-...
python3 benchmark/public/run_bfcl.py --model claude   # a real model (CLAUDE_MODEL to change it)
```

It reports **tool selection** (right function?) and **fully correct** (right function and arguments) per category, the same levels as Step 3 of the [Week 6 eval lab](../agent-eval-lab/README.md). The `none` baseline scores 29%: it passes every irrelevance case and nothing else, which is a good reminder of why a benchmark needs both kinds of case.

The checker is simplified for teaching. For official scores, use the [BFCL harness](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard).

### Download more

```bash
python3 benchmark/public/fetch_benchmarks.py --list               # what's available
python3 benchmark/public/fetch_benchmarks.py bfcl tau2            # full GitHub-hosted sets
python3 benchmark/public/fetch_benchmarks.py hotpotqa frames --limit 100
python3 benchmark/public/fetch_benchmarks.py all
```

Then point the scorer at the full BFCL set:

```bash
python3 benchmark/public/run_bfcl.py --data downloads/bfcl --model claude --limit 30
```

| Name | Benchmark | Notes |
| --- | --- | --- |
| `bfcl` | BFCL tool calling | GitHub; 8 categories including live (user-contributed) cases |
| `tau2` | τ²-bench retail + airline | GitHub; tasks and policies |
| `gaia` | GAIA | Gated: needs `HF_TOKEN` and accepting its terms on Hugging Face. **Do not commit or republish.** |
| `swebench-lite` | SWE-bench Lite | Task list; running it needs Docker |
| `hotpotqa`, `frames`, `nq-open`, `msmarco`, `beir-scifact` | RAG | Hugging Face |
| `mt-bench-judgments`, `judgebench` | Judge calibration | Hugging Face |

Hugging Face datasets are pulled through the Hugging Face dataset viewer API, `--limit` rows at a time (default 50), so you don't download gigabytes by accident. ToolBench, API-Bank, AgentBench, AppWorld, WebArena and OSWorld need their own setup; `--list` prints where to start.

Everything lands in `public/downloads/`, which git ignores. Check each dataset's license before sharing anything derived from it.
