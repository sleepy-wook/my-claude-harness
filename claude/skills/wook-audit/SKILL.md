---
name: wook-audit
description: Use to exhaustively audit an entire directory tree file-by-file and keep a living, resumable audit ledger under `.claude/audit/`. Triggers: "audit this codebase", "full scan of <dir>", "go through every file and record issues", "build/refresh the audit ledger", "review the whole repo for code rules and problems". A heavy, whole-tree pass — NOT a diff review (use /code-review) and NOT a one-pass bootstrap (use /wook-onboard).
---

# /wook-audit — exhaustive, resumable audit ledger for a whole tree

This walks **every file** under a target directory and maintains a *living ledger* in
`.claude/audit/`. It is deliberately heavy. It is **audit-only** — it records what it
observes and never edits code. Two files do the work, and both are updated continuously
across runs:

- **`coverage.md`** — the full file tree with a checkbox per file. Each file flips
  `⬜ → ✅` as it is reviewed. This IS the resume mechanism: a re-run continues at the
  unchecked files instead of starting over.
- **`findings.md`** — the observed code rules, styles, and problems, accumulated and
  deduped across runs.

It is **descriptive, not prescriptive.** `findings.md` says "this is how the code *is*";
`.claude/conventions/` says "this is how we agree to write it." Keep them separate — this
skill never writes to `conventions/`. (A human may later promote a finding into a
convention; that's a separate, deliberate act.)

## Step 0 — locate target and ledger
- **Target** = the directory argument, or the project root if none given.
- Ledger lives in `<project>/.claude/audit/` (create it if missing). **Resume, never
  clobber:** if `coverage.md`/`findings.md` already exist, load them and continue — do
  NOT regenerate from scratch or drop existing findings.

## Step 1 — build / refresh the coverage tree
- Enumerate files under the target. **Skip** vendored/generated/binary paths — honor
  `.gitignore`, and skip `.git`, `node_modules`, `dist`, `build`, `.venv`, `__pycache__`,
  lockfiles, images/binaries. Say what you skipped.
- Write/refresh `coverage.md` as a tree where every reviewable file is a checkbox line.
  On a refresh: add new files as `⬜`, keep `✅` for already-reviewed files, and re-mark a
  file `⬜ (changed)` if it changed since its review (e.g. git status / mtime).

```
# Audit coverage — <target>   (updated <date>)
Reviewed: 12 / 87    Skipped (vendored/generated): node_modules/, dist/
## src/api
- [x] src/api/users.py        ✅ 2026-06-30
- [ ] src/api/orders.py
## src/web
- [ ] src/web/App.tsx
```

## Step 2 — review file-by-file (heavy; batch + fan out)
- Go through `⬜` files. For a large tree, **fan out read-only subagents** (Explore /
  general-purpose — they read, never write) in batches; each returns observations, you
  assemble. Keep the *writing* of both ledger files in your own hands so they don't race.
- **Bound each run.** Don't try to read an entire huge repo in one shot — process a batch,
  update both files, and report how many remain (`Reviewed 40/87 — re-run to continue`).
  The checklist guarantees the next run picks up where this one stopped.
- For each file, record into `findings.md` anything worth keeping: the de-facto code
  rules/style it follows, and concrete problems (bugs, smells, dead code, inconsistency,
  security/perf risks). Then check the file off in `coverage.md`.

## Step 3 — maintain findings.md (accumulate, dedup, organize)
Keep it organized so it stays useful as it grows — group by category, note where each was
seen, and **merge duplicates** instead of appending the same observation per file.

```
# Audit findings — <target>   (updated <date>)
> Observed (descriptive), NOT agreed rules. Agreed style lives in .claude/conventions/.

## Conventions & style (as observed)
- snake_case for funcs, PascalCase for classes — consistent across src/api  · e.g. users.py
- API handlers return `(data, status)` tuples · src/api/*

## Problems & risks
- [high] SQL built by f-string — injection risk · src/api/orders.py:42
- [med]  duplicate date-format helper in 3 files · utils/date.py, web/fmt.ts, api/util.py
- [low]  dead import `os` · src/api/users.py:3
```

## Step 4 — report
- Summarize: reviewed N / total, remaining, new findings this run, and whether another run
  is needed to finish. Point to `.claude/audit/coverage.md` and `findings.md`.

## Rules
- **Audit-only.** Never edit code, never run tests/builds (that's `/wook-evaluate`), never
  write to `.claude/conventions/`. Observe and record.
- **Resumable & idempotent.** `coverage.md` is the source of truth for progress; always
  resume from it. Re-running must not lose `✅` marks or accumulated findings.
- **Heavy is fine, but bounded per run.** Batch + report remaining rather than blowing
  context trying to read everything at once.
- **Descriptive, deduped, organized.** findings.md records what *is*, merges duplicates,
  and groups by category + severity so it stays readable as it grows.
- **Skip the noise.** Vendored/generated/binary paths are excluded and named, not audited.
