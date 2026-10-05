"""Small, inspectable RAG pipeline used by the Week 3 lab.

The module deliberately keeps the moving parts visible: markdown documents become
overlapping chunks, chunks become embeddings, and normalized embeddings are stored
in a FAISS inner-product index (cosine similarity after normalization).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Iterable

try:  # Keep the rest of the teaching app importable before lab dependencies are installed.
    import faiss
    import numpy as np
except ImportError:  # pragma: no cover - exercised by the UI dependency message.
    faiss = None
    np = None
from openai import OpenAI


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
ABSTENTION = "I don't have enough information in the provided knowledge base."


@dataclass(frozen=True)
class Document:
    source: str
    text: str


@dataclass(frozen=True)
class Chunk:
    source: str
    text: str
    chunk_number: int


@dataclass
class RagIndex:
    index: Any
    chunks: list[Chunk]
    embedding_model: str
    build_latency_seconds: float
    embedding_tokens: int


def load_documents(directory: str | Path) -> list[Document]:
    """Load every non-empty markdown file and retain its filename as metadata."""
    path = Path(directory)
    return [
        Document(source=file.name, text=file.read_text(encoding="utf-8").strip())
        for file in sorted(path.glob("*.md"))
        if file.read_text(encoding="utf-8").strip()
    ]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Create character chunks, preferring a whitespace boundary at the end."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    clean = " ".join(text.split())
    if not clean:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        if end < len(clean):
            boundary = clean.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        # Begin the next chunk at a word boundary in the overlap window. This
        # makes the chunk inspector readable instead of showing partial words.
        overlap_start = clean.rfind(" ", 0, max(1, end - overlap))
        start = overlap_start + 1 if overlap_start >= 0 else max(0, end - overlap)
    return chunks


def chunk_documents(documents: Iterable[Document], chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(
            Chunk(source=document.source, text=text, chunk_number=number)
            for number, text in enumerate(chunk_text(document.text, chunk_size, overlap), start=1)
        )
    return chunks


def _normalized_matrix(vectors: list[list[float]]) -> np.ndarray:
    if faiss is None or np is None:
        raise RuntimeError("FAISS is not installed. Run `pip install -r requirements.txt` and restart Streamlit.")
    matrix = np.asarray(vectors, dtype="float32")
    faiss.normalize_L2(matrix)
    return matrix


def embed_texts(client: OpenAI, texts: list[str], model: str) -> tuple[np.ndarray, int]:
    """Embed texts in batches, preserving input order."""
    vectors: list[list[float]] = []
    tokens = 0
    for start in range(0, len(texts), 128):
        response = client.embeddings.create(model=model, input=texts[start : start + 128])
        vectors.extend(item.embedding for item in response.data)
        tokens += response.usage.total_tokens if response.usage else 0
    return _normalized_matrix(vectors), tokens


def build_index(
    knowledge_base: str | Path,
    chunk_size: int,
    overlap: int,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> RagIndex:
    """Load, chunk, embed, and add NovaTech knowledge to a FAISS index."""
    if faiss is None or np is None:
        raise RuntimeError("FAISS is not installed. Run `pip install -r requirements.txt` and restart Streamlit.")
    started = time.perf_counter()
    chunks = chunk_documents(load_documents(knowledge_base), chunk_size, overlap)
    if not chunks:
        raise ValueError("No markdown chunks were found in the knowledge base.")
    matrix, tokens = embed_texts(OpenAI(), [chunk.text for chunk in chunks], embedding_model)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    return RagIndex(index, chunks, embedding_model, time.perf_counter() - started, tokens)


def retrieve(rag_index: RagIndex, question: str, top_k: int) -> tuple[list[dict], float, int]:
    """Return highest-cosine-similarity chunks and query embedding timing."""
    if not question.strip():
        raise ValueError("Enter a question first.")
    started = time.perf_counter()
    vector, tokens = embed_texts(OpenAI(), [question], rag_index.embedding_model)
    scores, positions = rag_index.index.search(vector, min(top_k, len(rag_index.chunks)))
    results = [
        {
            "source": rag_index.chunks[position].source,
            "chunk_number": rag_index.chunks[position].chunk_number,
            "text": rag_index.chunks[position].text,
            "score": float(score),
        }
        for score, position in zip(scores[0], positions[0])
        if position != -1
    ]
    return results, time.perf_counter() - started, tokens


def build_context(results: list[dict]) -> str:
    return "\n\n".join(
        f"[{item['source']} · chunk {item['chunk_number']}]\n{item['text']}" for item in results
    )


def approximate_tokens(text: str) -> int:
    """A transparent estimate for the metrics panel; API usage is shown when available."""
    return max(1, len(text) // 4) if text else 0


def generate_without_rag(model: str, question: str) -> dict:
    started = time.perf_counter()
    response = OpenAI().responses.create(model=model, input=question)
    return _generation_result(response, time.perf_counter() - started)


def generate_with_rag(model: str, question: str, results: list[dict], threshold: float) -> dict:
    """Generate only when the best retrieved evidence clears the chosen threshold."""
    top_score = results[0]["score"] if results else -1.0
    if top_score < threshold:
        return {
            "text": ABSTENTION,
            "latency_seconds": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "status": "abstained_before_generation",
            "prompt": "Evidence did not meet the similarity threshold; no LLM call was made.",
            "abstained": True,
        }
    context = build_context(results)
    instructions = (
        "You are NovaTech's company knowledge assistant. Answer using only the supplied context. "
        f"If the context does not contain enough evidence, reply exactly: {ABSTENTION} "
        "Do not use outside knowledge or make up policies. Give a concise answer, then a final "
        "line beginning `Sources:` that lists only the supplied filenames supporting the answer."
    )
    prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
    started = time.perf_counter()
    response = OpenAI().responses.create(model=model, instructions=instructions, input=prompt)
    result = _generation_result(response, time.perf_counter() - started)
    result.update({"prompt": prompt, "abstained": False})
    return result


def _generation_result(response: object, latency: float) -> dict:
    usage = response.usage
    return {
        "text": response.output_text,
        "latency_seconds": latency,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "status": response.status,
    }
