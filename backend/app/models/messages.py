from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

MessageType = Literal[
    "presentation_connected",
    "presentation_disconnected",
    "presentation_changed",
    "slide_changed",
    "notes_updated",
    "synchronization_status",
    "error",
]


class WebSocketMessage(BaseModel):
    type: MessageType
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentStateUpdate(BaseModel):
    token: str | None = None
    powerpoint_running: bool = False
    presentation_path: str | None = None
    presentation_title: str | None = None
    slide_number: int | None = None
    total_slides: int | None = None
    slideshow_state: str = "unknown"
    message: str | None = None


class AgentCommandPoll(BaseModel):
    token: str


class NoteEditRequest(BaseModel):
    notes: str = ""
