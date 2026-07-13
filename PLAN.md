# Context Packer — Project Plan

> Companion to `ARCHI.md`. That file says **what we're building and how it's
> structured**; this file says **in what order, by when, and how we'll know
> it's working**. Update checkboxes and dates as you go — Claude Code should
> read both files at session start.

## 1. Goal & Success Criteria

**Goal:** Ship a working v1 that Rushi uses daily on his own projects
(EagleBurgmann, Sankalp, Rex Marcus repos) within ~4 weeks of part-time work.

**v1 is "done" when:**
- You can scan any local repo in under ~2 minutes (medium repo, ~500 files).
- You can type a task description and get a packed bundle under a chosen
  token budget in under ~5 seconds.
- Bundle can be copied or injected into claude.ai with one click.
- You personally stop hand-picking files for browser chats — that's the real
  test.

**Post-v1 success signal (before investing in v2):** at least 3–5 external
devs (colleagues/friends) install it and use it more than once without
hand-holding.

## 2. Phases Overview

| Phase | Focus                                  | Duration (part-time) |
|-------|------------------------------------------|----------------------|
| 0     | Setup & spike                           | 2–3 days             |
| 1     | Core engine (server, no UI)             | Week 1               |
| 2     | Extension UI + clipboard flow           | Week 2               |
| 3     | Page injection + polish                 | Week 3               |
| 4     | Dogfooding, fixes, private beta         | Week 4               |
| 5+    | v2 (only if beta signal is good)        | Later                |

---

## 3. Phase 0 — Setup & Spike (2–3 days)

Purpose: kill the riskiest unknowns before writing real code.

- [x] Create repo with `extension/` and `server/` top-level folders per ARCHI.md.
- [x] Add `ARCHI.md` + this `PLAN.md` to repo root; create `CLAUDE.md` that
      instructs Claude Code to read both.
- [x] **Spike 2 — extension ↔ localhost:** minimal MV3 extension (no build
      step yet — plain `manifest.json`/`popup.html`/`popup.js` in
      `extension/`) fetches `server/app/main.py`'s `/status` over
      `http://127.0.0.1:8000`. CORS enabled server-side via
      `CORSMiddleware(allow_origin_regex="chrome-extension://.*")`.
      Verified: server boots (`uv run uvicorn app.main:app`) and responds to
      `/status` and `/scan`. **Still needs a manual check**: load the
      extension unpacked in Chrome and click "Ping local server" — see
      `extension/README.md`. Decision gate passed assuming that manual check
      succeeds; flag here if it doesn't.
- [ ] **Spike 3 — claude.ai DOM:** `extension/content_spike.js` added,
      matches `https://claude.ai/*`, exposes `window.contextPackerSpike()` to
      manually trigger from devtools. Selector
      (`div[contenteditable="true"].ProseMirror`) is an untested best guess —
      **needs manual verification against the live claude.ai DOM** (see
      `extension/README.md` Spike 3 section) before this checkbox is truly
      done.
- [x] **Spike 1 — local embeddings:** `server/scripts/spike_embeddings.py`
      embeds 100 real code chunks with `sentence-transformers/all-MiniLM-L6-v2`.
      Results (warm model load, this machine): load 15.5s, encode 100 chunks
      in 3.1s (~32 chunks/s), RSS ~500MB. Extrapolated to a 500-file repo
      (~4000 chunks): **~2.3 min**, well under the 5-min gate.
      **Decision: local embeddings via `all-MiniLM-L6-v2` are viable for
      v1** — no need for API embeddings yet. Revisit only if real-world
      chunk counts run much higher than the ~8 chunks/file estimate used
      here.

> If all 3 spikes pass, architecture is validated. If any fail, update
> ARCHI.md before proceeding — do not build around a broken assumption.

## 4. Phase 1 — Core Engine (Week 1)

Server-only. Test everything via curl/HTTPie or a scratch script — no UI yet.

- [x] FastAPI skeleton: `app/api` (routes.py, schemas.py), `app/core`
      (config.py — hard-exclusion lists, model/tokenizer names, budget
      defaults), `app/services` (scanner, chunker, embeddings, indexer,
      retriever, packer). Pydantic models for all request/response shapes in
      `app/api/schemas.py`.
- [x] Repo scanner (`app/services/scanner.py`): walks the tree, prunes
      hard-excluded dirs (`.git`, `node_modules`, `.venv`, `dist`, etc.) and
      files (`.env*`, keys/certs, lockfiles, `.min.js`, `.map`) regardless of
      `.gitignore`, plus respects nested `.gitignore` files, binary
      extensions, oversized files (>1MB), and non-UTF-8/empty content.
      Covered by `server/tests/test_scanner.py` (3 tests, all passing) per
      the risk table's "add tests for it" note.
- [x] Chunker (`app/services/chunker.py`): regex heuristic on top-level
      `def`/`class` lines for Python, top-level function/class/exported-arrow
      patterns for JS/TS; fixed-size (40 lines, 10 overlap) fallback
      otherwise. Not full AST/tree-sitter parsing — see ARCHI.md §4.3.
- [x] Indexing (`app/services/indexer.py`): chunks → embeddings
      (`sentence-transformers/all-MiniLM-L6-v2`) → one shared Chroma
      collection tagged by `repo_id`; repo registry + chunk metadata → SQLite
      (`server/.data/`, gitignored).
- [x] Hybrid retrieval (`app/services/retriever.py`): ChromaDB vector search
      + `rank-bm25` keyword search, merged via reciprocal rank fusion
      (no LlamaIndex — see ARCHI.md §4.3 for why the plan changed here).
- [x] Packer (`app/services/packer.py`): greedy by fused relevance score,
      re-measuring the whole assembled bundle (tiktoken `cl100k_base`) each
      step so the final bundle never exceeds `token_budget`; file-tree
      summary + per-file `--- path (lines a-b) ---` blocks.
- [x] Endpoints live: `POST /scan`, `POST /pack`, `GET /status`
      (`app/api/routes.py`).
- [x] **Milestone M1 — passed:** scanned this repo itself (25 files, 83
      chunks, ~25s including one-time model warmup) via `curl POST /scan`,
      then `curl POST /pack` with the task "how does the /pack endpoint turn
      retrieved chunks into a token-budgeted bundle" returned a sensibly
      ranked, correctly budgeted bundle (3999/4000 tokens; top files were
      `packer.py`, `routes.py`, `schemas.py`) in 0.4s — well under the 5s
      goal in §1. (Note: "the Tailr repo" in the original plan text was this
      repo itself, not a separate project.)

## 5. Phase 2 — Extension UI + Clipboard Flow (Week 2)

- [x] Vite + React 19 + TS + Tailwind v4 extension scaffold (MV3), in
      `extension/`: `vite.config.ts` builds `popup.html` to `dist/`,
      `public/manifest.json` copied through verbatim. No content script yet
      (Phase 0's spike files were removed — see ARCHI.md §4.1).
- [x] Popup UI (`extension/src/popup/`): `/status` check on mount,
      `RepoPicker` (select a previously-scanned repo or scan a new path),
      task textarea, `TokenBudgetPicker` (8k/32k/100k presets), "Pack
      Context" button.
- [x] Bundle preview (`BundlePreview.tsx`): ranked file list (path + token
      count), per-file checkbox toggle, live-updating total token count —
      verified exact (excluding a 528-token file dropped the total from
      8,076 to 7,548).
- [x] Copy-to-clipboard (`lib/bundle.ts` reassembles client-side from each
      file's `content`, matching `packer.py`'s `_assemble` format exactly)
      with "Copied!" feedback.
- [x] Empty/error states: server-down shows start instructions; zero
      repos shows just the scan input (no dropdown); `/pack` 404 (repo not
      scanned) surfaces the server's own error detail text.
- [x] **Milestone M2 — passed, verified for real (not just build success):**
      used Playwright to load the actual built `extension/dist/` into a real
      Chromium instance (`--load-extension`) against the real running
      server. Confirmed: popup renders, repo select + scan-new-path both
      work, Pack Context returns a sensibly ranked bundle, toggling a file
      off updates the live token count by exactly that file's token count,
      Copy to clipboard produces the correctly-reassembled bundle text
      (verified via `navigator.clipboard.readText()`), and the server-down
      state renders the right instructions. The one piece still needing a
      human: actually pasting the copied text into claude.ai (trivial once
      clipboard content is confirmed correct) — and content-script
      injection is Phase 3's job anyway.

## 6. Phase 3 — Page Injection + Polish (Week 3)

- [ ] Content script: detect claude.ai input box, "Inject" button in popup
      writes the bundle directly into it (user still presses send themselves —
      never auto-send).
- [ ] Handle claude.ai DOM changes defensively: feature-detect, fall back to
      clipboard with a clear message if injection fails.
- [ ] Re-scan / incremental update flow: "repo changed since last scan"
      indicator + one-click re-index.
- [ ] UI polish pass: loading states, keyboard shortcuts (Enter to pack),
      dark theme (naturally — black/gold optional but resist over-designing v1).
- [ ] Basic onboarding: first-run screen explaining the companion server,
      with copy-paste install command.
- [ ] **Milestone M3:** you use it for a real work session on a real client
      repo without touching curl or the file explorer.

## 7. Phase 4 — Dogfooding & Private Beta (Week 4)

- [ ] Daily personal use on at least 2 different repos; log every friction
      point in `FEEDBACK.md`.
- [ ] Fix the top 5 friction items — nothing else. Resist feature creep.
- [ ] Write README: what it does, 3-step install, one GIF of the flow.
- [ ] Package server for easy install (`pip install context-packer` or a
      simple install script).
- [ ] Share with 3–5 devs (team/colleagues); collect: did they get it running
      unaided? did they use it twice?
- [ ] **Milestone M4 / Go–No-Go:** if ≥3 testers use it more than once →
      plan v2. If not → diagnose (install friction? output quality? no real
      pain?) before writing more code.

## 8. v2 Candidates (do NOT start before M4 passes)

Ordered by likely value:
1. ChatGPT (chatgpt.com) injection support — doubles the audience.
2. Packaged binary for the companion server (no Python required).
3. Optional cloud embeddings (Anthropic/OpenAI) for better ranking quality.
4. Incremental/watch-mode indexing (re-embed only changed files).
5. Monorepo / multi-repo workspaces.
6. Chrome Web Store publication + landing page.

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| claude.ai DOM changes break injection | High over time | Clipboard is the always-working fallback; injection is enhancement, not core |
| Local embedding too slow on big repos | Medium | Spike 1 gate; cap indexed file count; incremental indexing in v2 |
| Companion-server install friction kills adoption | High for non-you users | v1 is for you; solve packaging (binary) only after M4 signal |
| MV3 restrictions on localhost fetch | Low | Spike 2 gate before any real build |
| Scope creep (multi-model, cloud sync, teams…) | High (self-inflicted) | Out-of-scope list in ARCHI.md §6 is binding; new ideas go to §8 here |
| Indexing secrets/.env by accident | Medium, high impact | Hard exclusion list in scanner from day 1; add tests for it |

## 10. Working Rhythm

- Each Claude Code session: read `CLAUDE.md` → `ARCHI.md` → this plan → pick
  the next unchecked box in the current phase.
- One phase at a time; don't open Phase N+1 tasks while Phase N milestone
  is unmet.
- End of each phase: update checkboxes here, note any architecture changes
  in ARCHI.md, commit both.
