# Week 3 Lab · Retrieval-augmented generation

Documents → chunks → embeddings → search → grounded answer with sources → evidence evaluation.

Lab guide: [knowledge_base/week-03-rag/lab.md](../../knowledge_base/week-03-rag/lab.md)

## What's here

```text
week3_rag/
├── page.py          the web page: Ask a question, See the chunks, Compare settings
├── rag.py           loading, chunk strategies, embeddings, search methods, grounded generation
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

## Lab parameters

| Setting | Options | What changes |
| --- | --- | --- |
| Chunk strategy | Fixed size (size + overlap) · By paragraph · By heading | Where documents are cut, and so whether a fact stays in one piece |
| Search method | Hybrid · Meaning · Keywords | Meaning finds paraphrases, keywords find exact names and numbers, hybrid merges both |
| Embedding model | text-embedding-3-small · text-embedding-3-large (or type another) | The vectors used by meaning search; not used by keyword search |
| Top-K | 1–8 | How many chunks go into the context |

Change one setting, run **Compare settings**, and compare in its "Your runs so far" table.

## Run it

From the repo root, after `pip install -r requirements.txt` and setting `OPENAI_API_KEY` in `.env`:

```bash
streamlit run labs/week3_rag/page.py   # this lab on its own
streamlit run app.py                   # all labs, pick Week 3
```
