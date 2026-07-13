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
- **Stack:** React 19, TypeScript, Tailwind v4, Manifest V3.
- **Responsibilities:**
  - Popup/sidebar UI: pick a repo (already scanned by companion server),
    enter task description, trigger pack request.
  - Content script: detects claude.ai / chatgpt.com input box, injects
    assembled bundle text on user action.
  - Talks to local server via `fetch` (CORS enabled on server for the
    extension's origin only).
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
- **Runs locally only** — binds to `127.0.0.1`, never `0.0.0.0`.
- **Packaging (MVP):** simple `pip install` + `python -m context_packer.server`.
  V2: bundle as a signed local binary so non-technical users don't need Python.

### 4.3 Retrieval / Packing Core
- Chunking: file-aware (respect function/class boundaries where possible;
  fallback to fixed-size with overlap).
- Retrieval: hybrid BM25 (keyword) + vector similarity, reuse existing
  hybrid-scoring approach.
- Packing algorithm: greedy knapsack by relevance score under token budget
  (tiktoken-based counting), always include file path headers for context.
- Output format: structured bundle with a file tree summary + per-file
  content blocks, ready to paste.

## 5. Tech Stack

| Layer               | Choice                                    |
|----------------------|--------------------------------------------|
| Extension UI         | React 19, TypeScript, Tailwind v4          |
| Extension build      | Vite                                       |
| Local server          | FastAPI (Python 3.13), managed with `uv`   |
| Embedding model        | sentence-transformers/all-MiniLM-L6-v2 (local) |
| Retrieval             | LlamaIndex + ChromaDB, BM25 hybrid         |
| Token counting         | tiktoken (or equivalent for target model)  |
| Local storage (server) | SQLite (metadata) + Chroma (vectors)       |
| Packaging (v1)         | pip package, run as local process          |

## 6. MVP Scope (v1)

- [ ] Local server: `/scan` and `/pack` endpoints working end-to-end on a
      single repo.
- [ ] Extension popup: repo path input, task input, "Pack Context" button.
- [ ] Bundle preview with token count and per-file toggle (include/exclude).
- [ ] Copy-to-clipboard.
- [ ] Manual injection into claude.ai textarea (content script).

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
