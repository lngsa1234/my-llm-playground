# Week 2 · Context Engineering — Lab: From Single-Call Context to Multi-Run AI Systems

**Tips: This is only for the purpose of reference. Please feel free to make any adjustments or changes for your own demo.**

- **Level:** Beginner → Intermediate → Advanced
- **Language:** Python
- **Model:** OpenAI or Claude API
- **Format:** Hands-on peer learning lab
- **Estimated time:** 3–4 hours for the core lab, plus an optional advanced project

### Lab objectives

By the end of this lab, participants should be able to:

1. Explain how context differs from prompts, conversation history, memory, and application state.
2. Implement and compare multiple context construction strategies.
3. Measure token usage, latency, cost, and response quality.
4. Build an application that maintains context across multiple LLM calls.
5. Use summarization, retrieval, and structured state to manage growing context.
6. Evaluate how different context strategies affect the completion of a multi-step goal.

The lab contains three separate demos that increase in difficulty.

| Demo | Title | Difficulty |
| --- | --- | --- |
| 1 | Context Strategy Benchmark | Beginner |
| 2 | Multi-Run Goal Builder | Intermediate |
| 3 | Multi-Strategy Goal Benchmark | Advanced |

Core principle: Context engineering is the process of selecting, structuring, and managing the information supplied to an AI model so it can perform a task effectively.

# Part 1 — Preparation

## 1.1 Prerequisites

Participants should have completed Week 1 or be familiar with:

- Sending LLM API requests and reading responses.
- System instructions and user messages.
- Structured JSON output.
- Input/output tokens, latency, and API cost.
- Basic Python functions and dictionaries.

No agent framework is required. We will implement the context builder and execution loop ourselves so participants can understand how they work.

## 1.2 Technology stack

| Component | Recommended technology |
| --- | --- |
| User interface | Streamlit |
| LLM client | OpenAI SDK or Anthropic SDK |
| Backend | Python 3.11+ |
| State storage | JSON initially; SQLite optional |
| Retrieval | Keyword search initially; vector search optional |
| Token counting | Provider usage response; tokenizer for pre-call estimates |
| Evaluation | Python assertions and automated tests |
| Visualization | Streamlit charts and tables |

For consistency, choose one model and keep its configuration fixed during each benchmark.

## 1.3 Project structure

Create the following project:

```text
context-engineering-lab/
│
├── app.py
├── requirements.txt
├── .env
├── .env.example
│
├── demos/
│   ├── demo1_benchmark.py
│   ├── demo2_goal_builder.py
│   └── demo3_goal_benchmark.py
│
├── core/
│   ├── llm_client.py
│   ├── context_builder.py
│   ├── state_manager.py
│   ├── retrieval.py
│   ├── evaluator.py
│   └── metrics.py
│
├── data/
│   ├── benchmark_cases.json
│   ├── sample_history.json
│   └── knowledge_base/
│
├── runs/
│
└── tests/
    ├── test_context.py
    └── test_evaluation.py
```

Start with these dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install streamlit openai anthropic \
    python-dotenv pandas tiktoken pytest
```

Create `.env`:

```text
OPENAI_API_KEY=your_api_key
ANTHROPIC_API_KEY=your_api_key
```

Only configure the provider you intend to use. Never commit `.env` or API keys to GitHub.

Run the application with:

```bash
streamlit run app.py
```

The three demos should appear as separate tabs or pages.

# Part 2 — Core Concepts

Before coding, review the following architecture.

> 🖼️ *Diagram: context engineering lab architecture* — [view in Notion](https://app.notion.com/p/3e4dbc95f92c8088864ae0f336d311de)

## 2.1 Terminology

| Concept | Definition |
| --- | --- |
| Prompt | Instructions or content supplied to guide model behavior |
| Context | Information available to the model for a particular call |
| Context window | Model's maximum supported context capacity, subject to model-specific input/output limits |
| Conversation history | Previous messages exchanged between the user and assistant |
| Memory | Information preserved for use across interactions |
| State | Application-maintained data representing current progress, decisions, and status |
| RAG | Retrieval-Augmented Generation: retrieving relevant external information for model input |
| Compaction | Reducing context size while preserving important information |
| Context builder | Application logic that constructs the input for each LLM call |

Important: An LLM API call should not be assumed to remember previous independent calls. Your application must provide the necessary information, whether through explicitly supplied history, provider-supported conversation mechanisms, or retrieved state.

# Part 3 — Demo 1: Context Strategy Benchmark

Required · Beginner · 45–60 minutes

## 3.1 Objective

Build an application that accepts a user instruction and generates responses using different context strategies.

The user should immediately see how the choice of context changes the model's response, token consumption, and latency.

## 3.2 User interface

> 🖼️ *Mockup: Demo 1 user interface* — [view in Notion](https://app.notion.com/p/3e4dbc95f92c8088864ae0f336d311de)

The actual application should include an editable instruction, context-source selector, strategy checkboxes, a Run Benchmark button, and results.

## 3.3 Prepare a sample dataset

Use a synthetic engineering project about a file-processing API.

The project history should contain 20–30 messages, including:

- Initial requirements for uploading and processing files.
- File size and format constraints.
- Authentication requirements.
- An initial processing timeout of 30 seconds.
- A later decision changing the timeout to 60 seconds.
- Technical documentation for storage and processing.
- Several unrelated discussion turns.

Provide an authoritative expected answer containing the final requirements.

Example benchmark instruction:

> Summarize the current requirements for the file-processing API. Identify the active timeout, supported file types, authentication requirements, and unresolved issues.

Participants should also be able to enter their own instruction or upload a document. The supplied dataset makes the first experiment reproducible.

## 3.4 Implement five strategies

| Strategy | Implementation |
| --- | --- |
| S0 — Baseline | Current instruction only |
| S1 — Full history | Current instruction + all history that fits |
| S2 — Sliding window | Current instruction + last K turns |
| S3 — Summary | Current instruction + summary of older turns + recent turns |
| S4 — RAG | Current instruction + top K relevant retrieved passages |

For the first version, use keyword retrieval. Embeddings and vector search are optional.

Make each strategy return both the constructed context and metadata about which source items it included.

```python
def build_context(
    strategy,
    instruction,
    history,
    documents,
    token_budget
):
    # Select relevant information.
    # Apply strategy-specific processing.
    # Enforce token budget.
    # Return context and provenance.
    ...
```

Use the same system instructions and model settings across strategies. If the full-history input exceeds the configured budget, record a budget failure or apply a documented truncation rule.

## 3.5 Execute the benchmark

For each selected strategy:

1. Construct its context.
2. Count or estimate input tokens.
3. Call the LLM.
4. Record the actual API-reported token usage.
5. Measure latency and calculate cost.
6. Evaluate the response against expected facts.
7. Display the answer and metrics.

The basic loop:

```python
results = []

for strategy in selected_strategies:
    context = build_context(
        strategy=strategy,
        instruction=instruction,
        history=history,
        documents=documents,
        token_budget=4000
    )

    response = call_llm(context)

    results.append({
        "strategy": strategy,
        "context": context,
        "response": response,
        "metrics": evaluate(response)
    })
```

Implement `call_llm` and `evaluate` in the shared modules.

## 3.6 Display results

Include a side-by-side response comparison and a metrics table.

| Metric | What to show |
| --- | --- |
| Input tokens | Actual reported usage |
| Output tokens | Actual reported usage |
| Latency | Seconds per request |
| Cost | Estimated USD based on model pricing |
| Required-fact accuracy | Correct expected facts / total expected facts |
| Context inspection | Exact context sent to the model |

Do not invent a quality score for arbitrary user instructions without an evaluation rubric or reference answer.

### Demo 1 acceptance criteria

> 🖼️ *Demo 1 implementation checklist* — [view in Notion](https://app.notion.com/p/3e4dbc95f92c8088864ae0f336d311de)

# Part 4 — Demo 2: Multi-Run Goal Builder

Required · Intermediate · 75–90 minutes

## 4.1 Objective

Build an application that takes a user-defined goal and works toward it across multiple LLM calls.

Unlike Demo 1, this application does not compare strategies. It uses one selected strategy and demonstrates how context evolves during execution.

## 4.2 Example goal

> Design a REST API for a task management system. Support creating tasks, updating task status, retrieving tasks, and soft deletion. Generate an API specification and a test plan.

Participants may use other goals, including writing a technical specification, creating a data analysis plan, or generating requirements for a software feature.

For the core lab, keep execution text-based. The application should produce a specification and test plan; it does not need to run generated code.

## 4.3 Define the workflow

Use six steps:

| Run | Operation | Expected output |
| --- | --- | --- |
| 1 | Understand goal | Structured requirements |
| 2 | Plan | Subtasks and success criteria |
| 3 | Design | API specification |
| 4 | Refine | Updated design after feedback |
| 5 | Validate | Missing requirements and contradictions |
| 6 | Finalize | Final specification and test plan |

The user should be able to pause between runs and enter feedback or new requirements.

For the first version, use a fixed workflow. Automatic planning and dynamic execution can be introduced later.

## 4.4 Implement persistent state

Define a state object that survives individual LLM calls.

```json
{
  "goal_id": "goal-001",
  "goal": "Design a task management REST API",
  "status": "in_progress",
  "current_step": 3,
  "requirements": [],
  "decisions": [],
  "open_questions": [],
  "artifacts": {},
  "history": [],
  "summary": "",
  "validation_results": [],
  "metrics": []
}
```

Save state to a JSON file or SQLite database after each successful run.

Separate approved user requirements from model-generated proposals. A model suggestion should not automatically become an authoritative decision.

## 4.5 Implement the context builder

For each run, construct a prompt from the current goal, relevant state, recent history, and applicable artifacts.

```python
def build_goal_context(state, user_message):
    return {
        "goal": state["goal"],
        "current_step": state["current_step"],
        "requirements": state["requirements"],
        "decisions": state["decisions"],
        "recent_history": state["history"][-5:],
        "summary": state["summary"],
        "user_message": user_message
    }
```

This is a simplified example. The actual implementation should enforce the token budget and select relevant artifacts instead of blindly including every state field.

## 4.6 Add summarization

When history exceeds a configured threshold, summarize older messages.

The summary should preserve:

- Goal and constraints.
- Approved requirements.
- Important decisions.
- Completed work.
- Open questions.
- Known failures.

Retain the original history in storage. Compaction should change the context sent to the model, not destroy the application's audit trail.

## 4.7 Implement the execution loop

```python
def execute_step(goal_id, user_message):
    state = load_state(goal_id)

    context = build_goal_context(
        state,
        user_message
    )

    response = call_llm(context)

    validation = validate_output(
        response,
        state
    )

    state = update_state(
        state,
        response,
        validation
    )

    save_state(goal_id, state)

    return response, state
```

The actual `update_state` function should handle validation failures and avoid advancing the workflow when a required output is missing.

## 4.8 Visualize the execution

Show the current run, completed steps, constructed context, model response, and updated state.

> 🖼️ *Mockup: Demo 2 execution view* — [view in Notion](https://app.notion.com/p/3e4dbc95f92c8088864ae0f336d311de)

### Demo 2 acceptance criteria

> 🖼️ *Demo 2 acceptance checklist* — [view in Notion](https://app.notion.com/p/3e4dbc95f92c8088864ae0f336d311de)

# Part 5 — Demo 3: Multi-Strategy Goal Benchmark

Optional · Advanced · 90–120 minutes

## 5.1 Objective

Extend Demo 2 to execute the same goal using multiple context strategies and compare their end-to-end performance.

The key question is:

How does context engineering affect an AI application's ability to complete a multi-step task?

## 5.2 Experiment setup

Run four independent sessions:

| Session | Strategy |
| --- | --- |
| A | Full history |
| B | Sliding window |
| C | Summary + recent history |
| D | Structured state + retrieval + recent history |

All sessions must use the same initial goal, model, reference documents, available tools, and success criteria.

Each session must maintain its own state and generated artifacts.

## 5.3 Controlled experiment

Use the task management REST API goal from Demo 2.

Inject the same requirement changes at predefined steps:

| Run | Event |
| --- | --- |
| 1 | Initial goal |
| 2 | Require unique task IDs |
| 3 | Generate API design |
| 4 | Change deletion behavior to soft deletion |
| 5 | Generate final implementation specification |
| 6 | Validate against all requirements |

Each strategy should receive the same external events at the same points.

For a controlled comparison, also fix the orchestration steps. This isolates differences in context construction from differences in the execution plan.

## 5.4 Evaluate results

Measure both run-level and goal-level performance.

> 🖼️ *Table: run-level and goal-level metrics* — [view in Notion](https://app.notion.com/p/3e4dbc95f92c8088864ae0f336d311de)

For a more reliable comparison, repeat each strategy at least three times. Five or more repetitions can be useful when time and API budget permit.

Report individual results as well as averages, and inspect failures rather than relying on a single aggregate score.

## 5.5 Advanced extension: Independent execution

After controlled replay, allow each session to plan and execute independently.

The workflows may now take different numbers of steps, generate different artifacts, or require different retries.

Compare total cost, execution time, goal completion, and recovery from errors.

This is closer to evaluating a real agentic application, but it is harder to isolate the effect of context strategy alone.

# Part 6 — Testing and Evaluation

All participants should test their applications before presenting them.

## 6.1 Required test cases

| Test | Expected behavior |
| --- | --- |
| No history | Application handles an instruction without previous context |
| Long history | Context builder respects the configured token budget |
| Old requirement | Important earlier constraints remain available when needed |
| Changed requirement | Latest approved decision supersedes the old decision |
| Missing information | Model identifies uncertainty instead of inventing facts |
| Invalid response | Application records the error and avoids corrupting state |
| API failure | Application reports failure and supports a bounded retry |
| Resume session | Previously saved state can be loaded |

For the advanced demo, also verify that independent strategies cannot access one another's generated artifacts.

## 6.2 What participants should submit

Each participant or small group should submit:

- A working Streamlit application for Demo 1 and Demo 2.
- The context builder implementation.
- At least one benchmark result comparing three strategies.
- A multi-run execution trace with at least five LLM calls.
- A final generated artifact and its validation result.
- A short explanation of one observed context failure and how they addressed it.

Demo 3 is optional.

# Part 7 — Lab Discussion

Use these questions during the peer-learning session.

1. Why might full history perform worse than a shorter, carefully selected context?
2. What is the difference between memory and application state?
3. When should we use summarization instead of retrieval?
4. How can we evaluate context engineering without relying entirely on an LLM judge?
5. Why does Demo 3 require independent state for each strategy?

# Part 8 — Suggested Learning Schedule

For a 3–4-hour core lab, I recommend the following allocation.

| Activity | Time |
| --- | --- |
| Concepts and architecture | 20 min |
| Demo 1: Context benchmark | 50 min |
| Benchmark analysis | 15 min |
| Demo 2: Multi-run goal builder | 90 min |
| Testing and troubleshooting | 20 min |
| Participant demonstrations and discussion | 25 min |
| Total | 220 min |

Demo 3 can be completed independently or in an additional advanced session.

## Final learning outcome

By completing these three demos, participants progress from understanding how context changes a single model response to building and evaluating a multi-run AI application.

- **Demo 1:** Construct and compare context.
- **Demo 2:** Preserve and manage context across multiple runs.
- **Demo 3:** Measure how context strategies affect end-to-end goal completion.

This foundation leads naturally into the next Agent Engineering topics: tool calling, agent orchestration, execution state, validation loops, and human-in-the-loop control.


## 🧩 This week's Mini Muse step

🗂️ Memory: saved facts, recent turns and compaction. To try it, switch this week's page in the app to **🧩 Build Mini Muse**. The code, what to try and questions to check yourself are in the [Mini Muse guide](../mini-muse.md#week-2---memory--context-engineering).
