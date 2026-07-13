"""Repo scanner: walks a directory, respects .gitignore, and hard-excludes
secrets/binaries/lockfiles regardless of .gitignore contents (never index
these — see PLAN.md's "Indexing secrets/.env by accident" risk)."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pathspec

from app.core.config import (
    BINARY_EXTENSIONS,
    HARD_EXCLUDED_DIRS,
    HARD_EXCLUDED_FILE_PATTERNS,
    MAX_FILE_SIZE_BYTES,
)

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}


@dataclass
class ScannedFile:
    abs_path: Path
    rel_path: str
    language: str
    text: str


def _is_hard_excluded_file(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in HARD_EXCLUDED_FILE_PATTERNS)


def _load_ignore_specs(root: Path) -> list[tuple[Path, pathspec.PathSpec]]:
    """Compile every .gitignore under root into (its directory, PathSpec)
    pairs. Patterns are matched relative to their own .gitignore's directory,
    which is how git itself resolves nested .gitignore files."""
    specs: list[tuple[Path, pathspec.PathSpec]] = []
    for gitignore in root.rglob(".gitignore"):
        if any(part in HARD_EXCLUDED_DIRS for part in gitignore.relative_to(root).parts):
            continue
        try:
            lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        specs.append((gitignore.parent, pathspec.PathSpec.from_lines("gitignore", lines)))
    return specs


def _is_gitignored(path: Path, specs: list[tuple[Path, pathspec.PathSpec]]) -> bool:
    for base, spec in specs:
        try:
            rel = path.relative_to(base)
        except ValueError:
            continue
        if spec.match_file(str(rel).replace(os.sep, "/")):
            return True
    return False


def iter_candidate_paths(root: Path, exclusion_counter: list[int] | None = None) -> Iterator[Path]:
    """Yields files that pass every exclusion rule (hard-excluded
    dirs/files, binary extensions, .gitignore) without reading their
    content — shared by scan_repo (which then reads+chunks them) and the
    repo-fingerprint check (which only needs cheap stat() calls).

    Pass a single-element list as exclusion_counter to have it incremented
    for every excluded file, so callers that need that count (scan_repo's
    user-facing files_skipped stat) don't need a second directory walk."""
    specs = _load_ignore_specs(root)
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if d not in HARD_EXCLUDED_DIRS and not _is_gitignored(current / d, specs)
        ]

        for filename in filenames:
            abs_path = current / filename
            ext = abs_path.suffix.lower()

            if (
                _is_hard_excluded_file(filename)
                or ext in BINARY_EXTENSIONS
                or _is_gitignored(abs_path, specs)
            ):
                if exclusion_counter is not None:
                    exclusion_counter[0] += 1
                continue
            yield abs_path


def scan_repo(repo_path: str) -> tuple[list[ScannedFile], int]:
    """Returns (scanned files with readable text content, count of files
    skipped for any reason)."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"{repo_path!r} is not a directory")

    scanned: list[ScannedFile] = []
    exclusion_counter = [0]
    skipped = 0

    for abs_path in iter_candidate_paths(root, exclusion_counter):
        ext = abs_path.suffix.lower()
        try:
            if abs_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                skipped += 1
                continue
        except OSError:
            skipped += 1
            continue

        try:
            data = abs_path.read_bytes()
        except OSError:
            skipped += 1
            continue
        if b"\x00" in data:
            skipped += 1
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            skipped += 1
            continue
        if not text.strip():
            skipped += 1
            continue

        scanned.append(
            ScannedFile(
                abs_path=abs_path,
                rel_path=str(abs_path.relative_to(root)).replace(os.sep, "/"),
                language=LANGUAGE_BY_EXTENSION.get(ext, "text"),
                text=text,
            )
        )

    return scanned, skipped + exclusion_counter[0]
