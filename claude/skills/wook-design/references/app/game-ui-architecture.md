# Game UI architecture — when Phaser/canvas is involved

> Version-neutral principles (valid v3→v4). Do NOT assume Phaser 3 APIs — most ecosystem
> content is v3; verify anything API-level against the project's actual Phaser version.
> Source: openai/plugins game-studio phaser-2d-game (architecture only).

## DOM overlay vs canvas — the dividing line
- **DOM overlays** for: HUD, command menus, settings, narrative/dialog panels — anything
  with text density, status density, or responsiveness needs.
- **Canvas** for: the world, combat readability, motion. Only put UI in-canvas when the
  project explicitly needs in-canvas presentation (e.g. diegetic UI).
- Overlay mechanics: DOM layer absolutely positioned over the canvas, same fixed-ratio
  stage; `pointer-events: none` on the layer, `auto` on interactive elements, so the
  canvas still receives world input.

## State lives outside scenes (thin scenes)
- Gameplay state (rules, turn order, inventory, score, progression) lives in systems
  OUTSIDE Phaser scenes. Scenes adapt system state into sprites/camera/animation.
- One integration boundary: the scene reads simulation state and emits input actions
  back. Prefer deterministic system updates over scene-local mutation.
- Animation state derives from gameplay state — not ad-hoc sprite flags.

## View state is disposable
- Sprite containers, emitters, tweens, camera rigs = view state, NOT source of truth.
  Game state changes must never depend on a sprite or tween's lifetime.
- Use stable, human-readable asset manifest keys — never file paths sprinkled in code.

## Anti-patterns (verbatim from the source — all observed failures)
- Game rules inside `update()` loops without a system boundary.
- Scene-to-scene state passed through mutable global objects.
- HUD text rendered in the game canvas just because it is convenient.
- Asset paths embedded everywhere instead of a manifest layer.
- Overusing generic React dashboard patterns for game UI.

## Camera (presentation, not rules)
- Pick the model early: locked / follow / room-based / tactical-pan.
- Camera logic separate from game rules. Shake/hit-stop/parallax restrained — they must
  improve readability, never obscure it.
