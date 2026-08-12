## 3.5. Handle PRD Express Path

**Skip if:** No `--prd` flag in arguments.

**If `--prd <filepath>` provided:**

Read and execute `gsd-core/workflows/plan-phase/steps/prd-express-path.md` — it reads the PRD (`$PRD_FILE`), records the phase context (every PRD requirement/story/criterion → locked decision, uncovered areas → "Claude's Discretion", canonical refs extracted from the roadmap + PRD-referenced specs), sets `context_content`, and bypasses step 4 (load the phase context). The rest of the workflow proceeds normally with the PRD-derived context.

