from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VENV = ROOT / ".venv"


def local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def ensure_venv() -> Path:
    python = VENV / "bin" / "python"
    needs_create = not python.exists()
    if python.exists():
        version_check = subprocess.run(
            [
                str(python),
                "-c",
                "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)",
            ],
            check=False,
        )
        needs_create = version_check.returncode != 0
    if needs_create:
        args = [sys.executable, "-m", "venv"]
        if VENV.exists():
            args.append("--clear")
        args.append(str(VENV))
        subprocess.check_call(args)
    subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])
    return python


def read_status(url: str) -> dict:
    with urllib.request.urlopen(f"{url}/api/status", timeout=8) as response:
        import json

        return json.loads(response.read().decode("utf-8"))


def print_qr(url: str) -> None:
    print(f"\n아이패드에서 열 주소: {url}\n", flush=True)
    try:
        import qrcode
    except Exception:
        print("QR 코드를 보려면 qrcode 패키지 설치가 필요합니다.", flush=True)
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Slipping 실행기")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-agent", action="store_true")
    args = parser.parse_args()

    python = ensure_venv()
    if Path(sys.prefix).resolve() != VENV.resolve():
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    backend_cmd = [
        str(python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    backend = subprocess.Popen(backend_cmd, cwd=str(BACKEND), env=env)
    server_url = f"http://127.0.0.1:{args.port}"

    status = None
    for _ in range(40):
        try:
            status = read_status(server_url)
            break
        except Exception:
            time.sleep(0.25)
    if status is None:
        backend.terminate()
        raise SystemExit("백엔드 시작에 실패했습니다.")

    network_url = f"http://{local_ip()}:{args.port}"
    print_qr(network_url)
    print("종료하려면 Ctrl+C를 누르세요.\n", flush=True)

    agent = None
    if not args.no_agent:
        token = status["sessionToken"]
        agent = subprocess.Popen(
            [
                str(python),
                str(ROOT / "mac_agent" / "powerpoint_monitor.py"),
                "--server",
                server_url,
                "--token",
                token,
            ],
            cwd=str(ROOT / "mac_agent"),
            env=env,
        )

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\nSlipping을 종료합니다.")
    finally:
        if agent:
            agent.terminate()
        backend.terminate()


if __name__ == "__main__":
    main()
