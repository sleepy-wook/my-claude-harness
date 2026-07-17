# Aesthetic preset library — the menu

> 12 distinct, **AA-verified** vibes. Pick ONE per project (variants > rerolls). Palettes live in
> `library.json` (render all with `gen_palette.py library.json > library.html`; every palette passes
> WCAG AA — enforced by `tools/test_presets.py`). Aesthetics adapted **stack-neutral** from
> MengTo/Skills web-design presets (`source` per entry) — they are a starting point to tune, not law.
>
> Flow: user names a mood → match a preset here → read its block → seed `library.json`'s palette into
> `/wook-palette` (tweak & re-verify) → apply build/layout rules via the ui-ux-pro-max skill.

| slug | mode | when to reach for it |
|------|------|----------------------|
| warm-linen-minimal | light | warm, organized, unhurried — not cold enterprise white |
| archive-serif-reader | light | reading/editorial/archival, bookish, index navigation |
| stark-editorial-grid | light | refined agency/editorial, strict grid, dramatic type |
| emerald-console-dark | dark | modern technical data product, instrument-panel feel |
| laser-dither-noir | dark | atmospheric dark hero with a luminous accent motif |
| frosted-glass-blue | dark | premium glassy dashboard/hero with real depth |
| wireframe-diagnostic-mono | dark | diagnostic/teardown/annotated-systems look, monochrome |
| tactile-luxe-skeuo | dark | physically-assembled, touchable, high-contrast premium |
| gooey-fluid-organic | light | friendly, weightless, organic soft-body movement |
| arcade-fuchsia-play | dark | technical-but-funky, expressive, fashion-forward |
| sky-serene-air | light | calm aspirational landing with atmospheric sky |
| warm-paper-product | light | warm approachable product/onboarding, not cold SaaS |

---

## warm-linen-minimal · light
Calm parchment-and-stone surfaces, low-contrast structure, a single clay signal — quiet, premium, unhurried.
- Build the page on layered beige, stone, cream, and off-white surfaces separated only by very low-contrast borders and gentle tonal steps, never harsh black-on-white jumps.
- Keep a centered framed shell with a simple hero above and an even modular grid of equal blocks below.
- Use the accent as a signal color only — badges, active dots, progress, primary action — warm neutrals carry the rest.
- Type: modern sans, modest weight contrast, quiet tracking; thin dividers and soft washes over shadows.
- Motion: masked text reveals, mild fade-ins, slow radial background drift.
- Tuning: beige warmth (cool stone ↔ warm parchment); accent intensity.
- Avoid: stark white SaaS with cold gray borders · vintage paper distressing · heavy shadows / high-saturation accents.
- Source: clean-minimal-beige-light-mode, light-mode-paper-technical.

## archive-serif-reader · light
An open book of warm aged paper inside a quiet catalog frame — serif ink, mono index rails, scholarly, tactile.
- Center a lighter book-like reading surface (folio spread, soft center crease, edge shading, faint paper texture) inside a calmer shell.
- Let typography lead: display serif headings, readable serif body with generous line height, tracked mono labels for metadata/index.
- Surround the reading area with restrained catalog UI — chapter lists, section trees, archive groupings — with small active markers.
- Scholarly details sparingly: drop caps, pull quotes, marginal notes, thin-framed plates, footer folio labels; one accent in headings/active.
- Motion: calm masked reveals, gentle entrance, slow ambient drift.
- Tuning: antiquity (paper wear/warmth); index-rail density (airy ↔ dense).
- Avoid: flat cream cards with no book structure · bright modern SaaS color · heavy distress that hurts readability.
- Source: book-serif-index.

## stark-editorial-grid · light
Oversized black type on white, a disciplined grid, hairline rules and tiny uppercase labels — a confident agency spread.
- Build on a disciplined multi-column grid with large open spans, careful alignment, generous negative space.
- Anchor each view with oversized headlines (tight tracking, deliberate breaks) + very small uppercase metadata in adjacent columns.
- Surfaces near-white, thin separators, quiet image frames; large architectural photo blocks are the only imagery.
- One bold accent for one link/marker/CTA at a time — composition stays black, white, structural.
- Motion: masked reveals, slow image settle, restrained hover shifts.
- Tuning: headline scale/asymmetry; how much imagery competes with pure type.
- Avoid: generic startup hero blocks · card-heavy galleries/dashboards · decorative chrome around images.
- Source: agency-grid-layout-minimal, editorial-tech.

## emerald-console-dark · dark
Matte-black operational surfaces, emerald signal glow, mono labels and bracketed cards — a calm analytical instrument panel.
- Near-black base with subtle tonal lift between page/panels/cards; faint grid lines, corner brackets, tick marks, mono labels.
- Emerald as signal only — status dots, progress fills, active borders, graph highlights — controlled and localized.
- Cards: thin 1px shells, dark inner panels, small corner details, restrained inner glow (not flat rectangles).
- Clean sans headlines + mono for labels/IDs/timestamps so it reads instrumented.
- Motion: masked reveals, slight hover brightening, measured chart movement.
- Tuning: green intensity; technical density (guides/ticks/brackets).
- Avoid: full-screen green glow / hacker look · flat black with no hierarchy · multiple unrelated accents.
- Source: tech-green-dark-mode-modern, bright-green-tech-system-webgl.

## laser-dither-noir · dark
Near-black surfaces with ordered-dither grain and a thin white-hot magenta laser cutting the dark — cinematic, material, restrained.
- Near-black charcoal foundation + subtle ordered-dither / soft digital grain so darkness feels material, not flat.
- A thin laser motif (narrow white-hot core, soft halo, light haze) tinted with the accent — a compositional anchor, not a thick bar.
- Keep laser+grain fixed behind a higher content layer; crisp near-opaque cards with 1px gradient borders above.
- Neutral dark dominates; accent only in status chips, active tabs, icons, focal controls.
- Motion: slow soft beam pulse, faint haze drift, masked headline reveals.
- Tuning: dither density; laser intensity (beam thickness ↔ halo width).
- Avoid: thick neon bars / full-frame fog · heavy dither everywhere · flat black with no texture.
- Source: dither-laser-dark-mode, dither-background.

## frosted-glass-blue · dark
Deep navy-black with frosted translucent shells, gradient-lit borders, and a soft blue atmospheric beam — polished and expensive.
- Near-black navy base + fixed soft atmospheric glow behind the UI; float content above on a separate layer.
- Key panels frosted: translucent dark fill, backdrop blur, 1px gradient border, subtle inner top highlight, gentle shadow falloff.
- Floating blurred pill nav + framed max-width container with thin rails and tiny corner markers.
- Bright body text; blue selectively for active indicators, CTA emphasis, icon accents. Provide a solid-fill fallback where blur is unsupported.
- Motion: subtle card drift, soft beam pulse, gentle hover brightening, masked reveals.
- Tuning: glass depth (blur/opacity/edge highlight); blue hue (indigo ↔ electric cobalt).
- Avoid: pure-black overlays under blur · pastel/white glassmorphism · glow on every component.
- Source: glass-dark-ui, blue-laser-clean-glass-layout, mesh-gradient-dark-blue-clean.

## wireframe-diagnostic-mono · dark
Monochrome charcoal, exploded outline geometry, dashed connectors and sparse metric tags — a technical teardown with one amber signal.
- Near-black monochrome field, subtle texture, restrained tonal shifts; emphasis via brightness, line weight, placement — not color.
- Anchor with an exploded/layered outline object (edges and parts separated slightly), positioned like a diagram.
- Surround with floating info pills, dashed/routed connectors, sparse metric callouts — an annotated system view.
- Supporting UI diagnostic and minimal; reserve the single amber accent for one active readout.
- Motion: slow rotation/drift, staged label appearance, gentle connector updates.
- Tuning: line/annotation density; how much color escapes the monochrome.
- Avoid: generic sci-fi HUD decoration · filled/glossy 3D renders · multiple bright accents.
- Source: technical-wireframe-info-layout, split-layout-technical.

## tactile-luxe-skeuo · dark
Molded dark panels with inset highlights and reflective edges, a champagne signal light — industrial, tactile, high-contrast, premium.
- Deep charcoal shell, generous radius, premium shadow weight; subtle vertical/radial gradients so panels feel molded.
- Cards: thin white-to-transparent gradient borders, dark inner fills, stacked inset shadows, fine top-edge highlight (carved depth).
- High contrast — near-white text on dark shells, muted gray support; buttons/inputs look pressable (layered fill, soft bevel).
- One metallic signal accent for status lights, progress slivers, focal emphasis; quiet corner markers and guide rails keep it disciplined.
- Motion: masked reveals, gentle object lift, subtle highlight shimmer, slow orbiting detail.
- Tuning: skeuomorphic depth (bevel/inset strength); accent intensity.
- Avoid: washed-out mushy neumorphism · glossy chrome/leather/fake-material gimmicks · flat monochrome dark UI.
- Source: high-contrast-skeuomorphic-clean, skeuomorphic-ui.

## gooey-fluid-organic · light
Soft blush surfaces with fluid shapes that merge and separate as one continuous mass — playful, weightless, no hard edges.
- Light blush-and-white surface; the atmosphere is a fluid blob system: overlapping soft shapes that fuse/split by proximity, no hard edges.
- Achieve merging with blur-plus-threshold so forms read as one continuous organic mass (not separate blurred circles).
- Keep surrounding layout soft and rounded — generous radii, open spacing, buoyant pills — echoing the fluid background.
- One warm magenta-coral accent for actions/highlights; smooth cohesive motion with a static reduced-motion fallback.
- Motion: slow continuous blob drift (approach and separate), gentle fades.
- Tuning: merge visibility (blur/contrast/spacing); accent saturation.
- Avoid: fake gooeyness from plain blurred circles · fast jittery motion · sharp technical grids fighting the softness.
- Source: gooey-blob-system, atmosphere-background.

## arcade-fuchsia-play · dark
Near-black stage with vivid violet-fuchsia glow, layered rounded containers, and a playful floating focal orb — expressive and futuristic.
- Near-black base organized by large framed containers with visible boundaries, border rails, tiny corner squares.
- Violet-to-fuchsia accent family (optional blue undertones for depth); containers create hierarchy — pills, framed cards, inset panels, rails.
- One playful focal object (glowing orb, rotating text ring, ambient floor-light) to energize and concentrate bloom.
- Supporting UI technical with uppercase micro-labels; inputs and floating cards get dark tactile fills with accent hover.
- Motion: floating hero object, slow glow pulse, drifting line fields, gentle ring rotation, masked reveals.
- Tuning: purple mood (magenta ↔ cooler violet); funk factor (focal objects/bloom).
- Avoid: flat dark pages with accents but no container hierarchy · everything neon until focus is lost · many unrelated accents.
- Source: funky-purple-container-tech.

## sky-serene-air · light
A luminous blue-to-pale sky with soft drifting cloud light, thin white rails, and airy serene type — aspirational and weightless.
- Build around a rich blue-to-pale-blue sky atmosphere with soft cloud-like light drifting (richer at top, mistier below).
- Minimal framing — thin container rails, tiny corner squares, restrained nav — never boxed in.
- Refined airy type: large clean sans headlines with one word set in italic/serif for elegance, light body copy.
- Interface floats on translucent white details and buoyant pills; drop a grounded high-contrast CTA only where needed.
- Motion: masked word reveals, soft fades, slow cloud drift, subtle CTA hover scaling.
- Tuning: sky richness/gradient span; how grounded vs translucent the CTAs are.
- Avoid: generic flat SaaS blue · cartoon cloud theming · dense card systems / heavy dashboards.
- Source: blue-cloudy-clean-modern, atmosphere-background.

## warm-paper-product · light
Cream and parchment surfaces with a vivid orange signal, rounded premium forms and floating product cards — welcoming and polished.
- Warm off-white/cream/pale-stone surfaces (not stark white), wrapped in a large rounded container with a soft gradient border.
- Orange as primary signal/action — steps, buttons, active states, icons, focused inputs — energetic but disciplined, never full-page.
- High-quality light inputs: paper-toned fill, delicate borders, subtle focus rings, generous radius, soft shadow lift (tactile, not skeuo).
- Pair the functional panel with a polished product-illustration zone: warm gradients, floating stat chips, soft white UI cards.
- Motion: masked reveals, gently floating cards, smooth input focus transitions.
- Tuning: paper warmth (cream ↔ parchment); orange energy.
- Avoid: cold blue-gray SaaS · oversaturating with orange · vintage paper distress / noisy 3D objects.
- Source: orange-clean-paper-saas.
