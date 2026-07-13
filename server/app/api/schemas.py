from pydantic import BaseModel

from app.core.config import DEFAULT_TOKEN_BUDGET


class ScanRequest(BaseModel):
    repo_path: str


class ScanResponse(BaseModel):
    repo_id: str
    repo_path: str
    files_scanned: int
    files_skipped: int
    chunks_indexed: int


class RepoInfo(BaseModel):
    repo_id: str
    repo_path: str
    last_scanned_at: str
    file_count: int
    chunk_count: int


class StatusResponse(BaseModel):
    status: str
    indexed_repos: list[RepoInfo]


class PackRequest(BaseModel):
    repo_id: str
    task: str
    token_budget: int = DEFAULT_TOKEN_BUDGET


class PackedFileInfo(BaseModel):
    path: str
    chunk_count: int
    token_count: int
    relevance_score: float


class PackResponse(BaseModel):
    bundle: str
    token_count: int
    token_budget: int
    task: str
    files: list[PackedFileInfo]
