import subprocess
import argparse
import requests
import sys
import time
from src.clean_up import *
from src.embedding_memory import *
from src.ranking import build_ranking, write_report as write_ranking_report
from src.topic_clustering import (
    read_topic_files,
    build_clusters,
    write_report as write_topic_clusters_report,
)
from src.topic_memory import resolve_or_create_topic, build_index as build_topic_index

from src.generate_reports import generate_reports
from src.config import *
import argparse


# === load .env ===
def load_env():
    env_path = ENV_FILE
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v

# === run shell commands ===
def run_cmd(cmd):
    print(f"> {cmd}")
    subprocess.run(cmd, check=True)

def build_prompt_for_inbox(date_str):
    prompt = (PROMPTS_DIR / "summarized.md").read_text()
    data = (INBOX_DIR / f"{date_str}.md").read_text()
    return f"{prompt}\n\n--- DATA ---\n{data}"

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


def aggregate_insights(target_date: str):
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
def run_llm(backend, prompt):
    model = os.environ.get("OLLAMA_MODEL", "gemma3:12b")

    url = "http://localhost:11434/api/generate"

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
    # === regex ===
    def repl(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        candidate = normalize_name(raw)
        candidate = candidate.replace("-", " ")
        candidate = shorten_candidate(candidate)
        result = match_insight(candidate, threshold=threshold)

        if result["matched"]:
            slug = result["slug"]
        else:
            slug = slugify(candidate)

        return f"[[insights/{slug}]]"

    def shorten_candidate(text: str) -> str:
        words = text.split()[:4]  # ⭐ 最多 4 個詞
        return " ".join(words)

    def normalize_name(name: str) -> str:
        name = name.lower().strip()

        stopwords = {"insight", "insights", "analysis", "news", "trend"}
        words = re.split(r"[-\s]+", name)
        words = [w for w in words if w not in stopwords]
        name = "-".join(words)

# Remove k-insights pattern (more aggressive)
# Directly remove everything before "insights"
        name = re.sub(r".*insights?-", "", name)
        name = re.sub(r".*topics?-", "", name)

# Unify underscores
        name = name.replace("_", "-")

# Clear common noise
        name = re.sub(r"-?\d{1,3}d?-?k?-?insights?-?", "-", name)
        name = re.sub(r"-?\d{4}-?", "-", name)

# Clear duplicate words
        name = re.sub(r"(ai-search-)+", "ai-search-", name)
        name = re.sub(r"(smartwatch-)+", "smartwatch-", name)

# Convert to slug
        name = re.sub(r"[^a-z0-9]+", "-", name)
        name = re.sub(r"-{2,}", "-", name).strip("-")

        return name

    return INSIGHT_LINK_RE.sub(repl, text)



def normalize_topic_name(name: str) -> str:
    name = name.lower().strip()
    name = name.replace("_", "-")

    # Remove stopwords like "topic," "topics," and "insight"
    stopwords = {"topic", "topics", "insight", "insights", "news", "trend"}
    words = re.split(r"[-\s]+", name)
    words = [w for w in words if w not in stopwords]
    name = "-".join(words)

    # Directly remove everything before "insights" or "topics"
    name = re.sub(r".*insights?-", "", name)
    name = re.sub(r".*topics?-", "", name)

    # Clear common noise patterns like dates and numbers
    name = re.sub(r"-?\d{1,3}d?-?k?-?topics?-?", "-", name)
    name = re.sub(r"-?\d{1,3}d?-?k?-?topic?-?", "-", name)
    name = re.sub(r"-?\d{4}-?", "-", name)

    # Remove common words like "topics," "topic," and "insights"
    name = re.sub(r"\b(topics?|topic|insights?|insight)\b", "", name)

    # Convert to a clean slug
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")

    return name


def shorten_topic_candidate(text: str) -> str:
    words = [w for w in text.split() if w]
    return " ".join(words[:3])  # topic 不要太長，3 個詞通常夠了


def normalize_topic_links(text: str, threshold: float = 0.78) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        candidate = raw.replace("-", " ").replace("_", " ")
        candidate = normalize_topic_name(candidate)
        candidate = shorten_topic_candidate(candidate)

        slug, created_new = resolve_or_create_topic(candidate, threshold=threshold)

        return f"[[topics/{slug}]]"

    return TOPIC_LINK_RE.sub(repl, text)


# use for create reports
def run_reports(target_date: str, granularity: str, backend: str,start_date=None,end_date=None ):
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

    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--merge-threshold", type=float, default=0.88)
    parser.add_argument("--merge-apply", action="store_true")

    parser.add_argument("--ranking", action="store_true")

    parser.add_argument("--cluster-topics", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.84)

    parser.add_argument(
        "--reports-backend",
        choices=["ollama"],
    )

    parser.add_argument(
        "--reports-granularity",
        choices=["day", "week", "month", "all","custom"],
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
    INBOX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    INSIGHTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
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

        prompt = build_prompt_for_inbox(target_date)

        print(f"Running LLM ({args.execution_analysis_backend})...")

        raw_output = run_llm(
            args.execution_analysis_backend,
            prompt,
        )

        fixed_output = normalize_topic_links(raw_output)
        fixed_output = normalize_insight_links(fixed_output)

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

    if args.merge:
        print("Auto-merging insights...")

        merge_cmd = [
            sys.executable,
            "-m",
            "src.auto_merge_insights",
            "--threshold",
            str(args.merge_threshold),
        ]

        if args.merge_apply:
            merge_cmd.append("--apply")
        else:
            merge_cmd.append("--dry-run")

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