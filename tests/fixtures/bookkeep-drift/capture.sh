#!/usr/bin/env bash
# capture.sh — the ONLY writer of tests/fixtures/bookkeep-drift/*.
#
# Those files are a byte-for-byte copy of THIS repository's own .planning/
# ROADMAP.md, REQUIREMENTS.md and STATE.md, frozen while they still disagree
# with each other. The disagreement is the test input for cairn-bookkeep.py:
# a command that only ever runs against a synthetic fixture proves it can
# write, not that it can RESOLVE drift (29-CONTEXT.md, D-02).
#
# Run this ONLY when freezing a new state is INTENTIONAL and reviewed. It
# ends by printing `git diff --stat` of what it rewrote — that diff is the
# point. Read it, and commit it as its own visible act. A red bookkeep test
# is NOT a reason to run this script; it is a reason to find out what moved.
# Recapturing after someone tidies .planning/ turns the fixture into an empty
# proof, and every guard in tests/cairn-bookkeep.bats that names the disease
# will go red at once. That is the alarm working, not a test to relax.
#
# The inventory it writes into MANIFEST.md is measured HERE, by the small
# deliberately-dumb counters below — never by cairn-bookkeep.py. Two
# independent counts of the same files is the whole value: if this manifest
# and cairn-bookkeep reconcile ever disagree, that is a finding about one of
# them, not a bug in the fixture. (tests/cairn-bookkeep.bats hardcodes the
# anchors instead of reading them back from this manifest — a test that reads
# its expectations from a file this script rewrites would go green again the
# moment someone recaptured a tidied repo.)
#
# Needs python3 (stdlib only) and git. Does not need bd.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$(dirname "$HERE")")"
REPO_ROOT="$(dirname "$TESTS_DIR")"
PLANNING="$REPO_ROOT/.planning"

for name in ROADMAP REQUIREMENTS STATE; do
  if [ ! -f "$PLANNING/$name.md" ]; then
    echo "capture.sh: $PLANNING/$name.md not found" >&2
    exit 1
  fi
done

echo "freezing tests/fixtures/bookkeep-drift/ from $PLANNING:"
for name in ROADMAP REQUIREMENTS STATE; do
  cp "$PLANNING/$name.md" "$HERE/$name.md"
  echo "  copied $name.md ($(wc -c < "$HERE/$name.md" | tr -d ' ') bytes)"
done

python3 - "$HERE" "$REPO_ROOT" <<'PY'
import hashlib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

here = Path(sys.argv[1])
root = Path(sys.argv[2])
planning = root / ".planning"

COPIED = ["ROADMAP.md", "REQUIREMENTS.md", "STATE.md"]
REQ_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-\d+")
PHASE_DIR = re.compile(r"^(?:[A-Za-z0-9]+-)?0*(\d+)-")


def head():
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else "(no HEAD)"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- phases.tsv: one row per phase dir, counted by NAME, never by content ---
rows = []
for d in sorted((planning / "phases").iterdir()):
    if not d.is_dir():
        continue
    rows.append((d.name,
                 len(list(d.glob("*-PLAN.md"))),
                 len(list(d.glob("*-SUMMARY.md"))),
                 1 if list(d.glob("*-VERIFICATION.md")) else 0))
tsv = ["# phase_dir\tplans\tsummaries\thas_verification",
       "# Counted by capture.sh from .planning/phases/. make_drift_fixture",
       "# rebuilds the tree from these counts with EMPTY files of the right",
       "# names — every counter under test counts names, not content."]
tsv += ["\t".join(str(c) for c in r) for r in rows]
(here / "phases.tsv").write_text("\n".join(tsv) + "\n", encoding="utf-8")

# --- the independent inventory ---
roadmap = (planning / "ROADMAP.md").read_text(encoding="utf-8").splitlines()
reqs = (planning / "REQUIREMENTS.md").read_text(encoding="utf-8").splitlines()
state = (planning / "STATE.md").read_text(encoding="utf-8").splitlines()

# requirements, by section
section = None
active, deferred, out_of_scope = [], [], []
for line in reqs:
    m = re.match(r"^##\s+(.*)", line)
    if m:
        section = m.group(1).strip()
        continue
    m = re.match(r"^\s*-\s*\[([ xX])\]\s*\*\*([A-Za-z][A-Za-z0-9]*-\d+)\*\*",
                 line)
    if not m:
        m2 = re.match(r"^\s*-\s*\*\*([A-Za-z][A-Za-z0-9]*-\d+)\*\*", line)
        if m2:
            entry = (m2.group(1), None)
        else:
            continue
    else:
        entry = (m.group(2), m.group(1))
    if section and section.lower().endswith("requirements"):
        active.append(entry)
    elif section and section.lower().startswith("deferred"):
        deferred.append(entry)
    elif section and section.lower().startswith("out of scope"):
        out_of_scope.append(entry)

# coverage table + footer, anchored to the coverage heading
cov_start = None
for i, line in enumerate(roadmap):
    if re.match(r"^##\s+(Cobertura|Coverage)\b", line):
        cov_start = i
if cov_start is None:
    raise SystemExit("capture.sh: no coverage section in ROADMAP.md")
cov_rows, footer_claim, footer_line = [], None, None
for line in roadmap[cov_start + 1:]:
    if re.match(r"^##\s", line):
        break
    m = re.match(r"^\|\s*([A-Za-z][A-Za-z0-9]*-\d+)\s*\|\s*([^|]+?)\s*\|"
                 r"\s*([^|]+?)\s*\|", line)
    if m:
        cov_rows.append((m.group(1), m.group(2), m.group(3)))
        continue
    m = re.match(r"^(\d+)\s+requisitos?,\s*(\d+)\s+mapeados?", line.strip())
    if m:
        footer_claim = (int(m.group(1)), int(m.group(2)))
        footer_line = line.strip()

cov_ids = [r[0] for r in cov_rows]
missing = [rid for rid, _ in active if rid not in cov_ids]

# phase checkbox lines + the per-phase Requirements line
checkbox = re.compile(r"^\s*-\s*\[([ xX])\]\s.*?\bPhase\s+0*(\d+)\b")
phases = []
for line in roadmap:
    m = checkbox.match(line)
    if m:
        phases.append((int(m.group(2), 10), m.group(1).lower() == "x"))

req_lines = {}
cur = None
for line in roadmap:
    m = re.match(r"^#{1,6}\s+Phase\s+0*(\d+)\b", line)
    if m:
        cur = int(m.group(1), 10)
        continue
    if re.match(r"^#{1,6}\s", line):
        cur = None
    if cur is not None:
        m = re.match(r"^\*\*Requirements\*\*\s*:(.*)$", line.strip())
        if m and cur not in req_lines:
            req_lines[cur] = (line.strip(), REQ_ID.findall(m.group(1)))

# STATE frontmatter, and only the frontmatter — the prose body is never read
fm, in_fm, in_progress = {}, False, False
for i, line in enumerate(state):
    if line.strip() == "---":
        if i == 0:
            in_fm = True
            continue
        if in_fm:
            break
    if not in_fm:
        continue
    if re.match(r"^progress:\s*$", line):
        in_progress = True
        continue
    m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
    if m:
        key, val = m.group(2), m.group(3).strip()
        if m.group(1) and in_progress:
            fm[f"progress.{key}"] = val
        else:
            in_progress = False
            fm[key] = val

disk_plans = sum(r[1] for r in rows)
disk_summaries = sum(r[2] for r in rows)

lines = []
w = lines.append
w("# bookkeep-drift — the frozen disagreement")
w("")
w(f"**Captured:** {date.today().isoformat()}  ")
w(f"**From:** `.planning/` of this repository at `{head()}`  ")
w("**Writer:** `capture.sh` in this directory. Nothing else writes these "
  "files, and no test ever calls it.")
w("")
w("**NOTHING BELOW IS TO BE FIXED IN THE FIXTURE.** Every line of this "
  "inventory is test input: `cairn-bookkeep.py reconcile` has to NAME each "
  "one. Tidying a file here deletes the only realistic input this command "
  "has, and a command that only meets consistent files proves it can write, "
  "never that it can resolve drift.")
w("")
w("The counts below were measured by `capture.sh` itself, with its own "
  "deliberately dumb counters — never by `cairn-bookkeep.py`. Two "
  "independent counts of the same bytes is the point: if this manifest and "
  "`reconcile` disagree, that is a finding about one of them.")
w("")
w("## Frozen files")
w("")
w("| File | Bytes | sha256 |")
w("|------|-------|--------|")
for name in COPIED:
    p = here / name
    w(f"| `{name}` | {len(p.read_bytes())} | `{sha256(p)}` |")
w("")
w("`phases.tsv` is not hashed: it is a derived index of "
  ".planning/phases/, rewritten by this script alongside the copies.")
w("")
w("## The disagreement inventory")
w("")
w(f"1. **{len(active)} active requirements** in REQUIREMENTS.md's milestone "
  f"section, of which {len([r for r, c in active if c and c.lower() == 'x'])}"
  " carry a checked box.")
w(f"2. **{len(cov_rows)} rows** in the ROADMAP coverage table — "
  f"{len(missing)} active requirement(s) have no row at all: "
  f"{', '.join(f'`{m}`' for m in missing) or 'none'}.")
if footer_claim:
    w(f"3. The coverage footer asserts `{footer_line}` — a claim of "
      f"{footer_claim[0]} against {len(cov_rows)} actual rows and "
      f"{len(active)} actual active requirements. Neither number is right, "
      "and they are wrong for different reasons.")
else:
    w("3. No coverage footer line found.")
w(f"4. **Deferred, and NOT a disagreement:** "
  f"{', '.join(f'`{r}`' for r, _ in deferred) or 'none'} lives under a "
  "deferred heading and is out of the table by rule. An explained absence "
  "is not drift — but silencing it would repeat the same defect in the "
  "other direction, so `reconcile` reports it under `requirements.deferred`.")
board = [c for r, c in active if r == "BOARD-01"]
if board:
    w(f"5. **`BOARD-01`** is `- [{board[0]}]` in REQUIREMENTS.md and "
      "`Complete` in the coverage table, while the phase that carries it is "
      "already checked off in the phase list.")
if 29 in req_lines:
    raw, ids = req_lines[29]
    w(f"6. **The sharpest one: phase 29's requirements line is an "
      f"ellipsis.** It reads `{raw}`, and an id scan over it yields "
      f"{len(ids)} ids — {', '.join(f'`{i}`' for i in ids)} — not the eight "
      "the prose means. There is no readable source of phase 29's "
      "requirements inside the ROADMAP today. Two tools already answer `ok` "
      "over that silence: `cairn-doctor req-issue` reports "
      f"`{sum(len(v[1]) for v in req_lines.values())} requirement(s) mapped` "
      "(the sum of every phase's parsed ids), and `29-BEADS-MAP.md` says "
      "`None — every phase requirement is mapped`. Note the coincidence, "
      "because it is how this survives: that total happens to equal the "
      "wrong footer's number, from an unrelated cause.")
w(f"7. **STATE.md frontmatter vs the disk.** `progress.total_plans: "
  f"{fm.get('progress.total_plans')}` and `progress.completed_plans: "
  f"{fm.get('progress.completed_plans')}` against {disk_plans} `*-PLAN.md` "
  f"and {disk_summaries} `*-SUMMARY.md` actually on disk. The phase pair "
  f"(`{fm.get('progress.completed_phases')}`/"
  f"`{fm.get('progress.total_phases')}`, percent "
  f"`{fm.get('progress.percent')}`) still agrees with the "
  f"{len(phases)} phase lines — that half of the arithmetic is the part "
  "D-01 keeps.")
w(f"8. **`last_activity_desc`** reads `{fm.get('last_activity_desc')}` "
  f"against {len(phases)} phases and {len(active)} active requirements. "
  "Free-text frontmatter nobody recalculates; `reconcile` reports it and "
  "does not propose to rewrite it.")
w("9. **The prose body of STATE.md contradicts its own frontmatter** — the "
  "body names an older phase and an archived milestone while the "
  f"frontmatter says `current_phase: {fm.get('current_phase')}`. That prose "
  "is the measured source of the `current_phase: 29 -> 18` corruption "
  "`state record-session` produced (29-CONTEXT.md, D-01). `reconcile` never "
  "reads the body, and a test asserts the older number appears nowhere in "
  "its computed output.")
plan_ck = [ln.strip() for ln in roadmap
           if re.match(r"^\s*-\s*\[ \]\s*\d+-\d+-PLAN\.md", ln)]
w(f"10. **{len(plan_ck)} plan checkbox line(s)** still read `- [ ]` in the "
  "phase detail blocks; some of them have a `*-SUMMARY.md` sitting next to "
  "them on disk.")
w("")
w("## Phase tree (`phases.tsv`)")
w("")
w("| Phase dir | `*-PLAN.md` | `*-SUMMARY.md` | verification |")
w("|-----------|-------------|----------------|--------------|")
for name, np, ns, hv in rows:
    w(f"| `{name}` | {np} | {ns} | {'yes' if hv else 'no'} |")
w("")
w("`make_drift_fixture` (tests/helpers.bash) rebuilds this tree with EMPTY "
  "files of the right names and commits the result, so the diff a write "
  "test measures has a denominator.")
w("")

(here / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")
print(f"  wrote phases.tsv ({len(rows)} phase dirs)")
print(f"  wrote MANIFEST.md ({len(lines)} lines)")
PY

echo
echo "review this diff before committing it:"
git -C "$REPO_ROOT" diff --stat -- tests/fixtures/bookkeep-drift/
# `diff --stat` says nothing about a file git has never seen, so a first
# capture would land in total silence. List those separately.
git -C "$REPO_ROOT" ls-files --others --exclude-standard \
  -- tests/fixtures/bookkeep-drift/ | sed 's/^/ untracked  /'
