#!/usr/bin/env python3
"""Quality gate for the wook-palette aesthetic preset library.

Every shipped preset palette MUST pass WCAG AA on the load-bearing pairs — this is the
differentiator over hand-eyeballed preset libraries (incl. ui-ux-pro-max's 161: breadth
there, computed enforcement here). Reuses the deterministic contrast math in
gen_palette.py. Run from the repo root. Exit 0 = all presets AA-clean.
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIB = (
    REPO
    / "claude"
    / "skills"
    / "wook-palette"
    / "references"
    / "presets"
    / "library.json"
)
GEN = REPO / "claude" / "skills" / "wook-palette" / "scripts" / "gen_palette.py"

_spec = importlib.util.spec_from_file_location("gen_palette", GEN)
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

# The exact pairs gen_palette renders (so the test == the shown contrast table).
# (fg, bg, large): large-text rows use the 3.0 AA threshold, normal rows 4.5.
PAIRS = [
    ("text", "base", False),
    ("text", "surface", False),
    ("textMuted", "surface", False),
    ("accentInk", "accent", False),
    ("accent", "base", True),
    ("danger", "surface", False),
]
ROLES = {
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
}

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")


data = json.loads(LIB.read_text(encoding="utf-8"))
palettes = data.get("palettes", [])
check("library.json has >= 12 presets", len(palettes) >= 12, f"got {len(palettes)}")

for p in palettes:
    name = p.get("name", "?")
    modes = [m for m in ("dark", "light") if m in p]
    check(f"{name}: has a palette mode", bool(modes), "no dark/light block")
    for m in modes:
        roles = p[m]
        missing = ROLES - set(roles)
        check(
            f"{name}[{m}]: all roles present", not missing, f"missing {sorted(missing)}"
        )
        fails = []
        for fg, bg, large in PAIRS:
            if fg in roles and bg in roles:
                r = g.contrast(roles[fg], roles[bg])
                if not g.aa(r, large):
                    fails.append(f"{fg}/{bg}={r}")
        check(f"{name}[{m}]: AA on all rendered pairs", not fails, ", ".join(fails))

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
