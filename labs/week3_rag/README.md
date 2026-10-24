# Week 3 Lab · Build and Evaluate a RAG System

Documents → chunks → embeddings → FAISS search → grounded answer with sources → evidence evaluation.

Lab guide: [knowledge_base/week-03-rag/lab.md](../../knowledge_base/week-03-rag/lab.md)

## What's here

```text
week3_rag/
├── page.py          the web page: playground, documents & chunks, benchmark
├── rag.py           loading, chunking, embeddings, hybrid retrieval, grounded generation
├── evaluation.py    datasets and benchmark scoring (Evidence Recall@K, exact match, token F1)
├── documents/
│   ├── novatech/        ten fictional company-policy documents
│   └── hotpotqa_mini/   198 Wikipedia articles from HotpotQA (see ATTRIBUTION.txt)
├── questions/
│   ├── questions.json                 NovaTech questions with expected answers and evidence
│   └── hotpotqa_mini_questions.json   50 HotpotQA questions + unanswerable checks
├── tools/build_hotpotqa_mini.py       rebuilds the HotpotQA documents and questions
└── tests/
```

The app indexes every `.md` file directly inside a `documents/` subfolder, so keep notes and other Markdown out of those folders.

## Run it

From the repo root, after `pip install -r requirements.txt` and setting `OPENAI_API_KEY` in `.env`:

```bash
streamlit run labs/week3_rag/page.py   # this lab on its own
streamlit run app.py                   # all labs, pick Week 3
```
