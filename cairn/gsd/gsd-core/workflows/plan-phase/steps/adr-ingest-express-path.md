## 3.6. Handle ADR Ingest Express Path

**Skip if:** No `--ingest` flag in arguments.

**If `--ingest <path-or-glob>` provided:**

1. Display banner: `GSD ► ADR Ingest Express Path` with `{INGEST_PATH}` and `{INGEST_FORMAT}`.
2. Parse each resolved ADR through `gsd-core/bin/lib/adr-parser.cjs` (`--input`, `--format`) and collect normalized records.
3. Status gate: reject `superseded`/`rejected`/`deprecated`; warn on `proposed`; missing status defaults to `accepted`.
4. Empty-decisions fallback: if all parsed ADRs have zero `decisions[]`, emit `ADR ingest produced no locked decisions; fall back to discuss-phase for this phase.` and exit with `/gsd:discuss-phase {N}` guidance.
5. Record the phase context (`cairn/scripts/cairn-record.sh context --phase {phase_number}`, body on stdin) using `<domain>`, `<decisions>`, `<canonical_refs>`, `<specifics>`, `<deferred>`, `<scope_fence>`, map `consequences_positive[]` to Success Criteria and `consequences_negative[]` to Risk Summary, and include `**Source:** ADR Ingest Express Path ({INGEST_PATH})`.
6. Set `context_content` from the recorded body and continue to step 5. Nothing to commit — the record is durable when the call returns.

**Effect:** This bypasses step 4 (load the phase context) since the context record was synthesized from ADR input.

