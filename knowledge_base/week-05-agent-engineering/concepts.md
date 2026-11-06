# Week 5 · Agent Engineering — Concepts

## At a glance

| Learn | Build | Key terms | Watch for |
| --- | --- | --- | --- |
| How an agent runs a goal across many steps, and how to keep it in control | An agent: a loop, a harness, and a workflow | Agent loop, harness, workflow | The model proposes the next step; your code decides what is allowed to happen |

An **agent** pursues a goal across many steps instead of answering in one call. Three ideas are enough to understand how one works and why it stays reliable: the **agent loop** that drives it, the **harness** that surrounds the model, and the **workflow** that bounds it. For short definitions of any term, see the **Glossary**.

## 1. The agent loop

An agent runs a short cycle over and over: ask the model what to do next, run that action, add the result back into the context, and repeat until the goal is met or a limit is hit.

![The agent loop](agent-loop.svg "420")

The key point is that **the model decides the next step on every turn**. That is what makes it an agent rather than a fixed script: the path is not written in advance, it emerges from each result. The loop keeps going while there is more to do and stops when the goal is reached, a step/budget limit is hit, or it needs a human.

## 2. The harness

An **agent is a harness wrapped around an LLM**. The model only ever receives a prompt and returns a proposed next action — it is stateless between calls and cannot touch the outside world. Everything that makes the loop dependable lives in the **harness**, the code you control.

![Agent = harness + LLM](agent-architecture.svg "560")

| Harness part | What it does |
| --- | --- |
| **Agent loop** | Repeats ask → act → observe until done |
| **Context** | Builds the prompt sent to the model each turn |
| **Memory** | Persists state and facts across steps |
| **Tools** | Run real actions and reach the environment (files, shell, APIs) |
| **Guardrails** | Enforce limits, permissions, and approvals |

> 🎯 Reliability, cost control, and safety come from the **harness**, not the model. The model supplies judgment; the harness decides what that judgment is actually allowed to do.

## 3. The workflow

A loop on its own can wander. A **workflow** gives it a map: the fixed stages a task moves through and the legal transitions between them. The agent loop runs inside the open-ended stage; the stages around it are deterministic steps you control.

![A goal workflow with the agent loop nested inside](multi_task_goal_hybrid_flow.svg "560")

This hybrid is what keeps an agent bounded. The surrounding stages — intake, planning, checking the result against the goal — are plain code with known transitions. Only **Run next task** hands control to the model-driven loop, and only until that task is done. Every run ends at a defined terminal state (`done`, or `failed` with a reason), so the agent has freedom exactly where judgment is needed and nowhere else.

> 💡 If you can draw the whole decision tree before running it, you want a fixed workflow, not an agent. Reserve the agent loop for the stages where a runtime result genuinely changes what should happen next.

## References

- [OpenAI API — Agents](https://developers.openai.com/api/docs/guides/agents)
- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OWASP — AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [Hugging Face Agents Course](https://huggingface.co/learn/agents-course/en/unit1/introduction)
