# Context Engineering Lab — Week 2

A Streamlit multi-run goal builder. It uses explicit context construction and persistent JSON state to take a goal through six separate LLM calls: understand, plan, design, refine, validate, and finalize.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set your API key:

   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

State is saved after every successful call in `runs/`. You can pause, add an approved requirement or feedback, restart Streamlit, and resume the saved run from the sidebar. The UI shows the exact context sent for each call, provenance, artifacts, token usage, latency, and cumulative estimated cost.

Run the deterministic checks with:

```bash
pytest
```

`app_*.py` files are retained as Week 1 API exercises.
