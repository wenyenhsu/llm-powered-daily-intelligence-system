from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any
from config import *
import requests




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


def read_insight_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # 只取比較有訊息的內容做 embedding
    return text[:4000]


def build_insight_index() -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    items = []
    for file in INSIGHTS_DIR.glob("*.md"):
        slug = file.stem
        text = read_insight_text(file)
        emb = embed_text(text)
        items.append(
            {
                "slug": slug,
                "path": str(file.relative_to(BASE_DIR)),
                "text": text[:1000],
                "embedding": emb,
            }
        )

    index = {
        "model": EMBED_MODEL,
        "items": items,
    }

    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_index() -> dict[str, Any]:
    if not INDEX_FILE.exists():
        return build_insight_index()
    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))


def match_insight(candidate_text: str, threshold: float = 0.82) -> dict[str, Any]:
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


def upsert_index_for_file(file_path: Path) -> None:
    """
    當新增或更新 insight 檔案時，刷新 index。
    """
    build_insight_index()