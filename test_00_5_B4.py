#!/usr/bin/env python3
"""Phase 00.5-B4 — Movement & Circulation Integrity test suite.

Discipline carried over from B1/B2/B3:
  * every rule gets Positive + Negative + Isolation
  * a negative must fail because of the TARGETED rule, not fixture rot
  * UNKNOWN is a third verdict and is never silently upgraded to PASSABLE
"""

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from schema_gate import load_schema, validate_master          # noqa: E402
from validate_refs import validate_references, build_index    # noqa: E402
from validate_topology import validate_topology               # noqa: E402
from validate_furniture import validate_furniture             # noqa: E402
from validate_movement import (                               # noqa: E402
    validate_movement, PASSABLE, BLOCKED, UNKNOWN)

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []


def fact(value, status="C", src="CLIENT_INPUT", ref="client brief p.1",
         unit=None, **kw):
    f = {"value": value, "status": status, "source_type": src,
         "source_ref": ref, "recorded_on": TODAY}
    if unit:
        f["unit"] = unit
    f.update(kw)
    return f


def unknown_fact(uid, ref="not provided"):
    return {"value": None, "status": "U", "source_type": "NOT_PROVIDED",
            "source_ref": ref, "recorded_on": TODAY, "blocking": False,
            "unknown_id": uid}


def confirmed_absent(what):
    return {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
            "source_ref": f"client survey: no {what}", "recorded_on": TODAY,
            "presence": "NOT_PRESENT"}


def wall(wid, a, b, thickness=200):
    return {"id": wid, "start": fact(list(a), unit="mm"),
            "end": fact(list(b), unit="mm"),
            "thickness": fact(thickness, unit="mm"), "structural": fact(True)}


# ===========================================================================
# BASE: same 6000 x 4000 test room as B3, plus two doors to route between.
# Reuses the B3 fixture shape verbatim so B4 tests never fail on fixture rot.
# ===========================================================================
BASE = {
    "meta": {
        "project_id": "PRJ-96", "project_name": "CIRCULATION TEST ROOM",
        "revision": "R01", "geometry_version": "G-001", "status": "DRAFT",
        "track": "LITE", "units": "mm", "created_on": TODAY,
        "is_test_project": True,
        "test_banner": "TEST PROJECT — NOT A REAL CLIENT PROJECT",
        "not_for_construction": "DESIGN INTENT — NOT FOR CONSTRUCTION",
        "topology_policy": {"require_closed_envelope": True},
    },
    "space": {
        "outline": fact([[0, 0], [6000, 0], [6000, 4000], [0, 4000]], unit="mm"),
        "ceiling_height": fact(2800, unit="mm"),
        "orientation_north": unknown_fact("U-003", "not supplied"),
        "floor_level": fact(0, unit="mm"),
    },
    "presence_register": {
        "columns": confirmed_absent("columns"),
        "beams": confirmed_absent("beams"),
        "protrusions": confirmed_absent("protrusions"),
        "level_changes": confirmed_absent("level changes"),
        "services": confirmed_absent("services"),
        "existing_furniture": confirmed_absent("existing furniture"),
        "openings": fact(True, ref="client survey: two doors", unit="none",
                         presence="PRESENT"),
        "circulation": fact(True, ref="client survey: routes defined",
                            unit="none", presence="PRESENT"),
    },
    "walls": [
        wall("W-01", (0, 0), (6000, 0)),
        wall("W-02", (6000, 0), (6000, 4000)),
        wall("W-03", (6000, 4000), (0, 4000)),
        wall("W-04", (0, 4000), (0, 0)),
    ],
    "openings": [
        # D-01 sits on W-01 (0,0)->(6000,0): centre at x = 550 + 450 = 1000.
        {"id": "D-01", "kind": "door", "host_wall": "W-01",
         "offset": fact(550, unit="mm"), "width": fact(900, unit="mm"),
         "height": fact(2100, unit="mm")},
        # D-02 sits on W-03 (6000,4000)->(0,4000): centre at x = 6000-1000 = 5000.
        {"id": "D-02", "kind": "door", "host_wall": "W-03",
         "offset": fact(550, unit="mm"), "width": fact(900, unit="mm"),
         "height": fact(2100, unit="mm")},
    ],
    "columns": [],
    "zones": [],
    "furniture": [],
    "materials": [
        {"id": "M-01", "name": fact("Oak veneer"), "color_hex": fact("#B98A56"),
         "applied_to": ["W-01"]},
    ],
    "cameras": [],
    "circulation": [],
    "registers": {
        "unknowns": [{"id": "U-003", "question": "North orientation?",
                      "blocking": False, "raised_on": TODAY}],
        "assumptions": [], "proposals": [], "decisions": [],
        "change_requests": [], "objections": [],
        "changelog": [{"revision": "R01", "date": TODAY, "type": "INITIAL",
                       "summary": "Circulation test fixture."}],
    },
    "outputs": [],
}


_OMIT = object()


def seg_path(pid="CP-01", name="Segmented route", segs=None,
             start="D-01", end="D-02"):
    """A path declared as an explicit SEGMENT list (can express a real gap)."""
    return {"id": pid, "name": name,
            "segments": fact([[list(a), list(b)] for a, b in segs]),
            "start_ref": fact(start), "end_ref": fact(end)}


def path(pid="CP-01", name="Main route",
         pts=((1000, 0), (1000, 2000), (5000, 2000), (5000, 4000)),
         start="D-01", end="D-02", width=_OMIT):
    """A declared circulation path. Endpoints default to the two doors."""
    p = {"id": pid, "name": name,
         "centerline": fact([list(q) for q in pts]),
         "start_ref": fact(start),
         "end_ref": fact(end)}
    if width is not _OMIT:
        p["required_width"] = width
    return p


def furn(fid, name, cx, cy, w, d, h=750, material="M-01",
         datum="CENTER", rot=0):
    """Furniture declared the B3 way: datum and rotation explicit."""
    f = {"id": fid, "name": name, "position": fact([cx, cy], unit="mm"),
         "dims": fact([w, d, h], unit="mm"), "material_ref": material}
    if datum is not _OMIT:
        f["position_reference"] = fact(datum, ref="client survey: datum declared")
    if rot is not _OMIT:
        f["rotation"] = fact(rot, unit="deg", ref="client survey: orientation")
    return f


def run(data):
    return validate_movement(data)


def rules_of(findings, severity=None):
    return sorted({f.rule for f in findings
                   if severity is None or f.severity == severity})


# ==========================================================================
# POSITIVE
# ==========================================================================
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_ok_s, _es = validate_master(_d, SCHEMA)
_ok, _f, _v = run(_d)
RESULTS.append(("MP-01", "A connected path with valid refs is PASSABLE",
                "PASS" if (_ok_s and _ok and _v["CP-01"] == PASSABLE) else "FAIL",
                f"schema={_ok_s} ok={_ok} verdict={_v.get('CP-01')} "
                f"errors={rules_of(_f, 'ERROR')}"))

# MP-02: endpoint refs resolve and attach.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_ok, _f, _v = run(_d)
RESULTS.append(("MP-02", "Resolvable start/end references raise no MV-004/005",
                "PASS" if not any(x.rule in ("MV-004", "MV-005") for x in _f)
                else "FAIL", f"{rules_of(_f)}"))

# MP-03: a trusted required_width that IS met.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path(width=fact(800, unit="mm"))]
_d["furniture"] = [furn("F-01", "Cabinet", 3000, 3000, 600, 400)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("MP-03", "Sufficient width vs a trusted requirement passes",
                "PASS" if (_ok and _v["CP-01"] == PASSABLE
                           and not any(x.rule == "MV-008" for x in _f)) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MP-04: an obstacle well away from the path does not block.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_d["furniture"] = [furn("F-01", "Cabinet", 3000, 3500, 600, 400)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("MP-04", "An obstacle off the path causes no blocking",
                "PASS" if (_ok and _v["CP-01"] == PASSABLE) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MP-05: a master with no path must now DECLARE that fact (user ruling).
# The old premise ("no paths is simply fine") was reversed when circulation
# declaration became mandatory, so this test is retargeted rather than deleted:
# a properly declared NOT_PRESENT is accepted, silence is not.
_d = copy.deepcopy(BASE)
_d["circulation"] = []
_d["presence_register"]["circulation"] = confirmed_absent("defined routes")
_ok, _f, _v = run(_d)
RESULTS.append(("MP-05", "No paths is fine ONLY when declared NOT_PRESENT",
                "PASS" if (_ok and not _v) else "FAIL",
                f"ok={_ok} verdicts={_v}"))

# ==========================================================================
# NEGATIVE
# ==========================================================================
# MN-01: missing start_ref.
_d = copy.deepcopy(BASE)
_p = path()
del _p["start_ref"]
_d["circulation"] = [_p]
_ok_s, _ = validate_master(_d, SCHEMA)
_ok, _f, _v = run(_d)
RESULTS.append(("MN-01", "Missing start_ref is rejected (schema) / MV-004",
                "PASS" if (not _ok_s) else "FAIL",
                f"schema_rejected={not _ok_s}"))

# MN-02: end_ref points at something that does not resolve.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path(end="D-99")]
_ok, _f, _v = run(_d)
_mv4 = [x for x in _f if x.rule == "MV-004"]
RESULTS.append(("MN-02", "Unresolvable end_ref -> MV-004, verdict UNKNOWN",
                "PASS" if (not _ok and len(_mv4) == 1
                           and _v["CP-01"] == UNKNOWN) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MN-03: continuity. MV-003 was REMOVED as unreachable (a polyline shares its
# vertices by construction), so this test now pins the replacement guarantee:
# a zero-length segment is caught by MV-002 and never silently accepted.
_d = copy.deepcopy(BASE)
_dp = path()
_dp["centerline"] = fact([[1000, 0], [1000, 2000], [1000, 2000], [5000, 4000]])
_d["circulation"] = [_dp]
_ok, _f, _v = run(_d)
RESULTS.append(("MN-03", "A zero-length segment -> MV-002, never silently passed",
                "PASS" if (not _ok and any(x.rule == "MV-002" for x in _f)
                           and _v["CP-01"] == UNKNOWN) else "FAIL",
                f"verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MN-03b: a path that ends nowhere near its declared target.
# NOTE: the first draft of this test placed the ends exactly on both doors, so
# PASSABLE was the CORRECT verdict and the engine was right. Corrected here to
# actually detach the end, which is what the rule is meant to catch.
_d = copy.deepcopy(BASE)
_seg_path = path()
_seg_path["centerline"] = fact([[1000, 0], [1000, 1000],
                                [3000, 3000], [3000, 3500]])
_d["circulation"] = [_seg_path]
_ok, _f, _v = run(_d)
RESULTS.append(("MN-03b", "A path whose end misses its target is not PASSABLE",
                "PASS" if (_v["CP-01"] != PASSABLE
                           and any(x.rule == "MV-005" for x in _f)) else "FAIL",
                f"verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MN-04: a known obstacle sitting on the path -> BLOCKED.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_d["furniture"] = [furn("F-01", "Sideboard", 3000, 2000, 1200, 500)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
_mv6 = [x for x in _f if x.rule == "MV-006"]
RESULTS.append(("MN-04", "A known obstacle on the path -> MV-006 / BLOCKED",
                "PASS" if (not _ok and len(_mv6) == 1
                           and _v["CP-01"] == BLOCKED) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MN-05: width below a TRUSTED requirement -> MV-008 ERROR.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path(width=fact(1200, unit="mm"))]
_d["furniture"] = [furn("F-01", "Cabinet", 3000, 2400, 600, 400)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
_mv8 = [x for x in _f if x.rule == "MV-008"]
RESULTS.append(("MN-05", "Width under a trusted requirement -> MV-008 ERROR",
                "PASS" if (not _ok and len(_mv8) == 1
                           and _v["CP-01"] == BLOCKED) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MN-06: the SAME narrow geometry with NO requirement must NOT error.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]          # no required_width at all
_d["furniture"] = [furn("F-01", "Cabinet", 3000, 2400, 600, 400)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("MN-06", "Same narrow gap with NO requirement -> no invented ERROR",
                "PASS" if (_ok and not any(x.rule == "MV-008" for x in _f)
                           and _v["CP-01"] == PASSABLE) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} errors={rules_of(_f, 'ERROR')}"))

# MN-07: a path endpoint far from its declared target -> MV-005.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path(pts=((2500, 1500), (2500, 2000),
                               (5000, 2000), (5000, 4000)))]
_ok, _f, _v = run(_d)
_mv5 = [x for x in _f if x.rule == "MV-005"]
RESULTS.append(("MN-07", "A detached endpoint -> MV-005 / not PASSABLE",
                "PASS" if (not _ok and len(_mv5) >= 1
                           and _v["CP-01"] == BLOCKED) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))


# ==========================================================================
# UNKNOWN
# ==========================================================================
# MU-01: incomplete path geometry -> MV-001, UNKNOWN.
_d = copy.deepcopy(BASE)
_p = path()
_p["centerline"] = unknown_fact("U-401", "route not surveyed")
_d["circulation"] = [_p]
_d["registers"]["unknowns"].append(
    {"id": "U-401", "question": "Route geometry?", "blocking": False,
     "raised_on": TODAY})
_ok, _f, _v = run(_d)
RESULTS.append(("MU-01", "UNKNOWN centerline -> MV-001, verdict UNKNOWN",
                "PASS" if (not _ok and any(x.rule == "MV-001" for x in _f)
                           and _v["CP-01"] == UNKNOWN) else "FAIL",
                f"verdict={_v.get('CP-01')} {rules_of(_f)}"))

# MU-02: obstacle geometry unresolved near the path -> MV-007, UNKNOWN.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_f01 = furn("F-01", "Unplaced unit", 3000, 2000, 1200, 500, rot=_OMIT)
_f01["rotation"] = unknown_fact("U-402", "angle not decided")
_d["furniture"] = [_f01]
_d["registers"]["unknowns"].append(
    {"id": "U-402", "question": "Angle of F-01?", "blocking": False,
     "raised_on": TODAY})
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
_mv7 = [x for x in _f if x.rule == "MV-007"]
RESULTS.append(("MU-02", "Unresolved obstacle geometry -> MV-007, verdict UNKNOWN",
                "PASS" if (len(_mv7) == 1 and _v["CP-01"] == UNKNOWN) else "FAIL",
                f"verdict={_v.get('CP-01')} {rules_of(_f)}"))

# MU-03: UNKNOWN must never be reported as PASSABLE.
RESULTS.append(("MU-03", "UNKNOWN is never upgraded to PASSABLE",
                "PASS" if _v["CP-01"] != PASSABLE else "FAIL",
                f"verdict={_v.get('CP-01')}"))

# MU-04: UNKNOWN must not be downgraded to BLOCKED without proof.
RESULTS.append(("MU-04", "UNKNOWN is not asserted as BLOCKED without evidence",
                "PASS" if (_v["CP-01"] == UNKNOWN
                           and not any(x.rule == "MV-006" for x in _f)) else "FAIL",
                f"verdict={_v.get('CP-01')} codes={rules_of(_f)}"))

# MU-05: declared width from an UNTRUSTED source -> MV-009 INFO, never ERROR.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path(width=fact(1200, status="P", src="AGENT_PROPOSAL",
                                     ref="suggested corridor", unit="mm"))]
_d["furniture"] = [furn("F-01", "Cabinet", 3000, 2400, 600, 400)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f, _v = run(_d)
_mv9 = [x for x in _f if x.rule == "MV-009"]
RESULTS.append(("MU-05", "Untrusted required_width -> MV-009 INFO, not ERROR",
                "PASS" if (_ok and len(_mv9) == 1 and _mv9[0].severity == "INFO"
                           and not any(x.rule == "MV-008" for x in _f)) else "FAIL",
                f"ok={_ok} {[(x.rule, x.severity) for x in _f if x.rule.startswith('MV-00')]}"))

# MU-06: UNKNOWN required_width -> MV-009 INFO/GAP.
_d = copy.deepcopy(BASE)
_wp = path()
_wp["required_width"] = unknown_fact("U-403", "min width not agreed")
_d["circulation"] = [_wp]
_d["registers"]["unknowns"].append(
    {"id": "U-403", "question": "Minimum corridor width?", "blocking": False,
     "raised_on": TODAY})
_ok, _f, _v = run(_d)
RESULTS.append(("MU-06", "UNKNOWN required_width -> GAP recorded, no ERROR",
                "PASS" if (_ok and any(x.rule == "MV-009" and x.severity == "INFO"
                                       for x in _f)) else "FAIL",
                f"ok={_ok} {rules_of(_f)}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
# MI-01: a pure B3 defect (furniture overlap) must not make B4 fail.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_d["furniture"] = [furn("F-01", "Chair A", 3000, 3500, 600, 600),
                   furn("F-02", "Chair B", 3200, 3500, 600, 600)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_b3_ok, _b3f = validate_furniture(_d)
_ok, _f, _v = run(_d)
RESULTS.append(("MI-01", "A B3-only overlap does not fail B4",
                "PASS" if ((not _b3_ok) and any(x.rule == "FC-003" for x in _b3f)
                           and _ok and _v["CP-01"] == PASSABLE) else "FAIL",
                f"B3_ok={_b3_ok} B3={sorted({x.rule for x in _b3f})} "
                f"B4_ok={_ok} verdict={_v.get('CP-01')}"))

# MI-02: a B4 blockage must not disturb A / B1 / B2 / B3.
_d = copy.deepcopy(BASE)
_d["circulation"] = [path()]
_d["furniture"] = [furn("F-01", "Sideboard", 3000, 2000, 1200, 500)]
_d["materials"][0]["applied_to"] = ["F-01"]
_a_ok, _ = validate_master(_d, SCHEMA)
_b1_ok, _ = validate_references(_d)
_b2_ok, _ = validate_topology(_d)
_b3_ok, _b3f = validate_furniture(_d)
_ok, _f, _v = run(_d)
RESULTS.append(("MI-02", "B4 blockage leaves A/B1/B2/B3 clean (B3 independent)",
                "PASS" if (_a_ok and _b1_ok and _b2_ok and _b3_ok
                           and not _ok and _v["CP-01"] == BLOCKED) else "FAIL",
                f"A={_a_ok} B1={_b1_ok} B2={_b2_ok} B3={_b3_ok} B4_ok={_ok}"))

# MI-03: B4 never emits a furniture-collision code.
_all_codes = set()
for _case in (
        [furn("F-01", "Sideboard", 3000, 2000, 1200, 500)],
        [furn("F-01", "Chair A", 3000, 3500, 600, 600),
         furn("F-02", "Chair B", 3200, 3500, 600, 600)]):
    _d = copy.deepcopy(BASE)
    _d["circulation"] = [path()]
    _d["furniture"] = _case
    _d["materials"][0]["applied_to"] = [x["id"] for x in _case]
    _all_codes |= {x.rule for x in run(_d)[1]}
RESULTS.append(("MI-03", "B4 emits no FC-* / XR-* / WT-* code of its own",
                "PASS" if all(c.startswith("MV-") for c in _all_codes) else "FAIL",
                f"codes={sorted(_all_codes)}"))

# MI-04: B4 starts no door-swing logic (B5 territory).
_raw = open(os.path.join(ROOT, "scripts", "validate_movement.py"),
            encoding="utf-8").read()
# Strip comments and docstrings: a rule that NAMES B5 in prose to disclaim it
# must not count as implementing door-swing logic. Only executable code counts.
import ast as _ast  # noqa: E402
_tree = _ast.parse(_raw)
for _node in _ast.walk(_tree):
    if (isinstance(_node, _ast.Expr) and isinstance(_node.value, _ast.Constant)
            and isinstance(_node.value.value, str)):
        _node.value.value = ""
_src = _ast.unparse(_tree).lower()
_swing_terms = [t for t in ("swing", "arc", "leaf", "hinge", "door_angle")
                if t in _src]
RESULTS.append(("MI-04", "No door-swing logic exists in the B4 engine",
                "PASS" if not _swing_terms else "FAIL",
                f"terms_found={_swing_terms}"))

# MI-05: no hard-coded corridor/ergonomic number in the engine.
import re  # noqa: E402
_code_lines = [ln for ln in open(
    os.path.join(ROOT, "scripts", "validate_movement.py"),
    encoding="utf-8").read().splitlines()
    if not ln.strip().startswith("#")]
_suspects = []
for ln in _code_lines:
    for m in re.finditer(r"\b(\d{3,5})(?:\.\d+)?\b", ln):
        n = int(m.group(1))
        if n >= 300:            # any plausible corridor/ergonomic figure
            _suspects.append((n, ln.strip()[:60]))
RESULTS.append(("MI-05", "No hard-coded corridor width / ergonomic figure",
                "PASS" if not _suspects else "FAIL",
                f"suspects={_suspects[:3] if _suspects else 'none'}"))

# MI-06: B3 does not depend on B4 (no import of the movement engine).
_b3_src = open(os.path.join(ROOT, "scripts", "validate_furniture.py"),
               encoding="utf-8").read()
RESULTS.append(("MI-06", "B3 does not import or depend on B4",
                "PASS" if "validate_movement" not in _b3_src else "FAIL",
                "one-way dependency B4 -> B3"))

# MI-07: mutation sweep — each defect class is caught.
_sweep = []
_cases = [
    ("obstacle on path", lambda d: d.update(
        {"furniture": [furn("F-01", "Sideboard", 3000, 2000, 1200, 500)]}),
     "MV-006"),
    ("bad end ref", lambda d: d["circulation"].__setitem__(
        0, path(end="D-99")), "MV-004"),
    ("unknown centerline", lambda d: d["circulation"][0].__setitem__(
        "centerline", unknown_fact("U-409", "not surveyed")), "MV-001"),
    ("detached endpoint", lambda d: d["circulation"].__setitem__(
        0, path(pts=((2500, 1500), (2500, 2000), (5000, 2000), (5000, 4000)))),
     "MV-005"),
]
for _label, _mut, _expect in _cases:
    _d = copy.deepcopy(BASE)
    _d["circulation"] = [path()]
    _mut(_d)
    if _d.get("furniture"):
        _d["materials"][0]["applied_to"] = [x["id"] for x in _d["furniture"]]
    _codes = {x.rule for x in run(_d)[1]}
    _sweep.append((_label, _expect in _codes))
RESULTS.append(("MI-07", "Mutation sweep: every movement defect is detected",
                "PASS" if all(ok for _, ok in _sweep) else "FAIL",
                f"{sum(1 for _, o in _sweep if o)}/{len(_sweep)} caught"))

# MI-08: no false positives on the clean base, run repeatedly.
_clean = []
for _ in range(3):
    _d = copy.deepcopy(BASE)
    _d["circulation"] = [path()]
    _clean.append(run(_d)[0])
RESULTS.append(("MI-08", "No false positives on the valid base (3 runs)",
                "PASS" if all(_clean) else "FAIL", f"{_clean}"))

# MI-09: B4 issues no design opinion (detect/classify/report only).
_opinion_terms = [t for t in ("recommend", "suggest", "should be moved",
                              "better", "prefer", "optimi", "rearrange",
                              "aesthetic", "comfortable")
                  if t in _src]
RESULTS.append(("MI-09", "B4 offers no design judgement or auto-repair",
                "PASS" if not _opinion_terms else "FAIL",
                f"terms_found={_opinion_terms}"))


# ==========================================================================
# MV-003 REINSTATED — discontinuity on the segments representation
# ==========================================================================
# MS-01 (positive): contiguous segments behave exactly like the polyline.
_d = copy.deepcopy(BASE)
_d["circulation"] = [seg_path(segs=[((1000, 0), (1000, 2000)),
                                    ((1000, 2000), (5000, 2000)),
                                    ((5000, 2000), (5000, 4000))])]
_ok_s, _ = validate_master(_d, SCHEMA)
_ok, _f, _v = run(_d)
RESULTS.append(("MS-01", "Contiguous segment list is PASSABLE",
                "PASS" if (_ok_s and _ok and _v["CP-01"] == PASSABLE) else "FAIL",
                f"schema={_ok_s} ok={_ok} verdict={_v.get('CP-01')} "
                f"{rules_of(_f, 'ERROR')}"))

# MS-02 (negative): a genuine gap between consecutive segments -> MV-003.
_d = copy.deepcopy(BASE)
_d["circulation"] = [seg_path(segs=[((1000, 0), (1000, 2000)),
                                    ((1400, 2000), (5000, 2000)),
                                    ((5000, 2000), (5000, 4000))])]
_ok, _f, _v = run(_d)
_mv3 = [x for x in _f if x.rule == "MV-003"]
RESULTS.append(("MS-02", "A real gap between segments -> MV-003 / BLOCKED",
                "PASS" if (not _ok and len(_mv3) == 1
                           and _v["CP-01"] == BLOCKED) else "FAIL",
                f"ok={_ok} verdict={_v.get('CP-01')} {rules_of(_f, 'ERROR')}"))

# MS-03: MV-003 is now genuinely reachable (the reason it was removed is gone).
RESULTS.append(("MS-03", "MV-003 is reachable, not dead code",
                "PASS" if (len(_mv3) == 1 and "400 mm" in _mv3[0].message)
                else "FAIL",
                f"msg={_mv3[0].message[:58] if _mv3 else 'none'}"))

# MS-04: the gap is never closed by assumption (no silent join).
RESULTS.append(("MS-04", "A gap is reported, never silently joined",
                "PASS" if _v["CP-01"] == BLOCKED else "FAIL",
                f"verdict={_v.get('CP-01')}"))

# MS-05 (schema): declaring BOTH or NEITHER representation is rejected (CP1).
_d = copy.deepcopy(BASE)
_both = path()
_both["segments"] = fact([[[0, 0], [1, 1]]])
_d["circulation"] = [_both]
_ok_both, _ = validate_master(_d, SCHEMA)
_d2 = copy.deepcopy(BASE)
_d2["circulation"] = [{"id": "CP-01", "name": "No geometry",
                       "start_ref": fact("D-01"), "end_ref": fact("D-02")}]
_ok_neither, _ = validate_master(_d2, SCHEMA)
RESULTS.append(("MS-05", "Exactly one geometry representation is allowed (CP1)",
                "PASS" if (not _ok_both and not _ok_neither) else "FAIL",
                f"both={_ok_both} neither={_ok_neither}"))


# ==========================================================================
# MV-011 — circulation must be DECLARED; silence is not acceptance
# ==========================================================================
# MD-01 (negative): no paths and no presence declaration -> ERROR.
_d = copy.deepcopy(BASE)
_d["circulation"] = []
del _d["presence_register"]["circulation"]
_ok, _f, _v = run(_d)
_mv11 = [x for x in _f if x.rule == "MV-011"]
RESULTS.append(("MD-01", "Silence about circulation -> MV-011 ERROR",
                "PASS" if (not _ok and len(_mv11) == 1
                           and _mv11[0].severity == "ERROR") else "FAIL",
                f"ok={_ok} {[(x.rule, x.severity) for x in _f]}"))

# MD-02 (positive): confirmed NOT_PRESENT is accepted, no route invented.
_d = copy.deepcopy(BASE)
_d["circulation"] = []
_d["presence_register"]["circulation"] = confirmed_absent("defined routes")
_ok, _f, _v = run(_d)
RESULTS.append(("MD-02", "Confirmed NOT_PRESENT accepted, no route invented",
                "PASS" if (_ok and any(x.rule == "MV-011" and x.severity == "INFO"
                                       for x in _f) and not _v) else "FAIL",
                f"ok={_ok} verdicts={_v}"))

# MD-03 (unknown): UNKNOWN presence is recorded and NOT reported as clear.
_d = copy.deepcopy(BASE)
_d["circulation"] = []
_d["presence_register"]["circulation"] = unknown_fact("U-410", "not surveyed")
_d["registers"]["unknowns"].append(
    {"id": "U-410", "question": "Defined routes?", "blocking": False,
     "raised_on": TODAY})
_ok, _f, _v = run(_d)
_m = [x for x in _f if x.rule == "MV-011"]
RESULTS.append(("MD-03", "UNKNOWN presence is not reported as circulation-clear",
                "PASS" if (_ok and len(_m) == 1
                           and "NOT reported as circulation-clear" in _m[0].message
                           and not _v) else "FAIL",
                f"ok={_ok} sev={[x.severity for x in _m]}"))

# MD-04 (negative): presence says PRESENT but nothing is declared -> ERROR.
_d = copy.deepcopy(BASE)
_d["circulation"] = []
_ok, _f, _v = run(_d)
_m = [x for x in _f if x.rule == "MV-011"]
RESULTS.append(("MD-04", "PRESENT but no path declared -> missing, not empty",
                "PASS" if (not _ok and len(_m) == 1
                           and _m[0].severity == "ERROR") else "FAIL",
                f"ok={_ok} {[(x.rule, x.severity) for x in _f]}"))

# MD-05 (isolation): MV-011 never invents a route or a verdict.
RESULTS.append(("MD-05", "MV-011 issues no verdict and invents no route",
                "PASS" if not _v else "FAIL", f"verdicts={_v}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B4 — MOVEMENT & CIRCULATION INTEGRITY TEST REPORT")
print("=" * 94)
passed = sum(1 for r in RESULTS if r[2] == "PASS")
total = len(RESULTS)
for rid, desc, verdict, detail in RESULTS:
    mark = "OK  " if verdict == "PASS" else "FAIL"
    print(f"{mark} {rid:8} {desc:58} {detail[:44]}")
print("-" * 94)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 94)
sys.exit(0 if passed == total else 1)
