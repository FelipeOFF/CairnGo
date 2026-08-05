#!/usr/bin/env bats
# cairn-jira.bats — the decision to ask about Jira, and the record of both
# answers (cairn-jira.py / cairn-jira.sh):
#   - a repo with no signal is never asked (`ask:false`, reason "no signal");
#   - a recorded answer, yes OR no, stops the question coming back, and the
#     reason names which answer it was;
#   - `apply` writes the jira backend into .cairn/sync.json with the EXACT
#     documented field set and env var NAMES, never a credential, deriving the
#     site from an atlassian.net remote so nobody types anything;
#   - `apply` with no derivable site refuses rather than writing a placeholder;
#   - the `mcp` signal is "DECLARED in a config file", never "connected":
#     .mcp.json declaring an Atlassian server is declared:true, and a
#     ~/.claude.json carrying ONLY .claudeAiMcpEverConnected is declared:false;
#   - a malformed third-party .mcp.json degrades to "not declared" instead of
#     taking detection down with it;
#   - detection itself is never reimplemented here — it comes from
#     cairn-migrate.py detect --json, and killing that detector is exit 5.
#
# HOME is pinned to an empty dir in every test: `mcp` is read from
# ~/.claude.json, and a contributor's own MCP config must not decide a test.
#
# Assertion style note: substring checks use grep -qF and exact checks use
# `[ ]` (a failing `[[ ]]` mid-test does not fail a bats test on this bash).

load 'helpers'

JIRA_SH="$CAIRN_SCRIPTS_DIR/cairn-jira.sh"
CONFIG_SH="$CAIRN_SCRIPTS_DIR/cairn-config.sh"

setup() {
  FAKE_HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$FAKE_HOME"
}

# cairn-jira.sh with HOME pinned, in the repo made by make_tmp_repo.
JIRA() { env HOME="$FAKE_HOME" bash "$JIRA_SH" "$@"; }

# A repo whose history names a Jira key in three commits AND a branch, so the
# weak-signal guard in cairn-migrate.py's detect_jira is satisfied.
seed_jira_signals() {
  git commit -q --allow-empty -m "DTP-101: wire the login flow"
  git commit -q --allow-empty -m "DTP-102: and its tests"
  git commit -q --allow-empty -m "DTP-103 hotfix"
  git branch DTP-104-refresh-tokens
}

@test "a repo with no signal at all is never asked" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  git commit -q --allow-empty -m "chore: nothing that looks like a tracker"

  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ask' "false"
  assert_json_eq "$output" '.reason' "no signal"
  assert_json_eq "$output" '.already' "unset"
  # The break this guards: asking somebody with no Jira whether they use Jira.
  # The success criterion says that never happens, so it is asserted, not
  # assumed.
  [ ! -e .cairn/sync.json ]
  [ ! -e .cairn/config.json ]
}

@test "a key only in commit messages is still not enough to be asked" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  git commit -q --allow-empty -m "DTP-101: wire the login flow"
  git commit -q --allow-empty -m "DTP-102: and its tests"
  git commit -q --allow-empty -m "DTP-103 hotfix"

  # This is the seam between the two halves of the plan: the detector reports
  # the prefix (information) while `detected` stays false (verdict), and this
  # script asks on the verdict. 21/21 of this repo's commit-message matches
  # were false positives.
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ask' "false"
  assert_json_eq "$output" '.reason' "no signal"
  assert_json_eq "$output" '.findings.prefixes | join(",")' "DTP"
}

@test "a branch carrying the key makes it ask, with evidence to ask with" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  seed_jira_signals

  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ask' "true"
  assert_json_eq "$output" '.reason' "signal found, no answer on record"
  assert_json_eq "$output" '.findings.prefixes[0]' "DTP"
  # Evidence, not a verdict: the question has to be able to say "found DTP in
  # one branch and three commits" and quote them.
  assert_json_eq "$output" '.findings.samples.DTP.branch_count' "1"
  assert_json_eq "$output" '.findings.samples.DTP.commit_count' "3"
  assert_json_eq "$output" \
    '.findings.samples.DTP.branches[0]' "DTP-104-refresh-tokens"

  # ...and the human render carries the same evidence, so the prose command
  # is never the only place it exists.
  run JIRA detect
  [ "$status" -eq 0 ]
  grep -qF "ask=yes" <<<"$output"
  grep -qF "DTP- in 1 branch(es), 3 commit(s)" <<<"$output"
}

@test "a recorded no is as durable as a yes — the question does not come back" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  seed_jira_signals

  run JIRA decline
  [ "$status" -eq 0 ]
  grep -qF "jira.link=no recorded" <<<"$output"

  # The break: a `no` that is not written brings the question back next
  # session, and the criterion says it has the same force as a `yes`.
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ask' "false"
  assert_json_eq "$output" '.reason' "already answered: no"
  assert_json_eq "$output" '.already' "no"

  # The answer lives in the file cairn-config.py owns, under its schema — one
  # fact, one owner. It is readable through that owner, not only as bytes.
  run env HOME="$FAKE_HOME" bash "$CONFIG_SH" get jira.link \
    --project-dir "$PWD"
  [ "$status" -eq 0 ]
  [ "$output" = "no" ]

  # A decline never touches the sync configuration.
  [ ! -e .cairn/sync.json ]

  # Re-declining is a no-op with its own exit code, not a rewrite.
  run JIRA decline
  [ "$status" -eq 3 ]
}

@test "apply writes the jira backend with env var NAMES and no credential" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  seed_jira_signals
  # The site comes from the remote, so nothing at all is typed: not the key,
  # not the project, not the site.
  git remote add origin https://example.atlassian.net/scm/proj.git

  run JIRA apply --key DTP
  [ "$status" -eq 0 ]
  grep -qF "jira backend enabled for DTP at https://example.atlassian.net" \
    <<<"$output"
  grep -qF "JIRA_API_TOKEN" <<<"$output"

  cfg="$(cat .cairn/sync.json)"
  assert_json_eq "$cfg" '[.backends[] | select(.type=="jira")] | length' "1"
  assert_json_eq "$cfg" '.backends[0].enabled' "true"
  assert_json_eq "$cfg" '.backends[0].adapter' "jira"
  assert_json_eq "$cfg" '.backends[0].config.project_key' "DTP"
  assert_json_eq "$cfg" '.backends[0].config.base_url' \
    "https://example.atlassian.net"

  # The EXACT field set, asserted rather than described. The break this
  # guards is the critical one in the threat register: a token VALUE written
  # into a committed file. There is no field here that could hold one.
  assert_json_eq "$cfg" '.backends[0].config | keys | join(",")' \
    'base_url,email_env,issue_type,project_key,token_env,transitions'
  assert_json_eq "$cfg" '.backends[0].config.email_env' "JIRA_EMAIL"
  assert_json_eq "$cfg" '.backends[0].config.token_env' "JIRA_API_TOKEN"
  assert_json_eq "$cfg" \
    '[.backends[0].config | keys[] | select(test("^(token|api_token|password|secret|email)$"))] | length' \
    "0"

  # The yes is recorded with the same durability as the no.
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.ask' "false"
  assert_json_eq "$output" '.reason' "already answered: yes"

  # Re-applying is a no-op with its own exit code.
  run JIRA apply --key DTP
  [ "$status" -eq 3 ]
}

@test "apply preserves another backend already configured in sync.json" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  seed_jira_signals
  mkdir -p .cairn
  cat > .cairn/sync.json <<'EOF'
{
  "backends": [
    { "type": "github", "enabled": true, "adapter": "github",
      "config": { "repo": "example/fixture", "extra_labels": [] } }
  ]
}
EOF

  run JIRA apply --key DTP --base-url https://example.atlassian.net
  [ "$status" -eq 0 ]

  cfg="$(cat .cairn/sync.json)"
  # The break: an apply that overwrites the file wipes somebody's GitHub sync
  # as the price of answering a Jira question.
  assert_json_eq "$cfg" '[.backends[].type] | sort | join(",")' "github,jira"
  assert_json_eq "$cfg" \
    '[.backends[] | select(.type=="github") | .config.repo][0]' \
    "example/fixture"
}

@test "apply refuses to invent a site rather than writing a placeholder" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  seed_jira_signals

  # No atlassian.net remote, no --base-url: the honest gap, named. A backend
  # written with a fake base_url fails at push time with an error nobody can
  # read, so nothing is written at all.
  run JIRA apply --key DTP
  [ "$status" -eq 2 ]
  grep -qF "base_url cannot be derived" <<<"$output"
  [ ! -e .cairn/sync.json ]

  # ...and the answer is NOT recorded either: a refusal is not a yes.
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.already' "unset"
}

@test "an Atlassian MCP server DECLARED in .mcp.json is a signal" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  git commit -q --allow-empty -m "chore: no tracker key anywhere"
  cat > .mcp.json <<'EOF'
{
  "mcpServers": {
    "atlassian": { "command": "npx", "args": ["-y", "mcp-remote"] }
  }
}
EOF

  run JIRA detect --json
  [ "$status" -eq 0 ]
  # The break: a predicate that only reads ~/.claude.json never sees the
  # server the project itself declares.
  assert_json_eq "$output" '.findings.mcp.declared' "true"
  assert_json_eq "$output" '.findings.mcp.server' "atlassian"
  assert_json_eq "$output" \
    '.findings.mcp.source | endswith("/.mcp.json")' "true"
  assert_json_eq "$output" \
    '.findings.signals | contains(["mcp"])' "true"

  # A signal with no key found is a real case and NOT the same question:
  # there is nothing here to confirm, and the reason says so instead of
  # pretending a choice exists.
  assert_json_eq "$output" '.ask' "true"
  assert_json_eq "$output" '.reason' "signal found, no key to confirm"
  assert_json_eq "$output" '.findings.prefixes | length' "0"
}

@test "claudeAiMcpEverConnected alone is NOT a declaration" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  git commit -q --allow-empty -m "chore: no tracker key anywhere"

  # The only file trace of the active Atlassian Rovo connector on the machine
  # this was written. Whether the list means "connected now" or "connected at
  # some point" was NOT measured, so it stays outside the predicate: history
  # read as state is a silent false positive. Measuring it is what would move
  # it in — not convenience.
  cat > "$FAKE_HOME/.claude.json" <<'EOF'
{
  "claudeAiMcpEverConnected": [
    "claude.ai Gmail",
    "claude.ai Atlassian Rovo"
  ]
}
EOF

  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.findings.mcp.declared' "false"
  assert_json_eq "$output" '.findings.mcp.source' "null"
  assert_json_eq "$output" '.findings.signals | length' "0"
  assert_json_eq "$output" '.ask' "false"
  assert_json_eq "$output" '.reason' "no signal"
}

@test "an Atlassian server declared in ~/.claude.json IS read" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  git commit -q --allow-empty -m "chore: no tracker key anywhere"
  cat > "$FAKE_HOME/.claude.json" <<'EOF'
{
  "claudeAiMcpEverConnected": ["claude.ai Gmail"],
  "mcpServers": {
    "rovo": { "type": "http", "url": "https://mcp.atlassian.com/v1/sse" }
  }
}
EOF

  # Declared under a name that says nothing ("rovo"): the URL is what names
  # Atlassian, so the predicate has to look past the entry's key.
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.findings.mcp.declared' "true"
  assert_json_eq "$output" '.findings.mcp.server' "rovo"
  assert_json_eq "$output" \
    '.findings.mcp.source | endswith("/.claude.json")' "true"
}

@test "a malformed .mcp.json degrades to 'not declared', never a crash" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  git commit -q --allow-empty -m "chore: no tracker key anywhere"
  printf '{ "mcpServers": { "atlassian": ' > .mcp.json

  # T-29-20: a third party's broken file must not take detect down, and with
  # it /cairn:migrate. Same contract run_git() already follows.
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.findings.mcp.declared' "false"
  assert_json_eq "$output" '.reason' "no signal"
}

@test "detection is not reimplemented here: no detector, exit 5, no writes" {
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"
  seed_jira_signals

  # Copy the pair into a scratch dir MINUS cairn-migrate.py. If this script
  # ever grew its own regex, this test would go green while the two detectors
  # started disagreeing about the same repository — which is the disease this
  # milestone exists to cure.
  scratch="$BATS_TEST_TMPDIR/scripts"
  mkdir -p "$scratch"
  cp "$CAIRN_SCRIPTS_DIR/cairn-jira.py" "$CAIRN_SCRIPTS_DIR/cairn-jira.sh" \
     "$CAIRN_SCRIPTS_DIR/cairn-config.py" "$scratch/"

  run env HOME="$FAKE_HOME" bash "$scratch/cairn-jira.sh" detect --json \
    --project-dir "$PWD"
  [ "$status" -eq 5 ]
  grep -qF "could not run the detector" <<<"$output"
  [ ! -e .cairn/config.json ]
}

@test "the three routes are distinguishable by reason, and the command names them" {
  # WHAT THIS PROVES: that the seam between script and prose is real — the
  # three decisions carry distinct, stable `reason` strings, and
  # /cairn:sync-config names every one of them plus the exact invocation it
  # answers with. Rename a reason without touching the command and this goes
  # red, which is the drift worth catching.
  #
  # WHAT IT DOES NOT PROVE: that the conversation is any good.
  # AskUserQuestion does not run under bats, so nothing here shows that the
  # user is shown the evidence, asked once, or asked well. That layer is
  # prose, and asserting a green over it would be the "write_set_complete:
  # true" verde falso this phase already measured once. It is left honestly
  # unproven rather than dishonestly covered.
  make_tmp_repo
  make_gsd_fixture "$CAIRN_TMP_REPO"

  # route 1 — no signal
  git commit -q --allow-empty -m "chore: nothing that looks like a tracker"
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reason' "no signal"

  # route 3 — signal, no answer yet
  seed_jira_signals
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reason' "signal found, no answer on record"

  # route 2 — already answered
  run JIRA decline
  [ "$status" -eq 0 ]
  run JIRA detect --json
  [ "$status" -eq 0 ]
  assert_json_eq "$output" '.reason' "already answered: no"

  cmd="$CAIRN_REPO_ROOT/cairn/commands/sync-config.md"
  # A thin wrapper: the decision comes from the script, and the prose says so
  # by naming the invocation rather than describing detection in words.
  grep -qF 'scripts/cairn-jira.sh" detect --json' "$cmd"
  grep -qF 'scripts/cairn-jira.sh" apply --key' "$cmd"
  grep -qF 'scripts/cairn-jira.sh" decline' "$cmd"
  # ...and the three routes, by the literal reason each one keys off.
  grep -qF '"no signal"' "$cmd"
  grep -qF 'already answered: yes' "$cmd"
  grep -qF 'signal found, no key to confirm' "$cmd"
  # The two properties the success criterion states in words.
  grep -qF "A project with no signal is never asked" "$cmd"
  grep -qF "never ask for" "$cmd"
}

@test "cairn-jira.sh with no subcommand exits 2 and names the three verbs" {
  make_tmp_repo

  run env HOME="$FAKE_HOME" bash "$JIRA_SH"
  [ "$status" -eq 2 ]

  run env HOME="$FAKE_HOME" bash "$JIRA_SH" --help
  [ "$status" -eq 0 ]
  grep -qF "detect" <<<"$output"
  grep -qF "apply" <<<"$output"
  grep -qF "decline" <<<"$output"
}
