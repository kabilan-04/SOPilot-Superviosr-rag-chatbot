from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import List

load_dotenv()

# Ollama exposes an OpenAI-compatible API at /v1, so the same client works.
# The api_key is required by the client library but ignored by Ollama.
client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key="ollama",
)

# Run once:  ollama pull nomic-embed-text
# nomic-embed-text produces 768-dimension vectors (OpenAI's was 1536),
# so the Pinecone index must be created with dimension=768.
EMBEDDING_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# nomic-embed-text was trained with task prefixes; retrieval quality is
# noticeably better when documents and queries use them.
DOC_PREFIX = "search_document: " if "nomic" in EMBEDDING_MODEL else ""
QUERY_PREFIX = "search_query: " if "nomic" in EMBEDDING_MODEL else ""


def embed_chunks(chunks: List[str], batch_size: int = 32) -> List[List[float]]:
    """Embeds chunks with the local Ollama embedding model (batched for speed)."""
    embeddings: List[List[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch = [DOC_PREFIX + c for c in chunks[i:i + batch_size]]
        response = client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


def embed_User_query(query: str) -> List[float]:
    """Embeds a user query with the local Ollama embedding model."""
    response = client.embeddings.create(
        input=QUERY_PREFIX + query,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding
