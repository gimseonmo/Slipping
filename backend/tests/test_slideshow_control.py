from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.models.presentation import PresentationState, SlideNotes
from app.services.agent_commands import agent_command_bus
from app.services.powerpoint_control import PowerPointControlError
from app.services.presentation_store import store


def test_slideshow_control_endpoint_sends_command(monkeypatch, tmp_path):
    calls: list[str] = []
    previous_state_dir = store.state_dir
    previous_active_path = store.active_path
    previous_active = store.active
    store.state_dir = tmp_path
    store.active_path = tmp_path / "active_presentation.json"
    store.set_active(
        PresentationState(
            presentation_id="control",
            title="제어",
            source_filename="control.pptx",
            slide_count=2,
            slides=[
                SlideNotes(slide_number=1, imported_notes="1"),
                SlideNotes(slide_number=2, imported_notes="2"),
            ],
        )
    )

    def fake_control(action: str) -> str:
        calls.append(action)
        return "명령 전송됨"

    monkeypatch.setattr(routes, "control_slideshow", fake_control)

    try:
        client = TestClient(app)
        response = client.post("/api/slideshow/next")
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["presentation"]["currentSlide"] == 2
        assert calls == ["next"]
        assert store.active is not None
        assert store.active.current_slide == 2
        assert store.active.sync_message == "명령 전송됨"
    finally:
        store.state_dir = previous_state_dir
        store.active_path = previous_active_path
        store._active = previous_active


def test_slideshow_control_failure_returns_json_without_http_400(monkeypatch):
    def fake_control(action: str) -> str:
        raise PowerPointControlError("PowerPoint 제어 실패")

    monkeypatch.setattr(routes, "control_slideshow", fake_control)

    client = TestClient(app)
    response = client.post("/api/slideshow/previous")
    assert response.status_code == 200
    assert response.json() == {"ok": False, "message": "PowerPoint 제어 실패"}


def test_slideshow_control_first_resets_current_slide(monkeypatch, tmp_path):
    previous_state_dir = store.state_dir
    previous_active_path = store.active_path
    previous_active = store.active
    store.state_dir = tmp_path
    store.active_path = tmp_path / "active_presentation.json"
    store.set_active(
        PresentationState(
            presentation_id="reset",
            title="초기화",
            source_filename="reset.pptx",
            slide_count=3,
            current_slide=3,
            slides=[
                SlideNotes(slide_number=1, imported_notes="1"),
                SlideNotes(slide_number=2, imported_notes="2"),
                SlideNotes(slide_number=3, imported_notes="3"),
            ],
        )
    )

    monkeypatch.setattr(routes, "control_slideshow", lambda action: "첫 슬라이드")

    try:
        client = TestClient(app)
        response = client.post("/api/slideshow/first")
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["presentation"]["currentSlide"] == 1
        assert store.active is not None
        assert store.active.current_slide == 1
    finally:
        store.state_dir = previous_state_dir
        store.active_path = previous_active_path
        store._active = previous_active


def test_slideshow_control_queues_command_when_agent_is_connected(monkeypatch, tmp_path):
    queued: list[str] = []
    previous_state_dir = store.state_dir
    previous_active_path = store.active_path
    previous_active = store.active
    store.state_dir = tmp_path
    store.active_path = tmp_path / "active_presentation.json"
    store.set_active(
        PresentationState(
            presentation_id="agent",
            title="에이전트",
            source_filename="agent.pptx",
            slide_count=2,
            slides=[
                SlideNotes(slide_number=1, imported_notes="1"),
                SlideNotes(slide_number=2, imported_notes="2"),
            ],
        )
    )

    async def fake_enqueue(action: str) -> None:
        queued.append(action)

    monkeypatch.setattr(agent_command_bus, "has_recent_agent", lambda: True)
    monkeypatch.setattr(agent_command_bus, "enqueue", fake_enqueue)
    monkeypatch.setattr(routes, "control_slideshow", lambda action: (_ for _ in ()).throw(AssertionError("direct control should not run")))

    try:
        client = TestClient(app)
        response = client.post("/api/slideshow/next")
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["presentation"]["currentSlide"] == 2
        assert queued == ["next"]
    finally:
        store.state_dir = previous_state_dir
        store.active_path = previous_active_path
        store._active = previous_active
