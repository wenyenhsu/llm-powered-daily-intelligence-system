from __future__ import annotations

from unittest.mock import patch

import pytest

from src.embedding_memory import (
    format_retrieved_insights_section,
    insight_snippet,
    retrieve_top_insights,
)
from src.run_pipeline import build_prompt_for_inbox


def test_insight_snippet_skips_headings_and_wiki_links():
    text = "# ai-search\n\n## 2026-06-21\n- Derived from [[daily/2026-06-21]]\n- Related topic: [[topics/ai]]\n"
    assert insight_snippet(text) == "Derived from"


def test_retrieve_top_insights_returns_ranked_matches():
    fake_index = {
        "items": [
            {
                "slug": "ai-search",
                "embedding": [1.0, 0.0],
                "path": "insights/ai-search.md",
                "text": "# ai-search\n\nSearch competition is intensifying.",
            },
            {
                "slug": "market-growth",
                "embedding": [0.9, 0.1],
                "path": "insights/market-growth.md",
                "text": "# market-growth\n\nMarkets are expanding.",
            },
            {
                "slug": "other",
                "embedding": [0.0, 1.0],
                "path": "insights/other.md",
                "text": "# other\n\nUnrelated topic.",
            },
        ]
    }

    with patch("src.embedding_memory.load_index", return_value=fake_index), patch(
        "src.embedding_memory.embed_text",
        return_value=[1.0, 0.0],
    ):
        results = retrieve_top_insights("AI search news", top_k=2, min_score=0.5)

    assert [item["slug"] for item in results] == ["ai-search", "market-growth"]
    assert results[0]["score"] == pytest.approx(1.0)


def test_format_retrieved_insights_section_renders_prompt_block():
    section = format_retrieved_insights_section(
        [
            {
                "slug": "ai-search",
                "score": 0.91,
                "text": "# ai-search\n\nSearch competition is intensifying.",
            }
        ]
    )

    assert "## Existing Insights" in section
    assert "[[insights/ai-search]] (relevance: 0.91)" in section
    assert "Search competition is intensifying." in section


def test_build_prompt_for_inbox_injects_retrieved_insights(tmp_path, monkeypatch):
    inbox_dir = tmp_path / "inbox"
    prompts_dir = tmp_path / "prompts"
    inbox_dir.mkdir()
    prompts_dir.mkdir()

    (inbox_dir / "2026-06-22.md").write_text(
        "- [AI search update](https://example.com) — Source\n",
        encoding="utf-8",
    )
    (prompts_dir / "summarized.md").write_text("# Rules\n", encoding="utf-8")
    (prompts_dir / "EXTRACTION_CONTRACT.md").write_text("<!-- END EXTRACTION -->", encoding="utf-8")

    monkeypatch.setattr("src.run_pipeline.INBOX_DIR", inbox_dir)
    monkeypatch.setattr("src.run_pipeline.PROMPTS_DIR", prompts_dir)

    with patch(
        "src.run_pipeline.retrieve_top_insights",
        return_value=[
            {
                "slug": "ai-search",
                "score": 0.88,
                "text": "# ai-search\n\nSearch competition is intensifying.",
            }
        ],
    ):
        prompt = build_prompt_for_inbox("2026-06-22")

    assert "## Existing Insights" in prompt
    assert "[[insights/ai-search]]" in prompt
    assert "--- DATA ---" in prompt
    assert "AI search update" in prompt
    assert prompt.index("## Existing Insights") < prompt.index("--- DATA ---")


def test_build_prompt_for_inbox_can_disable_retrieval(tmp_path, monkeypatch):
    inbox_dir = tmp_path / "inbox"
    prompts_dir = tmp_path / "prompts"
    inbox_dir.mkdir()
    prompts_dir.mkdir()

    (inbox_dir / "2026-06-22.md").write_text("- [News](https://example.com) — Source\n", encoding="utf-8")
    (prompts_dir / "summarized.md").write_text("# Rules\n", encoding="utf-8")
    (prompts_dir / "EXTRACTION_CONTRACT.md").write_text("<!-- END EXTRACTION -->", encoding="utf-8")

    monkeypatch.setattr("src.run_pipeline.INBOX_DIR", inbox_dir)
    monkeypatch.setattr("src.run_pipeline.PROMPTS_DIR", prompts_dir)

    with patch("src.run_pipeline.retrieve_top_insights") as retrieve_mock:
        prompt = build_prompt_for_inbox("2026-06-22", enable_insight_retrieval=False)

    retrieve_mock.assert_not_called()
    assert "## Existing Insights" not in prompt
