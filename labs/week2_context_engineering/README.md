# Week 2 Lab · Context Engineering

The model only knows what you put in its context. The web page shows one demo: pick a context strategy, see which messages it keeps, then ask, or compare all five strategies on the same question.

Lab guide: [knowledge_base/week-02-context-engineering/lab.md](../../knowledge_base/week-02-context-engineering/lab.md)

## What's here

```text
week2_context_engineering/
├── page.py                 the web page: context strategies on one question (Demo 1, redesigned)
├── strategy_benchmark.py   Demo 1: five context strategies on the same question
├── goal_workflow.py        Demo 2 (code only): a goal built across several calls with saved state
├── goal_replay.py          Demo 3 (code only): the same events replayed against several strategies
├── context_builder.py      builds the context for each call within a token budget
├── state_manager.py        saves and loads goal state (in runs/, git-ignored)
├── evaluator.py            checks responses and final outputs
├── llm_client.py           the model call used by Demos 2 and 3
├── longbench_subset.py     optional official LongBench HotpotQA cases (code only; cached in data/, git-ignored)
└── tests/
```

## Run it

From the repo root, after `pip install -r requirements.txt` and setting `OPENAI_API_KEY` in `.env`:

```bash
streamlit run labs/week2_context_engineering/page.py   # this lab on its own
streamlit run app.py                                   # all labs, pick Week 2
```
