#!/usr/bin/env python3
"""Schema tests for the project-map template (fixed sections + YAML keys).

The `/wook-map` generation behavior is prompt-driven and can't be unit-tested; what we CAN
pin down deterministically is that the template conforms to the fixed schema the evaluator
relies on. Run from the repo root. Exit 0 = all pass.
"""

import re
import sys
from pathlib import Path

TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "claude"
    / "harness"
    / "project-map.example"
)
results = []


def check(name, ok):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


txt = TEMPLATE.read_text(encoding="utf-8")

# Fixed sections present, in order.
SECTIONS = ["## Stack & Run", "## Structure", "## How to exercise", "## Entry points"]
positions = [txt.find(s) for s in SECTIONS]
check("all 4 fixed sections present", all(p != -1 for p in positions))
check("sections in fixed order", positions == sorted(positions))

# YAML block with the fixed keys.
m = re.search(r"```yaml\n(.*?)\n```", txt, re.DOTALL)
check("has a ```yaml block", m is not None)
yaml_body = m.group(1) if m else ""
for key in ("stack:", "env:", "services:", "run:"):
    check(f"yaml has `{key}`", key in yaml_body)

# run commands carry a provenance pointer (summarize + point, per review).
check("run has `#` provenance pointer", "#" in yaml_body.split("run:", 1)[-1])

# verified stamp + shallow-structure intent are templated.
check("has verified stamp", "verified:" in txt)
check("smoke ties to evaluate.recipe (not duplicated)", "evaluate.recipe" in txt)

# Optional: if PyYAML is available, the block must actually parse.
try:
    import yaml  # type: ignore

    data = yaml.safe_load(yaml_body)
    check(
        "yaml parses to a dict with the keys",
        isinstance(data, dict) and {"stack", "env", "services", "run"} <= set(data),
    )
except ImportError:
    print("  [skip] PyYAML not installed — string checks only")

print(f"\nRESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
