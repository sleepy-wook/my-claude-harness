---
name: wook-index
description: Use to build or refresh this project's reuse catalog (`.claude/reuse-index/<domain>.md`). Triggers: "index reusable code", "build the reuse catalog", "refresh the reuse index"; after adding shared utilities/components/queries worth reusing. Not for onboarding a whole repo (use wook-onboard) or one-off edits.
---

# /wook-index — build the reuse catalog

Scan the project and write a per-domain reuse manifest, so future turns reuse existing
code from a short index instead of re-reading everything or duplicating it. This is the
generator for the reuse catalog; the `inject_reuse_pointer` hook then surfaces the domains
automatically every turn.

## Steps

1. **Find the reusable surface.** Exported/public functions, UI components, hooks, shared
   utilities, named DB queries — the things genuinely worth reusing. Skip one-off internals,
   tests, and generated code.

2. **Group by DOMAIN.** Infer domains from the project (e.g. `frontend`, `backend`, `db`,
   `shared`) — not a fixed list. One manifest file per domain.

3. **Write one compact line per item:**
   ```
   - <name> · <one-line what it does> · <repo-relative-path>:<symbol>
   ```
   `<symbol>` is the function/component/class name — the pointer to the real source, which
   holds the full detail. NO code bodies in the manifest.

4. **Write each domain** to `.claude/reuse-index/<domain>.md` (create the dir). The manifest
   is an INDEX, not docs: one line each, compact.

5. **Verify pointers.** Every `path:symbol` must actually exist in the code. Re-read to
   confirm; drop or fix any entry that doesn't resolve (no stale pointers).

6. **Report** which domains and how many entries you wrote.

## Rules

- Compact above all — full detail lives in the real source the pointer names, so the index
  stays small and the detail never goes stale.
- Only include reusable, reasonably stable things. Churn-y internals add noise.
- Re-run after adding shared code so the index stays current.
- Activation is automatic: once `.claude/reuse-index/` exists, the reuse pointer hook tells
  every future turn which domains are available, and to check the relevant one before
  writing new code.
