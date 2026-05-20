import os
import subprocess
import argparse
import sys
from clean_up import *
from embedding_memory import *
from ranking import build_ranking, write_report as write_ranking_report
from topic_clustering import (
    read_topic_files,
    build_clusters,
    write_report as write_topic_clusters_report,
)
from topic_memory import resolve_or_create_topic, build_index as build_topic_index

from generate_reports import generate_reports
from config import *


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

def fetch_news() -> None:
    print("Fetching news...")
    run_cmd([sys.executable, str(SRC_DIR / "fetch_news.py")])

def create_daily(date_str: str) -> Path:
    print("Creating daily note...")
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    daily_file = DAILY_DIR / f"{date_str}.md"
    return daily_file

def aggregate_insights():
    run_cmd([sys.executable, str(SRC_DIR / "aggregate_insights.py")])

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
    if backend == "gemini":
        result = subprocess.run(
            ["gemini", "--yolo", "-p", prompt],
            capture_output=True,
            text=True,
            check=True,
        )
    elif backend == "ollama":
        model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")

    return result.stdout


def normalize_insight_links(text: str, threshold: float = 0.82) -> str:
    """
    把 LLM 產生的 [[insights/...]] 做 embedding 比對：
    - 相似就 reuse 舊 insight
    - 不相似才保留/建立新 slug
    """
    # === regex ===
    INSIGHT_LINK_RE = re.compile(r"\[\[insights/([^\]]+)\]\]")

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

        # 移除 k-insights pattern（更強）
        # ⭐ 直接砍掉 "insights" 前面的所有東西
        name = re.sub(r".*insights?-", "", name)
        name = re.sub(r".*topics?-", "", name)

        # 先統一底線
        name = name.replace("_", "-")

        # 清掉常見噪音
        name = re.sub(r"-?\d{1,3}d?-?k?-?insights?-?", "-", name)
        name = re.sub(r"-?\d{4}-?", "-", name)

        # 清掉重複詞
        name = re.sub(r"(ai-search-)+", "ai-search-", name)
        name = re.sub(r"(smartwatch-)+", "smartwatch-", name)

        # 轉成 slug
        name = re.sub(r"[^a-z0-9]+", "-", name)
        name = re.sub(r"-{2,}", "-", name).strip("-")

        return name

    return INSIGHT_LINK_RE.sub(repl, text)



def normalize_topic_name(name: str) -> str:
    name = name.lower().strip()
    name = name.replace("_", "-")

    # ⭐ 放在這裡
    stopwords = {"topic", "topics", "insight", "insights", "news", "trend"}
    words = re.split(r"[-\s]+", name)
    words = [w for w in words if w not in stopwords]
    name = "-".join(words)

    # ⭐ 直接砍掉 "insights" 前面的所有東西
    name = re.sub(r".*insights?-", "", name)
    name = re.sub(r".*topics?-", "", name)

    # 清掉常見噪音
    name = re.sub(r"-?\d{1,3}d?-?k?-?topics?-?", "-", name)
    name = re.sub(r"-?\d{1,3}d?-?k?-?topic?-?", "-", name)
    name = re.sub(r"-?\d{4}-?", "-", name)

    # 移除明顯垃圾詞
    name = re.sub(r"\b(topics?|topic|insights?|insight)\b", "", name)

    # 壓成乾淨 slug
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
def run_reports(target_date: str, granularity: str, backend: str):
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






# === main pipeline ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-analysis-backend",choices=["ollama"])
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
    parser.add_argument("--threshold", type=float, default=0.84) #  for cluster-topic tunning
    parser.add_argument("--reports-backend",choices=["ollama"])  # execute all report
    parser.add_argument("--reports-granularity", choices=["day", "week", "month", "all"], default="all")
    args = parser.parse_args()

    load_env()

    print(f"Time to get some fresh info in ({TODAY})...")
    # === conditional steps ===
    if args.fetch:
        fetch_news()

    if args.init:
        create_daily(TODAY)

    daily_file = DAILY_DIR / f"{TODAY}.md"

    # === run data ===
    if args.execution_analysis_backend:
        prompt = build_prompt_for_inbox(TODAY)
        print(f"Running LLM ({args.backend})...")
        # === run Embedding_memory to avoid duplicated insights in graph ===
        raw_output = run_llm(args.backend, prompt)
        fixed_output = normalize_topic_links(raw_output)
        fixed_output = normalize_insight_links(fixed_output)
        daily_file.write_text(fixed_output, encoding="utf-8")

    # === aggregation ===
    if args.agg:
        aggregate_insights()
        print("aggregate done.")

    if args.clean:
        delete_bad_node_files()
        clean_all_markdown()
        print("Cleanup done.")

    if args.merge:
        print("Auto-merging insights...")
        merge_cmd = [
            sys.executable,
            str(SRC_DIR / "auto_merge_insights.py"),
            "--threshold",
            str(args.merge_threshold),
        ]

        if args.merge_apply:
            merge_cmd.append("--apply")
        else:
            merge_cmd.append("--dry-run")

        run_cmd(merge_cmd)

    # === embedding index refresh ===
    if args.reindex:
        build_insight_index()
        build_topic_index()
        print("embedding index refreshed.")

    # === ranking ===
    if args.ranking:
        scores = build_ranking()
        write_ranking_report(scores)
        print("ranking done.")

    # === cluster-topics===
    if args.cluster_topics:
        items = read_topic_files()
        if len(items) < 2:
            print("Not enough topic files to cluster.")
            return
        clusters = build_clusters(items, args.threshold)
        write_topic_clusters_report(clusters, items)
        print("topic clustering done.")

    # === Reports===
    if args.reports:
        run_reports(
            TODAY,
            args.reports_granularity,
            args.reports_backend,
        )


if __name__ == "__main__":
    main()