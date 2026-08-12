"""Identity that a tracked file may carry (CairnGo-xclf).

This repository publishes two files that are git-tracked BY DESIGN: the
per-checkout journal partitions under `.cairn/journal/` (phase 28) and the
beads export `.beads/issues.jsonl` (phase 36's `issues-recoverable`). Both
are read by every clone, every fork and every mirror of a PUBLIC
repository, so whatever a writer puts in them is published.

Three values were being published, all measured on this checkout before
this module existed:

  - `socket.gethostname()` as the journal record's `machine` and as the
    lease's `host`. On the checkout where this was measured that hostname
    carried its owner's given name, which is the ordinary case on a
    personal machine, not an unlucky one;
  - the same hostname, sanitized, as the FILENAME half of a journal
    partition slug;
  - `git rev-parse --show-toplevel` as the lease's `holder`: an absolute
    path whose second segment is the operating-system user's name.

  (The measured values are deliberately not reproduced here. A docstring
  that quotes them as evidence republishes them in the same tracked tree
  it exists to clean — the defect wearing the costume of its own fix.)

What those values are FOR is distinguishing, never naming. The journal
needs to tell two machines apart; it never needs to say which. The lease
needs to tell a human which checkout holds it, and to compare two holders
for equality; the home prefix serves neither.

So this module supplies the two narrow conversions, and nothing else:

  machine_id()   a hostname becomes a stable 12-hex digest. Distinct
                 between machines, identical across runs on one machine,
                 and it names nobody.
  collapse_home()  an absolute path under $HOME becomes ~-prefixed. A path
                 outside $HOME is returned untouched — a temp dir in a
                 test is not identity, and rewriting it would break the
                 equality the lease depends on for no gain.

Deliberately NOT done here, and each for a measured reason:

  - `resolve_checkout()` in cairn-journal.py keeps folding the RAW
    hostname into its sha256. That hash is the partition key and is
    already opaque; hashing a digest instead would change every existing
    checkout id and fragment history to buy nothing.
  - the env seams (`CAIRN_JOURNAL_MACHINE` and friends) are untouched.
    Every test that drives two simulated machines out of one directory
    sets them, so this module's default-path change is invisible to the
    suite — verified: `tests/cairn-journal.bats` mentions a real hostname
    only in two comments, and no test asserts the lease's `host` at all.
  - records already written are NOT rewritten from here. Scrubbing is a
    one-shot data migration, and a writer that keeps producing the value
    would undo it — which is exactly what the doctor's `export-identity`
    check reports as a warn rather than a fail."""

import hashlib
import os

# Same width as phase 28's checkout id. Enough to make a collision between
# two machines a non-event, short enough to read in a filename.
_MACHINE_ID_HEX = 12


def machine_id(machine):
    """MACHINE as a stable, non-identifying 12-hex digest.

    None or empty in, None out: a provenance value that could not be
    measured is UNKNOWN, and unknown has its own representation. This is
    the same rule resolve_machine() already applies — inventing a string
    here would turn "we do not know" into "we know, and it is this"."""
    if not machine:
        return None
    return hashlib.sha256(machine.encode("utf-8")).hexdigest()[:_MACHINE_ID_HEX]


def collapse_home(path, home=None):
    """PATH with a leading $HOME replaced by `~`.

    Returned untouched when it does not start with $HOME, when $HOME is
    unset, or when $HOME is `/` (a degenerate value that would rewrite
    every absolute path on the system into a tilde)."""
    if path is None:
        return None
    text = str(path)
    base = home if home is not None else os.environ.get("HOME")
    if not base or base == "/":
        return text
    base = base.rstrip("/")
    if text == base:
        return "~"
    if text.startswith(base + "/"):
        return "~" + text[len(base):]
    return text
