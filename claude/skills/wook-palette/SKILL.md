---
name: wook-palette
description: Use to create a project's color theme/palette interactively — ask the developer about mood, then generate several candidate palettes, render them as a fixed-UI HTML with live previews and computed WCAG contrast, let them pick, and write the chosen palette to the project's tokens + conventions. Triggers: "make a palette", "pick a color theme", "generate theme options", "design the color system", "I need brand colors". Not for laying out a screen (that's ui-ux-pro-max's job) or one-off color tweaks.
---

# /wook-palette — build a color theme, together, ending in a visual you pick from

The token gate of the design flow: **ui-ux-pro-max (main design brain) recommends → this
skill verifies and mints the tokens** a project designs against. Interactive (tiki-taka),
variant-based, and it ends in a **fixed-UI palette HTML** so you choose by seeing, not by
reading hex. Whatever a recommendation's source — ui-ux-pro-max's palette database (breadth,
but contrast NOT verified there), the local preset library, or a fresh idea — it only becomes
`tokens.css` after the computed WCAG check here passes.

## Step 1 — tiki-taka: gather intent (don't dump a form)
Ask a FEW pointed questions, one exchange at a time — mood/feeling, light vs dark (or both),
industry/context, any brand color or reference screenshots, what to AVOID. Stop and confirm
if unclear; don't invent a brand.

## Step 2 — generate N candidates (variants, not rerolls)
Two seed sources — don't reinvent a known-good palette from scratch:
- **ui-ux-pro-max's palette search** (installed skill; e.g. its `search.py "<industry>"
  --design-system`) for breadth — treat its hex values as *candidates*, never as done
  (its palettes are not contrast-verified).
- **The local preset library** (`references/presets/library.json`, 12 AA-verified vibes) —
  copy a matching palette in as a starting candidate, then vary.
Compose a `palettes.json` with a
**variable number** of candidates (default ~4). Each candidate defines the full role set for
`dark` and/or `light`:
`base, surface, surface2, border, text, textMuted, accent, accentInk, danger, success`
(see `references/token-roles.md`). Make candidates genuinely DIFFERENT (vary the mood axis),
not near-duplicates — the point is a real choice.

## Step 3 — render the fixed-UI picker (the deliverable)
Run the deterministic generator — the HTML template is fixed, only the colors vary:
```
python <skill>/scripts/gen_palette.py palettes.json > palette.html
```
Each card shows: role swatches, a live mini-preview (heading/muted/primary/alert on the actual
colors), and a **computed WCAG contrast table with AA PASS/FAIL** (accessibility measured, not
eyeballed). Serve it (`python -m http.server`) and show the developer a screenshot — optionally
via the wook-evaluator so the render is independently confirmed.

## Step 4 — tiki-taka to convergence
The developer picks a number and requests tweaks ("#2 but a calmer accent"). Adjust that
candidate in `palettes.json` and re-render. Loop until they're happy. Keep it variants: change
one axis at a time.

## Step 5 — commit the choice to tokens + conventions
On the final pick:
- Emit the tokens the project designs against (turnkey):
  ```
  python <skill>/scripts/gen_palette.py palettes.json --css <index> --mode dark > <project>/…/tokens.css
  ```
  (repeat `--mode light` if the project is bi-themed). Put the file where the project's stack
  imports it (CSS custom properties work for HTML and Phaser DOM overlays alike).
- Update `.claude/conventions/frontend.md` so its color section **points at** that token source
  (`path:symbol`) — the doc holds rules, the token file holds values (values never go stale).
- Keep the rendered `palette.html` as the project's living palette reference if wanted.

## Rules
- **Contrast is computed, never eyeballed.** The generator prints WCAG AA PASS/FAIL; a palette
  with FAIL on text/surface is not done — fix it before it becomes tokens.
- **The palette HTML UI is FIXED**; only the color data varies (one deterministic template).
- **Variants over rerolls**; candidates must be meaningfully distinct.
- **tokens are the source of truth, conventions points at them** — same rule the rest of the
  harness follows. This skill produces tokens; it does not scatter raw hex into components.
- Don't fabricate a brand — ask.
