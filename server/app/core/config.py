"""Shared constants. See ARCHI.md §4.2-4.3 for the reasoning behind these."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / ".data"
CHROMA_DIR = DATA_DIR / "chroma"
SQLITE_PATH = DATA_DIR / "context_packer.sqlite3"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOKENIZER_ENCODING = "cl100k_base"

# Directory names excluded regardless of .gitignore contents — never walked.
HARD_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    ".idea",
    ".vscode",
}

# Filename patterns excluded regardless of .gitignore — secrets and noise
# that should never be indexed or leave the machine embedded in a bundle.
HARD_EXCLUDED_FILE_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "*.p12",
    "*.pfx",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
    "*.min.js",
    "*.map",
    # Ignore-pattern files: filename globs, not prose or code — no semantic
    # content to rank on, so they should never be indexed at all rather than
    # scored (found via a real bug report: .gitignore was picking up
    # non-trivial relevance scores for unrelated queries). Excluding at scan
    # time, not just down-weighting, since there's nothing useful in them to
    # ever surface in a packed bundle. See ARCHI.md §4.3.
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    ".eslintignore",
    ".prettierignore",
    ".npmignore",
)

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".wav",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".pyc",
    ".db", ".sqlite", ".sqlite3",
    ".whl",
}

MAX_FILE_SIZE_BYTES = 1_000_000  # skip anything over ~1MB as likely non-source

CHUNK_FALLBACK_LINES = 40
CHUNK_OVERLAP_LINES = 10

DEFAULT_TOKEN_BUDGET = 8192
RRF_K = 60
RETRIEVAL_TOP_K = 40  # candidates pulled from each of vector/BM25 before fusion

# BM25 tokenization filters these out before scoring. Without this, a chunk
# that shares only common function words with the query (e.g. "the") can
# still post a non-trivial BM25 score — worse on short chunks, since BM25's
# length normalization rewards them. Found via a real bug report: a
# docstring chunk whose only overlapping token with "optimize the database
# query performance" was "the" ranked #1 overall. See ARCHI.md §4.3.
BM25_STOPWORDS = frozenset(
    """
    a an the this that these those
    is am are was were be been being
    to of in on at by for with from as
    and or but if then than so not no nor
    it its it's he she they them his her their our your my
    i you we do does did doing done
    have has had having
    will would shall should can could may might must
    there here what which who whom whose when where why how
    all any both each few more most other some such
    only own same too very just also
    """.split()
)

# Confidence heuristic for /pack: a result counts as "normal" confidence if
# EITHER signal found something real — a close vector match OR a strong raw
# BM25 hit — else "low". Calibrated against all-MiniLM-L6-v2's L2 distance
# distribution (genuine semantic matches observed ~0.9-1.3; unrelated
# content ~1.9-2.3) and this module's BM25_STOPWORDS list. Revisit both
# numbers if the embedding model or stopword list changes. See ARCHI.md §4.3.
CONFIDENCE_MAX_VECTOR_DISTANCE = 1.5
CONFIDENCE_MIN_BM25_SCORE = 3.0
