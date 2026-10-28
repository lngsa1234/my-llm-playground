# Week 6 · Evals — Concepts: Public Benchmarks

## At a glance

| Learn | Build | Key terms | Watch for |
| --- | --- | --- | --- |
| Use public benchmarks as ideas and comparison points, not as a substitute for product-specific evals | A small benchmark-derived test set adapted to your agent | Benchmark, BFCL, scorer, contamination, golden dataset | A high public score does not guarantee performance on your users' tasks |

Public benchmarks compare systems on shared tasks. Your golden dataset should instead reflect your agent's tools, users, policies, and past failures. Use benchmarks for case ideas, grading patterns, and baseline comparisons—not as proof that your product works.

Samples, a download script, and a BFCL scorer are in the [`benchmark/` folder on GitHub](https://github.com/lngsa1234/my-llm-playground/tree/main/benchmark).

## Useful benchmark families

| Area | Examples | What to borrow |
| --- | --- | --- |
| Tool calling | [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html), [τ-bench](https://github.com/sierra-research/tau-bench), [ToolBench](https://github.com/OpenBMB/ToolBench) | Exact tool and argument checks, no-tool-needed cases, end-state checks |
| General agents | [GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA), [AppWorld](https://github.com/StonyBrookNLP/appworld), [WebArena](https://github.com/web-arena-x/webarena), [SWE-bench](https://github.com/SWE-bench/SWE-bench) | Observable task completion and side-effect checks |
| RAG and retrieval | [HotpotQA](https://hotpotqa.github.io/), [MS MARCO](https://microsoft.github.io/msmarco/), [BEIR](https://github.com/beir-cellar/beir) | Evidence recall, ranking cases, and realistic question phrasing |
| Judge calibration | [MT-Bench human judgments](https://huggingface.co/datasets/lmsys/mt_bench_human_judgments), [JudgeBench](https://github.com/ScalerLab/JudgeBench) | Compare an LLM judge against known human judgments |

## Turn a benchmark case into your own test

1. Choose a task type that resembles your agent.
2. Identify how the original benchmark decides success.
3. Rewrite the task using your own tools, policies, and user language.
4. Add explicit expected tools, forbidden tools, expected state, and success criteria.
5. Run it in your golden dataset and inspect failures.

```json
{
  "id": "notool-01",
  "input": "What does a 40% chance of rain mean?",
  "expected_tools": [],
  "forbidden_tools": ["get_weather"],
  "expected_state": {"events_created": 0}
}
```

Two cautions: popular public tasks may have appeared in model training data, and a strong benchmark score may not transfer to your product. The right question is always: **does the agent work reliably for our users and constraints?**

## References

- [OpenAI API — Working with evals](https://developers.openai.com/api/docs/guides/evals)
- [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html), [τ-bench](https://github.com/sierra-research/tau-bench), and [BEIR](https://github.com/beir-cellar/beir)
- [OpenAI API — Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)
- [HotpotQA](https://hotpotqa.github.io/) and [SWE-bench](https://github.com/SWE-bench/SWE-bench)
- [Hugging Face — RAG evaluation cookbook](https://huggingface.co/learn/cookbook/en/rag_evaluation)
