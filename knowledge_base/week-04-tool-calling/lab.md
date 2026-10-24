# Week 4 · Tool Calling — Lab: Weather Assistant with Tool Calling & MCP

> The repository's own implementation of this lab is in [`labs/week4_tool_calling/`](../../labs/week4_tool_calling/): the weather tools, a command-line agent, an MCP server and client, and the web page. Run the page with `streamlit run labs/week4_tool_calling/page.py`, or as Week 4 in `streamlit run app.py`. The folder names below are for building your own version.

## 1. Lab Overview

In this lab, you will build a small AI assistant that can retrieve **real-time weather information**.

The lab introduces two core concepts in agent engineering:

**Tool Calling** — enabling an LLM to decide when an external capability is required, select the appropriate tool, and generate the arguments needed to invoke it.

**Model Context Protocol (MCP)** — exposing external capabilities to an AI application through a standardized protocol.

You will first implement weather lookup using direct tool calling, then expose the same weather capability through an MCP server.

### Learning objectives

By the end of this lab, you should be able to:

- Explain why LLMs need tools.
- Define a tool with a clear schema.
- Implement the tool-calling execution loop.
- Distinguish between the LLM and the agent runtime.
- Build a basic MCP server.
- Connect an MCP client to an MCP server.
- Explain the relationship between Tool Calling, MCP, APIs, and the agent runtime.
- Evaluate tool selection, arguments, execution, and task success.

### Estimated time

**90–120 minutes**

---

## 2. System Architecture

You will build the system in two phases.

### Phase A — Direct Tool Calling

```text
┌──────────┐
│   User   │
└────┬─────┘
     │
     ▼
┌──────────┐
│   LLM    │
└────┬─────┘
     │
     │ Tool Call
     ▼
┌─────────────────┐
│  Agent Runtime  │
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│  get_weather()  │
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│   Weather API   │
└─────────────────┘
```

### Phase B — MCP Integration

```text
┌──────────┐
│   User   │
└────┬─────┘
     ▼
┌──────────┐
│   LLM    │
└────┬─────┘
     │ Tool Call
     ▼
┌─────────────────┐
│  Agent Runtime  │
└───────┬─────────┘
        ▼
┌─────────────────┐
│   MCP Client    │
└───────┬─────────┘
        │ MCP
        ▼
┌─────────────────┐
│   MCP Server    │
└───────┬─────────┘
        ▼
┌─────────────────┐
│  Weather API    │
└─────────────────┘
```

The user-facing capability remains the same. What changes is **how the weather capability is integrated into the AI application**.

---

## 3. Prerequisites

You should have:

- Python 3.11+
- Basic Python knowledge
- Basic understanding of LLM APIs
- An OpenAI API key
- A code editor such as VS Code

We will use [Open-Meteo](https://open-meteo.com/) as the weather service because it provides weather and geocoding APIs without requiring a separate API key.

Create a project:

```bash
mkdir weather-agent-lab
cd weather-agent-lab

python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install openai requests python-dotenv mcp
```

Create the following structure:

```text
weather-agent-lab/
│
├── .env
├── .gitignore
│
├── weather_tool.py
├── tool_calling_demo.py
│
├── weather_mcp_server.py
├── mcp_client_demo.py
│
└── README.md
```

Add your API key to `.env`:

```text
OPENAI_API_KEY=your_api_key
```

Add `.env` to `.gitignore`.

---

## 4. Part A — Build the Weather Capability

### Task 1: Implement `get_weather()`

Create `weather_tool.py`.

Implement:

```python
def get_weather(location: str) -> dict:
    ...
```

The function should perform two operations:

```text
City Name
   │
   ▼
Geocoding API
   │
   ▼
Latitude / Longitude
   │
   ▼
Weather API
   │
   ▼
Current Weather
```

The expected output should follow a consistent structure:

```json
{
  "location": "Detroit",
  "state": "Michigan",
  "country": "United States",
  "temperature_f": 62.0,
  "feels_like_f": 60.0
}
```

For an invalid location:

```json
{
  "error": "Location not found."
}
```

### Checkpoint 1

Test the function directly:

```python
print(get_weather("Detroit"))
```

At this point, your architecture is simply:

```text
Python → Weather API
```

There is **no LLM, tool calling, or MCP yet**.

### Discussion

Before continuing, answer:

> What capability does the function provide?

> Who decides when this function should be executed?

Currently, your application code makes that decision.

---

## 5. Part B — Define the LLM Tool

We now want the LLM to decide when weather information is required.

Define a tool named `get_weather`.

Its conceptual schema is:

```json
{
  "name": "get_weather",
  "description": "Get the current weather for a city or location.",
  "parameters": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City or location to retrieve weather for."
      }
    },
    "required": ["location"]
  }
}
```

The description and parameter schema are part of the **context available to the model**.

The model can now reason about:

```text
Do I need a tool?

        ↓

Which tool?

        ↓

What arguments?
```

---

## 6. Part C — Implement the Tool-Calling Loop

Create `tool_calling_demo.py`.

Your application should implement the following control flow:

```text
User Prompt
    │
    ▼
Send Prompt + Tool Definition to LLM
    │
    ▼
Does LLM request a tool?
    │
 ┌──┴───┐
 │      │
NO     YES
 │      │
 ▼      ▼
Answer  Parse Tool Call
           │
           ▼
       Execute Tool
           │
           ▼
       Tool Result
           │
           ▼
     Send Result to LLM
           │
           ▼
       Final Answer
```

Notice the responsibility boundary.

### LLM responsibilities

The LLM decides:

```text
whether a tool is needed
which tool to select
what arguments to provide
how to interpret the result
```

### Runtime responsibilities

Your application handles:

```text
tool registration
tool execution
API credentials
timeouts
errors
result delivery
logging
permissions
```

The LLM **requests** execution.

The runtime **performs** execution.

---

## 7. Experiment 1 — Tool Selection

Run these prompts.

### Prompt A

```text
What is weather?
```

Expected behavior:

```text
LLM → Answer
```

Tool calls: **0**

### Prompt B

```text
What's the current weather in Detroit?
```

Expected:

```text
LLM
 ↓
get_weather("Detroit")
 ↓
Weather API
 ↓
LLM
 ↓
Answer
```

Tool calls: **1**

### Prompt C

```text
Which is warmer right now, Detroit or Miami?
```

Expected conceptually:

```text
get_weather("Detroit")

get_weather("Miami")

        ↓

Compare results

        ↓

Answer
```

Tool calls: **2**

### Observation

Record:

| Prompt | Tool Needed? | Tool Selected | Arguments | Result |
| --- | --- | --- | --- | --- |
| What is weather? | No | — | — |  |
| Weather in Detroit? | Yes | `get_weather` | Detroit |  |
| Detroit vs Miami? | Yes | `get_weather` × 2 | Detroit, Miami |  |

---

## 8. Experiment 2 — Failure Handling

Run:

```text
What's the weather in asdfghxyz?
```

The weather function should return an error rather than fabricated weather data.

Expected final response:

```text
I couldn't find a location named "asdfghxyz".
Please check the location and try again.
```

### Discussion

Consider the difference between **tool failure** and **agent failure**.

A tool can correctly report `"location not found"`.

If the model subsequently invents a temperature, the **tool worked correctly but the overall agent failed**.

---

## 9. Part D — Introduce MCP

Our current architecture tightly integrates the weather function with the application.

Now we will expose that capability through an MCP server.

Create `weather_mcp_server.py`.

Conceptually, the server should expose:

```text
Server: weather-server

Tools:

get_weather
    location: string
```

Using the MCP Python SDK, the implementation will conceptually look like:

```python
from mcp.server.fastmcp import FastMCP
from weather_tool import get_weather

mcp = FastMCP("weather-server")


@mcp.tool()
def weather(location: str) -> dict:
    """Get the current weather for a location."""
    return get_weather(location)


if __name__ == "__main__":
    mcp.run()
```

The existing business logic hasn't fundamentally changed.

Instead, we've changed how the capability is **exposed**.

---

## 10. Part E — MCP Tool Discovery

The MCP client connects to the server.

```text
MCP Client
     │
     │ Connect
     ▼
MCP Server
```

The server advertises available capabilities.

For example:

```text
Server
weather-server

Available Tools

get_weather

Description
Get current weather for a location.

Input
location: string
```

This introduces an important architectural distinction.

### Without MCP

Your application directly defines/integrates `get_weather()`.

### With MCP

Your application connects to a server that exposes:

```text
MCP Server
    │
    └── get_weather()
```

The MCP client can discover the tool definition and make that capability available to the agent.

---

## 11. Part F — Complete MCP Execution Flow

Now run the same prompt:

```text
What's the weather in Detroit?
```

Observe each layer separately:

```text
1. USER

What's the weather in Detroit?

        ↓

2. LLM

Decision:
Current external information is required.

Tool:
get_weather

Arguments:
location = Detroit

        ↓

3. AGENT RUNTIME

Receives tool request.

        ↓

4. MCP CLIENT

Invokes:
get_weather

        ↓

5. MCP SERVER

Executes weather capability.

        ↓

6. WEATHER API

Returns current data.

        ↓

7. MCP SERVER

Returns tool result.

        ↓

8. AGENT RUNTIME

Provides tool result to LLM.

        ↓

9. LLM

Generates grounded answer.

        ↓

10. USER

"It's currently 62°F in Detroit..."
```

---

## 12. Part G — Compare the Two Architectures

After both versions work, compare them.

### Direct Tool Calling

```text
LLM
 │
 │ Tool Call
 ▼
Runtime
 │
 ▼
Python Function
 │
 ▼
Weather API
```

### Tool Calling + MCP

```text
LLM
 │
 │ Tool Call
 ▼
Runtime
 │
 ▼
MCP Client
 │
 │ MCP
 ▼
MCP Server
 │
 ▼
Weather API
```

This leads to the central lesson:

> **MCP does not replace tool calling.**

Tool calling answers:

> **What capability should the model request, and with what arguments?**

MCP addresses:

> **How can external capabilities be exposed to and invoked by AI applications through a standardized protocol?**

---

## 13. Part H — Evaluation

Now evaluate your agent systematically.

Use the following test set:

| Test Case | Expected Behavior |
| --- | --- |
| What is weather? | No tool |
| Explain humidity. | No tool |
| Weather in Detroit now? | `get_weather("Detroit")` |
| Weather in Miami? | `get_weather("Miami")` |
| Detroit vs Miami right now? | Two weather lookups |
| Weather in invalid city? | Tool call + graceful error |

Evaluate four levels.

### Level 1 — Tool Selection

Did the model correctly determine whether a tool was required?

$$
\text{Accuracy} = \frac{\text{Correct tool decisions}}{\text{Total test cases}}
$$

### Level 2 — Argument Accuracy

If a tool was selected, were the arguments correct?

Example:

```text
Expected:
location = "Detroit"

Actual:
location = "Detroit"

PASS
```

### Level 3 — Execution

Did the tool execute successfully?

Measure:

```text
Successful tool executions
──────────────────────────
Total attempted executions
```

### Level 4 — Task Success

Did the final answer correctly satisfy the user's request?

This is the most important metric.

---

## 14. Bonus Challenge

Add another tool:

```python
get_forecast(
    location,
    days
)
```

Then ask:

```text
Should I plan an outdoor event in Detroit this weekend?
```

The agent now has to decide between `get_weather()` and `get_forecast()`.

This is a much better evaluation of **tool selection** than simply testing whether the model can call one available tool.

---

## 15. Lab Deliverables

Each participant should submit:

```text
weather-agent-lab/
│
├── weather_tool.py
├── tool_calling_demo.py
├── weather_mcp_server.py
├── mcp_client_demo.py
│
└── README.md
```

The README should briefly answer four questions:

1. What problem does tool calling solve?
2. What role does the agent runtime play?
3. What problem does MCP solve?
4. What is the difference between tool-calling failure, tool-execution failure, and task failure?

---

## 16. Completion Criteria

The lab is complete when you can demonstrate all five behaviors:

- **No-tool reasoning** — the model answers a conceptual weather question without unnecessarily invoking a tool.
- **Single-tool execution** — the model retrieves current weather for one city.
- **Multiple-tool execution** — the model compares current weather across two cities.
- **Failure handling** — an invalid location does not result in hallucinated weather information.
- **MCP execution** — the same weather capability can be discovered/invoked through an MCP server.

The final mental model students should leave with is:

```text
                 Context
                    │
                    ▼
                   LLM
                    │
              Tool Calling
                    │
                    ▼
             Agent Runtime
                    │
                    ▼
               MCP Client
                    │
                 [MCP]
                    │
                    ▼
               MCP Server
                    │
                    ▼
            External System
```

**LLM decides → Runtime controls → MCP connects → Tool acts → Result returns → LLM continues.**
