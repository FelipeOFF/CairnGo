# Planner — Load Graph Context

> Loaded by `gsd-planner` at the `load_graph_context` step.

Check for knowledge graph:

```bash
ls "${PLANNING_DIR}"/graphs/graph.json 2>/dev/null
```

If graph.json exists, check freshness:

```bash
CAIRN_GSD="${CAIRN_GSD:-}"; if [ ! -x "$CAIRN_GSD" ]; then _cg_try=""; for _cg_root in "${CLAUDE_PROJECT_DIR:-}" "$(git rev-parse --show-toplevel 2>/dev/null || true)" "$PWD"; do [ -n "$_cg_root" ] || continue; _cg_try="$_cg_root/cairn/scripts/cairn-gsd.sh"; if [ -x "$_cg_try" ]; then CAIRN_GSD="$_cg_try"; break; fi; done; fi; if [ ! -x "${CAIRN_GSD:-}" ]; then echo "ERROR: cairn-gsd.sh not found (last path tried: ${_cg_try:-<none>}) - this workflow speaks to the cairn dispatcher that lives in the repo. Run it from inside the CairnGo checkout, or export CAIRN_GSD=<checkout>/cairn/scripts/cairn-gsd.sh" >&2; exit 1; fi; export CAIRN_GSD; gsd_run() { "$CAIRN_GSD" "$@"; }
gsd_run graphify status
```

If the status response has `stale: true`, note for later: "Graph is {age_hours}h old -- treat semantic relationships as approximate." Include this annotation inline with any graph context injected below.

If the response instead carries `available: false` with a `reason`, the graph subsystem is not implemented in this installation. That payload is a DECLARED unavailability — it exits 0, so nothing failed and nothing is silent. Note the reason in the same place the freshness annotation would have gone, skip the query below (it answers the same payload), and take the branch this step already had for an absent graph.json: continue without graph context. The decision not to implement the subsystem is recorded in `tests/fixtures/gsd-goldens/divergences.json` under the `graphify` verb.

Query the graph for phase-relevant dependency context (single query per D-06):

```bash
gsd_run graphify query "<phase-goal-keyword>" --budget 2000
```

Use the keyword that best captures the phase goal. Examples:
- Phase "User Authentication" -> query term "auth"
- Phase "Payment Integration" -> query term "payment"
- Phase "Database Migration" -> query term "migration"

If the query returns nodes and edges, incorporate as dependency context for planning:
- Which modules/files are semantically related to this phase's domain
- Which subsystems may be affected by changes in this phase
- Cross-document relationships that inform task ordering and wave structure

If no results or graph.json absent, continue without graph context.
