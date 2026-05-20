# src/auto_merge_insights.py
from __future__ import annotations

import argparse
import sys
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
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def read_insight_files() -> list[dict]:
    files = []
    if not INSIGHTS_DIR.exists():
        return files

    for md in sorted(INSIGHTS_DIR.glob("*.md")):
        if should_skip(md):
            continue
        text = md.read_text(encoding="utf-8")
        files.append(
            {
                "path": md,
                "slug": md.stem,
                "text": text,
                "embedding": embed_text(text[:4000]),
            }
        )
    return files


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
    # 優先：slug 最短，其次字母序最小
    return min(group, key=lambda i: (len(items[i]["slug"]), items[i]["slug"]))


def strip_main_heading(text: str) -> str:
    """
    移除第一個 H1，避免合併後重複標題。
    """
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip()
    return text.strip()


def merge_duplicate_text(canonical_text: str, dup_slug: str, dup_text: str) -> str:
    body = strip_main_heading(dup_text)
    if not body.strip():
        return canonical_text

    merged_block = f"\n\n## Merged from [[insights/{dup_slug}]]\n\n{body}\n"
    return canonical_text.rstrip() + merged_block


def rewrite_links_everywhere(mapping: dict[str, str], dry_run: bool) -> None:
    """
    把整個 vault 裡所有 [[insights/old]] 改成 [[insights/new]]
    """
    for md in BASE_DIR.rglob("*.md"):
        if should_skip(md):
            continue

        original = md.read_text(encoding="utf-8")
        updated = original

        def repl(match: re.Match[str]) -> str:
            old_slug = match.group(1).strip()
            alias_part = ""

            if "|" in old_slug:
                old_slug = old_slug.split("|", 1)[0].strip()

            if old_slug in mapping:
                new_slug = mapping[old_slug]
                return f"[[insights/{new_slug}]]"

            return match.group(0)

        updated = INSIGHT_LINK_RE.sub(repl, updated)

        if updated != original:
            print(f"Rewriting links: {md}")
            if not dry_run:
                md.write_text(updated, encoding="utf-8")


def delete_duplicate_files(dup_paths: list[Path], dry_run: bool) -> None:
    for path in dup_paths:
        print(f"Deleting duplicate insight file: {path}")
        if not dry_run:
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.88)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    dry_run = not args.apply

    if not INSIGHTS_DIR.exists():
        print(f"Missing insights dir: {INSIGHTS_DIR}")
        sys.exit(1)

    items = read_insight_files()
    if len(items) < 2:
        print("Not enough insight files to merge.")
        return

    clusters = build_clusters(items, args.threshold)

    mapping: dict[str, str] = {}
    dup_paths: list[Path] = []

    for group in clusters:
        if len(group) < 2:
            continue

        canonical_idx = choose_canonical(group, items)
        canonical = items[canonical_idx]
        canonical_slug = canonical["slug"]
        canonical_path = canonical["path"]

        print("\nCluster:")
        print(f"  Canonical: {canonical_slug}")

        merged_text = canonical["text"]

        for idx in group:
            if idx == canonical_idx:
                continue

            dup = items[idx]
            dup_slug = dup["slug"]
            dup_path = dup["path"]

            print(f"  Merge -> {dup_slug}")

            mapping[dup_slug] = canonical_slug
            dup_paths.append(dup_path)
            merged_text = merge_duplicate_text(merged_text, dup_slug, dup["text"])

        if not dry_run:
            canonical_path.write_text(merged_text, encoding="utf-8")

    if not mapping:
        print("No clusters above threshold. Nothing to merge.")
        return

    print("\n--- Link rewrite phase ---")
    rewrite_links_everywhere(mapping, dry_run=dry_run)

    print("\n--- Delete duplicate files ---")
    delete_duplicate_files(dup_paths, dry_run=dry_run)

    if dry_run:
        print("\nDry run complete. Re-run with --apply to commit changes.")
    else:
        print("\nMerge complete.")

    # 如果你有自己的 index builder，可以在這裡接上
    try:
        from embedding_memory import build_index  # type: ignore

        if not dry_run:
            build_index()
            print("Embedding index rebuilt.")
    except Exception:
        pass


if __name__ == "__main__":
    main()