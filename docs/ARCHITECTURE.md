# 아키텍처

## 전체 흐름

1. MacBook에서 `scripts/start.sh`를 실행합니다.
2. FastAPI 백엔드가 PPTX 업로드, 상태 저장, WebSocket 브로드캐스트를 담당합니다.
3. macOS PowerPoint 에이전트가 AppleScript로 현재 슬라이드 상태를 읽습니다.
4. 에이전트가 `/api/agent/state`로 현재 슬라이드 번호를 보고합니다.
5. 백엔드는 연결된 iPad Safari 클라이언트에 `slide_changed` 메시지를 보냅니다.
6. React 앱은 현재 슬라이드의 발표자 노트를 표시합니다.

## WebSocket 메시지

서버는 다음 타입을 사용합니다.

- `presentation_connected`
- `presentation_disconnected`
- `presentation_changed`
- `slide_changed`
- `notes_updated`
- `synchronization_status`
- `error`

메시지는 모두 다음 형태입니다.

```json
{
  "type": "slide_changed",
  "payload": {}
}
```

## PPTX 파싱

슬라이드 텍스트와 기본 슬라이드 구조는 `python-pptx`로 읽습니다. 발표자 노트는 `python-pptx`의 공개 API만으로 안정적으로 접근하기 어려운 경우가 있어, PPTX 패키지 내부의 slide relationship XML을 따라 `notesSlide` 문서를 찾고 XML 파서로 본문 placeholder를 추출합니다.

원본 PPTX는 수정하지 않습니다. 웹에서 편집한 노트는 `data/state/active_presentation.json`에 별도로 저장됩니다.

## PowerPoint 연동

현재 설치된 PowerPoint AppleScript 사전에서 다음 속성이 확인되었습니다.

- `slide show window`
- `slideshow view`
- `current slide in show`
- `slide`
- `slide index`

에이전트는 `current slide in show`를 먼저 읽고, 실패하면 `slideshow view`의 현재 `slide index`를 읽습니다. 이 방식은 화면 캡처나 OCR을 사용하지 않으며 PowerPoint 조작을 방해하지 않습니다.

## 제한

AppleScript 이벤트 기반 슬라이드 변경 콜백이 확인되지 않아 에이전트는 짧은 간격으로 상태를 비교합니다. 중복 상태는 백엔드로 반복 전송하지 않습니다.
