# Week 7 · Production AI — Concepts: Agent Reliability

## At a glance

| Learn | Build | Key terms | Watch for |
| --- | --- | --- | --- |
| Keep an agent working, honest and affordable when models, tools and users misbehave | Tracing plus at least three failure-handling mechanisms (e.g. timeout, retry, max loop count) | Trace, span, p95 latency, timeout, backoff, jitter, idempotency, fallback, validation, loop budget, circuit breaker, human approval | The most dangerous failure is the silent one: a request that "succeeds" with a broken or invented answer and triggers no alert |

**Question of the week:** what happens when the demo meets real users?

In a demo, you send one request, the model answers, and the tool works. In production, you send thousands of requests a day, and some fraction of them will hit a rate limit, a slow server, a broken tool, a malformed JSON answer, or an agent that keeps looping. Reliability engineering is the work of deciding, ahead of time, what the system does in each of those cases.

---

## 1. Why the demo breaks in production

| In the demo | In production |
| --- | --- |
| One user, one request at a time | Many concurrent requests, shared rate limits |
| The API is up | The API returns 429 and 503, and sometimes hangs |
| The tool returns clean data | The tool times out, returns an error, or returns something unexpected |
| The model returns valid JSON | Occasionally it doesn't, and nothing crashes until a later step |
| The agent finishes in 3 steps | Sometimes it repeats the same tool call until you stop it |
| You read every answer | Nobody reads most answers, so a bad one goes unnoticed |
| Cost doesn't matter | Every retry, fallback and extra loop step is paid for |

A useful way to think about it: a component that works **99%** of the time looks perfect in a demo. An agent that makes **10** such calls per task fails roughly **1 task in 10** (0.99¹⁰ ≈ 0.90). Agents multiply small failure rates, because one task is many calls.

---

## 2. Reliability is a layer, not a feature

Rather than scattering `try/except` across the code, put every model call and every tool call through one **runtime layer**. That layer is where tracing, timeouts, retries, validation and fallbacks live.

```txt
                    Agent loop (Week 5)
                           │
                           ▼
        ┌────────────── RUNTIME LAYER ──────────────┐
        │  trace  →  timeout  →  retry/backoff  →   │
        │  validate output  →  fallback  →  budget  │
        └───────────────┬───────────────┬───────────┘
                        ▼               ▼
                       LLM            Tools / APIs
```

This is exactly what Mini Muse's Week 7 `Runtime` does: the agent asks the runtime to call the model or a tool, and the runtime decides how to survive failures.

What "reliable" means should be written down as targets, not feelings. For example:

```txt
Task success rate        ≥ 95%   (measured by the Week 6 eval suite)
p95 end-to-end latency   ≤ 8 s
Cost per task            ≤ $0.02
Silent failures          0 known (every failure is either retried, surfaced or alerted)
```

These targets are sometimes called **SLOs** (service-level objectives). They make trade-offs discussable: a fourth retry might raise success rate but break the latency and cost targets.

---

## 3. Observability: you can't fix what you can't see

**Observability** means being able to answer "what happened in this request, and why?" after the fact. It has three parts:

| Signal | What it is | Example |
| --- | --- | --- |
| **Logs** | Individual events, with detail | `tool get_weather failed: timeout after 5s` |
| **Metrics** | Numbers aggregated over time | success rate, p95 latency, cost per hour, retries per request |
| **Traces** | The full tree of steps for one request | user request → LLM call → tool call → retry → LLM call → answer |

### Traces and spans

A **trace** is one request's story. Each step inside it (a model call, a tool call, a retry) is a **span** with a start time, duration, inputs, outputs and status.

```txt
trace_id: 7f3a…   "Will it rain tomorrow? If so, remind me at 8."
│
├─ span: llm.call            1.2 s   in 812 tok / out 64 tok   ok
├─ span: tool.get_weather    5.0 s                             TIMEOUT
├─ span: tool.get_weather    0.4 s   (retry 1)                 ok
├─ span: llm.call            0.9 s   in 940 tok / out 41 tok   ok
├─ span: tool.create_reminder 0.2 s                            ok
└─ span: llm.call            0.7 s   in 1010 tok / out 38 tok  ok
                                                    total 8.4 s, 3 LLM calls, 1 retry
```

Without the trace, you only know "the request took 8.4 seconds." With it, you know a weather timeout cost 5 seconds and one retry fixed it.

### What to record on every call

```json
{
  "trace_id": "7f3a…",
  "span": "tool.get_weather",
  "attempt": 2,
  "model": null,
  "args": {"city": "Detroit"},
  "status": "ok",
  "error_type": null,
  "latency_ms": 412,
  "input_tokens": null,
  "output_tokens": null,
  "cost_usd": 0.0
}
```

For LLM spans, record the model, input and output tokens, and estimated cost:

```txt
cost = input_tokens × input_price + output_tokens × output_price
```

### Metrics worth watching

| Metric | Why it matters |
| --- | --- |
| Success rate (task-level, not just HTTP) | The headline number |
| p50 and **p95** latency | Averages hide the slow tail; users feel p95 |
| Tokens and cost per task | Agents can quietly get expensive |
| Retries per request, fallback rate | Rising numbers warn that a dependency is degrading |
| Validation failure rate | Catches the model drifting from your schema |
| Steps per task, loop-limit hits | Catches agents that wander |

**Privacy note:** traces often contain user input. Redact personal data or store only what you need, and set a retention period.

---

## 4. A map of failures

Not all failures should be handled the same way. The first question is always: **will trying again help?**

| Failure | Example | Kind | Typical handling |
| --- | --- | --- | --- |
| Rate limit | HTTP 429 | Transient | Back off (respect `Retry-After`), then retry |
| Server error | HTTP 500/503, overloaded | Transient | Retry with backoff; fallback model if it persists |
| Hang / slow response | No answer for 60 s | Transient | Timeout, then retry |
| Malformed output | Broken or incomplete JSON, wrong fields | Often transient | Validate, then retry (optionally with the error in the prompt) |
| Tool error | Weather API down | Transient or permanent | Retry a little; then tell the model the tool is unavailable |
| Bad request | 400, invalid arguments, auth failure | **Permanent** | Don't retry; fix the input or surface the error |
| Context overflow | Prompt exceeds the context window | Permanent for this input | Trim or summarize context (Week 2), don't retry as-is |
| Runaway loop | Same tool call over and over | Agent logic | Loop budget, repeated-action detection |
| Valid but wrong | Plausible answer, wrong facts or action | **Silent** | Evals (Week 6), grounding, validation, human review |

The last row is why reliability and evals belong together. Retries fix failures that announce themselves; only evaluation catches the ones that don't.

---

## 5. Timeouts

A missing timeout is the most common production bug in LLM apps. If a server hangs and your client waits forever (or for the library default, which can be minutes), one bad dependency freezes the whole agent.

Use timeouts at three levels:

```txt
Per call      each LLM or tool call       e.g. 10 s
Per tool      tuned to that tool          e.g. weather 3 s, search 8 s
End-to-end    the whole task (deadline)   e.g. 30 s, then stop and answer honestly
```

Setting the value: look at the latency distribution and set the timeout a bit above the normal p99. Too short and you kill healthy slow requests (and pay to redo them); too long and users wait on requests that will never finish.

An end-to-end **deadline** also limits retries: if only 2 seconds remain, don't start an 8-second retry.

---

## 6. Retries with exponential backoff and jitter

Retrying fixes most transient failures. Retrying badly makes things worse.

**Exponential backoff:** wait longer after each failure.

```txt
wait = base × 2^attempt          base = 0.5 s → 0.5 s, 1 s, 2 s, 4 s …
```

**Jitter:** add randomness so many clients don't retry at the same instant.

```txt
wait = random(0, base × 2^attempt)     ("full jitter")
```

Without jitter, a rate-limited service gets hit by a synchronized wave of retries and stays overloaded. If the server sends a `Retry-After` header, use it.

### Rules for retrying safely

1. **Retry only transient errors** (429, 5xx, timeouts, malformed output). Never retry a 400 or an auth error unchanged.
2. **Cap the attempts** (often 2–3). Every retry is a paid call and adds latency.
3. **Only retry what is safe to repeat.** Reading weather twice is harmless. Charging a card or sending an email twice is not. For side-effecting tools, use an **idempotency key**: a unique ID per intended action, so the second attempt is recognized as a duplicate.
4. **Don't stack retries.** If the SDK retries 3 times and your code retries 3 times, one request can become 16 attempts. Turn one layer off (the Week 7 lab sets the SDK to `max_retries=0` so every retry you see is the policy's).
5. **Watch the retry rate.** A rising rate means a dependency is degrading, even if success rate still looks fine.

---

## 7. Output validation: catching the silent failure

When the model's output feeds code (a JSON object, a tool call, a database write), **validate it before using it.**

```txt
LLM output
    ↓
Parse JSON ──── fails ───→ retry (optionally: "Your last answer was invalid: <error>")
    ↓
Validate schema (types, required fields, allowed values)
    ↓
Validate business rules (date in the future? amount within limit?)
    ↓
Use it
```

In the Week 7 lab, the naive policy reports success on broken JSON and passes it downstream, so nothing alerts. The hardened policy validates against a schema (a Pydantic model) and retries. That single check turns a silent failure into a handled one.

Helpful layers:

- **Structured outputs / JSON mode** (Week 1) make malformed output much rarer but don't remove the need to check business rules.
- **Schema validation** catches wrong types, missing fields and values outside an allowed set.
- **Semantic checks** catch "valid but wrong" cases you can express as code, e.g. a reminder time that is in the past.

---

## 8. Fallbacks and graceful degradation

When retries are exhausted, the system still has to do something. Options, roughly from best to worst:

| Fallback | Example | Trade-off |
| --- | --- | --- |
| Fallback model | Primary model overloaded → smaller or different-provider model | May be lower quality; must be tested with your prompts and evals |
| Cached or last-known answer | Serve yesterday's forecast with its timestamp | Possibly stale; say so |
| Degraded feature | Answer without the weather, but complete the rest | Partial result |
| Honest failure | "I couldn't reach the weather service, please try again" | Not helpful, but truthful |
| **Never:** invented answer | The model guesses a temperature | Looks like success; destroys trust |

**Key principle:** a fallback is a different system. Run your Week 6 eval suite against it too, or you will find out in production that it handles your prompts differently.

---

## 9. Tool failure inside the agent loop

In an agent, a tool failure is also information for the model. Return it as an observation rather than crashing the loop:

```json
{"tool": "get_weather", "status": "error",
 "error": "Weather service unavailable after 2 retries. Do not guess the weather."}
```

Good tool error messages:

- say what failed and whether retrying might help,
- tell the model what it may do instead (ask the user, skip that part, answer without it),
- never contain secrets or stack traces.

Then check the behavior in evals: when `get_weather` is down, does the agent admit it, or does it invent a temperature? This is one of the Mini Muse Week 7 exercises.

---

## 10. Loop control: making sure the agent stops

Week 5 introduced the termination condition. In production you also need **budgets**, because the model may never decide it is done.

```txt
max_steps            e.g. 8 loop iterations
max_tool_calls       e.g. 10 per task
token / cost budget  e.g. 20k tokens or $0.05 per task
wall-clock deadline  e.g. 30 s
repeat detection     same tool + same arguments 3 times → stop
```

When a budget is hit, stop **gracefully**: return the best partial answer and say what wasn't finished, and log the event so you can see which tasks hit limits. A spike in loop-limit hits after a prompt change is a regression worth investigating.

---

## 11. Rate limits, concurrency and circuit breakers

Rate limits are shared across all your users. Handling 429s one request at a time isn't enough at scale.

- **Client-side limiting:** cap concurrent requests and tokens per minute below the provider's limit, and queue the rest.
- **Prioritize:** interactive requests first, background jobs later.
- **Circuit breaker:** if a dependency has failed, say, 20 times in the last minute, stop calling it for a short period and go straight to the fallback. This avoids paying for calls that will fail and gives the dependency time to recover.

```txt
CLOSED ── too many failures ──→ OPEN (skip calls, use fallback)
   ↑                                  │
   └── test call succeeds ── HALF-OPEN ←── cool-down elapsed
```

---

## 12. Guardrails and human approval

Some failures are about the agent doing the wrong thing successfully. Match the control to the risk of the action:

| Risk | Example action | Control |
| --- | --- | --- |
| Low, reversible | Read calendar, search notes | Automatic |
| Medium | Create a reminder, draft an email | Automatic, logged, easy to undo |
| High or irreversible | Send an email, delete events, spend money | **Human approval** before executing |

Other guardrails:

- **Input guardrails:** detect prompt injection in retrieved documents or tool results (treat them as data, not instructions).
- **Output guardrails:** block leaking secrets or personal data, check policy before replying.
- **Least privilege:** give each tool only the permissions it needs.

---

## 13. Every safeguard has a cost

Reliability is a set of trade-offs, which is why the Week 7 lab compares a naive and a hardened policy side by side.

| Safeguard | Buys | Costs |
| --- | --- | --- |
| Retries | Higher success rate | More calls, more cost, higher tail latency |
| Backoff | Doesn't hammer a rate-limited service | Waiting time |
| Short timeout | Bounded latency | Kills some healthy slow requests (which then get retried) |
| Validation + retry | No silent broken output | Extra calls when output is invalid |
| Fallback model | Availability during outages | Possibly lower quality; must be evaluated |
| Human approval | Safety on risky actions | Slower, needs a person |
| Loop budgets | No runaway cost | May stop tasks that needed one more step |

---

## Putting it together

A hardened call path for one step of the agent:

```txt
  call(step)
     │
     ├─ budget left? (steps, tokens, deadline) ── no ──→ stop gracefully
     │
     ▼
  start span (trace)
     │
     ▼
  attempt with timeout ──── error ────┐
     │                                ▼
     ▼                         transient? ── no ──→ surface error
  validate output ── invalid ─→  attempts left? ── yes ─→ backoff + jitter ─→ retry
     │                                │ no
     ▼                                ▼
   ok ─→ end span                fallback (model / cache / honest message)
                                      │
                                      ▼
                              end span, record outcome
```

| Concept | Primary purpose |
| --- | --- |
| **Tracing & metrics** | See what happened and how often |
| **Timeouts** | Bound how long anything can take |
| **Retries + backoff + jitter** | Recover from transient failures without making them worse |
| **Validation** | Turn silent bad output into a handled failure |
| **Fallbacks** | Keep working, or fail honestly, when retries run out |
| **Loop budgets** | Guarantee the agent stops and costs stay bounded |
| **Circuit breakers & rate limiting** | Protect the system and its dependencies under load |
| **Human approval & guardrails** | Prevent the agent from successfully doing the wrong thing |

### Connecting back to evals

```txt
Production trace shows a failure
        ↓
Root cause (which span? which failure type?)
        ↓
Fix (timeout, retry rule, validation, prompt, tool message)
        ↓
Add the case to the golden dataset (Week 6)
        ↓
Run the eval suite, including fault-injection cases
        ↓
Deploy and keep watching the metrics
```

The principle to remember:

> **Assume every call can fail. Decide in advance whether to retry, fall back or stop, measure what actually happens, and never let a failure pass silently as a success.**

---

## 14. Tools in the wild

You don't have to build every safeguard yourself. Each concept on this page has open-source and commercial tools behind it. Products in this space change quickly, so treat this as a map of categories and check each project's docs before choosing.

### Concept → tools

| Concept (section) | What the tools do | Examples |
| --- | --- | --- |
| **Tracing standard** (3) | A vendor-neutral format for spans and metrics, so you can switch tools without re-instrumenting | [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) (parts still in development); auto-instrumentation: [OpenLLMetry](https://github.com/traceloop/openllmetry), [OpenInference](https://github.com/Arize-ai/openinference) |
| **Observability platforms** (3) | Trace viewer, token and cost tracking, latency dashboards, often evals and prompt versions too | [Langfuse](https://langfuse.com) (open source, self-hostable), [Arize Phoenix](https://phoenix.arize.com) (open source, OpenTelemetry-based), [LangSmith](https://docs.smith.langchain.com) (LangChain), [W&B Weave](https://wandb.ai/site/weave), [Braintrust](https://www.braintrust.dev), [Helicone](https://www.helicone.ai) (proxy, almost no code change), [Pydantic Logfire](https://logfire.pydantic.dev); general monitoring vendors such as Datadog and Grafana also offer LLM views |
| **Timeouts and retries** (5, 6) | Backoff, jitter, attempt caps, choosing which errors to retry | Model SDKs' built-in `timeout` and `max_retries`; [tenacity](https://tenacity.readthedocs.io) for Python |
| **Validation** (7) | Parse and check output against a schema; re-ask the model when it fails | [Pydantic](https://docs.pydantic.dev), [Instructor](https://python.useinstructor.com), provider structured-output modes |
| **Fallbacks and rate limiting** (8, 11) | A gateway between your code and model APIs: retries, fallback to another model or provider, load balancing, rate limits, spend tracking | [LiteLLM](https://docs.litellm.ai) (open source), [Portkey](https://portkey.ai) |
| **Guardrails** (12) | Input and output checks: prompt injection, PII, topic and policy rules | [Guardrails AI](https://www.guardrailsai.com), [NVIDIA NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) |
| **Loop budgets and human approval** (10, 12) | Max turns, pause for approval, resume afterwards | Built into agent frameworks: [LangGraph](https://langchain-ai.github.io/langgraph/) interrupts, [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) (tracing, guardrails, max turns), Claude Agent SDK, [Pydantic AI](https://ai.pydantic.dev) |
| **Durable execution** | Save progress after each step so a crash, deploy or long human wait resumes instead of restarting | [Temporal](https://temporal.io), LangGraph checkpointing, [Restate](https://restate.dev), [Inngest](https://www.inngest.com), [DBOS](https://www.dbos.dev) |

Durable execution is the one concept not covered earlier on this page. It matters once an agent runs for minutes or hours, or waits on a person: without it, a server restart in the middle of a task loses the work, or worse, repeats side effects that already happened.

### How they fit together

```txt
           Your agent code  (framework: LangGraph / OpenAI Agents SDK / Pydantic AI / plain Python)
                │    loop budgets, human approval, validation (Pydantic / Instructor)
                │    retries on tools (tenacity)
                ▼
           Gateway  (LiteLLM / Portkey)  ── retries, fallback model, rate limits, cost
                │
                ▼
           Model providers                 Tools / APIs

   Everything emits OpenTelemetry spans ──→  Observability platform (Langfuse / Phoenix / …)
                                                  │
                                                  └──→ failing traces become eval cases (Week 6)

   Long-running or approval-heavy agents run inside durable execution (Temporal / LangGraph checkpoints / …)
```

### A small example: retries and validation without writing them yourself

```python
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

class TicketLabel(BaseModel):
    category: str
    urgency: int

class Transient(Exception):
    """Raise this for 429, 5xx, timeouts. Don't raise it for 400s or auth errors."""

@retry(
    stop=stop_after_attempt(3),                                  # cap attempts (section 6)
    wait=wait_random_exponential(multiplier=0.5, max=8),         # backoff + full jitter
    retry=retry_if_exception_type((Transient, ValidationError)), # retry only what can heal
)
def classify(ticket: str) -> TicketLabel:
    raw = call_model(ticket)                  # your model call, with its own timeout set
    return TicketLabel.model_validate_json(raw)  # invalid JSON → ValidationError → retry
```

This is about fifteen lines for what the Week 7 lab's hardened policy does by hand. The lab is still worth doing: once you have seen the naive policy report broken JSON as success, you know what to check that a library is actually doing for you.

### A suggested starter stack for circle projects

| Need | Start with | Why |
| --- | --- | --- |
| See traces, tokens, cost | Langfuse or Arize Phoenix | Free and open source, work with any framework, OpenTelemetry-compatible |
| Retries and backoff | SDK settings + tenacity | No new service to run |
| Validation | Pydantic (+ Instructor if you want automatic re-asking) | Already in most Python stacks |
| Fallback model | LiteLLM, when you need it | One call signature across providers |
| Human approval, long tasks | Your framework's interrupt/checkpoint feature | Add Temporal-style durable execution only if tasks run long or must survive restarts |

**Rule of thumb:** adopt one tool per layer, and only when you feel the pain it solves. A project with three agents and twelve dependencies is harder to make reliable than the failures it was meant to handle.

---

## This week's lab and Mini Muse step

- **Lab:** [Production reliability drill](../../labs/week7_production/README.md) — send the same task many times under injected faults (429, 503, hangs, slow answers, broken JSON) and compare a naive and a hardened policy on success rate, p95 latency and cost.
- **Mini Muse:** [Week 7 · Reliability](../mini-muse.md) — build the `Runtime` that traces, retries, times out and falls back, then break tools on purpose (`flaky`, `down`, `slow`).
- **Build deliverable:** add tracing plus at least three failure-handling mechanisms to your own project, and update your architecture diagram with the production layer.

## Discussion questions

1. Which failures in your project are worth retrying, and which should never be retried? Why?
2. Your agent's success rate is 97%, but users complain it is slow. Which metric would you look at first, and what might the trace show?
3. A tool sends emails. How would you make retries safe?
4. When `get_weather` is down, what should Mini Muse say? How would you test that it says it?
5. Adding a fallback model raised availability but users say answers got worse. What went wrong in the process?
6. What three things would you alert on for your project in production?
7. Which layer of your project would you hand to an existing tool first (tracing, retries, validation, fallback, guardrails), and what would you still keep in your own code?

## Further reading

- Revisit the tracing and monitoring sections of [DeepLearning.AI — Evaluating AI Agents](https://www.deeplearning.ai/courses/evaluating-ai-agents)
- [Anthropic — Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (guardrails and human checkpoints)
- [OpenTelemetry — GenAI agent and framework spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans)
