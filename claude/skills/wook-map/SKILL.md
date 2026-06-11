---
name: wook-map
description: Build or refresh this project's map at .claude/project-map.md — the living "structure + stack + how to run/exercise" doc the evaluator and future work read. Triggers: "build the project map", "refresh project-map", "document how to run this project", "onboard this repo"; or after the structure, stack, or run/build/test commands changed. Not for one-off edits.
---

# /wook-map — build the project map

Write/refresh `.claude/project-map.md` so the AI (especially the independent evaluator) knows
how the project is laid out and **how to run and exercise it** — instead of rediscovering it
every session. Sibling of `/wook-index` (reuse) and `/wook-conventions` (style).

Use the **fixed schema** (same sections, order, and YAML keys in every project — see
`~/.claude/harness/project-map.example`). Content/language is the project's; the schema isn't.

## Principle (from independent review)
Commands are a **cache of real sources**, not a second source of truth. Derive them and keep a
provenance pointer; tie smoke verification to the recipe; make staleness visible. Don't let this
file quietly contradict its own "facts only, point don't duplicate" header.

## Steps

1. **Detect the stack & layout.** Read `package.json` / `pyproject.toml` / `go.mod` /
   `docker-compose.yml` / `Makefile` etc. Use read-only search (grep/Glob, or an Explore
   subagent for breadth). Infer domains (frontend/backend/db/…) from what's actually there.

2. **Fill the fixed sections:**
   - **`## Stack & Run`** (fenced ```yaml):
     - `stack:` one-line per domain.
     - `env:` how to set up env + the REQUIRED vars (read `.env.example`). This is the most
       common reason an agent can't boot — don't omit it.
     - `services:` ports + external services that must be up/stubbed (db, Redis, Stripe test
       key, etc.). If none, say so.
     - `run.<domain>:` `install`/`dev`/`url`/`test`/`build` as they apply — **derive each from
       the real source and append `# <path>:<key>` provenance** (e.g.
       `dev: "pnpm -C web dev  # web/package.json:scripts.dev"`). Don't invent commands.
     - Stamp the section: `<!-- verified: <YYYY-MM-DD> @ <git sha> -->`.
   - **`## Structure`** (fenced ascii tree): **≤ 2 levels** — orientation, not a file listing.
   - **`## How to exercise`**: for the evaluator — the smoke flows per domain. Point `smoke
     (deterministic) = run .claude/evaluate.recipe` rather than re-listing shell checks; add
     the UI routes/flows, a **test login**, and key API calls. (Don't duplicate the recipe.)
   - **`## Entry points`**: only the 1–3 boot/root symbols, as `- <name> · <path>:<symbol>`.
     Pointers must resolve — re-read to confirm.

3. **Write** `.claude/project-map.md` (create `.claude/` if missing). Report what you filled.

## Rules
- Fixed sections/keys; shallow structure; commands carry provenance and aren't the source of truth.
- Only stable facts. Re-run (or update inline per core-rules) when structure/stack/run change.
- If something can't be verified (a command you didn't actually derive from a real file), say so —
  don't fabricate a confident-but-wrong command (worse than omitting it).
