extension

Phase 0 Spike 2 only: a bare (no build step) MV3 extension that pings the
local companion server, to confirm `fetch()` from an extension context can
reach `127.0.0.1` without MV3/CORS blocking it. The real Vite + React + TS
scaffold replaces these files in Phase 2.

## Try it

1. Start the server (see `../server/README.md`).
2. Open `chrome://extensions`, enable "Developer mode".
3. "Load unpacked" → select this `extension/` folder.
4. Click the extension icon → "Ping local server" → should show
   `{"status": "ok", "indexed_repos": []}`.

If the fetch fails with a CORS error, check `server/app/main.py`'s
`CORSMiddleware` config and that the server is actually running on port 8000.

## Spike 3 — claude.ai injection

`content_spike.js` is loaded on any `https://claude.ai/*` page (after
reloading the extension in `chrome://extensions`, refresh the claude.ai tab
too). Open devtools console on a claude.ai chat page and run:

```js
contextPackerSpike()
```

It should type "hello world" into the message composer. The selector list is
a best guess (`div[contenteditable="true"].ProseMirror`) — if it doesn't
find the box, inspect the composer element and update
`findClaudeInput()` in `content_spike.js`, then note the real selector back
in `ARCHI.md`.
