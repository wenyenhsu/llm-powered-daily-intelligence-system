from __future__ import annotations

from unittest.mock import patch

import pytest

from src import embedding_memory as memory
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
        "model": memory.OLLAMA_EMBED_MODEL,
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
    ) as embed_mock:
        results = retrieve_top_insights("AI search news", top_k=2, min_score=0.5)

    assert [item["slug"] for item in results] == ["ai-search", "market-growth"]
    assert results[0]["score"] == pytest.approx(1.0)
    embed_mock.assert_called_once_with("AI search news", model=memory.OLLAMA_EMBED_MODEL)


@pytest.mark.parametrize(
    "top_k,min_score,expected_slugs",
    [
        (1, 0.0, ["best"]),
        (2, 0.0, ["best", "near"]),
        (3, 0.0, ["best", "near", "orthogonal"]),
        (3, 0.5, ["best", "near"]),
        (3, 0.995, ["best"]),
    ],
)
def test_retrieve_top_insights_preserves_top_k_and_threshold(top_k, min_score, expected_slugs):
    fake_index = {
        "model": memory.OLLAMA_EMBED_MODEL,
        "items": [
            {"slug": "near", "embedding": [0.9, 0.1]},
            {"slug": "orthogonal", "embedding": [0.0, 1.0]},
            {"slug": "best", "embedding": [1.0, 0.0]},
        ],
    }
    with patch.object(memory, "load_index", return_value=fake_index), patch.object(
        memory, "embed_text", return_value=[1.0, 0.0]
    ):
        results = retrieve_top_insights("query", top_k=top_k, min_score=min_score)

    assert [item["slug"] for item in results] == expected_slugs


def test_retrieve_top_insights_rejects_same_dimension_model_mismatch(monkeypatch):
    monkeypatch.setattr(memory, "OLLAMA_EMBED_MODEL", "model-B")
    fake_index = {
        "model": "model-A",
        "items": [{"slug": "old-space", "embedding": [1.0, 0.0]}],
    }
    with patch.object(memory, "load_index", return_value=fake_index), patch.object(
        memory, "embed_text", return_value=[1.0, 0.0]
    ) as embed_mock, patch.object(memory, "cosine_similarity", return_value=1.0) as compare_mock:
        with pytest.raises(ValueError, match="model-A.*model-B.*--reindex"):
            retrieve_top_insights("query")

    embed_mock.assert_not_called()
    compare_mock.assert_not_called()


@pytest.mark.parametrize("metadata", [{}, {"model": None}, {"model": ""}, {"model": " \t"}, {"model": 42}])
def test_retrieve_top_insights_rejects_unknown_model_metadata(metadata):
    fake_index = {**metadata, "items": [{"slug": "legacy", "embedding": [1.0, 0.0]}]}
    with patch.object(memory, "load_index", return_value=fake_index), patch.object(
        memory, "embed_text", return_value=[1.0, 0.0]
    ) as embed_mock, patch.object(memory, "build_insight_index") as rebuild_mock:
        with pytest.raises(ValueError, match="model metadata.*--reindex"):
            retrieve_top_insights("query")

    embed_mock.assert_not_called()
    rebuild_mock.assert_not_called()


def test_retrieve_top_insights_sends_validated_model_to_backend(monkeypatch):
    # Changing the module setting does not change embed_text's bound default.
    # Keep embed_text real and inspect its HTTP payload to catch that trap.
    monkeypatch.setattr(memory, "OLLAMA_EMBED_MODEL", "model-B")
    fake_index = {
        "model": "model-B",
        "items": [{"slug": "same-space", "embedding": [1.0, 0.0]}],
    }
    with patch.object(memory, "load_index", return_value=fake_index), patch.object(
        memory.requests, "post"
    ) as post_mock:
        post_mock.return_value.json.return_value = {"embedding": [1.0, 0.0]}
        results = retrieve_top_insights("  query  ")

    post_mock.assert_called_once_with(
        f"{memory.OLLAMA_HOST}/api/embeddings",
        json={"model": "model-B", "prompt": "query"},
        timeout=60,
    )
    assert [item["slug"] for item in results] == ["same-space"]
    assert results[0]["score"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "query,index",
    [
        ("query", {}),
        ("query", {"model": "old-model", "items": []}),
        ("query", {"items": None}),
        ("", {"items": [{"slug": "legacy", "embedding": [1.0, 0.0]}]}),
        (" \n\t ", {"model": "old-model", "items": [{"slug": "old", "embedding": [1.0, 0.0]}]}),
    ],
)
def test_retrieve_top_insights_preserves_empty_input_behavior(query, index):
    with patch.object(memory, "load_index", return_value=index), patch.object(
        memory, "embed_text"
    ) as embed_mock:
        assert retrieve_top_insights(query) == []

    embed_mock.assert_not_called()


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
