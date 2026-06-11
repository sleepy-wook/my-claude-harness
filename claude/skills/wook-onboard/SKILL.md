---
name: wook-onboard
description: Use to onboard an EXISTING project that has no harness setup yet — scan its code and docs and generate the full `.claude/` set in one pass (project-map, evaluate.recipe, conventions, reuse-index). Triggers: "onboard this repo", "set up the harness here", "this project has no .claude yet", "bootstrap the project map/conventions/recipe", adopting the harness on an existing codebase. Not for an already-set-up repo (refresh the individual docs) or one-off edits.
---

# /wook-onboard — bring an existing repo into the harness, in one pass

A project that's already underway has an empty `.claude/` — none of the harness artifacts
exist, so none of it is on. This scans the codebase and docs once and generates the whole set,
so the map/conventions/reuse-index/recipe are all in place. It is mostly an **orchestrator**:
it reuses the schemas of `/wook-map`, `/wook-conventions`, and `/wook-index` rather than
inventing new ones.

## Step 0 — survey what's already there
- List existing `.claude/` artifacts. **Idempotent:** never clobber blindly — for anything that
  exists, refresh it (or leave it and say so), don't overwrite silently.
- Infer the domains actually present (frontend/backend/db/infra/data/…) from the code.

## Step 1 — scan (read-only)
Read code + docs (README, package.json/pyproject/compose, Makefile, existing docs). For a large
repo, you MAY fan out **read-only subagents** (Explore / general-purpose — read, never write),
one per concern (map / conventions / reuse-index); they return drafts, you assemble. (Writing to
different files is independent, so this is safe — keep the *writing* in your hands at Step 3.)

## Step 2 — draft the four, in order
1. **`project-map.md`** — follow `/wook-map`'s fixed schema (Stack & Run / Structure / How to
   exercise / Entry points; commands derived from real sources with `# provenance`; smoke ties to
   the recipe; structure ≤2 levels). This comes first — the rest builds on it.
2. **`evaluate.recipe`** — derive a **baseline** from the test/lint/build commands the map found
   (e.g. `tests: <map.run.api.test>`, `lint: <…>`). Only include commands you actually found —
   don't fabricate. This is the one genuinely new step; the others reuse existing skills.
3. **`conventions/<domain>.md`** — follow `/wook-conventions` **brownfield**: extract the de-facto
   conventions from each domain's code, flag inconsistencies for the developer to resolve.
4. **`reuse-index/<domain>.md`** — follow `/wook-index`: compact `name · desc · path:symbol` per
   reusable piece.

## Step 3 — propose, then write on approval
- **Show a summary BEFORE writing**: the file list to be created/refreshed, the proposed
  `evaluate.recipe` (and that **its presence turns the auto-gate ON**), the domains covered, and
  any inconsistencies the developer must decide. Get approval/edits.
- **On approval, write** all the artifacts. Verify every `path:symbol` pointer resolves. Report
  what was created vs refreshed vs skipped, and remind that the gate is now on.

## Rules
- Approval-gated: this creates a lot at once (and the recipe turns the gate on) — never mass-write
  before the developer has seen the summary.
- Idempotent: refresh/merge existing artifacts; don't destroy hand-written content.
- Reuse the sub-skills' schemas exactly — `/wook-onboard` is orchestration, not a new format.
- Baseline recipe = real discovered commands only. If you found no tests/lint, say so (the gate
  needs at least one real check to be meaningful) rather than inventing one.
