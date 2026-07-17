# Token roles — the contract every palette candidate must define

> The generator (`scripts/gen_palette.py`) and the preset library assume these role names.
> Values live in the emitted `tokens.css` as CSS custom properties; docs point at them.

| role | CSS var | what it is | contrast partner |
|------|---------|-----------|------------------|
| `base` | `--base` | app background (the 60%) | text, accent(large) |
| `surface` | `--surface` | panel/card background (the 30%) | text, textMuted, danger |
| `surface2` | `--surface2` | raised surface / hover | — |
| `border` | `--border` | low-contrast separators | — |
| `text` | `--text` | primary text (100%) | base, surface (need AA) |
| `textMuted` | `--text-muted` | secondary text | surface (need AA) |
| `accent` | `--accent` | THE 10% — CTA, active, highlights | accentInk, base |
| `accentInk` | `--accent-ink` | text/icon on accent | accent (need AA) |
| `danger` | `--danger` | destructive / error | surface |
| `success` | `--success` | positive / confirm | surface |

## Rules
- 60/30/10: `base` ≈60%, `surface`/`surface2` ≈30%, `accent` ≈10% (sparse — CTA, active, key numbers).
- **AA targets** (the generator checks): text/base ≥4.5, text/surface ≥4.5, textMuted/surface ≥4.5,
  accentInk/accent ≥4.5, accent/base ≥3 (large), danger/surface ≥4.5. A FAIL means fix the value.
- Text tiers by opacity (body 80%, secondary 60%) are a *rendering* choice on top of `text`;
  if you rely on them, verify the resulting contrast still passes — don't assume.
- Provide `dark`, `light`, or both. If both, the project is bi-themed and needs both token blocks.

## palettes.json shape
```json
{"palettes": [
  {"name": "midnight-laser", "mood": "dark, technical, restrained glow",
   "dark": {"base":"#0b0e12","surface":"#151a21","surface2":"#1d242d","border":"#262f3a",
            "text":"#eef3f7","textMuted":"#98a3b0","accent":"#34e0d0","accentInk":"#04120f",
            "danger":"#ff5c6c","success":"#49d17f"}}
]}
```
