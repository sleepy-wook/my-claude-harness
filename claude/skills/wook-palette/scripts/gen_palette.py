#!/usr/bin/env python3
"""Generate a fixed-UI palette picker HTML (and tokens.css) from candidate palettes.

Deterministic: same JSON in -> same HTML out, with **computed WCAG contrast** so
accessibility is measured, not eyeballed. Runs via bash from the wook-palette
skill; its output never enters the model's context token-by-token.

Usage:
  python gen_palette.py palettes.json                      # picker HTML on stdout
  python gen_palette.py palettes.json --css 2 --mode dark  # tokens.css for palette #2 (0-based)

palettes.json schema:
  {"palettes": [
     {"name": "midnight-laser", "mood": "dark, technical, restrained glow",
      "dark":  {"base":"#0b0e12","surface":"#151a21","surface2":"#1d242d",
                "border":"#262f3a","text":"#eef3f7","textMuted":"#98a3b0",
                "accent":"#34e0d0","accentInk":"#04120f","danger":"#ff5c6c","success":"#49d17f"},
      "light": { ... same roles ... }        # optional
     }, ...]}
"""

import json
import sys

ROLES = [
    "base",
    "surface",
    "surface2",
    "border",
    "text",
    "textMuted",
    "accent",
    "accentInk",
    "danger",
    "success",
]


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


def emit_css(pal: dict, mode: str) -> str:
    roles = pal.get(mode) or pal.get("dark") or pal.get("light")
    lines = [
        f"/* {pal.get('name', 'palette')} — {mode} — {pal.get('mood', '')} */",
        ":root {",
    ]
    for r in ROLES:
        if r in roles:
            var = "--" + "".join("-" + c.lower() if c.isupper() else c for c in r)
            lines.append(f"  {var}: {roles[r]};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def contrast_rows(roles: dict) -> str:
    pairs = [
        ("text / base", "text", "base", False),
        ("text / surface", "text", "surface", False),
        ("textMuted / surface", "textMuted", "surface", False),
        ("accentInk / accent", "accentInk", "accent", False),
        ("accent / base (large)", "accent", "base", True),
        ("danger / surface", "danger", "surface", False),
    ]
    out = []
    for label, fg, bg, large in pairs:
        if fg not in roles or bg not in roles:
            continue
        ratio = contrast(roles[fg], roles[bg])
        ok = aa(ratio, large)
        badge = "PASS" if ok else "FAIL"
        cls = "ok" if ok else "bad"
        out.append(
            f'<tr><td>{label}</td><td class="num">{ratio}:1</td>'
            f'<td class="badge {cls}">{badge}</td></tr>'
        )
    return "\n".join(out)


def swatches(roles: dict) -> str:
    out = []
    for r in ROLES:
        if r not in roles:
            continue
        out.append(
            f'<div class="sw"><span class="chip" style="background:{roles[r]}"></span>'
            f'<span class="rk">{r}</span><span class="hx">{roles[r]}</span></div>'
        )
    return "\n".join(out)


def preview(roles: dict) -> str:
    g = roles.get
    return f"""
    <div class="pv" style="background:{g("base")};color:{g("text")};border:1px solid {g("border")}">
      <div class="pv-panel" style="background:{g("surface")};border:1px solid {g("border")}">
        <div class="pv-h" style="color:{g("text")}">Heading text</div>
        <div class="pv-m" style="color:{g("textMuted")}">Muted secondary line</div>
        <div class="pv-row">
          <span class="pv-btn" style="background:{g("accent")};color:{g("accentInk")}">Primary</span>
          <span class="pv-badge" style="background:{g("danger")};color:#fff">Alert</span>
        </div>
      </div>
    </div>"""


def card(i: int, pal: dict) -> str:
    modes = [m for m in ("dark", "light") if m in pal]
    blocks = []
    for m in modes:
        roles = pal[m]
        blocks.append(f"""
      <div class="mode">
        <div class="mode-tag">{m}</div>
        {preview(roles)}
        <div class="swatches">{swatches(roles)}</div>
        <table class="ct"><thead><tr><th>contrast</th><th>ratio</th><th>AA</th></tr></thead>
          <tbody>{contrast_rows(roles)}</tbody></table>
      </div>""")
    return f"""
    <section class="card">
      <header class="card-h"><span class="idx">#{i}</span>
        <span class="name">{pal.get("name", "palette")}</span>
        <span class="mood">{pal.get("mood", "")}</span></header>
      <div class="modes">{"".join(blocks)}</div>
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
  .modes {{ display: flex; flex-wrap: wrap; }}
  .mode {{ flex: 1; min-width: 300px; padding: 14px 16px; }}
  .mode-tag {{ text-transform: uppercase; font-size: 11px; letter-spacing: .08em; color: #5b6674; margin-bottom: 8px; }}
  .pv {{ border-radius: 10px; padding: 12px; margin-bottom: 12px; }}
  .pv-panel {{ border-radius: 8px; padding: 12px; }}
  .pv-h {{ font-weight: 700; font-size: 15px; }}
  .pv-m {{ font-size: 12px; margin: 2px 0 10px; }}
  .pv-row {{ display: flex; gap: 8px; }}
  .pv-btn, .pv-badge {{ padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .swatches {{ display: flex; flex-direction: column; gap: 3px; margin-bottom: 10px; }}
  .sw {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
  .chip {{ width: 20px; height: 20px; border-radius: 5px; border: 1px solid rgba(255,255,255,.12); }}
  .rk {{ width: 84px; color: #b6bfca; }}
  .hx {{ color: #7f8a97; font-family: ui-monospace, monospace; }}
  .ct {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .ct th {{ text-align: left; color: #5b6674; font-weight: 600; padding: 2px 0; }}
  .ct td {{ padding: 2px 0; border-top: 1px solid #1c232c; }}
  .num {{ font-family: ui-monospace, monospace; color: #b6bfca; }}
  .badge {{ font-weight: 700; }}
  .badge.ok {{ color: #49d17f; }}
  .badge.bad {{ color: #ff5c6c; }}
</style></head>
<body>
  <h1>Palette candidates</h1>
  <div class="sub">{len(palettes)} variant(s) · pick one — contrast is computed (WCAG AA), not eyeballed.</div>
  <div class="grid">{cards}</div>
  <script>console.log('palette picker rendered:', {len(palettes)}, 'candidates');</script>
</body></html>
"""


def main() -> int:
    args = sys.argv[1:]
    if not args:
        sys.stderr.write("usage: gen_palette.py palettes.json [--css N --mode dark]\n")
        return 2
    data = json.loads(open(args[0], encoding="utf-8").read())
    palettes = data.get("palettes") or []
    if "--css" in args:
        i = int(args[args.index("--css") + 1])
        mode = args[args.index("--mode") + 1] if "--mode" in args else "dark"
        sys.stdout.write(emit_css(palettes[i], mode))
        return 0
    sys.stdout.write(build_html(palettes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
