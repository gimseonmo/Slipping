from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass
class PowerPointSnapshot:
    powerpoint_running: bool
    presentation_title: str | None = None
    presentation_path: str | None = None
    slide_number: int | None = None
    total_slides: int | None = None
    slideshow_state: str = "unknown"
    message: str | None = None

    def to_payload(self, token: str) -> dict:
        return {
            "token": token,
            "powerpoint_running": self.powerpoint_running,
            "presentation_title": self.presentation_title,
            "presentation_path": self.presentation_path,
            "slide_number": self.slide_number,
            "total_slides": self.total_slides,
            "slideshow_state": self.slideshow_state,
            "message": self.message,
        }


class PowerPointAutomation:
    """Small AppleScript bridge for Microsoft PowerPoint on macOS."""

    STATUS_SCRIPT = r'''
const pp = Application("/Applications/Microsoft PowerPoint.app");

function reply(payload) {
  return JSON.stringify(payload);
}

if (!pp.running()) {
  reply({
    powerpoint_running: false,
    slideshow_state: "waiting",
    message: "PowerPoint 실행 대기 중"
  });
} else {
  try {
    const presentations = pp.presentations();
    if (presentations.length === 0) {
      reply({
        powerpoint_running: true,
        slideshow_state: "no_presentation",
        message: "열려 있는 발표 자료가 없습니다"
      });
    } else {
      const activeDoc = pp.activePresentation();
      let docPath = "";
      try { docPath = activeDoc.fullName(); } catch (_) {}
      const totalSlides = activeDoc.slides().length;
      let slideNumber = null;

      try {
        const presenterWindows = pp.presenterViewWindows();
        if (presenterWindows.length > 0) {
          slideNumber = presenterWindows[0].presenterTool().currentSlideInShow();
        }
      } catch (_) {}

      try {
        if (slideNumber === null) {
          const showWindows = pp.slideShowWindows();
          if (showWindows.length > 0) {
            slideNumber = showWindows[0].slideshowView().slide().slideIndex();
          }
        }
      } catch (_) {}

      if (slideNumber === null) {
        reply({
          powerpoint_running: true,
          presentation_title: activeDoc.name(),
          presentation_path: docPath,
          total_slides: totalSlides,
          slideshow_state: "not_started",
          message: "슬라이드쇼 시작 대기 중"
        });
      } else {
        reply({
          powerpoint_running: true,
          presentation_title: activeDoc.name(),
          presentation_path: docPath,
          slide_number: slideNumber,
          total_slides: totalSlides,
          slideshow_state: "running",
          message: "PowerPoint와 동기화됨"
        });
      }
    }
  } catch (error) {
    reply({
      powerpoint_running: true,
      slideshow_state: "permission_error",
      message: String(error)
    });
  }
}
'''

    def snapshot(self) -> PowerPointSnapshot:
        try:
            result = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", self.STATUS_SCRIPT],
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except subprocess.TimeoutExpired:
            return PowerPointSnapshot(False, slideshow_state="error", message="PowerPoint 자동화 응답 시간이 초과되었습니다.")

        if result.returncode != 0:
            return PowerPointSnapshot(
                False,
                slideshow_state="permission_error",
                message=(result.stderr or result.stdout or "PowerPoint 자동화 오류").strip(),
            )

        try:
            data = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return PowerPointSnapshot(False, slideshow_state="error", message="PowerPoint 응답을 해석할 수 없습니다.")

        return PowerPointSnapshot(
            powerpoint_running=bool(data.get("powerpoint_running")),
            presentation_title=data.get("presentation_title"),
            presentation_path=data.get("presentation_path"),
            slide_number=_to_int(data.get("slide_number")),
            total_slides=_to_int(data.get("total_slides")),
            slideshow_state=data.get("slideshow_state", "unknown"),
            message=data.get("message"),
        )


def _to_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except ValueError:
        return None
