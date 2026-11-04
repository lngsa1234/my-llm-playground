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

The program is built around three steps: **learn, practice, build**.

- **Learn** — each week covers one topic from the Knowledge Base.
- **Practice** — a small lab for the week's concept, plus that week's step of the Mini Muse reference project.
- **Build** — by the end of the program, everyone builds their own agent project.

### Weekly session (75 minutes)

Lynn shares what she learned that week, then the group practices and discusses together.

| Time | Part | What happens |
| --- | --- | --- |
| 20 min | **Learn** | Lynn walks through the week's Knowledge Base topic: the key concepts and why they matter. |
| 25 min | **Practice** | Hands-on with the week's small lab, then the matching Mini Muse step to see the concept inside a real agent. |
| 30 min | **Open discussion** | Members share their own learning and practice: what they tried, what worked, what surprised them, and questions for the group. |

Each session needs **1–2 volunteers** to help facilitate the open discussion.

### Final project

By the end of the program, **each member builds one agent project**. Choose one of three:

1. **A simple, task-based personal assistant** — one focused job done well.
2. **A Mini Muse project** — your own version of Mini Muse, or a feature of the Mini Muse MVP.
3. **Your own project** — any AI or agent project you want, applying the course concepts.

The [Course project](#course-project-mini-muse) section below describes the options in detail.

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

Choose one of three project scopes. All apply the course concepts; Option 1 is intentionally the simpler starting point.

### Option 1: Mini Muse Task Assistant

Build a **task assistant** that does one useful job well. Choose a focused task—such as answering questions from a small set of notes, drafting an email, planning a trip, or helping with a specific workflow—and clearly define what it can and cannot do.

**Project location:** embedded in the [lngsa1234/my-llm-playground](https://github.com/lngsa1234/my-llm-playground) course repository.

Complete Option 1 **by yourself** from start to finish.

Your demo should include:

- A chat-style input and a useful assistant response.
- A focused task, clear instructions, and an example user workflow.
- At least one course concept applied to the task, such as structured output, memory, retrieval, tool calling, or an evaluation.
- A short demo showing the task working and at least one limitation or safety boundary.

### Option 2: Mini Muse MVP

Build a **minimum viable product**: a small personal-assistant experience with connected features rather than a single task. The MVP includes:

**Project repository:** [lngsa1234/mini-muse-mvp](https://github.com/lngsa1234/mini-muse-mvp)

- **Chat** — a conversational home for interacting with Mini Muse.
- **Ideas** — capture, organize, and develop ideas with the assistant.
- **Goals** — create, review, and make progress on goals.
- **Library** — save and retrieve notes, resources, and other useful reference material.

The features should work together where practical—for example, chat can help turn an idea into a goal or answer a question using material from the library. Define a small, testable scope for each feature and demonstrate the user journey end to end.

You may build Option 2 on your own or with others. In a team, each person can focus on one feature or one part of the product.

### Option 3: Your Own Project

Build any AI or agent project you want. Choose a problem, audience, and scope that interest you, then apply relevant course concepts such as prompts, context, retrieval, tools, workflows, evaluation, or reliability. You may work independently or with others.

## Communication

- **Weekly virtual meeting:** we recommend joining on the web at [www.circlew.app](https://www.circlew.app).
- [Download the CircleW iOS app](https://apps.apple.com/us/app/circlew/id6780248349) to receive real-time notifications.
- **Questions:** send them in the group chat on the circle's page in CircleW.

## Appendix: Run your own weekly Mini Muse demo

The [hosted app](https://my-llm-playground-bvapyfhmkp7xn5ji9raank.streamlit.app/) runs on the organizer's API key. To experiment freely, change the code, and run the demo at your own pace, run **your own copy** with **your own OpenAI API key**. Set it up once, then follow the weekly routine.

### One-time setup

**1. Get an OpenAI API key.**

- Sign in at [platform.openai.com](https://platform.openai.com/), add a small amount of credit, and create a key under **API keys**.
- Treat the key like a password. Never paste it into a file you commit, a chat, or a screenshot.
- The app shows tokens and estimated cost for every call. Set a monthly budget limit in your OpenAI account so spending can't surprise you.

**2. Fork the course repository.**

1. Sign in to [GitHub](https://github.com/) (create a free account if you don't have one).
2. Open [lngsa1234/my-llm-playground](https://github.com/lngsa1234/my-llm-playground).
3. Click **Fork** (top right), keep the default name, and click **Create fork**.

You now have `https://github.com/<your-username>/my-llm-playground`, your own copy that you can change without affecting anyone else.

**3. Choose how to run your fork.** Pick one option.

| Option | Best for | What you need |
| --- | --- | --- |
| **A. GitHub Codespaces** | No installs; runs in the browser | A GitHub account |
| **B. On your computer** | Editing code in your own editor | Python 3.11+ and Git |
| **C. Streamlit Community Cloud** | A permanent link you can share in your demo | A free Streamlit account |

**Option A — GitHub Codespaces (easiest)**

1. In your fork, click **Code → Codespaces → Create codespace on main**.
2. Add your key as a Codespaces secret: GitHub **Settings → Codespaces → Secrets → New secret**, name `OPENAI_API_KEY`, paste your key, and give it access to your `my-llm-playground` fork. Then restart the codespace.
3. The repository is set up to install everything and start the app automatically. When the preview opens on port 8501, you're running Mini Muse.
4. If the app doesn't start, run this in the codespace terminal:

   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

Stop the codespace when you're done (**Code → Codespaces → … → Stop**) to save free hours.

**Option B — on your computer**

```bash
git clone https://github.com/<your-username>/my-llm-playground.git
cd my-llm-playground
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Open `.env`, set `OPENAI_API_KEY=` to your key, and save. `.env` is ignored by Git, so your key is never committed. Then start the app:

```bash
streamlit run app.py
```

The app opens at <http://localhost:8501>.

**Option C — Streamlit Community Cloud**

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) with GitHub.
2. Click **Create app**, choose your fork, branch `main`, and main file `app.py`.
3. Open **Advanced settings → Secrets** and add:

   ```toml
   OPENAI_API_KEY = "your-api-key"
   ```

4. Click **Deploy**. You get your own public link. Anyone with the link spends your API credit, so share it only with the circle.

**4. Check it works.**

- The sidebar should **not** show the missing-API-key note.
- Open **Week 1 → 🧩 Build Mini Muse**, enter `Book lunch with Maya on Tuesday at noon`, and run it. You should see structured fields such as `intent`, `date` and `time`.

### Weekly routine (about 30 minutes)

Do this before or after each weekly session.

**1. Sync your fork with the latest course material.** New weeks and fixes land in the course repository during the program.

- On GitHub: open your fork and click **Sync fork → Update branch**.
- Then pull the update where you run the app:
  - Codespaces or your computer: `git pull`, then `pip install -r requirements.txt` in case dependencies changed.
  - Streamlit Cloud: redeploys automatically after the sync.

If GitHub reports a conflict, you changed a file that the course also changed. Keep your own experiments in new files, or ask the group for help.

**2. Learn the concept.** Read the week's guide in **📚 Knowledge Base** and try the **🔬 Concept demo** on the week's page.

**3. Run the week's Mini Muse step.** On the week's page, switch to **🧩 Build Mini Muse**. Work through the week's **Try** list and **Check yourself** questions in the [Mini Muse guide](mini-muse.md).

| Week | Mini Muse step | Command-line version (optional) |
| --- | --- | --- |
| 1 | 🧠 Understand | `python3 -m mini_muse.week1_understand "Book lunch with Maya Tuesday at noon"` |
| 2 | 🗂️ Memory | `python3 -m mini_muse.week2_memory` (chat; type `quit` to exit) |
| 3 | 📚 Knowledge (RAG) | `python3 -m mini_muse.week3_knowledge "What did Jordan say about the offsite budget?"` |
| 4 | 🛠️ Tools | `python3 -m mini_muse.week4_tools "What's the weather in Detroit?"` |
| 5 | 🔁 Agent loop | `python3 -m mini_muse.week5_agent "Book a haircut on 2026-10-27 at 14:00"` |
| 6 | ✅ Evals | in the app only: Week 6 → 🧩 Build Mini Muse |
| 7 | 🛡️ Reliability | in the app only: Week 7 → 🧩 Build Mini Muse |
| 8 | 🧩 Assembled | sidebar **🧩 Mini Muse · all weeks → Week 8**, or `python3 -m mini_muse` |

All tools act on a fake world (calendar, contacts Maya and Jordan, outbox, weather, five notes), so nothing is ever really booked or sent.

**4. Make one change of your own.** This is where the learning sticks. Examples: reword an instruction, add a field to the Week 1 output, add a note to `mini_muse/data/notes/`, or add a tool in Week 4. Run the demo again and compare. To check you didn't break anything:

```bash
pytest mini_muse        # runs offline with a fake model, so it costs nothing
```

Commit and push your change to your fork:

```bash
git add -A
git commit -m "Week N: <what you tried>"
git push
```

**5. Prepare to share.** Bring one thing to the open discussion: what you tried, what you expected, what actually happened, and one question. A screenshot or a two-minute live demo from your own copy is ideal.

### Troubleshooting

- **"OPENAI_API_KEY is not set"** — check the key's name is exactly `OPENAI_API_KEY`. In Codespaces, restart the codespace after adding the secret. Locally, check `.env` is in the repository's top folder.
- **`401` or `insufficient_quota` errors** — the key is wrong, revoked, or the account has no credit.
- **`ModuleNotFoundError`** — run `pip install -r requirements.txt` again, inside your virtual environment.
- **Answers vary between runs** — that's expected; models are probabilistic. Week 6 shows how to measure it.
- **You accidentally committed your key** — revoke it immediately at [platform.openai.com/api-keys](https://platform.openai.com/api-keys) and create a new one. Deleting the commit is not enough.
