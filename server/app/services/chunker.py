"""Chunker: heuristic function/class-aware splitting for Python and JS/TS
(regex on top-level definition lines, not full AST parsing — see ARCHI.md
§4.3 for why), fixed-size + overlap fallback for everything else."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import CHUNK_FALLBACK_LINES, CHUNK_OVERLAP_LINES

PYTHON_BOUNDARY = re.compile(r"^(?:async\s+def|def|class)\s+\w+")
JS_TS_BOUNDARY = re.compile(
    r"^(?:export\s+(?:default\s+)?)?"
    r"(?:async\s+)?"
    r"(?:function\s*\*?\s*\w*|class\s+\w+|"
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(.*?\)\s*=>|"
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?function)"
)


@dataclass
class Chunk:
    text: str
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive


def _boundary_indices(lines: list[str], boundary: re.Pattern) -> list[int]:
    return [i for i, line in enumerate(lines) if boundary.match(line)]


def _chunks_from_boundaries(lines: list[str], boundaries: list[int]) -> list[Chunk]:
    chunks: list[Chunk] = []
    if boundaries[0] > 0:
        chunks.append(Chunk(text="\n".join(lines[0:boundaries[0]]), start_line=1, end_line=boundaries[0]))
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        text = "\n".join(lines[start:end])
        if text.strip():
            chunks.append(Chunk(text=text, start_line=start + 1, end_line=end))
    return chunks


def _fixed_size_chunks(lines: list[str]) -> list[Chunk]:
    chunks: list[Chunk] = []
    step = CHUNK_FALLBACK_LINES - CHUNK_OVERLAP_LINES
    for start in range(0, len(lines), step):
        end = min(start + CHUNK_FALLBACK_LINES, len(lines))
        text = "\n".join(lines[start:end])
        if text.strip():
            chunks.append(Chunk(text=text, start_line=start + 1, end_line=end))
        if end == len(lines):
            break
    return chunks


def chunk_file(text: str, language: str) -> list[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []

    boundary = {"python": PYTHON_BOUNDARY, "javascript": JS_TS_BOUNDARY, "typescript": JS_TS_BOUNDARY}.get(language)
    if boundary is not None:
        boundaries = _boundary_indices(lines, boundary)
        if boundaries:
            return _chunks_from_boundaries(lines, boundaries)

    return _fixed_size_chunks(lines)
