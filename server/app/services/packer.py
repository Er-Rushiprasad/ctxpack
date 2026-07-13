"""Packer: greedy selection of retrieved chunks under a token budget, then
assembled into a file-tree summary + per-file content blocks (ARCHI.md §4.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import tiktoken

from app.core.config import TOKENIZER_ENCODING
from app.services.retriever import RetrievedChunk

_encoding = tiktoken.get_encoding(TOKENIZER_ENCODING)


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


@dataclass
class PackedFile:
    path: str
    chunks: list[RetrievedChunk] = field(default_factory=list)

    @property
    def token_count(self) -> int:
        return sum(count_tokens(_chunk_block(c)) for c in self.chunks)

    @property
    def relevance_score(self) -> float:
        return max((c.score for c in self.chunks), default=0.0)


@dataclass
class PackResult:
    bundle: str
    token_count: int
    files: list[PackedFile]


def _chunk_block(chunk: RetrievedChunk) -> str:
    return f"--- {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line}) ---\n{chunk.text}\n"


def _assemble(included: list[RetrievedChunk]) -> str:
    files: dict[str, PackedFile] = {}
    for chunk in included:
        files.setdefault(chunk.file_path, PackedFile(path=chunk.file_path)).chunks.append(chunk)
    for pf in files.values():
        pf.chunks.sort(key=lambda c: c.start_line)

    # Order files by their best-scoring chunk, most relevant first.
    ordered_files = sorted(files.values(), key=lambda pf: pf.relevance_score, reverse=True)

    tree_summary = "\n".join(f"- {pf.path}" for pf in ordered_files)
    body = "\n".join(_chunk_block(c) for pf in ordered_files for c in pf.chunks)
    return f"# Files included ({len(ordered_files)})\n{tree_summary}\n\n{body}"


def pack_chunks(ranked_chunks: list[RetrievedChunk], token_budget: int) -> PackResult:
    # Greedy by relevance score, but the fit check re-measures the whole
    # assembled bundle (header + tree summary included) each time rather
    # than just summing chunk blocks, so the final result never exceeds
    # token_budget once assembled.
    included: list[RetrievedChunk] = []
    for chunk in ranked_chunks:
        candidate = included + [chunk]
        if count_tokens(_assemble(candidate)) > token_budget:
            continue
        included = candidate

    bundle = _assemble(included)
    files: dict[str, PackedFile] = {}
    for chunk in included:
        files.setdefault(chunk.file_path, PackedFile(path=chunk.file_path)).chunks.append(chunk)
    for pf in files.values():
        pf.chunks.sort(key=lambda c: c.start_line)
    ordered_files = sorted(files.values(), key=lambda pf: pf.relevance_score, reverse=True)

    return PackResult(bundle=bundle, token_count=count_tokens(bundle), files=ordered_files)
