"""Hybrid retrieval: vector similarity (ChromaDB) + keyword (BM25), merged
via reciprocal rank fusion. No LlamaIndex — see ARCHI.md §4.3 for why."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.core.config import RETRIEVAL_TOP_K, RRF_K
from app.services.embeddings import embed_texts
from app.services.indexer import get_chroma_collection, get_repo_chunks

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class RetrievedChunk:
    chunk_id: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    text: str
    score: float


def hybrid_search(repo_id: str, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[RetrievedChunk]:
    corpus = get_repo_chunks(repo_id)
    ids: list[str] = corpus["ids"]
    if not ids:
        return []
    documents: list[str] = corpus["documents"]
    metadatas: list[dict] = corpus["metadatas"]
    text_by_id = dict(zip(ids, documents))
    meta_by_id = dict(zip(ids, metadatas))

    bm25 = BM25Okapi([_tokenize(doc) for doc in documents])
    bm25_scores = bm25.get_scores(_tokenize(query))
    bm25_ranked = [ids[i] for i in sorted(range(len(ids)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]]

    query_embedding = embed_texts([query])[0]
    collection = get_chroma_collection()
    vector_result = collection.query(
        query_embeddings=[query_embedding],
        where={"repo_id": repo_id},
        n_results=min(top_k, len(ids)),
    )
    vector_ranked: list[str] = vector_result["ids"][0] if vector_result["ids"] else []

    fused_scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(vector_ranked):
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, chunk_id in enumerate(bm25_ranked):
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

    ranked_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

    return [
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
