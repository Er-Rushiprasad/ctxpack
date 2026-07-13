"""Hybrid retrieval: vector similarity (ChromaDB) + keyword (BM25), merged
via reciprocal rank fusion. No LlamaIndex — see ARCHI.md §4.3 for why."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from rank_bm25 import BM25Okapi

from app.core.config import (
    BM25_STOPWORDS,
    CONFIDENCE_MAX_VECTOR_DISTANCE,
    CONFIDENCE_MIN_BM25_SCORE,
    RETRIEVAL_TOP_K,
    RRF_K,
)
from app.services.embeddings import embed_texts
from app.services.indexer import get_chroma_collection, get_repo_chunks

_TOKEN_RE = re.compile(r"\w+")
# Splits snake_case/camelCase/PascalCase identifiers into constituent words
# (e.g. "DATABASE_URL" -> "DATABASE", "URL"; "getUserById" -> "get", "User",
# "By", "Id"). Without this, BM25 tokenizes an identifier as one opaque
# token ("database_url"), so a query for "database" can never match it even
# though the identifier is literally about a database — found via a real
# bug report where settings.py's DATABASE_URL didn't surface for "optimize
# the database query performance".
_SUBWORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        tokens.append(raw.lower())
        subwords = _SUBWORD_RE.findall(raw)
        if len(subwords) > 1:
            tokens.extend(w.lower() for w in subwords)
    return [t for t in tokens if t not in BM25_STOPWORDS]


@dataclass
class RetrievedChunk:
    chunk_id: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    text: str
    score: float


@dataclass
class HybridSearchResult:
    chunks: list[RetrievedChunk]
    confidence: Literal["low", "normal"]


def hybrid_search(repo_id: str, query: str, top_k: int = RETRIEVAL_TOP_K) -> HybridSearchResult:
    corpus = get_repo_chunks(repo_id)
    ids: list[str] = corpus["ids"]
    if not ids:
        return HybridSearchResult(chunks=[], confidence="low")
    documents: list[str] = corpus["documents"]
    metadatas: list[dict] = corpus["metadatas"]
    text_by_id = dict(zip(ids, documents))
    meta_by_id = dict(zip(ids, metadatas))

    bm25 = BM25Okapi([_tokenize(doc) for doc in documents])
    bm25_scores = bm25.get_scores(_tokenize(query))
    # Only chunks BM25 actually found evidence for (score > 0) belong in its
    # ranked list. Without this filter, a query with no keyword matches at
    # all leaves every score tied at 0.0, and Python's stable sort then
    # returns them in their original insertion order — which RRF would treat
    # as a real ranking signal (effectively "rank by scan order") even
    # though BM25 found nothing. Found via a real bug report where this
    # silently contaminated results for queries with no matching vocabulary.
    bm25_order = sorted(range(len(ids)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_ranked = [ids[i] for i in bm25_order if bm25_scores[i] > 0][:top_k]
    best_bm25_score = float(bm25_scores.max()) if len(bm25_scores) else 0.0

    query_embedding = embed_texts([query])[0]
    collection = get_chroma_collection()
    vector_result = collection.query(
        query_embeddings=[query_embedding],
        where={"repo_id": repo_id},
        n_results=min(top_k, len(ids)),
        include=["distances"],
    )
    vector_ranked: list[str] = vector_result["ids"][0] if vector_result["ids"] else []
    vector_distances: list[float] = vector_result["distances"][0] if vector_result["distances"] else []
    best_vector_distance = min(vector_distances) if vector_distances else float("inf")

    fused_scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(vector_ranked):
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, chunk_id in enumerate(bm25_ranked):
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    ranked_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

    chunks = [
        RetrievedChunk(
            chunk_id=cid,
            file_path=meta_by_id[cid]["file_path"],
            language=meta_by_id[cid]["language"],
            start_line=meta_by_id[cid]["start_line"],
            end_line=meta_by_id[cid]["end_line"],
            text=text_by_id[cid],
            score=fused_scores[cid],
        )
        for cid in ranked_ids
    ]

    # RRF's fused score is rank-based, not magnitude-based, so it's always
    # squeezed into roughly the same narrow numeric range regardless of
    # whether anything genuinely matched — it can't itself signal "weak
    # match". Confidence instead looks at the raw component scores: a
    # strong result needs either close semantic distance or a real keyword
    # hit. Thresholds calibrated against all-MiniLM-L6-v2's distance
    # distribution and this stopword list — revisit both if either changes.
    # See ARCHI.md §4.3.
    confidence: Literal["low", "normal"] = (
        "normal"
        if best_vector_distance <= CONFIDENCE_MAX_VECTOR_DISTANCE or best_bm25_score >= CONFIDENCE_MIN_BM25_SCORE
        else "low"
    )

    return HybridSearchResult(chunks=chunks, confidence=confidence)
