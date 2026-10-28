# Knowledge Base

Notes for the Agent Engineering Peer Learning Circle, exported from Notion on 2026-10-24. Week 1's core diagrams are rendered directly in the app; remaining diagrams and screenshots stay in Notion and are marked 🖼️ with a link back to their page.

**Start here:** [8-week plan](plan.md) — audience, schedule, readings, builds and agendas for every week.

**Course project:** [Mini Muse](mini-muse.md) — the personal-assistant agent the circle builds one component per week, with what to build, try and check each week.

## Notes in this folder

| Week | Concepts | Lab |
| --- | --- | --- |
| 1 · LLM Fundamentals | [LLM concepts](week-01-llm-fundamentals/concepts.md) | [Build your first LLM application](week-01-llm-fundamentals/lab.md) · [Extension: web demo](week-01-llm-fundamentals/lab-web-demo.md) · [Handout: Mini Muse](week-01-llm-fundamentals/handout-mini-muse.md) |
| 2 · Context Engineering | [Context engineering](week-02-context-engineering/concepts.md) | [From single-call context to multi-run AI systems](week-02-context-engineering/lab.md) |
| 3 · RAG | [Retrieval-augmented generation](week-03-rag/concepts.md) | [Build a RAG system from scratch](week-03-rag/lab.md) |
| 4 · Tool Calling | [Tool calling](week-04-tool-calling/concepts.md) · [MCP](week-04-tool-calling/concepts-mcp.md) | [Weather assistant with tool calling & MCP](week-04-tool-calling/lab.md) |
| 5 · Agent Engineering | [State, workflow, control loop, routing](week-05-agent-engineering/concepts.md) | [Stateful agent workflow in TypeScript](week-05-agent-engineering/lab.md) (Python app version in [`labs/week5_agent_workflow/`](../labs/week5_agent_workflow/)) |
| 6 · Evals | [Agent evaluation fundamentals](week-06-evals/concepts.md) · [Public benchmarks](week-06-evals/concepts-benchmarks.md) | [Evaluate and regression-test an agent](week-06-evals/lab.md) (code in [`labs/week6_agent_eval/`](../labs/week6_agent_eval/)) |
| 7 · Production AI | not written yet | [Production reliability drill](../labs/week7_production/README.md) |

**Naming convention.** Each week has a folder `week-NN-topic/` containing:

- `concepts.md` — the week's main knowledge base
- `concepts-<subtopic>.md` — extra knowledge pages (e.g. `concepts-mcp.md`)
- `lab.md` — the week's lab guide
- `lab-<extension>.md` — optional lab extensions (e.g. `lab-web-demo.md`)
- `handout-<topic>.md` — handouts for the session (e.g. `handout-mini-muse.md`)

Page titles follow the same pattern: `Week N · Topic — Concepts` or `Week N · Topic — Lab: …`. Lab code lives outside this folder (see below).

Also: [Project Pool](project-pool.md) · [AI Engineering Interview Questions](interview-questions.md)

**Elsewhere in the repo:** Mini Muse's code is in [`mini_muse/`](../mini_muse/); each lab's code, data and web page live in [`labs/`](../labs/), one folder per week; [`app.py`](../app.py) shows them all as one site; public benchmarks are in [`benchmark/`](../benchmark/).
