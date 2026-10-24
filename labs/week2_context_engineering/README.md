# Week 2 Lab · Context Engineering

Choose what the model sees on each call, and measure what that choice costs and changes.

Lab guide: [knowledge_base/week-02-context-engineering/lab.md](../../knowledge_base/week-02-context-engineering/lab.md)

## What's here

```text
week2_context_engineering/
├── page.py                 the web page (Demo 1–3)
├── strategy_benchmark.py   Demo 1: five context strategies on the same question
├── goal_workflow.py        Demo 2: a goal built across several calls with saved state
├── goal_replay.py          Demo 3: the same events replayed against several strategies
├── context_builder.py      builds the context for each call within a token budget
├── state_manager.py        saves and loads goal state (in runs/, git-ignored)
├── evaluator.py            checks responses and final outputs
├── llm_client.py           the model call used by Demos 2 and 3
├── longbench_subset.py     optional official LongBench HotpotQA cases (cached in data/, git-ignored)
└── tests/
```

## Run it

From the repo root, after `pip install -r requirements.txt` and setting `OPENAI_API_KEY` in `.env`:

```bash
streamlit run labs/week2_context_engineering/page.py   # this lab on its own
streamlit run app.py                                   # all labs, pick Week 2
```
