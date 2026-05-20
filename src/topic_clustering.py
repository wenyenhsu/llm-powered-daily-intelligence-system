from __future__ import annotations

import argparse
from collections import defaultdict

import requests

from config import *





def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_text(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def read_topic_files() -> list[dict]:
    items = []
    if not TOPICS_DIR.exists():
        return items

    for md in sorted(TOPICS_DIR.glob("*.md")):
        if should_skip(md):
            continue

        text = md.read_text(encoding="utf-8", errors="ignore")
        items.append(
            {
                "path": md,
                "slug": md.stem,
                "text": text[:4000],
                "embedding": embed_text(text[:4000]),
            }
        )

    return items


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def build_clusters(items: list[dict], threshold: float) -> list[list[int]]:
    n = len(items)
    uf = UnionFind(n)

    for i in range(n):
        for j in range(i + 1, n):
            sim = cosine_similarity(items[i]["embedding"], items[j]["embedding"])
            if sim >= threshold:
                uf.union(i, j)

    groups = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)

    return list(groups.values())


def choose_canonical(group: list[int], items: list[dict]) -> int:
    # 優先短名稱，次要字母序
    return min(group, key=lambda i: (len(items[i]["slug"]), items[i]["slug"]))


def write_report(clusters: list[list[int]], items: list[dict]) -> None:
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    out = reports_dir / "topic_clusters.md"
    lines = ["# Topic Clusters\n\n"]

    cluster_id = 1
    for group in clusters:
        if len(group) < 2:
            continue

        canonical_idx = choose_canonical(group, items)
        canonical = items[canonical_idx]["slug"]

        lines.append(f"## Cluster {cluster_id}: [[topics/{canonical}]]\n")
        for idx in group:
            slug = items[idx]["slug"]
            if slug == canonical:
                continue
            lines.append(f"- [[topics/{slug}]]\n")

        lines.append("\n")
        cluster_id += 1

    if cluster_id == 1:
        lines.append("No topic clusters above threshold.\n")

    out.write_text("".join(lines), encoding="utf-8")
    print(f"Topic clusters written to {out}")
