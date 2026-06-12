"""
FinPulse — Single-command launcher.

Starts all three services together:
  [API]      FastAPI backend   → http://localhost:8000
  [DASH]     Streamlit dashboard → http://localhost:8501
  [PIPELINE] Hybrid news pipeline (runs every 5 min)

Usage:
    venv\\Scripts\\python.exe start.py

Press Ctrl+C once to stop everything cleanly.
"""
import subprocess
import sys
import threading
import signal
import os
import time

# ── ANSI colour codes ──────────────────────────────────────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_RED    = "\033[91m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_GREY   = "\033[90m"

# Per-service label colours
SERVICE_COLOURS = {
    "API":      _GREEN,
    "DASH":     _CYAN,
    "PIPELINE": _YELLOW,
}

# ── Service definitions ────────────────────────────────────────────────────
PYTHON = sys.executable   # uses the active venv automatically

SERVICES = [
    {
        "name": "API",
        "cmd":  [PYTHON, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
    },
    {
        "name": "DASH",
        "cmd":  [PYTHON, "-m", "streamlit", "run", "src/dashboard/app.py",
                 "--server.port", "8501", "--server.headless", "true"],
    },
    {
        "name": "PIPELINE",
        "cmd":  [PYTHON, "-m", "src.streaming.pipeline"],
    },
]

_procs = []
_stop_event = threading.Event()


def _prefix(name: str, text: str) -> str:
    col = SERVICE_COLOURS.get(name, _GREY)
    return f"{col}{_BOLD}[{name:8s}]{_RESET} {text}"


def _stream_output(proc: subprocess.Popen, name: str):
    """Read stdout/stderr from a process and print with labelled prefix."""
    try:
        for raw_line in proc.stdout:
            if _stop_event.is_set():
                break
            line = raw_line.rstrip()
            if line:
                print(_prefix(name, line))
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
    print(f"\n{_RED}{_BOLD}Stopping all services...{_RESET}")
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
    print(f"{_GREEN}All services stopped.{_RESET}")
    sys.exit(0)


def main():
    # Enable ANSI codes on Windows
    if sys.platform == "win32":
        os.system("")

    print(f"""
{_BOLD}{_CYAN}╔══════════════════════════════════════════════════════╗
║          FinPulse — Starting All Services            ║
╚══════════════════════════════════════════════════════╝{_RESET}

  {_GREEN}[API]{_RESET}      http://localhost:8000/docs
  {_CYAN}[DASH]{_RESET}     http://localhost:8501
  {_YELLOW}[PIPELINE]{_RESET} Hybrid RSS + NewsAPI (runs every 5 min)

  Press {_BOLD}Ctrl+C{_RESET} to stop everything.
─────────────────────────────────────────────────────────
""")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Start all services
    for svc in SERVICES:
        print(_prefix(svc["name"], f"Starting → {' '.join(svc['cmd'])}"))
        proc = _start_service(svc)
        _procs.append(proc)
        time.sleep(1.5)   # stagger starts so API is up before dashboard

    print(f"\n{_GREEN}{_BOLD}All services launched.{_RESET} Logs streaming below:\n{'─'*55}\n")

    # Wait until something crashes or user hits Ctrl+C
    try:
        while not _stop_event.is_set():
            for i, (svc, proc) in enumerate(zip(SERVICES, _procs)):
                ret = proc.poll()
                if ret is not None:
                    print(f"\n{_RED}{_BOLD}[{svc['name']}] crashed (exit {ret}). Restarting...{_RESET}")
                    new_proc = _start_service(svc)
                    _procs[i] = new_proc
            time.sleep(3)
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
