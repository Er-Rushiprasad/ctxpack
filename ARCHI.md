# Context Packer — Architecture Reference

> This file is the source of truth for Claude Code while building this project.
> Read it before generating code. Keep it updated as decisions change — treat it
> like a living CLAUDE.md companion, not a one-time spec.

## 1. Problem

Anyone using Claude.ai / ChatGPT in the browser (i.e. not Claude Code) has to
manually decide which files from a repo to paste into a chat. Too few files →
bad answers. Too many → wasted tokens, diluted relevance, and hitting context
limits. There's no tool that ranks files by relevance to a stated task and
auto-assembles a right-sized bundle.

## 2. Product Summary

**Context Packer** is a Chrome extension + local companion server that:
1. Scans a local repo/folder.
2. Takes a short task description from the user ("fix the auth bug in login flow").
3. Uses hybrid retrieval (BM25 + embeddings) to rank files/chunks by relevance.
4. Packs the highest-relevance content into a token-budgeted bundle.
5. Shows token count + file list, lets the user tweak inclusion/exclusion.
6. One-click: copy to clipboard, or inject directly into the active
   claude.ai / chatgpt.com textarea.

## 3. Why This Shape (Key Architectural Decision)

Browser extensions (Manifest V3) **cannot read arbitrary local filesystem
paths**. So the system is split into two processes:

- **Extension (browser-side):** UI, page injection, orchestration. No file
  access.
- **Local Companion Server (machine-side):** does the actual repo scanning,
  chunking, embedding, and ranking. Runs on `localhost` only. Extension talks
  to it over `http://127.0.0.1:<port>`.

This also solves privacy by default: code never leaves the user's machine
unless they explicitly choose a cloud embedding provider later (v2 option).

```
┌─────────────────────┐        HTTP (localhost)        ┌──────────────────────────┐
│ Chrome Extension     │ ───────────────────────────▶  │ Local Companion Server   │
│ (React 19 + TS +     │ ◀───────────────────────────  │ (FastAPI, Python)        │
│  Tailwind v4)         │        JSON bundle             │                          │
│                       │                                 │  - repo scanner          │
│  - popup/sidebar UI   │                                 │  - chunker               │
│  - task input         │                                 │  - hybrid retriever      │
│  - bundle preview      │                                 │    (BM25 + vector)       │
│  - inject into page    │                                 │  - token packer          │
└─────────────────────┘                                 └──────────────────────────┘
                                                                    │
                                                          ┌─────────────────┐
                                                          │ Local vector     │
                                                          │ store (Chroma)   │
                                                          └─────────────────┘
```

## 4. Components

### 4.1 Chrome Extension
- **Stack:** React 19, TypeScript, Tailwind v4, Manifest V3, bundled with
  Vite (`extension/vite.config.ts`, `@tailwindcss/vite` plugin — Tailwind v4
  is CSS-first, see `src/index.css`).
- **Build layout:** `vite build` outputs `extension/dist/` (load this
  directory as the unpacked extension, not `extension/` itself).
  `public/manifest.json` is copied through by Vite's default `publicDir`
  behavior; `popup.html` at the extension root is the sole entry point for
  now. Root-relative asset paths (`/assets/...`) in the built HTML resolve
  correctly under `chrome-extension://<id>/` since that's the page's origin.
- **Responsibilities (current, Phase 2):**
  - Popup (`src/popup/`): checks `/status`, lets the user scan a new repo
    path or pick a previously-scanned one (`RepoPicker.tsx`), enter a task
    description, choose a token budget preset (`TokenBudgetPicker.tsx`), and
    pack. `BundlePreview.tsx` shows the ranked file list with per-file
    include/exclude toggles; toggling recomputes the token count and
    reassembles the copy-to-clipboard text entirely client-side using each
    file's `content` field from `/pack` (`src/lib/bundle.ts`) — no round
    trip needed. `src/lib/api.ts` is the fetch wrapper (surfaces FastAPI's
    `detail` field on errors).
  - Content script (`src/content/content.ts`, Phase 3): matches
    `https://claude.ai/*`, tries a selector list (ProseMirror
    contenteditable → generic contenteditable → textarea — most-specific
    first, since claude.ai's DOM has changed before and will again) and
    inserts text via `execCommand('insertText', ...)`, which reliably fires
    the input events ProseMirror-style editors listen for. Responds to a
    `chrome.runtime.onMessage` with `{ok: true}` or
    `{ok: false, reason: ...}`; the popup's `src/lib/inject.ts` sends the
    message and falls back to clipboard with a specific message on any
    failure (no tab open, tab unreachable/stale content script, composer not
    found, insert failed) — verified each path with Playwright against a
    mock composer page, since the real claude.ai selector still needs a
    live user check.
  - Built as a **second Vite config** (`vite.content.config.ts`, library
    mode, IIFE, fixed `content.js` filename, `emptyOutDir: false`) run after
    the popup build (`npm run build` runs both) — content scripts need one
    stable-path file, unlike the popup's normally-hashed assets.
  - Re-scan indicator: popup calls `GET /repos/{repo_id}/check` (backed by
    `indexer.compute_fingerprint` — hash of every candidate file's
    path/size/mtime, no content read) whenever the selected repo changes,
    and shows a badge + always-available Re-scan button.
  - Onboarding: gated on `chrome.storage.local.get(['onboarded'])`, shown
    once, explains the two-process split and gives the server start command.
  - Talks to local server via `fetch` (CORS enabled server-side for
    `chrome-extension://.*` origins).
- **No direct file system access.** No API keys stored in extension storage
  beyond user-provided ones (encrypted via `chrome.storage.session` where
  possible, never `localStorage`).

### 4.2 Local Companion Server
- **Stack:** FastAPI (Python), reuse of existing hybrid retrieval pipeline
  (LlamaIndex + ChromaDB + BM25, same pattern as prior RAG work).
- **Tooling:** managed with `uv`, project lives entirely inside `server/`
  (`server/pyproject.toml`, `server/.venv`) — independent of any tooling
  `extension/` picks up later, per §8. Run via `uv sync` then
  `uv run uvicorn app.main:app --reload`.
- **CORS:** `CORSMiddleware` with `allow_origin_regex="chrome-extension://.*"`
  so any locally-loaded unpacked extension can reach it (extension ids churn
  across reloads during dev; tighten to a fixed id before any wider release).
- **Responsibilities:**
  - `POST /scan` — index a given repo path (chunk + embed + store in Chroma).
  - `POST /pack` — given a task description + token budget, return ranked,
    packed bundle (file paths, chunk contents, total token count).
  - `GET /status` — health check / indexing progress.
  - `GET /repos/{repo_id}/check` — cheap "has this repo changed since its
    last scan" check (fingerprint comparison, no re-embedding); backs the
    extension's re-scan indicator.
- **Runs locally only** — binds to `127.0.0.1`, never `0.0.0.0`.
- **Packaging (MVP):** simple `pip install` + `python -m context_packer.server`.
  V2: bundle as a signed local binary so non-technical users don't need Python.

### 4.3 Retrieval / Packing Core
- Chunking: regex/indentation heuristic, not full AST parsing — splits on
  top-level `def`/`class` lines for Python and top-level
  `function`/`class`/exported-arrow-function patterns for JS/TS; anything
  else (or a file with no matches) falls back to fixed-size chunks (40 lines,
  10-line overlap). See `server/app/services/chunker.py`.
- Retrieval: direct ChromaDB (vector similarity) + `rank-bm25` (keyword),
  merged by reciprocal rank fusion (`k=60`) — no LlamaIndex dependency
  (decided in Phase 1: we couldn't reuse the "prior RAG work" pattern
  directly since that codebase isn't available here, so went with the
  simpler direct integration instead). See `server/app/services/retriever.py`.
- One Chroma collection (`chunks`) shared across all scanned repos,
  disambiguated by a `repo_id` metadata field (sha1 of the normalized repo
  path) rather than one collection per repo.
- Packing algorithm: greedy by fused relevance score under token budget
  (`tiktoken`, `cl100k_base` — an approximation since there's no public
  Claude tokenizer; counts run slightly high relative to Claude's real
  tokenizer, which is fine for a conservative budget). Chunks are grouped
  back under their source file and ordered by line number within each file.
  See `server/app/services/packer.py`.
- Output format: file-tree summary of included paths, then per-file blocks
  with a `--- path (lines a-b) ---` header before each chunk's content.
- Server-side state: SQLite (`server/.data/context_packer.sqlite3`) holds the
  repo registry (`repo_id`, path, scan timestamp, file/chunk counts,
  fingerprint) and per-chunk metadata; Chroma (`server/.data/chroma/`) holds
  embeddings + chunk text. Both paths are gitignored — regenerated by
  `/scan`.

#### Ranking bug fixes (found via dogfooding, see `claude-code-prompt-ranking-fix.md`)

Three real bugs in BM25 scoring, found by comparing raw BM25/vector scores
side by side for queries with no real answer in the corpus:

1. **No stopword filtering.** `_tokenize()` used to keep every token,
   including "the", "a", "to", etc. A chunk sharing *only* a stopword with
   the query could still post a non-trivial BM25 score — worse for short
   chunks, since BM25's length normalization rewards them. Fixed with
   `BM25_STOPWORDS` in `server/app/core/config.py`, applied in
   `retriever._tokenize`.
2. **Zero-score chunks were still "ranked."** When BM25 finds no real match
   at all, every chunk ties at score 0.0. Python's stable sort then returns
   them in original insertion (scan) order — and the old code fed all of
   them into RRF as if that reflected real relevance. Fixed: only chunks
   with `bm25_score > 0` enter `bm25_ranked` now; if none exist, BM25
   contributes nothing and ranking falls back cleanly to vector similarity.
3. **Snake_case/camelCase identifiers were one opaque token.** `\w+`
   includes underscores, so `DATABASE_URL` tokenized as a single
   `database_url` token that could never match a query's standalone
   "database". `_tokenize` now also emits the identifier's constituent
   words (`_SUBWORD_RE` in `retriever.py`) alongside the full token, so both
   literal-identifier and human-language queries can match code.
4. **File-type filtering decision**: `.gitignore` (and
   `.gitattributes`/`.dockerignore`/`.eslintignore`/`.prettierignore`/
   `.npmignore`) are now hard-excluded at scan time
   (`HARD_EXCLUDED_FILE_PATTERNS` in `config.py`), not just down-weighted.
   Decision: these are filename-pattern lists with no prose or code
   semantics — there's nothing in them worth ever surfacing in a packed
   bundle, so exclusion is strictly better than trying to score them fairly.

**Known, unfixed limitation**: neither BM25 nor the embedding model
understands negation. A test file whose docstring says "Not related to
authentication" still scores well for auth-related queries, because both
retrieval methods see the literal word "authentication" and have no way to
know it's being negated. This is a fundamental property of lexical/dense
retrieval, not a bug in this pipeline — fixing it would require an
LLM-based reranking step (noted as a v2 candidate in §8, not built here).

**Confidence signal**: RRF's fused score is rank-based, not
magnitude-based, so its numeric range stays roughly the same regardless of
whether anything genuinely matched — it structurally can't express "nothing
here is a good match." `/pack` now returns `confidence: "low" | "normal"`,
computed from the *raw* component scores (best raw BM25 score, closest
vector distance) rather than the fused score. Thresholds
(`CONFIDENCE_MAX_VECTOR_DISTANCE = 1.5`, `CONFIDENCE_MIN_BM25_SCORE = 3.0`
in `config.py`) are calibrated against `all-MiniLM-L6-v2`'s observed L2
distance distribution (genuine matches ~0.9–1.3, unrelated content
~1.9–2.3) and the current stopword list — revisit both if either changes.
The extension's per-file relevance bars don't yet surface this flag; that's
a follow-up UI task, intentionally not done here.
- Change detection: `scanner.iter_candidate_paths` (the same exclusion walk
  `scan_repo` uses) is reused by `indexer.compute_fingerprint` to hash every
  candidate file's `(path, size, mtime)` — cheap enough to run on every repo
  selection in the popup without re-embedding anything.

## 5. Tech Stack

| Layer               | Choice                                    |
|----------------------|--------------------------------------------|
| Extension UI         | React 19, TypeScript, Tailwind v4          |
| Extension build      | Vite                                       |
| Local server          | FastAPI (Python 3.13), managed with `uv`   |
| Embedding model        | sentence-transformers/all-MiniLM-L6-v2 (local) |
| Retrieval             | ChromaDB (vector) + rank-bm25 (keyword), merged via reciprocal rank fusion |
| Token counting         | tiktoken (or equivalent for target model)  |
| Local storage (server) | SQLite (metadata) + Chroma (vectors)       |
| Packaging (v1)         | pip package, run as local process          |

## 6. MVP Scope (v1)

- [x] Local server: `/scan` and `/pack` endpoints working end-to-end on a
      single repo (Phase 1 / Milestone M1, see PLAN.md §4).
- [x] Extension popup: repo path input, task input, "Pack Context" button
      (Phase 2 / Milestone M2, see PLAN.md §5).
- [x] Bundle preview with token count and per-file toggle (include/exclude).
- [x] Copy-to-clipboard.
- [x] Manual injection into claude.ai textarea (content script) — Phase 3
      / Milestone M3, see PLAN.md §6. Mechanism verified via Playwright
      against a mock composer page; the real claude.ai selector still needs
      a live check (see PLAN.md's M3 notes).

### Explicitly out of scope for v1
- ChatGPT injection (add after claude.ai flow is solid).
- Cloud embedding provider option.
- Multi-repo / monorepo support.
- Auto-detecting task from clipboard/context.
- Packaged binary distribution (Python install is fine for v1 dogfooding).

## 7. Open Decisions (revisit as we build)

- Embedding model: local (sentence-transformers, no API cost, slower) vs
  Anthropic/OpenAI embeddings (better quality, requires API key + costs).
  → **Decided for v1: local, `sentence-transformers/all-MiniLM-L6-v2`.**
  Spike 1 (`server/scripts/spike_embeddings.py`) measured ~2.3 min to embed
  a 500-file repo (warm model, ~32 chunks/s, ~500MB RSS) on dev machine —
  comfortably under the 5-min gate in PLAN.md. Revisit only if real repos
  produce far more chunks/file than the ~8 assumed here.
- How the extension discovers "which repos have been scanned" — likely just
  a list returned by `/status` from the local server.
- Auth between extension and local server: none for v1 (localhost-only trust
  boundary), revisit if we ever allow remote server mode.

## 8. Conventions for Claude Code

- Keep extension and server as separate top-level folders (`extension/`,
  `server/`) with independent tooling — don't cross-import.
- Server: standard FastAPI project layout (`app/api`, `app/core`,
  `app/services`); type hints everywhere; Pydantic models for all
  request/response shapes.
- Extension: functional components only, hooks-based state, Tailwind utility
  classes only (no custom CSS files unless unavoidable).
- No secrets in code or committed config — `.env` for server, never bundle
  keys into the extension.
- Every new endpoint or major component gets a short note added back into
  this file under the relevant section — this doc should stay accurate as
  the build progresses, not just reflect day-1 planning.
