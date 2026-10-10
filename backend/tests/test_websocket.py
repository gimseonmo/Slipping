from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.messages import WebSocketMessage
from app.models.presentation import PresentationState, SlideNotes
from app.services.presentation_store import store


@pytest.fixture(autouse=True)
def isolate_store(tmp_path):
    previous_state_dir = store.state_dir
    previous_active_path = store.active_path
    previous_active = store.active
    store.state_dir = tmp_path
    store.active_path = tmp_path / "active_presentation.json"
    store._active = None
    yield
    store.state_dir = previous_state_dir
    store.active_path = previous_active_path
    store._active = previous_active


def test_websocket_sends_current_presentation_on_connect():
    store.set_active(
        PresentationState(
            presentation_id="ws",
            title="웹소켓",
            source_filename="ws.pptx",
            slide_count=1,
            slides=[SlideNotes(slide_number=1, imported_notes="노트")],
        )
    )

    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "presentation_connected"
        assert message["payload"]["title"] == "웹소켓"


def test_websocket_rejects_unknown_messages():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "unknown"})
        message = websocket.receive_json()
        assert message["type"] == "error"
