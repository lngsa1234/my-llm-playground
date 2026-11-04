import datetime as dt
import json

from labs.shared import knowledge


def test_heading_anchor_matches_streamlit_ids():
    assert knowledge.heading_anchor("1. How an LLM generates text") == "1-how-an-llm-generates-text"
    assert knowledge.heading_anchor("3. Observability: you can't fix it") == "3-observability-you-cant-fix-it"
    assert knowledge.heading_anchor("Week 2 · Context — **Concepts**?") == "week-2-context-concepts"


def test_headings_skip_code_blocks():
    content = "# Title\n## One\n```bash\n## not a heading\n```\n### Two\n"
    assert knowledge.headings(content) == [(2, "One", "one"), (3, "Two", "two")]


def test_last_updated_falls_back_to_dates_file(tmp_path, monkeypatch):
    page = tmp_path / "week-09-demo" / "concepts.md"
    page.parent.mkdir()
    page.write_text("# Demo\n")
    dates = tmp_path / "last-updated.json"
    dates.write_text(json.dumps({"week-09-demo/concepts.md": "2026-11-04"}))
    monkeypatch.setattr(knowledge, "KNOWLEDGE_BASE", tmp_path)
    monkeypatch.setattr(knowledge, "DATES_FILE", dates)
    monkeypatch.setattr(knowledge, "_git_date", lambda path: None)
    assert knowledge.last_updated(page) == dt.date(2026, 11, 4)
    monkeypatch.setattr(knowledge, "DATES_FILE", tmp_path / "missing.json")
    assert knowledge.last_updated(page) is None


def test_every_page_has_a_date():
    for path in knowledge.available_concepts().values():
        assert knowledge.last_updated(path) is not None, path
