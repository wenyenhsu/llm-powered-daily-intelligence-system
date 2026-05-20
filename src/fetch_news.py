import feedparser
import yaml
from config import *

with open(f"{CONFIGS_DIR}/sources.yaml") as f:
    sources = yaml.safe_load(f)

output = f"{INBOX_DIR}/{TODAY}.md"

lines = [f"# {TODAY} News Inbox\n"]

for category, feeds in sources.items():
    lines.append(f"## {category.capitalize()}\n")
    for feed in feeds:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[:3]:
            lines.append(f"- [{entry.title}]({entry.link}) — {feed['name']}\n")

with open(output, "w") as f:
    f.writelines(lines)

print("News fetched:", output)