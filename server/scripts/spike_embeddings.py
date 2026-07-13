"""Phase 0, Spike 1: measure local embedding speed + memory on this machine.

Embeds ~100 real code chunks with sentence-transformers and reports timing
and process RSS, so we can decide (per PLAN.md's decision gate) whether local
embeddings are fast enough for a medium repo (~500 files) or whether we need
to fall back to an API embedding provider before Phase 1.

Run from server/: `uv run python scripts/spike_embeddings.py`
"""

import time
from pathlib import Path

import psutil

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_LINES = 40
TARGET_CHUNKS = 100


def collect_chunks(target: int) -> list[str]:
    """Pull real Python source out of installed packages as stand-ins for
    repo code chunks — this repo alone doesn't have enough files yet."""
    venv_site_packages = Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"
    chunks: list[str] = []
    for py_file in venv_site_packages.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for i in range(0, len(lines), CHUNK_LINES):
            chunk = "\n".join(lines[i : i + CHUNK_LINES]).strip()
            if chunk:
                chunks.append(chunk)
            if len(chunks) >= target:
                return chunks
    return chunks


def main() -> None:
    process = psutil.Process()
    rss_start_mb = process.memory_info().rss / 1_048_576

    chunks = collect_chunks(TARGET_CHUNKS)
    print(f"collected {len(chunks)} chunks")

    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    t1 = time.perf_counter()
    rss_after_load_mb = process.memory_info().rss / 1_048_576

    embeddings = model.encode(chunks, show_progress_bar=False)
    t2 = time.perf_counter()
    rss_after_embed_mb = process.memory_info().rss / 1_048_576

    load_s = t1 - t0
    embed_s = t2 - t1
    print(f"model load:        {load_s:.2f}s")
    print(f"embed {len(chunks)} chunks: {embed_s:.2f}s ({len(chunks) / embed_s:.1f} chunks/s)")
    print(f"embedding shape:   {embeddings.shape}")
    print(f"RSS start:         {rss_start_mb:.0f} MB")
    print(f"RSS after load:    {rss_after_load_mb:.0f} MB")
    print(f"RSS after embed:   {rss_after_embed_mb:.0f} MB")

    # Extrapolate to a medium repo: PLAN.md's decision gate is ~500 files.
    # Assume ~8 chunks/file on average (rough; refine once the real chunker
    # exists in Phase 1).
    est_chunks_500_files = 500 * 8
    est_seconds = load_s + (est_chunks_500_files / (len(chunks) / embed_s))
    print(
        f"\nestimated time for a 500-file repo (~{est_chunks_500_files} chunks): "
        f"{est_seconds:.0f}s ({est_seconds / 60:.1f} min)"
    )


if __name__ == "__main__":
    main()
