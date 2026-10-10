from __future__ import annotations

import json
import subprocess
from typing import Literal

SlideAction = Literal["next", "previous", "first"]


class PowerPointControlError(RuntimeError):
    pass


CONTROL_SCRIPT = r'''
const action = "%ACTION%";
const pp = Application("/Applications/Microsoft PowerPoint.app");

function reply(payload) {
  return JSON.stringify(payload);
}

if (!pp.running()) {
  reply({ ok: false, message: "PowerPoint가 실행 중이 아닙니다." });
} else {
  try {
    const presentations = pp.presentations();
    if (presentations.length === 0) {
      reply({ ok: false, message: "열려 있는 발표 자료가 없습니다." });
    } else {
      let handled = false;
      let errors = [];

      try {
        const presenterWindows = pp.presenterViewWindows();
        if (presenterWindows.length > 0 && action !== "first") {
          const tool = presenterWindows[0].presenterTool();
          if (action === "next") {
            pp.next(tool);
          } else {
            pp.previous(tool);
          }
          handled = true;
        }
      } catch (error) {
        errors.push("presenter view: " + String(error));
      }

      if (!handled) {
        try {
          const showWindows = pp.slideShowWindows();
          if (showWindows.length > 0) {
            const view = showWindows[0].slideshowView();
            if (action === "next") {
              pp.goToNextSlide(view);
            } else if (action === "previous") {
              pp.goToPreviousSlide(view);
            } else {
              pp.goToFirstSlide(view);
            }
            handled = true;
          }
        } catch (error) {
          errors.push("slide show window: " + String(error));
        }
      }

      if (!handled) {
        try {
          const activeDoc = pp.activePresentation();
          const view = activeDoc.slideShowWindow().slideshowView();
          if (action === "next") {
            pp.goToNextSlide(view);
          } else if (action === "previous") {
            pp.goToPreviousSlide(view);
          } else {
            pp.goToFirstSlide(view);
          }
          handled = true;
        } catch (error) {
          errors.push("active presentation show window: " + String(error));
        }
      }

      if (handled) {
        reply({ ok: true, message: action === "next" ? "다음 슬라이드로 이동했습니다." : action === "previous" ? "이전 슬라이드로 이동했습니다." : "첫 슬라이드로 이동했습니다." });
      } else {
        reply({
          ok: false,
          message: errors.length > 0
            ? "슬라이드쇼 제어 객체를 찾지 못했습니다: " + errors.join(" | ")
            : "슬라이드쇼가 시작되지 않았습니다."
        });
      }
    }
  } catch (error) {
    reply({ ok: false, message: String(error) });
  }
}
'''

KEYSTROKE_SCRIPT = r'''
const action = "%ACTION%";
const pp = Application("/Applications/Microsoft PowerPoint.app");
const systemEvents = Application("System Events");

function reply(payload) {
  return JSON.stringify(payload);
}

if (!pp.running()) {
  reply({ ok: false, message: "PowerPoint가 실행 중이 아닙니다." });
} else {
  try {
    pp.activate();
    delay(0.01);
    systemEvents.keyCode(action === "next" ? 124 : action === "previous" ? 123 : 115);
    reply({ ok: true, message: action === "next" ? "다음 슬라이드 명령을 보냈습니다." : action === "previous" ? "이전 슬라이드 명령을 보냈습니다." : "첫 슬라이드 명령을 보냈습니다." });
  } catch (error) {
    reply({ ok: false, message: String(error) });
  }
}
'''


def control_slideshow(action: SlideAction, prefer_keystroke: bool = True) -> str:
    errors: list[PowerPointControlError] = []
    scripts = (
        (KEYSTROKE_SCRIPT, CONTROL_SCRIPT)
        if prefer_keystroke
        else (CONTROL_SCRIPT, KEYSTROKE_SCRIPT)
    )
    for script_template in scripts:
        try:
            return _run_control_script(script_template.replace("%ACTION%", action))
        except PowerPointControlError as exc:
            errors.append(exc)

    detail = (
        "PowerPoint 제어에 실패했습니다. 빠른 제어를 위해 "
        "시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용에서 터미널 앱을 허용해 주세요."
    )
    if errors:
        detail = f"{detail} / 세부 오류: {' / '.join(str(error) for error in errors)}"
    raise PowerPointControlError(detail)


def control_slideshow_direct_first(action: SlideAction) -> str:
    try:
        return control_slideshow(action, prefer_keystroke=False)
    except PowerPointControlError as exc:
        raise exc


def _run_control_script(script: str) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
    except subprocess.TimeoutExpired as exc:
        raise PowerPointControlError("PowerPoint 자동화 응답 시간이 초과되었습니다.") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "PowerPoint 제어 오류").strip()
        raise PowerPointControlError(detail)

    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise PowerPointControlError("PowerPoint 제어 응답을 해석할 수 없습니다.") from exc

    if not payload.get("ok"):
        raise PowerPointControlError(payload.get("message") or "PowerPoint 제어에 실패했습니다.")
    return payload.get("message") or "PowerPoint 명령을 보냈습니다."
