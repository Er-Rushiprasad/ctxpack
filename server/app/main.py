from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Context Packer - Local Companion Server")

# Extension origin is a fixed chrome-extension:// id once loaded unpacked;
# update this once the extension has a stable id (Spike 2 uses a wildcard
# regex during dev since MV3 unpacked ids can change between reloads).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    repo_path: str


class PackRequest(BaseModel):
    task: str
    token_budget: Optional[int] = 8192


@app.get("/status")
async def status():
    return {"status": "ok", "indexed_repos": []}


@app.post("/scan")
async def scan(req: ScanRequest):
    # Placeholder: index the repo at `req.repo_path` in future work
    return {"status": "scanning", "repo_path": req.repo_path, "chunks_indexed": 0}


@app.post("/pack")
async def pack(req: PackRequest):
    # Placeholder: return an empty bundle; real packing will be implemented in Phase 1
    return {"bundle": "", "token_count": 0, "token_budget": req.token_budget, "task": req.task}
