from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SlideNotes(BaseModel):
    slide_number: int
    title: str = ""
    slide_text: str = ""
    imported_notes: str = ""
    edited_notes: str | None = None

    @property
    def effective_notes(self) -> str:
        return self.edited_notes if self.edited_notes is not None else self.imported_notes


class PresentationState(BaseModel):
    presentation_id: str
    title: str
    source_filename: str
    source_path: str | None = None
    slide_count: int
    slides: list[SlideNotes]
    current_slide: int = 1
    powerpoint_connected: bool = False
    slideshow_state: str = "waiting"
    sync_message: str = "PowerPoint 대기 중"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def slide(self, slide_number: int) -> SlideNotes | None:
        for slide in self.slides:
            if slide.slide_number == slide_number:
                return slide
        return None

    def to_client(self) -> dict:
        return {
            "presentationId": self.presentation_id,
            "title": self.title,
            "sourceFilename": self.source_filename,
            "slideCount": self.slide_count,
            "currentSlide": self.current_slide,
            "powerpointConnected": self.powerpoint_connected,
            "slideshowState": self.slideshow_state,
            "syncMessage": self.sync_message,
            "slides": [
                {
                    "slideNumber": slide.slide_number,
                    "title": slide.title,
                    "slideText": slide.slide_text,
                    "importedNotes": slide.imported_notes,
                    "editedNotes": slide.edited_notes,
                    "notes": slide.effective_notes,
                }
                for slide in self.slides
            ],
        }
