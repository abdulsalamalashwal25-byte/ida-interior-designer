#!/usr/bin/env python3
"""
make_demo_master.py — build examples/demo_master.json from demo_intake.json.

WHAT THIS DOES
  1. Runs the real Phase 01 pipeline on examples/demo_intake.json.
  2. Adds four walls (a closed 6000x4000 rectangle) as [C]/CLIENT_INPUT
     TEST FIXTURES, so the downstream interfaces (plan, quantities,
     fidelity, manifest) have geometry to consume.
  3. Applies the mandatory TEST banner and saves examples/demo_master.json.

WHAT THIS DOES NOT DO
  In a REAL project, walls come from a confirmed survey — never from a
  script. This file exists only to produce synthetic TEST data for
  exercising the interfaces. Every fixture is labelled as such in its
  source_ref, and the master carries is_test_project=true + test_banner.

Usage:
  python3 examples/make_demo_master.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ida_api as API                                        # noqa: E402
import ida_workspace as WS                                   # noqa: E402

WHEN = "2026-09-15"
FIXTURE_REF = "demo fixture (TEST — not a real survey)"


def fact(value, unit="mm", note=None):
    node = {"value": value, "status": "C",
            "source_type": "CLIENT_INPUT",
            "source_ref": FIXTURE_REF,
            "recorded_on": WHEN}
    if unit is not None:
        node["unit"] = unit
    if note is not None:
        node["note"] = note
    return node


def main():
    intake_path = os.path.join(ROOT, "examples", "demo_intake.json")
    specs_path = os.path.join(ROOT, "examples", "demo_field_specs.json")
    out_path = os.path.join(ROOT, "examples", "demo_master.json")

    master, record = API.run_phase01_from_files(intake_path, specs_path, WHEN)
    print("pipeline state:", record.get("state"))
    if master is None:
        print("pipeline abstained:", record.get("abstention_reason"))
        return 1

    corners = [[0, 0], [6000, 0], [6000, 4000], [0, 4000]]
    walls = []
    for i in range(4):
        walls.append({
            "id": "W-%02d" % (i + 1),
            "start": fact(corners[i]),
            "end": fact(corners[(i + 1) % 4]),
            "thickness": fact(200),
            "structural": fact(False, unit="none",
                               note="demo fixture: non-structural"),
        })
    master["walls"] = walls
    print("walls added: 4 (TEST fixtures)")

    master = WS.strip_private(master)
    master, bannered = WS.ensure_test_banner(master)
    print("test banner applied:", bannered)

    report = API.validate_all(master)
    print("validation:", report["summary"]["result"],
          "(%d errors)" % report["summary"]["total_errors"])
    for ref in (report["schema_gate"].get("finding_references") or []):
        if ref.get("severity") == "ERROR":
            print("  A ERROR:", ref.get("message", ref.get("rule"))[:200])
    for ref in (report["rules"].get("finding_references") or []):
        if ref.get("severity") == "ERROR":
            print("  %s ERROR %s @ %s: %s" % (
                ref.get("layer"), ref.get("rule"), ref.get("location"),
                str(ref.get("message"))[:160]))

    WS.save_json(master, out_path)
    print("demo master written:", out_path)
    return 0 if report["summary"]["total_errors"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
