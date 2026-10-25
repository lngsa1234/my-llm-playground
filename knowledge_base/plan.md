# Agent Engineering Peer Learning Circle — 8-Week Plan

> Exported from the Notion page "Agent Engineering Peer Learning Circle – Temporary Plan" on 2026-10-24. The notes for each week are linked under its heading; see the [knowledge base index](README.md) for all pages.

**Target audience:** PM, Technical PM, Software/System Engineer, Data/ML professionals moving toward AI PM, AI Engineer, AI Systems or Agent Engineering.

**Prerequisites:** Basic programming language and REST API familiarity recommended. Prior AI/ML experience is not required. AI coding tools are fine, but participants should understand the architecture and code they build.

**Standard build stack:** Python/JavaScript/TypeScript + OpenAI/Claude API

**Time commitment:** ~3–4 hours/week: 30–60 min required material, 1–2 hours hands-on building, and 60–75 min peer discussion.

**Team organization:**

- **Weeks 1–2:** Individual learning and builds
- **Weeks 3–4:** Work in pairs
- **Weeks 5–8:** Form teams of **2–3 people** and collaborate on a specific project

Please take a look at the [project pool](project-pool.md).

Lynn's demo: [lngsa1234/my-llm-playground](https://github.com/lngsa1234/my-llm-playground) (this repository)

**Communication:**

- CircleW app: please **approve your Circle invitation in the CircleW app**. Once you join the Circle, you'll be able to access your **weekly meeting link through the Calendar page, Circle page or Home page.**
- Please download the CircleW app to receive real-time notifications.

| Week | Topic | Core concepts | Build / Deliverable |
| --- | --- | --- | --- |
| **1** | LLM Fundamentals | API calls, tokens, context window, messages, structured output | Basic LLM application with structured output |
| **2** | Context Engineering | Context construction, conversation history, state, memory, context limits | Add context management and state |
| **3** | RAG | Embeddings, chunking, vector search, retrieval, grounding | Add a retrieval pipeline |
| **4** | Tool Calling + Catch-up | Function calling, tool schema, APIs, error handling, MCP | Add 2–3 tools; consolidate Weeks 1–3 |
| **5** | Agent Engineering | Agent loop, state, routing, workflow, orchestration, termination | Convert application into an agent, **JEV** |
| **6** | Evals | Golden datasets, task success, tool evaluation, LLM-as-a-judge, regression | Build 20–30 test cases + automated eval |
| **7** | Production AI | Tracing, observability, retries, fallback, latency, cost, reliability | Add tracing and failure handling |
| **8** | AI System Design | Architecture, trade-offs, scalability, human-in-loop, system boundaries | Final architecture + demo + peer review |

## Course project: Mini Muse

The circle builds one agent together across the 8 weeks: **Mini Muse**, a small personal assistant. Each week's topic adds one component, and by Week 8 they are wired into one assistant. See the [Mini Muse guide](mini-muse.md) and the code in [`mini_muse/`](../mini_muse/).

| Week | Mini Muse gains |
| --- | --- |
| 1 | 🧠 Understand: turn a request into structured fields |
| 2 | 🗂️ Memory: saved facts, recent turns and compaction |
| 3 | 📚 Knowledge: search and answer from your notes |
| 4 | 🛠️ Hands: calendar, contacts, email, weather and calculator tools |
| 5 | 🔁 Agent loop: plan → act → observe → stop, with approval before sending email |
| 6 | ✅ Proof: run the golden dataset on the real Mini Muse |
| 7 | 🛡️ Reliability: tracing, retries, timeouts and fault injection |
| 8 | 🧩 Assembled: every component in one assistant |

Every week page in the app has a **🧩 Build Mini Muse** part next to the concept demo. From Week 5, teams build their own projects with Mini Muse as the reference implementation.

## Week 1 — LLM Fundamentals

📘 Concepts: [LLM concepts](week-01-llm-fundamentals/concepts.md) · Lab: [Build your first LLM application](week-01-llm-fundamentals/lab.md) · [Extension: web demo](week-01-llm-fundamentals/lab-web-demo.md) · Handout: [Mini Muse, the course project](week-01-llm-fundamentals/handout-mini-muse.md)

🧩 Mini Muse: 🧠 Understand: turn a request into structured fields · [guide](mini-muse.md#week-1---understand--structured-output)

**Question:** What actually happens when an application calls an LLM?

Learn API requests/responses, tokens and context windows, system/user messages, structured output, model parameters, latency and cost.

**Recommended:**

1. [OpenAI API documentation](https://platform.openai.com/docs/overview)
2. [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
3. [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
4. [3Blue1Brown](https://www.youtube.com/watch?v=aircAruvnKk)

---

**Build:** A Python/JavaScript/TypeScript application that takes user input, calls an LLM and returns a predefined structured object — make the demo website publicly accessible.

- Vercel — [https://vercel.com/login](https://vercel.com/login), host JavaScript app
- Supabase — [https://supabase.com/dashboard/sign-in](https://supabase.com/dashboard/sign-in), database
- Streamlit — [https://streamlit.io/](https://streamlit.io/), host Python app
- GitHub — [https://github.com/](https://github.com/), host your source code

**Demos:**

Ling — [https://my-llm-playground-bvapyfhmkp7xn5ji9raank.streamlit.app/](https://my-llm-playground-bvapyfhmkp7xn5ji9raank.streamlit.app/)

Also think about your **8-week project** now and create the first version of its architecture diagram.

**Q&A:**

1. What are the benefits of structured outputs? Give one real-world scenario where structured output is needed.
2. Why are output tokens typically more expensive than input tokens?
3. What is the typical latency of an LLM API call, and what factors affect it?

**Agenda (90 minutes):**

1. Member Introductions (30 min): Get to know each other and share learning goals.
2. 8-Week Program Overview (30 min): Review the learning plan, organization, and project expectations.
3. Week 1 Demo Walkthrough (30 min): Walk through the LLM Playground demo together and discuss key concepts.

## Week 2 — Context Engineering

📘 Concepts: [Context engineering](week-02-context-engineering/concepts.md) · Lab: [From single-call context to multi-run AI systems](week-02-context-engineering/lab.md)

🧩 Mini Muse: 🗂️ Memory: saved facts, recent turns and compaction · [guide](mini-muse.md#week-2---memory--context-engineering)

**Question:** How does an AI system decide what the model needs to know?

Learn prompt vs context, conversation history, context construction, context-window limitations, state vs context, short/long-term memory and summarization/compaction.

**Recommended:**

1. [OpenAI — Conversation state](https://developers.openai.com/api/docs/guides/conversation-state?api-mode=responses)
2. [Anthropic — Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
3. [Anthropic — Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

**Build:** Add conversation history, a context builder and persistent application state.

Update your architecture diagram with **context + state**.

**Q&A:**

1. What is the difference between prompt engineering and context engineering?
2. Does an LLM remember information between independent API calls? How can we maintain conversation continuity?
3. What techniques can we use when conversation history exceeds the context window? What are the trade-offs?

**Agenda (90 minutes):**

1. Week 1 Recap (30 min): Share learning experiences, discuss challenges, and address questions.
2. Week 2 Brainstorming (30 min): Explore context engineering concepts, discuss key questions, and brainstorm practical applications.
3. Week 2 Demo Walkthrough (30 min): Walk through the context engineering demos, compare different strategies, and discuss evaluation metrics.

---

## Week 3 — RAG

📘 Concepts: [Retrieval-augmented generation](week-03-rag/concepts.md) · Lab: [Build a RAG system from scratch](week-03-rag/lab.md)

🧩 Mini Muse: 📚 Knowledge: search and answer from your notes · [guide](mini-muse.md#week-3---knowledge--rag-over-your-notes)

**Question:** How does the system give the LLM information it doesn't already have?

Learn embeddings, chunking, vector databases, similarity search, top-K retrieval, metadata filtering, grounding, retrieval quality and hallucination.

**Required:** [Anthropic — Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

**Recommended:** [DeepLearning.AI — Building and Evaluating Advanced RAG](https://www.deeplearning.ai/alpha/short-courses/building-evaluating-advanced-rag)

**Build:**

```text
Documents
   ↓
Chunking
   ↓
Embeddings
   ↓
Vector DB
   ↓
Retrieval
   ↓
Context Builder
   ↓
LLM
```

Use a small real dataset rather than a tutorial dataset if possible.

**Dataset:** HotpotQA — ask AI to download the dataset.

**Takeaways:**

1. **If the initial retrieval appears incomplete, use hybrid search** — combine **semantic/vector search** with **keyword/BM25 search**, then merge and rerank the results.

**Agenda:**

1. 30 min — review context engineering demo
2. 30 min — walk through RAG knowledge base
3. 30 min — walk through RAG demo

---

## Week 4 — Tool Calling + Catch-up

📘 Concepts: [Tool calling](week-04-tool-calling/concepts.md) · [MCP](week-04-tool-calling/concepts-mcp.md) · Lab: [Weather assistant with tool calling & MCP](week-04-tool-calling/lab.md)

🧩 Mini Muse: 🛠️ Hands: calendar, contacts, email, weather and calculator tools · [guide](mini-muse.md#week-4---hands--tool-calling)

This is intentionally a **lighter week**.

**Question:** How can an LLM interact with external systems?

Learn function/tool calling, tool schemas, API integration, validation, tool results and error handling.

**Required:** [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)

**Recommended:** [Anthropic — Writing Effective Tools for AI Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) and [OpenAI — A Practical Guide to Building Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/). Also: [Model Context Protocol — Getting started](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro).

**Build:** Give your application 2–3 real tools.

For example:

```text
search_documents()
get_product_metrics()
create_task()
```

Use remaining time to catch up on Weeks 1–3.

**Agenda:**

1. **30 min — Tool Calling + MCP:** concepts, architecture, and a short demo
2. **30 min — Agent Engineering Interview Questions:** review and discuss real-world interview questions from AI companies
3. **30 min — Final Project Planning & Team Formation:** discuss project ideas, select projects, and form teams

---

## Week 5 — Agent Engineering

📘 Concepts: [State, workflow, control loop, routing](week-05-agent-engineering/concepts.md) · Lab: [Stateful agent workflow in TypeScript](week-05-agent-engineering/lab.md)

🧩 Mini Muse: 🔁 Agent loop: plan → act → observe → stop, with approval before sending email · [guide](mini-muse.md#week-5---agent-loop--agent-engineering)

Now—and only now—introduce an agent framework.

**Question:** What turns an LLM application into an agent?

Learn goal, state, action, observation, tool selection, control loops, termination conditions, routing, workflow vs agent and orchestration.

**Required:** [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)

**Recommended / hands-on:** [LangGraph Academy — Introduction to LangGraph](https://academy.langchain.com/courses/intro-to-langgraph) and [OpenAI — A Practical Guide to Building Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/).

The mental model should now become:

```text
Goal
 ↓
Observe
 ↓
Decide
 ↓
Action / Tool
 ↓
Update State
 ↓
Goal completed?
 ↙          ↘
No          Yes
↓            ↓
LOOP        STOP
```

**Build:** Convert your existing application into an agent with a clearly defined control loop and termination condition.

Don't build multi-agent systems unless your use case genuinely needs them.

Demo link: [AI Web Page Builder](https://myagentstarter.vercel.app/)

**Agenda:**

1. 30 min — walk through agent demo
2. 30 min — go over concept/code
3. 30 min — discuss teams/agent projects/open issues

---

## Week 6 — Evals

📘 Concepts: [Agent evaluation fundamentals](week-06-evals/concepts.md) · [Public benchmarks](week-06-evals/concepts-benchmarks.md) · Lab: [Evaluate and regression-test an agent](week-06-evals/lab.md)

🧩 Mini Muse: ✅ Proof: run the golden dataset on the real Mini Muse · [guide](mini-muse.md#week-6---proof--evals)

**Question:** How do we know the AI system actually works?

Learn evaluation datasets, expected behavior, task completion, retrieval evaluation, tool-selection evaluation, trajectory evaluation, LLM-as-a-judge and regression testing.

**Required:** [DeepLearning.AI — Evaluating AI Agents](https://www.deeplearning.ai/courses/evaluating-ai-agents)

**Recommended:** [OpenAI Evals documentation](https://platform.openai.com/docs/guides/evals)

**Build:** Create a **20–30 case golden dataset** and an automated evaluation pipeline.

The key mindset change is:

```text
"It looks good when I try it."
            ↓
"We have evidence that it works."
```

---

## Week 7 — Production AI Systems

📘 Concepts and lab: not written yet.

🧩 Mini Muse: 🛡️ Reliability: tracing, retries, timeouts and fault injection · [guide](mini-muse.md#week-7---reliability--production)

**Question:** What happens when the demo meets real users?

Learn tracing, logging, observability, token usage, latency, cost, timeout, retries, fallbacks, rate limits, malformed output, tool failure, infinite loops and human approval.

**Required:** Revisit the tracing/monitoring sections of [DeepLearning.AI — Evaluating AI Agents](https://www.deeplearning.ai/courses/evaluating-ai-agents).

**Recommended:** [Anthropic — Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

**Build:** Add tracing plus at least three failure-handling mechanisms—for example timeout, retry and maximum agent-loop count.

Update the architecture with the **production layer**.

---

## Week 8 — AI System Design + Demo

📘 Concepts and lab: not written yet.

🧩 Mini Muse: 🧩 Assembled: every component in one assistant · [guide](mini-muse.md#week-8---assembled--system-design)

There should be **very little new coding this week**.

The project has already been built progressively during Weeks 1–7. Week 8 is about stepping back and reasoning about the complete system.

Each participant should be able to explain:

```text
                 User
                   ↓
             Application/API
                   ↓
              Agent Runtime
             ↙     ↓      ↘
           LLM    RAG     Tools
                   ↓
              State/Memory
                   ↓
          Guardrails / Human
                   ↓
                Output

                   ↓
          Observability/Tracing
                   ↓
                 Evals
```

Final review should answer: **What is deterministic vs probabilistic? What goes into context? Where does state live? Why is RAG needed? What tools are available? What controls the loop and stops it? How is quality measured? What happens when something fails? Where should a human intervene? What are the cost/latency/reliability trade-offs?**

**Final deliverables:** working demo, architecture diagram, 5–10 minute system-design presentation, evaluation results, and peer review.
