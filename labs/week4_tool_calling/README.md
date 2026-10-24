# Week 4 Lab · Tool Calling & MCP — Weather Assistant

Lab guide: [knowledge_base/week-04-tool-calling/lab.md](../../knowledge_base/week-04-tool-calling/lab.md)

This lab builds the same real-time weather capability in two ways:

1. **Direct tool calling**: the agent runtime calls a local Python function.
2. **Tool calling through MCP**: the agent runtime discovers and invokes that function through ## What's here

```text
week4_tool_calling/
├── page.py                 the web page: run with or without tools, inspect the trace, live benchmark
├── weather.py              the weather tools, tool schemas and agent loop, shared by everything below
├── tool_calling_demo.py    command-line agent using the tools directly
├── weather_mcp_server.py   MCP server exposing the same tools
├── mcp_client_demo.py      command-line agent that discovers and calls the tools over MCP
└── tests/
```

There is one copy of the weather code. The web page, the command-line demo and the MCP server all import `weather.py`, so they offer the same two tools: `get_weather` (current conditions) and `get_weekend_forecast` (upcoming Saturday and Sunday).

## Setup

From the repo root:

```bash
pip install -r requirements.txt
streamlit run labs/week4_tool_calling/page.py   # this lab on its own
streamlit run app.py                            # all labs, pick Week 4
```

Edit the repo-root `.env` to set `OPENAI_API_KEY`. The web page uses the model in its settings panel; the command-line demos use `OPENAI_MODEL` from `.env` (default `gpt-4o-mini`). Run the commands below from the repo root.

## Part A: Weather capability

`weather.py` is plain Python. It geocodes a location, calls Open-Meteo, and returns consistent JSON. Try the tools with no LLM involved:

```bash
python labs/week4_tool_calling/weather.py Detroit
```

Successful responses contain `location`, `state`, `country`, `temperature_f`, and `feels_like_f`. A missing place returns `{"error": "Location not found."}`. Provider/network failures are also returned as error data, so the agent can report them rather than hallucinate values.

At this point the architecture is simply **Python → Weather API**. The application code, not an LLM, decides when to execute the function.

 to execute the function. Its capability is to turn a human location into current, real-time weather data.

## Part B/C: Direct tool calling

```bash
python labs/week4_tool_calling/tool_calling_demo.py "What is weather?"
python labs/week4_tool_calling/tool_calling_demo.py "What's the current weather in Detroit?"
python labs/week4_tool_calling/tool_calling_demo.py "Which is warmer right now, Detroit or Miami?"
python labs/week4_tool_calling/tool_calling_demo.py "What's the weather in asdfghxyz?"
```

`tool_calling_demo.py` sends the model both tool schemas from `weather.py`. The model decides whether to call it and provides `location`; the runtime validates/parses the request, executes Python, logs the result, and sends that result back to the model. The loop supports multiple calls, which is necessary for a Detroit-versus-Miami comparison.

## Part D–F: MCP version

`weather_mcp_server.py` exposes the same two functions as MCP tools over stdio. The client starts it automatically, initializes an MCP session, discovers its tools, translates their input schemas for the LLM, and routes model tool calls back through MCP.

```bash
python labs/week4_tool_calling/mcp_client_demo.py "What's the weather in Detroit?"
python labs/week4_tool_calling/mcp_client_demo.py "Which is warmer right now, Detroit or Miami?"
```

The client prints the discovered MCP tools plus each MCP call/result, making the boundary visible. You can also start the server alone with `python labs/week4_tool_calling/weather_mcp_server.py`; it is a stdio protocol process, so it will wait for an MCP client rather than provide an interactive prompt.

## Architecture comparison

```text
Direct:  LLM → tool request → agent runtime → Python function → Weather API
MCP:     LLM → tool request → agent runtime → MCP client → MCP server → Weather API
```

MCP does not replace tool calling. Tool calling lets the model request a capability with arguments; MCP standardizes how capabilities are advertised and invoked across application boundaries.

## Evaluation worksheet

Run this set against either demo and record the printed calls/results and final response:

| Prompt | Expected behavior |
| --- | --- |
| `What is weather?` | No tool call |
| `Explain humidity.` | No tool call |
| `Weather in Detroit now?` | `get_weather("Detroit")` |
| `Weather in Miami?` | `get_weather("Miami")` |
| `Detroit vs Miami right now?` | Two weather lookups |
| `Weather in invalid city?` | Tool call and a graceful error |

- **Tool-selection accuracy** = correct tool decisions / total test cases.
- **Argument accuracy** = calls with the intended `location` / total tool calls.
- **Execution success** = successful tool executions / attempted executions.
- **Task success** = final answers that actually satisfy the user without inventing facts.

## Key questions answered

1. **What problem does tool calling solve?** LLMs do not inherently have live data or the ability to execute code. A schema lets the model ask the runtime for a suitable external capability and supply structured arguments.
2. **What does the agent runtime do?** It registers tools, applies permissions and validation, handles credentials/timeouts/errors/logging, executes calls, and returns results. The model requests; the runtime controls execution.
3. **What problem does MCP solve?** It gives external capabilities a standard discovery and invocation interface, allowing an application to connect to independently hosted tool servers instead of hard-wiring each integration.
4. **How do failures differ?** A tool-calling failure means the model picked the wrong tool or arguments (or skipped a necessary tool). A tool-execution failure is a runtime/API problem, such as a timeout. A task failure is any unsatisfactory final user outcome—for example, a model inventing a temperature after a correctly returned `Location not found` error.

## Bonus challenge

`get_weekend_forecast` is already in `weather.py`. Ask: “Should I plan an outdoor event in Detroit this weekend?” and check that the model picks the forecast tool rather than current weather. Then add a third tool, such as `get_hourly_forecast(location, hours)`, to `weather.py` and expose it in `TOOL_FUNCTIONS`, the tool list and the MCP server.
