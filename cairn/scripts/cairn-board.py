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

ENDPOINTS
    GET  /               the page
    GET  /api/status     cairn-status.py --json, verbatim, plus `board`
                         {fetched_at, generated}
    GET  /api/fragment   the board region as HTML, plus the live blocks
    GET  /api/trend      {cycles, phases, not_measured} — cairn-trend's
                         first-pass verdict per cycle plus closed-per-day
                         per phase of the open cycle, from bd (phase 51)
    GET  /api/ci         {enabled, switch, branch, runs, gates, errors} —
                         `gh run list` for the current branch, ONLY when
                         git.review_state is `gh`, cached 60 s under
                         .cairn/ci-cache.json; off says so (phase 51)
    GET  /healthz        "ok"
    POST /api/action     {action, id, reason?} — claim | close | reopen |
                         gate-check | gate-resolve | lease-release, each
                         run as the deterministic CLI (argv, never a shell)
                         with BEADS_ACTOR=board, mirrored through gbsync
                         when .cairn/sync.json exists (the post-bd-write
                         hook never sees this process), one line per action
                         in .cairn/board.log. 403 unless Origin/Host name
                         this board's own port (ACT-02, no token by
                         decision); 400 on a malformed request; 409 when
                         the CLI refused, with its stderr.

NO NETWORK LEAVES THIS PROCESS. It binds the loopback and calls sibling
scripts; it never reaches a forge or a tracker itself (phase 51 adds gh
behind git.review_state, in this process, never in cairn-status).

Exit codes: 0 ok · 2 usage · 4 port busy / cannot bind · 5 bd or the
status script unavailable.
"""
import argparse
import json
import os
import re
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
CAIRN_GBSYNC = os.environ.get("CAIRN_GBSYNC", str(SCRIPTS_DIR / "gbsync.sh"))
CAIRN_STOP = os.environ.get("CAIRN_STOP", str(SCRIPTS_DIR / "cairn-stop.py"))
CAIRN_TREND = os.environ.get("CAIRN_TREND", str(SCRIPTS_DIR / "cairn-trend.py"))
CAIRN_CONFIG = os.environ.get("CAIRN_CONFIG", str(SCRIPTS_DIR / "cairn-config.py"))
CAIRN_GH = os.environ.get("CAIRN_GH", "gh")
TREND_TTL = 60.0
CI_TTL = float(os.environ.get("CAIRN_BOARD_CI_TTL") or 60.0)
TEMPLATE = PLUGIN_ROOT / "templates" / "status-board.html"
LIVE_MARK = "<!-- cairn:live:blocks -->"
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


# --------------------------------------------------------------------------- #
# the live blocks — what a snapshot cannot carry (BOARD-03)
# --------------------------------------------------------------------------- #
def esc(text):
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def run_json(argv, cwd, default):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              cwd=str(cwd), timeout=60)
        out = (proc.stdout or "").strip()
        start = min([i for i in (out.find("["), out.find("{")) if i >= 0] or [-1])
        if start < 0:
            return default
        value = json.loads(out[start:])
        return value if value is not None else default
    except (OSError, ValueError, subprocess.SubprocessError):
        return default


def leases_now(root):
    entries = run_json([sys.executable, CAIRN_LEASE, "status", "--all",
                        "--json", "--project-dir", str(root)], root, [])
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and e.get("held")]


def open_gates(root):
    gates = run_json(["bd", "-C", str(root), "gate", "list", "--json"], root, [])
    if isinstance(gates, dict):
        gates = gates.get("gates") or []
    return [g for g in gates if isinstance(g, dict)] if isinstance(gates, list) else []


def journal_tail(root, limit=12):
    """The last `limit` journal records across this checkout AND every
    worktree of the repo (C-04): each one keeps its own .cairn/journal/, and
    a phase running in a sibling tree is exactly what "now" has to show."""
    roots = [root]
    try:
        proc = subprocess.run(["git", "-C", str(root), "worktree", "list",
                               "--porcelain"], capture_output=True, text=True,
                              timeout=30)
        for line in (proc.stdout or "").splitlines():
            if line.startswith("worktree "):
                path = Path(line[len("worktree "):].strip())
                if path.resolve() != root.resolve() and path.is_dir():
                    roots.append(path)
    except (OSError, subprocess.SubprocessError):
        pass
    records = []
    for base in roots:
        for f in sorted((base / ".cairn" / "journal").glob("*.jsonl")):
            try:
                lines = f.read_text(encoding="utf-8").splitlines()[-limit:]
            except OSError:
                continue
            for line in lines:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("ts"):
                    rec["_where"] = base.name
                    records.append(rec)
    records.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return records[:limit]


def copy_button(cmd):
    return (f'<button type="button" class="copy" data-cmd="{esc(cmd)}" '
            f'title="{esc(cmd)}">copy</button>')


def act_button(action, ident, label, needs_reason=False):
    """An action control (phase 49): one click runs the CLI; an action
    that needs a reason reads it from the input beside it."""
    field = (f'<input class="why" type="text" placeholder="reason" '
             f'aria-label="reason for {esc(label)}">' if needs_reason else "")
    return (f'{field}<button type="button" class="act" data-action="{esc(action)}" '
            f'data-id="{esc(ident)}">{esc(label)}</button>')


def live_blocks(root, data):
    """The four blocks appended after the board region: attention, now,
    jira, commands. Every button copies a command for the terminal; no
    endpoint writes (actions are phase 49)."""
    if not data:
        return ""
    ms = data.get("milestone")
    lanes = {k: data.get(k) or [] for k in ("ready", "doing", "blocked")}
    out = [LIVE_MARK, '<div class="live">']

    # --- attention -------------------------------------------------------
    rows = []
    for g in open_gates(root):
        gid = g.get("id") or "?"
        what = f"{g.get('type') or 'gate'} gate {gid}"
        blocks = g.get("blocks") or g.get("blocked") or ""
        reason = g.get("reason") or g.get("title") or ""
        gtype = str(g.get("type") or "gh:run")
        rows.append(f'<li><span class="live-k">{esc(what)}</span> '
                    f'<span class="live-v">{esc(reason)}'
                    f'{" · blocks " + esc(blocks) if blocks else ""}</span> '
                    f'{act_button("gate-check", gtype, "check")} '
                    f'{act_button("gate-resolve", gid, "resolve", needs_reason=True)} '
                    f'{copy_button("bd gate resolve " + str(gid) + " -r \"\"")}</li>')
    if lanes["blocked"]:
        ids = ", ".join(str(i.get("id")) for i in lanes["blocked"][:6])
        rows.append(f'<li><span class="live-k">{len(lanes["blocked"])} blocked</span> '
                    f'<span class="live-v">{esc(ids)}</span></li>')
    nxt = data.get("next") or {}
    if nxt.get("text"):
        cmd = nxt.get("command") or (f"bd update {nxt.get('id')} --claim"
                                     if nxt.get("id") else "")
        rows.append(f'<li><span class="live-k is-next">next</span> '
                    f'<span class="live-v">{esc(nxt["text"])}</span> '
                    f'{copy_button(cmd) if cmd else ""}</li>')
    out.append('<section class="live-block" id="live-attention"><h2 class="panel-h">attention</h2>'
               + (f'<ul>{"".join(rows)}</ul>' if rows
                  else '<p class="live-empty">nothing waits on you.</p>')
               + '</section>')

    # --- now -------------------------------------------------------------
    rows = []
    stop_flag = run_json([sys.executable, CAIRN_STOP, "check", "--json",
                          "--project-dir", str(root)], root, {})
    if stop_flag.get("requested"):
        target = stop_flag.get("phase")
        rows.append(f'<li class="live-stop"><span class="live-k is-next">stop requested</span> '
                    f'<span class="live-v">{esc((stop_flag.get("ts") or "")[11:19])} by '
                    f'{esc(stop_flag.get("actor"))} for '
                    f'{esc("phase " + str(target) if target else "everything")}'
                    f'{" · " + esc(stop_flag.get("reason")) if stop_flag.get("reason") else ""}'
                    f' — the loop stops at its next boundary</span> '
                    f'{act_button("stop-clear", "", "clear")}</li>')
    for e in leases_now(root):
        who = (f"phase {e.get('phase')}" if e.get("phase") is not None
               else f"bead {e.get('bead')}")
        stale = " (stale)" if e.get("stale") else ""
        key = (str(e.get("phase")) if e.get("phase") is not None
               else f"bead:{e.get('bead')}")
        rows.append(f'<li><span class="live-k">{esc(who)}{stale}</span> '
                    f'<span class="live-v">{esc(e.get("holder") or "")} since '
                    f'{esc((e.get("acquired_at") or "")[:19])}</span> '
                    f'{act_button("stop", key, "stop")} '
                    f'{act_button("lease-release", key, "release")}</li>')
    journal = journal_tail(root)
    jrows = []
    for r in journal:
        ev = r.get("event") or ""
        detail = ""
        if ev == "state_changed":
            detail = f"{r.get('source')}: {r.get('from')} → {r.get('to')}"
        elif ev == "verdict_changed":
            detail = f"{r.get('from')} → {r.get('to')}"
        elif ev == "lease_changed":
            detail = f"{r.get('action') or ''} {r.get('holder') or ''}".strip()
        jrows.append(f'<li><span class="live-t">{esc((r.get("ts") or "")[11:19])}</span> '
                    f'<span class="live-k">phase {esc(r.get("phase"))}</span> '
                    f'<span class="live-v">{esc(ev)} {esc(detail)} '
                    f'<span class="live-dim">{esc(r.get("_where"))}</span></span></li>')
    out.append('<section class="live-block" id="live-now"><h2 class="panel-h">now</h2>'
               + (f'<ul>{"".join(rows)}</ul>' if rows
                  else '<p class="live-empty">no lease held.</p>')
               + (f'<h3>journal</h3><ul class="live-journal">{"".join(jrows)}</ul>'
                  if jrows else '')
               + '</section>')

    # --- jira ------------------------------------------------------------
    jira = data.get("jira") or {}
    carrier = data.get("milestone_carrier") or {}
    rows = []
    if ms:
        story = (jira.get("milestone") or {}).get("story")
        epic = (jira.get("milestone") or {}).get("epic")
        rows.append(f'<li><span class="live-k">m-{esc(ms)}</span> '
                    f'<span class="live-v">{esc(carrier.get("name") or "")}'
                    f'{" ⧉ " + esc(story) if story else " (no story linked)"}'
                    f'{" · epic " + esc(epic) if epic else ""}</span></li>')
        for n, key in sorted((jira.get("phases") or {}).items(),
                             key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
            rows.append(f'<li><span class="live-k">phase {esc(n)}</span> '
                        f'<span class="live-v">⧉ {esc(key)}</span></li>')
    out.append('<section class="live-block" id="live-jira"><h2 class="panel-h">jira</h2>'
               + (f'<ul>{"".join(rows)}</ul>' if rows
                  else '<p class="live-empty">no open cycle.</p>')
               + '</section>')

    # --- commands --------------------------------------------------------
    rows = []
    for i in lanes["ready"][:12]:
        iid = str(i.get("id"))
        rows.append(f'<li><span class="live-k">{esc(iid)}</span> '
                    f'<span class="live-v">{esc(i.get("title"))}</span> '
                    f'{act_button("claim", iid, "claim")} '
                    f'{copy_button("bd update " + iid + " --claim")}</li>')
    for i in lanes["doing"][:12]:
        iid = str(i.get("id"))
        rows.append(f'<li><span class="live-k">{esc(iid)}</span> '
                    f'<span class="live-v">{esc(i.get("title"))}</span> '
                    f'{act_button("close", iid, "close", needs_reason=True)} '
                    f'{copy_button("bd close " + iid + " --reason=\"\"")}</li>')
    out.append('<section class="live-block" id="live-commands"><h2 class="panel-h">commands</h2>'
               + (f'<ul>{"".join(rows)}</ul>' if rows
                  else '<p class="live-empty">nothing to claim or close.</p>')
               + '</section>')
    out.append(trend_block(root))
    out.append(ci_block(root))
    out.append('</div>')
    return "\n".join(out)


LIVE_CSS = """
<style>
/* the live blocks — data in mono where it is data, tone over decoration */
.live { display: grid; align-items: start; gap: clamp(20px, 3vw, 36px); margin-top: clamp(28px, 4vw, 48px); }
@media (min-width: 900px) { .live { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.live-block > .panel-h { margin: 0 0 10px; }
.live-block h3 { font: 400 var(--t-xs)/1.2 var(--sans); color: var(--bone-dim); margin: 18px 0 6px; }
.live-block ul { list-style: none; margin: 0; padding: 0; }
.live-block li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 12px; padding: 7px 0; border-top: 1px solid color-mix(in srgb, var(--bone) 12%, transparent); }
.live-block li:first-child { border-top: 0; }
.live-k { font: 400 var(--t-s)/1.4 var(--mono); color: var(--bone); white-space: nowrap; }
.live-k.is-next { color: var(--amber); }
.live-t { font: 400 var(--t-xs)/1.4 var(--mono); color: var(--bone-dim); }
.live-v { font: 400 var(--t-s)/1.4 var(--sans); color: var(--bone); flex: 1 1 200px; min-width: 0; overflow-wrap: anywhere; }
.live-dim { color: var(--bone-dim); }
.live-empty { font: 400 var(--t-s)/1.4 var(--sans); color: var(--bone-dim); margin: 0; }
.live-journal li { padding: 4px 0; border-top: 0; }
.copy, .act { font: 400 var(--t-xs)/1 var(--mono); color: var(--bone); background: color-mix(in srgb, var(--bone) 10%, transparent); border: 1px solid color-mix(in srgb, var(--bone) 18%, transparent); border-radius: 4px; padding: 5px 9px; cursor: pointer; }
.copy { margin-left: auto; }
.act { color: var(--amber); border-color: color-mix(in srgb, var(--amber) 40%, transparent); }
.copy:hover, .copy:focus-visible, .act:hover, .act:focus-visible { background: color-mix(in srgb, var(--bone) 18%, transparent); outline: none; }
.copy.is-done, .act.is-done { color: var(--lichen); border-color: color-mix(in srgb, var(--lichen) 60%, transparent); }
.act.is-failed { color: var(--oxide); border-color: color-mix(in srgb, var(--oxide) 60%, transparent); }
.act[disabled] { opacity: .6; cursor: progress; }
.why { font: 400 var(--t-xs)/1.2 var(--mono); color: var(--bone); background: color-mix(in srgb, var(--bone) 6%, transparent); border: 1px solid color-mix(in srgb, var(--bone) 18%, transparent); border-radius: 4px; padding: 4px 8px; width: 12rem; max-width: 100%; }
.why:focus { outline: none; border-color: color-mix(in srgb, var(--amber) 60%, transparent); }
.why.is-missing { border-color: color-mix(in srgb, var(--oxide) 70%, transparent); }
.spark { display: inline-block; vertical-align: middle; }
.live-block li.has-spark { align-items: center; }
.spark polyline, .spark line { fill: none; stroke: var(--lichen); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.spark line { stroke: var(--bone-dim); }
.live-k.is-ok { color: var(--lichen); }
.live-k.is-bad { color: var(--oxide); }
.live-link { font: 400 var(--t-xs)/1 var(--mono); color: var(--bone-dim); text-decoration: none; border-bottom: 1px solid color-mix(in srgb, var(--bone) 25%, transparent); }
.live-link:hover { color: var(--bone); }
.live-status { font: 400 var(--t-xs)/1.4 var(--mono); color: var(--bone-dim); max-width: var(--measure); margin: 0 auto; padding: 18px var(--pad) 0; }
.live-status.is-off { color: var(--oxide); }
</style>
"""

LIVE_JS = """
<script>
(function () {
  var main = document.querySelector('main.sheet');
  var status = document.getElementById('live-status');
  var lastSig = null, lastChange = Date.now(), timer = null, due = 0, inflight = false;
  function sig(d) {
    var ids = function (xs) { return (xs || []).map(function (i) { return i.id + ':' + (i.assignee || ''); }).join(','); };
    return JSON.stringify([d.counts, ids(d.ready), ids(d.doing), ids(d.blocked),
      d.lease && d.lease.held, d.phase && d.phase.active, d.next && d.next.text, d.jira]);
  }
  function cadence(d) {
    var active = (d.lease && d.lease.held && !d.lease.stale) || (d.counts && d.counts.doing > 0);
    if (active) return 5000;
    return (Date.now() - lastChange > 5 * 60 * 1000) ? 30000 : 15000;
  }
  function clock() {
    if (!status || status.classList.contains('is-off') || !due) return;
    var s = Math.max(0, Math.round((due - Date.now()) / 1000));
    status.textContent = 'observed ' + status.dataset.at + ' · next in ' + s + 's';
  }
  function schedule(ms) {
    clearTimeout(timer); due = Date.now() + ms;
    timer = setTimeout(poll, ms);
  }
  function refresh() {
    fetch('/api/fragment', { cache: 'no-store' }).then(function (r) { return r.text(); }).then(function (html) {
      main.innerHTML = html; wire();
    });
  }
  function poll() {
    if (document.visibilityState !== 'visible' || inflight) return;
    inflight = true;
    fetch('/api/status', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
      inflight = false;
      var s = sig(d);
      if (status) { status.dataset.at = new Date().toTimeString().slice(0, 8); status.classList.remove('is-off'); }
      if (s !== lastSig) {
        lastChange = Date.now();
        if (lastSig !== null) refresh();   // the first poll is the page itself
        lastSig = s;
      }
      schedule(cadence(d));
    }).catch(function () {
      inflight = false;
      if (status) { status.textContent = 'board unreachable — cairn-board.sh start'; status.classList.add('is-off'); }
      schedule(15000);
    });
  }
  function copyText(text, btn) {
    var done = function () { btn.textContent = 'copied'; btn.classList.add('is-done');
      setTimeout(function () { btn.textContent = 'copy'; btn.classList.remove('is-done'); }, 1400); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); });
    } else { fallback(text); done(); }
  }
  function fallback(text) {
    var ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', '');
    ta.style.position = 'fixed'; ta.style.left = '-9999px'; document.body.appendChild(ta);
    ta.select(); try { document.execCommand('copy'); } catch (e) {} document.body.removeChild(ta);
  }
  function act(btn) {
    var why = btn.previousElementSibling;
    var reason = (why && why.classList.contains('why')) ? why.value.trim() : '';
    if (why && why.classList.contains('why') && !reason) {
      why.classList.add('is-missing'); why.focus(); return;
    }
    var label = btn.textContent;
    btn.disabled = true; btn.textContent = 'running';
    fetch('/api/action', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: btn.dataset.action, id: btn.dataset.id, reason: reason }) })
    .then(function (r) { return r.json(); }).then(function (res) {
      btn.disabled = false;
      if (res.ok) {
        btn.textContent = 'done'; btn.classList.add('is-done');
        // The write is done: show it now, and let the next poll settle the
        // signature. (Resetting the signature would trip the first-poll
        // guard above and never swap — measured in the browser.)
        setTimeout(function () { refresh(); poll(); }, 400);
      } else {
        btn.textContent = 'failed'; btn.classList.add('is-failed');
        btn.title = (res.error || res.stderr || res.stdout || '').trim();
        setTimeout(function () { btn.textContent = label; btn.classList.remove('is-failed'); }, 4000);
      }
    }).catch(function () { btn.disabled = false; btn.textContent = 'failed'; btn.classList.add('is-failed'); });
  }
  function wire() {
    main.querySelectorAll('button.copy').forEach(function (b) {
      b.addEventListener('click', function () { copyText(b.dataset.cmd, b); });
    });
    main.querySelectorAll('button.act').forEach(function (b) {
      b.addEventListener('click', function () { act(b); });
    });
    main.querySelectorAll('input.why').forEach(function (i) {
      i.addEventListener('input', function () { i.classList.remove('is-missing'); });
    });
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') poll();
  });
  wire();
  setInterval(clock, 1000);
  poll();
})();
</script>
"""


# --------------------------------------------------------------------------- #
# trend and CI — history, and the one block that reaches the forge (phase 51)
# --------------------------------------------------------------------------- #
_TREND = {"at": 0.0, "model": None}
_CI = {"at": 0.0, "model": None}


def trend_model(root):
    """{cycles: what cairn-trend says, phases: closed-per-day per phase of the
    open cycle, from bd}. 'Time in DOING' is deliberately absent: bd keeps
    no entry-into-in_progress stamp, and a number derived from updated_at
    would measure the last edit, not the work."""
    if time.time() - _TREND["at"] < TREND_TTL and _TREND["model"] is not None:
        return _TREND["model"]
    trend = run_json([sys.executable, CAIRN_TREND, "--json"], root, {})
    cycles = []
    for c in (trend.get("cycles") or []) if isinstance(trend, dict) else []:
        num = den = 0
        for e in c.get("entries") or []:
            r = e.get("score_ratio")
            if isinstance(r, list) and len(r) == 2 and r[1]:
                num += r[0]; den += r[1]
        cycles.append({"cycle": c.get("cycle"), "coverage": c.get("coverage"),
                       "ratio": (num / den) if den else None,
                       "comparable": c.get("cycle") in (trend.get("comparable") or [])})
    issues = run_json(["bd", "-C", str(root), "list", "--all", "--limit", "0",
                       "--json"], root, [])
    phases = {}
    open_keys = set()
    for i in issues if isinstance(issues, list) else []:
        labels = i.get("labels") or []
        ms = [l[2:] for l in labels if l.startswith("m-")]
        if i.get("status") != "closed":
            open_keys.update(ms)
    for i in issues if isinstance(issues, list) else []:
        labels = i.get("labels") or []
        ms = [l[2:] for l in labels if l.startswith("m-")]
        if not (set(ms) & open_keys):
            continue
        for l in labels:
            if l.startswith("phase-") and l[6:].isdigit():
                n = int(l[6:])
                row = phases.setdefault(n, {"phase": n, "title": None, "open": 0,
                                            "closed": 0, "closed_by_day": {}})
                if i.get("status") == "closed":
                    row["closed"] += 1
                    day = (i.get("closed_at") or "")[:10]
                    if day:
                        row["closed_by_day"][day] = row["closed_by_day"].get(day, 0) + 1
                else:
                    row["open"] += 1
                gsd = (i.get("metadata") or {}).get("gsd") if isinstance(i.get("metadata"), dict) else None
                if not gsd and not any(x.startswith("plan-") for x in labels) \
                        and "." not in (i.get("id") or "").split("-", 1)[-1]:
                    row["title"] = i.get("title")
    model = {"cycles": cycles, "phases": [phases[k] for k in sorted(phases)],
             "disambiguator": trend.get("disambiguator") if isinstance(trend, dict) else None,
             "not_measured": ["time in DOING: bd keeps no entry-into-in_progress stamp"]}
    _TREND.update(at=time.time(), model=model)
    return model


def review_switch(root):
    try:
        proc = subprocess.run([sys.executable, CAIRN_CONFIG, "get", "git.review_state",
                               "--project-dir", str(root)],
                              capture_output=True, text=True, cwd=str(root), timeout=30)
        return (proc.stdout or "").strip() or "off"
    except (OSError, subprocess.SubprocessError):
        return "off"


def ci_model(root):
    """The CI block's data (TREND-02): only when git.review_state is `gh`,
    only from THIS process — cairn-status and cairn-land stay structurally
    offline — and cached under .cairn/ci-cache.json with fetched_at."""
    if time.time() - _CI["at"] < CI_TTL and _CI["model"] is not None:
        return _CI["model"]
    switch = review_switch(root)
    if switch != "gh":
        model = {"enabled": False, "switch": switch,
                 "note": ("CI desligada · /cairn:config git.review_state gh"
                          if switch == "off" else
                          f"CI via {switch}: not wired in the board yet "
                          "(gh only for now)")}
        _CI.update(at=time.time(), model=model)
        return model
    try:
        branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                                capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        branch = ""
    runs, errors = [], []
    fields = "databaseId,name,status,conclusion,headSha,url,createdAt,displayTitle,headBranch"
    try:
        proc = subprocess.run([CAIRN_GH, "run", "list", "--branch", branch or "HEAD",
                               "--limit", "6", "--json", fields],
                              capture_output=True, text=True, cwd=str(root), timeout=60)
        if proc.returncode == 0:
            runs = json.loads(proc.stdout or "[]")
        else:
            errors.append((proc.stderr or proc.stdout).strip()[:300] or f"gh exited {proc.returncode}")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        errors.append(f"gh could not run: {exc}")
    gates = []
    for g in open_gates(root):
        if str(g.get("type") or "") == "gh:run":
            gates.append({"id": g.get("id"), "await_id": g.get("await_id"),
                          "blocks": g.get("blocks") or g.get("blocked"),
                          "reason": g.get("reason") or g.get("title")})
    model = {"enabled": True, "switch": "gh", "branch": branch,
             "fetched_at": now_iso(), "runs": runs if isinstance(runs, list) else [],
             "gates": gates, "errors": errors}
    try:
        (root / ".cairn").mkdir(parents=True, exist_ok=True)
        (root / ".cairn" / "ci-cache.json").write_text(json.dumps(model, indent=2) + "\n")
    except OSError:
        pass
    _CI.update(at=time.time(), model=model)
    return model


def sparkline(points, width=160, height=28):
    """One polyline over `points` (ints), no axis, no fill — a line and the
    number beside it is all a per-phase daily count needs."""
    if not points or max(points) == 0:
        return f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-hidden="true"><line x1="0" y1="{height-2}" x2="{width}" y2="{height-2}"></line></svg>'
    top = max(points)
    n = len(points)
    xs = [(i * (width - 2) / max(1, n - 1)) + 1 for i in range(n)]
    ys = [height - 2 - (p / top) * (height - 6) for p in points]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'aria-hidden="true"><polyline points="{pts}"></polyline></svg>')


def trend_block(root):
    m = trend_model(root)
    rows = []
    comp = [c for c in m["cycles"] if c.get("ratio") is not None]
    if comp:
        w, h = 160, 28
        xs = [(i * (w - 2) / max(1, len(comp) - 1)) + 1 for i in range(len(comp))]
        ys = [h - 2 - c["ratio"] * (h - 6) for c in comp]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        labels = " · ".join(f"{c['cycle']} {round(c['ratio'] * 100)}%" for c in comp)
        rows.append(f'<li class="has-spark"><span class="live-k">first pass</span> '
                    f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
                    f'<polyline points="{pts}"></polyline></svg> '
                    f'<span class="live-v live-dim">{esc(labels)}</span></li>')
        if m.get("disambiguator"):
            rows.append(f'<li><span class="live-v live-dim">{esc(str(m["disambiguator"])[:200])}</span></li>')
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=13 - i)).isoformat() for i in range(14)]
    for ph in m["phases"]:
        series = [ph["closed_by_day"].get(d, 0) for d in days]
        total = ph["closed"] + ph["open"]
        rows.append(f'<li class="has-spark"><span class="live-k">phase {ph["phase"]}</span> '
                    f'{sparkline(series)} '
                    f'<span class="live-v"><span class="n">{ph["closed"]}</span>/{total} closed'
                    f'{" · " + esc(ph["title"]) if ph.get("title") else ""}</span></li>')
    note = "; ".join(m.get("not_measured") or [])
    return ('<section class="live-block" id="live-trend"><h2 class="panel-h">trend</h2>'
            + (f'<ul>{"".join(rows)}</ul>' if rows else '<p class="live-empty">no history yet.</p>')
            + (f'<p class="live-empty">not measured: {esc(note)}</p>' if note else '')
            + '<p class="live-empty">14 days per phase, from bd closed_at; first pass from cairn-trend.</p>'
            + '</section>')


def ci_block(root):
    m = ci_model(root)
    if not m.get("enabled"):
        return ('<section class="live-block" id="live-ci"><h2 class="panel-h">ci</h2>'
                f'<p class="live-empty">{esc(m.get("note"))}</p></section>')
    rows = []
    for r in m.get("runs") or []:
        state = r.get("conclusion") or r.get("status") or "?"
        cls = {"success": "is-ok", "failure": "is-bad"}.get(state, "")
        rows.append(f'<li><span class="live-k {cls}">{esc(state)}</span> '
                    f'<span class="live-v">{esc(r.get("name") or r.get("displayTitle") or "run")} '
                    f'<span class="live-dim">{esc(str(r.get("headSha") or "")[:7])} · '
                    f'{esc(str(r.get("createdAt") or "")[:16])}</span></span>'
                    + (f' <a class="live-link" href="{esc(r.get("url"))}">open</a>' if r.get("url") else "")
                    + '</li>')
    for g in m.get("gates") or []:
        rows.append(f'<li><span class="live-k">gate {esc(g.get("id"))}</span> '
                    f'<span class="live-v">{esc(g.get("reason") or "")}'
                    f'{" · run " + esc(g.get("await_id")) if g.get("await_id") else " · no run matched yet (bd gate discover)"}'
                    f'{" · blocks " + esc(g.get("blocks")) if g.get("blocks") else ""}</span> '
                    f'{act_button("gate-check", "gh:run", "check")}</li>')
    for e in m.get("errors") or []:
        rows.append(f'<li><span class="live-k is-bad">gh</span> <span class="live-v">{esc(e)}</span></li>')
    return ('<section class="live-block" id="live-ci"><h2 class="panel-h">ci</h2>'
            f'<p class="live-empty">branch {esc(m.get("branch") or "?")} · fetched {esc((m.get("fetched_at") or "")[11:19])} · via gh</p>'
            + (f'<ul>{"".join(rows)}</ul>' if rows else '<p class="live-empty">no run on this branch.</p>')
            + '</section>')


# --------------------------------------------------------------------------- #
# actions — the panel writes through the CLIs, never around them (phase 49)
# --------------------------------------------------------------------------- #
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*-[A-Za-z0-9.]+$")
LEASE_KEY_RE = re.compile(r"^(\d+|bead:[A-Za-z][A-Za-z0-9_.-]*-[A-Za-z0-9.]+)$")
MIRROR_VERB = {"claim": "update", "close": "close", "reopen": "update"}


def action_argv(root, action, ident, reason):
    """The exact CLI for one action, as an argv list — never a shell string.
    None means the request does not name a valid action; a (None, msg)
    pair is a refusal with its reason."""
    if action in ("claim", "close", "reopen"):
        if not ID_RE.match(ident or ""):
            return None, "id is not a bead id"
        if action == "claim":
            return ["bd", "-C", str(root), "update", ident, "--claim"], None
        if action == "close":
            if not (reason or "").strip():
                return None, "close needs a reason"
            return ["bd", "-C", str(root), "close", ident,
                    f"--reason={reason.strip()}"], None
        return ["bd", "-C", str(root), "update", ident, "--status", "open",
                "--assignee", ""], None
    if action == "gate-check":
        gtype = (reason or "gh:run").strip()
        if not re.match(r"^[a-z:]+$", gtype):
            return None, "gate type is not a type"
        return ["bd", "-C", str(root), "gate", "check", f"--type={gtype}"], None
    if action == "gate-resolve":
        if not ID_RE.match(ident or ""):
            return None, "id is not a gate id"
        if not (reason or "").strip():
            return None, "resolving a gate needs a reason"
        return ["bd", "-C", str(root), "gate", "resolve", ident,
                f"--reason={reason.strip()}"], None
    if action == "lease-release":
        if not LEASE_KEY_RE.match(ident or ""):
            return None, "lease key is neither a phase number nor bead:<id>"
        return [sys.executable, CAIRN_LEASE, "release", ident,
                "--project-dir", str(root)], None
    if action == "stop-clear":
        return [sys.executable, CAIRN_STOP, "clear", "--project-dir", str(root)], None
    if action == "stop":
        # Phase 50: the flag the loop honours at its next boundary — and the
        # lease goes too (the grilling's contract), so the front is free.
        if ident and not LEASE_KEY_RE.match(ident):
            return None, "stop target is neither a phase number nor bead:<id>"
        argv = [sys.executable, CAIRN_STOP, "request", "--actor", "board",
                "--reason", (reason or "requested from the board").strip(),
                "--project-dir", str(root)]
        if ident:
            argv += ["--phase", ident]
        return argv, None
    return None, f"unknown action {action!r}"


def run_action(root, snapshot, action, ident, reason):
    argv, err = action_argv(root, action, ident, reason)
    if argv is None:
        return {"ok": False, "action": action, "id": ident, "error": err}, 400
    env = dict(os.environ, BEADS_ACTOR="board", CLAUDE_PROJECT_DIR=str(root))
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              cwd=str(root), env=env, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "action": action, "id": ident,
                "error": f"could not run: {exc}"}, 500
    result = {"ok": proc.returncode == 0, "action": action, "id": ident,
              "exit": proc.returncode, "stdout": (proc.stdout or "")[-1200:],
              "stderr": (proc.stderr or "")[-1200:], "mirror": None}
    if result["ok"] and action == "stop" and ident:
        rel = subprocess.run([sys.executable, CAIRN_LEASE, "release", ident,
                              "--project-dir", str(root)],
                             capture_output=True, text=True, cwd=str(root),
                             env=env, timeout=60)
        result["lease_released"] = rel.returncode == 0
    # The post-bd-write hook only sees the session's own `bd` commands: a
    # write from this process mirrors itself, explicitly, when a sync
    # config exists. Never fatal — the bead write is the fact.
    verb = MIRROR_VERB.get(action)
    if result["ok"] and verb and (root / ".cairn" / "sync.json").is_file():
        try:
            m = subprocess.run(["bash", CAIRN_GBSYNC, verb, ident, "--dir",
                                str(root)], capture_output=True, text=True,
                               cwd=str(root), timeout=120)
            tail = (m.stdout or m.stderr).strip().splitlines()
            result["mirror"] = {"ok": m.returncode == 0,
                                "detail": tail[-1] if tail else ""}
        except (OSError, subprocess.SubprocessError) as exc:
            result["mirror"] = {"ok": False, "detail": str(exc)}
    with open(root / ".cairn" / "board.log", "a", encoding="utf-8") as fh:
        fh.write(f"{now_iso()} action {action} {ident or '-'} exit "
                 f"{proc.returncode} actor board\n")
    snapshot.fetched_at = 0.0    # the next read sees the write
    return result, (200 if result["ok"] else 409)


def same_origin(headers, port):
    """ACT-02 (no token by decision): the bind is the loopback, and a POST
    has to come from THIS page — Origin, when the browser sends one, must
    be this port on 127.0.0.1 or localhost, and Host must name the same. A
    page served from anywhere else, on any other port, gets 403. A local
    curl without Origin is the operator and passes."""
    allowed = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    host = (headers.get("Host") or "").strip()
    if host not in allowed:
        return False
    origin = (headers.get("Origin") or "").strip()
    if origin and origin not in {f"http://{h}" for h in allowed}:
        return False
    return True


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
            path = self.path.split("?", 1)[0]
            if path != "/api/action":
                return self.send(405, "only POST /api/action writes\n")
            port = self.server.server_address[1]
            if not same_origin(self.headers, port):
                return self.send(403, json.dumps({"ok": False, "error":
                                 "origin or host is not this board"}),
                                 "application/json; charset=utf-8")
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, OSError):
                return self.send(400, json.dumps({"ok": False, "error": "bad JSON"}),
                                 "application/json; charset=utf-8")
            if not isinstance(body, dict):
                return self.send(400, json.dumps({"ok": False, "error": "bad JSON"}),
                                 "application/json; charset=utf-8")
            result, code = run_action(root, snapshot, str(body.get("action") or ""),
                                      str(body.get("id") or ""),
                                      str(body.get("reason") or ""))
            return self.send(code, json.dumps(result),
                             "application/json; charset=utf-8")

        def do_PUT(self):
            self.send(405, "only POST /api/action writes\n")

        do_DELETE = do_PATCH = do_PUT

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/healthz":
                return self.send(200, "ok\n")
            if path == "/favicon.ico":
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
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
            if path == "/api/trend":
                return self.send(200, json.dumps(trend_model(root)),
                                 "application/json; charset=utf-8")
            if path == "/api/ci":
                return self.send(200, json.dumps(ci_model(root)),
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
    """The page: status-board.html itself (one renderer, one CSS), its
    generated region filled with the fragment plus the live blocks, the
    live CSS added to the head, the status line and the poller added to
    the body. The static --html file and this page share every byte of
    board markup; only the script differs."""
    data, fragment, error, fetched_at = snapshot.current()
    try:
        page = TEMPLATE.read_text(encoding="utf-8")
    except OSError:
        return f"<p>{error or 'board template missing'}</p>"
    body = (fragment + live_blocks(root, data) if data is not None
            else f'<p class="placeholder">{esc(error)}</p>')
    start, end = page.find(BOARD_START), page.find(BOARD_END)
    if start >= 0 and end > start:
        page = page[:start + len(BOARD_START)] + "\n" + body + "\n" + page[end:]
    stamp = datetime.fromtimestamp(fetched_at).strftime("%H:%M:%S") if fetched_at else "--:--:--"
    status_line = (f'<p class="live-status" id="live-status" data-at="{stamp}">'
                   f'observed {stamp}</p>')
    page = page.replace("<title>cairn: status board</title>",
                        "<title>cairn: live board</title>", 1)
    page = page.replace("</head>", LIVE_CSS + "</head>", 1)
    page = page.replace('<main class="sheet">', status_line + '\n<main class="sheet">', 1)
    page = page.replace("</body>", LIVE_JS + "</body>", 1)
    return page


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
