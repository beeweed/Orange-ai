"""HTTP API routes.

Exposes:
- GET  /api/health        : liveness probe
- GET  /api/ready         : readiness probe
- POST /api/models        : list provider models (validates the api key)
- POST /api/chat/stream   : run one autonomous agent turn (SSE stream)
- POST /api/sandbox/files : fetch the current sandbox file tree
- POST /api/sandbox/file  : read a single file's raw content (for the editor)
- POST /api/sandbox/kill  : terminate a sandbox
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.controllers.agent_controller import agent_controller
from src.schemas.chat import (
    ChatRequest,
    ModelsRequest,
    ModelsResponse,
    Provider,
)
from src.services.llm_service import LLMError, llm_service
from src.services.sandbox_service import SandboxError, sandbox_service
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api")
settings = get_settings()


@router.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@router.get("/ready")
async def ready() -> dict:
    """Readiness probe (process is up and able to serve requests)."""
    return {"status": "ready", "max_iterations": settings.max_iterations}


@router.post("/models", response_model=ModelsResponse)
async def list_models(req: ModelsRequest) -> ModelsResponse:
    """List available models for a provider after validating the API key."""
    try:
        models = await llm_service.list_models(req.provider, req.api_key)
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ModelsResponse(provider=req.provider, models=models)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Run one autonomous agent turn and stream events as SSE."""
    return StreamingResponse(
        agent_controller.stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering for real-time SSE
        },
    )


class SandboxFilesRequest(BaseModel):
    sandbox_id: str = Field(min_length=1)
    e2b_api_key: str = Field(min_length=1)
    root: str = "/home/user"


@router.post("/sandbox/files")
async def sandbox_files(req: SandboxFilesRequest) -> dict:
    """Return the current recursive file tree of a sandbox."""
    try:
        files = await sandbox_service.list_tree(req.sandbox_id, req.e2b_api_key, req.root)
    except SandboxError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"sandbox_id": req.sandbox_id, "files": files}


class SandboxFileRequest(BaseModel):
    sandbox_id: str = Field(min_length=1)
    e2b_api_key: str = Field(min_length=1)
    file_path: str = Field(min_length=1)


@router.post("/sandbox/file")
async def sandbox_file(req: SandboxFileRequest) -> dict:
    """Read a single file's raw content (used by the code editor panel)."""
    try:
        content = await sandbox_service.read_file(
            req.sandbox_id, req.e2b_api_key, req.file_path
        )
    except SandboxError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"file_path": req.file_path, "content": content}


class SandboxKillRequest(BaseModel):
    sandbox_id: str = Field(min_length=1)
    e2b_api_key: str = Field(min_length=1)


@router.post("/sandbox/kill")
async def sandbox_kill(req: SandboxKillRequest) -> dict:
    """Terminate a sandbox."""
    await sandbox_service.kill(req.sandbox_id, req.e2b_api_key)
    return {"status": "killed", "sandbox_id": req.sandbox_id}
