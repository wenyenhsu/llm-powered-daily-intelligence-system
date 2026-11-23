"""Exercise real retrieval with a temporary index and a mocked HTTP backend.

Run from the repository root with the project virtual environment. Exit 1 means
the required rejection/backend isolation failed; exit 0 means both hold.
"""

import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import embedding_memory as memory


def main():
    index = {
        "model": "model-A",
        "items": [{
            "slug": "same-dimension",
            "path": "insights/same-dimension.md",
            "text": "A vector from another representation space.",
            "embedding": [1.0, 0.0],
        }],
    }
    response = Mock()
    response.json.return_value = {"embedding": [1.0, 0.0]}
    print("Expected: ValueError naming model-A, model-B and --reindex; zero HTTP calls.")
    print("Indexed vector and mocked query vector both have dimension 2.")
    # Set OLLAMA_EMBED_MODEL=model-B before starting Python, so the original
    # embed_text default also selects model-B (no mock of the retrieval code).
    print(f"Configured query model: {memory.OLLAMA_EMBED_MODEL}")
    with tempfile.TemporaryDirectory() as directory:
        index_file = Path(directory) / "insight_index.json"
        original_bytes = json.dumps(index).encode("utf-8")
        index_file.write_bytes(original_bytes)
        with patch.object(memory, "INSIGHT_INDEX_FILE", index_file), patch.object(
            memory.requests, "post", return_value=response
        ) as post:
            error = None
            results = None
            try:
                results = memory.retrieve_top_insights("query", top_k=1, min_score=0.5)
            except ValueError as exc:
                error = str(exc)
            print("Actual exception:", repr(error))
            print("Actual results:", repr(results))
            print("Embedding HTTP calls:", post.call_count)
            if post.called:
                print("Embedding HTTP payload:", post.call_args.kwargs["json"])
            unchanged = index_file.read_bytes() == original_bytes
            print("Temporary index bytes unchanged:", unchanged)
    passed = (
        error is not None
        and all(token in error for token in ("model-A", "model-B", "--reindex"))
        and post.call_count == 0
        and unchanged
    )
    print("PASS" if passed else "FAIL: incompatible models were not rejected before embedding")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
