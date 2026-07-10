---
name: wook-sandbox
description: Use to build a non-trivial frontend component/UI or backend feature in ISOLATION first — try it yourself, then graduate it into the real project — instead of wiring rough code straight into the app. Triggers: "build this in a sandbox", "prototype this component first", "let me try it before integrating", "scaffold X in isolation then merge". Not for trivial edits or when the change must land directly in existing wiring.
---

# /wook-sandbox — build in isolation → try it → graduate

Rough code wired straight into the real project is the failure this prevents. Instead you
build the piece **alone** in `sandbox/`, actually use it, iterate until you like it, and only
then **graduate** it into the codebase. On-demand skill (not a hook — zero cost unless called).

`sandbox/` is a throwaway scratch area, **gitignored** — it never pollutes the real project or
its history. The skill ensures `sandbox/` is in `.gitignore`.

## Step 0 — read the stack
Read `.claude/project-map.md` (`Stack & Run` / `How to exercise`) to learn how this project
runs, so the sandbox matches its real toolchain. No map → detect from package.json/pyproject/
compose and say what you assumed. Pick the isolation method from the **domain** of what's being
built (same domain-adaptive idea as the evaluator).

## Step 1 — scaffold the isolated piece → `sandbox/<name>/`
Build ONLY the thing, with mock data / fake inputs, not wired into production paths.

- **frontend** → a standalone entry that renders just this component with mock props.
  **Import the project's real palette/theme** (the token source `.claude/conventions/frontend.md`
  points at, e.g. `src/theme/tokens.ts`) — never hardcode colors. So what you see in the sandbox
  is visually identical to the real app, and graduation needs no color rework.
- **backend** → a standalone runnable (scratch script / isolated endpoint) that exercises the
  feature with fake inputs and **no production wiring** (no real DB/queue/services — use
  fakes/mocks). 
- **other (lib/util)** → a scratch script that calls the new API with representative inputs.

Ensure `sandbox/` is gitignored (add it if missing).

## Step 2 — let the developer actually use it
Hand over a real way to try it, don't just declare it built:
- **frontend** → start the dev server (Bash, background) and give the URL; if useful, dispatch
  the **wook-evaluator** to drive Playwright MCP and screenshot it so it's seen immediately.
- **backend** → give the `curl`/run commands (and their actual output) to exercise it.

## Step 3 — iterate in the sandbox
Refine against the developer's feedback **inside `sandbox/`** only. Nothing touches the real
project yet. Loop here until they're happy.

## Step 4 — graduate (approval-gated)
Only on the developer's OK:
- **Move** the piece to its real path in the project and wire it in (default: move, so the
  sandbox copy is removed; keep a copy only if asked).
- If it's reusable, add one line to the right `.claude/reuse-index/<domain>.md`
  (`name · one-liner · path:symbol`).
- Hand off to the normal flow — the change is now real code, so it goes through the
  independent evaluator and the commit gate like anything else.

## Rules
- **Isolation first, integration last.** Rough code never lands directly in the real project;
  it lives in gitignored `sandbox/` until the developer approves graduation.
- **The sandbox consumes the palette, it does not own it.** Frontend sandboxes import the
  project's real theme/tokens; the palette itself stays a project-wide convention.
- **Faithful trial.** The sandbox must run with the project's real toolchain/tokens so trying
  it there predicts the real thing — otherwise it's a useless preview.
- **Real inputs, no production side effects.** Exercise with mocks/fakes; never touch the real
  DB/services from the sandbox.
- **Graduation is deliberate and human-approved.** Never auto-merge sandbox code into the app.
