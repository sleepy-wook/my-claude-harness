---
name: evaluate
description: Verify that the current change actually works by running its tests, lint, and build in an independent context — verdict bound to real exit codes, not vibes. Use when asked to "evaluate", "verify this works", "did the tests actually pass", or before claiming a task is done.
---

# /evaluate — run the independent Evaluator

This skill enforces the harness rule: **a change is not "done" until an independent
Evaluator has run its tests/lint/build and seen them pass.** It exists to kill the
"claimed done without actually running the tests" failure mode.

## How to run it

1. **Determine the scope.** Default = the change just made in this session (the files
   touched / the feature requested). If the user named a target (a dir, a module,
   "the whole project"), use that.

2. **Dispatch the `evaluator` subagent** (do NOT evaluate inline — independence is the
   point; the context that wrote the code must not grade itself). Use the Agent tool:
   - `subagent_type: "evaluator"`
   - prompt: state the scope and the working directory, e.g.
     "Evaluate the change to <scope> in <cwd>. Run the project's tests, lint, and build
     and return your verdict."

3. **Relay the verdict honestly.** Show the Evaluator's `VERDICT` line and its gate
   results to the user verbatim — do not soften FAIL/INCONCLUSIVE into PASS.

4. **Act on the result:**
   - **PASS** → the change is verified; safe to call it done.
   - **FAIL** → take the Evaluator's specific failures as the next to-do. Fix, then run
     `/evaluate` again. (You may loop, but stop and ask the developer if you are not
     converging — repeated failures or oscillation.)
   - **INCONCLUSIVE** → no real test gate ran. Do NOT claim done. Tell the developer what
     is missing (e.g. no tests exist) and ask how to proceed.

## Hard rule

Never report a task complete on the basis of this skill unless the Evaluator returned
**PASS** with at least the test gate actually run. "The Evaluator couldn't find tests" is
not a pass.
