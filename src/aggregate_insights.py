import argparse
from src.config import *


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate daily insights."
    )

    parser.add_argument(
        "--date",
        default=TODAY,
        help="Target date in YYYY-MM-DD format.",
    )

    return parser.parse_args()


def clean_name(name: str) -> str:
    name = name.strip().lower()

    name = re.sub(r"[^a-z0-9\-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name)

    return name.strip("-")


def main() -> int:
    args = parse_args()
    target_date = args.date

    daily_file = DAILY_DIR / f"{target_date}.md"
    if not daily_file.exists():
        print("No daily file:", daily_file)
        return 0

    content = daily_file.read_text(encoding="utf-8")

    block_match = re.search(
        r"## Extraction Block(.*?)<!-- END EXTRACTION -->",
        content,
        flags=re.S,
    )

    if block_match:
        parse_text = block_match.group(1)
    else:
        parse_text = content
        print(f"[WARN] Extraction block not found in {daily_file}; falling back to full content.")

    raw_insights = sorted(set(re.findall(INSIGHT_PATTERN, parse_text)))
    raw_topics = sorted(set(re.findall(TOPIC_PATTERN, parse_text)))

    insights = [clean_name(i) for i in raw_insights]
    topics = [clean_name(t) for t in raw_topics]

    # 去掉空字串，保留順序後再去重
    insights = list(dict.fromkeys(i for i in insights if i))
    topics = list(dict.fromkeys(t for t in topics if t))

    print("Aggregated insights:", insights)

    if not insights:
        print(f"[WARN] No insights found for {target_date}")
        return 0

    backlink_line = f"- Derived from [[daily/{target_date}]]"
    topic_lines = [f"- Related topic: [[topics/{t}]]" for t in topics]

    for insight in insights:
        insight_file = INSIGHTS_DIR / f"{insight}.md"

        if not insight_file.exists():
            insight_file.write_text(f"# {insight}\n", encoding="utf-8")

        existing = insight_file.read_text(encoding="utf-8")

        section_header = f"## {target_date}"

        # 如果這個日期已經寫過，就不要重複 append
        if section_header in existing:
            continue

        with open(insight_file, "a", encoding="utf-8") as f:
            f.write(f"\n{section_header}\n")
            f.write(backlink_line + "\n")
            for line in topic_lines:
                f.write(line + "\n")

    print("Aggregated insights:", insights)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())