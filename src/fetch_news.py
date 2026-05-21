import argparse
import feedparser
import yaml

from src.config import *
from datetime import datetime

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch RSS news into inbox/YYYY-MM-DD.md"
    )

    parser.add_argument(
        "--date",
        default=TODAY,
        help="Target date for inbox file.",
    )

    return parser.parse_args()

def entry_matches_date(entry, target_date: str) -> bool:
    target = datetime.strptime(
        target_date,
        "%Y-%m-%d",
    ).date()

    published = None

    if hasattr(entry, "published_parsed") and entry.published_parsed:
        published = datetime(*entry.published_parsed[:6]).date()

    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        published = datetime(*entry.updated_parsed[:6]).date()

    if published is None:
        return False

    return published == target

def main() -> int:
    args = parse_args()

    target_date = args.date

    with open(f"{CONFIGS_DIR}/sources.yaml") as f:
        sources = yaml.safe_load(f)

    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    output = INBOX_DIR / f"{target_date}.md"

    lines = [f"# {target_date} News Inbox\n\n"]

    for category, feeds in sources.items():
        lines.append(f"## {category.capitalize()}\n\n")

        for feed in feeds:
            parsed = feedparser.parse(feed["url"])

            matched_entries = [
                entry
                for entry in parsed.entries
                if entry_matches_date(entry, target_date)
            ]

            if not matched_entries:
                fallback_entries = parsed.entries[:3]

                lines.append(
                    f"- No exact-date entries found for "
                    f"{feed['name']} ({target_date})\n"
                )

                matched_entries = fallback_entries

            for entry in matched_entries[:5]:
                lines.append(
                    f"- [{entry.title}]({entry.link}) "
                    f"— {feed['name']}\n"
                )

        lines.append("\n")

    output.write_text(
        "".join(lines),
        encoding="utf-8",
    )

    print("News fetched:", output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())