# Web mode — desktop/responsive page layout

> For landing pages, dashboards, docs — wide viewport, vertical scroll.

## Page structure
- Landing rhythm: hero → proof (logos/numbers/testimonial) → features → deep-dive → CTA.
  One idea per section; each section earns its scroll.
- Section vertical padding 80–96px (160px at major narrative breaks). Content max-width
  bounded (text ≤600px, full layout typically ≤1200–1440px), centered.
- F-pattern scanning: key info and primary CTA on the left-to-right top sweep; don't hide
  the primary action below the fold on desktop.

## Hierarchy & density
- One primary CTA per screenful; secondary actions visually quieter (ghost/text buttons,
  accent at 5% fill).
- Cards: internal padding 24–32px, consistent radius from tokens, tonal separation over
  hard borders.

## Responsive
- Design desktop and mobile-web as the SAME system: spacing/type tokens shrink by scale,
  not by ad-hoc overrides. Check ~375px width before calling any page done.
- Collapse multi-column grids predictably (3→2→1); never let text containers exceed 600px.

## Motion
- Restrained: masked reveals, fades, gentle parallax. Motion supports reading order —
  it never competes with it. Respect `prefers-reduced-motion`.
