from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models.messages import AgentCommandPoll, AgentStateUpdate, NoteEditRequest, WebSocketMessage
from app.services.agent_commands import agent_command_bus
from app.services.powerpoint_control import PowerPointControlError, SlideAction, control_slideshow
from app.services.pptx_parser import PptxParseError, parse_pptx
from app.services.presentation_store import store
from app.websocket.manager import manager

router = APIRouter(prefix="/api")


@router.get("/status")
async def status() -> dict:
    active = store.active
    return {
        "appName": settings.app_name,
        "hasPresentation": active is not None,
        "presentation": active.to_client() if active else None,
        "sessionToken": settings.session_token,
    }


@router.get("/presentations/current")
async def current_presentation() -> dict:
    active = store.active
    if active is None:
        raise HTTPException(status_code=404, detail="불러온 발표 자료가 없습니다.")
    return active.to_client()


@router.post("/slideshow/{action}")
async def control_powerpoint_slideshow(action: SlideAction) -> dict:
    if agent_command_bus.has_recent_agent():
        await agent_command_bus.enqueue(action)
        message = _slide_action_message(action)
    else:
        try:
            message = control_slideshow(action)
        except PowerPointControlError as exc:
            message = str(exc)
            await manager.broadcast(WebSocketMessage(type="error", payload={"message": message}))
            return {"ok": False, "message": message}

    active = store.active
    if active:
        if action == "first":
            target_slide = 1
        else:
            target_slide = active.current_slide + (1 if action == "next" else -1)
        target_slide = max(1, min(active.slide_count, target_slide))
        if target_slide != active.current_slide:
            active = store.update_current_slide(target_slide)
        active.sync_message = message
        active.powerpoint_connected = True
        store.save()
        await manager.broadcast(WebSocketMessage(type="slide_changed", payload=active.to_client()))
        return {"ok": True, "message": message, "presentation": active.to_client()}
    return {"ok": True, "message": message, "presentation": None}


@router.post("/agent/commands/poll")
async def poll_agent_command(request: AgentCommandPoll) -> dict:
    if request.token != settings.session_token:
        raise HTTPException(status_code=403, detail="에이전트 토큰이 올바르지 않습니다.")
    action = await agent_command_bus.poll()
    return {"action": action}


def _slide_action_message(action: SlideAction) -> str:
    if action == "next":
        return "다음 슬라이드"
    if action == "previous":
        return "이전 슬라이드"
    return "첫 슬라이드"


@router.post("/presentations/upload")
async def upload_presentation(file: UploadFile = File(...)) -> dict:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="PPTX 파일만 업로드할 수 있습니다.")

    destination = settings.uploads_dir / filename
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="업로드 파일이 너무 큽니다.")
            output.write(chunk)

    try:
        presentation = parse_pptx(destination)
    except PptxParseError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored_copy = settings.uploads_dir / f"{presentation.presentation_id}.pptx"
    if destination != stored_copy:
        shutil.copy2(destination, stored_copy)
        destination.unlink(missing_ok=True)
        presentation.source_path = str(stored_copy)

    store.set_active(presentation)
    await manager.broadcast(WebSocketMessage(type="presentation_changed", payload=presentation.to_client()))
    return presentation.to_client()


@router.patch("/notes/{slide_number}")
async def edit_note(slide_number: int, request: NoteEditRequest) -> dict:
    try:
        presentation = store.update_note(slide_number, request.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await manager.broadcast(WebSocketMessage(type="notes_updated", payload=presentation.to_client()))
    return presentation.to_client()


@router.post("/notes/{slide_number}/restore")
async def restore_note(slide_number: int) -> dict:
    try:
        presentation = store.restore_note(slide_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await manager.broadcast(WebSocketMessage(type="notes_updated", payload=presentation.to_client()))
    return presentation.to_client()


@router.post("/agent/state")
async def update_agent_state(update: AgentStateUpdate) -> dict:
    if update.token != settings.session_token:
        raise HTTPException(status_code=403, detail="에이전트 토큰이 올바르지 않습니다.")

    active = store.active
    if not update.powerpoint_running:
        presentation = store.mark_powerpoint_status(False, "waiting", "PowerPoint 실행 대기 중")
        if presentation:
            await manager.broadcast(WebSocketMessage(type="presentation_disconnected", payload=presentation.to_client()))
        return {"ok": True}

    if active is None:
        return {"ok": True, "message": "발표 자료가 아직 업로드되지 않았습니다."}

    if update.slide_number is not None:
        try:
            active = store.update_current_slide(update.slide_number)
            active.slideshow_state = update.slideshow_state
            active.sync_message = update.message or "PowerPoint와 동기화됨"
            store.save()
            await manager.broadcast(WebSocketMessage(type="slide_changed", payload=active.to_client()))
        except ValueError as exc:
            await manager.broadcast(WebSocketMessage(type="error", payload={"message": str(exc)}))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        active = store.mark_powerpoint_status(True, update.slideshow_state, update.message or "슬라이드쇼 대기 중")
        if active:
            await manager.broadcast(WebSocketMessage(type="synchronization_status", payload=active.to_client()))

    return {"ok": True}
