from __future__ import annotations

import json
from fastapi import WebSocket

from app.models.messages import WebSocketMessage


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def send(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        await websocket.send_text(message.model_dump_json())

    async def broadcast(self, message: WebSocketMessage) -> None:
        disconnected: list[WebSocket] = []
        payload = message.model_dump_json()
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)

    @staticmethod
    def parse(text: str) -> dict:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("WebSocket 메시지는 JSON 객체여야 합니다.")
        return data


manager = ConnectionManager()
