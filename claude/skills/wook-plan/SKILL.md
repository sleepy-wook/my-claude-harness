---
name: wook-plan
description: Use at the START of a non-trivial feature or task, before writing code. Triggers: "plan this", "write a spec", "define acceptance criteria", "what's the plan for"; a request to implement a medium-or-larger feature when no spec/recipe exists yet. Not for trivial edits, lookups, or questions.
---

# /wook-plan — Planner (define "done" before coding)

This is the FRONT of the Planner -> Generator -> Evaluator loop. Its job is to decide
**what correct behaviour is, before any code**, and to express the acceptance criteria as
things a machine can actually run — then write them as the project's verification recipe
so the Evaluator and the commit gate check exactly those criteria. Plan defines the bar;
Generator implements; the gate (a git `pre-commit` hook) enforces it at commit time.

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

3. **Wire criteria to verification — keep the gate recipe LEAN and FAST.** The commit gate
   runs `.claude/evaluate.recipe` on every `git commit`, so it must stay a *small, stable,
   fast* set — **not** a per-feature pile that grows each plan.
   - Prefer expressing each acceptance criterion as a **test** under the project's existing
     runner (pytest/jest/…). The standing line (`tests: pytest -q`) then already covers it —
     no new recipe line, and the recipe does not grow per feature.
   - The recipe holds only the project's **standing fast checks** (tests, lint, typecheck).
     Add a NEW line only for a genuinely new *category* of fast check, never per criterion.
     **Do not accumulate** one-off commands.
   - **Scope lint/format to CHANGED files, not the whole repo.** A trivial one-line commit must
     not lint the entire tree. Prefer staged-file scoping, e.g.
     `lint: git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx)$' | xargs -r npx eslint`
     over a whole-repo glob (`eslint .` / `**/*`). Same for stylelint/prettier.
   - Route **slow** checks (`build`, full e2e, integration, Playwright visual) to on-demand
     `/wook-evaluate`, **NEVER the commit gate** — `build` in the gate makes every trivial commit
     slow. Mark **MANUAL** anything that can't be automated (don't fake a command).

4. **Get approval / edits** from the developer before writing anything.

5. **On approval, write the artifacts:**
   - Write `.claude/evaluate.recipe` as the **lean standing set** — do NOT blindly append to
     what's already there; **prune** redundant/old/slow lines so the gate stays fast and the
     recipe converges instead of growing. Note: editing the recipe triggers one `ask` prompt
     (guard_paths self-protection) — that prompt IS the developer approving the bar.
   - **Install the gate**: run `python ~/.claude/harness/install_gate.py` so
     `.git/hooks/pre-commit` runs the recipe on every commit (idempotent; it never overwrites
     a foreign pre-commit hook). Tell the developer the gate is armed, that
     `.claude/evaluate-off` disables it, and that `git commit --no-verify` bypasses it.
   - **Replace** `.claude/plan.md` with the CURRENT plan only — it holds the *in-flight* spec so
     it survives context loss, NOT a history of finished plans. Overwrite the previous plan; the
     permanent record of done work lives in `docs/build-log.md` (and the code/tests). Don't
     accumulate completed specs here. (While plan.md exists, its acceptance criteria are
     re-injected each turn by the plan-pointer hook, so keep that section tight.)

6. **Hand off to implementation.** Build against the spec. Do NOT claim done until the recipe
   passes — the **pre-commit gate** runs exactly these checks on `git commit` and blocks the
   commit until they pass (for any agent AND for human commits); `/wook-evaluate` gives a deeper
   on-demand verdict. The verdict is bound to real exit codes. The gate also refuses commits
   whose staged diff weakens the gate itself (recipe edits / test deletions) unless committed
   with `GATE_EDIT_OK=1` — an intentional bar change is a human decision.

## Rules

- Acceptance criteria must be **machine-checkable wherever possible** — that is the whole
  point; the Evaluator runs them. This is what makes "done" mean something here. Apply the
  two-person test: if two people could disagree whether a criterion is met, rewrite it as
  precondition → action → exact observable assertion.
- Keep scope tight and out-of-scope explicit.
- The recipe is a **small, stable, fast** set the gate runs on every commit — keep it
  *converging, not growing*. Feature criteria become tests (covered by the standing line);
  slow/visual checks go to `/wook-evaluate`, never the commit gate. Prune accumulated cruft
  when you touch it.
- The recipe you write is the contract. If the plan changes later, update it in the same breath
  so the gate never checks a stale bar.
