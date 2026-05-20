from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta


from config import *


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def extract_links(text: str) -> list[str]:
    return [m.strip() for m in INSIGHT_LINK_RE.findall(text)]


def get_recent_daily_files(days: int = 7) -> list[Path]:
    cutoff = datetime.now() - timedelta(days=days)
    files = []

    if not DAILY_DIR.exists():
        return files

    for md in DAILY_DIR.glob("*.md"):
        if should_skip(md):
            continue
        if md.stat().st_mtime >= cutoff.timestamp():
            files.append(md)

    return files


def build_ranking():
    insight_scores = Counter()
    backlinks = defaultdict(set)
    mentions = Counter()
    recent_mentions = Counter()

    # 1) 全庫掃描：統計所有 insight 被提到幾次
    for md in BASE_DIR.rglob("*.md"):
        if should_skip(md):
            continue

        text = md.read_text(encoding="utf-8", errors="ignore")
        links = extract_links(text)

        for link in links:
            mentions[link] += 1

            # 如果不是自己的檔案，就視為 backlink
            if md.parent.name != "insights" or md.stem != link:
                backlinks[link].add(str(md))

    # 2) 最近 7 天的 daily 加權
    recent_files = get_recent_daily_files(days=7)
    for md in recent_files:
        text = md.read_text(encoding="utf-8", errors="ignore")
        links = extract_links(text)
        for link in links:
            recent_mentions[link] += 1

    # 3) 計分
    for insight in set(list(mentions.keys()) + list(backlinks.keys()) + list(recent_mentions.keys())):
        score = 0

        # 基本被提及次數
        score += mentions[insight] * 2

        # 被其他檔案連回來
        score += len(backlinks[insight]) * 5

        # 最近出現頻率
        score += recent_mentions[insight] * 3

        # canonical insight 加一點分（如果檔案存在）
        if (INSIGHTS_DIR / f"{insight}.md").exists():
            score += 2

        insight_scores[insight] = score

    return insight_scores


def write_report(scores: Counter):
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    out = reports_dir / "top_insights.md"
    lines = ["# Top Insights\n"]

    for i, (insight, score) in enumerate(scores.most_common(20), start=1):
        lines.append(f"{i}. [[insights/{insight}]] — score: {score}\n")

    out.write_text("".join(lines), encoding="utf-8")
    print(f"Ranking written to {out}")


# def main():
#     scores = build_ranking()
#     write_report(scores)


