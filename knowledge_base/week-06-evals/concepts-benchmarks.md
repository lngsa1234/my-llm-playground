# Week 6 · Evals — Concepts: Public Benchmarks

## At a glance

| Learn | Build | Key terms | Watch for |
| --- | --- | --- | --- |
| Use public benchmarks as ideas and comparison points, not as a substitute for product-specific evals | A small benchmark-derived test set adapted to your agent | Benchmark, BFCL, scorer, contamination, golden dataset | A high public score does not guarantee performance on your users' tasks |

There is no single "standard" golden dataset. A golden dataset is built around **your** agent: its tools, users and failure modes. Public benchmarks do something different: they compare models on shared tasks.

Samples, a download script and a BFCL scorer are in [`benchmark/`](../../benchmark/).

Use them for two things:

1. **Ideas and formats** for your own test cases (what a "no tool needed" case looks like, how to check end state, how to write an exact answer).
2. **Starting cases** you rewrite for your own agent and add to your golden dataset.

> **Two cautions.** A high benchmark score doesn't mean a model will do well on your agent's tasks. And popular benchmarks may have leaked into model training data, which inflates scores.

---

## Tool calling

Closest to **Step 2 (task success)** and **Step 3 (tool evaluation)** of the [evaluation lab](../../labs/week6_agent_eval/README.md).

| Benchmark | What it tests | How it's graded | Borrow for your golden set |
| --- | --- | --- | --- |
| [BFCL — Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) ([code & data](https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard)) | Picking the right function and arguments: single, multiple, parallel calls, and cases where **no** function should be called | Checks the call's structure and arguments against expected values, plus executing some calls | "Irrelevance" cases → tests that your agent *doesn't* call a tool |
| [τ-bench](https://github.com/sierra-research/tau-bench) / [τ²-bench](https://github.com/sierra-research/tau2-bench) | Multi-turn customer service (retail, airline, telecom) where the agent must use tools **and** follow a written policy | Compares the final database state with the expected state; runs each task several times (pass^k) | End-state checks (like `expected_state` in our lab) and policy cases ("must not refund after 30 days") |
| [ToolBench](https://github.com/OpenBMB/ToolBench) | Choosing and chaining calls across thousands of real REST APIs | Pass rate plus model-graded comparison | Multi-step tool chains |
| [API-Bank](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank) | Planning, retrieving and calling APIs in dialogue | Exact match on calls and responses | Dialogue-style tool cases |

## General agents

| Benchmark | What it tests | How it's graded | Borrow for your golden set |
| --- | --- | --- | --- |
| [GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA) | Real-world assistant questions needing web search, files and multi-step reasoning | One exact short answer per question | Exact-answer cases that are easy to grade automatically |
| [AgentBench](https://github.com/THUDM/AgentBench) | Agents in 8 environments: OS shell, database, knowledge graph, games, web | Task success per environment | Environment-specific success criteria |
| [AppWorld](https://github.com/StonyBrookNLP/appworld) | Everyday tasks across simulated apps (email, calendar, payments, notes) | Unit tests on the final app state, including checking for unwanted side effects | Closest to a personal assistant like Muse: side-effect checks |
| [WebArena](https://github.com/web-arena-x/webarena) | Completing tasks on realistic self-hosted websites (shopping, forums, GitLab) | Checks the resulting page or data state | Browser-agent tasks |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | Operating real desktop apps on Ubuntu, Windows, macOS | Scripts check the computer's final state | Computer-use tasks |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) | Fixing real GitHub issues in Python repos | The repo's own tests must pass after the fix | Coding agents (e.g. the AI Software Engineering Team project) |

## RAG and retrieval

For the [Week 3 RAG lab](../week-03-rag/lab.md).

| Benchmark | What it tests | Borrow for your golden set |
| --- | --- | --- |
| [HotpotQA](https://hotpotqa.github.io/) ([code](https://github.com/hotpotqa/hotpot)) | Multi-hop questions with labeled supporting sentences | Evidence recall: each question lists the facts it needs |
| [Natural Questions](https://ai.google.com/research/NaturalQuestions) | Real Google search questions answered from Wikipedia | Realistic phrasing of user questions |
| [MS MARCO](https://microsoft.github.io/msmarco/) | Passage ranking from real Bing queries | Retrieval ranking cases |
| [BEIR](https://github.com/beir-cellar/beir) | Retrieval across 18 domains (science, finance, biomedical…) | Testing retrieval outside your own domain |
| [FRAMES](https://huggingface.co/datasets/google/frames-benchmark) | Multi-hop questions needing several Wikipedia articles, with sources | End-to-end RAG: retrieval + reasoning + answer |

## LLM-as-a-judge calibration

For **Step 4** of the [evaluation lab](../../labs/week6_agent_eval/README.md): check that a judge agrees with humans before trusting it.

| Benchmark | What it gives you |
| --- | --- |
| [MT-Bench human judgments](https://huggingface.co/datasets/lmsys/mt_bench_human_judgments) | Thousands of human votes on which of two answers is better, to compare against your judge |
| [JudgeBench](https://github.com/ScalerLab/JudgeBench) | Hard answer pairs with known correct choices, to test whether a judge picks correctness over style |

---

## Exercise: from benchmark to golden case

1. Pick the benchmark closest to your project (e.g. τ-bench for a customer-support agent, AppWorld for a personal assistant, HotpotQA for RAG).
2. Read 5 of its tasks and note **how each one is graded**.
3. Rewrite each task for your own agent's tools and users.
4. Add them to your golden dataset with `expected_tools`, `forbidden_tools` and `expected_state`, then run `python3 labs/week6_agent_eval/lab/step1_golden.py` to check coverage.

Example — a BFCL-style "no tool needed" case rewritten for Muse:

```json
{"id": "notool-01", "category": "no_tool", "difficulty": "easy",
 "input": "What does it mean when a forecast says 40% chance of rain?",
 "expected": {"must_contain": [], "must_not_contain": ["°F"],
   "expected_tools": [], "expected_args": {},
   "forbidden_tools": ["get_weather", "send_email", "create_event"],
   "expected_state": {"events_created": 0, "emails_sent": 0}},
 "notes": "Conceptual question: answering should not trigger a weather lookup."}
```
