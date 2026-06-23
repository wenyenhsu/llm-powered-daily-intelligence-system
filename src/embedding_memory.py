from __future__ import annotations

import json
import math
from typing import Any
from src.config import *
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


def embed_text(text: str, model: str = OLLAMA_EMBED_MODEL) -> list[float]:
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
        "model": OLLAMA_EMBED_MODEL,
        "items": items,
    }

    INSIGHT_INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_index() -> dict[str, Any]:
    if not INSIGHT_INDEX_FILE.exists():
        return build_insight_index()
    return json.loads(INSIGHT_INDEX_FILE.read_text(encoding="utf-8"))


def insight_snippet(text: str, max_chars: int = INSIGHT_RETRIEVAL_SNIPPET_CHARS) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"\[\[[^\]]+\]\]", "", line).strip(" -")
        if not line:
            continue
        snippet = re.sub(r"\s+", " ", line)
        if len(snippet) > max_chars:
            return snippet[:max_chars].rstrip() + "..."
        return snippet
    return ""


def retrieve_top_insights(
    query_text: str,
    top_k: int = INSIGHT_RETRIEVAL_TOP_K,
    min_score: float = INSIGHT_RETRIEVAL_MIN_SCORE,
) -> list[dict[str, Any]]:
    index = load_index()
    items = index.get("items") or []
    if not items:
        return []

    query = query_text.strip()
    if not query:
        return []

    query_emb = embed_text(query[:4000])

    scored: list[dict[str, Any]] = []
    for item in items:
        score = cosine_similarity(query_emb, item["embedding"])
        if score < min_score:
            continue
        scored.append(
            {
                "slug": item["slug"],
                "score": score,
                "path": item.get("path"),
                "text": item.get("text", ""),
            }
        )

    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[:top_k]


def format_retrieved_insights_section(
    items: list[dict[str, Any]],
    snippet_chars: int = INSIGHT_RETRIEVAL_SNIPPET_CHARS,
) -> str:
    if not items:
        return ""

    lines = [
        "## Existing Insights (reuse when semantically matching)",
        "",
        "The following insights already exist in the knowledge base.",
        "Prefer reusing these links when a news item matches an existing concept.",
        "Do NOT create near-duplicate insight names if one of these already fits.",
        "",
    ]

    for item in items:
        slug = item["slug"]
        score = item["score"]
        snippet = insight_snippet(item.get("text", ""), snippet_chars)
        if snippet:
            lines.append(f"- [[insights/{slug}]] (relevance: {score:.2f}) — {snippet}")
        else:
            lines.append(f"- [[insights/{slug}]] (relevance: {score:.2f})")

    lines.append("")
    return "\n".join(lines)


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
    renew the index
    """
    build_insight_index()