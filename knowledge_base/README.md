# Knowledge Base

Notes for the Agent Engineering Peer Learning Circle, exported from Notion on 2026-10-24. Diagrams and screenshots stay in Notion; each one is marked 🖼️ with a link back to its page.

**Start here:** [8-week plan](plan.md) — audience, schedule, readings, builds and agendas for every week.

## Notes in this folder

| Week | Concepts | Lab |
| --- | --- | --- |
| 1 · LLM Fundamentals | [LLM concepts](week-01-llm-fundamentals/concepts.md) | [Build your first LLM application](week-01-llm-fundamentals/lab.md) · [Extension: web demo](week-01-llm-fundamentals/lab-web-demo.md) |
| 2 · Context Engineering | [Context engineering](week-02-context-engineering/concepts.md) | [From single-call context to multi-run AI systems](week-02-context-engineering/lab.md) |
| 3 · RAG | [Retrieval-augmented generation](week-03-rag/concepts.md) | [Build a RAG system from scratch](week-03-rag/lab.md) |
| 4 · Tool Calling | [Tool calling](week-04-tool-calling/concepts.md) · [MCP](week-04-tool-calling/concepts-mcp.md) | [Weather assistant with tool calling & MCP](week-04-tool-calling/lab.md) |
| 5 · Agent Engineering | [State, workflow, control loop, routing](week-05-agent-engineering/concepts.md) | [Stateful agent workflow in TypeScript](week-05-agent-engineering/lab.md) |
| 6 · Evals | [Agent evaluation fundamentals](week-06-evals/concepts.md) · [Public benchmarks](week-06-evals/concepts-benchmarks.md) | [Evaluate and regression-test an agent](week-06-evals/lab.md) (code in [`agent-eval-lab/`](../agent-eval-lab/)) |

**Naming convention.** Each week has a folder `week-NN-topic/` containing:

- `concepts.md` — the week's main knowledge base
- `concepts-<subtopic>.md` — extra knowledge pages (e.g. `concepts-mcp.md`)
- `lab.md` — the week's lab guide
- `lab-<extension>.md` — optional lab extensions (e.g. `lab-web-demo.md`)

Page titles follow the same pattern: `Week N · Topic — Concepts` or `Week N · Topic — Lab: …`. Lab code lives outside this folder (see below).

Also: [Project Pool](project-pool.md) · [AI Engineering Interview Questions](interview-questions.md)

**Elsewhere in the repo:** lab code lives at the top level ([`agent-eval-lab/`](../agent-eval-lab/), [`weather-agent-lab/`](../weather-agent-lab/), [`app.py`](../app.py)); the Week 3 RAG documents are in [`rag_corpus/`](../rag_corpus/); question sets and public benchmarks are in [`benchmark/`](../benchmark/).
