"""Lazy singleton for the local embedding model (see PLAN.md Spike 1 /
ARCHI.md §7 for why this model was chosen)."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    return model.encode(texts, show_progress_bar=False).tolist()
