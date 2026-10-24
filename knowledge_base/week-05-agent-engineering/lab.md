# Week 5 · Agent Engineering — Lab: Stateful Agent Workflow in TypeScript

## Building a Stateful Agent Workflow in TypeScript

### Topics

**State · Workflow · Control Loop · Routing · Agent Orchestration**

### Estimated Time

**2–2.5 hours** for the core lab and experiments. The two bonus challenges are take-home.

| Block | Time |
| --- | --- |
| Setup and tour of the starter kit | 10 min |
| Parts I–II: state and workflow | 20 min |
| Parts III–VII: actions | 35 min |
| Parts VIII–XI: routing, loop, boundaries, tracing | 25 min |
| Experiments C and B | 20 min |
| Experiment A (discussion) | 10 min |
| Reflection | 10 min |

### Technology

- TypeScript, Node.js 20+
- OpenAI API (optional: the starter kit runs in **mock mode** without a key)
- Zod for structured output
- `tsx` to run TypeScript directly

---

# 1. Lab Overview

In previous weeks, we learned how to give an LLM access to context, knowledge, and external tools.

So far, most applications followed a relatively simple interaction pattern:

```text
User → LLM → Tool → LLM → Response
```

This week, we move from **LLM applications** to **agent systems**.

An agent must be able to:

1. Maintain task state.
2. Decide what should happen next.
3. Execute an action.
4. Observe the result.
5. Update its state.
6. Continue until the task reaches a terminal condition.

```text
                  ┌──────────────────────────────┐
                  ▼                              │
User → State → Route → Execute → Observe → Update State
                                                 │
                                       Terminal? → Stop
```

This repeated pattern is the **agent control loop**.

---

# 2. Learning Objectives

By completing this lab, you should be able to:

- Define explicit agent state using TypeScript.
- Model a multi-stage workflow with legal transitions.
- Build a bounded agent control loop.
- Use an LLM for decisions that need reasoning, and code for decisions that don't.
- Combine a deterministic tool and an LLM in one step.
- Add termination conditions, repair budgets, timeouts and failure handling.
- Trace every step so you can explain why the agent did what it did.
- Judge when a single workflow should, and should not, become a multi-agent system.

---

# 3. What You Will Build

A small **AI Software Engineering Agent**. It receives a feature request such as:

> Add a `/health` endpoint that returns service status and the current timestamp.

and moves it through a simplified development workflow:

```text
Feature Request
      ↓
    TRIAGE ──────────────┐
      ↓                  │
 REQUIREMENTS            │
      ↓                  │
   PLANNING              │
      ↓                  │
IMPLEMENTATION ◄──┐      │
      ↓           │      │
      QA          │      │
   ↙      ↘       │      │
FAIL      PASS    │      │
 │          ↓     │      │
 ├─ budget left ──┘      │
 │       COMPLETE        │
 └─ budget used ─► FAILED ◄┘
```

A failed QA sends the work back to **IMPLEMENTATION** with the QA feedback. That is the "repair". There is no separate repair stage.

The goal is **not** a production coding agent. The goal is to understand the engineering architecture behind one.

---

# 4. Architecture

Five concepts, each in its own file:

| Concept | Question it answers | File |
| --- | --- | --- |
| **State** | What does the system know? | `state.ts` |
| **Workflow** | Which transitions are legal? | `workflow.ts` |
| **Action** | What work happens in this stage? (LLM, tool, code or human) | `actions/*.ts` |
| **Router** | Given the new state, what runs next? | `router.ts` |
| **Control loop** | Execute, observe, update, route, repeat, stop | `agent.ts` |

One rule ties them together:

> **Actions do work and report what they observed. They never change the stage. The router decides the next stage, the workflow checks it is legal, and the loop applies it.**

And the principle behind the whole lab:

> **Use deterministic code for decisions that can be deterministic. Use the LLM when semantic reasoning is actually required.**

---

# 5. Project Setup

Download and unzip the **starter kit**, then:

```bash
cd week5-starter
npm install
cp .env.example .env
npm run typecheck
```

Put your key in `.env`. **No key? Leave it blank.** Every LLM call then returns deterministic fake output, so the whole workflow still runs. Do not commit `.env`.

```text
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5-mini
```

### What the starter kit gives you

```text
src/
├── state.ts               Part I — provided, read it
├── workflow.ts            Part II — YOU WRITE
├── router.ts              Part VIII — YOU WRITE
├── agent.ts               Part IX–X — YOU WRITE the loop
├── llm.ts                 provided: llmStructured() / llmText() + mock mode
├── trace.ts               provided: tracing
├── index.ts               provided: CLI
├── scenarios.ts           provided: self-check (npm run scenarios)
├── actions/
│   ├── types.ts           provided: the Action contract
│   ├── triage.ts          provided: worked example
│   ├── requirements.ts    YOU WRITE
│   ├── planning.ts        YOU WRITE
│   ├── implementation.ts  YOU WRITE
│   └── qa.ts              YOU WRITE
├── tools/runHandler.ts    provided: runs generated code
├── mock/responses.ts      provided: fake LLM output
└── experiments/llmRouter.ts  provided: Experiment B
```

> **Why a starter kit?** Without it, most of a session goes to SDK plumbing and tsconfig errors. (A fresh `npx tsc --init` currently produces settings that break plain relative imports and hide Node's types.) The kit's `tsconfig.json` just works with `tsx`.

`npm run scenarios` is your progress check. It fails until your code is in place and passes when the agent behaves correctly in every scenario.

---

# 6. Part I — Agent State

Open `src/state.ts`. The important part:

```ts
export type Stage =
  | "triage" | "requirements" | "planning"
  | "awaiting_approval"            // bonus
  | "implementation" | "qa"
  | "complete" | "failed";

export type Status = "running" | "paused" | "completed" | "failed";

export interface AgentState {
  request: string;
  stage: Stage;
  status: Status;

  triage?: { accepted: boolean; reason: string; decidedBy: "code" | "llm" };
  requirements?: string[];
  plan?: string[];
  implementation?: string;
  qaResult?: QAResult;

  requireApproval: boolean;   // bonus
  planVersion: number;
  approval?: { planVersion: number; approved: boolean; note?: string };

  repairCount: number;        // how many times QA has sent work back
  maxRepairs: number;         // 2 → up to 3 implementation attempts
  stepCount: number;
  maxSteps: number;           // 12

  failureReason?: string;     // why the agent stopped, if it failed
  history: TraceEvent[];      // the trace, as data
}
```

Notice three choices:

- **`repairCount` / `maxRepairs`**, not "retries". `maxRepairs: 2` means QA can send work back twice. The name says exactly what is counted.
- **`failureReason`**: a failed agent must say why.
- **`history`** is part of state, so a run can be saved, inspected and compared.

### Think About

Why not store the entire conversation as state?

- What information do future decisions actually need?
- Which fields should be structured, and which free-form text?
- What must survive between steps, or across a pause for human approval?

---

# 7. Part II — The Workflow

In `src/workflow.ts`, define the legal transitions:

```ts
const transitions: Record<Stage, readonly Stage[]> = {
  triage: ["requirements", "failed"],
  requirements: ["planning", "failed"],
  planning: ["implementation", "awaiting_approval", "failed"],
  awaiting_approval: ["implementation", "planning", "failed"],
  implementation: ["qa", "failed"],
  qa: ["implementation", "complete", "failed"],
  complete: [],
  failed: [],
};

export function canTransition(from: Stage, to: Stage): boolean {
  return transitions[from].includes(to);
}
```

Then write `advance()`, the **only** place that changes `stage` and `status`:

```ts
export function advance(state: AgentState, next: Stage, reason: string): void {
  const from = state.stage;

  if (!canTransition(from, next)) {
    throw new Error(`Invalid workflow transition: ${from} → ${next}`);
  }

  // Bookkeeping lives with the transition that causes it.
  if (from === "qa" && next === "implementation") {
    state.repairCount++;
  }

  state.stage = next;

  switch (next) {
    case "complete":
      state.status = "completed";
      break;
    case "failed":
      state.status = "failed";
      state.failureReason ??= reason;
      break;
    case "awaiting_approval":
      state.status = "paused";
      break;
    default:
      state.status = "running";
  }
}
```

### Why Do This?

Two reasons.

**The LLM must not be able to skip stages.** No model output can produce `triage → complete` or `requirements → qa`.

```text
LLM               → reasons about the task
Workflow engine   → controls which transitions are allowed
```

**Stage and status can't drift apart.** If stage is changed in five places, sooner or later one of them reaches `complete` but leaves `status = "running"`, and the loop never stops. One function, one source of truth.

---

# 8. Part III — Actions

Every action has the same shape (`src/actions/types.ts`):

```ts
export interface ActionResult {
  patch: Partial<AgentState>;   // what to write into state
  summary: string;              // one line for the trace
}

export type Action = (
  state: Readonly<AgentState>,
  ctx: ActionContext
) => Promise<ActionResult>;
```

An action receives **read-only** state and returns what it observed. It doesn't touch `stage`. This keeps actions easy to test, and makes "Observe" a real step in the loop instead of a box on a diagram.

## Worked example — Triage

Read `src/actions/triage.ts`. It has two gates:

```ts
export const triage: Action = async (state) => {
  const request = state.request.trim();

  // Deterministic gate first. No point paying for an LLM call to reject "".
  if (request.length < 10) {
    return {
      patch: { triage: { accepted: false, reason: "Request is too short to act on.", decidedBy: "code" } },
      summary: "Rejected by deterministic pre-check (too short)",
    };
  }
  // ...same for > 2000 characters...

  // Semantic gate: is this concrete enough to build?
  const result = await llmStructured(TriageSchema, {
    name: "triage",
    system: "You triage software feature requests. Accept a request only if it describes a concrete, " +
            "buildable change (what behavior, where). Reject vague requests and say what is missing.",
    user: request,
    mock: () => mockTriage(request),
  });

  return {
    patch: { triage: { ...result, decidedBy: "llm" } },
    summary: `${result.accepted ? "Accepted" : "Rejected"}: ${result.reason}`,
  };
};
```

`llmStructured(schema, call)` sends the prompt, asks the model for output matching the Zod schema, and returns a typed, validated object. The `mock` function is what it returns in mock mode.

Notice `decidedBy`. The trace will always say whether code or the LLM made the call.

### Question

Which other checks could run in code before the request reaches the model?

---

# 9. Part IV — Requirements

Write `src/actions/requirements.ts`. Follow the triage pattern:

- Schema: `{ requirements: string[] }`
- Prompt: turn the request into a short list of testable requirements, specific about fields, formats and status codes.
- Return `{ patch: { requirements }, summary: "Generated N requirements" }`
- Mock: `mock: mockRequirements`

Expected output for the `/health` request:

```text
1. Expose GET /health.
2. Return HTTP 200 when the service is healthy.
3. Return a JSON body.
4. Include a "status" field.
5. Include a "timestamp" field in ISO-8601 format.
6. Do not require authentication.
```

Structured as an array rather than a text blob, so the router can check that the list isn't empty, and so the QA reviewer can check each requirement one by one.

---

# 10. Part V — Planning

Write `src/actions/planning.ts`:

- Schema: `{ steps: string[] }`
- Input: `state.requirements`
- Tell the model the code contract (see Part VI) so the plan targets it.
- Return `{ patch: { plan: steps, planVersion: state.planVersion + 1 }, summary }`
- Mock: `mock: () => mockPlan()`

Every new plan gets a new version number. That matters in the approval bonus.

---

# 11. Part VI — Implementation

Write `src/actions/implementation.ts`. The generated code must follow a contract, so that QA can actually run it:

```text
One TypeScript module, no imports, exporting:

  function handle(): { status: number; body: unknown }
```

For example:

```ts
export function handle(): { status: number; body: unknown } {
  return {
    status: 200,
    body: { status: "ok", timestamp: new Date().toISOString() },
  };
}
```

Use `llmText(...)`, then clean the output with `stripFences()`, since models often wrap code in ``` fences even when told not to.

### Repairs are not re-rolls

If `state.qaResult` exists and failed, this is a **repair**. Put the QA feedback and the previous implementation in the prompt:

```ts
const isRepair = state.qaResult !== undefined && !state.qaResult.passed;

if (isRepair) {
  user +=
    `\n\nYour previous implementation FAILED QA.\n` +
    `QA feedback: ${state.qaResult!.feedback}\n\n` +
    `Previous implementation:\n${state.implementation}\n\n` +
    `Fix the problem. Keep everything that already worked.`;
}
```

Without this, a "repair" is just asking the same question again and hoping for a different answer. The feedback is what makes the loop a loop.

### Fault injection (for Experiment C)

`ctx.inject` lets you force failures. On the first attempt (`state.repairCount === 0`):

- `missing-timestamp`: tell the model to leave the timestamp out. Mock: return `MISSING_TIMESTAMP_IMPLEMENTATION`.
- `syntax-error`: after generating, cut the code at its last `}` so it can't compile. Done in code, not the prompt, so it is reliable.

On every attempt:

- `always-fail`: always leave the timestamp out.

---

# 12. Part VII — QA: a tool, then the LLM

QA receives the request, the requirements and the implementation. It runs **two** checks, in order.

**1. Deterministic: does the code run?** `runHandler(code)` writes the code to a temp file, runs it in a child process with a 5-second timeout, calls `handle()`, and checks the result has the shape `{ status: number, body }`.

If that fails, QA fails immediately with `checkedBy: "tool"`. **No LLM call.** A module that doesn't compile doesn't need a reviewer.

**2. Semantic: does it meet the requirements?** Only now ask the LLM, and give it the **observed output** from running the code, not just the code:

```ts
const review = await llmStructured(QASchema, {
  name: "qa_review",
  system: "You are a strict QA reviewer. Check the implementation against EACH requirement. " +
          "You are given the code and the actual response it produced when executed. " +
          "Fail it if any requirement is not met, and say exactly which one.",
  user: `Requirements: ...\n\nCode:\n${code}\n\n` +
        `Observed response when executed:\n${JSON.stringify(tool.output, null, 2)}`,
  mock: () => mockQA(tool.output),
});
```

Return:

```ts
{ passed: false,
  feedback: 'The response body is missing the required ISO-8601 "timestamp" field.',
  checkedBy: "llm",
  observed: { status: 200, body: { status: "ok" } } }
```

This is Principle 2 inside a single step: the cheap, certain check first; the expensive, judgment-based check only when it's needed.

> ⚠️ **Running generated code.** `runHandler` uses a separate process and a timeout, so a crash or infinite loop can't take down the agent. It is **not** a sandbox: the child process can still reach your files and network. In production, generated code runs in a container or VM with no credentials. Worth a minute of discussion.

---

# 13. Part VIII — Routing

Write `src/router.ts`. The router reads state **after** the action's result was applied and returns a decision with a reason:

```ts
export interface Decision {
  next: Stage;
  reason: string;
}

export function route(state: AgentState): Decision {
  switch (state.stage) {
    case "triage":
      return state.triage?.accepted
        ? { next: "requirements", reason: "Request accepted" }
        : { next: "failed", reason: `Triage rejected the request: ${state.triage?.reason ?? "no result"}` };

    case "requirements":
      return state.requirements?.length
        ? { next: "planning", reason: `${state.requirements.length} requirements` }
        : { next: "failed", reason: "No requirements were produced" };

    // planning, implementation: same idea

    case "qa":
      return routeAfterQA(state);
    // ...
  }
}
```

The QA decision:

```ts
export function routeAfterQA(state: AgentState): Decision {
  const qa = state.qaResult;

  if (!qa) {
    return { next: "failed", reason: "QA produced no result" };
  }
  if (qa.passed) {
    return { next: "complete", reason: "QA passed" };
  }
  if (state.repairCount >= state.maxRepairs) {
    return {
      next: "failed",
      reason: `QA failed and repair budget is used up (${state.repairCount}/${state.maxRepairs}): ${qa.feedback}`,
    };
  }
  return {
    next: "implementation",
    reason: `QA failed (${qa.checkedBy}); repair ${state.repairCount + 1} of ${state.maxRepairs}`,
  };
}
```

The QA step made a **semantic judgment**: does this satisfy the requirements? Code made the **workflow decision**:

```text
PASS                        → complete
FAIL + repair budget left   → implementation
FAIL + budget used up       → failed
```

Every decision carries a `reason`. That is what makes the trace explain *why*, not just *what*.

---

# 14. Part IX — The Control Loop

Write `runAgent()` in `src/agent.ts`:

```ts
export async function runAgent(state: AgentState, opts: AgentOptions): Promise<AgentState> {
  const router = opts.router ?? route;
  const stepTimeoutMs = opts.stepTimeoutMs ?? 120_000;

  while (state.status === "running") {
    // Boundary 1: never run forever. Stop cleanly in a terminal state.
    if (state.stepCount >= state.maxSteps) {
      forceFail(state, `Maximum steps exceeded (${state.maxSteps})`);
      traceStep(state, state.stage, "Stopped by step limit");
      break;
    }

    const stage = state.stage;
    const action = actions[stage];
    if (!action) {
      forceFail(state, `No action registered for stage "${stage}"`);
      break;
    }

    state.stepCount++;

    // EXECUTE + OBSERVE. Boundary 2: every step has a timeout.
    let result;
    try {
      result = await withTimeout(action(state, opts), stepTimeoutMs);
    } catch (e) {
      forceFail(state, `Action "${stage}" threw: ${(e as Error).message}`);
      traceStep(state, stage, `ERROR: ${(e as Error).message}`);
      break;
    }

    // UPDATE STATE with what the action observed.
    Object.assign(state, result.patch);

    // DECIDE what happens next.
    const decision = await router(state);

    // Boundary 3: the workflow validates the decision, whoever made it.
    if (!canTransition(stage, decision.next)) {
      traceStep(state, stage, result.summary);
      forceFail(state, `Router proposed an illegal transition ${stage} → ${decision.next}`);
      break;
    }

    advance(state, decision.next, decision.reason);
    traceStep(state, stage, result.summary, { from: stage, to: decision.next, reason: decision.reason });
  }

  return state;
}
```

```text
Read state → Run action → Observe result → Update state → Route → Validate → Advance
     ▲                                                                          │
     └────────────────────── while status === "running" ───────────────────────┘
```

---

# 15. Part X — Safety Boundaries

The loop above already has them. Make sure you can point to each:

| Boundary | Where | What happens |
| --- | --- | --- |
| Max steps | top of the loop | `failed`, reason "Maximum steps exceeded" |
| Repair budget | `routeAfterQA` | `failed` with the last QA feedback |
| Step timeout | `withTimeout` | `failed`, reason names the stage |
| Action crash | `try/catch` | `failed`, reason names the stage |
| Illegal decision | `canTransition` check | `failed`, reason names the transition |
| Generated code | `runHandler` | separate process, 5 s timeout |

Every one of these ends in a **terminal state with a reason**. None of them throws out of the loop. "Throw and crash" is not a terminal state; it is a stack trace someone has to read at 2 a.m.

The repair budget, counted precisely, with `maxRepairs: 2`:

```text
Implementation #1 → QA FAIL → repair 1 of 2
Implementation #2 → QA FAIL → repair 2 of 2
Implementation #3 → QA FAIL → budget used up → FAILED   (9 steps)
```

Two kinds of retry exist in this system. Keep them apart:

- **Network retries** (a 503 from the API): the OpenAI SDK does these, configured in `llm.ts`.
- **Workflow repairs** (the work was wrong): the agent does these, counted in state and visible in the trace.

---

# 16. Part XI — Execution Tracing

`traceStep()` records one event per step into `state.history` and prints it. At the end, `saveTrace()` writes the whole state as JSON to `traces/`.

Run:

```bash
npm start -- --inject missing-timestamp
```

You should see:

```text
================================================
Agent started  (LLM: mock)
Request: Add a /health endpoint that returns service status and the current timestamp.
================================================

[Step 1] TRIAGE
  Result:     Accepted: The request describes a concrete backend change.
  Transition: TRIAGE → REQUIREMENTS
  Why:        Request accepted

[Step 2] REQUIREMENTS
  Result:     Generated 6 requirements
  Transition: REQUIREMENTS → PLANNING
  Why:        6 requirements

[Step 3] PLANNING
  Result:     Plan v1 with 4 steps
  Transition: PLANNING → IMPLEMENTATION
  Why:        Plan v1 ready

[Step 4] IMPLEMENTATION
  Result:     Implementation generated
  Transition: IMPLEMENTATION → QA
  Why:        Implementation ready for QA

[Step 5] QA
  Result:     FAIL (llm): The response body is missing the required ISO-8601 "timestamp" field.
  Transition: QA → IMPLEMENTATION
  Why:        QA failed (llm); repair 1 of 2

[Step 6] IMPLEMENTATION
  Result:     Implementation repaired using QA feedback
  Transition: IMPLEMENTATION → QA
  Why:        Implementation ready for QA

[Step 7] QA
  Result:     PASS (llm): All requirements are satisfied.
  Transition: QA → COMPLETE
  Why:        QA passed

================================================
Agent completed
Steps: 7   Repairs: 1/2   LLM calls: 7
================================================
Trace saved to traces/2026-...-missing-timestamp.json
```

From this trace alone you can answer: what happened, which action ran, what it returned, why each transition happened, how many repairs it took, how many LLM calls it cost, and why it stopped.

Now run `npm run scenarios`. When every line says `PASS`, your agent is complete.

---

# 17. Part XII — Agent Orchestration

Your workflow already has distinct responsibilities:

```text
Triage → Requirements → Planning → Implementation → QA
   PM          PM         Tech lead     Engineer      QA
```

**Do not automatically turn every role into a separate agent.** Ask what a separate agent would give you. Separate agents become useful when roles need different:

- system instructions or context
- tools or permissions (QA can run code; the planner can't)
- models (a cheap model for triage, a strong one for implementation)
- evaluation criteria or ownership

Otherwise, a single controlled workflow is simpler, cheaper and easier to debug.

---

# 18. Experiment C — Inject Failures (10 min)

Run each and read the trace:

```bash
npm start -- --inject missing-timestamp
npm start -- --inject syntax-error
npm start -- --inject always-fail
```

Compare:

- `missing-timestamp`: the code runs, so the **LLM reviewer** catches the problem. 7 steps.
- `syntax-error`: the **tool** catches it. QA fails with `checkedBy: "tool"` and no LLM call: still 7 steps, but 6 LLM calls instead of 7. The compiler error becomes the repair feedback.
- `always-fail`: the repair budget runs out. The agent stops at step 9 in `failed`, and the reason includes the last QA feedback.

Look at the repair prompt in your implementation action. What would happen if it didn't include the QA feedback?

---

# 19. Experiment B — Let the LLM Route (10 min)

`src/experiments/llmRouter.ts` replaces `routeAfterQA` with an LLM call using the naive prompt:

```text
QA result: { passed: false, feedback: "..." }

Available actions:
- implementation
- qa
- complete
- failed
```

Run it against a task that never passes:

```bash
npm start -- --router llm --inject always-fail
```

With the code router, this run stopped at **step 9**: repair budget used up. With the LLM router, it keeps choosing `implementation`, a perfectly reasonable answer to the question it was asked, until the **step limit** stops it at step 12. Look at the summary line:

```text
Steps: 12   Repairs: 4/2   LLM calls: 16
```

Four repairs against a budget of two. Every one of those decisions was a legal transition, so the workflow guard allowed them. The budget only lived in the code router, and the code router was gone.

> In mock mode the LLM router's choice is **simulated**. With a real key, run it 3–5 times and compare.

Discuss:

1. The model never saw `repairCount` or `maxRepairs`. To route correctly it would need them in the prompt, and then you are trusting it to compare two integers. If a decision fits in three lines of TypeScript, why delegate it?
2. Which guardrail saved the run? What if `maxSteps` had been 100, and each step cost a real API call?
3. If the model answered `qa` (QA again, without changes), what would `canTransition` do? Try forcing it.
4. When the LLM router fails, can you tell *why* from the trace? Compare with the code router's reason.
5. Should the repair budget be enforced in `advance()` instead of only in the router, so that *no* router can exceed it? What's the tradeoff?

---

# 20. Experiment A — Remove the Workflow (discussion, 10 min)

Imagine replacing everything with one prompt:

```text
You are an autonomous software engineering agent.
Given the user's request, determine what steps are necessary
and continue until the task is complete.
```

You don't need to build it. Using your traces, discuss:

- In the free-form version, where would you find the requirements, or the reason it stopped?
- How would you guarantee it can't skip QA?
- How would you cap its cost?
- Which failure from Experiment C would it handle worse, and which might it handle *better*?
- Which would you trust in production, and for which kinds of task?

(Optional take-home: build it with a tool-calling loop and compare traces.)

---

# 21. Final Architecture

```text
                       USER
                         │
                         ▼
                  ┌─────────────┐
           ┌─────►│ Agent State │◄──────────────┐
           │      └──────┬──────┘               │
           │             ▼                      │
           │      ┌─────────────┐               │
           │      │   Action    │  LLM / Tool / Code / Human
           │      └──────┬──────┘               │
           │             ▼                      │
           │       Observe (patch)  ── update ──┘
           │             ▼
           │      ┌─────────────┐
           │      │   Router    │  decides next stage + reason
           │      └──────┬──────┘
           │             ▼
           │      ┌─────────────┐
           │      │  Workflow   │  legal? → advance()
           │      └──────┬──────┘
           │             ▼
           │      Terminal or paused?
           │        ↙           ↘
           └─── NO              YES → END (complete / failed / awaiting human)

   Boundaries on every iteration: max steps · timeout · repair budget · crash handling
```

---

# 22. Key Engineering Principles

### Principle 1 — Agent state should be explicit

Don't hide important application state inside prompts or conversation history.

### Principle 2 — Not every decision belongs to the LLM

```text
Deterministic when possible.
Probabilistic when necessary.
```

You saw this three times: triage pre-checks, the QA tool before the QA reviewer, and the router.

### Principle 3 — Workflow and reasoning are different

The LLM reasons about what something means. Your application controls what the system is allowed to do.

### Principle 4 — Every loop needs boundaries

```text
max steps · repair budget · timeouts · tool permissions
isolation for generated code · failure states with reasons · human approval
```

### Principle 5 — Agent behavior must be observable

You should be able to answer, from the trace alone:

```text
What happened? Why? What state was the agent in?
Which action ran? What did it return?
Why did the workflow transition? Why did the agent stop?
```

---

# 23. Deliverables

### 1. Source code

Your completed starter kit. `npm run scenarios` must pass.

### 2. Execution traces

Two JSON files from `traces/`:

- a clean run (`npm start`)
- a repair run (`npm start -- --inject missing-timestamp`)

If you used a real API key, say which model.

### 3. Architecture diagram

Draw your agent. Mark: state, workflow, router, LLM actions, tool, control loop, boundaries, terminal states.

### 4. Short reflection

1. What is the difference between **state** and **conversation history**?
2. What is the difference between a **workflow** and a **control loop**?
3. Which decisions in your agent are deterministic? Which need LLM reasoning?
4. In QA, why does the tool run before the LLM reviewer?
5. In Experiment B, which guardrail stopped the LLM router, and what does that tell you?
6. What prevents your agent from looping forever? List every mechanism.
7. When would you split this system into multiple agents?

---

# 24. Bonus Challenge — Human Approval (take-home)

Add a human checkpoint between planning and implementation:

```text
PLANNING → AWAITING_APPROVAL → (human) ─ approve → IMPLEMENTATION
                                       └ reject  → PLANNING (with the reviewer's note)
```

The loop exits with `status: "paused"`. Implement `applyApproval(state, decision)` in `agent.ts`, which:

1. Checks the agent is actually in `awaiting_approval`.
2. Checks `decision.planVersion === state.planVersion`. **An approval of plan v1 must never approve plan v2.** Throw on a stale approval.
3. Records the decision in `state.approval` and calls `advance()`.

Then let the planning action include `state.approval.note` in its prompt after a rejection.

Run it:

```bash
npm start -- --approval
npm start -- --approval --approvals "reject:Add a version field,approve"
npm run scenarios -- --bonus
```

The trace should show plan v1 rejected, plan v2 generated and approved, then implementation.

> **Autonomy does not mean removing human control. Good agent systems deliberately define where humans remain in the loop, and which version of the work they approved.**

---

# 25. Bonus Challenge — Multi-Agent Version (take-home)

Redesign as:

```text
                 Orchestrator
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
    PM Agent    Engineer Agent    QA Agent
        └─────────────┼─────────────┘
                      ↓
                 Shared State
```

For each agent define: responsibility, input, output, tools, permissions, model, context, exit criteria.

Then answer the most important question:

> **Did the multi-agent architecture actually improve the system, or did it only make the architecture more complicated?**

Back up your answer with traces: steps, LLM calls, and whether failures got easier or harder to explain.

---

# Completion Criteria

You have completed Week 5 when you can look at any agent application and identify:

- **State** — What does the agent know?
- **Workflow** — What stages can the task move through, and what is forbidden?
- **Control Loop** — What makes the agent continue, and what makes it stop?
- **Routing** — How is the next action chosen, and by whom: code or model?
- **Orchestration** — How are responsibilities coordinated?
- **Guardrails** — What prevents uncontrolled execution?

The goal of this lab is not simply to build an agent. It is to understand **how to engineer an agent whose behavior you can control, observe, debug and evaluate.**
