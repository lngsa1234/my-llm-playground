# Agent Engineering Peer Learning Labs

A collection of hands-on agent-engineering labs: a single API-call playground (Week 1), a multi-run context-engineering workflow (Week 2), an inspectable Retrieval-Augmented Generation system (Week 3), and a tool-calling/MCP weather assistant (Week 4).

## Repository layout

```text
app.py                  Streamlit entry point: navigation only
ui/                     front end, one page per week
  components.py         shared sidebar panels and widgets used by every page
  week1.py … week4.py
core/                   back-end logic per week (plain Python, no Streamlit)
  common.py             ModelSettings + defaults shared by all weeks
  week1/playground.py   one API call, structured output
  week2/                context strategies, goal workflow, state, controlled replay
  week3/                RAG pipeline (rag.py) and benchmark scoring (evaluation.py)
  week4/weather.py      weather tools, tool-calling loop, live benchmark
tests/                  pytest suite for core/
exercises/week1/        standalone Week 1 API scripts
weather-agent-lab/      Week 4 command-line tool-calling and MCP demos
agent-eval-lab/         Week 6 agent evaluation lab
```

- [`knowledge_base/`](knowledge_base/) — the circle's weekly plan, knowledge bases and lab guides.
- [`rag_corpus/`](rag_corpus/) — the documents the Week 3 RAG app searches: ten NovaTech policies and the HotpotQA mini articles.
- [`agent-eval-lab/`](agent-eval-lab/) — the Week 6 agent evaluation lab (runs offline, standard library only).
- [`benchmark/`](benchmark/) — the Week 3 RAG question sets in `benchmark/rag/`, and public agent-evaluation benchmarks (BFCL, τ²-bench and a download script for others) in `benchmark/public/`.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file and set your API key:

   ```bash
   cp .env.example .env
   # Edit .env and set OPENAI_API_KEY="your-api-key"
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

Week 2 state is saved after every successful call in `runs/`. Week 3 uses the ten fictional NovaTech markdown files in `rag_corpus/novatech/`, OpenAI embeddings, and a FAISS index. The Week 3 UI makes chunks, similarity scores, augmented prompts, answer sources, and benchmark Evidence Recall@K visible.

Run the deterministic checks with:

```bash
pytest
```

## Using the app

Every week's page has the same layout:

- **Sidebar · ⚙️ Model settings** — model, max output tokens and $/1M token prices (plus the embedding model in Week 3). The values are shared across weeks, so set them once. The default is `gpt-5.4-mini`, with matching default prices; change both together if you switch models.
- **Sidebar · 🧪 Lab parameters** — the knobs specific to that week, such as output format (Week 1), chunk size and Top-K (Week 3), or max tool-call rounds (Week 4). In Week 2, each demo tab has its own parameter panel at the top.
- **Main area** — a one-line description, a "How this lab works" explainer, then inputs, a run button and results with the same token, latency and cost metrics.

To add a week: put its logic in `core/weekN/`, add `ui/weekN.py` with a `render()` function that calls `model_settings()` and `lab_parameters()` from `ui/components.py`, and register it in `PAGES` in `app.py`.

The standalone Week 1 API scripts are in [`exercises/week1/`](exercises/week1/).

## Week 4: Weather Assistant

Week 4 is available inside the Streamlit app as **Week 4 · Weather Assistant**.
It lets learners ask live weather questions and inspect the assistant's
requests and returned data. Supporting implementation material lives in
[`weather-agent-lab/`](weather-agent-lab/) and uses the repository's shared
virtual environment and `.env` file.
