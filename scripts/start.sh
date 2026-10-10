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

"$(pick_python)" mac_agent/launcher.py "$@"
