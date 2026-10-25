# Mini Muse

The personal-assistant agent the circle builds across the 8 weeks: one component per week, all wired together by Week 8. The full week-by-week guide is in [`knowledge_base/mini-muse.md`](../knowledge_base/mini-muse.md).

| Week | Component | File | Run alone |
| --- | --- | --- | --- |
| 1 | 🧠 Understand: structured output | `week1_understand.py` | `python -m mini_muse.week1_understand "Book lunch with Maya Tuesday at noon"` |
| 2 | 🗂️ Memory: facts, history, compaction | `week2_memory.py` | `python -m mini_muse.week2_memory` (chat loop) |
| 3 | 📚 Knowledge: RAG over your notes | `week3_knowledge.py` | `python -m mini_muse.week3_knowledge "What did Jordan say about the offsite budget?"` |
| 4 | 🛠️ Hands: tools, one round | `week4_tools.py` | `python -m mini_muse.week4_tools "What's the weather in Detroit?"` |
| 5 | 🔁 Agent loop with approval | `week5_agent.py` | `python -m mini_muse.week5_agent "Book a haircut on 2026-10-27 at 14:00"` |
| 6 | ✅ Golden dataset on the real agent | `week6_eval.py` | in the app: Week 6 → 🧩 Build Mini Muse |
| 7 | 🛡️ Tracing, retries, timeouts, faults | `week7_reliability.py` | in the app: Week 7 → 🧩 Build Mini Muse |
| 8 | 🧩 Everything assembled | `week8_assistant.py` | `python -m mini_muse` (chat loop) |

Shared files:

- `world.py` holds the fake calendar, contacts, outbox and weather. It matches the Week 6 golden dataset, and nothing real is ever booked or sent.
- `data/notes/` holds five sample personal notes for Week 3.
- `llm.py` is a thin OpenAI wrapper that counts calls, tokens and cost.
- `page.py` holds the Streamlit screens. `streamlit run mini_muse/page.py` opens them on their own; in the full site they appear under each week as **🧩 Build Mini Muse** and in the sidebar as **🧩 Mini Muse · all weeks** (the only place for Week 8).

Command-line runs need `OPENAI_API_KEY` in `.env`. `OPENAI_MODEL` changes the model; it defaults to `gpt-5.4-mini`.

```bash
pytest mini_muse     # offline: a scripted fake model stands in for the API
```
