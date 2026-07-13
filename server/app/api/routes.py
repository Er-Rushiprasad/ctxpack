from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    PackedFileInfo,
    PackRequest,
    PackResponse,
    RepoInfo,
    ScanRequest,
    ScanResponse,
    StatusResponse,
)
from app.services.indexer import index_repo, list_repos
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


@router.post("/pack", response_model=PackResponse)
def pack(req: PackRequest) -> PackResponse:
    ranked_chunks = hybrid_search(req.repo_id, req.task)
    if not ranked_chunks:
        raise HTTPException(
            status_code=404,
            detail=f"no indexed chunks for repo_id={req.repo_id!r} — scan it first via /scan",
        )

    result = pack_chunks(ranked_chunks, req.token_budget)
    return PackResponse(
        bundle=result.bundle,
        token_count=result.token_count,
        token_budget=req.token_budget,
        task=req.task,
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
