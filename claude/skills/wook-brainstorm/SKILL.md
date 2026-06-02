---
name: wook-brainstorm
description: Diverge BEFORE committing to a plan — explore options, surface tradeoffs, and widen the solution space when the problem or approach is still open. The step BEFORE the PGE loop. Use when the goal is fuzzy, multiple approaches exist, or you want to think before deciding. Triggers: "brainstorm", "what are my options", "how should I approach", "I'm not sure how to", "explore approaches for". Hands off to /wook-plan once a direction is chosen. Does NOT write code or a recipe.
---

# /wook-brainstorm — diverge before you plan

This is the step **before** the Planner→Generator→Evaluator loop. Its job is the opposite
of `/wook-plan`: where `wook-plan` *converges* (locks down "done" as runnable acceptance
criteria), `wook-brainstorm` *diverges* — it widens the option space while the right answer
is still unknown. It deliberately produces **no code and no recipe**; rushing to a recipe
before the approach is settled just locks in the wrong bar.

When the direction is clear, it hands off to `/wook-plan`, which writes the spec and recipe.

## When to use which

- **brainstorm** — the problem/approach is open: "how should I…", "what are my options",
  "I'm not sure", multiple designs compete. Goal: explore, don't decide yet.
- **plan** — the *what* is decided, you need to define "done": acceptance criteria → recipe.
- **neither** — a small edit, a lookup, or a question. Just do it (per core-rules).

## Steps

1. **Frame the problem, not the solution.** Restate the goal, the constraints, and what
   "good" would mean — *without* presupposing an approach. If the goal itself is unclear,
   ask 1-3 pointed questions first (do not guess).

2. **Widen the space (this is the point).** Produce **2-4 genuinely distinct approaches**,
   not minor variants of one. For each: the core idea, why it might be best, and its main
   cost/risk. Include at least one option the developer probably hasn't considered.
   - **Use read-only sub-agents to fan out** when exploration is broad (the safe sub-agent
     pattern — read, never write). Good fits:
     - `Explore` / `general-purpose` agent to map how the existing codebase already does
       similar things (so options fit reality, not theory);
     - a research agent for external prior art when the question is "how do people solve X".
     Dispatch several in parallel; you keep the conclusions, not the file dumps.

3. **Compare honestly.** Lay the approaches side by side on the axes that actually matter
   here (e.g. simplicity, risk, effort, reversibility, fit with the existing harness).
   Surface tradeoffs; do not pretend one option dominates if it doesn't.

4. **Recommend, but keep it the developer's call.** State which you'd pick and why, in one
   or two sentences. Then stop and let the developer choose or push back — this is a
   divergence tool, not a decision you make for them.

## Handoff

Once the developer picks a direction, **hand off to `/wook-plan`** to turn that choice into
a spec + `.claude/evaluate.recipe` (the front of the PGE loop). Do not write the recipe
here — naming the chosen approach and the open questions plan should resolve is enough.

## Rules

- **Diverge, don't converge.** If you find yourself writing acceptance criteria or a recipe,
  you've drifted into `wook-plan`'s job — stop and hand off instead.
- **No code, no files.** Brainstorm explores; it does not implement or write artifacts.
- **Distinct options, not strawmen.** Each approach must be one a reasonable engineer could
  actually choose; don't pad the list with options built to lose.
- **Honest tradeoffs over false confidence** — if the right answer genuinely depends on
  something unknown, say so and name what would resolve it.
</content>
