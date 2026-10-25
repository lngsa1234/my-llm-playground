# Agent Engineering Peer Learning Labs

Over 8 weeks the circle builds **Mini Muse**, a personal-assistant agent, one component per week ([guide](knowledge_base/mini-muse.md)). Alongside it are hands-on concept labs: a single API-call playground (Week 1), a multi-run context-engineering workflow (Week 2), an inspectable Retrieval-Augmented Generation system (Week 3), a tool-calling/MCP weather assistant (Week 4), a stateful workflow agent (Week 5), agent evaluation with regression testing (Week 6), and a production reliability drill (Week 7).

## Repository layout

```text
app.py                         the full site: every lab in one app (streamlit run app.py)
mini_muse/                     the course project: one file per week, wired together by week 8
labs/                          one self-contained folder per lab
  shared/                      settings panel and model settings shared by every page
  week1_llm_api/               one API call, structured output, command-line exercises
  week2_context_engineering/   context strategies, multi-run goal builder, controlled replay
  week3_rag/                   RAG pipeline, its documents/ and questions/, benchmark scoring
  week4_tool_calling/          weather tools, command-line agent, MCP server and client
  week5_agent_workflow/        stateful workflow agent: state, router, repair budget, bounded loop
  week6_agent_eval/            Muse agent, golden dataset, five evaluation steps, LLM judge
  week7_production/            reliability drill: injected failures, retries, timeouts, validation, fallback
knowledge_base/                the 8-week plan, weekly concepts and lab guides
benchmark/                     public benchmarks: BFCL and τ²-bench samples, downloader, scorer
```

[`mini_muse/`](mini_muse/) is the agent itself: `week1_understand.py` through `week8_assistant.py`, a fake world its tools act on, and sample notes. See its [README](mini_muse/README.md).

Each lab folder holds everything for that week: its logic, data, tests, a README, and a `page.py`. Every lab runs three ways:

- **In the full site** — `streamlit run app.py`, then pick the week in the sidebar.
- **On its own** — `streamlit run labs/<lab>/page.py`, for example `streamlit run labs/week3_rag/page.py`.
- **From the command line**, where the lab has command-line tools — see that lab's README.

- [`knowledge_base/`](knowledge_base/) — the circle's [8-week plan](knowledge_base/plan.md), weekly concepts and lab guides.
- [`benchmark/`](benchmark/) — public agent-evaluation benchmarks (BFCL, τ²-bench and a download script for others).

## Run locally

The [hosted app](https://my-llm-playground-bvapyfhmkp7xn5ji9raank.streamlit.app/) runs on the circle organizer's API key. To use your own key, **fork this repository**, then run your fork locally as below, or deploy it on Streamlit Community Cloud with `OPENAI_API_KEY` in the app's Secrets.

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

Run every lab's tests with:

```bash
pytest
```

## Using the app

Every week's page has the same layout:

- **Left sidebar** — choose the week, or **🧩 Mini Muse · all weeks** for every Mini Muse component in one place (Week 8, the assembled assistant, lives only there).
- **Top of each week page** — switch between **🔬 Concept demo** (the week's lab) and **🧩 Build Mini Muse** (the same idea, added to Mini Muse).
- **Main area** — the week title, a one-line description, a "How this lab works" explainer, then inputs, a run button and results with the same token, latency and cost metrics.
- **Right panel** — one box with two sections stacked in a single column:
  - **⚙️ Model settings** — model, max output tokens and $/1M token prices (plus the embedding model in Week 3). The values are shared across weeks, so set them once. The default is `gpt-5.4-mini`, with matching default prices; change both together if you switch models.
  - **🧪 Lab parameters** — the settings specific to that week, such as output format (Week 1), the demo and its dataset or strategies (Week 2), chunk size and Top-K (Week 3), max tool-call rounds (Week 4), steps, repair budget and router (Week 5), the evaluation step, agent version, judge and release gates (Week 6), or failure rates and the hardened policy (Week 7).

To add a lab: create `labs/weekN_topic/` with its logic, a README, `tests/`, and a `page.py` whose `render()` calls `page_layout()`, `model_settings()` and `lab_parameters()` from `labs/shared/ui.py` (copy the first lines and the `__main__` block of an existing `page.py` so it also runs alone). Then register it in `PAGES` in `app.py`.
