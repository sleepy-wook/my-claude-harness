---
name: wook-palette
description: Use when a project needs its color tokens minted or verified — after ui-ux-pro-max recommends a design system, or whenever tokens.css / theme colors are created or changed. Triggers: "make a palette", "pick a color theme", "set up design tokens", "check contrast", "these colors accessible?", "generate theme options". Not for laying out a screen or choosing a visual style (that is ui-ux-pro-max's job).
---

# /wook-palette — the AA gate over ui-ux-pro-max's tokens

**ui-ux-pro-max is the design brain; this skill is the check it doesn't have.** It owns the
schema and the taste (84 styles / 192 palettes / 22 stacks). We add the one thing it lacks:
contrast that is **computed and bound to an exit code**, so a failing palette cannot reach the
project.

The harness speaks **pro-max's vocabulary**, not its own — the 16 `--color-*` roles below —
so its stack code-gen consumes our tokens unchanged. No translation layer.

## Why read its CSV, not its printed table (measured 2026-07-17)

- `data/colors.csv` has **16 roles**; its renderer prints **10**, silently dropping
  `On Secondary` / **`On Accent`** / `Card` / `Card Foreground` / `Muted Foreground` /
  `On Destructive`. An agent reading the printed table sees no on-accent colour, guesses
  white, and ships a **CTA at 2.28:1** — this actually happened here. The CSV had the right
  answer (`#0F172A`, 7.83:1) all along.
- Its values are still unverified: **571 of 1517** semantically-correct pairs across the 192
  rows fail AA (`On Accent/Accent` alone: 113). Breadth is theirs, verification is ours.

## Step 1 — let pro-max design (don't duplicate it)

Run its design system first; that is the source of taste, pattern, style and typography:
```
python ~/.claude/skills/ui-ux-pro-max/scripts/search.py "<product> <industry> <keywords>" --design-system
```
If the developer wants the design system persisted, use its `--persist` — **`design-system/MASTER.md`
is pro-max's source of truth and stays that way.** We do not copy it into our docs.

## Step 2 — pull ALL 16 roles from the CSV

Never retype colours off the printed table (it hides 6 roles):
```
python <skill>/scripts/gen_palette.py --from-promax "<product type>" > tokens.css
```
Roles: `primary, on-primary, secondary, on-secondary, accent, on-accent, background,
foreground, card, card-foreground, muted, muted-foreground, border, destructive,
on-destructive, ring` (see `references/token-roles.md`).

## Step 3 — compute the contrast (the gate)

```
python <skill>/scripts/gen_palette.py --check tokens.css     # exit 1 if any text pair < AA
python <skill>/scripts/gen_palette.py --fix   tokens.css > tokens.css.new
```
- `--check` fails ONLY on text pairs (4.5:1). `border/background` is reported as a **warning**:
  WCAG 1.4.11 covers boundaries needed to *identify* a component, not decorative dividers —
  and pro-max fails it 173/192 times, so enforcing it would be noise.
- `--fix` adjusts **only the ink** (`on-*`/foreground); the brand colour is never touched.
  It reuses the palette's own anchors (background/foreground/card) before inventing a value —
  which reproduces the designer's actual choice (it independently rederived pro-max's
  `#0F172A` for on-accent).

## Step 4 — offer a real choice when the direction is open

For several candidates, build a `palettes.json` (`{"palettes":[{"name","mood","roles":{…16…}}]}`)
and render the fixed-UI picker — swatches, a live preview, and a computed AA table per card:
```
python <skill>/scripts/gen_palette.py palettes.json > palette.html   # serve + view
python <skill>/scripts/gen_palette.py palettes.json --css 2 > tokens.css
```
Seed candidates from pro-max rows (`--from-promax`) and vary one axis at a time — variants,
not rerolls. Have the **wook-evaluator** view the render if an independent look is wanted.

## Step 5 — arm the gate, then point at the source

- Put `tokens.css` where the project's stack imports it (CSS custom properties work for
  HTML, React and Phaser DOM overlays alike).
- **Add the check to `.claude/evaluate.recipe`** so the commit gate enforces it from now on:
  ```
  tokens-aa: python ~/.claude/skills/wook-palette/scripts/gen_palette.py --check <path>/tokens.css
  ```
  (Editing the recipe prompts once — that prompt IS the developer approving the bar. If the
  repo has no gate yet: `python ~/.claude/harness/install_gate.py`.)
- In `.claude/conventions/frontend.md`, **point at both sources** — pro-max's
  `design-system/MASTER.md` for the design rules, and `tokens.css:` for the values. Rules in
  docs, values in tokens; the doc never restates a hex.

## Rules

- **Contrast is computed, never eyeballed** — and never taken on trust from a recommendation.
  pro-max's own §1 calls 4.5:1 CRITICAL; it just doesn't measure. We measure.
- **Their schema, their names.** Don't invent a parallel vocabulary — `--color-*` is what
  their 22 stacks generate against.
- **Their MASTER.md owns the design; our tokens own the values.** Don't fork the design system
  into our docs.
- `--fix` touches ink only. A brand colour that can't carry legible text is a *design*
  decision — surface it to the developer, don't silently repaint it.
- Don't fabricate a brand — ask.
