# Week 1 Lab · Single API Call

Make one LLM API call and see everything about it: the response, token use, latency and cost, with optional structured (JSON) output.

Lab guide: [knowledge_base/week-01-llm-fundamentals/lab.md](../../knowledge_base/week-01-llm-fundamentals/lab.md)

## What's here

```text
week1_llm_api/
├── page.py          the web page
├── playground.py    one API call + structured output (no Streamlit)
├── exercises/       standalone scripts, one per lab experiment
└── tests/
```

## Run it

From the repo root, after `pip install -r requirements.txt` and setting `OPENAI_API_KEY` in `.env`:

```bash
streamlit run labs/week1_llm_api/page.py      # this lab on its own
streamlit run app.py                          # all labs, pick Week 1
python3 labs/week1_llm_api/exercises/app_2.py # one experiment from the command line
```

`exercises/app.old.py` is an earlier single-file version of the playground (`streamlit run labs/week1_llm_api/exercises/app.old.py`).
