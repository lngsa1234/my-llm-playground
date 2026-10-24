# Week 3 Lab — Build a RAG System from Scratch

## Retrieval-Augmented Generation: From Documents → Retrieval → Grounded Answers

### Estimated Time

- **Build:** 1–2 hours
- **Group Demo & Discussion:** 60–90 minutes

### Tech Stack

- Python
- OpenAI API
- Streamlit
- FAISS or Chroma
- Markdown/text files
- Optional: pandas for benchmark results

> The repository's own implementation of this lab lives in [`rag_corpus/`](../../rag_corpus/) (the documents), [`benchmark/rag/`](../../benchmark/rag/) (the questions) and the Week 3 tab of [`app.py`](../../app.py).

---

# 1. Learning Objectives

By the end of this lab, you should be able to explain and build a basic Retrieval-Augmented Generation (RAG) system.

You should understand:

1. What problem RAG solves
2. Why RAG is different from simply asking an LLM a question
3. Why RAG existed conceptually before modern LLMs
4. What embeddings are
5. What vector search does
6. Why documents need to be chunked
7. How a user query is converted into an embedding
8. How relevant chunks are retrieved
9. How retrieved information is inserted into the LLM context
10. How the LLM generates a grounded answer
11. Why retrieval quality and generation quality are separate problems
12. How Top-K and chunk size affect results
13. How to evaluate a RAG system
14. Why an LLM should sometimes answer:

> "I don't have enough information in the provided knowledge base."

---

# 2. What Is RAG?

RAG stands for:

**Retrieval-Augmented Generation**

The core idea is simple:

Instead of expecting the LLM to know everything, retrieve relevant information from an external knowledge source and provide that information to the model when answering the question.

Conceptually:

```text
User Question
      ↓
Retrieve Relevant Information
      ↓
Add Information to Prompt
      ↓
LLM
      ↓
Grounded Answer
```

A more complete RAG pipeline looks like:

```text
                    OFFLINE / INDEXING

Documents
   ↓
Document Loading
   ↓
Chunking
   ↓
Embedding
   ↓
Vector Database


                    ONLINE / QUERY

User Question
   ↓
Query Embedding
   ↓
Vector Search
   ↓
Top-K Relevant Chunks
   ↓
Context Construction
   ↓
Prompt
   ↓
LLM
   ↓
Grounded Answer + Sources
```

---

# 3. Did RAG Exist Before LLMs?

Yes.

The term **Retrieval-Augmented Generation** became associated with modern neural language models around 2020, but the fundamental concept of retrieving relevant information before answering a question is much older.

Traditional information retrieval systems already performed:

```text
Query
 ↓
Search
 ↓
Rank Documents
 ↓
Return Relevant Information
```

Search engines are an obvious example.

Traditional question-answering systems also combined:

```text
Information Retrieval
        +
Question Answering
```

Modern RAG adds a powerful generative model after retrieval:

```text
Traditional Search

Question
   ↓
Retrieve
   ↓
Documents


Modern RAG

Question
   ↓
Retrieve
   ↓
Relevant Context
   ↓
LLM
   ↓
Natural-Language Answer
```

Therefore, retrieval is not new.

The important development is the combination of retrieval with modern generative language models.

---

# 4. The Problem We Are Going to Solve

Imagine that we work for a fictional technology company called:

**NovaTech**

NovaTech has internal documentation covering:

- employee benefits
- remote-work policies
- vacation policies
- product pricing
- subscription plans
- refunds
- API limits
- security requirements
- customer support

We want to build an AI assistant that can answer questions about NovaTech.

Example:

```text
User:

How long do Pro customers have to request a refund?
```

The answer exists inside:

```text
refund_policy.md
```

But the base LLM has never seen NovaTech's internal policies.

We will compare:

```text
LLM without RAG
```

against:

```text
LLM + RAG
```

---

# 5. Project Structure

Create the following project:

```text
rag_lab/

├── app.py
├── rag.py
├── requirements.txt
├── .env
│
├── knowledge_base/
│   ├── employee_benefits.md
│   ├── vacation_policy.md
│   ├── remote_work_policy.md
│   ├── security_policy.md
│   ├── pricing.md
│   ├── refund_policy.md
│   ├── enterprise_plan.md
│   ├── product_features.md
│   ├── api_limits.md
│   └── customer_support.md
│
└── benchmark/
    └── questions.json
```

---

# 6. Step 1 — Build the Knowledge Base

Create several small fictional documents.

For example:

## refund_policy.md

```markdown
# NovaTech Refund Policy

Customers subscribed to the Pro plan may request a full refund
within 14 calendar days of their initial purchase.

Enterprise subscriptions are non-refundable after the contract
has been signed.

Monthly Basic subscriptions can be canceled at any time,
but previously charged subscription fees are not refunded.
```

## remote_work_policy.md

```markdown
# NovaTech Remote Work Policy

Employees may work remotely up to three days per week.

Employees must work from their assigned office at least two
days per week.

Fully remote arrangements require approval from both the
employee's manager and Human Resources.
```

## api_limits.md

```markdown
# NovaTech API Limits

Basic customers may make up to 100 API requests per minute.

Pro customers may make up to 1,000 API requests per minute.

Enterprise customers receive configurable API rate limits
based on their contract.

When the rate limit is exceeded, the API returns HTTP 429.
```

Create enough documents that retrieval actually has to determine which information is relevant.

---

# 7. Step 2 — Ask the LLM Without RAG

Before building RAG, establish a baseline.

Ask:

```text
How long do NovaTech Pro customers have to request a refund?
```

Send only the question to the LLM.

Conceptually:

```python
response = client.responses.create(
    model="YOUR_MODEL",
    input=question
)
```

The model does not have access to NovaTech's private documents.

Therefore it may:

- say it doesn't know
- guess
- produce a plausible answer
- hallucinate a policy

Record the answer.

This becomes our baseline.

---

# 8. Step 3 — Load the Documents

Next, load every `.md` file from the knowledge-base directory.

Conceptually:

```python
documents = []

for file in knowledge_base:
    text = read(file)

    documents.append({
        "source": filename,
        "text": text
    })
```

Each document should retain metadata.

For example:

```json
{
    "source": "refund_policy.md",
    "text": "Customers subscribed to the Pro plan..."
}
```

Metadata becomes important later because we want the system to provide sources.

---

# 9. Step 4 — Chunk the Documents

LLMs and retrieval systems generally should not retrieve entire large documents.

Instead, documents are divided into smaller pieces called:

**chunks**

Example:

```text
Original Document
────────────────────────

Paragraph 1
Paragraph 2
Paragraph 3
Paragraph 4
Paragraph 5


After Chunking
────────────────────────

Chunk 1
Paragraph 1
Paragraph 2

Chunk 2
Paragraph 3
Paragraph 4

Chunk 3
Paragraph 5
```

For the first experiment, use something like:

```text
Chunk size: 500 characters/tokens
Overlap: 50
```

The exact unit depends on your implementation.

---

# 10. Why Chunking Matters

Imagine a 100-page employee handbook.

A question asks:

```text
How many remote days are employees allowed?
```

Sending the entire handbook would:

- consume unnecessary tokens
- increase cost
- increase latency
- potentially distract the model
- eventually exceed context limits

Instead, RAG tries to retrieve only something like:

```text
Employees may work remotely up to three days per week.
```

This is one of the central ideas behind RAG:

> Give the model the smallest amount of highly relevant information needed to answer the question.

---

# 11. Step 5 — Generate Embeddings

Now convert each chunk into an embedding.

An embedding is a numerical representation of meaning.

Conceptually:

```text
"Employees may work remotely three days per week."

        ↓ embedding model

[0.013, -0.82, 0.114, 0.392, ...]
```

Another sentence:

```text
"What is the company's work-from-home policy?"

        ↓ embedding model

[0.021, -0.79, 0.121, 0.401, ...]
```

Because these sentences are semantically related, their vectors should be relatively close in embedding space.

---

# 12. Embeddings vs LLM Generation

Do not confuse these two operations.

### Embedding model

Input:

```text
Remote employees may work from home three days per week.
```

Output:

```text
[0.023, -0.421, 0.882, ...]
```

Its job is:

**represent meaning numerically.**

### Generative LLM

Input:

```text
What is NovaTech's remote-work policy?
```

Output:

```text
Employees may work remotely up to three days per week.
```

Its job is:

**generate language.**

RAG usually uses both.

---

# 13. Step 6 — Store the Embeddings

Store the chunk embeddings in a vector index.

For this lab, use **FAISS** or **Chroma**.

Conceptually the database contains:

```text
Vector Database

Vector A
Text: refund policy...
Source: refund_policy.md

Vector B
Text: remote work policy...
Source: remote_work_policy.md

Vector C
Text: API rate limits...
Source: api_limits.md

Vector D
Text: vacation policy...
Source: vacation_policy.md
```

---

# 14. Step 7 — Embed the User Question

Now the user asks:

```text
How long do Pro customers have to request their money back?
```

Notice something important.

The document says:

```text
request a full refund within 14 calendar days
```

The question says:

```text
request their money back
```

Keyword search might struggle with this variation.

Semantic retrieval can recognize "money back" and "refund" as related concepts.

Generate an embedding for the question.

```text
Question

"How long do Pro customers have to request their money back?"

        ↓

Embedding Model

        ↓

Query Vector
```

---

# 15. Step 8 — Vector Search

Compare the query vector against the document chunk vectors.

Conceptually:

```text
Query Vector
      ↓
Similarity Search
      ↓

#1 refund_policy.md        0.91
#2 pricing.md              0.73
#3 enterprise_plan.md      0.65
#4 customer_support.md     0.49
```

Retrieve the top results.

For example, `Top-K = 3` means:

> Return the three most relevant chunks.

---

# 16. Step 9 — Inspect Retrieval Before Calling the LLM

This is extremely important.

Do NOT immediately send the results to the LLM.

Display the retrieved chunks first.

Example:

```text
QUESTION

How long do Pro customers have to request their money back?


RETRIEVED CHUNKS

#1 — score 0.91
Source: refund_policy.md

Customers subscribed to the Pro plan may request a full
refund within 14 calendar days of their initial purchase.


#2 — score 0.73
Source: pricing.md

The Pro plan costs $49 per month...


#3 — score 0.65
Source: enterprise_plan.md

Enterprise plans require an annual contract...
```

Ask:

**Did retrieval find the evidence needed to answer the question?**

If yes, retrieval succeeded.

If not, generation cannot reliably fix the problem.

This leads to a critical RAG principle:

> Retrieval failure and generation failure are different problems.

---

# 17. Step 10 — Build the Augmented Prompt

Now construct the LLM prompt.

Instead of:

```text
How long do Pro customers have to request a refund?
```

send:

```text
You are a company knowledge assistant.

Answer the question using only the provided context.

If the answer cannot be found in the context, say:

"I don't have enough information in the knowledge base."

CONTEXT:

[refund_policy.md]
Customers subscribed to the Pro plan may request a full
refund within 14 calendar days of their initial purchase.

[pricing.md]
The Pro plan costs $49 per month.

QUESTION:

How long do Pro customers have to request a refund?
```

This is the **Augmented** part of Retrieval-Augmented Generation.

---

# 18. Step 11 — Generate the Answer

The LLM should now respond with something like:

```text
Pro customers may request a full refund within
14 calendar days of their initial purchase.

Source: refund_policy.md
```

The full pipeline is now:

```text
Question
   ↓
Embedding
   ↓
Vector Search
   ↓
Top-K Chunks
   ↓
Build Context
   ↓
LLM Prompt
   ↓
Answer
```

Congratulations.

You have built a basic RAG system.

---

# 19. Build the Streamlit Demo

Create a simple interface.

```text
┌────────────────────────────────────────────────────┐
│                  RAG PLAYGROUND                    │
├────────────────────────────────────────────────────┤
│                                                    │
│ Ask NovaTech                                       │
│                                                    │
│ [ How long is the Pro refund period?             ] │
│                                                    │
│ [Ask Without RAG]       [Ask With RAG]             │
│                                                    │
├───────────────────────┬────────────────────────────┤
│ WITHOUT RAG           │ WITH RAG                   │
│                       │                            │
│ I don't know the      │ Pro customers have         │
│ company's specific    │ 14 calendar days...        │
│ policy...             │                            │
│                       │ Source: refund_policy.md   │
├───────────────────────┴────────────────────────────┤
│ RETRIEVED CONTEXT                                  │
│                                                    │
│ #1 refund_policy.md                  score: .91    │
│ Customers subscribed to Pro...                     │
│                                                    │
│ #2 pricing.md                        score: .73    │
│ The Pro subscription costs...                      │
└────────────────────────────────────────────────────┘
```

The important part of the UI is not the chatbot.

The important part is making the RAG pipeline visible.

---

# 20. Experiment 1 — No RAG vs RAG

Run the same question through both systems.

### System A

```text
Question → LLM
```

### System B

```text
Question
   ↓
Retrieval
   ↓
Context
   ↓
LLM
```

Compare:

| Metric | No RAG | RAG |
| --- | --- | --- |
| Correct answer | ? | ? |
| Uses company data | No | Yes |
| Source provided | No | Yes |
| Grounded | Low/Unknown | Higher |
| Retrieval latency | 0 | Added |
| Token usage | Lower | Higher |

Discuss:

> When is the additional complexity of RAG worth it?

---

# 21. Experiment 2 — Top-K

Now change:

```text
Top-K = 1
Top-K = 3
Top-K = 5
```

Ask the same question.

Observe the retrieved context.

### K = 1

Advantages:

- less context
- cheaper
- faster
- less noise

Risk:

The correct evidence may not be the #1 result.

### K = 5

Advantages:

- higher chance of retrieving evidence

Risks:

- more irrelevant information
- higher token usage
- potentially more confusion

This demonstrates an important tradeoff:

```text
Recall
  ↑

More retrieved documents

  ↓

More noise + more tokens
```

---

# 22. Experiment 3 — Chunk Size

Try:

```text
Chunk size = 200
Chunk size = 500
Chunk size = 1000
```

Observe what happens.

Very small chunks may lose context.

Example:

```text
Chunk 1:
Pro customers may request refunds.

Chunk 2:
The refund period is 14 days.
```

If only Chunk 1 is retrieved, critical information is missing.

But extremely large chunks may contain too much unrelated information.

Therefore:

```text
Small chunks
→ precise
→ potentially incomplete

Large chunks
→ more context
→ potentially noisy
```

There is no universally perfect chunk size.

---

# 23. Experiment 4 — Unanswerable Question

Ask:

```text
Does NovaTech reimburse gym memberships?
```

Assume none of the documents mention gym memberships.

A weak RAG system might still produce:

```text
NovaTech provides employees with a $50 monthly
fitness reimbursement.
```

That sounds plausible.

But it is hallucinated.

A better answer is:

```text
I don't have enough information in the knowledge base
to answer that question.
```

This demonstrates an important principle:

> A production RAG system needs to know when its evidence is insufficient.

---

# 24. Experiment 5 — Semantic Search

Ask:

```text
How long do I have to get my money back?
```

But the document uses "refund", not "money back".

The retrieval system should ideally still find `refund_policy.md`.

This demonstrates why embeddings are useful.

Retrieval is based on semantic similarity rather than exact keyword matching.

---

# 25. Experiment 6 — Retrieval Failure

Create a difficult question.

For example:

```text
Can a Pro customer cancel after ten days and still
receive their payment back?
```

Inspect the retrieved chunks.

If the correct policy isn't retrieved, ask:

Is this an LLM problem?

Not necessarily.

It may be a **retrieval problem**.

Potential fixes include:

```text
better chunking
better embeddings
larger Top-K
query rewriting
metadata filtering
hybrid search
reranking
```

This distinction becomes extremely important in production RAG systems.

---

# 26. Benchmark the System

Now stop manually trying individual questions.

Create `benchmark/questions.json`.

Example:

```json
[
  {
    "question": "How many remote days are employees allowed?",
    "expected_answer": "3 days",
    "evidence": "remote_work_policy.md"
  },
  {
    "question": "How long is the Pro refund period?",
    "expected_answer": "14 calendar days",
    "evidence": "refund_policy.md"
  },
  {
    "question": "What is the Pro API rate limit?",
    "expected_answer": "1000 requests per minute",
    "evidence": "api_limits.md"
  },
  {
    "question": "Does NovaTech reimburse gym memberships?",
    "expected_answer": "NOT_FOUND",
    "evidence": null
  }
]
```

Run every question automatically.

---

# 27. Evaluate Retrieval Separately

Before evaluating the final answer, evaluate retrieval.

For each benchmark question ask:

```text
Was the correct evidence retrieved?
```

Example:

```text
Question:
How long is the Pro refund period?

Expected evidence:
refund_policy.md

Retrieved:
1. pricing.md
2. refund_policy.md
3. customer_support.md
```

The correct evidence appears in Top-3.

Therefore:

```text
Evidence Recall@3 = success
```

Across 10 questions:

```text
Correct evidence retrieved: 8

Evidence Recall@3 = 8 / 10 = 80%
```

This metric tells us whether retrieval is working.

---

# 28. Evaluate the Final Answer

Next evaluate generation.

Possible metrics:

- **Answer Correctness** — Does the answer match the expected answer?
- **Groundedness** — Is the answer supported by retrieved evidence?
- **Citation Correctness** — Does the cited document actually support the answer?
- **Abstention Accuracy** — When the answer isn't available, does the model correctly refuse to invent one?
- **Latency** — How long does the entire request take?
- **Token Usage** — How many input/output tokens are used?

---

# 29. Add a Metrics Panel

The Streamlit app can show:

```text
RAG METRICS

Retrieval latency:       82 ms
Generation latency:      1.24 sec
Total latency:           1.32 sec

Retrieved chunks:        3
Context tokens:          612
Output tokens:           43

Top similarity score:    0.91
```

This reinforces that RAG is an engineering system—not simply a prompt.

---

# 30. Final Benchmark Table

Display something like:

| Question | Evidence Found | Correct Answer | Grounded | Latency |
| --- | --- | --- | --- | --- |
| Remote days | ✓ | ✓ | ✓ | 1.2s |
| Refund | ✓ | ✓ | ✓ | 1.3s |
| API limit | ✓ | ✓ | ✓ | 1.1s |
| Gym benefit | N/A | ✓ abstain | ✓ | 1.2s |
| Enterprise refund | ✓ | ✓ | ✓ | 1.4s |

Then calculate:

```text
Evidence Recall@3
Answer Accuracy
Groundedness
Abstention Accuracy
Average Latency
```

---

# 31. Debugging RAG

When the system produces a wrong answer, don't immediately blame the LLM.

Debug the pipeline in order.

## Step 1 — Check Retrieval

Did we retrieve the correct evidence?

If NO → **retrieval problem**. Investigate:

- chunking
- embeddings
- query formulation
- Top-K
- metadata
- vector search

If YES, continue.

## Step 2 — Check Context

Did we provide the correct chunks to the model?

If NO → **context construction problem**.

If YES, continue.

## Step 3 — Check Generation

Did the LLM correctly interpret the evidence?

If NO → **generation/prompt problem**.

This gives us:

```text
Wrong Answer
     ↓
Was evidence retrieved?
     ↓
 NO ─────→ Retrieval problem
     ↓ YES
Was evidence included?
     ↓
 NO ─────→ Context problem
     ↓ YES
Did LLM use evidence correctly?
     ↓
 NO ─────→ Generation problem
```

---

# 32. Important Concept — RAG Does Not Train the LLM

Suppose we add `refund_policy.md` to our vector database.

Did the LLM learn NovaTech's refund policy?

**No.**

We did not modify the model's weights.

Instead:

```text
Document
   ↓
Vector Database

Later...

Question
   ↓
Retrieve Document
   ↓
Put Document in Prompt
   ↓
LLM reads it
```

The model receives the information at inference time.

This is fundamentally different from pretraining or fine-tuning.

---

# 33. RAG vs Long Context

A natural question is:

> Why don't we simply put every document into the prompt?

For very small knowledge bases, you sometimes can.

But as the knowledge base grows:

```text
10 documents
100 documents
10,000 documents
1,000,000 documents
```

sending everything becomes inefficient or impossible.

RAG attempts to find:

```text
Large Knowledge Base

        ↓

Relevant 3–10 chunks

        ↓

LLM
```

rather than:

```text
Entire Knowledge Base

        ↓

LLM
```

---

# 34. RAG vs Fine-Tuning

Another important distinction:

### RAG

Best for:

```text
Knowledge
Facts
Policies
Documents
Frequently changing information
Private company data
```

### Fine-Tuning

Often better suited for:

```text
Behavior
Style
Format
Task patterns
Specialized response behavior
```

A useful mental model:

```text
Need the model to KNOW something current/private?

→ Consider RAG


Need the model to BEHAVE differently?

→ Consider fine-tuning/prompting
```

This is simplified, but useful when first learning the concepts.

---

# 35. Production RAG Is More Than Vector Search

Our lab builds:

```text
Question
 ↓
Embedding
 ↓
Vector Search
 ↓
Top-K
 ↓
LLM
```

Real production systems can become:

```text
User Question
      ↓
Query Understanding
      ↓
Query Rewriting
      ↓
┌──────────────────────┐
│ Keyword Search       │
│ Vector Search        │
│ Metadata Filtering   │
└──────────────────────┘
      ↓
Candidate Documents
      ↓
Reranker
      ↓
Top Relevant Evidence
      ↓
Context Construction
      ↓
LLM
      ↓
Grounded Answer
      ↓
Citation Verification
```

This introduces concepts such as:

- hybrid search
- BM25
- metadata filtering
- reranking
- query expansion
- query rewriting
- contextual retrieval
- multi-query retrieval
- citation verification

We do NOT need to implement all of these in Week 3.

The goal is to first understand the basic pipeline.

---

# 36. Recommended Demo Flow During the Meeting

## Part 1 — Explain RAG (10 minutes)

Draw:

```text
Documents
 ↓
Chunks
 ↓
Embeddings
 ↓
Vector DB

Question
 ↓
Embedding
 ↓
Search
 ↓
Context
 ↓
LLM
 ↓
Answer
```

## Part 2 — Ask Without RAG (5 minutes)

Ask:

```text
What is NovaTech's Pro refund policy?
```

Observe the result.

## Part 3 — Inspect the Knowledge Base (5 minutes)

Show:

```text
refund_policy.md
pricing.md
api_limits.md
remote_work_policy.md
...
```

## Part 4 — Show Chunking (10 minutes)

Display the chunks.

Discuss why chunk size matters.

## Part 5 — Show Embeddings and Retrieval (10 minutes)

Ask:

```text
How long do I have to get my money back?
```

Show:

```text
#1 refund_policy.md       .91
#2 pricing.md             .73
#3 customer_support.md    .55
```

This is the most important moment of the demo.

## Part 6 — Generate the RAG Answer (10 minutes)

Show the actual prompt:

```text
Context
+
Question
↓
LLM
↓
Answer
```

Then compare WITHOUT RAG vs WITH RAG.

## Part 7 — Break the System (15 minutes)

Change Top-K, chunk size, and question wording.

Try an unanswerable question.

Observe failures.

## Part 8 — Run the Benchmark (15 minutes)

Run 10–20 questions.

Display:

```text
Evidence Recall
Answer Accuracy
Groundedness
Latency
```

## Part 9 — Discussion (10 minutes)

Ask the group:

1. What happens when retrieval fails?
2. Can a good LLM fix bad retrieval?
3. Why not send every document?
4. When would keyword search outperform vector search?
5. How would you detect hallucination?
6. What should happen when evidence is missing?
7. How would this architecture change with 1 million documents?

---

# 37. Homework / Challenge

Choose one improvement.

### Level 1

Change Top-K, chunk size, or chunk overlap. Measure the result.

### Level 2

Add metadata filtering.

Example:

```text
department = HR
document_type = policy
```

### Level 3

Implement hybrid retrieval:

```text
Vector Search
+
Keyword Search
```

### Level 4

Add a reranker:

```text
Initial Retrieval

Top 20

↓

Reranker

↓

Top 3

↓

LLM
```

### Level 5

Create a real knowledge base using:

```text
your own project documentation
company policies
GitHub documentation
research papers
product specifications
```

---

# 38. Key Takeaways

If you remember only five things from this lab, remember these:

### 1. RAG is not training.

RAG provides external knowledge to an LLM at inference time.

### 2. Retrieval and generation are different systems.

A bad answer can originate from either one.

### 3. Retrieval quality matters enormously.

If the correct evidence never reaches the LLM, even an excellent model may fail.

### 4. More context is not always better.

Good RAG tries to provide the **right context**, not the maximum context.

### 5. Evaluate retrieval separately from generation.

Don't only ask:

```text
Did the chatbot answer correctly?
```

Also ask:

```text
Did we retrieve the correct evidence?
```

That distinction is fundamental to building reliable RAG systems.

---

# Final Mental Model

Think of RAG as an **open-book exam**.

Without RAG:

```text
Student receives question
        ↓
Answer from memory
```

With RAG:

```text
Student receives question
        ↓
Searches textbook
        ↓
Finds relevant pages
        ↓
Reads evidence
        ↓
Answers question
        ↓
Cites source
```

The LLM is the student.

The vector database is the search system.

The knowledge base is the textbook.

Retrieval finds the relevant pages.

The context window is the material placed on the student's desk.

And the final answer should be grounded in the evidence that was actually retrieved.
