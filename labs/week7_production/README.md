# Week 7 · Production Reliability

A reliability drill. One small production task, classifying a support ticket into JSON, is sent many times while failures are injected. The same requests run under a **naive** and a **hardened** policy, so you can see what each safeguard buys and what it costs.

| Injected failure | What a naive caller sees | What the hardened policy does |
| --- | --- | --- |
| Rate limit (429) | an error | waits (exponential backoff with jitter), then retries |
| Server error (503) | an error | retries |
| Hang | waits 60 s for the server to give up | gives up at its own timeout, then retries |
| Slow answer (simulated only) | waits | cuts it off at the timeout, then retries |
| Broken JSON | **reports success** and passes it on | validates against a schema and retries |

After the retries, an optional **fallback model** gets one try.

## Run

```bash
streamlit run labs/week7_production/page.py   # this page alone (or pick Week 7 in app.py)
pytest labs/week7_production                  # offline
```

- **Simulated mode** is free and instant. Latency is simulated rather than waited for, so 500 requests take a second. The same seed gives the same faults, so you can change one knob and compare fairly.
- **Live mode** makes real calls with the SDK's built-in retries turned off (`max_retries=0`), so every retry you see is the policy's. Faults are still injected on top: 429, 503 and hangs never reach the API, and broken JSON is made by cutting the real answer in half.

## Things to try

- Set everything to 0% except **Broken JSON**. The naive policy "succeeds" on every request, but some of those answers are unusable. This is the most dangerous failure: nothing alerts.
- Raise **Hang** to 20% and compare p95 latency. A missing timeout makes the slowest requests very slow.
- Set **Retries** to 0, then 1, then 3. Watch success rate and cost rise together: retries are paid attempts.
- Set **Rate limit** to 40% and the backoff base to 0. Retrying instantly into a rate limit mostly hits it again.

## Code

`reliability.py`:

- `Faults` and `Policy` are the knobs.
- `SimulatedBackend` and `LiveBackend` make one attempt each.
- `run_request()` applies the policy: retries, backoff, timeout, validation, fallback.
- `run_batch()` and `summarize()` produce the comparison.

The page's **🧩 Build Mini Muse** part applies the same ideas inside Mini Muse's agent, tracing every model and tool call.
