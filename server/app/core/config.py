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
