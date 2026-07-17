#!/usr/bin/env python3
"""Behavioral tests for gen_palette.py — the AA gate over ui-ux-pro-max's token schema.

Two layers, deliberately separated:
  1. FIXTURES (always run) — pin our behaviour: 16-role parse, check/fix/exit codes,
     ink-only repair, rgba() tolerance, border = warn-not-fail. No third-party dep.
  2. INTEGRATION (skipped when pro-max isn't installed) — asserts the *mechanism* against
     the real CSV: all 16 roles recovered incl. the 6 its renderer drops, and that the
     checker finds real failures. Counts are NOT pinned: pro-max auto-updates via npm, so
     asserting "571 fails" would break on their next release — we assert invariants instead.

Run from the repo root. Exit 0 = all pass.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # gate-executed script contract: our own output must survive a cp949 console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "claude" / "skills" / "wook-palette" / "scripts" / "gen_palette.py"

_spec = importlib.util.spec_from_file_location("gen_palette", GEN)
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")


def css(roles: dict) -> str:
    d = tempfile.mkdtemp(prefix="promaxtok_")
    p = Path(d) / "tokens.css"
    p.write_text(g.emit_css(roles, "fixture"), encoding="utf-8")
    return str(p)


def run_cli(*args, strip_ioenc=False):
    """strip_ioenc=True reproduces a REAL user's shell.

    run_tests.py injects PYTHONIOENCODING=utf-8 into the environment, which propagates to
    this grandchild and papers over any stdout-encoding bug. On 2026-07-17 that masked a
    crash that blocked every commit for real users while the suite stayed 13/13 green.
    Tests that assert the shipped CLI works must therefore drop the variable.
    """
    env = dict(os.environ)
    if strip_ioenc:
        env.pop("PYTHONIOENCODING", None)
    p = subprocess.run(
        [sys.executable, "-B", str(GEN), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=env,
    )
    return p.returncode, p.stdout + p.stderr


# --- fixtures ----------------------------------------------------------------
# The exact failure we actually shipped into a sandbox on 2026-07-17: pro-max's renderer
# hid on_accent, the agent guessed white, CTA landed at 2.28:1.
CTA_FAIL = {
    "primary": "#1E293B",
    "on_primary": "#FFFFFF",
    "secondary": "#334155",
    "on_secondary": "#FFFFFF",
    "accent": "#22C55E",
    "on_accent": "#FFFFFF",  # 2.28:1 — the bug
    "background": "#0F172A",
    "foreground": "#F8FAFC",
    "card": "#1B2336",
    "card_foreground": "#F8FAFC",
    "muted": "#272F42",
    "muted_foreground": "#94A3B8",
    "border": "#475569",  # 2.36:1 — warn only
    "destructive": "#EF4444",
    "on_destructive": "#FFFFFF",  # 3.76:1
    "ring": "#1E293B",
}
CLEAN = {**CTA_FAIL, "on_accent": "#0F172A", "on_destructive": "#171717"}

print("Test A-C — check: exit codes bound to computed contrast")
rc, out = run_cli("--check", css(CLEAN))
check("A AA-clean tokens -> exit 0", rc == 0 and "TOKENS AA OK" in out, f"rc={rc}")
rc, out = run_cli("--check", css(CTA_FAIL))
check("B failing tokens -> exit 1", rc == 1, f"rc={rc}")
check(
    "C failure names the pair + ratio",
    "on_accent/accent" in out and "2.28" in out,
    out.strip().splitlines()[-3] if out else "",
)

print("Test D-E — border is WARN, never a gate failure (WCAG 1.4.11 scoping)")
rc, out = run_cli("--check", css(CLEAN))
check(
    "D border under 3:1 reported as warn",
    "[warn]" in out and "border/background" in out,
    "",
)
check("E ...and still exit 0", rc == 0, f"rc={rc}")

print("Test F-H — fix: repairs the ink, never the brand colour")
fixed, changed = g.repair(CTA_FAIL)
check(
    "F on_accent repaired to AA",
    g.aa(g.contrast(fixed["on_accent"], fixed["accent"])),
    f"{fixed['on_accent']} = {g.contrast(fixed['on_accent'], fixed['accent'])}:1",
)
check(
    "G brand colours untouched",
    fixed["accent"] == CTA_FAIL["accent"]
    and fixed["destructive"] == CTA_FAIL["destructive"],
    f"accent {fixed['accent']}",
)
check("H repaired tokens now pass --check", not g.audit(fixed)["fails"], "")

print("Test T-W — repair must not win the metric by killing the design (2026-07-17)")
# An evaluator caught --fix scoring muted_foreground 8.4:1 by making it IDENTICAL to
# foreground: body text and muted captions in one colour. Goodhart in one line.
TIER = {
    **CLEAN,
    "background": "#FDF2F8",
    "foreground": "#831843",
    "card": "#FFFFFF",
    "card_foreground": "#831843",
    "muted": "#F1EEF5",
    "muted_foreground": "#64748B",  # 4.14:1 — just under
    "primary": "#EC4899",
    "on_primary": "#FFFFFF",
    "accent": "#0891B2",
    "on_accent": "#FFFFFF",
}
fixed_t, _ = g.repair(TIER)
check(
    "T muted_foreground repaired to AA",
    g.aa(g.contrast(fixed_t["muted_foreground"], fixed_t["muted"])),
    f"{fixed_t['muted_foreground']} = {g.contrast(fixed_t['muted_foreground'], fixed_t['muted'])}:1",
)
check(
    "U ...WITHOUT collapsing into foreground (the tier must survive)",
    fixed_t["muted_foreground"].upper() != fixed_t["foreground"].upper(),
    f"muted={fixed_t['muted_foreground']} vs fg={fixed_t['foreground']}",
)
check(
    "V ...and it just clears the bar, not maxes it (designer intent survives)",
    g.contrast(fixed_t["muted_foreground"], fixed_t["muted"]) < 6.0,
    f"{g.contrast(fixed_t['muted_foreground'], fixed_t['muted'])}:1",
)
collapsed = {**TIER, "muted_foreground": TIER["foreground"]}
check(
    "W audit warns when a tier IS collapsed (contrast alone cannot see it)",
    any("tier collapsed" in n for n, *_ in g.audit(collapsed)["warns"]),
    "",
)
check(
    "X ...but card_foreground == foreground is normal, never warned",
    not any("card_foreground" in n for n, *_ in g.audit(TIER)["warns"]),
    "",
)

print("Test I — fix via CLI round-trips to exit 0")
d = tempfile.mkdtemp(prefix="promaxtok_")
out_css = Path(d) / "fixed.css"
rc, out = run_cli("--fix", css(CTA_FAIL))
# --fix puts CSS on stdout and its repair log on stderr; run_cli merges them, so drop the log.
clean_css = "\n".join(
    ln for ln in out.splitlines() if not ln.strip().startswith("fixed ")
)
out_css.write_text(clean_css, encoding="utf-8")
rc2, out2 = run_cli("--check", str(out_css))
check("I --fix output passes --check", rc2 == 0, f"rc={rc2}")

print(
    "Test R-S — works in a REAL shell (no PYTHONIOENCODING) — the 2026-07-17 regression"
)
# The suite was 13/13 green while `--check` crashed for every actual user, because
# run_tests.py injects PYTHONIOENCODING=utf-8. These two drop it on purpose.
rc, out = run_cli("--check", css(CLEAN), strip_ioenc=True)
check(
    "R AA-clean tokens -> exit 0 without PYTHONIOENCODING",
    rc == 0,
    f"rc={rc} {out.strip().splitlines()[-1] if out.strip() else ''}",
)
rc, out = run_cli("--check", css(CTA_FAIL), strip_ioenc=True)
check(
    "S failing tokens -> exit 1 (not a crash) without PYTHONIOENCODING",
    rc == 1 and "on_accent/accent" in out,
    f"rc={rc}",
)

print("Test J — rgba() cells tolerated, never crash")
rgba = {**CLEAN, "border": "rgba(255,255,255,0.08)"}
try:
    a = g.audit(rgba)
    check(
        "J rgba border skipped, no crash", any("border" in s for s in a["skipped"]), ""
    )
except Exception as e:
    check("J rgba border skipped, no crash", False, f"crashed: {e}")

print("Test K-M — integration with the real pro-max CSV (skipped if not installed)")
if not g.PROMAX_CSV.exists():
    print(
        f"  [SKIP] pro-max not installed at {g.PROMAX_CSV} — fixtures already cover behaviour"
    )
else:
    import csv as _csv

    rows = list(_csv.DictReader(g.PROMAX_CSV.open(encoding="utf-8")))
    check("K CSV parses with >= 100 rows", len(rows) >= 100, f"{len(rows)} rows")
    # the 6 roles its renderer drops must actually come back
    dropped = [
        "on_secondary",
        "on_accent",
        "card",
        "card_foreground",
        "muted_foreground",
        "on_destructive",
    ]
    roles = g.from_promax("smart home iot dashboard")
    check(
        "L renderer-dropped roles recovered from CSV",
        all(g.is_hex(roles.get(k)) for k in dropped),
        ", ".join(f"{k}={roles.get(k)}" for k in dropped[:3]),
    )
    # the checker must find real failures across the corpus (count NOT pinned — npm updates it)
    fails = sum(
        len(g.audit({k: (r.get(g.CSV_OF[k]) or "").strip() for k in g.KEYS})["fails"])
        for r in rows
    )
    check(
        "M checker finds real AA failures in their data",
        fails > 0,
        f"{fails} enforced fails",
    )

for p in Path(tempfile.gettempdir()).glob("promaxtok_*"):
    __import__("shutil").rmtree(p, ignore_errors=True)

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
