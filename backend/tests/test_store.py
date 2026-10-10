from __future__ import annotations

from app.models.presentation import PresentationState, SlideNotes
from app.services.presentation_store import PresentationStore


def sample_state() -> PresentationState:
    return PresentationState(
        presentation_id="abc",
        title="테스트",
        source_filename="test.pptx",
        slide_count=2,
        slides=[
            SlideNotes(slide_number=1, imported_notes="원본 1"),
            SlideNotes(slide_number=2, imported_notes="원본 2"),
        ],
    )


def test_note_edit_and_restore_are_persisted(tmp_path):
    store = PresentationStore(tmp_path)
    store.set_active(sample_state())

    store.update_note(1, "편집 노트")
    assert store.active is not None
    assert store.active.slide(1).effective_notes == "편집 노트"

    reloaded = PresentationStore(tmp_path)
    assert reloaded.active is not None
    assert reloaded.active.slide(1).effective_notes == "편집 노트"

    reloaded.restore_note(1)
    assert reloaded.active.slide(1).effective_notes == "원본 1"


def test_invalid_slide_number_is_rejected(tmp_path):
    store = PresentationStore(tmp_path)
    store.set_active(sample_state())

    try:
        store.update_current_slide(99)
    except ValueError as exc:
        assert "유효하지 않은" in str(exc)
    else:
        raise AssertionError("invalid slide number was accepted")
