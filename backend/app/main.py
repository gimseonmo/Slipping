from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.models.messages import WebSocketMessage
from app.services.presentation_store import store
from app.websocket.manager import manager

app = FastAPI(title="Slipping", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        active = store.active
        await manager.send(
            websocket,
            WebSocketMessage(
                type="presentation_connected" if active else "synchronization_status",
                payload=active.to_client() if active else {"message": "발표 자료 업로드 대기 중"},
            ),
        )
        while True:
            text = await websocket.receive_text()
            try:
                data = manager.parse(text)
                if data.get("type") == "ping":
                    await manager.send(websocket, WebSocketMessage(type="synchronization_status", payload={"message": "연결됨"}))
                else:
                    await manager.send(websocket, WebSocketMessage(type="error", payload={"message": "지원하지 않는 메시지입니다."}))
            except Exception as exc:
                await manager.send(websocket, WebSocketMessage(type="error", payload={"message": str(exc)}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


dist_dir = settings.frontend_dist.resolve()
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")


@app.get("/{path:path}")
async def spa(path: str):
    index = dist_dir / "index.html"
    requested = dist_dir / path
    if path and requested.exists() and requested.is_file():
        return FileResponse(requested)
    if index.exists():
        return FileResponse(index)
    return {
        "app": "Slipping",
        "message": "프론트엔드 빌드가 없습니다. 개발 중에는 frontend에서 npm run dev를 실행하세요.",
    }
