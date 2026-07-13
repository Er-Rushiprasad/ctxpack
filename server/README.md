# Context Packer — Local Companion Server (dev)

Managed with [uv](https://docs.astral.sh/uv/). Python 3.13 (see `.python-version`).

## Spikes

`scripts/spike_embeddings.py` — Phase 0 Spike 1, measures local embedding
speed/RAM (`uv run python scripts/spike_embeddings.py`). Results recorded in
`../PLAN.md` and `../ARCHI.md`.

```bash
cd server
uv sync                     # install deps into server/.venv
uv run uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

Add a new dependency with `uv add <package>` (run from this `server/` folder,
never from the repo root — this project's tooling is independent of
`extension/`, per ARCHI.md §8).

This is a minimal skeleton for Phase 0/1 development.
