import re

from config import *

daily_file = DAILY_DIR / f"{TODAY}.md"

if not daily_file.exists():
    print("No daily file:", daily_file)
    exit()

content = daily_file.read_text(encoding="utf-8")

# === 找 insight links ===
pattern = r"\[\[insights\/([^\]]+)\]\]"
insights = sorted(set(re.findall(pattern, content)))

topic_pattern = r"\[\[topics\/([^\]]+)\]\]"
topics = sorted(set(re.findall(topic_pattern, content)))

print("Aggregated insights:", insights)

# clear name for the ANSI control char
def clean_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name)
    return name.strip("-")


# === aggregation ===
for insight in insights:
    insight = clean_name(insight)
    insight_file = INSIGHTS_DIR / f"{insight}.md"

    if not insight_file.exists():
        insight_file.write_text(f"# {insight}\n", encoding="utf-8")

    existing = insight_file.read_text(encoding="utf-8")

    backlink_line = f"- Derived from [[daily/{TODAY}]]"
    topic_lines = [f"- Related topic: [[topics/{t}]]" for t in topics]

    with open(insight_file, "a", encoding="utf-8") as f:
        if backlink_line not in existing:
            f.write(f"\n## {TODAY}\n")
            f.write(backlink_line + "\n")
            for line in topic_lines:
                f.write(line + "\n")

print("Aggregated insights:", insights)
