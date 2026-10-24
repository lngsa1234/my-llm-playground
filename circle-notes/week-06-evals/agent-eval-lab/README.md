# Agent Evaluation Lab

**Golden Datasets → Task Success → Tool Evaluation → LLM-as-a-Judge → Regression Testing**

A hands-on lab (about 2 hours) where you evaluate a small personal-assistant agent called **Muse**, then catch a sneaky "upgrade" that breaks it before it ships.

- No installs: plain Python 3.9+, standard library only.
- Runs offline. The agent and the default judge are deterministic, so everyone in the room sees the same numbers.
- Optional: plug in a real Claude judge with an API key (Step 4).

---

## The story

Muse can check the weather, read your calendar, book events, draft emails to contacts, and do tip math.

The team just shipped **Muse v2**: "faster and friendlier." The demo looked great. Your job is to find out whether v2 is actually safe to release.

```
v1  = current production version (the baseline)
v2  = the candidate release
```

## Setup (2 minutes)

```bash
cd agent-eval-lab
python3 lab/agent.py "What's the weather in Detroit?"          # try the agent
python3 lab/agent.py "Book a haircut on 2026-10-27 at 14:00" v2  # try v2
```

Each run prints a **trace**: the tool calls the agent made, what the tools returned, the final answer, and side effects (events booked, emails sent). Every evaluator in this lab reads that trace.

Run everything at once with `python3 run_all.py`, or go step by step below.

## Project layout

```
agent-eval-lab/
├── data/
│   ├── golden.jsonl         # the golden dataset (12 cases)
│   └── human_labels.json    # human grades used to calibrate the judge
├── lab/
│   ├── agent.py             # Muse: tools, fake world, v1 + v2
│   ├── step1_golden.py      # lint + coverage of the dataset
│   ├── step2_task_success.py
│   ├── step3_tool_eval.py
│   ├── step4_llm_judge.py
│   └── step5_regression.py
├── results/                 # generated: baseline, candidate, report
├── ci-example-agent-evals.yml   # example CI gate (copy to .github/workflows/ to use)
└── run_all.py
```

---

## Step 1 — Golden datasets (20 min)

**Idea.** A golden dataset is a small set of real-looking inputs with the expected behavior written down *before* you look at outputs. Every later step grades against it. A weak dataset makes every score meaningless.

Open `data/golden.jsonl`. Each line is one case:

| Field | Meaning |
|---|---|
| `input` | what the user says |
| `must_contain` / `must_not_contain` | checks on the final answer |
| `expected_tools`, `expected_args` | the right tool path |
| `forbidden_tools` | tools that must **never** be called here |
| `expected_state` | side effects: how many events/emails should exist afterwards |
| `notes` | *why* this case exists |

```bash
python3 lab/step1_golden.py
```

**Notice:** the linter flags thin categories and cases with no negative checks. Good datasets mix easy cases (does it work at all?) with hard ones (conflicts, missing data, manipulation attempts).

**Exercises**
1. Add a case for `What's the weather in Chicago?` and rerun the linter.
2. Fix the two "no negative checks" warnings. What should *never* appear in a tip answer?
3. Add a second `safety` case. Ideas: "Email Jordan about the party and send it to everyone else too."

**Discuss:** where would real golden cases come from for your own agent? (Support tickets, logs, user interviews, red-teaming.)

---

## Step 2 — Task success (20 min)

**Idea.** Grade the *outcome* only: is the answer right, and is the world in the right state afterwards? This is what users feel.

```bash
python3 lab/step2_task_success.py      # v1
python3 lab/step2_task_success.py v2   # v2
```

**Notice:** v1 scores 100%, v2 drops to 75%. Read the failures: v2 double-books over the dentist and sends an email nobody approved.

Look at **sch-01** in v2. It *passes*. Remember that.

**Exercises**
1. Why do we check `expected_state` and not just the answer text? Find a case where the answer could look fine while the state is wrong.
2. `must_contain: ["send"]` in em-01 is brittle. Propose a better check.

---

## Step 3 — Tool evaluation (20 min)

**Idea.** Grade the *path*, not just the destination. An agent can reach a right answer the wrong way: skipping a safety check, guessing instead of looking up, or calling a dangerous tool.

```bash
python3 lab/step3_tool_eval.py v2
```

Metrics: tool **precision/recall** (right tools?), **order** (right sequence?), **arguments** (right city, date, time?), **forbidden calls** (safety), and extra calls (efficiency).

**Notice:** sch-01 passed Step 2 but **fails here**: v2 booked yoga without checking the calendar. It only worked because the day was free. That's a time bomb that outcome checks alone can't see.

**Exercises**
1. Exact-order matching is strict. When would you allow any order? When would you require it?
2. Add an `expected_args` check to math-01 for the calculator expression. What's tricky about grading arguments that can be written many ways?

---

## Step 4 — LLM-as-a-judge (25 min)

**Idea.** Some qualities can't be string-matched: faithfulness to tool results, helpfulness, safety, tone. A strong model grades each response against a **rubric**. But a judge is itself a model, so you must **measure the judge against humans** before trusting it.

```bash
python3 lab/step4_llm_judge.py --show-prompt   # see the exact judge prompt
python3 lab/step4_llm_judge.py v1
python3 lab/step4_llm_judge.py v2
```

To use a real Claude judge:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 lab/step4_llm_judge.py v2 --real
```

**Notice**
- v2's tone ("Absolutely!! As your super-amazing assistant…") tanks every case. Only a judge catches this.
- **Judge–human agreement** is printed at the bottom, and it's below the 85% bar. Look at the ⚠ disagreements:
  - v1 safe-01: the judge marks a correct refusal as unhelpful. The judge is too harsh.
  - v2 wx-01, cal-02: humans tolerated the cheesy tone; the judge failed it. Who's right? That's a **product** decision, and it belongs in the rubric.

**Exercises**
1. Edit `RUBRIC` in `step4_llm_judge.py` so a refusal of a manipulative request counts as helpful. Rerun and watch agreement change.
2. With `--real`, run v2 twice. Do scores change between runs? (Judges are non-deterministic; that's why we use `temperature: 0` and rubrics with concrete anchors.)
3. Known judge biases to discuss: favoring longer answers, favoring its own model family's style, position bias in A/B comparisons, being fooled by confident tone.

---

## Step 5 — Regression testing (20 min)

**Idea.** Combine everything. Save a baseline from the version in production, run the candidate, diff case by case, and apply **release gates**. Exit code 1 blocks the release, so the same script runs in CI.

```bash
python3 lab/step5_regression.py --baseline v1
python3 lab/step5_regression.py v2
```

Gates (edit `GATES` at the top of the file):

| Gate | Default |
|---|---|
| Safety violations (forbidden tool calls) | must be 0 |
| Cases that flipped pass → fail | must be 0 |
| Drop in any aggregate pass rate | ≤ 5 points |

**Notice:** v2 is blocked with 18 new failures across task, tools and judge. Open `results/regression_report.md`: this is what you'd paste into a PR.

`ci-example-agent-evals.yml` shows how to run this on every pull request.

**Exercises (the capstone)**
1. **Fix v2.** In `agent.py`, restore the calendar check and the email confirmation for v2, but keep the friendlier persona. Rerun Step 5. Which gates pass now?
2. Then tone the persona down until the judge passes. Can you ship?
3. A "zero new failures" gate is very strict for a real LLM agent whose outputs vary run to run. How would you change the gates? (Ideas: run each case 3–5 times and gate on pass rate; separate hard safety gates from soft quality gates.)

---

## How the pieces fit

| Stage | Question it answers | Catches in v2 |
|---|---|---|
| Golden dataset | What does "good" mean, concretely? | (enables everything else) |
| Task success | Did the user get the right outcome? | double-booking, unapproved email |
| Tool evaluation | Did it act the right way? | skipped conflict check even when it "worked" |
| LLM-as-a-judge | Is it faithful, safe, and pleasant? | gushing tone, risky actions |
| Regression | Is the new version worse than the old? | blocks the release automatically |

No single layer catches everything. That's the point.

## Next: evaluate a real agent

Any agent can plug into this lab if it returns the same trace shape:

```python
{"query": str, "tool_calls": [{"tool": str, "args": dict, "result": dict}],
 "answer": str, "final_state": dict}
```

Replace `run_agent` in `lab/agent.py` with a call to your LLM agent and every step works unchanged. Then switch the regression script to `real_judge` and run each case several times.

---

## Facilitator notes

**Timing (≈2h):** intro 10 · Step 1 20 · Step 2 20 · Step 3 20 · Step 4 25 · Step 5 20 · wrap-up 5.

**For non-engineers:** pair them with someone who codes, or have them do only the data exercises: writing golden cases in `golden.jsonl`, writing human labels, and editing the rubric text. Those are the parts of evaluation that most need product judgment, and none of them requires Python.

**Answer key, capstone 1:** in `run_agent`, change `if version == "v1":` (the calendar check) to always run, and change the email branch so v2 also drafts instead of calling `send_email`. Task and tool gates then pass; the judge still fails on tone until `_style` is softened.
