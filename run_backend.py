"""
FinPulse — Backend Launcher for Production (Koyeb, Fly.io, etc).

Starts only the required backend services:
  [API]      FastAPI backend
  [PIPELINE] News pipeline (runs continuously in the background)

NOTE: The Streamlit dashboard should be deployed separately (e.g., Streamlit Community Cloud).
"""
import subprocess
import sys
import threading
import signal
import os
import time

PORT = os.environ.get("PORT", "8000")
PYTHON = sys.executable

SERVICES = [
    {
        "name": "API",
        "cmd":  [PYTHON, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
    },
    {
        "name": "PIPELINE",
        "cmd":  [PYTHON, "-m", "src.streaming.pipeline"],
    },
]

_procs = []
_stop_event = threading.Event()

def _stream_output(proc: subprocess.Popen, name: str):
    """Read stdout/stderr from a process and print with labelled prefix."""
    try:
        for raw_line in proc.stdout:
            if _stop_event.is_set():
                break
            line = raw_line.rstrip()
            if line:
                print(f"[{name}] {line}", flush=True)
    except Exception:
        pass

def _start_service(svc: dict) -> subprocess.Popen:
    name = svc["name"]
    proc = subprocess.Popen(
        svc["cmd"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    thread = threading.Thread(target=_stream_output, args=(proc, name), daemon=True)
    thread.start()
    return proc

def _shutdown(sig=None, frame=None):
    if _stop_event.is_set():
        return
    _stop_event.set()
    print("Stopping backend services...", flush=True)
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1)
    for p in _procs:
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass
    print("All backend services stopped.", flush=True)
    sys.exit(0)

def main():
    print(f"Starting FinPulse Backend on Port {PORT}...", flush=True)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for svc in SERVICES:
        proc = _start_service(svc)
        _procs.append(proc)
        time.sleep(1)

    print("Backend launched successfully.", flush=True)

    try:
        while not _stop_event.is_set():
            for i, (svc, proc) in enumerate(zip(SERVICES, _procs)):
                ret = proc.poll()
                if ret is not None:
                    print(f"[{svc['name']}] crashed (exit {ret}). Restarting...", flush=True)
                    new_proc = _start_service(svc)
                    _procs[i] = new_proc
            time.sleep(5)
    except KeyboardInterrupt:
        _shutdown()

if __name__ == "__main__":
    main()
