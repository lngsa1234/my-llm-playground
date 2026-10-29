# Agent Engineering Peer Learning Circle — Program Guide

A hands-on program for learning AI engineering foundations. The program ends with building and validating an AI assistant.

**Course repository:** [lngsa1234/my-llm-playground](https://github.com/lngsa1234/my-llm-playground)

## Who this course is for

This course is for anyone looking to systematically learn AI agent concepts, architecture, and engineering practices.

- **Product managers and technical PMs** who want enough technical depth to scope AI features, define quality bars, and make informed trade-offs.
- **Software, systems, data, and ML practitioners** who want stronger product judgment and hands-on agent-building experience.
- **Career switchers into AI product or agent engineering** who want a concrete portfolio project rather than theory alone.

## What you will learn

1. **Understand AI agents** — prompts, context, retrieval, tools, memory, and state.
2. **Build an AI assistant** — connect knowledge, tools, and workflows into one working system.
3. **Evaluate and improve quality** — use test cases, observable outcomes, and regression checks.

**Build stack:** Python, JavaScript, or TypeScript with an LLM API.

**Time commitment:** about 3–4 hours per week.

## How this program is organized

Each weekly session has three parts:

1. **20 minutes — Learn the essential concept.**
2. **30 minutes — Walk through the lab and Mini Muse demo.**
3. **25 minutes — Open discussion.**

## Learning modules roadmap

> **Note:** This guide includes eight learning modules, delivered across six calendar weeks. Some modules are combined within the same weekly session.

| Week | Topic | Key idea | Basic knowledge points |
| --- | --- | --- | --- |
| 1 | LLM Fundamentals | How an application sends and receives model requests. | Tokens, prompts, context window, structured output |
| 2 | Context Engineering | How to select the right information for each model call. | Instructions, history, state, memory, compaction |
| 3 | RAG | How to retrieve evidence before the model answers. | Chunks, embeddings, search, grounding, citations |
| 4 | Tool Calling + MCP | How an AI system can safely use external tools and data. | Tool schemas, validation, APIs, MCP, approval |
| 5 | Agent Engineering | How state, workflows, and control loops enable multi-step work. | Routing, state, control loop, termination, orchestration |
| 6 | Evals | How to measure outcomes, tool behavior, and regressions. | Golden dataset, task success, graders, regression tests |
| 7 | Production Reliability | How to trace, recover, and operate an AI system safely. | Traces, retries, timeouts, fallback, cost and latency |
| 8 | Mini Muse Demo | How the complete assistant fits together. | Architecture, system boundaries, safety, trade-offs |

For each week, use the matching **Knowledge Base** guide, lab, and quiz in the sidebar. The table is the single program overview; the weekly materials contain the details.

## Course project: Mini Muse

**Mini Muse repository:** [lngsa1234/mini-muse-project](https://github.com/lngsa1234/mini-muse-project)

Choose one of two project scopes. Both apply the course concepts; Option 1 is intentionally the simpler starting point.

### Option 1: Mini Muse Demo

Build a **single-task assistant** that does one useful job well. Choose a focused task—such as answering questions from a small set of notes, drafting an email, planning a trip, or helping with a specific workflow—and clearly define what it can and cannot do.

Your demo should include:

- A chat-style input and a useful assistant response.
- A focused task, clear instructions, and an example user workflow.
- At least one course concept applied to the task, such as structured output, memory, retrieval, tool calling, or an evaluation.
- A short demo showing the task working and at least one limitation or safety boundary.

### Option 2: Mini Muse MVP

Build a **minimum viable product**: a small personal-assistant experience with connected features rather than a single task. The MVP includes:

- **Chat** — a conversational home for interacting with Mini Muse.
- **Ideas** — capture, organize, and develop ideas with the assistant.
- **Goals** — create, review, and make progress on goals.
- **Library** — save and retrieve notes, resources, and other useful reference material.

The features should work together where practical—for example, chat can help turn an idea into a goal or answer a question using material from the library. Define a small, testable scope for each feature and demonstrate the user journey end to end.

Open **Week 8 · Mini Muse Demo** in the sidebar to explore the course reference implementation.

## Communication

- [Download the CircleW iOS app](https://apps.apple.com/us/app/circlew/id6780248349) to receive real-time notifications.
