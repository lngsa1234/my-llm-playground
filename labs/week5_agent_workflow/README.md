# Week 5 · Agent Workflow

A stateful workflow agent with a bounded control loop. It is the Python version of the architecture in the [Week 5 TypeScript lab](../../knowledge_base/week-05-agent-engineering/lab.md), applied to a writing task so that no generated code is ever executed.

```text
request → TRIAGE → REQUIREMENTS → PLANNING → DRAFTING → QA → COMPLETE
             │                                   ▲       │
             └──────────► FAILED ◄─ budget used ─┴─ fail ┘   (repair: back to DRAFTING)
```

| Concept | Question it answers | In `workflow_agent.py` |
| --- | --- | --- |
| State | What does the agent know? | `AgentState` |
| Workflow | Which moves are legal? | `TRANSITIONS`, `can_transition` |
| Actions | What work happens in this stage? | `act_triage` … `act_qa` |
| Router | What runs next, and why? | `route` (code), `llm_route` (experiment) |
| Control loop | Run, observe, update, route, validate, repeat, stop | `run_agent` |

QA runs a deterministic check first (word limit, required phrases). It calls the model only when that check passes, so a draft that is obviously wrong costs nothing to reject.

## Run

```bash
streamlit run labs/week5_agent_workflow/page.py       # this page alone (or pick Week 5 in app.py)
python labs/week5_agent_workflow/workflow_agent.py "Write a 50-word note that mentions Mini Muse"
pytest labs/week5_agent_workflow                      # offline, with a scripted fake model
```

## Experiments (🧪 Lab parameters)

- **B · LLM decides:** the model picks the next stage. The workflow still rejects an illegal move. Compare the reasons in the trace with the code router's.
- **C · Make QA always fail:** watch the repair budget end the run as `failed`, with the last feedback as the reason.
- **Max steps:** set it below the number of stages and see the step limit stop the run.

The page's **🧩 Build Mini Muse** part shows the same ideas in Mini Muse's agent loop. There, the "stages" are tool calls, and the risky action (sending email) waits for your approval.
