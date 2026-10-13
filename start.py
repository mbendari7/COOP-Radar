#!/usr/bin/env python3
"""
Start the whole CoopRadar website with one command.

    python start.py            sets things up the first time and opens http://localhost:8000
    python start.py --dev      same thing plus live reload while you edit code on http://localhost:5173
    python start.py --hosted   what a host runs. Migrate, load data and serve on $PORT

The first run takes a few minutes. It makes a Python environment in backend/.venv, installs
the packages, builds the website and makes a private database in ~/.coopradar, or uses the
DATABASE_URL in your .env. After that it starts in seconds. Press Ctrl+C to stop.

You need Python 3.12 or newer and Node.js 20 or newer. Nothing else.
"""

import argparse
import atexit
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from contextlib import suppress
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
# The local database lives in your home folder outside the repo, and outside OneDrive or
# Dropbox sync which can break a running database. Set COOPRADAR_DATA to put it somewhere else
DATA = Path(os.getenv("COOPRADAR_DATA") or Path.home() / ".coopradar")
IS_WINDOWS = os.name == "nt"
VENV_PYTHON = VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def say(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def fail(msg: str) -> NoReturn:
    print(f"\n[CoopRadar] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError:
        fail(f"This step failed: {' '.join(cmd)}\nScroll up for the error message.")


def load_dotenv() -> None:
    """Read KEY=VALUE lines from .env into the environment. Real env vars win."""
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


# Step 1 is the Python environment. This runs on whatever Python started the script


def _fingerprint() -> str:
    return hashlib.sha256((BACKEND / "pyproject.toml").read_bytes()).hexdigest()


def ensure_venv() -> None:
    """Make backend/.venv and install the backend unless it is already up to date."""
    uv = shutil.which("uv")
    if not VENV_PYTHON.exists():
        say("Creating a Python environment in backend/.venv (first run only)")
        if uv:
            run([uv, "venv", "--python", "3.12", str(VENV)])
        else:
            if sys.version_info < (3, 12):  # noqa: UP036 any Python might run this file
                fail("CoopRadar needs Python 3.12 or newer. Get it from https://www.python.org/downloads/")
            run([sys.executable, "-m", "venv", str(VENV)])

    marker = VENV / ".coopradar-installed"
    if marker.exists() and marker.read_text() == _fingerprint():
        return
    say("Installing Python packages (first run takes a few minutes)")
    target = f"{BACKEND}[local]"
    if uv:
        run([uv, "pip", "install", "--python", str(VENV_PYTHON), "-e", target])
    else:
        run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"])
        run([str(VENV_PYTHON), "-m", "pip", "install", "-e", target])
    marker.write_text(_fingerprint())


# Step 2 is the database


def stop_local_database() -> None:
    """Shut the local database down cleanly when start.py exits from Ctrl+C or an error."""
    import pgserver

    try:
        pgserver.pg_ctl(["-w", "-m", "fast", "stop"], pgdata=DATA / "postgres")
        print("Database stopped.", flush=True)
    except Exception:  # noqa: BLE001 it already stopped
        pass


def start_local_database() -> str:
    """Start a private Postgres from the pgserver package and give back its URL."""
    try:
        import pgserver
    except ImportError:
        fail("pgserver isn't installed. Delete backend/.venv and run start.py again.")
    say(f"Starting the database (stored in {DATA})")
    DATA.mkdir(parents=True, exist_ok=True)
    server = None
    for attempt in range(8):
        try:
            server = pgserver.get_server(DATA / "postgres", cleanup_mode=None)
            break
        except Exception:  # noqa: BLE001
            # After a crash or a closed window Postgres fixes itself first, which can take
            # longer than pgserver waits. It keeps going in the background so try again
            if attempt == 0:
                print("    The database wasn't shut down cleanly last time. Repairing it, "
                      "this can take a minute...", flush=True)
            time.sleep(10)
    if server is None:
        fail(f"The database didn't start. Its log is in {DATA / 'postgres' / 'log'}")
    if "1 row" not in server.psql("SELECT 1 FROM pg_database WHERE datname = 'coopradar';"):
        server.psql("CREATE DATABASE coopradar;")
    atexit.register(stop_local_database)
    return str(server.get_uri("coopradar"))


# Step 3 is the website


def _npm() -> str:
    npm = shutil.which("npm")
    if not npm:
        fail("Node.js is needed to build the website. Install it from https://nodejs.org (LTS).")
    return str(npm)


def _newest_change(*paths: Path) -> float:
    newest = 0.0
    for path in paths:
        files = path.rglob("*") if path.is_dir() else [path]
        newest = max([newest, *(f.stat().st_mtime for f in files if f.is_file())])
    return newest


def ensure_frontend_packages() -> None:
    lock = FRONTEND / "package-lock.json"
    stamp = FRONTEND / "node_modules" / ".package-lock.json"
    if not stamp.exists() or stamp.stat().st_mtime < lock.stat().st_mtime:
        say("Installing website packages (first run only)")
        run([_npm(), "ci"], cwd=FRONTEND)


def ensure_frontend_build() -> None:
    """Build the React site into frontend/dist if the code changed since the last build."""
    ensure_frontend_packages()
    index = FRONTEND / "dist" / "index.html"
    sources = [FRONTEND / "src", FRONTEND / "index.html", FRONTEND / "package-lock.json"]
    if index.exists() and index.stat().st_mtime >= _newest_change(*sources):
        return
    say("Building the website")
    run([_npm(), "run", "build"], cwd=FRONTEND)


# Step 4 is running it


def wait_until_up(url: str, process: subprocess.Popen[bytes], seconds: int = 90) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the CoopRadar website.")
    parser.add_argument("--dev", action="store_true", help="live reload while editing code")
    parser.add_argument("--hosted", action="store_true", help="run on a hosting provider")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    load_dotenv()

    if not args.hosted and Path(sys.prefix).resolve() != VENV.resolve():
        # Set up backend/.venv, then run this same script again with that Python
        ensure_venv()
        child = subprocess.Popen([str(VENV_PYTHON), __file__, *sys.argv[1:]])
        while True:
            # Ctrl+C reaches the child too and it shuts everything down cleanly
            with suppress(KeyboardInterrupt):
                sys.exit(child.wait())

    env = os.environ.copy()
    if not args.hosted:
        # Your own computer. Real jobs only, and plain http on localhost is fine
        env.setdefault("SEED_SAMPLE_POSTINGS", "false")
        env.setdefault("SEED_DEV_SOURCES", "false")
        env.setdefault("COOKIE_SECURE", "false")
    if not env.get("DATABASE_URL"):
        if args.hosted:
            fail("DATABASE_URL isn't set. Add your database URL in the host's settings.")
        env["DATABASE_URL"] = start_local_database()

    if args.dev:
        ensure_frontend_packages()
    elif args.hosted:
        if not (FRONTEND / "dist" / "index.html").exists():
            fail("The website isn't built. The build command must run: npm ci && npm run build")
    else:
        ensure_frontend_build()
    if not args.dev:
        env["STATIC_DIR"] = str(FRONTEND / "dist")

    py = sys.executable
    say("Updating the database tables")
    run([py, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env)
    if env.get("SEED_ON_START", "true").lower() == "true":
        say("Loading the skills list and career boards")
        run([py, "-m", "seed"], cwd=BACKEND, env=env)

    host = "0.0.0.0" if args.hosted else "127.0.0.1"
    server_cmd = [py, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(args.port)]
    if args.hosted:
        # Trust X-Forwarded headers from the host's HTTPS proxy
        server_cmd += ["--proxy-headers", "--forwarded-allow-ips", "*"]
    if args.dev:
        server_cmd += ["--reload", "--reload-dir", "app"]

    say(f"Starting the server on port {args.port}")
    processes = [subprocess.Popen(server_cmd, cwd=BACKEND, env=env)]
    site = f"http://localhost:{args.port}"
    if args.dev:
        vite_env = {**env, "API_PROXY_TARGET": f"http://127.0.0.1:{args.port}"}
        processes.append(subprocess.Popen([_npm(), "run", "dev"], cwd=FRONTEND, env=vite_env))
        site = "http://localhost:5173"

    interrupted = False
    try:
        if not args.hosted:
            if not wait_until_up(f"http://127.0.0.1:{args.port}/api/health", processes[0]):
                fail("The server didn't start. Scroll up for the error message.")
            print(
                f"\n  CoopRadar is running:  {site}\n"
                "  Real jobs are being imported in the background; they appear within a couple\n"
                "  of minutes. Press Ctrl+C to stop.\n",
                flush=True,
            )
            if not args.no_browser:
                webbrowser.open(site)
        while all(p.poll() is None for p in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        interrupted = True
        print("\nStopping CoopRadar...", flush=True)
    finally:
        exit_code = next((p.returncode for p in processes if p.returncode is not None), 0)
        for p in processes:
            if p.poll() is None:
                p.terminate()
        for p in processes:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    sys.exit(0 if interrupted else exit_code)


if __name__ == "__main__":
    main()
