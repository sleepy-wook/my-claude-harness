---
name: wook-conventions
description: Use to set up or refresh a project's coding conventions for a domain (frontend/backend/db/infra/data/shared). Triggers: "set up conventions", "define the style guide / theme", "what are our frontend conventions", "establish conventions for <domain>", "refresh the conventions"; starting a new project that should follow a convention, or onboarding an existing codebase. Not for one-off edits.
---

# /wook-conventions — establish or extract a domain's conventions

Write a per-domain convention doc at `.claude/conventions/<domain>.md` so future turns
follow consistent rules (theme/colors, API shape, naming, etc.). The `inject_convention_pointer`
hook then surfaces it every turn; machine-checkable rules go into `.claude/evaluate.recipe`
so the gate enforces them.

A convention doc keeps RULES, not values — values live in the real source (a theme/tokens
file, a config), referenced by a `path:symbol` pointer so detail never goes stale.

## Step 0 — scope & mode

1. **Determine the domain** (frontend/backend/db/infra/data, or `shared` for cross-cutting:
   testing, security, logging/errors, git). Ask if ambiguous.
2. **Detect mode** by checking whether code for this domain already exists (look for the
   relevant files — e.g. frontend: components/styles/`*.css|tsx`):
   - **GREENFIELD** (no/empty domain code) → establish conventions FIRST, so coding follows them.
   - **BROWNFIELD** (domain code exists) → extract the de-facto conventions from the code.

## What each domain typically covers (a prompt, not a schema — infer the real categories)

- **frontend**: theme (light/dark), color tokens (primary/secondary/danger + hover/active/disabled), spacing scale, typography, component naming.
- **backend**: API response shape, error/HTTP policy, layering (controller/service/repo), naming, validation, logging, pagination.
- **db**: table/column naming, PK/FK conventions, timestamps, soft-delete, migration rules, indexes, enums.
- **infra**: resource naming, tagging, module structure, secrets handling, environment promotion.
- **data/ML**: pipeline/ETL structure, model/dataset naming, notebook conventions, analytics SQL.
- **shared** (cross-cutting, applies to every task): testing, security/auth, logging/observability, error handling, git (commit/branch).

Use this to know what to ASK (greenfield) or EXTRACT (brownfield) for the domain at hand. Other domains follow the same shape — adapt to the project.

## GREENFIELD — establish before coding
1. Propose a starter set of conventions **for this domain** (use the per-domain categories
   above), **one decision at a time** (multiple-choice where possible). Only what this domain
   needs — apply YAGNI.
2. Note where the real source-of-truth SHOULD live (e.g. a theme/tokens file for frontend, a
   schema/migrations dir for db). If it does not exist yet, say so and flag that it must be
   created when coding starts (don't fake a pointer).
3. Get approval, then write the doc (below).

## BROWNFIELD — extract from existing code
1. **Scan ONLY this domain's code** (frontend → frontend files only; backend → backend only;
   ignore the rest). Use read-only search (grep/Glob, or an Explore subagent for breadth —
   read, never write).
2. Pull out the de-facto conventions for this domain (per the categories above) and the real
   source files that hold them.
3. **Flag inconsistencies** rather than silently picking (e.g. frontend: "3 different blues
   found — choose the canonical one"; backend: "two error-response shapes in use — pick one";
   db: "both `createdAt` and `created_at` exist"). Let the developer decide.
4. Present the draft, get approval/edits, then write the doc.

## Write the doc — `.claude/conventions/<domain>.md`
- **Rules / guidance** (judgment): prose the AI should follow — e.g. frontend "primary for main
  CTAs", backend "errors return `{error, code}`", db "every table has `created_at`/`updated_at`".
- **Source pointers** (so values never go stale): compact lines, same form the stale-check
  hook reads — `- <name> · <one-line> · <path>:<symbol>` (same for every domain):
  ```
  - primary · main CTA, hover=-8% · src/theme/tokens.ts:primary      # frontend
  - error-shape · all API errors · src/http/errors.ts:ApiError        # backend
  ```
  `<path>:<symbol>` must actually resolve — re-read to confirm (no stale pointers).
- **Enforced rules**: for each machine-checkable rule, mark it `[강제: <check-name>]` in the
  doc AND propose the matching command for `.claude/evaluate.recipe` — use whatever tool fits
  the domain (frontend `style: npx stylelint …` banning raw hex; db `db-naming: python
  scripts/check_naming.py`; backend an eslint/test check). The doc↔gate stay paired.
- Create `.claude/conventions/` if missing — its presence turns the convention pointer on.

## Rules
- Keep it compact; values live in the pointed-at source, not duplicated here.
- Only stable, reusable conventions — not one-off choices.
- Enforce only rules that have a real checker; leave the rest as guidance (don't fake a gate).
- Re-run after conventions change so the doc stays current (or update it inline per core-rules).
