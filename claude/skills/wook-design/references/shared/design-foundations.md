# Design foundations — hard numbers (shared by web & app modes)

> Rules are anchored to numbers so they're checkable. Sources: ceorkm/mobile-app-ui-design,
> bergside/awesome-design-skills (adapted; stack-specific parts stripped).

## Color — 60/30/10
- 60% neutral base / 30% complementary / 10% brand·accent.
- Accent is **sparse and purposeful**: key badges, active indicators, progress, primary action.
- Text hierarchy by opacity: headings 100% · body 80% · secondary 60–70%.
- Subtle fills: accent at ~5% opacity for secondary buttons / soft highlights.
- Values come from the project's token source (see `.claude/conventions/frontend.md`) — never raw hex.

## Spacing — 8-point grid
- All spacing divisible by 8 or 4 (8, 12, 16, 24, 32, 48, 64, 80, 96).
- Related elements 16px → next logical group doubles (32px).
- Card internal padding 24–32px. Section vertical padding (web) 80–96px, 160px for major breaks.

## Typography
- ONE font family (two max). **Max 4 sizes, 2 weights.** Hierarchy via size/weight/opacity.
- Monospace for large numbers (scores, prices, timers).
- Text containers under 600px wide (readability).

## Interaction targets & accessibility
- Tap/click targets ≥ 44×44px (app mode: non-negotiable).
- WCAG 2.2 AA contrast, keyboard-first interactions, visible focus states.
- Required states per component: default, hover, focus-visible, active, disabled, loading, error.

## Emotional design (Peak-End Rule)
- Engineer ONE peak moment per flow (the delight) + a satisfying ending (clear feedback on completion).
- Everything else stays calm — peaks only read as peaks against restraint.

## Quality gates (expanded)
1. No rule depends on ambiguous adjectives alone — anchor to a token, threshold, or example.
2. Every accessibility statement must be testable in implementation.
3. Aesthetics-vs-accessibility conflicts → accessibility wins; flag the conflict explicitly.
4. End every design spec with a QA checklist executable in code review.
