"""Mini Muse: the personal-assistant agent the circle builds across the 8 weeks.

Each week adds one component, in its own module:

    week1_understand.py   Understanding  structured output turns a request into fields
    week2_memory.py       Memory         conversation history, saved preferences, compaction
    week3_knowledge.py    Knowledge      search and answer from your own notes (RAG)
    week4_tools.py        Hands          calendar, contacts, email, weather, calculator tools
    week5_agent.py        Agent loop     plan → act → observe → stop, with approval before risky actions
    week6_eval.py         Proof          the Week 6 golden dataset, run against the real agent
    week7_reliability.py  Reliability    tracing, retries, timeouts, fault injection
    week8_assistant.py    Assembly       every component wired into one assistant

Shared pieces:

    world.py   the fake world the tools act on (calendar, contacts, notes, weather);
               nothing real is ever booked or sent
    llm.py     a thin OpenAI wrapper that counts tokens and cost
    page.py    the Streamlit screens, used by the week pages and the Mini Muse page
"""
