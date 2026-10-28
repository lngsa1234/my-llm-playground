# Week 4 · Tool Calling — Concepts

> 🎯 **At a glance — Learning goal:** let an LLM request reliable external actions and data through safe, validated tool calls.

## 1. What is Tool Calling?

**Tool calling is the mechanism that allows an LLM or AI agent to request an external function or system to perform an action or retrieve information.**

An LLM by itself primarily generates text based on its context. It does not inherently know current database values, execute code, query private systems, or perform real-world actions.

Tools extend the LLM:

- **LLM = reasoning / decision making** — probabilistic, dynamic, inefficient
- **Tools = information retrieval / computation / actions** — deterministic, efficient

Question: in which situation do you need to call the LLM or use tools? (e.g. calculate 1 - 0.1)

Examples:

| User request | Tool |
| --- | --- |
| "What's the weather in Detroit?" | Weather API |
| "Find order #1234." | Database query |
| "Calculate my mortgage payment." | Calculator |
| "Send an email to John." | Email API |
| "Search our engineering documents." | Search / RAG tool |
| "Create a Jira ticket." | Jira API |
| "Run the test suite." | Shell / CI tool |

A useful distinction:

> **The LLM does not normally execute the tool itself. It generates a structured request for the application/agent runtime to execute.**

---

## 2. Why Do We Need Tool Calling?

LLMs have several fundamental limitations.

### A. Knowledge can be unavailable or outdated

The model may not know today's stock price, current weather, or the latest state of your product database.

A tool can retrieve it.

```text
LLM
 ↓
get_stock_price("NVDA")
 ↓
Stock API
 ↓
$xxx.xx
```

### B. LLMs cannot reliably perform external actions

Generating:

> "I have created the Jira ticket."

doesn't actually create anything.

Instead:

```text
LLM decides:
create_jira_ticket(...)

        ↓

Agent Runtime

        ↓

Jira API

        ↓

Ticket actually created
```

### C. Some tasks require deterministic computation

For example:

```text
calculate_tax()
run_python()
query_database()
run_unit_tests()
```

It's usually better to let a deterministic system perform the calculation rather than ask the LLM to approximate it.

### D. Tools connect AI to existing systems

This is what turns:

**LLM → assistant**

into:

**LLM + tools → agent**

An engineering agent might have:

```text
read_file()
search_code()
write_file()
run_tests()
create_pull_request()
query_jira()
```

---

## 3. How Tool Calling Works

A typical architecture is:

```text
             ┌───────────────┐
             │     User      │
             └───────┬───────┘
                     │
                     ▼
             ┌───────────────┐
             │ Agent Runtime │
             └───────┬───────┘
                     │
        Prompt + available tools
                     │
                     ▼
             ┌───────────────┐
             │      LLM      │
             └───────┬───────┘
                     │
              Tool request
                     │
                     ▼
             ┌───────────────┐
             │ Agent Runtime │
             └───────┬───────┘
                     │
                Execute tool
                     │
                     ▼
             ┌───────────────┐
             │ API / DB / OS │
             └───────┬───────┘
                     │
                 Result
                     │
                     ▼
             ┌───────────────┐
             │      LLM      │
             └───────┬───────┘
                     │
                     ▼
                 Response
```

The important point is that **the application/runtime sits between the LLM and the real tool**.

---

## 4. Step-by-Step Example

Suppose the user asks:

> "What's the weather in Detroit?"

The application tells the LLM that this tool exists:

```text
get_weather

Description:
Get the current weather for a city.

Input:
city: string
```

### Step 1 — User request

```text
What's the weather in Detroit?
```

### Step 2 — LLM selects a tool

Instead of answering directly, the model produces something conceptually like:

```json
{
  "tool": "get_weather",
  "arguments": {
    "city": "Detroit"
  }
}
```

### Step 3 — Runtime executes it

The application receives the tool request and calls the actual weather service.

```text
get_weather("Detroit")
```

### Step 4 — Tool returns data

```json
{
  "temperature": 62,
  "condition": "Cloudy"
}
```

### Step 5 — Result goes back into the LLM context

The model now receives something equivalent to:

```text
Tool result:

Detroit
Temperature: 62°F
Condition: Cloudy
```

### Step 6 — LLM generates the final response

> It's currently 62°F and cloudy in Detroit.

So the full loop is:

**User → LLM → tool request → runtime → tool → result → LLM → answer**

---

## 5. What Defines a Tool?

A tool generally needs at least three things:

### Name

```text
search_documents
```

### Description

```text
Search internal engineering documentation.
```

### Input schema

```json
{
  "query": "string",
  "max_results": "integer"
}
```

The **tool description is particularly important** because the model uses it to determine when that tool should be selected.

For an agent with many tools:

```text
Tools

├── search_documents()
├── search_code()
├── read_file()
├── write_file()
├── run_tests()
├── query_jira()
└── create_pull_request()
```

the model must solve two problems:

```text
Should I use a tool?

        ↓ yes

Which tool should I use?

        ↓

What arguments should I provide?
```

---

## 6. Tool Calling vs API Calling

These concepts are related but different.

An **API call** is normally explicitly programmed:

```python
weather_api.get_weather("Detroit")
```

With **LLM tool calling**, the model decides whether the API/function should be invoked and constructs its arguments.

```text
Traditional software

Developer
   ↓
Code decides which API
   ↓
API


Agentic software

User
   ↓
LLM decides which tool
   ↓
Runtime
   ↓
API
```

The underlying tool can still be a REST API, database operation, Python function, shell command, MCP server, or another agent.

---

## 7. Tool Calling and MCP

Tool calling and MCP are also different layers.

**Tool calling answers:**

> How does the model decide that it wants to use a tool?

**MCP answers more closely:**

> How can applications expose tools/resources to AI systems through a standardized protocol?

Conceptually:

```text
LLM
 │
 │ tool call
 ▼
Agent Runtime
 │
 │ MCP
 ▼
MCP Client
 │
 ▼
MCP Server
 │
 ├── GitHub
 ├── Database
 ├── Jira
 └── Filesystem
```

MCP is therefore **not a replacement for tool calling**. It can be part of the infrastructure through which tools are discovered and invoked. See the [MCP knowledge base](concepts-mcp.md).

---

## 8. Single vs Multiple Tool Calls

A simple request may require one call:

```text
User
 ↓
LLM
 ↓
Weather Tool
 ↓
LLM
 ↓
Answer
```

Agentic tasks often require multiple calls.

Example:

> "Fix this bug and create a PR."

The agent might perform:

```text
search_code()
      ↓
read_file()
      ↓
edit_file()
      ↓
run_tests()
      ↓
tests fail
      ↓
read_logs()
      ↓
edit_file()
      ↓
run_tests()
      ↓
create_pull_request()
```

This creates the common **agent loop**:

```text
Reason
  ↓
Choose Tool
  ↓
Execute
  ↓
Observe Result
  ↓
Reason
  ↓
Choose Next Tool
  ↓
...
  ↓
Finish
```

Tool calling is therefore one of the core building blocks of an AI agent.

---

## 9. How Do We Evaluate Tool Calling?

Yes—tool calling should be evaluated.

There are several different things to measure.

### 1. Tool Selection Accuracy

Did the model choose the correct tool?

Example:

```text
Question:
"What's the weather in Detroit?"

Expected:
get_weather

Actual:
web_search
```

You can calculate:

**Tool Selection Accuracy = Correct tool selections / Total tool-selection cases**

### 2. Tool Call Precision

Of all the tool calls the agent made, how many were actually appropriate?

```text
Precision =
Correct / appropriate tool calls
────────────────────────────────
All tool calls made
```

This catches **unnecessary tool usage**.

An agent that calls five tools when only one was necessary may have poor precision.

### 3. Tool Call Recall

Of all tool calls that were necessary, how many did the agent successfully make?

```text
Recall =
Necessary tool calls successfully made
───────────────────────────────────────
All necessary tool calls
```

This catches **missing calls**.

For example, an agent might answer a question from memory even though it should have queried the database.

### 4. Argument Accuracy

Even if the correct tool was selected, were the parameters correct?

Expected:

```json
{
  "city": "Detroit",
  "unit": "fahrenheit"
}
```

Actual:

```json
{
  "city": "Chicago",
  "unit": "fahrenheit"
}
```

Correct tool, wrong arguments → failure.

### 5. Tool Execution Success Rate

Did the requested calls actually execute successfully?

```text
Successful executions
─────────────────────
Total execution attempts
```

Failures can come from invalid arguments, authentication, timeouts, unavailable APIs, schema violations, etc.

### 6. Task Success Rate

This is ultimately more important than individual tool accuracy:

> **Did the agent actually accomplish the user's goal?**

Consider:

```text
search_code ✓
read_file ✓
edit_file ✓
run_tests ✓
create_PR ✓
```

Individual calls succeeded, but if the PR doesn't fix the requested bug, the **task failed**.

So evaluate both:

```text
Tool-level evaluation
        +
Task-level evaluation
```

---

## 10. Efficiency Metrics

A production agent should also measure efficiency.

Useful metrics include:

| Metric | Question |
| --- | --- |
| Tool selection accuracy | Did it choose the correct tool? |
| Argument accuracy | Were the parameters correct? |
| Execution success | Did the call execute? |
| Tool-call precision | Were the calls actually necessary? |
| Tool-call recall | Did it make all required calls? |
| Task success rate | Did it solve the user's problem? |
| Tool calls/task | Did it use too many tools? |
| Latency | How long did execution take? |
| Cost/task | How expensive was the complete run? |

For more advanced agents, I would also evaluate **tool sequence correctness**.

For example:

```text
read requirements
      ↓
inspect code
      ↓
modify code
      ↓
run tests
      ↓
create PR
```

may be correct, while:

```text
modify code
      ↓
create PR
      ↓
run tests
```

could violate your engineering workflow even if every individual tool call is technically valid.

---

## 11. Recommended Evaluation Hierarchy

For your Agent Engineering course, I'd teach evaluation at **four levels**:

```text
Level 1 — Selection
Did the agent choose the right tool?

Level 2 — Arguments
Did it call the tool correctly?

Level 3 — Execution / Sequence
Did the calls succeed and occur in the right order?

Level 4 — Task Outcome
Did the agent actually accomplish the goal?
```

The last level is the most important.

An agent can have **95% tool-selection accuracy but still be a poor agent** if it chains those calls incorrectly or fails to complete the task.

---

## 12. Core Mental Model

The simplest model to remember is:

```text
                    LLM
                 "What next?"
                     │
          ┌──────────┴──────────┐
          │                     │
       Respond               Use Tool
                                │
                                ▼
                           Agent Runtime
                                │
                                ▼
                              Tool
                                │
                                ▼
                             Result
                                │
                                └──────► LLM
```

Or even more simply:

> **LLM decides. Runtime executes. Tool acts. Result returns. LLM decides again.**

That distinction becomes very important when you move from basic tool calling into **MCP, agent loops, LangGraph, permissions, human-in-the-loop, and multi-agent engineering systems**.
