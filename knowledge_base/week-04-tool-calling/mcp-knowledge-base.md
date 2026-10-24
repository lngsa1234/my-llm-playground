# Week 4 — MCP Knowledge Base

## 1. What is MCP?

**MCP = Model Context Protocol.**

MCP is an open protocol for connecting AI applications to external **tools, data, and resources** through a standardized interface.

A useful mental model is:

> **Tool calling tells the LLM how to request a tool. MCP provides a standardized way for the AI application to connect to and use external tools/resources.**

Without MCP, every external system may require a custom integration.

```text
Agent
 ├── Custom GitHub integration
 ├── Custom Jira integration
 ├── Custom database integration
 ├── Custom filesystem integration
 └── Custom Slack integration
```

With MCP:

```text
                  Agent / AI App
                        │
                   MCP Client
                        │
             Standard MCP Protocol
                        │
        ┌───────────────┼──────────────┐
        ▼               ▼              ▼
   GitHub MCP       Jira MCP       Database MCP
     Server          Server           Server
```

---

## 2. Why Do We Need MCP?

Tool calling alone doesn't standardize **how external systems expose capabilities to AI applications**.

Suppose you are building an engineering agent that needs:

```text
GitHub
Jira
PostgreSQL
Filesystem
CI/CD
Internal documentation
```

Without a common protocol, you may need to build and maintain a different integration for every system.

MCP creates a common interface.

Think of it somewhat like:

> **USB-C for AI integrations.**

Different devices do different things, but they can expose themselves through a common connection standard.

---

## 3. Tool Calling vs MCP

This distinction is very important.

|  | Tool Calling | MCP |
| --- | --- | --- |
| Primary purpose | Let an LLM request tools | Standardize connection to external capabilities |
| Main question | "Which tool should I use?" | "How is this capability exposed to my AI application?" |
| LLM involved? | Yes | Usually mediated by the AI application/runtime |
| Defines tool schema? | Yes | Can expose tool definitions |
| Executes external operations? | Runtime executes requested tool | MCP server implements/exposes capability |
| Example | `search_code(query)` | GitHub MCP server exposes `search_code` |

They are **complementary**, not competing technologies.

```text
Tool Calling = decision/request mechanism

MCP = integration protocol
```

---

## 4. Core MCP Architecture

There are several important components:

```text
┌──────────────────────┐
│         LLM          │
└──────────┬───────────┘
           │
      Tool decision
           │
           ▼
┌──────────────────────┐
│    Host / Runtime    │
│                      │
│     MCP Client       │
└──────────┬───────────┘
           │
           │ MCP
           ▼
┌──────────────────────┐
│     MCP Server       │
├──────────────────────┤
│ Tools                │
│ Resources            │
│ Prompts              │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ External System      │
│ GitHub / DB / Jira   │
└──────────────────────┘
```

### Host

The **host** is the AI application.

For example, an IDE agent, desktop AI application, or your own AgentForge runtime.

### MCP Client

The MCP client lives inside the host/application and communicates with MCP servers.

### MCP Server

The MCP server exposes capabilities from an external system through MCP.

For example:

```text
GitHub MCP Server

Tools:
  search_code()
  create_issue()
  create_pull_request()

Resources:
  repositories
  files
  issues
```

---

## 5. What Can MCP Expose?

Three concepts are particularly useful to understand:

### Tools — actions

Things the AI can invoke.

```text
create_issue()
search_code()
run_query()
send_message()
```

Think:

> **Tools = Do something**

### Resources — data/context

Information that the application can access.

```text
source code
documents
database records
configuration
logs
```

Think:

> **Resources = Get/read context**

### Prompts — reusable interaction templates

Servers can also expose predefined prompt templates/workflows that clients can use.

Think:

> **Prompts = reusable instructions/templates**

A simple mental model:

```text
MCP Server

Resources → KNOW

Tools     → DO

Prompts   → GUIDE
```

---

## 6. How MCP + Tool Calling Work Together

Suppose the user says:

> "Find the authentication bug in our repository."

### Step 1 — MCP connection

The agent runtime connects to a GitHub MCP server.

```text
Agent Runtime
      ↓
MCP Client
      ↓
GitHub MCP Server
```

The server exposes tools such as:

```text
search_code()
read_file()
get_commit()
create_pull_request()
```

### Step 2 — Tools are provided to the LLM

The LLM receives descriptions/schema for the relevant available tools.

### Step 3 — LLM decides

The model determines:

```text
I need to search the repository.
```

It requests:

```python
search_code(
    query="authentication"
)
```

### Step 4 — Runtime executes

```text
LLM
 ↓
Tool Call
 ↓
Agent Runtime
 ↓
MCP Client
 ↓
MCP Server
 ↓
GitHub
```

### Step 5 — Result returns

```text
GitHub
 ↓
MCP Server
 ↓
MCP Client
 ↓
Agent Runtime
 ↓
LLM
```

### Step 6 — Agent continues reasoning

The LLM may now decide:

```text
search_code()
      ↓
read_file()
      ↓
read_related_file()
      ↓
modify_file()
      ↓
run_tests()
      ↓
create_pull_request()
```

This is how **Tool Calling + MCP + Agent Loop** fit together.

---

## 7. Does the LLM Call the MCP Server Directly?

Usually, **no**.

A better architecture is:

```text
LLM
 │
 │ structured tool request
 ▼
Agent Runtime
 │
 ▼
MCP Client
 │
 │ MCP protocol
 ▼
MCP Server
 │
 ▼
External System
```

The runtime remains important because it can handle things such as:

```text
Authentication
Authorization
Permissions
Retries
Timeouts
Logging
Human approval
Tool result handling
State
Security policies
```

This is particularly important for an engineering agent.

You don't want the LLM itself controlling authentication credentials or unrestricted system access.

---

## 8. MCP Does Not Eliminate APIs

This is another important misconception.

MCP doesn't necessarily replace REST APIs, SDKs, databases, or command-line tools.

An MCP server may internally use them:

```text
LLM
 ↓
Tool Calling
 ↓
MCP Client
 ↓
MCP Server
 ↓
REST API
 ↓
GitHub
```

Or:

```text
MCP Server
 ↓
Database Driver
 ↓
PostgreSQL
```

Or:

```text
MCP Server
 ↓
Shell
 ↓
Local Filesystem
```

So MCP is better understood as an **AI-facing integration layer**.

---

## 9. MCP and Authentication

MCP can help standardize how AI applications interact with integrations, but it does **not magically eliminate authentication or authorization**.

The underlying system still needs security.

For example:

```text
Agent
 ↓
MCP Client
 ↓
Authentication / Authorization
 ↓
GitHub MCP Server
 ↓
GitHub API
```

The important distinction is:

> MCP can hide some integration complexity from the LLM, but the application/infrastructure still has to securely manage credentials, permissions, and authorization.

---

## 10. Why MCP Matters for Agents

Basic chat:

```text
User → LLM → Answer
```

Tool-enabled assistant:

```text
User → LLM → Tool → Answer
```

Agent:

```text
User
 ↓
LLM
 ↓
Tool
 ↓
Observation
 ↓
LLM
 ↓
Tool
 ↓
Observation
 ↓
...
 ↓
Goal completed
```

MCP makes it easier for that agent ecosystem to connect to many external capabilities without every connection being designed from scratch.

---

## 11. How Do We Evaluate MCP?

MCP itself is a protocol, so I would separate **protocol/integration evaluation** from **agent/tool-calling evaluation**.

For the MCP layer, useful metrics include:

| Metric | What it measures |
| --- | --- |
| Connection success rate | Can client connect to server? |
| Tool discovery success | Are expected tools exposed correctly? |
| Schema validity | Are tool inputs/outputs valid? |
| Execution success rate | Do MCP calls execute successfully? |
| Latency | How long does MCP communication take? |
| Error handling | Are failures handled correctly? |
| Permission correctness | Are unauthorized actions blocked? |
| Reliability | Does the integration work consistently? |

Then evaluate the **agent separately**:

```text
Agent Evaluation
│
├── Correct tool selected?
├── Correct arguments?
├── Correct tool sequence?
├── Unnecessary calls?
└── Task completed?
```

This separation is useful because:

```text
Wrong tool selected
        ↓
LLM / agent problem

Correct tool + wrong arguments
        ↓
LLM / context/schema problem

Correct call but MCP server fails
        ↓
Integration / infrastructure problem

Everything executes but goal fails
        ↓
Agent workflow/reasoning problem
```

That makes debugging much easier.

---

## 12. Tool Calling + MCP + RAG

These three concepts solve different problems:

```text
                 AI Agent
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
      RAG      Tool Calling      MCP
       │            │            │
Retrieve       Decide what    Standardized
knowledge      action/tool     integration
```

**RAG**

> What information should I retrieve and put into context?

**Tool Calling**

> What external capability should I invoke?

**MCP**

> How can my AI application connect to external capabilities through a standard protocol?

They can absolutely work together.

For example:

```text
User
 ↓
Agent
 ↓
RAG → retrieve engineering standards
 ↓
LLM
 ↓
Tool Call → search repository
 ↓
MCP → GitHub
 ↓
LLM
 ↓
Tool Call → run tests
 ↓
MCP → engineering environment
 ↓
Final result
```

---

## 13. The Full Mental Model

For your learning sequence, I'd use this architecture:

```text
                    USER
                      │
                      ▼
              ┌──────────────┐
              │ Agent Runtime│
              └───────┬──────┘
                      │
             Context Engineering
                      │
          ┌───────────┼───────────┐
          │           │           │
       System        RAG       Tool Schemas
     Instructions
          │           │           │
          └───────────┼───────────┘
                      ▼
                     LLM
                      │
                 Tool Calling
                      │
                      ▼
                Agent Runtime
                      │
                  MCP Client
                      │
                      ▼
                  MCP Server
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
        GitHub       Jira       Database
```

The most important concepts to remember are:

- **Context Engineering = give the model the right information.**
- **RAG = retrieve relevant external knowledge.**
- **Tool Calling = let the model decide when and how to request an external capability.**
- **MCP = standardize how the AI application connects to external tools and resources.**
- **Agent Runtime = execute and control the process.**
- **Agent Loop = repeatedly reason → act → observe until the task is complete.**

That gives you a very natural progression for your Agent Engineering course: **Context Engineering → RAG → Tool Calling → MCP → Agent Loop → Agent Workflow/Graph → Evaluation.**

### MCP protocol

MCP defines how clients and servers communicate. Its messages are based on **JSON-RPC 2.0**.

For example, MCP defines operations such as:

```text
initialize
tools/list
tools/call
resources/list
resources/read
prompts/list
```

So MCP standardizes things like **discovering tools, invoking tools, accessing resources, and exchanging results**.

### MCP transport

Those MCP/JSON-RPC messages still need a way to travel between the client and server. The two main transports are:

| Transport | Typical use | Example |
| --- | --- | --- |
| **stdio** | Local MCP server | Claude/AI app ↔ local Python process |
| **Streamable HTTP** | Remote MCP server | AI app ↔ remote MCP service |

So you can think of it as:

```text
MCP Client
    │
    │ MCP messages
    │ (JSON-RPC 2.0)
    │
    ├──── stdio ────────► Local MCP Server
    │
    └──── HTTP ─────────► Remote MCP Server
```

Then the **MCP server** may use completely different technologies behind the scenes:

```text
LLM
 ↓
AI Application
 ↓
MCP Client
 ↓
MCP Protocol (JSON-RPC)
 ↓
stdio / Streamable HTTP
 ↓
MCP Server
 ↓
REST / gRPC / SQL / filesystem / shell / proprietary API
```
