#!/usr/bin/env python3
"""cairn-board — the local, live panel of one repository (phase 48).

WHAT THIS IS
------------
One stdlib HTTP server per repo, bound to 127.0.0.1 only, serving the same
board `cairn-status.py --html` renders — plus what a static page cannot
show: what is running now, what needs attention, the cycle's Jira links,
and the exact bd command to copy for each row. Nothing here reimplements
the board: every refresh is ONE `cairn-status.py --json --html <cache>`
call, cached for CACHE_TTL seconds, whose JSON becomes /api/status and
whose generated region (between the cairn:generated:board markers) becomes
the fragment the page swaps in. The page polls; the server never pushes.

LIFECYCLE (cairn-board.sh <verb>)
---------------------------------
    start [--port N] [--open]   launch `serve` in the background (nohup,
                                its own session), write .cairn/board.json
                                {port, pid, url, plugin_root, started_at}
                                — gitignored, per machine — and print the
                                URL. A live pid in that file is REUSED (the
                                URL is printed, nothing new starts); a dead
                                one is cleaned up. The port is --port or a
                                free one the OS picks; a busy --port is
                                exit 4, named.
    stop                        SIGTERM the pid, wait, remove board.json.
    open                        open the URL in the default browser.
    status [--json]             what board.json says, and whether the pid
                                is alive.
    serve --port N              the foreground server (what start runs).

After a plugin upgrade the running server still executes the OLD plugin's
files (the cache directory of the previous version stays on disk):
`stop` then `start` moves it to the new one. Nothing is ever written under
the plugin's own directory.

ENDPOINTS (GET only — every POST is 405 in this phase; actions are phase 49)
    /                the page
    /api/status      cairn-status.py --json, verbatim, plus `board`
                     {fetched_at, generated}
    /api/fragment    the board region as HTML, plus the live blocks
    /healthz         "ok"

NO NETWORK LEAVES THIS PROCESS. It binds the loopback and calls sibling
scripts; it never reaches a forge or a tracker itself (phase 51 adds gh
behind git.review_state, in this process, never in cairn-status).

Exit codes: 0 ok · 2 usage · 4 port busy / cannot bind · 5 bd or the
status script unavailable.
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPTS_DIR.parent
CAIRN_STATUS = os.environ.get("CAIRN_STATUS", str(SCRIPTS_DIR / "cairn-status.py"))
CAIRN_LEASE = os.environ.get("CAIRN_LEASE", str(SCRIPTS_DIR / "cairn-lease.py"))
TEMPLATE = PLUGIN_ROOT / "templates" / "board-live.html"
BOARD_START = "<!-- cairn:generated:board:start -->"
BOARD_END = "<!-- cairn:generated:board:end -->"
CACHE_TTL = float(os.environ.get("CAIRN_BOARD_TTL") or 3.0)
EXIT_OK, EXIT_USAGE, EXIT_PORT, EXIT_NO_BD = 0, 2, 4, 5
TAG = "[cairn-board]"


def die(msg, code=EXIT_USAGE):
    print(f"{TAG} error: {msg}", file=sys.stderr)
    sys.exit(code)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_root(project_dir):
    root = Path(project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    return root.resolve()


def board_file(root):
    return root / ".cairn" / "board.json"


def read_board(root):
    try:
        data = json.loads(board_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --------------------------------------------------------------------------- #
# the snapshot: one cairn-status call, cached
# --------------------------------------------------------------------------- #
class Snapshot:
    def __init__(self, root):
        self.root = root
        self.lock = threading.Lock()
        self.fetched_at = 0.0
        self.data = None
        self.fragment = ""
        self.error = None
        self.cache_dir = root / ".cairn" / "cache"

    def refresh(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        html_path = self.cache_dir / "board.html"
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root))
        try:
            proc = subprocess.run(
                [sys.executable, CAIRN_STATUS, "--json", "--html", str(html_path)],
                capture_output=True, text=True, cwd=str(self.root), env=env,
                timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            self.error = f"cairn-status could not run: {exc}"
            return
        if proc.returncode not in (0, EXIT_NO_BD):
            self.error = (f"cairn-status exited {proc.returncode}: "
                          f"{(proc.stderr or proc.stdout).strip()[:300]}")
            return
        try:
            data = json.loads(proc.stdout or "{}")
        except ValueError as exc:
            self.error = f"cairn-status returned no JSON: {exc}"
            return
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError:
            html = ""
        start, end = html.find(BOARD_START), html.find(BOARD_END)
        fragment = html[start + len(BOARD_START):end] if start >= 0 and end > start else ""
        self.data, self.fragment, self.error = data, fragment, None
        self.fetched_at = time.time()

    def current(self):
        with self.lock:
            if time.time() - self.fetched_at > CACHE_TTL or self.data is None:
                self.refresh()
            return self.data, self.fragment, self.error, self.fetched_at


def live_blocks(root, data):
    """The live blocks the static board has no way to show (BOARD-03):
    filled in by phase 48's second wave; the first wave serves the board
    region alone."""
    return ""


# --------------------------------------------------------------------------- #
# the server
# --------------------------------------------------------------------------- #
def make_handler(root, snapshot):
    class Handler(BaseHTTPRequestHandler):
        server_version = "cairn-board"

        def log_message(self, fmt, *args):
            sys.stderr.write(f"{TAG} {self.address_string()} {fmt % args}\n")

        def send(self, code, body, ctype="text/plain; charset=utf-8"):
            raw = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            self.send(405, "read only in this phase — actions arrive in phase 49\n")

        do_PUT = do_DELETE = do_PATCH = do_POST

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/healthz":
                return self.send(200, "ok\n")
            data, fragment, error, fetched_at = snapshot.current()
            stamp = datetime.fromtimestamp(fetched_at, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ") if fetched_at else None
            if path == "/api/status":
                if data is None:
                    return self.send(503, json.dumps({"error": error}),
                                     "application/json; charset=utf-8")
                payload = dict(data)
                payload["board"] = {"fetched_at": stamp,
                                    "generated": data.get("generated"),
                                    "error": error}
                return self.send(200, json.dumps(payload),
                                 "application/json; charset=utf-8")
            if path == "/api/fragment":
                if data is None:
                    return self.send(503, f"<p class=\"placeholder\">{error}</p>",
                                     "text/html; charset=utf-8")
                return self.send(200, fragment + live_blocks(root, data),
                                 "text/html; charset=utf-8")
            if path == "/":
                return self.send(200, render_page(root, snapshot),
                                 "text/html; charset=utf-8")
            return self.send(404, "not found\n")
    return Handler


def render_page(root, snapshot):
    """The page: the live template when it ships (wave 02), else the
    static render itself — the same board, without the poller."""
    data, fragment, error, fetched_at = snapshot.current()
    if TEMPLATE.is_file():
        page = TEMPLATE.read_text(encoding="utf-8")
        body = fragment + live_blocks(root, data) if data is not None else \
            f"<p class=\"placeholder\">{error}</p>"
        return page.replace("<!-- cairn:board:fragment -->", body)
    cached = snapshot.cache_dir / "board.html"
    try:
        return cached.read_text(encoding="utf-8")
    except OSError:
        return f"<p>{error or 'no board yet'}</p>"


def cmd_serve(args, root):
    if not (root / ".beads").is_dir():
        die(f"no .beads/ under {root} — the board shows a tracked repo", EXIT_USAGE)
    snapshot = Snapshot(root)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                     make_handler(root, snapshot))
    except OSError as exc:
        die(f"cannot bind 127.0.0.1:{args.port}: {exc}", EXIT_PORT)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    record = {"port": port, "pid": os.getpid(), "url": url,
              "plugin_root": str(PLUGIN_ROOT), "started_at": now_iso()}
    board_file(root).parent.mkdir(parents=True, exist_ok=True)
    board_file(root).write_text(json.dumps(record, indent=2) + "\n")

    def bye(*_):
        try:
            if read_board(root) and read_board(root).get("pid") == os.getpid():
                board_file(root).unlink()
        except OSError:
            pass
        os._exit(0)
    signal.signal(signal.SIGTERM, bye)
    signal.signal(signal.SIGINT, bye)
    print(f"{TAG} serving {root} at {url} (pid {os.getpid()})", flush=True)
    server.serve_forever()


def cmd_start(args, root):
    if not (root / ".beads").is_dir():
        die(f"no .beads/ under {root} — the board shows a tracked repo", EXIT_USAGE)
    existing = read_board(root)
    if existing and pid_alive(existing.get("pid")):
        out = dict(existing, reused=True)
        if args.json:
            print(json.dumps(out))
        else:
            print(f"{TAG} already serving at {existing.get('url')} "
                  f"(pid {existing.get('pid')}) — cairn-board.sh stop to restart")
        if args.open:
            open_url(existing.get("url"))
        sys.exit(EXIT_OK)
    if existing:
        try:
            board_file(root).unlink()
        except OSError:
            pass
    port = args.port if args.port else free_port()
    if args.port and not port_free(port):
        die(f"port {port} is busy — pick another with --port, or stop what "
            "holds it", EXIT_PORT)
    log = root / ".cairn" / "board.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as fh:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve",
             "--port", str(port), "--project-dir", str(root)],
            stdout=fh, stderr=fh, stdin=subprocess.DEVNULL,
            start_new_session=True, cwd=str(root))
    deadline = time.time() + 10
    record = None
    while time.time() < deadline:
        record = read_board(root)
        if record and record.get("pid") == proc.pid:
            break
        if proc.poll() is not None:
            tail = ""
            try:
                tail = log.read_text(encoding="utf-8").strip().splitlines()[-1]
            except (OSError, IndexError):
                pass
            die(f"the server exited {proc.returncode} before it was up: {tail}",
                EXIT_PORT if proc.returncode == EXIT_PORT else EXIT_USAGE)
        time.sleep(0.1)
    else:
        die("the server did not come up within 10s — see .cairn/board.log",
            EXIT_USAGE)
    out = dict(record, reused=False)
    if args.json:
        print(json.dumps(out))
    else:
        print(f"{TAG} serving at {record['url']} (pid {record['pid']}) — "
              f"cairn-board.sh stop ends it")
    if args.open:
        open_url(record["url"])
    sys.exit(EXIT_OK)


def cmd_stop(args, root):
    record = read_board(root)
    if not record:
        print(f"{TAG} nothing to stop (no .cairn/board.json)")
        sys.exit(EXIT_OK)
    pid = record.get("pid")
    if pid_alive(pid):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + 5
        while pid_alive(pid) and time.time() < deadline:
            time.sleep(0.1)
        if pid_alive(pid):
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass
    try:
        board_file(root).unlink()
    except OSError:
        pass
    if args.json:
        print(json.dumps({"stopped": pid, "url": record.get("url")}))
    else:
        print(f"{TAG} stopped pid {pid} ({record.get('url')})")
    sys.exit(EXIT_OK)


def open_url(url):
    if not url:
        return
    for cmd in (["open", url], ["xdg-open", url]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            continue
    print(f"{TAG} open {url} in your browser", file=sys.stderr)


def cmd_open(args, root):
    record = read_board(root)
    if not record or not pid_alive(record.get("pid")):
        die("the board is not running — cairn-board.sh start", EXIT_USAGE)
    open_url(record.get("url"))
    print(f"{TAG} {record.get('url')}")
    sys.exit(EXIT_OK)


def cmd_status(args, root):
    record = read_board(root) or {}
    alive = pid_alive(record.get("pid")) if record else False
    out = dict(record, running=alive)
    if args.json:
        print(json.dumps(out))
    elif not record:
        print(f"{TAG} not running (no .cairn/board.json)")
    else:
        print(f"{TAG} {'running' if alive else 'NOT running (stale board.json)'} "
              f"at {record.get('url')} (pid {record.get('pid')}, plugin "
              f"{record.get('plugin_root')})")
    sys.exit(EXIT_OK)


def build_parser():
    parser = argparse.ArgumentParser(prog="cairn-board",
                                     description="the local live panel of a cairn repo")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start", help="launch the server in the background")
    start.add_argument("--port", type=int, help="port (default: a free one)")
    start.add_argument("--open", action="store_true", help="open the browser")
    start.set_defaults(func=cmd_start)
    stop = sub.add_parser("stop", help="stop the server")
    stop.set_defaults(func=cmd_stop)
    opn = sub.add_parser("open", help="open the board in the browser")
    opn.set_defaults(func=cmd_open)
    status = sub.add_parser("status", help="is it running, and where")
    status.set_defaults(func=cmd_status)
    serve = sub.add_parser("serve", help="the foreground server")
    serve.add_argument("--port", type=int, default=0)
    serve.set_defaults(func=cmd_serve)
    for p in (start, stop, opn, status, serve):
        p.add_argument("--project-dir", metavar="DIR")
        p.add_argument("--json", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    root = resolve_root(args.project_dir)
    if not root.is_dir():
        die(f"project directory does not exist: {root}", EXIT_USAGE)
    args.func(args, root)


if __name__ == "__main__":
    main()
