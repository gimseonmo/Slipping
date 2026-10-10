from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.request

from powerpoint_automation import PowerPointAutomation, PowerPointSnapshot
from app.services.powerpoint_control import PowerPointControlError, control_slideshow


def post_state(server_url: str, snapshot: PowerPointSnapshot, token: str) -> None:
    payload = json.dumps(snapshot.to_payload(token)).encode("utf-8")
    request = urllib.request.Request(
        f"{server_url.rstrip('/')}/api/agent/state",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        response.read()


def poll_command(server_url: str, token: str) -> str | None:
    payload = json.dumps({"token": token}).encode("utf-8")
    request = urllib.request.Request(
        f"{server_url.rstrip('/')}/api/agent/commands/poll",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))
    action = data.get("action")
    return action if action in {"next", "previous", "first"} else None


def command_worker(server_url: str, token: str) -> None:
    automation = PowerPointAutomation()
    while True:
        try:
            action = poll_command(server_url, token)
            if not action:
                continue
            control_slideshow(action)
            snapshot = automation.snapshot()
            post_state(server_url, snapshot, token)
            print(f"[agent] 명령 처리: {action}", flush=True)
        except PowerPointControlError as exc:
            print(f"[agent] PowerPoint 제어 실패: {exc}", flush=True)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"[agent] 명령 채널 연결 실패: {exc}", flush=True)
            time.sleep(0.5)


def monitor(server_url: str, token: str, interval: float) -> None:
    automation = PowerPointAutomation()
    threading.Thread(target=command_worker, args=(server_url, token), daemon=True).start()
    last_signature: tuple | None = None
    while True:
        snapshot = automation.snapshot()
        signature = (
            snapshot.powerpoint_running,
            snapshot.presentation_path,
            snapshot.slide_number,
            snapshot.total_slides,
            snapshot.slideshow_state,
            snapshot.message,
        )
        if signature != last_signature:
            try:
                post_state(server_url, snapshot, token)
                last_signature = signature
                status = snapshot.message or snapshot.slideshow_state
                print(f"[agent] {status}", flush=True)
            except (urllib.error.URLError, TimeoutError) as exc:
                print(f"[agent] 서버 연결 실패: {exc}", flush=True)
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Slipping PowerPoint 동기화 에이전트")
    parser.add_argument("--server", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--interval", type=float, default=0.4)
    args = parser.parse_args()
    monitor(args.server, args.token, args.interval)


if __name__ == "__main__":
    main()
