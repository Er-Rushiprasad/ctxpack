from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    CheckResponse,
    PackedFileInfo,
    PackRequest,
    PackResponse,
    RepoInfo,
    ScanRequest,
    ScanResponse,
    StatusResponse,
)
from app.services.indexer import index_repo, list_repos, repo_needs_rescan
from app.services.packer import pack_chunks
from app.services.retriever import hybrid_search

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    return StatusResponse(status="ok", indexed_repos=[RepoInfo(**r) for r in list_repos()])


@router.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    try:
        result = index_repo(req.repo_path)
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ScanResponse(
        repo_id=result.repo_id,
        repo_path=result.repo_path,
        files_scanned=result.files_scanned,
        files_skipped=result.files_skipped,
        chunks_indexed=result.chunks_indexed,
    )


@router.get("/repos/{repo_id}/check", response_model=CheckResponse)
def check_repo(repo_id: str) -> CheckResponse:
    try:
        changed = repo_needs_rescan(repo_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CheckResponse(changed=changed)


@router.post("/pack", response_model=PackResponse)
def pack(req: PackRequest) -> PackResponse:
    search_result = hybrid_search(req.repo_id, req.task)
    if not search_result.chunks:
        raise HTTPException(
            status_code=404,
            detail=f"no indexed chunks for repo_id={req.repo_id!r} — scan it first via /scan",
        )

    result = pack_chunks(search_result.chunks, req.token_budget)
    return PackResponse(
        bundle=result.bundle,
        token_count=result.token_count,
        token_budget=req.token_budget,
        task=req.task,
        confidence=search_result.confidence,
        files=[
            PackedFileInfo(
                path=pf.path,
                chunk_count=len(pf.chunks),
                token_count=pf.token_count,
                relevance_score=pf.relevance_score,
                content=pf.content,
            )
            for pf in result.files
        ],
    )
