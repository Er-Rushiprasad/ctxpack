extension

Chrome extension (MV3): React 19 + TypeScript + Tailwind v4, bundled with Vite.

## Build & load

```bash
cd extension
npm install
npm run build       # outputs to dist/
```

Then in Chrome: `chrome://extensions` → enable "Developer mode" → "Load
unpacked" → select `extension/dist/` (not `extension/` itself — the built
output, including `manifest.json`, lives in `dist/`).

`npm run dev` rebuilds on file changes (`vite build --watch`); reload the
extension in `chrome://extensions` after each rebuild to pick up changes —
there's no live-reload for MV3 popups in this setup.

## What's here (Phase 2)

- Popup UI (`src/popup/`): checks `/status`, lets you scan a new repo path or
  pick a previously-scanned one, enter a task description, choose a token
  budget preset, and pack. The bundle preview lists ranked files with a
  live-updating token count as you toggle files in/out, then copies the
  assembled bundle to the clipboard.
- `src/lib/api.ts` — fetch wrapper for the local server (`127.0.0.1:8000`).
- `src/lib/bundle.ts` — reassembles the bundle client-side from the
  per-file `content` the server returns, so toggling files doesn't need a
  round trip to `/pack`. Must stay in sync with
  `server/app/services/packer.py`'s `_assemble` format if that ever changes.

Content-script injection into claude.ai (Phase 3) isn't wired up yet — the
Phase 0 spike for it was removed when this real scaffold replaced the flat
`manifest.json`/`popup.html`/`popup.js` files; the working selector
(`div[contenteditable="true"].ProseMirror`) is still noted in `ARCHI.md` for
when Phase 3 rebuilds it properly.

## Manual check (can't be automated from here)

With the server running (`cd ../server && uv run uvicorn app.main:app --port
8000`), open the popup, scan a real repo path, type a task, pick a budget,
and confirm Pack Context returns a sensible ranked list and Copy to
clipboard actually copies.
