# Slipping

`Slipping`은 MacBook의 Microsoft PowerPoint 슬라이드쇼와 iPad Safari의 발표자 노트를 로컬 Wi-Fi에서 동기화하는 웹 기반 발표 보조 시스템입니다.

## 구성

- `backend`: FastAPI 서버, PPTX 업로드, 발표자 노트 추출, WebSocket 동기화
- `mac_agent`: macOS PowerPoint AppleScript 감시 에이전트
- `frontend`: React + TypeScript iPad 웹 앱
- `scripts`: 설치, 시작, 종료 스크립트
- `docs`: 설치와 검증 문서

## 빠른 시작

```bash
./scripts/setup.sh
./scripts/start.sh
```

실행 후 터미널에 표시되는 로컬 네트워크 주소 또는 QR 코드를 iPad Safari에서 엽니다. PPTX 파일을 업로드하면 발표자 노트가 표시되고, Mac의 PowerPoint 슬라이드쇼가 시작되면 현재 슬라이드에 맞춰 자동 갱신됩니다.

iPad의 노트 화면에서 왼쪽으로 크게 쓸면 다음 슬라이드, 오른쪽으로 크게 쓸면 이전 슬라이드 명령이 Mac의 PowerPoint로 전송됩니다. 노트 편집 중에는 오작동을 막기 위해 스와이프 제어가 꺼집니다.

프론트엔드 개발 서버를 별도로 띄울 때는 다음을 사용합니다.

```bash
cd frontend
npm run dev
```

## 현재 검증 상태

이 저장소에서 PowerPoint AppleScript 사전을 확인했고, 현재 설치된 PowerPoint가 `slide show window`, `slideshow view`, `current slide in show`, `slide index` 속성을 노출하는 것을 확인했습니다. 다만 이 Codex 실행 환경에서는 프로세스 목록과 macOS 자동화 호출이 샌드박스 제한으로 차단되어 실제 슬라이드쇼 런타임 동작은 아직 수동 검증이 필요합니다.

검증 절차는 [docs/TESTING.md](docs/TESTING.md)를 확인하세요.

## 보안

기본 용도는 신뢰할 수 있는 로컬 네트워크입니다. 서버는 공개 인터넷에 노출하지 않는 것을 전제로 하며, PowerPoint 에이전트는 실행 시 생성되는 세션 토큰으로 백엔드에 상태를 보고합니다. 업로드한 PPTX와 편집 노트는 기본적으로 로컬 `data` 디렉터리에만 저장됩니다.
