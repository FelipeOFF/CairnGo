#!/usr/bin/env bash
# bench-all.sh — the single documented command that reproduces the full
# benchmark run: stage-plugins.py -> bench-matrix.py -> bench-aggregate.py ->
# bench-chart.py -> bench-publish.py, in that exact order.
#
# Usage:
#   bench-all.sh [--dry-run | --yes]
#                [--seed <int>] [--tasks <spec>] [--baselines <name,name,...>]
#                [--baselines-dir <dir>] [--reps <N>] [--out <dir>]
#                [--charts-dir <dir>] [--benchmarks <path>] [--readme <path>]
#
# Modes (the safety contract):
#   default / --dry-run  Print the execution plan (resolved tasks, baselines,
#                        reps, total run count, dollar-cost ceiling) and exit 0
#                        WITHOUT invoking any downstream script. This is always
#                        the default, regardless of whether ANTHROPIC_API_KEY
#                        happens to be set — spend is never inferred from the
#                        environment.
#   --yes                The only path that can spend real money. Requires a
#                        non-empty ANTHROPIC_API_KEY (usage error otherwise,
#                        before anything is printed or invoked). Mutually
#                        exclusive with --dry-run.
#
# Flags and defaults:
#   --seed <int>         20260726 (the same fixed seed as the Variance pilot
#                        recipe in benchmarks/README.md — override for any
#                        other reproducible run)
#   --tasks <spec>       "benchmarks/tasks/*" (comma list or a single glob,
#                        passed through to bench-matrix.py verbatim)
#   --baselines <names>  "vanilla,gsd-only,cairn,competitor-ralph-specum"
#   --baselines-dir <d>  "benchmarks/baselines" (where <name>.json manifests
#                        live; passed through to bench-matrix.py)
#   --reps <N>           5
#   --out <dir>          "benchmarks/results" (matrix.jsonl + aggregated.json)
#   --charts-dir <dir>   "benchmarks/charts"
#   --benchmarks <path>  "BENCHMARKS.md" (must already exist)
#   --readme <path>      "README.md" (must already exist)
#
# Cost ceiling: the printed ~$40 figure restates the declared ceiling for one
# full 120-run matrix pass published in benchmarks/README.md's Cost model
# (worked example) and BENCHMARKS.md's Methodology/Reproduction sections. It
# is deliberately hardcoded — this script has no live pricing API and must
# never drift from (or re-derive) the published number.
#
# Exit codes: 0 ok; 2 usage error; otherwise the propagated exit code of
# whichever pipeline step failed first (set -e aborts the sequence
# immediately — this script is an orchestrator, not a new numeric contract).
#
# Seams:
#   CAIRN_BENCH_SCRIPTS_DIR  where the five downstream scripts are resolved
#                            (default: this script's own directory). Lets
#                            tests point the orchestrator at stubs.
#   CAIRN_BENCH_CLAUDE_BIN   honored downstream by bench-run.py (the claude
#                            binary seam — never read here directly).
#
# NEVER wire this script into .github/workflows/ci.yml or any other
# automated, scheduled, or on-push trigger. It is a deliberately manual,
# operator-invoked command: the --yes path spends real money, and the plan
# print above is the operator's last chance to abort. tests/bench-all.bats
# mechanically enforces that no GitHub workflow references this script.
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${CAIRN_BENCH_SCRIPTS_DIR:-$SELF_DIR}"

USAGE="usage: bench-all.sh [--dry-run | --yes] [--seed <int>] [--tasks <spec>]
                   [--baselines <name,name,...>] [--baselines-dir <dir>]
                   [--reps <N>] [--out <dir>] [--charts-dir <dir>]
                   [--benchmarks <path>] [--readme <path>]"

die_usage() {
  echo "[bench-all] error: $1" >&2
  echo "$USAGE" >&2
  exit 2
}

need_value() {
  # $1 = flag name, $2 = number of remaining args
  [ "$2" -ge 2 ] || die_usage "$1 needs a value"
}

MODE=""
SEED=20260726
TASKS="benchmarks/tasks/*"
BASELINES="vanilla,gsd-only,cairn,competitor-ralph-specum"
BASELINES_DIR="benchmarks/baselines"
REPS=5
OUT="benchmarks/results"
CHARTS_DIR="benchmarks/charts"
BENCHMARKS_PATH="BENCHMARKS.md"
README_PATH="README.md"
COST_CEILING='~$40'

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)
      [ "$MODE" = "yes" ] && die_usage "--dry-run and --yes are mutually exclusive"
      MODE="dry-run"; shift ;;
    --yes)
      [ "$MODE" = "dry-run" ] && die_usage "--dry-run and --yes are mutually exclusive"
      MODE="yes"; shift ;;
    --seed)
      need_value --seed $#
      case "$2" in (*[!0-9]*|'') die_usage "--seed must be an integer, got '$2'" ;; esac
      SEED="$2"; shift 2 ;;
    --tasks)
      need_value --tasks $#; TASKS="$2"; shift 2 ;;
    --baselines)
      need_value --baselines $#; BASELINES="$2"; shift 2 ;;
    --baselines-dir)
      need_value --baselines-dir $#; BASELINES_DIR="$2"; shift 2 ;;
    --reps)
      need_value --reps $#
      case "$2" in (*[!0-9]*|'') die_usage "--reps must be an integer, got '$2'" ;; esac
      REPS="$2"; shift 2 ;;
    --out)
      need_value --out $#; OUT="$2"; shift 2 ;;
    --charts-dir)
      need_value --charts-dir $#; CHARTS_DIR="$2"; shift 2 ;;
    --benchmarks)
      need_value --benchmarks $#; BENCHMARKS_PATH="$2"; shift 2 ;;
    --readme)
      need_value --readme $#; README_PATH="$2"; shift 2 ;;
    *)
      die_usage "unknown option '$1'" ;;
  esac
done

# Mode resolution: the safe default is ALWAYS dry-run — spend requires an
# explicit --yes, never an inference from the environment.
[ -z "$MODE" ] && MODE="dry-run"

if [ "$MODE" = "yes" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  # Die BEFORE printing the plan or invoking anything: --yes is the spend
  # path and spend is never attempted without a key.
  die_usage "--yes requires ANTHROPIC_API_KEY to be set (non-empty) in the environment"
fi

# Resolve counts for the plan print. Task count: glob-expand when the spec
# contains '*', else count comma-separated entries.
TASK_COUNT=0
if [ "${TASKS#*'*'}" != "$TASKS" ]; then
  for d in $TASKS; do
    [ -d "$d" ] && TASK_COUNT=$((TASK_COUNT + 1))
  done
else
  OLD_IFS="$IFS"; IFS=','
  for t in $TASKS; do
    [ -n "$t" ] && TASK_COUNT=$((TASK_COUNT + 1))
  done
  IFS="$OLD_IFS"
fi

BASELINE_NAMES=()
OLD_IFS="$IFS"; IFS=','
for b in $BASELINES; do
  [ -n "$b" ] && BASELINE_NAMES+=("$b")
done
IFS="$OLD_IFS"
BASELINE_COUNT="${#BASELINE_NAMES[@]}"
[ "$BASELINE_COUNT" -gt 0 ] || die_usage "--baselines needs at least one baseline name"

TOTAL_RUNS=$((TASK_COUNT * BASELINE_COUNT * REPS))

if [ "$MODE" = "dry-run" ]; then
  MODE_LABEL="DRY-RUN"
else
  MODE_LABEL="LIVE"
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  KEY_PRESENT="yes"   # presence only — the value is never printed
else
  KEY_PRESENT="no"
fi

# The plan is ALWAYS printed first, in both modes: it is the operator's last
# chance to abort before any spend.
echo "[bench-all] execution plan"
echo "  mode:          $MODE_LABEL"
echo "  tasks:         $TASKS ($TASK_COUNT task dir(s))"
echo "  baselines:     $BASELINES ($BASELINE_COUNT arm(s))"
echo "  baselines-dir: $BASELINES_DIR"
echo "  reps:          $REPS"
echo "  seed:          $SEED"
echo "  total_runs:    $TOTAL_RUNS ($TASK_COUNT tasks x $BASELINE_COUNT baselines x $REPS reps)"
echo "  cost ceiling:  $COST_CEILING for the full 120-run matrix (declared in benchmarks/README.md Cost model and BENCHMARKS.md — restated, never recomputed)"
echo "  ANTHROPIC_API_KEY present: $KEY_PRESENT"

if [ "$MODE" = "dry-run" ]; then
  echo "[bench-all] dry-run: no downstream script invoked, \$0 spent"
  exit 0
fi

# ---- LIVE path: the only lines below that can spend money ----

FIRST_BASELINE="${BASELINE_NAMES[0]}"
FIRST_MANIFEST="$BASELINES_DIR/$FIRST_BASELINE.json"
[ -f "$FIRST_MANIFEST" ] || die_usage "baseline manifest not found: $FIRST_MANIFEST"
MODEL="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["model"])' "$FIRST_MANIFEST")"
LABEL="$MODEL - $(date -u +%Y-%m-%d)"

mkdir -p "$OUT"

# set -e aborts the whole pipeline on the first non-zero exit — no manual
# per-step checks needed.
STEP_TOTAL=$((4 + BASELINE_COUNT))
STEP=0
for name in "${BASELINE_NAMES[@]}"; do
  STEP=$((STEP + 1))
  echo "[bench-all] step $STEP/$STEP_TOTAL: stage-plugins ($name)"
  python3 "$SCRIPTS_DIR/stage-plugins.py" --baseline "$BASELINES_DIR/$name.json"
done

STEP=$((STEP + 1))
echo "[bench-all] step $STEP/$STEP_TOTAL: bench-matrix"
python3 "$SCRIPTS_DIR/bench-matrix.py" \
  --tasks "$TASKS" \
  --baselines "$BASELINES" \
  --baselines-dir "$BASELINES_DIR" \
  --out "$OUT/matrix.jsonl" \
  --seed "$SEED" \
  --reps "$REPS"

STEP=$((STEP + 1))
echo "[bench-all] step $STEP/$STEP_TOTAL: bench-aggregate"
python3 "$SCRIPTS_DIR/bench-aggregate.py" \
  --in "$OUT/matrix.jsonl" \
  --out "$OUT/aggregated.json"

STEP=$((STEP + 1))
echo "[bench-all] step $STEP/$STEP_TOTAL: bench-chart"
python3 "$SCRIPTS_DIR/bench-chart.py" \
  --in "$OUT/aggregated.json" \
  --out-dir "$CHARTS_DIR" \
  --label "$LABEL"

STEP=$((STEP + 1))
echo "[bench-all] step $STEP/$STEP_TOTAL: bench-publish"
python3 "$SCRIPTS_DIR/bench-publish.py" \
  --in "$OUT/aggregated.json" \
  --benchmarks "$BENCHMARKS_PATH" \
  --label "$LABEL" \
  --readme "$README_PATH"

echo "[bench-all] done: results in $OUT, charts in $CHARTS_DIR." \
     "Reminder: total_cost_usd is Anthropic's own client-side estimate, never authoritative billing data."
