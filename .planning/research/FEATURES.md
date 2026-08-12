# Feature Research

**Domain:** Drift detection & multi-source state reconciliation for developer tooling (phase ↔ issue-tracker ↔ artifact ↔ git corroboration)
**Researched:** 2026-07-29
**Confidence:** MEDIUM-HIGH (cross-checked against official docs — HashiCorp, Kubernetes, dbt Labs, git-scm.com, Ansible, Pulumi, Nix, Docker, GitHub CLI — plus independent practitioner sources for the alert-fatigue and CLI-layout claims)

## Why this domain, not a generic one

cairn's root problem (PROJECT.md) is that phase state is decided by `phase_disk_state()` checking for four filenames — never opening them, never consulting bd, git, or the tree. This is structurally the same problem solved, in different shapes, by every tool below: a **declared/recorded state** (Terraform state, Kubernetes spec, dbt manifest, git index, cairn's PLAN/SUMMARY/VERIFICATION files) can silently diverge from **what is actually true** (real cloud resources, actual pod health, real warehouse data, the working tree, the actual bd issues and git commits). The research below is deliberately narrow to that shape of problem, because that is the exact shape of this milestone.

## Prior Art Deep Dive (answers to the four research questions)

### Q1 — When sources of truth disagree, what do good tools DO?

**Universal finding: report-and-require-confirmation, never silent auto-reconcile.** Every mature tool researched separates *detecting* a gap from *writing* a correction into at least two explicit steps, and none of them auto-writes by default:

- **Terraform** splits it further than any other tool: `terraform plan -refresh-only` shows drift with **zero** proposed remediation; `terraform apply -refresh-only` is a **second, explicit** command that shows the same diff again and asks for confirmation before writing the updated state file. A plain `terraform plan` refreshes in-memory only — it never writes state or touches infrastructure on its own. ([HashiCorp tutorial](https://developer.hashicorp.com/terraform/tutorials/state/resource-drift))
- **Ansible** `--check` mode makes every check-mode-aware module report what it *would* change instead of changing it; nothing is written unless you drop `--check` and re-run. `--diff` composes with it for a full textual preview with zero side effects. ([Ansible docs](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html))
- **Pulumi** `refresh --preview-only` queries every resource's real provider state, diffs it against stack state, and prints the diff with no writes at all; plain `refresh` does write state but still never touches infrastructure. It is explicitly **not** run automatically by default, specifically because it costs one API round-trip per resource — an intentional latency/cost gate on an otherwise "safe" read operation. ([Pulumi docs](https://www.pulumi.com/docs/iac/operations/stack-management/drift/), [Pulumi blog](https://www.pulumi.com/blog/repairing-state-with-pulumi-refresh/))

**Evidence users tolerate this and resent the alternative:** the commercial platforms built on top of these CLIs (Scalr, Spacelift, HCP Terraform) all had the option to sell "one-click auto-fix drift" and deliberately did not ship full automated remediation — they added severity classification and ignore-lists instead, citing safety. That is a revealed preference from vendors who would profit from selling automation, choosing not to. ([Scalr](https://scalr.com/learning-center/terraform-drift-detection-how-to-prevent-and-remediate))

**Evidence of what users resent:** uncategorized, all-severity-equal drift alerts. Documented failure mode: teams receiving 50+ drift alerts/day see response quality and speed degrade up to 40%; a cited healthcare org adopted open-source drift scanning and ended up with staff **ignoring alerts until a real incident hit**, because false positives (provider-managed read-only fields, expected autoscaling changes) were mixed in with real ones at equal severity. ([Dev|Journal](https://earezki.com/ai-news/2026-05-02-why-severity-classification-changes-everything-about-drift-detection/), [Drift Alert Burnout](https://medium.com/@Praxen/drift-alert-burnout-f1d7f498b53d))

This directly validates two Key Decisions already logged in PROJECT.md ("A escalada nunca grava estado — só propõe"; "Corroboração determinística antes de escalada semântica") — they match the only pattern that survived contact with real users across this entire research set.

### Q2 — Is an explicit "conflict"/"unknown" state a recognized pattern, or do tools avoid it?

**Recognized and load-bearing, not avoided — this is the strongest finding in this research.**

- **Kubernetes conditions** use a literal three-value status: `True` / `False` / `Unknown` — not two. `Unknown` means "cannot be determined right now," and by written convention the **absence** of a condition is read identically to `Unknown` rather than defaulting to `False`. This is normative API convention, not an edge case. ([kubernetes.io](https://kubernetes.io/docs/concepts/workloads/pods/pod-condition/), [maelvls.dev](https://maelvls.dev/kubernetes-conditions/))
- **Jujutsu (jj)**, a modern VCS, goes further and makes conflicts **first-class, storable data**: a rebase that produces a conflict still *succeeds* and records the conflict inside the resulting commit (a logical representation, not textual markers), so work is never blocked on immediate resolution — you keep going and resolve later, deliberately. ([jj docs](https://github.com/jj-vcs/jj/blob/main/docs/conflicts.md), [Chris Krycho on deferred resolution](https://v5.chriskrycho.com/journal/deferred-conflict-resolution-in-jujutsu/))
- **Terraform's drift note** ("Note: Objects have changed outside of Terraform...") is the closest real template for *what a good conflict message contains*: it names exactly what changed, states plainly why it matters (the next plan may try to undo real external changes), and tells you the two ways out (update config, or `ignore_changes`). ([HashiCorp support](https://support.hashicorp.com/hc/en-us/articles/4405950960147-New-Feature-Objects-have-changed-outside-of-Terraform))

**Synthesis for cairn:** a good conflict message needs, at minimum: (1) which sources disagree, named explicitly (not "state mismatch" but "bd says closed, SUMMARY.md is absent"); (2) what each source claims, with its own timestamp/actor where available (bd has this natively — closer, author, reason); (3) why it isn't safe to auto-resolve (which source would be discarded and what that would silently erase); (4) the exact next command to resolve it. And per Q1/jj: **a conflict state must not block other work** — it should be visible and durable, the way jj commits a conflict and keeps going, not the way git blocks a merge.

### Q3 — Dense per-unit-of-work status cards in real CLIs

Three concrete, well-known layouts, described precisely enough to copy the information hierarchy:

**1. `kubectl describe pod`** — three stacked zones, each with a different shape, never merged into one:
- *Identity/current-state block*: flat `Label: value` lines (Name, Namespace, Node, Status, IP) — the "what is this and where does it stand right now" zone.
- *Conditions table*: a real table, two columns only (`Type | Status`), one row per independent condition (`Initialized`, `Ready`, `ContainersReady`, `PodScheduled`) — deliberately narrow, scannable at a glance, each row independently true/false/unknown.
- *Events log*: chronological table (`Type | Reason | Age | From | Message`), oldest-to-newest, explicitly the "root cause is usually readable here in plain English" section — this is the *history* zone, distinct from the *current-state* zone above it.
  ([Warp terminus](https://www.warp.dev/terminus/kubectl-describe-pod), [Spacelift](https://spacelift.io/blog/kubectl-describe))

**2. `systemctl status`** — a colored one-glyph summary (`●`, green/red/yellow) fused to the unit name on line 1, then labeled blocks below it: `Loaded:` (source + enabled/disabled), `Active:` (state + since-timestamp + duration), `Main PID:`, then a tail of the actual journal log inline at the bottom. The structural lesson: **the single most important fact (is it up) is a colored glyph you read in under a second; everything else is progressively more detail below it**, ending in raw evidence (log lines), not a summary of the summary. ([DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units))

**3. `docker compose ps`** — flat table (`NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS`) with health folded as a parenthetical suffix inside the STATUS cell (`Up 2 minutes (healthy)`). This is the **cautionary** example: collapsing two independently-meaningful signals (process uptime state, health-check result) into one string is exactly the anti-pattern this milestone must not repeat — `--format json` has to expose them as separate `State`/`Health` fields for anything to consume them independently, which the human-readable table does not. ([Docker docs](https://docs.docker.com/reference/cli/docker/compose/ps/), [docker/compose#5525](https://github.com/docker/compose/issues/5525))

**Fourth data point (bucket pattern, not a full layout):** `gh pr checks --json` categorizes every check into a five-value `bucket` field (`pass | fail | pending | skipping | cancel`) rather than a raw per-check string — a small but real example of normalizing N independent signals into a small closed enum for scripting, while the human view still shows each check by name. ([GitHub CLI manual](https://cli.github.com/manual/gh_pr_checks))

**Synthesis for the phase status card cairn needs:** identity/purpose line (what the phase is FOR) → a Conditions-style table of independent signals (research done? requirement ids satisfied? issue counts by status? verification verdict?) → a chronological events/journal tail (what happened, when, per source) → what it waits on → the next command. Never fold two independently-true/false signals into one display string (docker compose's mistake); do fold the single most important fact into one glyph/word at the top (systemctl's `●`).

### Q4 — Anti-features: what caused alert fatigue or got turned off

See the anti-features table below; the evidence is the alert-fatigue research cited in Q1 (50+/day alerts → up to 40% degraded response; a real org disengaging until an incident) plus the concrete workaround teams reached for instead of accepting noisy binary alerts: `.tfdriftignore` entries for known-noisy fields like autoscaling `desired_capacity`, and severity classification of *which* field drifted rather than treating every diff as equally urgent. ([Dev|Journal](https://earezki.com/ai-news/2026-05-02-why-severity-classification-changes-everything-about-drift-detection/))

## Feature Landscape

### Table Stakes (Users Expect These)

Any tool that reconciles a declared state against reality has these, in every mature example researched. Missing them here would make cairn's drift detection read as unfinished next to Terraform, Kubernetes, or dbt — the exact bar this milestone is competing against.

| Feature | Why Expected | Complexity | Dependency |
|---------|--------------|------------|------------|
| Read-only corroboration pass that never writes (a "plan"/"check mode" for phase state) | Terraform `plan -refresh-only`, Ansible `--check`, Pulumi `refresh --preview-only` are all opt-in, side-effect-free reads before any write. Users expect to be able to ask "what's the real state?" without risking a mutation. | LOW-MEDIUM | Needs the corroboration sources (bd, git log, artifact files) already readable, which they are today via `cairn-status.py`/`cairn-doctor.py`. |
| Independent per-signal conditions, not one collapsed enum | Kubernetes Conditions (`Ready`, `Progressing`, `Available`, `Degraded`, each True/False/Unknown) and git's staged/unstaged/untracked triad both refuse to compress multiple independent facts into one status word. `phase_disk_state()` doing exactly that (4 filenames → 1 of 4 words) is the diagnosed root cause. | MEDIUM | This is the architectural crux of the milestone — everything else (conflict state, status card, journal) is built on top of a per-signal model, not a single string. |
| Explicit "cannot determine" / conflict value, not silently defaulting to a guess | K8s's `Unknown` status and "absent condition reads as Unknown" convention; jj's first-class stored conflicts. Silently picking one source's answer when two disagree is the exact anti-pattern PROJECT.md names ("discordância vira `conflict`, nunca escolha silenciosa"). | MEDIUM | Depends on the per-signal model above — you cannot mark *one* signal Unknown/conflicted if state is one collapsed enum. |
| Human-readable diff naming what changed and where each side's claim came from | Terraform's "Objects have changed outside of Terraform" note itemizes the actual diff, not just "drift detected." A conflict report that says "state mismatch" with no detail is not table stakes, it is a regression from Terraform's bar. | LOW | Depends on the conditions/signals existing as structured data first, not just a boolean. |
| Never auto-write a correction; propose and require confirmation | Universal across Terraform/Ansible/Pulumi (see Q1). PROJECT.md already commits to this ("A escalada nunca grava estado — só propõe"). | LOW | Mostly a process/discipline constraint on the escalation path, not new plumbing — but must be enforced as a hard invariant (no code path where semantic escalation writes STATE.md/PLAN.md directly). |
| Machine-readable output mirroring the human view (same shape, `--json`) | `gh pr checks --json` (bucket field), `docker compose ps --format json` (separate State/Health), Terraform `-detailed-exitcode`. cairn's own `/cairn:status --json` already follows this pattern. | LOW | Extend the existing `--json` phase-panel shape (`disk_state`, etc. in status.md) rather than inventing a second schema. |
| Corroboration keyed on content/identity, not filename existence or mtime | The literal cause named in PROJECT.md: `phase_disk_state()` checks 4 filenames, never opens them. This is Make's exact staleness bug (mtime, not content) — the fix researched tools converged on is content/identity-addressed checking (Bazel/Nix hash inputs; here: do the bd issue ids stamped for this phase actually match what SUMMARY.md/PLAN.md claim, do git commits actually touch the phase's declared paths). | MEDIUM | Requires bd's `metadata.gsd` stamp (already shipped in v1.0) and PLAN frontmatter `beads:` ids (already shipped) to be read and compared, not just checked for file existence. |

### Differentiators (Competitive Advantage)

Where cairn can visibly exceed both the generic dev-tool bar and its closest direct comparisons (plain GSD, spec-kit, BMAD, buildomator — none of which corroborate state against anything external at all, per PROJECT.md's own finding that GSD needs `/gsd:audit-milestone` precisely because its state is inferred from side effects).

| Feature | Value Proposition | Complexity | Dependency |
|---------|-------------------|------------|------------|
| A named `conflict` phase-state value, with each disagreeing source's claim shown side by side | No competitor in cairn's space corroborates state against bd/git at all — this is table stakes vs. Terraform/K8s, but a genuine differentiator vs. every other GSD-family tool, which has no cross-check step. Modeled on Terraform's drift note (itemized) + K8s's `Unknown` (a first-class value, not an error state). | MEDIUM-HIGH | Requires the per-signal model (table stakes) plus bd's timestamp/author/reason data, which cairn already has structural access to and PROJECT.md explicitly calls out as an advantage GSD itself lacks. |
| A rich phase status card: purpose, research-happened flag, requirement ids, issue counts, verification verdict, what it waits on, next command — identical rendering in terminal and HTML | Directly modeled on kubectl describe's three-zone layout (identity block → conditions table → events log) and systemctl's "one glyph, then progressive detail" hierarchy. cairn's status board already has a phase panel (`PENDING PHASES`, `NEXT COMMANDS`) — this extends that schema rather than inventing new rendering. | MEDIUM | Depends on the per-signal conditions model; the terminal/HTML parity constraint is already solved architecturally (status.md documents "one model behind the board, the `--json`, and the HTML" from v1.3). |
| Append-only transition journal, separate from current-state | K8s's Events log (chronological, causal, additive) is a proven, dense, real pattern already validated in Q3 — distinct from the Conditions table, which is a current snapshot. PROJECT.md's stated requirement ("Journal append-only... estado lido, não reconstruído") maps directly onto this split. | MEDIUM | Independent of the conflict-state work but should share the same event vocabulary (what changed, source, timestamp) so the journal and the conflict message use one format, not two. |
| Phase-level lease visibility for concurrent agents | Not found as a *display* pattern in the infra tools researched (Terraform state-locking blocks rather than displays; Pulumi/Ansible have no equivalent) — the closer analogue is jj's non-blocking-but-visible conflict, and cairn's own existing `◆ assignee` marker on in-progress bd issues in the DOING lane. This is mostly an extension of an already-shipped pattern (issue-level claim visibility) up to phase level, not new territory. | MEDIUM | Depends on bd already exposing assignee/in_progress data (it does, per status.md's DOING lane) — the work is surfacing it at the phase granularity the milestone asks for, not building new plumbing. |
| Severity-classified conflicts (a cairn-native `.tfdriftignore` equivalent) | Directly answers the alert-fatigue evidence: not every mismatch is equally urgent (a doctor-closed issue vs. zero commits touching a phase's declared paths are very different conflicts). No competitor tool in this space has this at all, since none corroborate in the first place. | MEDIUM | **Requires** the per-signal conditions model and the named `conflict` state to exist first — you cannot classify severity of a mismatch that is still represented as one collapsed word. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Auto-reconciliation that silently rewrites STATE.md/PLAN.md to match discovered reality | Feels convenient — "just fix it for me" — and is the fastest thing to build once corroboration exists. | Zero mature tool researched does this by default (Terraform, Ansible, Pulumi all gate writes behind an explicit second command); the commercial platforms that could sell "auto-fix drift" deliberately don't, citing safety. An agent correcting its own state record also destroys the evidence that something went wrong — already logged as a Key Decision risk in PROJECT.md. | Propose a structured diff (each source's claim, named) and require a `/cairn:*` command to confirm the write — exactly the two-step Terraform pattern. |
| Uncategorized, all-severity-equal conflict alerts on every mismatch | Simplest to ship — flag anything that doesn't match. | Directly the documented failure mode: 50+/day alerts degrade response quality up to 40%, and real teams disengage/mute rather than triage — one cited org ignored drift alerts entirely until an actual incident. A cairn conflict list with no severity would train users to ignore `/cairn:doctor` output the same way. | Classify what disagrees (e.g., "bd closed by doctor sweep, harmless" vs. "phase marked verified, zero commits touch its declared paths, high severity") the same way `.tfdriftignore` and drift-severity classification tools do. |
| Timestamp/mtime-based re-check of the same four filenames, just refreshed more often | Looks like a quick fix for the root-cause bug — "just also check mtime, not just existence." | This is Make's exact bug, already diagnosed as the root cause in PROJECT.md. A file's mtime says nothing about whether its *content* still matches bd/git reality; a human hand-editing SUMMARY.md updates its mtime without making the claim true. | Content/identity-based corroboration: compare what SUMMARY.md/PLAN.md's stamped requirement ids and bd ids actually say against what bd and git currently show — the Bazel/Nix hash-over-timestamp move, applied to phase artifacts instead of build outputs. |
| A background watcher/daemon that continuously recomputes phase state on every file change | Feels "always up to date," and the milestone's language ("estado corroborado") could be read as implying live sync. | No tool researched does this by default — Terraform/Pulumi refresh is explicitly opt-in because of round-trip cost; git/Bazel/dbt do not watch by default either. PROJECT.md already ruled out the adjacent idea for the prior milestone ("Telemetria contínua de sessões reais — não escolhida"), for the same reproducibility/cost reasoning. | On-demand corroboration triggered by `/cairn:status`, `/cairn:doctor`, `/cairn:verify` — consistent with cairn's existing philosophy and this milestone's own "Corroboração determinística antes de escalada semântica" decision. |
| Collapsing a multi-source conflict into one opaque confidence score or percentage | Reads as a tidy, dashboard-friendly single number. | No tool researched does this either — K8s doesn't score conditions into a percentage, Terraform doesn't score drift as "73% confident." A single number hides *which* source disagrees and *why*, which is precisely what the conflict message must show per Q2. cairn's own prior-milestone research independently flagged "one opaque composite score" as an anti-pattern for the benchmark surface — same principle applies here. | Show each source's literal claim (bd: closed, reason X, date Y; git: N commits touching phase dir; PLAN.md: M requirement ids declared; SUMMARY.md: absent) as a structured list, never reduced to one number. |

## Feature Dependencies

```
Per-signal conditions model (independent True/False/Unknown per source)
    └──requires──> nothing new structurally (bd metadata.gsd, PLAN frontmatter, git log all already readable)

Named `conflict` phase-state value, itemized by source
    └──requires──> Per-signal conditions model
                       └──requires──> nothing new (see above)

Severity-classified conflicts (cairn-native ignore/priority list)
    └──requires──> Named `conflict` state
                       └──requires──> Per-signal conditions model

Rich phase status card (terminal + HTML, identical schema)
    └──requires──> Per-signal conditions model
    └──enhances──> Named `conflict` state (renders it, doesn't create it)

Append-only transition journal
    └──requires──> a shared event vocabulary with the conflict message (source, claim, timestamp)
    └──enhances──> Rich phase status card (feeds its "history" zone, per the kubectl describe layout)

Phase-level lease visibility
    └──requires──> bd's existing assignee/in_progress data (already shipped)
    └──independent of── the conflict-state work (can ship in parallel)

Read-only corroboration pass (never writes)
    └──requires──> Per-signal conditions model
    └──blocks──> any write-path work (escalation, auto-anything) must sit strictly after this, never before
```

### Dependency Notes

- **Everything downstream requires the per-signal conditions model first.** This is the single highest-leverage item: it is the direct fix for `phase_disk_state()`'s root-cause bug, and every differentiator (conflict state, status card, severity classification) is unbuildable on top of a collapsed single-enum state. Sequence it first.
- **Severity classification requires the named conflict state to exist**, not the other way around — you cannot rank the severity of something that isn't yet represented as a distinct, structured value.
- **Lease visibility is architecturally independent** of the conflict/corroboration work — it reads bd's already-shipped assignee data and can ship in parallel without blocking or being blocked by the state-model rework.
- **The journal and the conflict message should share one event vocabulary** (source, claim, timestamp, actor) so a conflict report and a journal entry are the same shape, not two schemas that drift apart from each other — which would be a small, ironic instance of the exact problem this milestone fixes.

## MVP Definition

### Launch With (v1.4 — Honest State, per PROJECT.md's Active requirements)

- [ ] Per-signal conditions model replacing `phase_disk_state()`'s four-filename check — the load-bearing fix everything else sits on
- [ ] Named `conflict` state, itemized by source, surfaced instead of a silent choice — matches PROJECT.md's explicit requirement
- [ ] Read-only corroboration pass with a hard invariant that escalation never writes state — matches PROJECT.md's "propõe, nunca decide" decision
- [ ] Phase lease visibility extending the existing DOING-lane assignee marker to phase granularity

### Add After Validation (v1.x)

- [ ] Rich terminal+HTML phase status card (kubectl-describe-style: identity → conditions table → events tail → next command) — once the per-signal model is stable, the rendering is comparatively low-risk to extend
- [ ] Append-only transition journal sharing the conflict-message event vocabulary

### Future Consideration (v2+)

- [ ] Severity classification / cairn-native ignore-list for known-harmless conflicts (e.g., doctor-sweep-closed issues) — defer until there is a real corpus of conflict types to classify; premature severity tiers on zero real data would be guessing, the same mistake the alert-fatigue research warns against
- [ ] Cross-repo or cross-milestone conflict trend view — no evidence any researched tool needs this at cairn's scale; revisit only if the conflict volume itself becomes a scaling problem

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Per-signal conditions model | HIGH | MEDIUM | P1 |
| Named `conflict` state, itemized by source | HIGH | MEDIUM | P1 |
| Escalation never writes (hard invariant) | HIGH | LOW | P1 |
| Phase lease visibility | MEDIUM | MEDIUM | P1 |
| Rich phase status card (terminal+HTML) | HIGH | MEDIUM | P2 |
| Append-only transition journal | MEDIUM | MEDIUM | P2 |
| Severity-classified conflicts | MEDIUM | MEDIUM | P3 |
| Cross-milestone conflict trends | LOW | HIGH | P3 |

## Competitor Feature Analysis

| Feature | Plain GSD (4.x / gsd-core without cairn) | Terraform/Pulumi (nearest infra analogue) | cairn's approach |
|---------|--------------------------------------------|--------------------------------------------|-------------------|
| Cross-checks declared state against an independent source | No — state is inferred from side effects; PROJECT.md notes this is exactly why GSD needs `/gsd:audit-milestone` | Yes — real infra is the independent source, queried on demand | Yes — bd (timestamped, authored, reasoned) and git are the independent sources cairn already has structural access to |
| Explicit "cannot determine" / conflict value | No | Partial — Terraform reports drift as a diff, not a named enum state; no built-in "Unknown" value in its CLI vocabulary (K8s has this, Terraform does not) | Yes — `conflict` as a first-class phase-state value, closer to Kubernetes' convention than Terraform's |
| Auto-write on detected mismatch | N/A (no detection at all) | No, by design, across every tool researched | No — matches the universal pattern; already a Key Decision |
| Dense single-command status view | Partial — ROADMAP.md/STATE.md prose | Partial — `terraform plan` output, not a persistent card | Yes — extends the existing `/cairn:status` phase panel, terminal+HTML parity already solved |

## Sources

- Terraform drift/refresh: [HashiCorp tutorial — Manage resource drift](https://developer.hashicorp.com/terraform/tutorials/state/resource-drift), [HashiCorp blog — Detecting and Managing Drift](https://www.hashicorp.com/en/blog/detecting-and-managing-drift-with-terraform), [HashiCorp support — "Objects have changed outside of Terraform"](https://support.hashicorp.com/hc/en-us/articles/4405950960147-New-Feature-Objects-have-changed-outside-of-Terraform)
- Kubernetes conditions: [kubernetes.io — Pod Conditions](https://kubernetes.io/docs/concepts/workloads/pods/pod-condition/), [maelvls.dev — What the heck are Conditions](https://maelvls.dev/kubernetes-conditions/), [oneuptime — CRD Status Conditions Conventions](https://oneuptime.com/blog/post/2026-02-09-crd-status-conditions-conventions/view)
- dbt: [dbt Developer Hub — Configure state selection](https://docs.getdbt.com/reference/node-selection/configure-state), [dbt Developer Hub — Source freshness](https://docs.getdbt.com/docs/deploy/source-freshness), [dbt Developer Hub — Node selector methods](https://docs.getdbt.com/reference/node-selection/methods)
- Build systems / content addressing: [Buckaroo — Build-Systems Should Use Hashes Over Timestamps](https://medium.com/@buckaroo.pm/build-systems-should-use-hashes-over-timestamps-54d09f6f2c4), [Nalys — Bazel vs Make](https://nalys-taas-projects.gitlab.io/internal/taas_blog/post/bazel_vs_make/), [Nix reference manual — Content-addressing derivation outputs](https://nix.dev/manual/nix/2.28/store/derivation/outputs/content-address.html), [NixOS RFC 62](https://github.com/NixOS/rfcs/blob/master/rfcs/0062-content-addressed-paths.md)
- git status: [git-scm.com — git-status docs](https://git-scm.com/docs/git-status)
- Ansible: [Ansible Community Docs — Check mode and diff mode](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html)
- Pulumi refresh: [Pulumi Docs — Detecting and reconciling drift](https://www.pulumi.com/docs/iac/operations/stack-management/drift/), [Pulumi Blog — Repairing State With Pulumi Refresh](https://www.pulumi.com/blog/repairing-state-with-pulumi-refresh/)
- Alert fatigue / drift severity: [Dev|Journal — Solving Alert Fatigue via Severity Classification](https://earezki.com/ai-news/2026-05-02-why-severity-classification-changes-everything-about-drift-detection/), [Drift Alert Burnout](https://medium.com/@Praxen/drift-alert-burnout-f1d7f498b53d), [Scalr — Terraform Drift Detection](https://scalr.com/learning-center/terraform-drift-detection-how-to-prevent-and-remediate)
- Dense CLI status layouts: [Warp — kubectl describe pod](https://www.warp.dev/terminus/kubectl-describe-pod), [Spacelift — Kubectl Describe Command](https://spacelift.io/blog/kubectl-describe), [Docker Docs — docker compose ps](https://docs.docker.com/reference/cli/docker/compose/ps/), [docker/compose#5525](https://github.com/docker/compose/issues/5525), [DigitalOcean — systemctl](https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units), [GitHub CLI — gh pr checks manual](https://cli.github.com/manual/gh_pr_checks)
- First-class conflict state: [jj-vcs — conflicts.md](https://github.com/jj-vcs/jj/blob/main/docs/conflicts.md), [Chris Krycho — Deferred Conflict Resolution in Jujutsu](https://v5.chriskrycho.com/journal/deferred-conflict-resolution-in-jujutsu/)
- Project context: `.planning/PROJECT.md` (root-cause diagnosis of `phase_disk_state()`, milestone requirements and Key Decisions already logged), `cairn/docs/commands/doctor.md` and `cairn/docs/commands/status.md` (existing surfaces this milestone extends)

---
*Feature research for: cairn v1.4 "Honest State" — drift detection & multi-source state reconciliation*
*Researched: 2026-07-29*
