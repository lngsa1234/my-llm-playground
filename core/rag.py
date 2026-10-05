"""Small, inspectable RAG pipeline used by the Week 3 lab.

The module deliberately keeps the moving parts visible: markdown documents become
overlapping chunks, chunks become embeddings, and normalized embeddings are stored
in a FAISS inner-product index (cosine similarity after normalization).
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import math
from pathlib import Path
import re
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
    source_titles: dict[str, str]
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
    documents = load_documents(knowledge_base)
    chunks = chunk_documents(documents, chunk_size, overlap)
    if not chunks:
        raise ValueError("No markdown chunks were found in the knowledge base.")
    matrix, tokens = embed_texts(OpenAI(), [chunk.text for chunk in chunks], embedding_model)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    source_titles = {document.source: _document_title(document) for document in documents}
    return RagIndex(index, chunks, source_titles, embedding_model, time.perf_counter() - started, tokens)


def _document_title(document: Document) -> str:
    """Use the Markdown H1 as a deterministic entity label for a document."""
    for line in document.text.splitlines():
        match = re.fullmatch(r"\s*#\s+(.+?)\s*", line)
        if match:
            return match.group(1)
    return Path(document.source).stem.replace("-", " ")


def _terms(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def _bm25_scores(query: str, chunks: list[Chunk]) -> list[float]:
    """A small dependency-free BM25 implementation for keyword retrieval."""
    query_terms = _terms(query)
    documents = [_terms(chunk.text) for chunk in chunks]
    if not query_terms or not documents:
        return [0.0] * len(chunks)
    document_frequency = Counter(term for document in documents for term in set(document))
    average_length = sum(len(document) for document in documents) / len(documents)
    scores: list[float] = []
    for document in documents:
        counts = Counter(document)
        score = 0.0
        for term in set(query_terms):
            frequency = counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += inverse_frequency * frequency * 2.5 / (frequency + 1.5 * (1 - 0.75 + 0.75 * len(document) / average_length))
        scores.append(score)
    return scores


def _ranked_positions(scores: list[float], limit: int) -> list[int]:
    return sorted(range(len(scores)), key=lambda position: scores[position], reverse=True)[:limit]


def _linked_source_positions(
    rag_index: RagIndex, primary_positions: list[int], excluded_sources: set[str]
) -> list[int]:
    """Follow titles named in retrieved text, without asking an LLM to expand a query."""
    text = " ".join(rag_index.chunks[position].text.casefold() for position in primary_positions)
    first_chunk_by_source: dict[str, int] = {}
    for position, chunk in enumerate(rag_index.chunks):
        first_chunk_by_source.setdefault(chunk.source, position)
    linked: list[int] = []
    for source, title in rag_index.source_titles.items():
        title_terms = _terms(title)
        if source in excluded_sources or len(title_terms) < 2:
            continue
        pattern = r"(?<!\w)" + r"\s+".join(re.escape(term) for term in title_terms) + r"(?!\w)"
        if re.search(pattern, text):
            linked.append(first_chunk_by_source[source])
    return linked


def retrieve(rag_index: RagIndex, question: str, top_k: int) -> tuple[list[dict], float, int]:
    """Hybrid, multi-hop retrieval using dense search, BM25, RRF, and title links."""
    if not question.strip():
        raise ValueError("Enter a question first.")
    started = time.perf_counter()
    vector, tokens = embed_texts(OpenAI(), [question], rag_index.embedding_model)
    candidate_limit = min(max(top_k * 4, 12), len(rag_index.chunks))
    scores, positions = rag_index.index.search(vector, candidate_limit)
    dense_scores = {int(position): float(score) for score, position in zip(scores[0], positions[0]) if position != -1}
    lexical_scores = _bm25_scores(question, rag_index.chunks)
    dense_positions = list(dense_scores)
    lexical_positions = _ranked_positions(lexical_scores, candidate_limit)
    candidates = set(dense_positions) | set(lexical_positions)
    fused_scores = {position: 0.0 for position in candidates}
    for rank, position in enumerate(dense_positions, start=1):
        fused_scores[position] = fused_scores.get(position, 0.0) + 1 / (60 + rank)
    for rank, position in enumerate(lexical_positions, start=1):
        fused_scores[position] = fused_scores.get(position, 0.0) + 1 / (60 + rank)
    primary_positions = sorted(candidates, key=lambda position: fused_scores[position], reverse=True)

    # A title named in a retrieved chunk is an explicit, corpus-grounded bridge
    # to another document. Reserve room for these second-hop evidence chunks.
    linked_positions = _linked_source_positions(
        rag_index,
        primary_positions[:top_k],
        {rag_index.chunks[position].source for position in primary_positions[:top_k]},
    )
    linked_positions = linked_positions[: max(0, top_k - 1)]
    remaining_primary = [position for position in primary_positions[1:] if position not in linked_positions]
    selected_positions = (primary_positions[:1] + linked_positions + remaining_primary)[:top_k]
    results = [
        {
            "source": rag_index.chunks[position].source,
            "chunk_number": rag_index.chunks[position].chunk_number,
            "text": rag_index.chunks[position].text,
            "score": dense_scores.get(position, 0.0),
            "lexical_score": lexical_scores[position],
            "fused_score": fused_scores.get(position, 0.0),
            "retrieval_method": "title-linked second hop" if position in linked_positions else "dense + BM25 + RRF",
        }
        for position in selected_positions
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
        "You are a grounded knowledge assistant. Answer using only the supplied context. "
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
