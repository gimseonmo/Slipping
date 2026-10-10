#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_python() {
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)' >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  echo "Python 3.11, 3.12, 3.13 중 하나가 필요합니다." >&2
  return 1
}

PYTHON_BIN="$(pick_python)"
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)' >/dev/null 2>&1; then
  "$PYTHON_BIN" -m venv --clear .venv
else
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt

if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm install)
fi

echo "설치가 완료되었습니다. scripts/start.sh 로 실행하세요."
