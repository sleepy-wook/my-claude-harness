---
name: wook-design
description: Use when designing the LOOK and INTERACTION of a screen or page — a web landing/dashboard, or a mobile-ratio app/game screen (HTML/Phaser). Triggers: "design this screen/page", "make this UI look good", "define the visual direction", "design the HUD/menu", starting UI work where no visual spec exists yet. Two modes — web (desktop/responsive pages) vs app (mobile-ratio interactive screens). Not for backend, not for pure logic, not for choosing tech stack.
---

# /wook-design — design skill pack (web / app modes)

Design like a design system, not a wish: **specs beat vibes**. Every visual decision gets
anchored to a token, a number, or a reference — never an adjective alone. One project = ONE
cohesive aesthetic, written down as a spec the whole project follows.

## Step 0 — pick the mode, load the right references
- **web** — desktop/responsive web pages: landing, dashboard, docs. → read
  `references/shared/*` + `references/web/web-layout.md`
- **app** — mobile-ratio interactive screens in web tech (HTML/CSS/Phaser): game UI,
  app-like screens. → read `references/shared/*` + `references/app/app-layout.md`
  (+ `references/app/game-ui-architecture.md` when Phaser/canvas is involved)

Ambiguous? Ask which mode — don't guess. (The two modes have opposite layout physics:
web scrolls vertically on a wide viewport; app lives in a fixed portrait ratio.)

## Step 1 — context before pixels
App type, target user, the ONE primary action per screen, industry conventions.
**Tokens come from the project, not this skill**: use `.claude/conventions/frontend.md`
(and the token source it points at). No conventions yet? Propose `/wook-conventions
frontend` first so the palette has a home. Never hardcode raw hex in designs.

## Step 2 — structure first (UX), then visuals (UI)
Map the flow and hierarchy before any styling: MVP elements only, primary action placed
where the mode dictates (web: F-pattern scan path; app: thumb zone). Then apply visuals
in order — typography → color (60/30/10) → spacing (8pt grid) → depth/imagery.
Hard numbers live in `references/shared/design-foundations.md`; don't restate them from
memory, read them.

## Step 3 — one aesthetic, written as a spec
Define the project's single visual mood using `references/shared/aesthetic-method.md`:
declarative buildable sentences, a Tuning-knobs section, and an **Avoid** list that
defines the aesthetic negatively. Include the fixed negative prompts. Record the result
in the project's conventions doc — that becomes the source of truth, not this skill.

## Step 4 — iterate as variants, not rerolls
Lock the system (layout + hierarchy + copy) on the first pass. Then change **one
variable at a time** per variant (accent, density, arrangement). Never regenerate from
scratch hoping for taste.

## Step 5 — verify like the harness verifies
- Non-trivial UI → build it in **`/wook-sandbox`** first (isolated, project tokens
  imported), try it, then graduate.
- Before calling it done → **wook-evaluator** drives Playwright to actually view it
  (render, interactions, console clean).

## Quality gates (self-check before presenting any design)
- Every rule is anchored to a token, threshold, or example — no ambiguous adjectives.
- Every accessibility statement is testable in implementation (contrast, focus, targets).
- Aesthetics vs accessibility conflict → accessibility wins, flag the conflict.
- All interactive states defined: default, hover, focus-visible, active, disabled,
  loading, error (as relevant).
- The design references the project's tokens — zero raw hex.
