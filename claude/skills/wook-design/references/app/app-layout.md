# App mode — mobile-ratio interactive screens (web tech)

> The ecosystem gap this skill fills: portrait-ratio interactive UI built with HTML/CSS
> (+ optionally Phaser), between desktop landing pages and native app screens.

## The frame
- Design at a fixed portrait baseline: 375×812 (or the project's chosen ratio). The
  screen IS the unit — no page scroll unless the screen explicitly scrolls a list.
- On larger/desktop viewports: letterbox the fixed-ratio stage (centered, side gutters)
  or scale it — pick one strategy per project and write it into conventions.
- Respect safe areas: top notch/status zone and bottom home-indicator zone get padding;
  nothing tappable inside them.

## Thumb zone
- Primary action lives in the bottom third, reachable by thumb. Destructive actions
  OUT of the easy-reach zone.
- Top of screen = status/context (read-only tier). Middle = content. Bottom = actions.

## Targets & density
- Tap targets ≥ 44×44px, ≥8px apart. Fewer, bigger controls beat dense toolbars.
- One primary action per screen. If a screen needs 5 buttons, the screen is 2 screens.

## Type & numbers
- Same token scale as the rest of the project, but check at arm's length: body ≥15-16px.
- Scores/timers/currency in monospace, large, high-contrast — they're the app's peaks.

## States & feedback
- Every interactive element: pressed state visible within 100ms (scale/opacity/fill).
- Async actions: optimistic or loading state — a dead tap is the #1 mobile-feel killer.
- Engineer the Peak-End: one delight moment (score pop, streak, completion) per flow.
