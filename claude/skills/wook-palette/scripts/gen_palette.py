#!/usr/bin/env python3
"""Verify / repair / emit design tokens in the **ui-ux-pro-max schema**.

The harness adapts to pro-max, not the other way round: pro-max is the design brain
(84 styles / 192 palettes / 22 stacks) and owns the vocabulary — this script speaks its
16 `--color-*` roles so its stack code-gen consumes our tokens unchanged. What we add is
the one thing it does not do: **compute** WCAG contrast, repair what fails, and bind the
result to an exit code the commit gate can enforce.

Why we read its CSV instead of its rendered output (measured 2026-07-17):
  - `data/colors.csv` carries **16 roles**, but `design_system.py`'s renderer prints only
    10 — it silently drops On Secondary / **On Accent** / Card / Card Foreground /
    Muted Foreground / On Destructive. An agent reading the rendered table sees no
    on-accent colour, guesses white, and ships a CTA at 2.28:1. The CSV had the right
    answer (#0F172A, 7.83:1) all along.
  - Its values are still unverified: of 1517 semantically-correct pairs across 192 rows,
    **571 (37.6%) fail AA** — On Accent/Accent alone fails 113 times. Hence --check/--fix.

Usage:
  gen_palette.py --check <tokens.css|tokens.json>     # exit 1 if any TEXT pair < AA
  gen_palette.py --fix   <tokens.css|tokens.json>     # repaired tokens on stdout
  gen_palette.py --from-promax "<product type>"       # pull a row (all 16 roles) as tokens
  gen_palette.py palettes.json                        # picker HTML (candidates)
  gen_palette.py palettes.json --css N                # tokens.css for candidate N

palettes.json schema: {"palettes": [{"name": ..., "mood": ..., "roles": {<16 roles>}}, ...]}
"""

import csv
import json
import os
import re
import sys
from pathlib import Path


def _utf8_stdout():
    """Our own output contains em-dashes; the gate runs us with stdout piped, and on a
    Windows console/pipe that defaults to cp949 a plain print() raises UnicodeEncodeError.
    Because the gate is (correctly) fail-closed, that crash would block EVERY commit —
    which is exactly what shipped on 2026-07-17 and only stayed hidden because the test
    runner injects PYTHONIOENCODING=utf-8. Every script the gate executes must do this."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


_utf8_stdout()

# --- pro-max's schema (data/colors.csv header order) -------------------------
# CSV column -> our canonical key -> the CSS variable pro-max's stacks expect.
SCHEMA = [
    ("Primary", "primary", "--color-primary"),
    ("On Primary", "on_primary", "--color-on-primary"),
    ("Secondary", "secondary", "--color-secondary"),
    ("On Secondary", "on_secondary", "--color-on-secondary"),
    ("Accent", "accent", "--color-accent"),
    ("On Accent", "on_accent", "--color-on-accent"),
    ("Background", "background", "--color-background"),
    ("Foreground", "foreground", "--color-foreground"),
    ("Card", "card", "--color-card"),
    ("Card Foreground", "card_foreground", "--color-card-foreground"),
    ("Muted", "muted", "--color-muted"),
    ("Muted Foreground", "muted_foreground", "--color-muted-foreground"),
    ("Border", "border", "--color-border"),
    ("Destructive", "destructive", "--color-destructive"),
    ("On Destructive", "on_destructive", "--color-on-destructive"),
    ("Ring", "ring", "--color-ring"),
]
KEYS = [k for _, k, _ in SCHEMA]
CSV_OF = {k: c for c, k, _ in SCHEMA}
VAR_OF = {k: v for _, k, v in SCHEMA}
KEY_OF_VAR = {v: k for _, k, v in SCHEMA}

# Pairs the schema *means*. `enforced=False` => reported but never fails the gate:
# WCAG 1.4.11 (3:1) covers boundaries needed to IDENTIFY a component — a decorative card
# divider isn't one, and pro-max fails it 173/192 times. Warn, don't block (2026-07-17).
PAIRS = [
    ("on_primary", "primary", False, True),
    ("on_secondary", "secondary", False, True),
    ("on_accent", "accent", False, True),
    ("on_destructive", "destructive", False, True),
    ("foreground", "background", False, True),
    ("card_foreground", "card", False, True),
    ("muted_foreground", "muted", False, True),
    ("border", "background", True, False),  # non-text: warn only
]

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
PROMAX_CSV = (
    Path(os.path.expanduser("~")) / ".claude/skills/ui-ux-pro-max/data/colors.csv"
)


# --- contrast math (the part pro-max has only as prose) ----------------------


def _lin(c: float) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexstr: str) -> float:
    h = hexstr.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    hi, lo = luminance(fg), luminance(bg)
    if lo > hi:
        hi, lo = lo, hi
    return round((hi + 0.05) / (lo + 0.05), 2)


def aa(ratio: float, large: bool = False) -> bool:
    return ratio >= (3.0 if large else 4.5)


def is_hex(v) -> bool:
    """pro-max ships 19 rgba() cells (all in Border) — tolerate, never crash."""
    return bool(v and HEX.match(str(v).strip()))


# --- audit ------------------------------------------------------------------


def audit(roles: dict) -> dict:
    """Return {'fails': [...], 'warns': [...], 'skipped': [...]} over the schema pairs."""
    out = {"fails": [], "warns": [], "skipped": []}
    for fg, bg, large, enforced in PAIRS:
        a, b = roles.get(fg), roles.get(bg)
        if not (is_hex(a) and is_hex(b)):
            if a or b:
                out["skipped"].append(f"{fg}/{bg} (non-hex or missing)")
            continue
        r = contrast(a, b)
        if not aa(r, large):
            (out["fails"] if enforced else out["warns"]).append((f"{fg}/{bg}", r, a, b))
    return out


# --- repair -----------------------------------------------------------------


def _shift(hexstr: str, toward_white: bool, step: int) -> str:
    h = hexstr.lstrip("#")
    ch = [int(h[i : i + 2], 16) for i in (0, 2, 4)]
    ch = [
        min(255, c + step) if toward_white else max(0, c - step)  # noqa: E501
        for c in ch
    ]
    return "#%02X%02X%02X" % tuple(ch)


def repair(roles: dict) -> tuple:
    """Fix failing TEXT pairs by moving the `on-*`/foreground colour only.

    The brand colour (accent/primary/destructive background) is never touched — that is
    the designer's choice; only the ink on top of it is ours to adjust.

    Ink is chosen in the palette's own vocabulary first: try the existing anchors
    (background / foreground / card) before inventing a new value. That is what a designer
    actually does — and it reproduces pro-max's own answer (its on_accent for the OLED row
    IS the background, #0F172A). Blind channel-shifting is the last resort because it
    lands on muddy greys (#FFFFFF -> #3F3F3F) that belong to no palette.
    """
    roles = dict(roles)
    changed = []
    for fg, bg, large, enforced in PAIRS:
        if not enforced:
            continue
        a, b = roles.get(fg), roles.get(bg)
        if not (is_hex(a) and is_hex(b)) or aa(contrast(a, b), large):
            continue
        orig, best = a, None

        # 1. reuse an anchor already in this palette (highest contrast wins)
        anchors = [
            roles.get(k) for k in ("background", "foreground", "card", "primary")
        ]
        ok = [c for c in anchors if is_hex(c) and aa(contrast(c, b), large)]
        if ok:
            best = max(ok, key=lambda c: contrast(c, b))

        # 2. otherwise nudge the original ink until it passes
        if best is None:
            toward_white = luminance(b) < 0.18
            for step in range(8, 256, 8):
                cand = _shift(a, toward_white, step)
                if aa(contrast(cand, b), large):
                    best = cand
                    break

        # 3. extreme palettes: pure black/white, whichever reads better
        if best is None:
            best = max(("#FFFFFF", "#000000"), key=lambda c: contrast(c, b))

        roles[fg] = best
        changed.append((fg, orig, best, contrast(best, b)))
    return roles, changed


# --- io ---------------------------------------------------------------------


def load_tokens(path: str) -> dict:
    """Read roles from a tokens.css (--color-* vars) or a flat/nested json."""
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".json"):
        data = json.loads(text)
        data = data.get("roles", data)
        return {k: data[k] for k in KEYS if k in data}
    roles = {}
    for var, key in KEY_OF_VAR.items():
        m = re.search(rf"{re.escape(var)}\s*:\s*([^;]+);", text)
        if m:
            roles[key] = m.group(1).strip()
    return roles


def emit_css(roles: dict, name: str = "tokens") -> str:
    # State the MEASURED status, never a blanket "verified" claim — these values may come
    # straight from pro-max, whose palettes fail AA in 571/1517 pairs. Claiming verification
    # before verifying is the exact thing this harness exists to prevent.
    a = audit(roles)
    status = (
        "WCAG AA: PASS (all enforced text pairs)"
        if not a["fails"]
        else "WCAG AA: **FAIL** — "
        + ", ".join(f"{n} {r}:1" for n, r, _, _ in a["fails"])
        + "  → run: gen_palette.py --fix"
    )
    lines = [
        f"/* {name} — ui-ux-pro-max schema (--color-*)",
        f" * {status}",
        " * Values live here; components reference var(--color-*), never raw hex. */",
        ":root {",
    ]
    for k in KEYS:
        if k in roles:
            lines.append(f"  {VAR_OF[k]}: {roles[k]};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def from_promax(query: str) -> dict:
    """Pull ALL 16 roles for the best-matching row — the renderer only shows 10."""
    if not PROMAX_CSV.exists():
        sys.stderr.write(f"gen_palette: pro-max CSV not found at {PROMAX_CSV}\n")
        return {}
    rows = list(csv.DictReader(PROMAX_CSV.open(encoding="utf-8")))
    q = query.lower().split()
    best, score = None, -1
    for r in rows:
        hay = (r.get("Product Type", "") + " " + r.get("Notes", "")).lower()
        s = sum(1 for t in q if t in hay)
        if s > score:
            best, score = r, s
    return {k: (best.get(CSV_OF[k]) or "").strip() for k in KEYS} if best else {}


def report(roles: dict, label: str) -> int:
    a = audit(roles)
    for name, r, fg, bg in a["warns"]:
        print(f"  [warn] {name:32} {r:>6}:1  ({fg} on {bg}) — non-text, not enforced")
    for s in a["skipped"]:
        print(f"  [skip] {s}")
    if not a["fails"]:
        print(f"TOKENS AA OK: {label} — all enforced text pairs pass WCAG AA.")
        return 0
    print(f"TOKENS AA FAIL: {label} — {len(a['fails'])} text pair(s) below WCAG AA:")
    for name, r, fg, bg in a["fails"]:
        print(f"  - {name:32} {r:>6}:1  ({fg} on {bg})  needs 4.5")
    print(
        "\n  Fix: python gen_palette.py --fix <tokens> > <tokens>  (adjusts the ink only)"
    )
    return 1


# --- picker HTML (candidate comparison) --------------------------------------


def contrast_rows(roles: dict) -> str:
    out = []
    for fg, bg, large, enforced in PAIRS:
        a, b = roles.get(fg), roles.get(bg)
        if not (is_hex(a) and is_hex(b)):
            continue
        r = contrast(a, b)
        ok = aa(r, large)
        badge = "PASS" if ok else ("WARN" if not enforced else "FAIL")
        cls = "ok" if ok else ("warn" if not enforced else "bad")
        out.append(
            f'<tr><td>{fg} / {bg}</td><td class="num">{r}:1</td>'
            f'<td class="badge {cls}">{badge}</td></tr>'
        )
    return "\n".join(out)


def swatches(roles: dict) -> str:
    out = []
    for k in KEYS:
        if not roles.get(k):
            continue
        out.append(
            f'<div class="sw"><span class="chip" style="background:{roles[k]}"></span>'
            f'<span class="rk">{k}</span><span class="hx">{roles[k]}</span></div>'
        )
    return "\n".join(out)


def preview(roles: dict) -> str:
    g = roles.get
    return f"""
    <div class="pv" style="background:{g("background")};color:{g("foreground")};border:1px solid {g("border")}">
      <div class="pv-panel" style="background:{g("card")};border:1px solid {g("border")}">
        <div class="pv-h" style="color:{g("card_foreground")}">Heading text</div>
        <div class="pv-m" style="color:{g("muted_foreground")}">Muted secondary line</div>
        <div class="pv-row">
          <span class="pv-btn" style="background:{g("accent")};color:{g("on_accent")}">Primary CTA</span>
          <span class="pv-badge" style="background:{g("destructive")};color:{g("on_destructive")}">Alert</span>
        </div>
      </div>
    </div>"""


def card(i: int, pal: dict) -> str:
    roles = pal.get("roles", {})
    return f"""
    <section class="card">
      <header class="card-h"><span class="idx">#{i}</span>
        <span class="name">{pal.get("name", "palette")}</span>
        <span class="mood">{pal.get("mood", "")}</span></header>
      <div class="mode">
        {preview(roles)}
        <div class="swatches">{swatches(roles)}</div>
        <table class="ct"><thead><tr><th>contrast</th><th>ratio</th><th>AA</th></tr></thead>
          <tbody>{contrast_rows(roles)}</tbody></table>
      </div>
    </section>"""


def build_html(palettes: list) -> str:
    cards = "\n".join(card(i, p) for i, p in enumerate(palettes))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Palette candidates</title>
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ background: #0a0c10; color: #e8edf2; font: 14px/1.5 system-ui, sans-serif; padding: 24px; }}
  h1 {{ font-size: 18px; margin-bottom: 4px; }}
  .sub {{ color: #8a94a2; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
  .card {{ background: #12161c; border: 1px solid #232b35; border-radius: 14px; overflow: hidden; }}
  .card-h {{ display: flex; align-items: baseline; gap: 8px; padding: 14px 16px; border-bottom: 1px solid #232b35; }}
  .idx {{ font-weight: 700; color: #5b6674; }}
  .name {{ font-weight: 700; }}
  .mood {{ color: #8a94a2; font-size: 12px; }}
  .mode {{ padding: 14px 16px; }}
  .pv {{ border-radius: 10px; padding: 12px; margin-bottom: 12px; }}
  .pv-panel {{ border-radius: 8px; padding: 12px; }}
  .pv-h {{ font-weight: 700; font-size: 15px; }}
  .pv-m {{ font-size: 12px; margin: 2px 0 10px; }}
  .pv-row {{ display: flex; gap: 8px; }}
  .pv-btn, .pv-badge {{ padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .swatches {{ display: flex; flex-direction: column; gap: 3px; margin-bottom: 10px; }}
  .sw {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
  .chip {{ width: 20px; height: 20px; border-radius: 5px; border: 1px solid rgba(255,255,255,.12); }}
  .rk {{ width: 120px; color: #b6bfca; }}
  .hx {{ color: #7f8a97; font-family: ui-monospace, monospace; }}
  .ct {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .ct th {{ text-align: left; color: #5b6674; font-weight: 600; padding: 2px 0; }}
  .ct td {{ padding: 2px 0; border-top: 1px solid #1c232c; }}
  .num {{ font-family: ui-monospace, monospace; color: #b6bfca; }}
  .badge {{ font-weight: 700; }}
  .badge.ok {{ color: #49d17f; }}
  .badge.warn {{ color: #e0b341; }}
  .badge.bad {{ color: #ff5c6c; }}
</style></head>
<body>
  <h1>Palette candidates</h1>
  <div class="sub">{len(palettes)} variant(s) · ui-ux-pro-max schema · contrast computed (WCAG AA), not eyeballed.</div>
  <div class="grid">{cards}</div>
</body></html>
"""


# --- cli --------------------------------------------------------------------


def main() -> int:
    args = sys.argv[1:]
    if not args:
        sys.stderr.write(__doc__.split("Usage:")[1].split("palettes.json schema")[0])
        return 2

    if args[0] == "--check":
        return report(load_tokens(args[1]), args[1])

    if args[0] == "--fix":
        roles = load_tokens(args[1])
        fixed, changed = repair(roles)
        for k, o, n, r in changed:
            sys.stderr.write(f"  fixed {k}: {o} -> {n} ({r}:1)\n")
        if not changed:
            sys.stderr.write("  nothing to fix — already AA-clean\n")
        sys.stdout.write(emit_css(fixed, Path(args[1]).stem))
        return 0

    if args[0] == "--from-promax":
        roles = from_promax(args[1])
        if not roles:
            return 1
        if "--fix" in args:
            roles, changed = repair(roles)
            for k, o, n, r in changed:
                sys.stderr.write(f"  fixed {k}: {o} -> {n} ({r}:1)\n")
        sys.stdout.write(emit_css(roles, args[1]))
        return 0

    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    palettes = data.get("palettes") or []
    if "--css" in args:
        i = int(args[args.index("--css") + 1])
        sys.stdout.write(
            emit_css(palettes[i].get("roles", {}), palettes[i].get("name", "tokens"))
        )
        return 0
    sys.stdout.write(build_html(palettes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
