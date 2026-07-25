# External Integrations

**Analysis Date:** 2026-07-25

## APIs & External Services

CairnGo's only "external services" are the five optional issue-tracker mirrors reached through the hub-and-spoke sync layer (`cairn/scripts/gbsync.py` dispatches to `cairn/adapters/*.py`), plus GSD and context-mode as sibling Claude Code plugins. bd (beads) itself is the hub — every other tool talks to bd, never to another tool directly (`cairn/adapters/_contract.md`).

**Issue tracker mirrors (all optional, `enabled: false` by default in `.cairn/sync.json`):**
- GitHub Issues - `cairn/adapters/github.py`
  - SDK/Client: shells out to the `gh` CLI (`subprocess.run(["gh", *args], ...)`); no direct HTTP calls, no token handling in-repo
  - Auth: delegated entirely to `gh auth status` (whatever the user's `gh` is authenticated as)
  - Config: `{"repo": "owner/name", "extra_labels": []}` under `.cairn/sync.json`
  - Status mapping: GitHub only has open/closed, so push maps `in_progress` → open (issue stays open), pull maps `OPEN` → open, `CLOSED` → closed
- GitLab Issues - `cairn/adapters/gitlab.py`
  - SDK/Client: raw HTTP via `urllib.request` against the GitLab REST API
  - Auth: env var named by `token_env` (default `GITLAB_TOKEN`)
  - Base URL: configurable (`base_url`, defaults to `https://gitlab.com`, supports self-hosted)
- Jira - `cairn/adapters/jira.py`
  - SDK/Client: raw HTTP via `urllib.request` against the Jira REST API
  - Auth: `email_env` (default `JIRA_EMAIL`) + `token_env` (default `JIRA_API_TOKEN`), Atlassian API token created at `id.atlassian.com`
  - Base URL: `base_url` (e.g. `https://yourorg.atlassian.net`), required config also includes `project_key`, `issue_type`, and a `transitions` status map
- Asana - `cairn/adapters/asana.py`
  - SDK/Client: raw HTTP via `urllib.request` against `https://app.asana.com/api/1.0`
  - Auth: env var named by `token_env` (default `ASANA_TOKEN`), a Personal Access Token from `app.asana.com/0/my-apps`
  - Config: `project_gid`
- Azure Boards - `cairn/adapters/azure-boards.py`
  - SDK/Client: raw HTTP via `urllib.request` against the Azure DevOps REST API
  - Auth: env var named by `pat_env` (default `AZURE_DEVOPS_PAT`), a Personal Access Token
  - Config: `org_url` (e.g. `https://dev.azure.com/yourorg`), `project`, `work_item_type`, `api_version`, `states` status map

**Sibling Claude Code plugins (not network APIs, but declared dependencies):**
- GSD (`jnuyens/gsd-plugin`, ≥1.8.0) - the planning/execution/verification workflow that cairn hooks into via capability contribution points (`plan:post`, `execute:wave:pre`, `execute:wave:post`, `verify:post`, `ship:pre`). Declared in `cairn/.claude-plugin/plugin.json` as a plugin dependency; sourced directly from upstream (not forked).
- context-mode (`mksglu/context-mode`) - optional cross-marketplace dependency providing `ctx_*` MCP tools for compressed memory; wired via `.cairn/context.json` (see `cairn/templates/context.json.example` and the `cairn-context` skill). `allowCrossMarketplaceDependenciesOn: ["context-mode"]` is declared in `.claude-plugin/marketplace.json`.

## Data Storage

**Databases:**
- Dolt (embedded, git-native SQL database) - the storage engine underneath `bd`/beads itself
  - Location: `.beads/embeddeddolt/` (local, per-machine)
  - `.beads/metadata.json`: `{"database": "dolt", "backend": "dolt", "dolt_mode": "embedded", "dolt_database": "CairnGo"}`
  - Sync/remote: `.beads/config.yaml` sets `sync.remote: "git+https://github.com/FelipeOFF/CairnGo.git"` — beads pushes/pulls its Dolt database over this git remote (`bd dolt push`/`bd dolt pull`), separate from the JSONL export
  - Cairn itself never talks to Dolt directly — always through the `bd` CLI's JSON output (`bd list --json`, `bd show --json`, etc.), per the adapter/test contract in `cairn/adapters/_contract.md` and `tests/README.md`
- JSONL - `.beads/issues.jsonl` (optional, disabled by default) - flat-file export/interchange format for beads issues, controlled by `export.auto`/`export.path` in `.beads/config.yaml`; `.beads/interactions.jsonl` also present for audit trail

**File Storage:**
- Local filesystem only. No object storage (S3/GCS/etc). Generated artifacts (`NN-BEADS-MAP.md`, `.cairn/id-map.json`, `.cairn/state.json`, `.cairn/conflicts.json`) are plain files written under the consuming project's own repo tree, not this plugin repo.

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None centralized. Each external integration authenticates independently and only at sync time:
  - GitHub: delegated to the user's existing `gh` CLI session (`gh auth status`)
  - GitLab / Jira / Asana / Azure Boards: bearer tokens/PATs read from environment variables named in the (committed, secret-free) `.cairn/sync.json` config — see `cairn/adapters/_contract.md` §"Secrets": "Never read or write secrets to disk. Each adapter reads its API token from an environment variable named in its config."
- No user-facing auth in this repo — it is a developer-tooling plugin, not an app with end users

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Bugsnag/etc.). Adapter failures are logged to stderr and the dispatcher (`gbsync.py`) continues with remaining backends; nonzero adapter exit codes are captured, not silently swallowed.

**Logs:**
- Plain stdout/stderr from bash and Python scripts; no structured logging framework or log aggregation. `.cairn/state.json` and `.cairn/conflicts.json` (both gitignored, per-machine) act as durable sync-run state rather than logs.

## CI/CD & Deployment

**Hosting:**
- No hosted service — this is a Claude Code plugin distributed via a git-based plugin marketplace (`.claude-plugin/marketplace.json` → `https://github.com/FelipeOFF/CairnGo`), installed into consuming projects with `/plugin marketplace add FelipeOFF/CairnGo` + `/plugin install cairn@cairngo`

**CI Pipeline:**
- GitHub Actions - `.github/workflows/ci.yml`, runs on `push` to `main` and on every `pull_request`, on `ubuntu-latest`:
  1. Checkout (`actions/checkout@v4`)
  2. Install `bd` (beads) via the upstream install script (`raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh`), adds `~/.local/bin` to `PATH`
  3. Install `bats-core` via `sudo npm install -g bats`
  4. Lint: `python3 -m py_compile cairn/scripts/*.py cairn/adapters/*.py cairn/capability/scripts/*.py`
  5. Test: `bd version && bats tests/`
- `.pr-autopilot/` directory present (per-PR automation state — `state.json`, `merge.json`, iteration review reports) suggesting an external PR-review automation tool runs against this repo, though no workflow/config for it is checked in under `.github/`

## Environment Configuration

**Required env vars (all optional, only needed if the corresponding sync backend is enabled):**
- `GITLAB_TOKEN` (configurable name via `token_env`)
- `JIRA_EMAIL`, `JIRA_API_TOKEN` (configurable names via `email_env`/`token_env`)
- `ASANA_TOKEN` (configurable name via `token_env`)
- `AZURE_DEVOPS_PAT` (configurable name via `pat_env`)
- `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`, `GSD_HOME` - Claude Code / GSD runtime environment, not secrets

**Secrets location:**
- Never stored in this repo. `.cairn/sync.json` (committed) holds only environment-variable *names*; actual token values live in the operator's shell/CI secrets. `.gitignore` additionally excludes generated per-machine sync state (`.cairn/id-map.json`, `.cairn/state.json`, `.cairn/conflicts.json`), which could otherwise leak external issue IDs/timestamps.

## Webhooks & Callbacks

**Incoming:**
- None. There is no HTTP server in this repo; all sync is pull/push initiated by the local `bd` lifecycle events (via Claude Code's `PostToolUse` hook, `cairn/hooks/post-bd-write.sh`) or explicit `/cairn:sync-pull` invocation — not by remote webhooks.

**Outgoing:**
- Effectively "outgoing calls" rather than webhooks: `cairn/hooks/post-bd-write.sh` fires a fire-and-forget mirror push after any `bd` create/claim/close, calling `cairn/scripts/gbsync.py`, which in turn calls the enabled adapter(s) in `cairn/adapters/`. No webhook registration/receiver pattern is used on either side.

---

*Integration audit: 2026-07-25*
