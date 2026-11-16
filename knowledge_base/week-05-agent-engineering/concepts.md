# Week 5 · Agent Engineering — Concepts

## At a glance

| Learn | Build | Key terms | Watch for |
| --- | --- | --- | --- |
| What an agent is made of, how to build one that stays in control, and when one agent isn't enough | An agent: a loop, a harness, and a workflow | Agent loop, harness, workflow, router, orchestrator–workers, handoff | The model proposes the next step; your code decides what is allowed to happen |

An **agent** pursues a goal across many steps instead of answering in one call. This page answers three questions: **what an agent looks like**, **how you implement one**, and **when to use more than one agent**. For short definitions of any term, see the **Glossary**.

## 1. What an agent looks like

An agent is a **harness wrapped around an LLM**, driven by a short **loop**. The model supplies judgment on each turn; the harness holds state, runs actions, and keeps the whole thing bounded.

### 1.1 The agent loop

An agent runs a short cycle over and over: ask the model what to do next, run that action, add the result back into the context, and repeat until the goal is met or a limit is hit.

![The agent loop](agent-loop.svg "300")

The key point is that **the model decides the next step on every turn**. That is what makes it an agent rather than a fixed script: the path is not written in advance, it emerges from each result. The loop keeps going while there is more to do and stops when the goal is reached, a step/budget limit is hit, or it needs a human.

### 1.2 The harness

The model only ever receives a prompt and returns a proposed next action — it is stateless between calls and cannot touch the outside world. Everything that makes the loop dependable lives in the **harness**, the code you control.

![Agent = harness + LLM](agent-architecture.svg "560")

| Harness part | What it does |
| --- | --- |
| **Agent loop** | Repeats ask → act → observe until done |
| **Context** | Builds the prompt sent to the model each turn |
| **Memory** | Persists state and facts across steps |
| **Tools** | Run real actions and reach the environment (files, shell, APIs) |
| **Guardrails** | Enforce limits, permissions, and approvals |

> 🎯 Reliability, cost control, and safety come from the **harness**, not the model. The model supplies judgment; the harness decides what that judgment is actually allowed to do.

## 2. How do we implement an agent

Building an agent is mostly deciding where the model gets freedom and where your code stays in charge. Design the **workflow** first, then let the loop run only inside the stages that genuinely need judgment.

### 2.1 Design the workflow

A loop on its own can wander. A **workflow** gives it a map: the fixed stages a task moves through and the legal transitions between them. The agent loop runs inside the open-ended stage; the stages around it are deterministic steps you control.

![A goal workflow with the agent loop nested inside](multi_task_goal_hybrid_flow.svg "560")

This hybrid is what keeps an agent bounded. The surrounding stages — intake, planning, checking the result against the goal — are plain code with known transitions. Only **Run next task** hands control to the model-driven loop, and only until that task is done. Every run ends at a defined terminal state (`done`, or `failed` with a reason), so the agent has freedom exactly where judgment is needed and nowhere else.

> 💡 If you can draw the whole decision tree before running it, you want a fixed workflow, not an agent. Reserve the agent loop for the stages where a runtime result genuinely changes what should happen next.

### 2.2 Build it in order

With the workflow drawn, the rest is filling it in — structure first, model last.

1. **Define the workflow** — stages, legal transitions, and terminal states — before writing any prompt.
2. **Build the control loop** that runs each stage, updates state, and stops as soon as state is terminal.
3. **Let the model drive only the open-ended stage**; keep known decisions in code.
4. **Give every tool an owner:** validate its arguments, check permissions, and require approval for risky actions.
5. **Bound every loop** — max steps, budget, timeout — each ending in a terminal state with a reason, never a crash.
6. **Trace every step** so any run can be explained, saved, and evaluated.

> 🛡️ Tool results and retrieved text are **evidence, not instructions**. Treat external responses as untrusted input, and enforce tool permissions and approval gates in the harness, never in the prompt alone.

### 2.3 Keep a human in the loop

Some actions are too costly to undo for the agent to take on its own — sending a message, spending money, deleting data, changing production. For these, the loop should **pause and ask a person to approve** before the tool runs, then resume with the decision recorded in state.

An approval gate is just another guardrail, but instead of ending the run it moves it into a **paused** state: the agent waits for a human decision rather than stopping. The model may *propose* a risky action; only an approval lets the tool actually run.

| The agent may act on its own | Require human approval first |
| --- | --- |
| Read-only or easily reversible actions — search, read a file, draft text | Irreversible or high-impact actions — send, pay, delete, publish, change production |

> 🧭 Keep the gate in the harness, not the prompt, and record **who approved what**. A model can be talked out of a rule; an approval check in code cannot, and the trace then explains every side effect.

## 3. When one agent isn't enough

Mini Muse is a **single agent**: one loop, one system prompt, one context window, and 6–7 tools. That is the right design for it, and for most first agents. This section covers what comes next: the patterns teams reach for when a single loop stops being enough, what each one costs, and how to tell whether you need one.

### 3.1 Four patterns, simplest first

![Four ways to arrange agents](agent-patterns.svg "560")

**Router.** One cheap classification call picks which prompt, model, or tool set handles the request. Exactly one path runs.
- *In Mini Muse:* "What's the weather in Detroit?" goes to a small model with only `get_weather`. "Plan Friday and email Maya" goes to the full agent.
- *In a real product:* customer support triage, where refund questions, technical issues, and general questions each get their own prompt and tools. Anthropic's agent guide gives another: easy questions to a small, cheap model and hard ones to a stronger model.

**Orchestrator–workers** (also called a supervisor or "super agent"). A lead agent decides the subtasks *at runtime*, sends each to a worker agent with its own context, then combines the short results.
- *In Mini Muse:* "Plan the team offsite." One worker finds a free day on the calendar, one pulls the budget from your notes, and one drafts the invite. The lead combines them and holds the email for approval.
- *In a real product:* Claude's Research feature, where a lead agent runs 3–5 search agents in parallel (see 3.3).

**Evaluator–optimizer.** One call drafts, a second call critiques against explicit criteria, and the draft is revised until it passes or hits a round cap.
- *In Mini Muse:* before the email to Maya is held for approval, a critic checks it against your notes ("Is the agenda item correct? Is the tone right?") and asks for at most two revisions.
- *In a real product:* code agents that write a change, run the tests, and fix what fails; writing tools that check a draft against a style guide.

**Handoffs.** A specialist agent takes over the conversation and owns the next reply, instead of reporting back to a manager.
- *In Mini Muse:* not needed today. If Mini Muse grew a separate travel-booking agent, the main agent would hand the conversation to it.
- *In a real product:* support flows that go triage agent → billing agent → escalation agent.

These patterns combine: the orchestrator's workers can be routers, and a worker can run its own evaluator–optimizer loop. Start with one.

### 3.2 Manager or handoff: who owns the reply?

When agents work together, one design choice shapes everything else: does the first agent **stay in charge**, or does it **give the conversation away**? The OpenAI Agents SDK names these two options explicitly.

**Agents as tools (a manager).** The manager calls a specialist like a function, gets its result back, and decides what to do next. The manager always writes the reply to the user. It can call several specialists at once, and every decision sits in one trace, so it is easy to debug. Use it for fan-out and fan-in work: research, or a plan built from several sources.

**Handoffs.** The specialist takes over and talks to the user directly. Only one agent works at a time, and to see why a conversation ended up somewhere, you follow the chain of handoffs. Use it when the domains are clearly separate and each needs its own instructions and permissions, such as billing vs. tech support.

In Mini Muse terms, the approval gate is easier to keep with a manager: one agent owns every risky action, so one place holds them all for approval.

### 3.3 Case study: Claude's Research feature, with real numbers

Anthropic published how they built Claude's Research feature, a multi-agent system in production. It is a useful benchmark for what multi-agent buys you and what it costs.

- **Architecture.** A lead agent plans the research, saves the plan to memory, and spawns subagents. Each subagent searches in parallel in its own context window and returns condensed findings. A separate citation agent adds the citations at the end.
- **How many agents.** The lead usually starts 3–5 subagents in parallel. The prompt scales effort to the question: simple fact-finding gets 1 agent and 3–10 tool calls; a direct comparison gets 2–4 subagents with 10–15 calls each; complex research gets 10 or more subagents with clearly divided jobs.
- **The gain.** A Claude Opus 4 lead with Claude Sonnet 4 subagents scored **90.2% higher** than a single Claude Opus 4 agent on Anthropic's internal research eval.
- **The cost.** A single agent uses about **4×** the tokens of a chat. The multi-agent system uses about **15×**. On the BrowseComp benchmark, token usage alone explained **80%** of the difference in performance: the system wins largely because it can spend more tokens across more context windows.
- **What went wrong first.** Early versions started 50 subagents for simple questions, kept searching for sources that don't exist, and gave vague instructions that sent two subagents after the same question.
- **Where it doesn't fit.** Tasks where every agent needs the same context, tasks where subtasks depend on each other, and most coding tasks, which split into fewer independent pieces than research does.

> 🎯 Multi-agent wins when the work splits into **independent threads that can run in parallel** and the answer is worth roughly 15× the tokens. Research fits. Booking yoga after checking the calendar does not: the second step depends on the first.

### 3.4 Should your agent be multi-agent? Five questions

Answer these about your own agent. Split only where the answer is clearly yes. The Mini Muse answers are filled in as an example.

1. **Do subtasks run independently, without needing each other's results?** If yes, orchestrator–workers can run them in parallel.
   - *Mini Muse:* mostly no. Booking depends on checking the calendar first.
2. **Do parts need different tools or permissions?** If yes, separate agents can keep a read-only agent away from sending email.
   - *Mini Muse:* partly. Reading notes is safe and sending email is risky, but the approval gate already handles that.
3. **Would a cheaper model handle most requests?** If yes, add a router.
   - *Mini Muse:* yes. Weather and single calendar checks don't need the full agent. This is the first split worth trying.
4. **Does the context overflow one window?** If yes, workers with their own context can return summaries.
   - *Mini Muse:* no. Requests are short.
5. **Is the result worth about 15× the tokens?** If yes, multi-agent can pay off.
   - *Mini Muse:* no. Requests are quick and personal.

For Mini Muse, the verdict is: stay a single agent, and try a **router** first if cost matters. The Week 5 lab's **Part XII — Agent Orchestration** and the take-home **Multi-Agent Version** challenge ask you to make this call for your own workflow and to back it up with traces.

> 💡 Every extra agent adds a prompt to maintain, a context to keep in sync, and a place for errors to compound. Add one only when you can name what it gets that the single loop can't: different tools, a different model, its own context window, or parallel speed.

## References

- [OpenAI API — Agents](https://developers.openai.com/api/docs/guides/agents)
- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [OpenAI API — Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [OWASP — AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [Hugging Face Agents Course](https://huggingface.co/learn/agents-course/en/unit1/introduction)
