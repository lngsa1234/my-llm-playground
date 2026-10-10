# Agent Engineering Peer Learning Labs

A collection of hands-on agent-engineering labs: a single API-call playground (Week 1), a multi-run context-engineering workflow (Week 2), an inspectable Retrieval-Augmented Generation system (Week 3), and a tool-calling/MCP weather assistant (Week 4).

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

Week 2 state is saved after every successful call in `runs/`. Week 3 uses the ten fictional NovaTech markdown files in `knowledge_base/`, OpenAI embeddings, and a FAISS index. The Week 3 UI makes chunks, similarity scores, augmented prompts, answer sources, and benchmark Evidence Recall@K visible.

Run the deterministic checks with:

```bash
pytest
```

`app_*.py` files are retained as Week 1 API exercises.

## Week 4: Weather Assistant

Week 4 is available inside the Streamlit app as **Week 4 · Weather Assistant**.
It lets learners ask live weather questions and inspect the assistant's
requests and returned data. Supporting implementation material lives in
[`weather-agent-lab/`](weather-agent-lab/) and uses the repository's shared
virtual environment and `.env` file.
