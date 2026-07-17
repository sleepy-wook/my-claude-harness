# Token roles — the ui-ux-pro-max schema (16 roles)

> The harness adopts **pro-max's vocabulary**, not its own. These names come from
> `~/.claude/skills/ui-ux-pro-max/data/colors.csv` (header order) and map 1:1 to the
> `--color-*` CSS variables its 22 stack generators emit against — so our tokens drop
> straight into its code output. `gen_palette.py`'s `SCHEMA` is the single definition;
> this doc explains it.

| CSV column | key | CSS variable | what it is |
|---|---|---|---|
| Primary | `primary` | `--color-primary` | main brand surface/button |
| On Primary | `on_primary` | `--color-on-primary` | ink on `primary` |
| Secondary | `secondary` | `--color-secondary` | secondary surface/button |
| On Secondary | `on_secondary` | `--color-on-secondary` | ink on `secondary` ← **dropped by renderer** |
| Accent | `accent` | `--color-accent` | **the CTA colour** |
| On Accent | `on_accent` | `--color-on-accent` | **ink on the CTA** ← **dropped by renderer** |
| Background | `background` | `--color-background` | page base |
| Foreground | `foreground` | `--color-foreground` | body text on `background` |
| Card | `card` | `--color-card` | raised surface ← **dropped** |
| Card Foreground | `card_foreground` | `--color-card-foreground` | text on `card` ← **dropped** |
| Muted | `muted` | `--color-muted` | subdued surface |
| Muted Foreground | `muted_foreground` | `--color-muted-foreground` | subdued text ← **dropped** |
| Border | `border` | `--color-border` | dividers/outlines |
| Destructive | `destructive` | `--color-destructive` | danger surface |
| On Destructive | `on_destructive` | `--color-on-destructive` | ink on danger ← **dropped** |
| Ring | `ring` | `--color-ring` | focus ring |

**The renderer trap:** `design_system.py` prints only 10 of these — it drops the 6 marked
above. Read the CSV (`--from-promax`), never the printed table: the dropped roles are exactly
where contrast failures live, and an agent that cannot see `on_accent` guesses white — a
green CTA at **2.28:1**, which is how this trap was actually found (2026-07-17).

## Enforced pairs (what `--check` computes)

Text pairs — **fail the gate below 4.5:1**:

| pair | why |
|---|---|
| `on_primary` / `primary` | button label |
| `on_secondary` / `secondary` | secondary button label |
| `on_accent` / `accent` | **CTA label — pro-max fails this in 113/192 palettes** |
| `on_destructive` / `destructive` | danger button label |
| `foreground` / `background` | body text |
| `card_foreground` / `card` | text on cards |
| `muted_foreground` / `muted` | secondary text |

Non-text — **warned, not enforced**:

| pair | why warn only |
|---|---|
| `border` / `background` (3:1) | WCAG 1.4.11 covers boundaries needed to *identify* a component; a decorative divider isn't one. pro-max fails it 173/192 — enforcing would be noise, not safety. |

## Notes

- **19 cells are `rgba(...)`** (all in Border) — `--check` skips non-hex values with a notice
  instead of crashing.
- Values live in `tokens.css`; convention docs point at it (`path:symbol`) and never restate a hex.
- `--fix` adjusts **ink only**, preferring an anchor already in the palette
  (`background`/`foreground`/`card`) over a synthesised value — this rederives the designer's
  own choice rather than landing on muddy greys.

## palettes.json shape (candidate picker)

```json
{"palettes": [
  {"name": "midnight-ops", "mood": "dark, technical, restrained glow",
   "roles": {"primary":"#1E293B","on_primary":"#FFFFFF","secondary":"#334155",
             "on_secondary":"#FFFFFF","accent":"#22C55E","on_accent":"#0F172A",
             "background":"#0F172A","foreground":"#F8FAFC","card":"#1B2336",
             "card_foreground":"#F8FAFC","muted":"#272F42","muted_foreground":"#94A3B8",
             "border":"#475569","destructive":"#EF4444","on_destructive":"#171717",
             "ring":"#1E293B"}}
]}
```
