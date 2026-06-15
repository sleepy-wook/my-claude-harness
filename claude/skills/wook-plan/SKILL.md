---
name: wook-plan
description: Use at the START of a non-trivial feature or task, before writing code. Triggers: "plan this", "write a spec", "define acceptance criteria", "what's the plan for"; a request to implement a medium-or-larger feature when no spec/recipe exists yet. Not for trivial edits, lookups, or questions.
---

# /wook-plan — Planner (define "done" before coding)

This is the FRONT of the Planner -> Generator -> Evaluator loop. Its job is to decide
**what correct behaviour is, before any code**, and to express the acceptance criteria as
things a machine can actually run — then write them as the project's verification recipe
so the Evaluator and the Stop-gate check exactly those criteria. Plan defines the bar;
Generator implements; Evaluator/gate enforce it.

## Steps

1. **Clarify if vague.** If scope, inputs/outputs, or success are unclear, ask 1-3 pointed
   questions first. Do not guess (this developer prefers stopping to confirm over guessing).

2. **Produce the SPEC** and show it:
   - **Scope** — what is in, and what is explicitly OUT (list out-of-scope to prevent
     over-building).
   - **Edge cases** — the tricky inputs/states that must be handled.
   - **Acceptance criteria** — each phrased as something OBSERVABLE / RUNNABLE: a test that
     passes, a command that exits 0, an endpoint that returns 200, a query whose count
     matches. Reject unverifiable criteria like "production-ready"; rewrite them into
     checkable ones ("`pytest tests/auth` passes", "`curl -sf /health` exits 0").

3. **Wire criteria to verification — keep the gate recipe LEAN and FAST.** The auto-gate runs
   `.claude/evaluate.recipe` on EVERY code-changing turn, so it must stay a *small, stable,
   fast* set — **not** a per-feature pile that grows each plan.
   - Prefer expressing each acceptance criterion as a **test** under the project's existing
     runner (pytest/jest/…). The standing line (`tests: pytest -q`) then already covers it —
     no new recipe line, and the recipe does not grow per feature.
   - The recipe holds only the project's **standing fast checks** (tests, lint, typecheck).
     Add a NEW line only for a genuinely new *category* of fast check, never per criterion.
     **Do not accumulate** one-off commands.
   - Route **slow or non-deterministic** checks (full e2e, build, integration, Playwright
     visual) to on-demand `/wook-evaluate`, NOT the auto-gate. Mark **MANUAL** anything that
     can't be automated (don't fake a command).

4. **Get approval / edits** from the developer before writing anything.

5. **On approval, write the artifacts:**
   - Write `.claude/evaluate.recipe` as the **lean standing set** — do NOT blindly append to
     what's already there; **prune** redundant/old/slow lines so the gate stays fast and the
     recipe converges instead of growing. **Writing this file turns the auto-gate ON** (recipe
     present = gate active on every code-changing turn; no separate enable). Tell the developer,
     and that `.claude/evaluate-off` disables it.
   - Save the full spec to `.claude/plan.md` (so it survives context loss). Feature-specific
     criteria live there (and as tests) — not as extra recipe lines.

6. **Hand off to implementation.** Build against the spec. Do NOT claim done until the
   recipe passes — the auto-gate (now on) runs exactly these checks on every turn-end and
   blocks "done" until they pass; `/wook-evaluate` gives a deeper on-demand verdict. Either
   way the verdict is bound to real exit codes.

## Rules

- Acceptance criteria must be **machine-checkable wherever possible** — that is the whole
  point; the Evaluator runs them. This is what makes "done" mean something here.
- Keep scope tight and out-of-scope explicit.
- The recipe is a **small, stable, fast** set the gate runs every turn — keep it *converging,
  not growing*. Feature criteria become tests (covered by the standing line); slow/visual
  checks go to `/wook-evaluate`, never the auto-gate. Prune accumulated cruft when you touch it.
- The recipe you write is the contract. If the plan changes later, update it in the same breath
  so the gate never checks a stale bar.
