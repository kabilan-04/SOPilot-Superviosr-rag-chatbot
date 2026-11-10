"""Local vector store (replaces Pinecone).

Chunks and their embeddings are kept in one JSON file next to the code.
Search is cosine similarity with numpy. For a few hundred chunks this is
instant, needs no account or API key, and works offline with Ollama.
"""
import json
import os
from pathlib import Path
from typing import List, Optional

import numpy as np
from dotenv import load_dotenv

from documents import meta_for, query_wants_old_revision

load_dotenv()

STORE_PATH = Path(os.getenv("VECTOR_STORE_PATH", "vector_store.json"))


def _load() -> dict:
    if STORE_PATH.exists():
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {}


def store_chunks(chunks: List[str], embeddings: List[List[float]], source: str = ""):
    """Save the chunks of one PDF. Re-running replaces that PDF's old chunks (no duplicates)."""
    data = _load()
    data[source] = [
        {"text": chunk, "chunk_index": i, "embedding": emb}
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]
    STORE_PATH.write_text(json.dumps(data), encoding="utf-8")


def search_chunks(
    query_vector: List[float],
    top_k: int = 4,
    query: Optional[str] = None,
):
    """Return ranked hits with source metadata.

    Superseded files (QC-SOP-014 Rev 03) are skipped unless the question
    asks for the old revision. That is the shop-floor safety improvement:
    Rev 04 changed the sampling plan.
    """
    data = _load()
    want_old = query_wants_old_revision(query or "")
    items = []
    for src, chunks in data.items():
        status = meta_for(src)["status"]
        if status == "superseded" and not want_old:
            continue
        for c in chunks:
            items.append((src, c))

    if not items:
        raise RuntimeError("Vector store is empty. Run `python dataprocessor.py` first.")

    matrix = np.array([c["embedding"] for _, c in items], dtype=np.float32)
    q = np.array(query_vector, dtype=np.float32)
    scores = (matrix @ q) / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-9)

    best = np.argsort(-scores)[:top_k]
    hits = []
    for i in best:
        source, chunk = items[i]
        info = meta_for(source)
        hits.append(
            {
                "text": chunk["text"],
                "source": source,
                "title": info["title"],
                "status": info["status"],
                "score": float(scores[i]),
                "chunk_index": chunk["chunk_index"],
            }
        )
    return hits
