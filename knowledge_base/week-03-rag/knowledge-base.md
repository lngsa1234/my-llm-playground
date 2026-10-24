# Week 3 — Retrieval-Augmented Generation (RAG)

**Learning goal:** Understand why RAG exists, how a basic RAG pipeline works, and how retrieval quality affects the final LLM answer.

## 1. What Is RAG?

**RAG = Retrieval-Augmented Generation.**

RAG is an architecture that combines **information retrieval** with an **LLM**.

Instead of asking an LLM to answer a question using only knowledge learned during training, a RAG system first searches an external knowledge source for relevant information. That information is then supplied to the LLM as context.

```text
User Question
      ↓
Retrieve Relevant Information
      ↓
Build Context
      ↓
LLM
      ↓
Grounded Answer
```

A useful mental model is:

> **RAG = Search + Context Engineering + Generation**

The retriever's job is to **find evidence**.

The LLM's job is to **reason over that evidence and communicate an answer**.

## 2. Why Do We Need RAG?

Imagine asking an LLM:

> "What is our company's cancellation policy?"

A general-purpose LLM probably wasn't trained on your internal policy. Even if you paste the policy into one conversation, that doesn't create a scalable knowledge system.

RAG solves this by connecting the LLM to external knowledge such as:

```text
PDFs
Documentation
Internal policies
Product specifications
Research papers
Support tickets
Notion pages
Web pages
Databases
Company knowledge bases
```

### Four major reasons to use RAG

**Private knowledge**

```text
LLM training data
      ✗
Your internal documents

RAG
      ↓
Internal documents
      ↓
LLM
```

**Current knowledge**

A model's training knowledge is not automatically the same thing as your current database or latest documents.

RAG can retrieve recently updated information.

**Grounding**

Instead of letting the model answer freely:

```text
Question
   ↓
LLM
   ↓
"I think the answer is..."
```

RAG attempts:

```text
Question
   ↓
Evidence
   ↓
LLM
   ↓
"Based on this evidence..."
```

**Traceability**

A good RAG system can tell users which documents or passages support an answer.

## 3. RAG vs. Prompting vs. Fine-Tuning

These approaches solve different problems.

| Approach | Primary purpose |
| --- | --- |
| Prompt engineering | Tell the model **how to behave** |
| Context engineering | Give the model the **right information/state** |
| RAG | Dynamically **retrieve external knowledge** |
| Fine-tuning | Change model **behavior or learned patterns** |

Suppose you have 100,000 internal documents.

Putting all of them in a prompt is impractical.

Fine-tuning is usually not the right mechanism for continuously changing factual knowledge either.

RAG allows you to retrieve only the relevant information.

```text
100,000 documents
       ↓
    Retrieval
       ↓
5 relevant chunks
       ↓
     Prompt
       ↓
      LLM
```

---

## 4. The Two Sides of RAG

A basic RAG system has two major pipelines.

### Pipeline A — Indexing

Usually performed when documents are added or updated.

```text
Documents
    ↓
Parsing / Cleaning
    ↓
Chunking
    ↓
Embeddings
    ↓
Index / Vector Store
```

### Pipeline B — Retrieval + Generation

Performed when the user asks a question.

```text
User Question
      ↓
Query Processing
      ↓
Retrieval
      ↓
Relevant Chunks
      ↓
Prompt Construction
      ↓
LLM
      ↓
Answer
```

Understanding the distinction between **index time** and **query time** is fundamental.

## 5. Documents

Everything starts with a knowledge source.

For example:

```text
employee_handbook.pdf
product_manual.pdf
engineering_specs.md
support_articles/
```

A document may contain:

```text
Title
Sections
Paragraphs
Tables
Images
Metadata
```

Real-world RAG systems often fail before embeddings are even involved because document extraction is poor.

For example, a PDF table might be extracted as:

```text
Premium
8
monthly
coffee
chat
$19.99
```

instead of preserving the relationships between the fields.

The retrieval system can only retrieve what the ingestion pipeline successfully represents.

## 6. Chunking

Documents are usually too large to retrieve as complete objects.

Therefore we split them into smaller pieces called **chunks**.

Imagine a 40-page employee handbook.

Instead of:

```text
Employee Handbook
      ↓
one giant embedding
```

we might create:

```text
Chunk 1 — Vacation Policy
Chunk 2 — Sick Leave
Chunk 3 — Parental Leave
Chunk 4 — Health Insurance
Chunk 5 — Remote Work
...
```

Now retrieval can find the relevant section.

## 7. Why Chunking Matters

Consider the question:

> "How many vacation days do new employees receive?"

If the relevant paragraph is buried inside a huge chunk containing many unrelated topics, retrieval may perform poorly.

But chunks that are too small also lose context.

For example:

```text
Chunk 1:
Employees receive

Chunk 2:
15 days

Chunk 3:
of paid vacation annually.
```

None of those chunks alone contains the complete fact.

This creates a central RAG tradeoff:

```text
Smaller chunks
→ precise retrieval
→ less context

Larger chunks
→ more context
→ more irrelevant information
```

There is no universally correct chunk size.

## 8. Chunking Strategies

### Fixed-size chunking

Split every N tokens.

```text
Chunk 1 = tokens 1–500
Chunk 2 = tokens 451–950
Chunk 3 = tokens 901–1400
```

Simple and useful as a baseline.

### Recursive chunking

Try natural separators first:

```text
Section
↓
Paragraph
↓
Sentence
↓
Tokens
```

This often preserves structure better than arbitrary splitting.

### Structure-aware chunking

Respect document boundaries such as:

```text
Chapter
Section
Subsection
Paragraph
```

For example:

```text
## Refund Policy

Customers may cancel...
```

can remain a logical unit.

### Semantic chunking

Attempt to create boundaries when the topic changes.

Potentially better conceptually, but more complicated and computationally expensive.

---

## 9. Chunk Overlap

Chunks sometimes overlap.

For example:

```text
Chunk 1:
tokens 1–500

Chunk 2:
tokens 451–950
```

Tokens 451–500 appear in both chunks.

Why?

Important information might occur near a boundary.

Without overlap:

```text
Chunk A:
The cancellation policy requires users to...

---------------- boundary ----------------

Chunk B:
...provide 48 hours notice.
```

Neither chunk contains the complete idea.

Overlap can help preserve continuity, although excessive overlap creates duplicated retrieval results and increases storage/context cost.

## 10. Metadata

Chunks should normally retain metadata.

For example:

```json
{
  "text": "Employees receive 15 vacation days...",
  "document": "employee_handbook.pdf",
  "section": "Vacation Policy",
  "page": 23,
  "updated_at": "2026-09-01"
}
```

Metadata enables filtering.

For example:

> Search only HR documents updated after January 2026.

Metadata also enables better citations.

## 11. Embeddings

Computers need a numerical representation of text for dense semantic retrieval.

An **embedding model** converts text into a vector.

Conceptually:

```text
"How much vacation do employees get?"
              ↓
       Embedding Model
              ↓
[0.12, -0.34, 0.91, ...]
```

A document chunk also receives an embedding:

```text
"Employees receive 15 days of paid vacation."
              ↓
       Embedding Model
              ↓
[0.15, -0.30, 0.88, ...]
```

Because the meanings are related, their vectors should be relatively close according to the retrieval metric.

## 12. Embeddings Are Not LLM Answers

A common beginner misunderstanding is:

> Does the embedding model understand the question and answer it?

Not in the RAG pipeline.

Its main role here is to produce a numerical representation useful for comparing semantic similarity.

Think of:

```text
Embedding model → representation / retrieval

LLM → reasoning / generation
```

They solve different problems.

## 13. Semantic Search

Traditional keyword search might struggle with:

> "How much time can I take off?"

when the document says:

> "Employees receive 15 days of annual paid vacation."

There may be little exact word overlap.

Semantic retrieval attempts to recognize that:

```text
time off
vacation
annual leave
PTO
```

can have related meanings.

This is one reason embeddings became important in RAG systems.

## 14. Similarity

The system compares the query embedding with document embeddings.

Conceptually:

```text
Query vector
     ↓
Compare against
     ↓
Chunk A vector
Chunk B vector
Chunk C vector
...
```

A commonly encountered metric is **cosine similarity**:

$$
\text{cosine similarity}(A,B) = \frac{A \cdot B}{\|A\|\,\|B\|}
$$

For beginners, the important intuition is:

> The retrieval system needs a way to rank vectors according to similarity.

You do not need to understand the mathematics deeply to build your first RAG application.

## 15. Vector Stores and Vector Databases

After creating embeddings, we need somewhere to store and search them.

Conceptually:

```text
Chunk
+ Embedding
+ Metadata
       ↓
Vector Store / Search Index
```

Example record:

```text
Text:
"Employees receive 15 days..."

Vector:
[0.15, -0.30, ...]

Metadata:
document = employee_handbook
section = vacation
page = 23
```

A query searches this index for similar vectors.

## 16. Top-K Retrieval

Suppose a user asks:

> "What is the parental leave policy?"

The system could retrieve the five most relevant chunks.

```text
Query
 ↓
Retriever
 ↓
Top 5

Chunk 31   0.91
Chunk 72   0.87
Chunk 18   0.82
Chunk 44   0.76
Chunk 11   0.72
```

This is often called **Top-K retrieval**.

If:

```text
K = 3
```

the system returns three candidates.

Increasing K may improve the chance of finding the necessary evidence, but it also increases the amount of potentially irrelevant context passed downstream.

## 17. Dense vs. Sparse Retrieval

RAG does not mean "vector search only."

There are multiple retrieval families.

### Sparse / lexical retrieval

Methods such as **BM25** rely heavily on lexical signals.

Excellent for things such as:

```text
Error code: XG-4297
Product ID: AX104
API function names
Exact terminology
Names
```

### Dense retrieval

Uses embeddings and semantic similarity.

Often useful when wording differs:

```text
Query:
"Can I work from home?"

Document:
"Employees may perform their duties remotely..."
```

---

## 18. Hybrid Search

Production RAG systems often combine lexical and semantic retrieval.

```text
              Query
             /     \
            /       \
        BM25        Dense
        Search      Search
            \       /
             \     /
           Combine
              ↓
           Results
```

This is commonly called **hybrid retrieval/search**.

It can capture both exact terminology and semantic similarity.

## 19. Reranking

The initial retriever may return 20 candidates.

Instead of putting all 20 into the LLM context, another model can rerank them.

```text
Query
 ↓
Retrieve 20 candidates
 ↓
Reranker
 ↓
Best 5
 ↓
LLM
```

The first retrieval stage emphasizes efficiently finding candidates.

The reranker spends more computation determining which candidates are most relevant.

This architecture is extremely useful:

> **Retrieve broadly → rank carefully → generate from the best evidence.**

## 20. Prompt Construction

Once evidence is retrieved, it must be supplied to the LLM.

Example:

```text
SYSTEM

Answer the user's question using only the supplied context.
If the context does not contain enough information, say so.
Cite the supporting source.

CONTEXT

[Document A, page 23]
Employees receive 15 paid vacation days annually.

[Document B, page 8]
Vacation benefits begin after the probationary period.

USER QUESTION

How much vacation do employees receive?
```

The LLM might generate:

```text
Employees receive 15 paid vacation days annually.

Source: Employee Handbook, p. 23.
```

## 21. Grounding

A **grounded answer** should be supported by the provided evidence.

Suppose context says:

> Employees receive 15 vacation days.

But the model answers:

> Employees receive 20 vacation days.

The answer is not grounded in the retrieved evidence.

RAG reduces some hallucination risks, but **RAG does not eliminate hallucination**.

The model can still misread evidence, combine facts incorrectly, or introduce unsupported claims.

## 22. RAG Has Two Quality Problems

This distinction is one of the most important concepts in Week 3.

Suppose the final answer is wrong.

Why?

### Retrieval failure

The necessary evidence never reached the model.

```text
Knowledge Base
      ↓
Retriever
      ↓
WRONG CHUNKS
      ↓
LLM
```

### Generation failure

The correct evidence was retrieved, but the model produced an incorrect answer.

```text
Knowledge Base
      ↓
Retriever
      ↓
CORRECT EVIDENCE
      ↓
LLM
      ↓
WRONG ANSWER
```

These require different fixes.

That means you should not evaluate a RAG system with only:

> "Did the final answer look good?"

## 23. Evaluating Retrieval

Assume a benchmark question requires two pieces of evidence:

```text
Relevant chunks:
D7
D19
```

Your retriever returns:

```text
D7
D3
D19
D42
D8
```

It successfully retrieved both required pieces.

### Recall@K

Conceptually:

$$
\text{Recall@K} = \frac{\text{relevant evidence retrieved in Top K}}{\text{total relevant evidence}}
$$

If two relevant chunks exist and both are retrieved:

```text
Recall@5 = 2/2 = 100%
```

If only one is retrieved:

```text
Recall@5 = 1/2 = 50%
```

This answers:

> **Did retrieval find the evidence we needed?**

---

## 24. Precision@K

Suppose Top-5 returns:

```text
Relevant
Irrelevant
Relevant
Irrelevant
Irrelevant
```

Two of five results are relevant.

$$
\text{Precision@5} = 2/5 = 40\%
$$

Precision asks:

> **How much of what we retrieved was actually relevant?**

There is often tension between recall and precision.

Retrieving more documents can increase recall while adding noise.

---

## 25. Evidence Recall vs. Fact Coverage

These concepts can be confused.

Imagine the correct answer requires three facts:

```text
Fact A
Fact B
Fact C
```

The retrieved evidence supports:

```text
Fact A ✓
Fact B ✓
Fact C ✗
```

Then the retrieved context does not fully cover what is needed for the answer.

A useful conceptual distinction is:

**Evidence recall**

> Did we retrieve the relevant source evidence?

**Fact coverage**

> Does the retrieved context contain the facts required to answer the question?

They are related but not necessarily identical, especially when multiple chunks contain overlapping evidence.

---

## 26. Evaluating Generation

Once good evidence reaches the model, we evaluate the answer.

Important dimensions include:

### Answer correctness

Is the answer correct relative to a reference or expected result?

### Faithfulness / groundedness

Are the claims actually supported by retrieved context?

### Relevance

Does the answer address the question?

### Completeness

Does it include the important information needed to answer fully?

A response can be correct but poorly grounded.

For example, the model might know the answer from training even though retrieval failed.

That's dangerous because your benchmark could appear successful while your RAG pipeline is broken.

---

## 27. End-to-End Evaluation

A useful evaluation framework is:

```text
                RAG Evaluation

          ┌────────────┴────────────┐
          ↓                         ↓

    Retrieval Quality         Generation Quality

    Recall@K                  Correctness
    Precision@K               Faithfulness
    Ranking quality           Relevance
    Evidence coverage         Completeness
```

Then add system measurements:

```text
Latency
Cost
Token usage
Failure rate
```

This gives you a much more realistic picture than one overall "accuracy" number.

---

## 28. Common RAG Failure Modes

### Failure 1 — Bad chunking

The required information is separated from its context.

**Possible fix:** change chunking strategy or preserve document structure.

### Failure 2 — Retrieval misses the evidence

The correct chunk exists but is not returned.

**Possible fixes:** improve embeddings, increase K, add lexical/hybrid retrieval, rewrite the query, improve metadata.

### Failure 3 — Too much context

You retrieve 30 chunks and dump everything into the prompt.

More context is **not automatically better**.

Noise can distract the model and increases latency/cost.

### Failure 4 — Duplicate chunks

Large overlaps can cause nearly identical chunks to dominate retrieval.

### Failure 5 — Exact terms are missed

Embedding retrieval may not be ideal for an exact code such as:

```text
RCV-SYS-002
```

Lexical or hybrid retrieval may perform better.

### Failure 6 — Correct evidence, wrong answer

Retrieval worked; generation failed.

Changing the vector database will probably not fix this problem.

Instead investigate prompt construction, context formatting, model choice, reasoning requirements, or contradictory evidence.

### Failure 7 — No evidence exists

The knowledge base simply does not contain the answer.

A robust system should be able to respond:

> "I don't have enough information in the available sources."

rather than fabricate an answer.

---

## 29. Query Transformation

Sometimes the user's original query is not ideal for retrieval.

For example:

```text
"What about PTO after having a baby?"
```

A query transformation step could produce:

```text
parental leave policy
maternity leave
paid time off after childbirth
```

Then retrieval runs against these improved queries.

This is one example of **advanced RAG**.

---

## 30. Multi-Query Retrieval

Instead of performing one search:

```text
User question
      ↓
one query
```

generate several search queries:

```text
User question
      ↓
Query A
Query B
Query C
      ↓
Retrieve
      ↓
Merge
```

This may improve recall for ambiguous or multi-faceted questions.

The tradeoff is more latency, cost, and duplicate results.

---

## 31. Parent-Child Retrieval

Small chunks can retrieve precisely, while large chunks preserve context.

Parent-child retrieval tries to get both benefits.

```text
Large Parent Section
        ↓
   Small Chunks

Child A
Child B
Child C
Child D
```

Search against small child chunks.

If Child C matches, return Child C's larger parent section to the LLM.

This separates:

> **What representation is best for retrieval?**

from:

> **What context is best for generation?**

That is a powerful RAG design principle.

---

## 32. Contextual Retrieval

A chunk can lose meaning when removed from its original document.

Example:

```text
"It must be submitted within 30 days."
```

What is "it"?

Contextualization can attach additional document context so retrieval has a better representation of the chunk.

Conceptually:

```text
Original chunk
+
Document/section context
      ↓
Better retrieval representation
```

---

## 33. RAG vs. Long Context

Modern models can accept increasingly large contexts.

So why not just put every document into the prompt?

Sometimes that is reasonable for a small corpus.

But with large knowledge bases:

```text
10 documents → maybe

1,000 documents → difficult

1,000,000 documents → retrieval required
```

RAG helps select the small subset likely to matter.

The real design question is therefore not:

> "RAG or long context?"

It is often:

> **How much should we retrieve, and how should we construct the final context?**

---

## 34. RAG vs. Fine-Tuning

Another common misconception:

> "Why don't we fine-tune the model on our documents?"

Fine-tuning is typically better suited to changing **behavior, style, format, or task patterns** than acting as a continuously updated document retrieval mechanism.

RAG is often appropriate when knowledge:

```text
changes frequently
needs citations
is private
is large
must be updated/deleted
```

They can also be combined.

---

## 35. Agentic RAG

Basic RAG usually has a predefined pipeline:

```text
Question
↓
Retrieve
↓
Generate
```

An agentic system can make decisions about retrieval.

```text
Question
    ↓
Agent
    ↓
Do I need retrieval?
    ↓
Which source?
    ↓
Search
    ↓
Enough evidence?
    ↓
No → Search again
    ↓
Yes
    ↓
Generate answer
```

The important change is **control flow**.

Retrieval becomes a tool the agent can choose to use rather than a fixed single step.

This connects nicely with later agent-engineering material.

---

## 36. Production RAG Architecture

A more realistic architecture might look like:

```text
                    DOCUMENT PIPELINE

PDF / Web / DB / Docs
          ↓
       Parsing
          ↓
       Cleaning
          ↓
       Chunking
          ↓
      Embeddings
          ↓
 Search / Vector Index


                    QUERY PIPELINE

User
 ↓
Query Processing
 ↓
Hybrid Retrieval
 ↓
Candidate Documents
 ↓
Reranking
 ↓
Context Construction
 ↓
LLM
 ↓
Grounded Answer + Citations
 ↓
Evaluation / Logging
```

---

## 37. Latency and Cost

Every stage has a cost.

```text
Query transformation       + latency
Embedding                   + latency
Retrieval                   + latency
Reranking                   + latency
LLM generation              + latency
```

Similarly:

```text
More retrieved context
        ↓
More input tokens
        ↓
Higher cost
+
Potentially higher latency
```

Production RAG therefore involves optimization across:

```text
Quality
Cost
Latency
```

You usually cannot optimize one without considering the others.

---

## 38. Access Control

Enterprise RAG introduces another critical issue.

Suppose Alice can read:

```text
Engineering documents
```

but cannot read:

```text
Executive compensation documents
```

Retrieval must respect those permissions.

Otherwise RAG becomes a data-leak mechanism.

Conceptually:

```text
User
 ↓
Identity + Permissions
 ↓
Authorized Retrieval
 ↓
Documents user may access
 ↓
LLM
```

Security needs to happen at or before retrieval, not merely by telling the LLM:

> "Please don't reveal confidential information."

---

## 39. Updating the Knowledge Base

Documents change.

A production pipeline therefore needs to handle:

```text
Document created
Document changed
Document deleted
```

which may trigger:

```text
Parse
↓
Re-chunk
↓
Re-embed
↓
Update index
```

Otherwise the RAG system can continue answering from stale information.

---

## 40. A Simple RAG Algorithm

At indexing time:

```python
documents = load_documents()
chunks = chunk(documents)

for chunk in chunks:
    vector = embed(chunk.text)
    index.store(
        vector=vector,
        text=chunk.text,
        metadata=chunk.metadata
    )
```

At query time:

```python
question = user_input()
query_vector = embed(question)

results = index.search(
    query_vector,
    top_k=5
)

context = build_context(results)

answer = llm(
    question=question,
    context=context
)

return answer
```

That's the conceptual foundation of a RAG system.

Everything else improves individual pieces.

---

## 41. The Most Important RAG Debugging Question

When the system produces a bad answer, don't immediately change the model.

Ask:

```text
Was the required evidence retrieved?
```

### If NO

Debug:

```text
documents
chunking
metadata
embeddings
query
retrieval
Top-K
hybrid search
ranking
```

### If YES

Debug:

```text
context construction
prompt
conflicting evidence
LLM
reasoning
generation
```

This simple decision tree can save enormous debugging time.

### Token-level F1

**Token-level F1** is a metric that measures how much the **tokens (usually words)** in a model's answer overlap with the tokens in the **reference answer**.

It's commonly used in **question answering** and can also be useful in **RAG evaluation** when you care about answer overlap.

#### Simple example

Reference answer:

> `Paris is the capital of France`

Model answer:

> `Paris is the capital`

Treat each word as a token:

- Reference: 6 tokens
- Prediction: 4 tokens
- Matching: 4 tokens

Then:

**Precision** = matching tokens / predicted tokens = 4 / 4 = **1.0**

**Recall** = matching tokens / reference tokens = 4 / 6 = **0.67**

Token-level F1 combines them:

$$
F1 = \frac{2PR}{P+R}
$$

So:

$$
F1 = \frac{2(1.0)(0.67)}{1.0+0.67} \approx 0.80
$$

So the **token-level F1 = 0.80**.

#### Why use it instead of exact match?

Suppose the correct answer is:

> `The capital of France is Paris.`

And the model says:

> `Paris is the capital of France.`

**Exact Match = 0**, because the strings aren't identical.

But **Token F1 would be very high**, because nearly all the important words overlap.
