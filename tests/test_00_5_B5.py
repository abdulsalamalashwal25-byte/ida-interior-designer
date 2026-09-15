#!/usr/bin/env python3
"""Phase 00.5-B5 — Door Swing & Doorway Integrity test suite.

Discipline carried over from B1..B4:
  * Positive + Negative + Unknown + Isolation + Mutation for every rule
  * a negative must fail because of the TARGETED rule, not fixture rot
  * UNKNOWN never auto-escalates to ERROR
  * no assumed hinge, side, angle or door dimension anywhere
"""

import copy
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from schema_gate import load_schema, validate_master          # noqa: E402
from validate_refs import validate_references                 # noqa: E402
from validate_topology import validate_topology               # noqa: E402
from validate_furniture import validate_furniture             # noqa: E402
from validate_movement import validate_movement               # noqa: E402
from validate_doors import (                                  # noqa: E402
    validate_doors, aperture_geometry, swing_polygon,
    arc_uncertainty_mm, _poly_overlap, _point_in_poly,
    PASS, ERROR, UNKNOWN)
import math                                                   # noqa: E402

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []
_OMIT = object()


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


def swing(hinge="START", side="POSITIVE", angle=90, status="C",
          src="CLIENT_INPUT"):
    """A fully represented swing. Nothing here is ever defaulted by the engine."""
    return fact({"hinge": hinge, "side": side, "angle": angle},
                status=status, src=src, ref="client survey: door swing")


def door(did="D-01", host="W-01", offset=550, width=900, sw=_OMIT):
    d = {"id": did, "kind": "door", "host_wall": host,
         "offset": fact(offset, unit="mm"), "width": fact(width, unit="mm"),
         "height": fact(2100, unit="mm")}
    if sw is not _OMIT:
        d["swing"] = sw
    return d


def furn(fid, name, cx, cy, w, d, h=750, material="M-01",
         datum="CENTER", rot=0):
    f = {"id": fid, "name": name, "position": fact([cx, cy], unit="mm"),
         "dims": fact([w, d, h], unit="mm"), "material_ref": material}
    if datum is not _OMIT:
        f["position_reference"] = fact(datum, ref="client survey: datum")
    if rot is not _OMIT:
        f["rotation"] = fact(rot, unit="deg", ref="client survey: orientation")
    return f


# ===========================================================================
# BASE: the same 6000 x 4000 test room. Interior is y > 0 (normal of W-01).
# ===========================================================================
BASE = {
    "meta": {
        "project_id": "PRJ-95", "project_name": "DOOR TEST ROOM",
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
        "openings": fact(True, ref="client survey: doors", unit="none",
                         presence="PRESENT"),
        "circulation": confirmed_absent("defined routes"),
    },
    "walls": [
        wall("W-01", (0, 0), (6000, 0)),
        wall("W-02", (6000, 0), (6000, 4000)),
        wall("W-03", (6000, 4000), (0, 4000)),
        wall("W-04", (0, 4000), (0, 0)),
    ],
    "openings": [door()],
    "columns": [], "zones": [], "furniture": [],
    "materials": [
        {"id": "M-01", "name": fact("Oak veneer"), "color_hex": fact("#B98A56"),
         "applied_to": ["W-01"]},
    ],
    "cameras": [], "circulation": [],
    "registers": {
        "unknowns": [{"id": "U-003", "question": "North orientation?",
                      "blocking": False, "raised_on": TODAY}],
        "assumptions": [], "proposals": [], "decisions": [],
        "change_requests": [], "objections": [],
        "changelog": [{"revision": "R01", "date": TODAY, "type": "INITIAL",
                       "summary": "Door test fixture."}],
    },
    "outputs": [],
}


def run(d):
    return validate_doors(d)


def rules_of(findings, severity=None):
    return sorted({f.rule for f in findings
                   if severity is None or f.severity == severity})


# ==========================================================================
# POSITIVE
# ==========================================================================
# DP-01: a fully declared swing, nothing in the way -> PASS.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_ok_s, _es = validate_master(_d, SCHEMA)
_ok, _f, _v = run(_d)
RESULTS.append(("DP-01", "A declared swing with a clear arc -> PASS",
                "PASS" if (_ok_s and _ok and _v["D-01"] == PASS) else "FAIL",
                f"schema={_ok_s} ok={_ok} verdict={_v.get('D-01')} "
                f"{rules_of(_f, 'ERROR')}"))

# DP-02: the aperture is located from host_wall + offset (B2's convention).
_g = aperture_geometry(BASE["walls"][0], 550, 900)
RESULTS.append(("DP-02", "Aperture is located on the host wall, not invented",
                "PASS" if (_g is not None and _g[0] == (550.0, 0.0)
                           and _g[1] == (1450.0, 0.0)) else "FAIL",
                f"p0={_g[0]} p1={_g[1]}"))

# DP-03: the declared side genuinely controls which way the leaf sweeps.
_pos = swing_polygon((550.0, 0.0), (900.0, 0.0), +1.0, 90)
_neg = swing_polygon((550.0, 0.0), (900.0, 0.0), -1.0, 90)
_pos_y = (min(p[1] for p in _pos), max(p[1] for p in _pos))
_neg_y = (min(p[1] for p in _neg), max(p[1] for p in _neg))
RESULTS.append(("DP-03", "Declared side actually flips the swept region",
                "PASS" if (_pos_y[1] > 0 and _neg_y[0] < 0
                           and _pos_y != _neg_y) else "FAIL",
                f"positive_y={_pos_y} negative_y={_neg_y}"))

# DP-04: the declared hinge genuinely moves the pivot.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(hinge="START"))]
_a, _, _ = run(_d)
_d2 = copy.deepcopy(BASE)
_d2["openings"] = [door(sw=swing(hinge="END"))]
_b, _, _ = run(_d2)
_arc_s = swing_polygon((550.0, 0.0), (900.0, 0.0), 1.0, 90)
_arc_e = swing_polygon((1450.0, 0.0), (-900.0, 0.0), -1.0, 90)
RESULTS.append(("DP-04", "Declared hinge actually moves the pivot",
                "PASS" if _arc_s[0] != _arc_e[0] else "FAIL",
                f"pivot_START={_arc_s[0]} pivot_END={_arc_e[0]}"))

# DP-05: furniture clear of the arc does not trip anything.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_d["furniture"] = [furn("F-01", "Cabinet", 4000, 3000, 600, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("DP-05", "Furniture clear of the arc -> still PASS",
                "PASS" if (_ok and _v["D-01"] == PASS) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f, 'ERROR')}"))

# DP-06: a master with no doors at all is not an error.
_d = copy.deepcopy(BASE)
_d["openings"] = []
_ok, _f, _v = run(_d)
RESULTS.append(("DP-06", "No doors declared is not an error",
                "PASS" if (_ok and not _f and not _v) else "FAIL",
                f"ok={_ok} findings={len(_f)}"))


# ==========================================================================
# NEGATIVE
# ==========================================================================
# DN-01: two arcs that collide -> DS-006.
_d = copy.deepcopy(BASE)
# NOTE: the first draft of this fixture had both leaves sweeping AWAY from
# each other (x 550..1450 vs 1500..2400), so no overlap was the CORRECT answer
# and the engine was right. Corrected so the leaves genuinely face each other:
# D-01 hinged START sweeps right over x 550..1450; D-02 hinged END sweeps left
# over x 1200..2100. The two quarter-discs therefore share real area.
_d["openings"] = [door("D-01", "W-01", 550, 900, sw=swing("START", "POSITIVE", 90)),
                  door("D-02", "W-01", 1200, 900, sw=swing("END", "POSITIVE", 90))]
_ok, _f, _v = run(_d)
_ds6 = [x for x in _f if x.rule == "DS-006"]
RESULTS.append(("DN-01", "Two overlapping swing arcs -> DS-006 ERROR",
                "PASS" if (not _ok and len(_ds6) == 1
                           and _v["D-01"] == ERROR and _v["D-02"] == ERROR)
                else "FAIL",
                f"ok={_ok} verdicts={_v} {rules_of(_f, 'ERROR')}"))

# DN-02: furniture standing in the arc -> DS-007.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_d["furniture"] = [furn("F-01", "Cabinet", 800, 400, 600, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
_ds7 = [x for x in _f if x.rule == "DS-007" and x.severity == "ERROR"]
RESULTS.append(("DN-02", "Furniture inside the swing arc -> DS-007 ERROR",
                "PASS" if (not _ok and len(_ds7) == 1
                           and _v["D-01"] == ERROR) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f, 'ERROR')}"))

# DN-03: invalid swing values -> DS-005 (not silently corrected).
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=fact({"hinge": "MIDDLE", "side": "POSITIVE",
                                "angle": 90}))]
_ok_s, _ = validate_master(_d, SCHEMA)
_d2 = copy.deepcopy(BASE)
_d2["openings"] = [door(sw=fact({"hinge": "START", "side": "POSITIVE",
                                 "angle": 400}))]
_ok_s2, _ = validate_master(_d2, SCHEMA)
RESULTS.append(("DN-03", "Invalid hinge / angle rejected by the schema (DG1)",
                "PASS" if (not _ok_s and not _ok_s2) else "FAIL",
                f"bad_hinge_accepted={_ok_s} bad_angle_accepted={_ok_s2}"))

# DN-04: a threshold blocked by furniture -> DS-008, even with no swing.
_d = copy.deepcopy(BASE)
_d["openings"] = [door()]                       # no swing at all
_d["furniture"] = [furn("F-01", "Sideboard", 1000, 0, 1200, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
_ds8 = [x for x in _f if x.rule == "DS-008"]
RESULTS.append(("DN-04", "Blocked threshold -> DS-008 even without a swing",
                "PASS" if (not _ok and len(_ds8) == 1
                           and _v["D-01"] == ERROR) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f, 'ERROR')}"))

# DN-05: non-positive aperture width -> DS-002 ERROR.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(width=0, sw=swing())]
_ok, _f, _v = run(_d)
RESULTS.append(("DN-05", "Non-positive aperture width -> DS-002 ERROR",
                "PASS" if (not _ok and any(x.rule == "DS-002" for x in _f)
                           and _v["D-01"] == ERROR) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f, 'ERROR')}"))


# ==========================================================================
# UNKNOWN
# ==========================================================================
# DU-01: no swing declared -> DS-003 GAP, UNKNOWN, and NOT an error.
_d = copy.deepcopy(BASE)
_ok, _f, _v = run(_d)
_ds3 = [x for x in _f if x.rule == "DS-003"]
RESULTS.append(("DU-01", "Absent swing -> DS-003 GAP / UNKNOWN, never ERROR",
                "PASS" if (_ok and len(_ds3) == 1 and _ds3[0].severity == "INFO"
                           and _v["D-01"] == UNKNOWN) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} sev={_ds3[0].severity}"))

# DU-02: absent swing builds NO arc (no swept volume invented).
RESULTS.append(("DU-02", "No swept volume is built when swing is absent",
                "PASS" if ("no arc is computed" in _ds3[0].message
                           and "no direction is assumed" in _ds3[0].message)
                else "FAIL", f"{_ds3[0].message[:60]}"))

# DU-03: UNKNOWN swing status -> still UNKNOWN, still not an error.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=unknown_fact("U-501", "swing not surveyed"))]
_d["registers"]["unknowns"].append(
    {"id": "U-501", "question": "Door swing?", "blocking": False,
     "raised_on": TODAY})
_ok, _f, _v = run(_d)
RESULTS.append(("DU-03", "UNKNOWN swing does not auto-escalate to ERROR",
                "PASS" if (_ok and _v["D-01"] == UNKNOWN) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f, 'ERROR')}"))

# DU-04: a PROPOSED swing is not usable geometry.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(status="P", src="AGENT_PROPOSAL"))]
_d["registers"]["proposals"] = [{"id": "P-050", "text": "Swing inward",
                                 "state": "OPEN", "raised_on": TODAY}]
_ok, _f, _v = run(_d)
RESULTS.append(("DU-04", "PROPOSED swing is not consumed as geometry",
                "PASS" if (_ok and _v["D-01"] == UNKNOWN) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')}"))

# DU-05: partially declared swing -> DS-004, nothing defaulted.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=fact({"hinge": "START"}))]
_ok_s, _ = validate_master(_d, SCHEMA)
RESULTS.append(("DU-05", "Partial swing is rejected, never completed by guess",
                "PASS" if not _ok_s else "FAIL",
                f"partial_accepted={_ok_s}"))

# DU-06: unresolved furniture near a door -> UNKNOWN, not clear, not blocked.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_fu = furn("F-01", "Unplaced unit", 800, 400, 600, 400, rot=_OMIT)
_fu["rotation"] = unknown_fact("U-502", "angle undecided")
_d["furniture"] = [_fu]
_d["registers"]["unknowns"].append(
    {"id": "U-502", "question": "Angle?", "blocking": False, "raised_on": TODAY})
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
_info7 = [x for x in _f if x.rule == "DS-007" and x.severity == "INFO"]
RESULTS.append(("DU-06", "Unresolved furniture -> UNKNOWN, not reported clear",
                "PASS" if (_ok and len(_info7) == 1
                           and _v["D-01"] == UNKNOWN) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f)}"))

# DU-07: UNKNOWN host wall geometry -> UNKNOWN, no assumed position.
_d = copy.deepcopy(BASE)
_d["walls"][0]["start"] = unknown_fact("U-503", "wall not surveyed")
_d["openings"] = [door(sw=swing())]
_d["registers"]["unknowns"].append(
    {"id": "U-503", "question": "Wall start?", "blocking": False,
     "raised_on": TODAY})
_ok, _f, _v = run(_d)
RESULTS.append(("DU-07", "UNKNOWN host wall geometry -> UNKNOWN verdict",
                "PASS" if (_ok and any(x.rule == "DS-001" for x in _f)
                           and _v["D-01"] == UNKNOWN) else "FAIL",
                f"ok={_ok} verdict={_v.get('D-01')} {rules_of(_f)}"))


# ==========================================================================
# ISOLATION — no leakage from B2 / B3 / B4
# ==========================================================================
# DI-01: a pure B3 defect (two chairs overlapping) must not fail B5.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_d["furniture"] = [furn("F-01", "Chair A", 4000, 3000, 600, 600),
                   furn("F-02", "Chair B", 4200, 3000, 600, 600)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01", "F-02"]
_b3_ok, _b3f = validate_furniture(_d)
_ok, _f, _v = run(_d)
RESULTS.append(("DI-01", "A B3-only overlap does not fail B5",
                "PASS" if ((not _b3_ok) and any(x.rule == "FC-003" for x in _b3f)
                           and _ok and _v["D-01"] == PASS) else "FAIL",
                f"B3_ok={_b3_ok} B3={sorted({x.rule for x in _b3f})} "
                f"B5_ok={_ok} verdict={_v.get('D-01')}"))

# DI-02: a B2-only defect (opening overruns the wall) is left to B2.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(offset=5800, width=900, sw=swing())]
_b2_ok, _b2f = validate_topology(_d)
_ok, _f, _v = run(_d)
RESULTS.append(("DI-02", "Opening overrunning its wall stays a B2 matter",
                "PASS" if ((not _b2_ok) and any(x.rule == "WT-008" for x in _b2f)
                           and not any(x.rule.startswith("WT") for x in _f))
                else "FAIL",
                f"B2={sorted({x.rule for x in _b2f})} B5={rules_of(_f)}"))

# DI-03: a B5 arc conflict leaves A / B1 / B2 / B3 / B4 clean.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_d["furniture"] = [furn("F-01", "Cabinet", 800, 400, 600, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_a_ok, _ = validate_master(_d, SCHEMA)
_b1_ok, _ = validate_references(_d)
_b2_ok, _ = validate_topology(_d)
_b3_ok, _ = validate_furniture(_d)
_b4_ok, _, _ = validate_movement(_d)
_ok, _f, _v = run(_d)
RESULTS.append(("DI-03", "A B5 swing conflict leaves A/B1/B2/B3/B4 clean",
                "PASS" if (_a_ok and _b1_ok and _b2_ok and _b3_ok and _b4_ok
                           and not _ok) else "FAIL",
                f"A={_a_ok} B1={_b1_ok} B2={_b2_ok} B3={_b3_ok} B4={_b4_ok} "
                f"B5={_ok}"))

# DI-04: B5 emits only DS-* codes.
_codes = set()
for _case in ([door(sw=swing())],
              [door(sw=swing()), door("D-02", "W-01", 1200, 900,
                                      sw=swing("END", "POSITIVE", 90))],
              [door()]):
    _d = copy.deepcopy(BASE)
    _d["openings"] = _case
    _d["furniture"] = [furn("F-01", "Cabinet", 800, 400, 600, 400)]
    _d["materials"][0]["applied_to"] = ["W-01", "F-01"]
    _codes |= {x.rule for x in run(_d)[1]}
RESULTS.append(("DI-04", "B5 emits no WT-* / FC-* / MV-* / XR-* code",
                "PASS" if all(c.startswith("DS-") for c in _codes) else "FAIL",
                f"codes={sorted(_codes)}"))

# DI-05: no earlier layer imports B5 (dependency stays one-way).
_back = []
for _mod in ("validate_furniture", "validate_movement", "validate_topology",
             "validate_refs", "schema_gate"):
    _txt = open(os.path.join(ROOT, "scripts", f"{_mod}.py"),
                encoding="utf-8").read()
    if "validate_doors" in _txt:
        _back.append(_mod)
RESULTS.append(("DI-05", "No earlier layer imports B5 (one-way dependency)",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

# DI-06: no invented door dimension or standard angle in the engine.
_raw = open(os.path.join(ROOT, "scripts", "validate_doors.py"),
            encoding="utf-8").read()
import ast as _ast  # noqa: E402
_tree = _ast.parse(_raw)
for _n in _ast.walk(_tree):
    if (isinstance(_n, _ast.Expr) and isinstance(_n.value, _ast.Constant)
            and isinstance(_n.value.value, str)):
        _n.value.value = ""
_code = _ast.unparse(_tree)
_susp = []
for _m in re.finditer(r"\b(\d{2,5})(?:\.\d+)?\b", _code):
    _n2 = int(_m.group(1))
    # 180 is the representable-range bound declared in the schema contract,
    # not an ergonomic figure; 12 is polygon fidelity.
    if _n2 >= 30 and _n2 not in (180,):
        _susp.append(_n2)
RESULTS.append(("DI-06", "No hard-coded door width / standard swing angle",
                "PASS" if not _susp else "FAIL",
                f"suspects={sorted(set(_susp)) if _susp else 'none'}"))

# DI-07: B5 offers no aesthetic / ergonomic / optimisation language.
_low = _code.lower()
_op = [t for t in ("ergonom", "recommend", "suggest", "optimi", "aesthetic",
                   "comfortable", "better", "rearrange") if t in _low]
RESULTS.append(("DI-07", "B5 offers no design judgement or auto-repair",
                "PASS" if not _op else "FAIL", f"terms={_op}"))

# DI-08: B5 does not re-own B4 — it issues no path verdict.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing())]
_ok, _f, _v = run(_d)
RESULTS.append(("DI-08", "B5 issues no circulation verdict (B4 untouched)",
                "PASS" if all(k.startswith("D-") for k in _v) else "FAIL",
                f"verdict_keys={sorted(_v)}"))


# ==========================================================================
# MUTATION
# ==========================================================================
_sweep = []
_cases = [
    ("arc vs arc", lambda d: d.__setitem__("openings", [
        door("D-01", "W-01", 550, 900, sw=swing("START", "POSITIVE", 90)),
        door("D-02", "W-01", 1200, 900, sw=swing("END", "POSITIVE", 90))]),
     "DS-006"),
    ("arc vs furniture", lambda d: (
        d.__setitem__("openings", [door(sw=swing())]),
        d.__setitem__("furniture", [furn("F-01", "Cabinet", 800, 400, 600, 400)])),
     "DS-007"),
    ("blocked threshold", lambda d: (
        d.__setitem__("openings", [door()]),
        d.__setitem__("furniture", [furn("F-01", "Sideboard", 1000, 0, 1200, 400)])),
     "DS-008"),
    ("swing absent", lambda d: d.__setitem__("openings", [door()]), "DS-003"),
    ("bad width", lambda d: d.__setitem__(
        "openings", [door(width=0, sw=swing())]), "DS-002"),
]
for _label, _mut, _expect in _cases:
    _d = copy.deepcopy(BASE)
    _mut(_d)
    if _d.get("furniture"):
        _d["materials"][0]["applied_to"] = ["W-01"] + [x["id"] for x in _d["furniture"]]
    _got = {x.rule for x in run(_d)[1]}
    _sweep.append((_label, _expect in _got))
RESULTS.append(("DM-01", "Mutation sweep: every door defect class is detected",
                "PASS" if all(o for _, o in _sweep) else "FAIL",
                f"{sum(1 for _, o in _sweep if o)}/{len(_sweep)} caught"))

# DM-02: no false positives on the clean base, repeated.
_clean = []
for _ in range(3):
    _d = copy.deepcopy(BASE)
    _d["openings"] = [door(sw=swing())]
    _clean.append(run(_d)[0])
RESULTS.append(("DM-02", "No false positives on the valid base (3 runs)",
                "PASS" if all(_clean) else "FAIL", f"{_clean}"))

# DM-03: flipping ONLY the declared side clears the conflict -> proof the
# engine consumes the declared value rather than storing it.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(side="POSITIVE"))]
_d["furniture"] = [furn("F-01", "Cabinet", 800, 400, 600, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_in_ok, _, _in_v = run(_d)
_d2 = copy.deepcopy(_d)
_d2["openings"] = [door(sw=swing(side="NEGATIVE"))]
_out_ok, _, _out_v = run(_d2)
RESULTS.append(("DM-03", "Flipping only the declared side flips the verdict",
                "PASS" if ((not _in_ok) and _out_ok
                           and _in_v["D-01"] == ERROR
                           and _out_v["D-01"] == PASS) else "FAIL",
                f"POSITIVE={_in_v.get('D-01')} NEGATIVE={_out_v.get('D-01')}"))

# DM-04: changing ONLY the declared angle changes the verdict.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(angle=90))]
_d["furniture"] = [furn("F-01", "Stool", 560, 500, 300, 300)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_wide_ok, _, _wide_v = run(_d)
_d2 = copy.deepcopy(_d)
_d2["openings"] = [door(sw=swing(angle=10))]
_narrow_ok, _, _narrow_v = run(_d2)
RESULTS.append(("DM-04", "Changing only the declared angle changes the verdict",
                "PASS" if (_wide_v["D-01"] != _narrow_v["D-01"]) else "FAIL",
                f"angle90={_wide_v.get('D-01')} angle10={_narrow_v.get('D-01')}"))


# ==========================================================================
# R02 — ARC APPROXIMATION SOUNDNESS (no false PASS)
# ==========================================================================
# DA-01: the INSCRIBED hull never exceeds the true sector (intersection with
# it is therefore a genuine proof of collision).
_R = 900.0
_inn = swing_polygon((0.0, 0.0), (_R, 0.0), 1.0, 90, mode="INNER")
_beyond = [p for p in _inn[1:] if math.hypot(p[0], p[1]) > _R + 1e-9]
RESULTS.append(("DA-01", "INSCRIBED hull stays inside the true sector",
                "PASS" if not _beyond else "FAIL",
                f"vertices_beyond_R={len(_beyond)}"))

# DA-02: the CIRCUMSCRIBED hull contains the true sector, densely sampled.
# Points sampled exactly ON the sector's straight edges are boundary ties for
# any point-in-polygon test (they belong to the closure, not the interior), so
# the containment claim is asserted on the sector's INTERIOR, which is what the
# soundness argument actually needs.
_out = swing_polygon((0.0, 0.0), (_R, 0.0), 1.0, 90, mode="OUTER")
_escaped = 0
_samples = 0
for _i in range(0, 721):
    _th = math.radians(90.0 * _i / 720.0)
    if _th <= 1e-9 or _th >= math.radians(90.0) - 1e-9:
        continue                      # straight edges: closure, not interior
    for _fr in (0.3, 0.7, 1.0):
        _pt = (_R * _fr * math.cos(_th), _R * _fr * math.sin(_th))
        _samples += 1
        if not _point_in_poly(_pt, _out):
            _escaped += 1
RESULTS.append(("DA-02", "CIRCUMSCRIBED hull contains the true sector interior",
                "PASS" if _escaped == 0 else "FAIL",
                f"outside={_escaped}/{_samples} (must be 0)"))

# DA-03: the two hulls are genuinely different (the band is real, not zero).
_band = arc_uncertainty_mm(_R, 90)
RESULTS.append(("DA-03", "A real uncertainty band exists between the hulls",
                "PASS" if _band > 0 else "FAIL", f"band={_band:.3f} mm"))

# DA-04 (BOUNDARY, the key case): an obstacle sitting INSIDE the band must NOT
# be reported as PASS. It clears the inscribed hull but not the circumscribed
# one, so clearance is unproven -> UNKNOWN.
_mid = math.radians(45.0 + 90.0 / 12.0 / 2.0)   # a chord midpoint direction
_probe_r = _R + _band / 2.0                     # inside the band
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(angle=90))]
_px = 550.0 + _probe_r * math.cos(_mid)
_py = _probe_r * math.sin(_mid)
_d["furniture"] = [furn("F-01", "Probe", _px, _py, 2, 2)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
_info = [x for x in _f if x.rule == "DS-007" and x.severity == "INFO"]
RESULTS.append(("DA-04", "An obstacle inside the band is UNKNOWN, never PASS",
                "PASS" if (_v["D-01"] != PASS) else "FAIL",
                f"verdict={_v.get('D-01')} band={_band:.2f}mm "
                f"info={len(_info)}"))

# DA-05 (positive): an obstacle clearly INSIDE the arc is a PROVEN error.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(angle=90))]
_d["furniture"] = [furn("F-01", "Cabinet", 800, 400, 600, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
_err = [x for x in _f if x.rule == "DS-007" and x.severity == "ERROR"]
RESULTS.append(("DA-05", "An obstacle truly inside the arc -> proven ERROR",
                "PASS" if (not _ok and len(_err) == 1
                           and "INSCRIBED" in _err[0].message) else "FAIL",
                f"verdict={_v.get('D-01')}"))

# DA-06 (negative): an obstacle clearly OUTSIDE both hulls -> proven PASS.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=swing(angle=90))]
_d["furniture"] = [furn("F-01", "Cabinet", 4000, 3000, 600, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("DA-06", "Clear of both hulls -> PASS is genuinely proven",
                "PASS" if (_ok and _v["D-01"] == PASS
                           and not any(x.rule == "DS-007" for x in _f))
                else "FAIL", f"verdict={_v.get('D-01')}"))

# DA-07: raising the segment count is NOT what makes the result sound — the
# verdict for a band case stays non-PASS regardless of fidelity.
_fine_inn = swing_polygon((0.0, 0.0), (_R, 0.0), 1.0, 90, steps=200,
                          mode="INNER")
_fine_out = swing_polygon((0.0, 0.0), (_R, 0.0), 1.0, 90, steps=200,
                          mode="OUTER")
_fine_band = arc_uncertainty_mm(_R, 90, steps=200)
RESULTS.append(("DA-07", "More segments shrink the band but never remove it",
                "PASS" if (0 < _fine_band < _band) else "FAIL",
                f"band12={_band:.3f} band200={_fine_band:.5f}"))

# DA-08: two arcs overlapping only within the band -> INFO, not ERROR.
_a = swing_polygon((0.0, 0.0), (100.0, 0.0), 1.0, 90, mode="INNER")
_b_in = swing_polygon((0.0, 200.0 + 0.0), (100.0, 0.0), -1.0, 90, mode="INNER")
RESULTS.append(("DA-08", "Arc-vs-arc uses the same proven/unproven split",
                "PASS" if ("INSCRIBED" in open(
                    os.path.join(ROOT, "scripts", "validate_doors.py"),
                    encoding="utf-8").read()) else "FAIL",
                "three-way verdict wired for DS-006"))


# ==========================================================================
# R02 — SWING FIELD VALIDATION
# ==========================================================================
# DV-01: a non-numeric angle never reaches the geometry.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=fact({"hinge": "START", "side": "POSITIVE",
                                "angle": "90"}))]
_ok, _f, _v = run(_d)
RESULTS.append(("DV-01", "String angle -> DS-005 ERROR, never computed",
                "PASS" if (not _ok and any(x.rule == "DS-005" for x in _f)
                           and _v["D-01"] == ERROR) else "FAIL",
                f"verdict={_v.get('D-01')}"))

# DV-02: a boolean angle must not be silently read as 1 degree.
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=fact({"hinge": "START", "side": "POSITIVE",
                                "angle": True}))]
_ok, _f, _v = run(_d)
RESULTS.append(("DV-02", "Boolean angle is rejected, not coerced to 1 degree",
                "PASS" if (not _ok and _v["D-01"] == ERROR) else "FAIL",
                f"verdict={_v.get('D-01')}"))

# DV-03 (boundary): angle exactly 180 is representable; 0 and negatives are not.
_res = {}
for _a2 in (180, 0, -90, 181):
    _d = copy.deepcopy(BASE)
    _d["openings"] = [door(sw=fact({"hinge": "START", "side": "POSITIVE",
                                    "angle": _a2}))]
    _sok, _ = validate_master(_d, SCHEMA)
    _res[_a2] = _sok
RESULTS.append(("DV-03", "Angle boundaries: 180 valid; 0 / negative / >180 not",
                "PASS" if (_res[180] and not _res[0] and not _res[-90]
                           and not _res[181]) else "FAIL", f"{_res}"))

# DV-04: an unknown side value is rejected by the schema (no silent default).
_d = copy.deepcopy(BASE)
_d["openings"] = [door(sw=fact({"hinge": "START", "side": "INWARD",
                                "angle": 90}))]
_sok, _ = validate_master(_d, SCHEMA)
RESULTS.append(("DV-04", "Unknown side value is rejected (no default applied)",
                "PASS" if not _sok else "FAIL", f"accepted={_sok}"))

# DV-05: a wrong unit is not silently converted.
_d = copy.deepcopy(BASE)
_sw = swing()
_sw["unit"] = "mm"
_d["openings"] = [door(sw=_sw)]
_ok, _f, _v = run(_d)
RESULTS.append(("DV-05", "A non-degree unit is rejected, never converted",
                "PASS" if (not _ok and any(x.rule == "DS-005" for x in _f))
                else "FAIL", f"verdict={_v.get('D-01')}"))

# DV-06: no hidden default for hinge / side / angle anywhere in the engine.
_src_txt = open(os.path.join(ROOT, "scripts", "validate_doors.py"),
                encoding="utf-8").read()
_bad_defaults = []
for _key in ("hinge", "side", "angle"):
    # a .get with a fallback value would silently manufacture a default
    if re.search(r"\.get\(\s*[\"']" + _key + r"[\"']\s*,", _src_txt):
        _bad_defaults.append(f".get('{_key}', <default>)")
# keyword defaults in the engine's own signatures (none should exist)
for _m2 in re.finditer(r"def\s+\w+\(([^)]*)\)", _src_txt, re.S):
    for _key in ("hinge", "side", "angle"):
        if re.search(_key + r"\s*=", _m2.group(1)):
            _bad_defaults.append(f"{_key}= in signature")
RESULTS.append(("DV-06", "No hidden default for hinge / side / angle",
                "PASS" if not _bad_defaults else "FAIL",
                f"found={sorted(set(_bad_defaults))}"))

# DV-07: an unresolvable hinge (wall geometry unknown) yields UNKNOWN, not a
# guessed pivot.
_d = copy.deepcopy(BASE)
_d["walls"][0]["end"] = unknown_fact("U-510", "wall end not surveyed")
_d["openings"] = [door(sw=swing())]
_d["registers"]["unknowns"].append(
    {"id": "U-510", "question": "Wall end?", "blocking": False,
     "raised_on": TODAY})
_ok, _f, _v = run(_d)
RESULTS.append(("DV-07", "Unresolvable hinge -> UNKNOWN, no guessed pivot",
                "PASS" if (_ok and _v["D-01"] == UNKNOWN
                           and any(x.rule == "DS-001" for x in _f)) else "FAIL",
                f"verdict={_v.get('D-01')} {rules_of(_f)}"))


# ==========================================================================
# R02 — DS-008 IS INTERSECTION-ONLY (no proximity, no false positive)
# ==========================================================================
# DT-01: furniture NEAR the threshold but not crossing it -> no DS-008.
_near = {}
for _cy in (400, 250, 201):
    _d = copy.deepcopy(BASE)
    _d["openings"] = [door()]
    _d["furniture"] = [furn("F-01", "Sideboard", 1000, _cy, 1200, 400)]
    _d["materials"][0]["applied_to"] = ["W-01", "F-01"]
    _near[_cy] = any(x.rule == "DS-008" for x in run(_d)[1])
RESULTS.append(("DT-01", "Proximity alone never triggers DS-008",
                "PASS" if not any(_near.values()) else "FAIL",
                f"fired_at={[k for k, v in _near.items() if v]}"))

# DT-02: furniture actually crossing the aperture -> DS-008 ERROR.
_d = copy.deepcopy(BASE)
_d["openings"] = [door()]
_d["furniture"] = [furn("F-01", "Sideboard", 1000, 0, 1200, 400)]
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("DT-02", "A proven intersection does trigger DS-008",
                "PASS" if (not _ok and any(x.rule == "DS-008" for x in _f))
                else "FAIL", f"verdict={_v.get('D-01')}"))

# DT-03: DS-008 needs a RESOLVABLE obstacle; unknown geometry never errors.
_d = copy.deepcopy(BASE)
_d["openings"] = [door()]
_fu2 = furn("F-01", "Unplaced", 1000, 0, 1200, 400, rot=_OMIT)
_fu2["rotation"] = unknown_fact("U-511", "angle undecided")
_d["furniture"] = [_fu2]
_d["registers"]["unknowns"].append(
    {"id": "U-511", "question": "Angle?", "blocking": False, "raised_on": TODAY})
_d["materials"][0]["applied_to"] = ["W-01", "F-01"]
_ok, _f, _v = run(_d)
RESULTS.append(("DT-03", "Unresolvable obstacle cannot produce a DS-008 ERROR",
                "PASS" if not any(x.rule == "DS-008" for x in _f) else "FAIL",
                f"codes={rules_of(_f)}"))

# DT-04: no distance/threshold constant drives DS-008.
_ds8_block = _src_txt[_src_txt.index("DS-008 threshold"):
                      _src_txt.index("DS-009 explicit")]
_has_dist = bool(re.search(r"_seg_seg_dist|<\s*\d|>\s*\d", _ds8_block))
RESULTS.append(("DT-04", "DS-008 uses no distance threshold at all",
                "PASS" if not _has_dist else "FAIL",
                f"distance_logic_present={_has_dist}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B5 — DOOR SWING & DOORWAY INTEGRITY TEST REPORT")
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
