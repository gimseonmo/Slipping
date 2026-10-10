from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.presentation import PresentationState


class PresentationStore:
    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or settings.state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.active_path = self.state_dir / "active_presentation.json"
        self._active: PresentationState | None = None
        self.load()

    @property
    def active(self) -> PresentationState | None:
        return self._active

    def load(self) -> PresentationState | None:
        if not self.active_path.exists():
            return None
        data = json.loads(self.active_path.read_text(encoding="utf-8"))
        self._active = PresentationState.model_validate(data)
        return self._active

    def set_active(self, presentation: PresentationState) -> PresentationState:
        self._active = presentation
        self.save()
        return presentation

    def save(self) -> None:
        if self._active is None:
            return
        self._active.updated_at = datetime.now(timezone.utc)
        self.active_path.write_text(
            self._active.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def update_current_slide(self, slide_number: int) -> PresentationState:
        if self._active is None:
            raise ValueError("활성 발표 자료가 없습니다.")
        if slide_number < 1 or slide_number > self._active.slide_count:
            raise ValueError(f"유효하지 않은 슬라이드 번호입니다: {slide_number}")
        self._active.current_slide = slide_number
        self._active.powerpoint_connected = True
        self._active.sync_message = "PowerPoint와 동기화됨"
        self.save()
        return self._active

    def update_note(self, slide_number: int, notes: str) -> PresentationState:
        if self._active is None:
            raise ValueError("활성 발표 자료가 없습니다.")
        slide = self._active.slide(slide_number)
        if slide is None:
            raise ValueError(f"{slide_number}번 슬라이드를 찾을 수 없습니다.")
        slide.edited_notes = notes
        self._active.sync_message = "노트 편집 내용 저장됨"
        self.save()
        return self._active

    def restore_note(self, slide_number: int) -> PresentationState:
        if self._active is None:
            raise ValueError("활성 발표 자료가 없습니다.")
        slide = self._active.slide(slide_number)
        if slide is None:
            raise ValueError(f"{slide_number}번 슬라이드를 찾을 수 없습니다.")
        slide.edited_notes = None
        self._active.sync_message = "원본 발표자 노트로 복원됨"
        self.save()
        return self._active

    def mark_powerpoint_status(self, connected: bool, state: str, message: str) -> PresentationState | None:
        if self._active is None:
            return None
        self._active.powerpoint_connected = connected
        self._active.slideshow_state = state
        self._active.sync_message = message
        self.save()
        return self._active


store = PresentationStore()
