from pathlib import Path

import pytest

from core.rag import (
    ABSTENTION,
    Chunk,
    Document,
    build_context,
    chunk_documents,
    chunk_text,
    generate_with_rag,
    load_documents,
)


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
