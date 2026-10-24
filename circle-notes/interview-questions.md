# AI Engineering Interview Questions

Real-world interview questions from AI companies, reviewed in Week 4. See [Lynn's Answer Sheet](#lynns-answer-sheet) below for draft answers.

### RAG

1. What chunking strategy would you use for a large technical documentation, and why? (fixed size/overlap - well structured document, structured chunking, semantic chunking) — text file, image, video file.
2. How do you choose between a sparse retriever (BM25) and a dense retriever? When do you need both?
3. How would you evaluate the quality of a RAG pipeline: retrieval and generation separately?
4. How does agentic RAG differ from standard RAG, and when is the extra complexity justified?
5. What causes semantic drift in embedding search and how do you detect it?

### Tool Calling

1. What is MCP (Model Context Protocol) and how does it differ from traditional function calling?
2. How many tools is too many? How do you design tool schemas an LLM can actually use correctly?
3. How does an agent decide when to call a tool versus answer from its own knowledge?
4. How do you handle tool-call errors, timeouts and retries in an agentic loop?

### Agent

1. How does multi-agent orchestration work, and when does it break down?
2. Design memory for a long-running agent: what do you store, where, and how do you retrieve it?
3. What makes an agent loop terminate correctly? How do you bound cost and steps?
4. How do you make an agent's actions reversible, or at least auditable, in a production system?
5. Design human-in-the-loop approval for an agent that takes consequential actions.

---

## Lynn's Answer Sheet

### RAG

**How would you evaluate the quality of a RAG pipeline: retrieval and generation separately?**

I would evaluate **retrieval and generation separately**, because they measure different parts of the RAG pipeline.

**Retrieval quality:**

- **Recall** — Of all the relevant information needed, how much did we retrieve?
- **Precision** — Of everything we retrieved, how much was actually relevant?
- **F1** — Harmonic mean of precision and recall, balancing both. The larger the F1, the better the result.

### Tool Calling

**1. What is MCP (Model Context Protocol) and how does it differ from traditional function calling?**

MCP is a standardized protocol that connects AI applications and LLMs with external tools and data sources. MCP provides a standard interface to AI applications/LLMs regardless of how the underlying traditional function calls are implemented — e.g. through a **REST API, gRPC service, database, file system, or shell/CLI command**.

Technically, MCP introduces a client-server architecture where an AI application uses an MCP client to discover tools available from an MCP server and provide relevant tool definitions to LLMs. During reasoning, the **LLM decides whether and which tool to call**. The AI application then executes that tool call through the MCP client and MCP server and returns the result to the LLM.

**2. How many tools is too many? How do you design tool schemas an LLM can actually use correctly?**

Tool count becomes a problem when the LLM can no longer reliably distinguish which tool to use. Tool organization is similar to service-based design, while tool schemas are similar to API interface design.

**3. How does an agent decide when to call a tool versus answer from its own knowledge?**

We need to differentiate the agent from the LLM. In general, the LLM decides if it can answer the question from its own knowledge or if it should call a tool.
