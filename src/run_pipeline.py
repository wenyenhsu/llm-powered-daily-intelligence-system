from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

from src.clean_up import *
from src.embedding_memory import *
from src.generate_reports import generate_reports
from src.ranking import build_ranking, write_report as write_ranking_report
from src.topic_clustering import (
    build_clusters,
    read_topic_files,
    write_report as write_topic_clusters_report,
)
from src.topic_memory import build_index as build_topic_index, resolve_or_create_topic
from src.config import *


# === load .env ===
def load_env() -> None:
    env_path = ENV_FILE
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v


# === text cleanup ===
def clean_input(text: str) -> str:
    text = ANSI_ESCAPE_RE.sub("", text)
    text = INVISIBLE_RE.sub("", text)
    return text


# === run shell commands ===
def run_cmd(cmd):
    print(f"> {cmd}")
    subprocess.run(cmd, check=True)


def _read_first_existing(*paths: Path) -> str:
    for path in paths:
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"None of the prompt files exist: {', '.join(str(p) for p in paths)}"
    )

def limit_inbox_items(text: str, max_items: int = 12) -> str:
    """
    Keep headings and only the first N bullet news items.
    This reduces prompt size while preserving structure.
    """
    lines = text.splitlines()
    kept_lines: list[str] = []
    item_count = 0

    for line in lines:
        stripped = line.strip()

        # keep headers
        if stripped.startswith("#") or stripped.startswith("##"):
            kept_lines.append(line)
            continue

        # keep only news bullets
        if re.match(r"^\s*-\s+\[", line):
            if item_count < max_items:
                kept_lines.append(line)
                item_count += 1
            continue

        # keep blank lines between sections
        if stripped == "":
            kept_lines.append(line)

    return "\n".join(kept_lines).strip()

def build_prompt_for_inbox(date_str: str, max_items=10) -> str:
    prompt = clean_input((PROMPTS_DIR / "summarized.md").read_text(encoding="utf-8"))
    extraction_contract = clean_input(
        _read_first_existing(
            PROMPTS_DIR / "EXTRACTION_CONTRACT.md",
            PROMPTS_DIR / "extraction_contract.md",
        )
    )
    data = clean_input((INBOX_DIR / f"{date_str}.md").read_text(encoding="utf-8"))

    data = limit_inbox_items(data, max_items=max_items)

    # Put the contract at the end so the model sees the rule right before generation.
    return (
        f"{prompt}\n\n"
        f"--- DATA ---\n"
        f"{data}\n\n"
        f"{extraction_contract}"
    )


def fetch_news(target_date: str) -> None:
    print("Fetching news...")
    run_cmd([
        sys.executable,
        "-m",
        "src.fetch_news",
        "--date",
        target_date,
    ])


def create_daily(date_str: str) -> Path:
    print("Creating daily note...")
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    daily_file = DAILY_DIR / f"{date_str}.md"
    if not daily_file.exists():
        daily_file.write_text(
            f"# {date_str} Daily\n",
            encoding="utf-8",
        )
    return daily_file


def aggregate_insights(target_date: str) -> None:
    run_cmd([
        sys.executable,
        "-m",
        "src.aggregate_insights",
        "--date",
        target_date,
    ])


def load_existing_insights():
    insights_dir = BASE_DIR / "insights"
    insights = []

    if not insights_dir.exists():
        return insights

    for file in insights_dir.glob("*.md"):
        insights.append(file.stem)

    return insights


# === run LLM ===
def run_llm(backend: str, prompt: str) -> str:
    model = os.environ.get("OLLAMA_MODEL", "gemma3:12b")
    url = "http://localhost:11434/api/generate"

    print("=" * 80)
    print("MODEL =", model)
    print("PROMPT LEN =", len(prompt))
    print("=" * 80)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    for attempt in range(2):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

        except Exception as e:
            print(f"Ollama API error: {e}", file=sys.stderr)
            if attempt == 0:
                print("Retrying Ollama request...", file=sys.stderr)
                time.sleep(2)
                continue
            raise


def normalize_insight_links(text: str, threshold: float = 0.82) -> str:
    """
    Process LLM-generated [[insights/...]] for embedding comparison:
    - If similar, reuse the old insight
    - If not similar, retain or create a new slug
    """

    def shorten_candidate(text: str) -> str:
        words = text.split()[:4]
        return " ".join(words)

    def normalize_name(name: str) -> str:
        name = name.lower().strip()

        stopwords = {"insight", "insights", "analysis", "news", "trend"}
        words = re.split(r"[-\s]+", name)
        words = [w for w in words if w not in stopwords]
        name = "-".join(words)

        name = re.sub(r".*insights?-", "", name)
        name = re.sub(r".*topics?-", "", name)
        name = name.replace("_", "-")
        name = re.sub(r"-?\d{1,3}d?-?k?-?insights?-?", "-", name)
        name = re.sub(r"-?\d{4}-?", "-", name)
        name = re.sub(r"(ai-search-)+", "ai-search-", name)
        name = re.sub(r"(smartwatch-)+", "smartwatch-", name)
        name = re.sub(r"[^a-z0-9]+", "-", name)
        name = re.sub(r"-{2,}", "-", name).strip("-")
        return name

    def repl(match: re.Match[str]) -> str:
        raw_slug = match.group(1).strip()
        candidate = normalize_name(raw_slug)
        candidate = candidate.replace("-", " ")
        candidate = shorten_candidate(candidate)

        result = match_insight(candidate, threshold=threshold)
        if result.get("matched"):
            slug = result["slug"]
        else:
            slug = slugify(candidate)

        return f"[[insights/{slug}]]"

    return INSIGHT_LINK_RE.sub(repl, text)


def normalize_topic_name(name: str) -> str:
    name = name.lower().strip()
    name = name.replace("_", "-")

    stopwords = {"topic", "topics", "insight", "insights", "news", "trend"}
    words = re.split(r"[-\s]+", name)
    words = [w for w in words if w not in stopwords]
    name = "-".join(words)

    name = re.sub(r".*insights?-", "", name)
    name = re.sub(r".*topics?-", "", name)
    name = re.sub(r"-?\d{1,3}d?-?k?-?topics?-?", "-", name)
    name = re.sub(r"-?\d{1,3}d?-?k?-?topic?-?", "-", name)
    name = re.sub(r"-?\d{4}-?", "-", name)
    name = re.sub(r"\b(topics?|topic|insights?|insight)\b", "", name)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name


def shorten_topic_candidate(text: str) -> str:
    words = [w for w in text.split() if w]
    return " ".join(words[:3])


def normalize_topic_links(text: str, threshold: float = 0.78) -> str:
    def repl(match: re.Match[str]) -> str:
        raw_slug = match.group(1).strip()
        candidate = raw_slug.replace("-", " ").replace("_", " ")
        candidate = normalize_topic_name(candidate)
        candidate = shorten_topic_candidate(candidate)

        slug, created_new = resolve_or_create_topic(candidate, threshold=threshold)
        return f"[[topics/{slug}]]"

    return TOPIC_LINK_RE.sub(repl, text)


def run_llm_and_validate(backend: str, prompt: str) -> str:
    raw_output = run_llm(backend, prompt)

    print("\n===== RAW LLM OUTPUT =====\n")
    print(raw_output[:4000])
    print("\n===== END RAW LLM OUTPUT =====\n")

    fixed_output = normalize_topic_links(raw_output)
    fixed_output = normalize_insight_links(fixed_output)

    if re.search(r'\[\[insights\/[^\]]+\]\]', fixed_output):
        return fixed_output

    retry_prompt = (
        prompt
        + "\n\n"
        + "Your previous answer was invalid because it did not include any "
        + "required [[insights/...]] links.\n"
        + "Return ONLY clean Markdown.\n"
        + "You MUST include the required Extraction Block.\n"
        + "Do not add any prose after <!-- END EXTRACTION -->."
    )

    raw_output = run_llm(backend, retry_prompt)

    print("\n===== RAW LLM RETRY OUTPUT =====\n")
    print(raw_output[:4000])
    print("\n===== END RAW LLM RETRY OUTPUT =====\n")

    fixed_output = normalize_topic_links(raw_output)
    fixed_output = normalize_insight_links(fixed_output)

    if not re.search(r'\[\[insights\/[^\]]+\]\]', fixed_output):
        raise ValueError("LLM output invalid: missing insight links after retry")

    return fixed_output


# === use for create reports ===
def run_reports(
    target_date: str,
    granularity: str,
    backend: str,
    start_date=None,
    end_date=None,
):
    """
    Pipeline entrypoint for reports generation.
    """
    if granularity == "all":
        granularities = ["day", "week", "month"]
    else:
        granularities = [granularity]

    for g in granularities:
        result = generate_reports(
            granularity=g,
            target_date=target_date,
            source_dir=BASE_DIR / "insights",
            output_dir=BASE_DIR / "reports",
            prompt_dir=PROMPTS_DIR,
            llm_callable=lambda prompt, provider, model: run_llm(backend, prompt),
        )
        print(f"report done: {result.output_path}")


def build_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execution-analysis-backend",
        choices=["ollama"],
    )

    parser.add_argument(
        "--date",
        "--execution-analysis-backend-date",
        dest="target_date",
        default=TODAY,
        help="Target date in YYYY-MM-DD format.",
    )

    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--agg", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--reindex", action="store_true")

    parser.add_argument("--merge-apply", action="store_true")
    parser.add_argument("--merge-dry-run", action="store_true")
    parser.add_argument("--merge-threshold", type=float, default=0.88)

    parser.add_argument("--ranking", action="store_true")

    parser.add_argument("--cluster-topics", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.84)

    parser.add_argument(
        "--reports-backend",
        choices=["ollama"],
    )

    parser.add_argument(
        "--reports-granularity",
        choices=["day", "week", "month", "all", "custom"],
        default="all",
    )
    parser.add_argument("--reports-start-date")
    parser.add_argument("--reports-end-date")

    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    load_env()

    target_date = args.target_date

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Time to get some fresh info in ({target_date})...")

    if args.fetch:
        fetch_news(target_date)

    if args.init:
        create_daily(target_date)

    daily_file = DAILY_DIR / f"{target_date}.md"

    if args.execution_analysis_backend:
        inbox_file = INBOX_DIR / f"{target_date}.md"

        if not inbox_file.exists():
            raise FileNotFoundError(
                f"Missing inbox file: {inbox_file}\n"
                f"Run with --fetch first."
            )

        prompt = build_prompt_for_inbox(target_date, max_items=10)

        print(f"Running LLM ({args.execution_analysis_backend})...")

        fixed_output = run_llm_and_validate(
            args.execution_analysis_backend,
            prompt,
        )

        daily_file.write_text(
            fixed_output,
            encoding="utf-8",
        )

    if args.agg:
        aggregate_insights(target_date)
        print("aggregate done.")

    if args.clean:
        delete_bad_node_files()
        clean_all_markdown()
        print("Cleanup done.")

    if args.merge_dry_run:
        print("Auto-merging insights preview...")

        merge_cmd = [
            sys.executable,
            "-m",
            "src.auto_merge_insights",
            "--threshold",
            str(args.merge_threshold),
            "--dry-run",
        ]

        run_cmd(merge_cmd)

    if args.merge_apply:
        print("Auto-merging insights...")

        merge_cmd = [
            sys.executable,
            "-m",
            "src.auto_merge_insights",
            "--threshold",
            str(args.merge_threshold),
            "--apply",
        ]

        run_cmd(merge_cmd)

    if args.reindex:
        build_insight_index()
        build_topic_index()
        print("embedding index refreshed.")

    if args.ranking:
        scores = build_ranking()
        write_ranking_report(scores)
        print("ranking done.")

    if args.cluster_topics:
        items = read_topic_files()

        if len(items) < 2:
            print("Not enough topic files to cluster.")
            return

        clusters = build_clusters(
            items,
            args.threshold,
        )

        write_topic_clusters_report(
            clusters,
            items,
        )

        print("topic clustering done.")

    if args.reports_backend:
        print(f"topic clustering done:{args.reports_backend}")
        run_reports(
            target_date=target_date,
            granularity=args.reports_granularity,
            backend=args.reports_backend,
            start_date=args.reports_start_date,
            end_date=args.reports_end_date,
        )


if __name__ == "__main__":
    main()
