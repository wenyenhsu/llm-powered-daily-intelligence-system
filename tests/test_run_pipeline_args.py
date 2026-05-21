# Unit tests for the parse_args function in the run_pipeline module

import pytest
from src.run_pipeline import parse_args
from src.config import TODAY

def test_default_args():
    # Test that default arguments are set correctly when no arguments are provided
    args = parse_args([])
    assert args.target_date == TODAY
    assert args.reports_granularity == "all"
    assert args.merge_threshold == 0.88
    assert args.threshold == 0.84
    assert args.fetch is False
    assert args.init is False
    assert args.agg is False
    assert args.clean is False
    assert args.reindex is False
    assert args.merge is False
    assert args.merge_apply is False
    assert args.ranking is False
    assert args.cluster_topics is False
    assert args.execution_analysis_backend is None
    assert args.reports_backend is None

@pytest.mark.parametrize(
    "argv, attr",
    [
        (["--fetch"], "fetch"),
        (["--init"], "init"),
        (["--agg"], "agg"),
        (["--clean"], "clean"),
        (["--reindex"], "reindex"),
        (["--merge"], "merge"),
        (["--merge-apply"], "merge_apply"),
        (["--ranking"], "ranking"),
        (["--cluster-topics"], "cluster_topics"),
    ],
)
def test_flag_args(argv, attr):
    # Test that flags are set to True when provided

    args = parse_args(argv)
    assert getattr(args, attr) is True
@pytest.mark.parametrize(
    "argv, attr, expected",
    [
        (["--merge-threshold", "0.91"], "merge_threshold", 0.91),
        (["--threshold", "0.77"], "threshold", 0.77),
        (["--date", "2026-05-20"], "target_date", "2026-05-20"),
        (["--execution-analysis-backend-date", "2026-05-21"], "target_date", "2026-05-21"),
        (["--reports-granularity", "day"], "reports_granularity", "day"),
        (["--reports-granularity", "week"], "reports_granularity", "week"),
        (["--reports-granularity", "month"], "reports_granularity", "month"),
        (["--reports-granularity", "all"], "reports_granularity", "all"),
        (["--execution-analysis-backend", "ollama"], "execution_analysis_backend", "ollama"),
        (["--reports-backend", "ollama"], "reports_backend", "ollama"),
    ],
)
def test_value_args(argv, attr, expected):
    # Test that values are set correctly when provided
    args = parse_args(argv)
    assert getattr(args, attr) == expected

def test_combined_args():
    # Test that multiple arguments can be combined and parsed correctly
    args = parse_args([
        "--fetch",
        "--merge",
        "--merge-threshold", "0.91",
        "--reports-backend", "ollama",
        "--reports-granularity", "week",
        "--date", "2026-05-20",
    ])

    assert args.fetch is True
    assert args.merge is True
    assert args.merge_threshold == 0.91
    assert args.reports_backend == "ollama"
    assert args.reports_granularity == "week"
    assert args.target_date == "2026-05-20"

def test_invalid_execution_backend_raises():
    # Test that an error is raised when an invalid execution analysis backend is provided
    with pytest.raises(SystemExit):
        parse_args(["--execution-analysis-backend", "bad"])

def test_invalid_reports_granularity_raises():
    # Test that an error is raised when an invalid reports granularity is provided
    with pytest.raises(SystemExit):
        parse_args(["--reports-granularity", "year"])