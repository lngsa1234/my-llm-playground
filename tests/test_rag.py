from pathlib import Path

import pytest

from core.rag import (
    ABSTENTION,
    Chunk,
    Document,
    RagIndex,
    _bm25_scores,
    _linked_source_positions,
    build_context,
    chunk_documents,
    chunk_text,
    generate_with_rag,
    load_documents,
    retrieve,
)
from core.week3 import _answer_scores, _expected_found


ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_base_loads_all_novatech_documents():
    documents = load_documents(ROOT / "knowledge_base")

    assert len(documents) == 10
    assert {document.source for document in documents} >= {
        "refund_policy.md",
        "remote_work_policy.md",
        "api_limits.md",
    }
    assert all(document.text.startswith("# NovaTech") for document in documents)


def test_chunking_retains_source_and_creates_readable_overlap():
    document = Document(
        source="policy.md",
        text="one two three four five six seven eight nine ten eleven twelve",
    )

    chunks = chunk_documents([document], chunk_size=24, overlap=8)

    assert len(chunks) > 1
    assert all(chunk.source == "policy.md" for chunk in chunks)
    assert [chunk.chunk_number for chunk in chunks] == list(range(1, len(chunks) + 1))
    assert "four" in chunks[0].text
    assert "four" in chunks[1].text


@pytest.mark.parametrize("chunk_size, overlap", [(0, 0), (20, -1), (20, 20)])
def test_chunk_text_rejects_invalid_settings(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=chunk_size, overlap=overlap)


def test_build_context_keeps_source_and_chunk_metadata():
    context = build_context(
        [{"source": "refund_policy.md", "chunk_number": 2, "text": "Refunds are available."}]
    )

    assert context == "[refund_policy.md · chunk 2]\nRefunds are available."


def test_bm25_prioritizes_a_chunk_with_matching_terms():
    chunks = [
        Chunk(source="refund.md", text="Pro customers can request a refund.", chunk_number=1),
        Chunk(source="security.md", text="Encryption protects data.", chunk_number=1),
    ]

    scores = _bm25_scores("How can a Pro customer request a refund?", chunks)

    assert scores[0] > scores[1]


def test_title_linked_retrieval_adds_the_named_document_as_second_hop():
    index = RagIndex(
        index=None,
        chunks=[
            Chunk("kiss.md", "# Kiss and Tell Shirley Temple portrayed Corliss Archer.", 1),
            Chunk("shirley.md", "# Shirley Temple She served as Chief of Protocol.", 1),
        ],
        source_titles={"kiss.md": "Kiss and Tell", "shirley.md": "Shirley Temple"},
        embedding_model="test",
        build_latency_seconds=0.0,
        embedding_tokens=0,
    )

    linked = _linked_source_positions(index, [0, 1])

    assert linked == [1]


def test_title_linked_retrieval_keeps_neighboring_chunks_from_the_linked_document():
    index = RagIndex(
        index=None,
        chunks=[
            Chunk("kiss.md", "# Kiss and Tell Shirley Temple portrayed Corliss Archer.", 1),
            Chunk("shirley.md", "# Shirley Temple She was a diplomat.", 1),
            Chunk("shirley.md", "She also served as Chief of Protocol of the United States.", 2),
        ],
        source_titles={"kiss.md": "Kiss and Tell", "shirley.md": "Shirley Temple"},
        embedding_model="test",
        build_latency_seconds=0.0,
        embedding_tokens=0,
    )

    linked = _linked_source_positions(index, [0])

    assert linked == [1, 2]


def test_hybrid_retrieval_keeps_a_title_linked_second_hop(monkeypatch):
    class FakeFaissIndex:
        def search(self, vector, limit):
            return [[0.9, 0.7, 0.1][:limit]], [[0, 2, 1][:limit]]

    index = RagIndex(
        index=FakeFaissIndex(),
        chunks=[
            Chunk("kiss.md", "Kiss and Tell starred Shirley Temple as Corliss Archer.", 1),
            Chunk("shirley.md", "Shirley Temple served as Chief of Protocol.", 1),
            Chunk("other.md", "A woman held a government position.", 1),
        ],
        source_titles={"kiss.md": "Kiss and Tell", "shirley.md": "Shirley Temple", "other.md": "Other"},
        embedding_model="test",
        build_latency_seconds=0.0,
        embedding_tokens=0,
    )
    monkeypatch.setattr("core.rag.OpenAI", lambda: object())
    monkeypatch.setattr("core.rag.embed_texts", lambda client, texts, model: ([[0.0]], 1))

    results, _, _ = retrieve(index, "What position did the woman in Kiss and Tell hold?", top_k=2)

    assert [result["source"] for result in results] == ["kiss.md", "shirley.md"]
    assert results[1]["retrieval_method"] == "title-linked second hop"
    assert results[0]["fused_rank"] == 1


def test_low_similarity_abstains_without_calling_the_llm(monkeypatch):
    def unexpected_client():
        raise AssertionError("The LLM should not be called when evidence is insufficient")

    monkeypatch.setattr("core.rag.OpenAI", unexpected_client)
    result = generate_with_rag(
        "test-model",
        "Does NovaTech reimburse gym memberships?",
        [{"source": "employee_benefits.md", "chunk_number": 1, "text": "Benefits.", "score": 0.12}],
        threshold=0.35,
    )

    assert result["text"] == ABSTENTION
    assert result["abstained"] is True
    assert result["status"] == "abstained_before_generation"
    assert result["gate"].startswith("blocked:")


def test_multi_hop_evidence_requires_every_supporting_document():
    item = {"evidence": ["first.md", "second.md"]}

    assert _expected_found(item, [{"source": "first.md"}, {"source": "second.md"}]) is True
    assert _expected_found(item, [{"source": "first.md"}]) is False


def test_answer_score_ignores_the_sources_line():
    exact, f1 = _answer_scores("Chief of Protocol\nSources: kiss-and-tell.md", "Chief of Protocol")

    assert exact == 1.0
    assert f1 == 1.0
