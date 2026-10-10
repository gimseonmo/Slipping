#!/usr/bin/env bash
set -euo pipefail

pkill -f "uvicorn app.main:app" || true
pkill -f "powerpoint_monitor.py" || true
echo "Slipping 관련 백엔드와 에이전트 종료 요청을 보냈습니다."
