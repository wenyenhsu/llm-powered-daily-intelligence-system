from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import src.aggregate_insights as ai
import src.clean_up as cu
import src.embedding_memory as em
import src.generate_reports as gr
import src.ranking as rk
import src.topic_clustering as tc
import src.topic_memory as tm


class TestAggregateInsights(unittest.TestCase):
    def test_clean_name_normalizes_text(self):
        self.assertEqual(ai.clean_name("  Hello, WORLD!!  "), "hello-world")


class TestCleanUp(unittest.TestCase):
    def test_normalize_target_strips_folder_and_alias(self):
        self.assertEqual(cu.normalize_target("insights/AI Agent|Alias"), "ai agent")

    def test_is_bad_target_matches_bad_nodes(self):
        self.assertTrue(cu.is_bad_target("insights/summarized"))

    def test_clean_text_removes_bad_links_and_empty_bullets(self):
        text = "Line 1\n[[insights/summarized]]\n- \n\n\nLine 2"
        cleaned = cu.clean_text(text)
        self.assertNotIn("[[insights/summarized]]", cleaned)
        self.assertNotIn("- \n", cleaned)
        self.assertEqual(cleaned, "Line 1\n\nLine 2")


class TestRanking(unittest.TestCase):
    def test_extract_links_returns_slugs(self):
        text = "[[insights/ai-search]] and [[insights/market-growth|alias]]"
        self.assertEqual(rk.extract_links(text), ["ai-search", "market-growth"])


class TestTopicClustering(unittest.TestCase):
    def test_cosine_similarity_handles_basic_vectors(self):
        self.assertAlmostEqual(tc.cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertEqual(tc.cosine_similarity([1, 0], [1, 0, 0]), 0.0)

    def test_build_clusters_groups_similar_items(self):
        items = [
            {"slug": "a", "embedding": [1.0, 0.0]},
            {"slug": "b", "embedding": [0.9, 0.1]},
            {"slug": "c", "embedding": [0.0, 1.0]},
        ]
        clusters = tc.build_clusters(items, threshold=0.95)
        self.assertEqual(sorted(sorted(group) for group in clusters), [[0, 1], [2]])

    def test_choose_canonical_prefers_shorter_slug_then_lexical(self):
        items = [
            {"slug": "very-long-name"},
            {"slug": "mid"},
            {"slug": "abc"},
        ]
        self.assertEqual(tc.choose_canonical([0, 1, 2], items), 2)


class TestGenerateReports(unittest.TestCase):
    def test_parse_frontmatter_and_body(self):
        text = """---
title: Hello World
tags: [ai, search]
topic: product
---
Body text here.
"""
        meta, body = gr.parse_frontmatter(text)
        self.assertEqual(meta["title"], "Hello World")
        self.assertEqual(meta["tags"], ["ai", "search"])
        self.assertEqual(meta["topic"], "product")
        self.assertEqual(body, "Body text here.\n")

    def test_parse_date_helpers(self):
        self.assertEqual(gr.parse_date("2026-05-21"), dt.date(2026, 5, 21))
        self.assertEqual(gr.parse_date_from_any("published on 2026-05-18"), dt.date(2026, 5, 18))
        self.assertEqual(gr.parse_date_from_any(dt.datetime(2026, 5, 19, 12, 0)), dt.date(2026, 5, 19))

    def test_report_window_and_output_path(self):
        target = dt.date(2026, 5, 21)
        window = gr.get_report_window("week", target)
        self.assertEqual(window.start, dt.date(2026, 5, 18))
        self.assertEqual(window.end, dt.date(2026, 5, 24))
        self.assertEqual(gr.output_path(Path("reports"), window), Path("reports/weekly/2026-W21.md"))

    def test_filter_items_sorts_and_trims(self):
        window = gr.ReportWindow("day", dt.date(2026, 5, 21), dt.date(2026, 5, 21), dt.date(2026, 5, 21))
        items = [
            gr.InsightItem("B", "short", Path("b.md"), dt.date(2026, 5, 21), topic="beta", tags=None, raw=None),
            gr.InsightItem("A", "x" * 20, Path("a.md"), dt.date(2026, 5, 21), topic="alpha", tags=None, raw=None),
            gr.InsightItem("Out", "ignore", Path("o.md"), dt.date(2026, 5, 20), topic=None, tags=None, raw=None),
        ]
        filtered = gr.filter_items(items, window, max_items=10, max_chars_per_item=5)
        self.assertEqual([item.title for item in filtered], ["A", "B"])
        self.assertEqual(filtered[0].body, "xxxxx...")

    def test_clean_report_strips_thinking_and_tags(self):
        raw = "\x1b[31m<think>hidden</think>\n[12D][K]  Hello   world\n\n\n"
        cleaned = gr.clean_report(raw)
        self.assertEqual(cleaned, "Hello world\n")

    def test_has_required_structure_needs_three_sections(self):
        text = "## Executive Summary\n\n## Major Themes\n\n## Key Signals\n"
        self.assertTrue(gr.has_required_structure(text))
        self.assertFalse(gr.has_required_structure("## Executive Summary\n"))


class TestEmbeddingAndTopicMemory(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(em.slugify("AI Search & Market Growth"), "ai-search-market-growth")

    def test_match_insight_with_mocked_index(self):
        fake_index = {
            "items": [
                {"slug": "ai-search", "embedding": [1.0, 0.0], "path": "insights/ai-search.md"},
                {"slug": "other", "embedding": [0.0, 1.0], "path": "insights/other.md"},
            ]
        }
        with patch.object(em, "load_index", return_value=fake_index), patch.object(em, "embed_text", return_value=[1.0, 0.0]):
            result = em.match_insight("candidate", threshold=0.8)
        self.assertEqual(result["matched"], True)
        self.assertEqual(result["slug"], "ai-search")

    def test_resolve_or_create_topic_creates_file_when_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch.object(tm, "TOPICS_DIR", tmp_path), patch.object(tm, "match_topic", return_value={"matched": False, "slug": None, "score": 0.0, "path": None}):
                slug, created = tm.resolve_or_create_topic("AI Search")
            self.assertEqual(slug, "ai-search")
            self.assertTrue(created)
            self.assertTrue((tmp_path / "ai-search.md").exists())


if __name__ == "__main__":
    unittest.main()
