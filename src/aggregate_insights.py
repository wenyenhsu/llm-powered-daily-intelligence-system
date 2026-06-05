from __future__ import annotations

import argparse
import re

from src.config import *


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate daily insights.")
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


def extract_block(content: str) -> str:
    match = EXTRACTION_BLOCK_RE.search(content)
    if match:
        return match.group(1)

    print("[WARN] Extraction block not found; falling back to full content.")
    return content


def build_section(target_date: str, topics: list[str]) -> str:
    lines = [
        f"## {target_date}",
        f"- Derived from [[daily/{target_date}]]",
    ]
    for topic in topics:
        lines.append(f"- Related topic: [[topics/{topic}]]")
    lines.append("")
    return "\n".join(lines)


def upsert_section(existing: str, target_date: str, section_text: str) -> str:
    section_header = f"## {target_date}"

    pattern = re.compile(
        rf"(^|\n){re.escape(section_header)}.*?(?=\n## |\Z)",
        flags=re.S,
    )

    if pattern.search(existing):
        updated = pattern.sub("\n" + section_text.rstrip() + "\n", existing, count=1)
        return updated.rstrip() + "\n"

    if not existing.endswith("\n"):
        existing += "\n"
    return existing.rstrip() + "\n\n" + section_text.rstrip() + "\n"


def main() -> int:
    args = parse_args()
    target_date = args.date

    daily_file = DAILY_DIR / f"{target_date}.md"
    if not daily_file.exists():
        print("No daily file:", daily_file)
        return 0

    content = daily_file.read_text(encoding="utf-8")
    parse_text = extract_block(content)

    raw_insights = sorted(set(INSIGHT_LINK_RE.findall(parse_text)))
    raw_topics = sorted(set(TOPIC_LINK_RE.findall(parse_text)))

    insights = list(
        dict.fromkeys(
            clean_name(i)
            for i in raw_insights
            if clean_name(i)
        )
    )
    topics = list(
        dict.fromkeys(
            clean_name(t)
            for t in raw_topics
            if clean_name(t)
        )
    )

    print("Aggregated insights:", insights)

    if not insights:
        print(f"[WARN] No insights found for {target_date}")
        return 0

    section_text = build_section(target_date, topics)

    for insight in insights:
        insight_file = INSIGHTS_DIR / f"{insight}.md"

        if insight_file.exists():
            existing = insight_file.read_text(encoding="utf-8")
        else:
            existing = f"# {insight}\n"

        updated = upsert_section(existing, target_date, section_text)
        insight_file.write_text(updated, encoding="utf-8")

    print("Aggregated insights:", insights)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
