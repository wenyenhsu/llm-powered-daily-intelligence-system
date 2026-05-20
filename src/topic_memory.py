from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

import requests

from config import *

def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_text(text: str, model: str = EMBED_MODEL) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embedding"]


def read_topic_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:4000]


def build_index() -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)

    items = []
    for file in TOPICS_DIR.glob("*.md"):
        if should_skip(file):
            continue
        text = read_topic_text(file)
        items.append(
            {
                "slug": file.stem,
                "path": str(file.relative_to(BASE_DIR)),
                "text": text[:1000],
                "embedding": embed_text(text),
            }
        )

    index = {
        "model": EMBED_MODEL,
        "items": items,
    }

    TOPIC_INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_index() -> dict[str, Any]:
    if not TOPIC_INDEX_FILE.exists():
        return build_index()
    return json.loads(TOPIC_INDEX_FILE.read_text(encoding="utf-8"))


def match_topic(candidate_text: str, threshold: float = 0.78) -> dict[str, Any]:
    index = load_index()
    candidate_emb = embed_text(candidate_text)

    best = {
        "slug": None,
        "score": 0.0,
        "path": None,
    }

    for item in index["items"]:
        score = cosine_similarity(candidate_emb, item["embedding"])
        if score > best["score"]:
            best = {
                "slug": item["slug"],
                "score": score,
                "path": item["path"],
            }

    if best["score"] >= threshold:
        return {
            "matched": True,
            "slug": best["slug"],
            "score": best["score"],
            "path": best["path"],
        }

    return {
        "matched": False,
        "slug": None,
        "score": best["score"],
        "path": None,
    }

def resolve_or_create_topic(candidate: str, threshold: float = 0.78) -> tuple[str, bool]:
    """
    returns:
      (slug, created_new)
    """
    result = match_topic(candidate, threshold=threshold)

    if result["matched"]:
        return result["slug"], False

    slug = slugify(candidate)
    topic_file = TOPICS_DIR / f"{slug}.md"

    if not topic_file.exists():
        topic_file.write_text(
            f"# {slug}\n\n## Description\n- Auto-created topic node\n",
            encoding="utf-8",
        )

    return slug, True