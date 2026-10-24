# Week 6 — Agent Evaluation Fundamentals

Evaluating an AI agent requires more than assessing whether its final response appears correct. An agent may generate a convincing response while selecting the wrong tool, using incorrect parameters, failing to complete the requested action, or introducing failures that did not exist in a previous version.

A robust evaluation framework typically includes five foundational concepts:

**Golden Datasets → Task Success → Tool Evaluation → LLM-as-a-Judge → Regression Testing**

Together, they answer three fundamental questions:

1. **Did the agent accomplish the intended task?**
2. **Did the agent behave correctly while accomplishing it?**
3. **Does the system continue to perform reliably as it evolves?**

---

## 1. Golden Dataset

A **golden dataset** is a curated collection of representative test cases used as a stable benchmark for evaluating an AI system.

Each test case typically contains an input and one or more expectations about the desired outcome or behavior.

For traditional software, a test might specify an exact expected output. For agents, the expected behavior is often more flexible.

For example:

```json
{
  "input": "What is the weather in Detroit tomorrow?",
  "expected_outcome": "Provide tomorrow's Detroit weather forecast",
  "expected_tools": ["get_weather"],
  "expected_arguments": {
    "location": "Detroit"
  }
}
```

A strong golden dataset should represent the actual operating environment of the agent and include:

- Common user scenarios
- Edge cases
- Ambiguous requests
- Tool-use scenarios
- Error and recovery scenarios
- Previously observed production failures

The dataset should evolve over time. When a meaningful failure occurs in production, that case can be added to the golden dataset so future versions are tested against it.

Conceptually:

```text
Production Traffic
       │
       ├── Representative Cases
       ├── Edge Cases
       └── Historical Failures
                │
                ▼
          Golden Dataset
```

**Key principle:** The quality of an evaluation system depends heavily on the quality of its evaluation dataset. A small, carefully curated dataset is often more useful than a large but poorly defined one.

Public benchmarks (BFCL, τ-bench, GAIA, AppWorld, HotpotQA and others) are a good source of case ideas and grading formats. See [Public Benchmarks for Agent Evaluation](benchmarks.md).

---

## 2. Task Success

**Task success** measures whether the agent accomplished the user's intended objective.

This is generally the most important end-to-end metric for an agent system.

Consider the request:

```text
Find tomorrow's weather in Detroit.
If it will rain, create a reminder for 8 AM.
```

The agent could correctly determine that rain is expected and respond:

```text
It will rain tomorrow. I created a reminder for you.
```

However, if the reminder was never actually created, the response may appear correct while the task itself failed.

Task success should therefore focus on **observable outcomes**, not merely response quality.

For example:

```text
Success Criteria

✓ Weather information retrieved
✓ Rain condition evaluated correctly
✓ Reminder created when required
✓ Reminder scheduled for 8:00 AM
```

Task success can be represented as a binary metric:

```text
PASS / FAIL
```

or as a structured score:

```text
0 — Failed
1 — Partially completed
2 — Fully completed
```

For production systems, task success can also be expressed as:

**Task Success Rate = Successful Tasks / Total Evaluated Tasks**

The important distinction is:

> **Response correctness evaluates what the agent said. Task success evaluates what the agent accomplished.**

---

## 3. Tool Evaluation

Agents frequently interact with external systems through tools, APIs, databases, search systems, or other agents.

**Tool evaluation** measures whether those interactions were performed correctly.

A typical agent execution may look like:

```text
User Request
     ↓
Reasoning / Routing
     ↓
Tool Selection
     ↓
Argument Generation
     ↓
Tool Execution
     ↓
Result Interpretation
     ↓
Next Action
     ↓
Final Response
```

Tool evaluation can examine several dimensions:

| Dimension | Evaluation Question |
| --- | --- |
| Tool Selection | Did the agent choose the correct tool? |
| Argument Accuracy | Were the tool parameters correct? |
| Tool Necessity | Was the tool call necessary? |
| Tool Sequence | Were multiple tools called in the appropriate order? |
| Result Interpretation | Did the agent correctly use the returned information? |
| Error Recovery | Did the agent respond appropriately when the tool failed? |

For example:

```text
User:
"What is the weather in Detroit?"

Expected:
get_weather(location="Detroit")

Actual:
web_search(query="Detroit weather")
```

The agent might still produce a correct weather forecast.

Therefore:

```text
Task Success:      PASS
Tool Evaluation:   FAIL
```

This distinction is important because **successful outcomes do not necessarily imply correct agent behavior**.

For more complex systems, evaluation can extend from individual tool calls to the entire **agent trajectory**.

```text
User Request
      ↓
search_customer
      ↓
retrieve_order
      ↓
check_refund_policy
      ↓
issue_refund
      ↓
respond_to_customer
```

Trajectory evaluation asks whether the sequence of decisions and actions was appropriate, efficient, and compliant with system constraints.

---

## 4. LLM-as-a-Judge

Some evaluation criteria can be implemented deterministically.

For example:

```text
Was the correct tool called?
Was the API parameter correct?
Was the database record created?
```

Other qualities are difficult to evaluate using traditional code:

```text
Was the answer relevant?
Was the explanation complete?
Did the agent follow the user's intent?
Was the response professionally written?
```

In these situations, another language model can be used as an evaluator. This approach is commonly called **LLM-as-a-Judge**.

A judge typically receives:

```text
User Input
     +
Reference / Expected Behavior
     +
Agent Output
     +
Evaluation Rubric
     ↓
Judge Model
     ↓
Evaluation Result
```

For example:

```json
{
  "task_success": "pass",
  "correctness": 4,
  "completeness": 3,
  "reason": "The response correctly answered the request but omitted one required detail."
}
```

LLM judges are particularly useful for evaluating:

- Semantic correctness
- Relevance
- Completeness
- Instruction following
- Response quality
- Complex task outcomes

However, an LLM judge should not automatically be treated as ground truth. Judges can exhibit biases and inconsistencies.

A stronger methodology is:

```text
Human-Labeled Examples
        ↓
Define Evaluation Rubric
        ↓
Test LLM Judge
        ↓
Compare Judge vs Human
        ↓
Refine Rubric
        ↓
Deploy Judge at Scale
```

Where possible, deterministic evaluation should be preferred. LLM judges are most valuable when the desired property cannot be reliably expressed as code.

---

## 5. Regression Testing

Agent systems evolve continuously.

Changes may include:

- Model upgrades
- Prompt modifications
- Tool descriptions
- Retrieval configuration
- Memory implementation
- Routing logic
- Agent frameworks
- Workflow changes

An improvement in one area can unexpectedly degrade another.

Suppose version 1 produces:

| Metric | V1 |
| --- | --- |
| Task Success | 86% |
| Tool Accuracy | 92% |
| Quality Score | 88% |

After changing the agent prompt:

| Metric | V1 | V2 |
| --- | --- | --- |
| Task Success | 86% | 90% |
| Tool Accuracy | 92% | 84% |
| Quality Score | 88% | 89% |

The new version is not unambiguously better.

More importantly, evaluation should examine individual cases:

```text
Test Case 17
V1 → PASS
V2 → FAIL

REGRESSION
```

A **regression** occurs when behavior that previously worked correctly begins to fail after a system change.

This leads to an important development cycle:

```text
Production Failure
        ↓
Root-Cause Analysis
        ↓
Fix
        ↓
Add Failure to Golden Dataset
        ↓
Run Evaluation Suite
        ↓
Deploy
        ↓
Continue Monitoring
```

Over time, the golden dataset becomes an institutional record of behaviors that the system must preserve.

---

# Putting the Evaluation System Together

These concepts play different roles and should not be treated as interchangeable metrics.

```text
                 GOLDEN DATASET
                Evaluation Cases
                       │
                       ▼
                   RUN AGENT
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       TASK SUCCESS        TOOL EVALUATION
       Did it achieve      Did it behave
       the objective?      correctly?
             │                   │
             └─────────┬─────────┘
                       ▼
                LLM-AS-A-JUDGE
             Semantic evaluation
                       │
                       ▼
                 EVAL RESULTS
                       │
                 V1 ↔ V2 ↔ V3
                       │
                       ▼
              REGRESSION TESTING
```

The distinction can be summarized as follows:

| Concept | Primary Purpose |
| --- | --- |
| **Golden Dataset** | Defines representative evaluation cases |
| **Task Success** | Measures whether the objective was accomplished |
| **Tool Evaluation** | Measures correctness of agent actions |
| **LLM-as-a-Judge** | Evaluates semantic or subjective qualities |
| **Regression Testing** | Detects degradation across system versions |

A mature agent evaluation system therefore combines **deterministic checks, task-level metrics, trajectory/tool evaluation, model-based judges, human review, and regression testing**.

For your Agent Engineering course, the most useful principle to emphasize is:

> **Evaluate outcomes, not just outputs. Evaluate trajectories, not just final answers. And evaluate every meaningful system change against a stable benchmark.**

This moves agent development from **"the demo seems to work"** toward **measurable, repeatable engineering quality**.
