# Aesthetic method — how to define ONE cohesive visual mood

> One project = one aesthetic, written as a spec. Style: directive-declarative,
> sensory-but-buildable ("Build…", "Keep…", "Use…"). Source: MengTo/Skills prose style.

## The template (write the project's aesthetic in this shape)
```
## <aesthetic-name>
Visual target: <one sentence — the mood in plain words>
Implementation guidance:
- Build <surfaces/foundation> …
- Keep <accent/contrast discipline> …
- Use <shape language, radius, texture> …
Motion: <2-3 allowed motion patterns, restrained>
Tuning knobs: <the 1-2 axes that may vary per screen (e.g. warmer↔cooler)>
Avoid: <what this aesthetic is NOT — define it negatively>
```
- The **Avoid** list is not optional — an aesthetic is half-defined by what it refuses.
- Record the finished spec in `.claude/conventions/frontend.md` (values → token pointers).

## Fixed negative prompts (append to any generation/prompting)
- No logos, no watermarks.
- No extra text beyond provided copy. No gibberish typography.
- No second aesthetic mixed in "for variety".

## Variants > rerolls
- First pass: lock layout + hierarchy + copy (the "system").
- Each variant changes ONE variable: accent color, crop/angle, card arrangement, background tone.
- Never regenerate from scratch hoping taste appears — taste comes from the locked spec.

## References beat paragraphs
- Don't describe taste in 1000 words; collect 3-5 reference screenshots in the project
  (`refs/` or the design doc) and point at them. One screenshot carries fonts, spacing,
  colors, icons, and layout at once.

## Example presets (pick ONE per project, adapt, then delete the other from your spec)
### warm-minimal-light
Visual target: organized, premium calm — warm paper, not cold SaaS.
- Build the page on layered warm neutrals (beige/stone/cream) with very low-contrast
  borders and tonal separation instead of hard lines.
- Keep accent sparse: badges, active states, progress, primary action only.
Motion: masked text reveals, mild fade-ins, gentle background drift.
Tuning knobs: cooler stone ↔ warmer parchment.
Avoid: stark white layouts, cold gray 1px borders, heavy shadows, loud gradients.

### dark-technical-grain
Visual target: material darkness — technical, atmospheric, restrained glow.
- Build on near-black/charcoal with premium dark surfaces layered above.
- Introduce subtle ordered-dither / soft digital grain so darkness feels material, not flat.
- Keep glow cinematic and narrow: white-hot core, soft halo — never thick neon bars.
Motion: haze/bloom only around focal areas, never filling the screen.
Tuning knobs: grain intensity; glow hue.
Avoid: overwhelming bloom, neon-everything, flat #000 backgrounds, rainbow accents.
