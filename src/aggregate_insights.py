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

    insight_pattern = r"\[\[insights\/([^\]]+)\]\]"
    insights = sorted(set(re.findall(insight_pattern, content)))

    topic_pattern = r"\[\[topics\/([^\]]+)\]\]"
    topics = sorted(set(re.findall(topic_pattern, content)))

    print("Aggregated insights:", insights)

    for insight in insights:
        insight = clean_name(insight)

        insight_file = INSIGHTS_DIR / f"{insight}.md"

        if not insight_file.exists():
            insight_file.write_text(
                f"# {insight}\n",
                encoding="utf-8",
            )

        existing = insight_file.read_text(encoding="utf-8")

        backlink_line = f"- Derived from [[daily/{target_date}]]"

        topic_lines = [
            f"- Related topic: [[topics/{t}]]"
            for t in topics
        ]

        # the error line will just append. This need to be rebuild
        if backlink_line not in existing:
            with open(insight_file, "a", encoding="utf-8") as f:
                f.write(f"\n## {target_date}\n")
                f.write(backlink_line + "\n")

                for line in topic_lines:
                    f.write(line + "\n")

    print("Aggregated insights:", insights)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())