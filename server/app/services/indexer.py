"""Indexing: chunks -> embeddings -> ChromaDB; repo/chunk metadata -> SQLite.

One shared Chroma collection ("chunks") holds every scanned repo's chunks,
disambiguated by a repo_id metadata field, rather than one collection per
repo (see ARCHI.md §4.3).
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import CHROMA_DIR, DATA_DIR, SQLITE_PATH
from app.services.chunker import chunk_file
from app.services.embeddings import embed_texts
from app.services.scanner import iter_candidate_paths, scan_repo

_CHROMA_ADD_BATCH_SIZE = 500


def get_repo_id(repo_path: str) -> str:
    return hashlib.sha1(str(Path(repo_path).resolve()).encode("utf-8")).hexdigest()[:16]


def compute_fingerprint(repo_path: str) -> str:
    """Cheap "has this repo changed since we last scanned it" signal: hash
    of every candidate file's (path, size, mtime), without reading content —
    reuses scan_repo's exclusion walk (scanner.iter_candidate_paths) so a
    change check doesn't require a full re-embed to answer."""
    root = Path(repo_path).resolve()
    parts = []
    for path in sorted(iter_candidate_paths(root)):
        try:
            stat = path.stat()
        except OSError:
            continue
        parts.append(f"{path.relative_to(root)}:{stat.st_size}:{int(stat.st_mtime)}")
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()


def _connect_sqlite() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repos (
            repo_id TEXT PRIMARY KEY,
            repo_path TEXT NOT NULL,
            last_scanned_at TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            chunk_count INTEGER NOT NULL,
            fingerprint TEXT NOT NULL DEFAULT ''
        )
        """
    )
    try:
        # Migration for DBs created before the fingerprint column existed.
        conn.execute("ALTER TABLE repos ADD COLUMN fingerprint TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            repo_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            language TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL
        )
        """
    )
    return conn


def get_chroma_collection():
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection("chunks")


@dataclass
class IndexResult:
    repo_id: str
    repo_path: str
    files_scanned: int
    files_skipped: int
    chunks_indexed: int


def index_repo(repo_path: str) -> IndexResult:
    scanned_files, skipped = scan_repo(repo_path)
    repo_id = get_repo_id(repo_path)
    resolved_path = str(Path(repo_path).resolve())
    fingerprint = compute_fingerprint(repo_path)

    chunk_ids: list[str] = []
    chunk_texts: list[str] = []
    chunk_metas: list[dict] = []
    for f in scanned_files:
        for c in chunk_file(f.text, f.language):
            chunk_ids.append(f"{repo_id}::{f.rel_path}::{c.start_line}-{c.end_line}")
            chunk_texts.append(c.text)
            chunk_metas.append(
                {
                    "repo_id": repo_id,
                    "file_path": f.rel_path,
                    "language": f.language,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                }
            )

    collection = get_chroma_collection()
    collection.delete(where={"repo_id": repo_id})
    if chunk_texts:
        embeddings = embed_texts(chunk_texts)
        for i in range(0, len(chunk_ids), _CHROMA_ADD_BATCH_SIZE):
            end = i + _CHROMA_ADD_BATCH_SIZE
            collection.add(
                ids=chunk_ids[i:end],
                embeddings=embeddings[i:end],
                documents=chunk_texts[i:end],
                metadatas=chunk_metas[i:end],
            )

    conn = _connect_sqlite()
    with conn:
        conn.execute("DELETE FROM chunks WHERE repo_id = ?", (repo_id,))
        conn.executemany(
            "INSERT INTO chunks (chunk_id, repo_id, file_path, language, start_line, end_line) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (cid, m["repo_id"], m["file_path"], m["language"], m["start_line"], m["end_line"])
                for cid, m in zip(chunk_ids, chunk_metas)
            ],
        )
        conn.execute(
            """
            INSERT INTO repos (repo_id, repo_path, last_scanned_at, file_count, chunk_count, fingerprint)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                repo_path = excluded.repo_path,
                last_scanned_at = excluded.last_scanned_at,
                file_count = excluded.file_count,
                chunk_count = excluded.chunk_count,
                fingerprint = excluded.fingerprint
            """,
            (
                repo_id,
                resolved_path,
                datetime.now(timezone.utc).isoformat(),
                len(scanned_files),
                len(chunk_ids),
                fingerprint,
            ),
        )
    conn.close()

    return IndexResult(
        repo_id=repo_id,
        repo_path=resolved_path,
        files_scanned=len(scanned_files),
        files_skipped=skipped,
        chunks_indexed=len(chunk_ids),
    )


def list_repos() -> list[dict]:
    conn = _connect_sqlite()
    try:
        rows = conn.execute(
            "SELECT repo_id, repo_path, last_scanned_at, file_count, chunk_count FROM repos "
            "ORDER BY last_scanned_at DESC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "repo_id": r[0],
            "repo_path": r[1],
            "last_scanned_at": r[2],
            "file_count": r[3],
            "chunk_count": r[4],
        }
        for r in rows
    ]


def repo_needs_rescan(repo_id: str) -> bool:
    conn = _connect_sqlite()
    try:
        row = conn.execute(
            "SELECT repo_path, fingerprint FROM repos WHERE repo_id = ?", (repo_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise KeyError(f"no repo indexed with repo_id={repo_id!r}")
    repo_path, stored_fingerprint = row
    return compute_fingerprint(repo_path) != stored_fingerprint


def get_repo_chunks(repo_id: str) -> dict:
    """Returns Chroma's raw get() result (ids/documents/metadatas) for every
    chunk belonging to repo_id — used by the BM25 side of retrieval, which
    needs the full corpus rather than a top-k vector match."""
    collection = get_chroma_collection()
    return collection.get(where={"repo_id": repo_id}, include=["documents", "metadatas"])
