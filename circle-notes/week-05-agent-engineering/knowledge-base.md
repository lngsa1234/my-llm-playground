# Week 5 | Agent Engineering

**Topics:** State · Workflow · Control Loop · Routing · Agent Orchestration

**Reference:** https://github.com/bojieli/ai-agent-book

### Learning objectives

By the end of Week 5, you should be able to:

- Explain what makes a system an **agent**, rather than a chatbot or simple tool-calling application.
- Understand how **state** allows an agent to track progress across multiple steps.
- Design a **workflow** with clear stages and transitions.
- Understand the **agent control loop**: observe → decide → act → observe.
- Use **routing** to choose the appropriate next action, tool, or specialized agent.
- Understand when **multi-agent orchestration** is useful—and when it is unnecessary.
- Build a small agent system with observable state and controlled execution.

---

## 1. State — What does the agent know right now?

Start with the idea:

> **State is the structured representation of where the agent currently is and what it knows about the task.**

A normal LLM call is essentially stateless. An agent needs application-level state to execute a task over multiple steps.

For example:

```python
state = {
    "user_request": "Plan a 3-day trip to Chicago",
    "destination": "Chicago",
    "budget": 1000,
    "tasks_completed": [],
    "tool_results": [],
    "current_step": "research",
    "status": "in_progress"
}
```

Discuss the difference between:

- **Conversation history** → what has been said
- **Context** → what information is provided to the model now
- **State** → structured information representing the execution of the task
- **Memory** → information persisted beyond the immediate execution

A useful discussion question:

> Should everything in the conversation become part of the agent state?

Usually, no. State should contain the information necessary to make reliable downstream decisions.

---

## 2. Workflow — How does work move through the system?

A workflow defines the **stages, transitions, and rules** governing execution.

Example:

```text
User Request
     ↓
Understand Request
     ↓
Create Plan
     ↓
Execute
     ↓
Validate
     ↓
Complete
```

A more realistic workflow can branch:

```text
                 ┌── Need more info ──→ Ask User
                 │
Request → Analyze
                 │
                 └── Enough info ──→ Execute → Validate
                                             │
                                      ┌──────┴──────┐
                                      ↓             ↓
                                    Pass           Fail
                                      ↓             ↓
                                    Done          Retry
```

This introduces an important Agent Engineering principle:

> **Not every workflow decision should be made by an LLM.**

Use deterministic logic where possible and LLM reasoning where judgment is actually required.

For example:

```python
if retry_count >= 2:
    return "human_review"

if test_result == "passed":
    return "complete"

return llm_decide_next_step(state)
```

---

## 3. Control Loop — What makes an agent keep working?

This is probably the most important Week 5 concept.

A basic agent loop can be represented as:

```text
Observe
   ↓
Reason / Decide
   ↓
Act
   ↓
Observe Result
   ↓
Update State
   ↓
Continue or Stop
```

Or in pseudocode:

```python
while not done:
    context = build_context(state)
    decision = model.decide(context)
    result = execute(decision)
    state = update_state(state, result)
    done = check_completion(state)
```

Connect this directly to Week 4.

In Week 4:

```text
User → LLM → Tool → Result → LLM
```

In Week 5:

```text
              ┌─────────────────────┐
              │                     │
              ↓                     │
State → LLM Decision → Action → Result
  ↑                              │
  └──────── State Update ────────┘
```

The **loop** is what allows the system to continue pursuing a goal rather than simply responding once.

Also introduce safeguards:

- maximum steps
- timeout
- retry limit
- tool permissions
- validation
- human approval
- failure states

An agent should never just "keep trying."

---

## 4. Routing — Who or what should handle the next step?

Routing answers:

> **Given the current state, what should happen next?**

For example:

```text
Incoming Request
       ↓
     Router
   /    |      \
  ↓     ↓       ↓
RAG   Tool    General
      Agent     LLM
```

Routing can be **deterministic**:

```python
if request.type == "weather":
    route_to_weather_tool()
```

or **LLM-based**:

```python
route = llm.classify(
    request,
    options=["research", "coding", "general"]
)
```

Or hybrid:

```text
Rules first
   ↓
Can we determine route?
   ↓
YES → deterministic route
NO  → LLM router
```

This is generally a better engineering pattern than asking an LLM to make every decision.

---

## 5. Agent Orchestration — How do multiple agents work together?

Only introduce multi-agent systems **after understanding a single agent**.

Example software-development system:

```text
              Product Request
                    ↓
                PM Agent
                    ↓
                 PRD
                    ↓
             Tech Lead Agent
                    ↓
              Architecture
                    ↓
            Engineer Agent
                    ↓
                  Code
                    ↓
                QA Agent
                    ↓
              Test Results
```

Each agent can have:

**Role + Inputs + Tools + State + Outputs + Exit criteria**

For example:

| Agent | Input | Output |
| --- | --- | --- |
| PM | User request | Feature spec |
| Tech Lead | Feature spec | Technical plan |
| Engineer | Technical plan | Code |
| QA | Code + requirements | Test results |

But emphasize an important point:

> **Multiple roles do not automatically require multiple agents.**

One agent with a good workflow may be simpler, cheaper, faster, and more reliable.

Use multiple agents when there is meaningful separation in:

- responsibilities
- context
- tools
- permissions
- evaluation criteria
