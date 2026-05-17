import feedparser
import yaml
from datetime import datetime

with open("references/sources.yaml") as f:
    sources = yaml.safe_load(f)

date = datetime.now().strftime("%Y-%m-%d")
output = f"inbox/{date}.md"

lines = [f"# {date} News Inbox\n"]

for category, feeds in sources.items():
    lines.append(f"## {category.capitalize()}\n")
    for feed in feeds:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[:3]:
            lines.append(f"- [{entry.title}]({entry.link}) — {feed['name']}\n")

with open(output, "w") as f:
    f.writelines(lines)

print("News fetched:", output)