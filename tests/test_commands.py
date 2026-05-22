import pytest

from src.run_pipeline import parse_args


# -------------------
# full pipeline
# -------------------

def test_full_pipeline_quick_start():

    args = parse_args([
        "--fetch",
        "--init",
        "--execution-analysis-backend", "ollama",
        "--agg",
        "--clean",
        "--merge",
        "--reindex",
        "--ranking",
        "--cluster-topics",
        "--reports-backend", "ollama",
    ])

    assert args.fetch is True
    assert args.init is True
    assert args.agg is True
    assert args.clean is True
    assert args.merge is True
    assert args.reindex is True
    assert args.ranking is True
    assert args.cluster_topics is True

    assert args.execution_analysis_backend == "ollama"
    assert args.reports_backend == "ollama"


# -------------------
# reports granularities
# -------------------

@pytest.mark.parametrize(
    "granularity",
    [
        "day",
        "week",
        "month",
        "all",
    ],
)
def test_report_granularity(granularity):

    args = parse_args([
        "--reports-backend", "ollama",
        "--reports-granularity", granularity,
    ])

    assert args.reports_backend == "ollama"
    assert args.reports_granularity == granularity


# -------------------
# fetch only
# -------------------

def test_fetch_only():

    args = parse_args([
        "--fetch",
    ])

    assert args.fetch is True


# -------------------
# execution analysis
# -------------------

def test_execution_analysis():

    args = parse_args([
        "--execution-analysis-backend",
        "ollama",
    ])

    assert args.execution_analysis_backend == "ollama"


# -------------------
# reindex
# -------------------

def test_reindex():

    args = parse_args([
        "--reindex",
    ])

    assert args.reindex is True


# -------------------
# merge apply
# -------------------

def test_merge_apply():

    args = parse_args([
        "--merge",
        "--merge-apply",
    ])

    assert args.merge is True
    assert args.merge_apply is True


# -------------------
# reports backend
# -------------------

def test_reports_backend():

    args = parse_args([
        "--reports-backend",
        "ollama",
    ])

    assert args.reports_backend == "ollama"


# -------------------
# custom report range
# -------------------

def test_custom_report_range():

    args = parse_args([
        "--reports-backend", "ollama",
        "--reports-granularity", "custom",
        "--reports-start-date", "2026-05-01",
        "--reports-end-date", "2026-05-21",
    ])

    assert args.reports_backend == "ollama"
    assert args.reports_granularity == "custom"

    assert args.reports_start_date == "2026-05-01"
    assert args.reports_end_date == "2026-05-21"

