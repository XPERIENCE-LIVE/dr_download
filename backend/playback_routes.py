"""Authenticated-by-main playback API, with safe metadata and streamed media."""
import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, conint
from starlette.concurrency import run_in_threadpool

from .playback_service import PlaybackError, manager, start_playback

router = APIRouter()


class PlaybackRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    cookie_source: str = "none"
    max_height: conint(strict=True, ge=144, le=2160) = 1080


@router.post("/playback")
def create_playback(body: PlaybackRequest):
    try:
        return start_playback(body.url, body.cookie_source, body.max_height)
    except PlaybackError as error:
        raise HTTPException(error.status, detail=error.detail) from None


@router.get("/playback/{session_id}")
def playback_detail(session_id: UUID):
    try:
        return manager.describe(str(session_id))
    except PlaybackError as error:
        raise HTTPException(error.status, detail=error.detail) from None


@router.delete("/playback/{session_id}", status_code=204)
def stop_playback(session_id: UUID):
    manager.stop(str(session_id))
    return Response(status_code=204)


@router.get("/playback/{session_id}/stream")
async def playback_stream(session_id: UUID, start: str = Query("0", max_length=32), revision: int = Query(0, ge=0, le=2147483647)):
    # Query strings use a restricted decimal form, never NaN, infinity or exponent notation.
    import re
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", start):
        raise HTTPException(422, detail={"code": "invalid_start"})
    value = float(start)
    if not math.isfinite(value):
        raise HTTPException(422, detail={"code": "invalid_start"})
    try:
        generation = manager.reserve_stream(str(session_id), revision)
        session, process = await run_in_threadpool(manager.open_stream, str(session_id), value, generation)
    except PlaybackError as error:
        raise HTTPException(error.status, detail=error.detail) from None
    return StreamingResponse(manager.stream(session, process), media_type="video/mp4",
                             headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
