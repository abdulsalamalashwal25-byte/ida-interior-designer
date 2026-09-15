#!/usr/bin/env python3
"""
test_00_5_B3.py — Furniture Geometry & Clearance Integrity acceptance tests.

Discipline carried from B1/B2:
  - positive + negative + isolation per rule
  - every negative asserts the EXACT rule and NO collateral ERROR
  - a mutation that breaks A, B1 or B2 is a FAILED test, not a pass
  - clearance tests prove the engine invents NO numbers
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from schema_gate import validate_master, load_schema        # noqa: E402
from validate_refs import validate_references               # noqa: E402
from validate_topology import validate_topology             # noqa: E402
from validate_furniture import validate_furniture           # noqa: E402

SCHEMA = load_schema()
TODAY = "2026-09-11"
RESULTS = []


def fact(value, status="C", src="CLIENT_INPUT", ref="test fixture", **kw):
    f = {"value": value, "status": status, "source_type": src,
         "source_ref": ref, "recorded_on": TODAY}
    f.update(kw)
    return f


def confirmed_absent(what):
    return {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
            "source_ref": f"client survey: no {what}", "recorded_on": TODAY,
            "presence": "NOT_PRESENT"}


def wall(wid, a, b, thickness=200):
    return {"id": wid, "start": fact(list(a), unit="mm"),
            "end": fact(list(b), unit="mm"),
            "thickness": fact(thickness, unit="mm"), "structural": fact(True)}


_OMIT = object()


def piece(fid, name, cx, cy, w, d, h=750, material="M-01",
          datum="CENTER", rot=0, **kw):
    """Build a furniture item.

    datum/rot default to explicitly DECLARED values, because after the R02
    patch an absent field means UNKNOWN and blocks geometric judgement.
    Pass datum=_OMIT or rot=_OMIT to leave the field out entirely.
    """
    p = {"id": fid, "name": name, "position": fact([cx, cy], unit="mm"),
         "dims": fact([w, d, h], unit="mm"), "material_ref": material}
    if datum is not _OMIT:
        p["position_reference"] = fact(datum, ref="client survey: datum declared")
    if rot is not _OMIT:
        p["rotation"] = fact(rot, unit="deg", ref="client survey: orientation")
    p.update(kw)
    return p


# ===========================================================================
# BASE: 6000 x 4000 room, walls on the boundary, three well-spaced pieces.
# Interior clear span is 5800 x 3800 (walls are 200 thick, centre-line).
# ===========================================================================
BASE = {
    "meta": {
        "project_id": "PRJ-97", "project_name": "FURNITURE TEST ROOM",
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
        "orientation_north": {"value": None, "status": "U",
                              "source_type": "NOT_PROVIDED",
                              "source_ref": "not supplied", "recorded_on": TODAY,
                              "blocking": False, "unknown_id": "U-003"},
        "floor_level": fact(0, unit="mm"),
    },
    "presence_register": {
        "columns": confirmed_absent("columns"),
        "beams": confirmed_absent("beams"),
        "protrusions": confirmed_absent("protrusions"),
        "level_changes": confirmed_absent("level changes"),
        "services": confirmed_absent("services"),
        "existing_furniture": confirmed_absent("existing furniture"),
        "openings": confirmed_absent("openings"),
    },
    "walls": [
        wall("W-01", (0, 0), (6000, 0)),
        wall("W-02", (6000, 0), (6000, 4000)),
        wall("W-03", (6000, 4000), (0, 4000)),
        wall("W-04", (0, 4000), (0, 0)),
    ],
    "openings": [],
    "columns": [],
    "zones": [],
    "furniture": [
        piece("F-01", "Table", 1500, 1500, 1200, 800),
        piece("F-02", "Sofa", 4200, 1500, 2000, 900),
        piece("F-03", "Cabinet", 1500, 3000, 1000, 450),
    ],
    "materials": [
        {"id": "M-01", "name": fact("Oak veneer"), "color_hex": fact("#B98A56"),
         "applied_to": ["F-01", "F-02", "F-03"]},
    ],
    "cameras": [],
    "registers": {
        "unknowns": [{"id": "U-003", "question": "North orientation?",
                      "blocking": False, "raised_on": TODAY}],
        "assumptions": [], "proposals": [], "decisions": [],
        "change_requests": [], "objections": [],
        "changelog": [{"revision": "R01", "date": TODAY, "type": "INITIAL",
                       "summary": "Furniture test fixture."}],
    },
    "outputs": [],
}


def mutate(fn):
    d = copy.deepcopy(BASE)
    fn(d)
    return d


def expect_exactly(test_id, title, mutator, expected_rule, expected_count=1):
    """Corrupt ONE thing; demand exactly the expected B3 rule.
    Guards: must not break A, B1 or B2."""
    data = mutate(mutator)

    ok_a, errs_a = validate_master(data, SCHEMA)
    if not ok_a:
        RESULTS.append((test_id, title, "FAIL",
                        f"broke SCHEMA: {errs_a[0][:55]}"))
        return
    ok_b1, f_b1 = validate_references(data)
    if not ok_b1:
        RESULTS.append((test_id, title, "FAIL", f"broke B1: {f_b1[0].rule}"))
        return
    ok_b2, f_b2 = validate_topology(data)
    if not ok_b2:
        RESULTS.append((test_id, title, "FAIL",
                        f"broke B2: {[x.rule for x in f_b2 if x.severity=='ERROR'][:2]}"))
        return

    ok, findings = validate_furniture(data)
    errors = [f for f in findings if f.severity == "ERROR"]
    codes = [f.rule for f in errors]
    hit = [c for c in codes if c == expected_rule]
    other = [c for c in codes if c != expected_rule]

    if ok:
        RESULTS.append((test_id, title, "FAIL", "accepted — rule never fired"))
    elif not hit:
        RESULTS.append((test_id, title, "FAIL", f"wrong rule: {sorted(set(codes))}"))
    elif other:
        RESULTS.append((test_id, title, "FAIL", f"collateral: {sorted(set(other))}"))
    elif len(hit) != expected_count:
        RESULTS.append((test_id, title, "FAIL",
                        f"{expected_rule} x{len(hit)}, expected {expected_count}"))
    else:
        RESULTS.append((test_id, title, "PASS",
                        f"{expected_rule} x{len(hit)}, no collateral"))


def expect_clean(test_id, title, data=None):
    data = data if data is not None else copy.deepcopy(BASE)
    ok_a, ea = validate_master(data, SCHEMA)
    ok_b1, fb1 = validate_references(data)
    ok_b2, fb2 = validate_topology(data)
    ok, findings = validate_furniture(data)
    if not ok_a:
        RESULTS.append((test_id, title, "FAIL", f"schema: {ea[0][:55]}"))
    elif not ok_b1:
        RESULTS.append((test_id, title, "FAIL", f"b1: {fb1[0].rule}"))
    elif not ok_b2:
        RESULTS.append((test_id, title, "FAIL", f"b2: {fb2[0].rule}"))
    elif not ok:
        errs = [f for f in findings if f.severity == "ERROR"]
        RESULTS.append((test_id, title, "FAIL",
                        f"false positive: {errs[0].rule} {errs[0].message[:35]}"))
    else:
        RESULTS.append((test_id, title, "PASS", ""))


# ===========================================================================
# POSITIVE TESTS
# ===========================================================================
expect_clean("FP-00", "Well-spaced furniture in a valid room passes")

_p = copy.deepcopy(BASE)
# F-01 spans x 900..2100. Chair half-width 200 -> touching at centre 2300.
# A 1mm gap therefore means centre 2301.
_p["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800),
                   piece("F-02", "Chair", 2301, 1500, 400, 400)]
_p["materials"][0]["applied_to"] = ["F-01", "F-02"]
expect_clean("FP-01", "Pieces separated by 1mm do not count as overlapping", _p)

_p = copy.deepcopy(BASE)
# Exactly edge-to-edge: chair centre 2300 -> left edge 2100 = table right edge.
_p["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800),
                   piece("F-02", "Chair", 2300, 1500, 400, 400)]
_p["materials"][0]["applied_to"] = ["F-01", "F-02"]
expect_clean("FP-02", "Pieces touching exactly edge-to-edge are accepted", _p)

_p = copy.deepcopy(BASE)
_p["furniture"] = [piece("F-01", "Cabinet", 3000, 300, 1000, 400)]
_p["materials"][0]["applied_to"] = ["F-01"]
expect_clean("FP-03", "Piece flush against a wall face (not inside it) is accepted", _p)

_p = copy.deepcopy(BASE)
_p["furniture"][0]["clearance"] = fact(600, unit="mm",
                                       ref="client brief: 600mm circulation")
expect_clean("FP-04", "Approved clearance that IS met passes", _p)

_p = copy.deepcopy(BASE)
_p["presence_register"]["columns"] = fact(True, ref="client survey: one column",
                                          unit="none", presence="PRESENT")
_p["columns"] = [{"id": "C-01", "position": fact([3000, 2000], unit="mm"),
                  "dims": fact([300, 300], unit="mm")}]
expect_clean("FP-05", "Furniture clear of a column is accepted", _p)

_p = copy.deepcopy(BASE)
_p["furniture"] = [piece("F-01", "Chair A", 1000, 1000, 400, 400),
                   piece("F-02", "Chair B", 2000, 1000, 400, 400)]
_p["materials"][0]["applied_to"] = ["F-01", "F-02"]
expect_clean("FP-06", "Identical models at different positions are legitimate", _p)


# ===========================================================================
# NEGATIVE TESTS
# ===========================================================================
def _unresolved_dims(d):
    d["furniture"][0]["dims"] = {
        "value": None, "status": "U", "source_type": "NOT_PROVIDED",
        "source_ref": "not specified by client", "recorded_on": TODAY,
        "blocking": False, "unknown_id": "U-030"}
    d["registers"]["unknowns"].append(
        {"id": "U-030", "question": "Dimensions of F-01?", "blocking": False,
         "raised_on": TODAY})


expect_exactly("FN-001a", "UNKNOWN dims are flagged, never invented",
               _unresolved_dims, "FC-001")


def _unresolved_pos(d):
    d["furniture"][1]["position"] = {
        "value": None, "status": "U", "source_type": "NOT_PROVIDED",
        "source_ref": "position not decided", "recorded_on": TODAY,
        "blocking": False, "unknown_id": "U-031"}
    d["registers"]["unknowns"].append(
        {"id": "U-031", "question": "Position of F-02?", "blocking": False,
         "raised_on": TODAY})


expect_exactly("FN-001b", "UNKNOWN position is flagged, never inferred",
               _unresolved_pos, "FC-001")

expect_exactly("FN-002", "Non-positive footprint is caught",
               lambda d: d["furniture"][0].__setitem__("dims", fact([0, 800, 750], unit="mm")),
               "FC-002")

expect_exactly("FN-003a", "Overlapping furniture is caught",
               lambda d: d["furniture"][1].__setitem__("position", fact([1800, 1500], unit="mm")),
               "FC-003")


def _partial_overlap(d):
    d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800),
                      piece("F-02", "Rug", 1900, 1700, 1200, 800)]
    d["materials"][0]["applied_to"] = ["F-01", "F-02"]


expect_exactly("FN-003b", "Partially overlapping footprints are caught",
               _partial_overlap, "FC-003")

expect_exactly("FN-004", "Furniture buried inside a wall body is caught",
               lambda d: d["furniture"][0].__setitem__("position", fact([1500, 20], unit="mm")),
               "FC-004")


def _column_clash(d):
    d["presence_register"]["columns"] = fact(True, ref="client survey: one column",
                                             unit="none", presence="PRESENT")
    d["columns"] = [{"id": "C-01", "position": fact([1500, 1500], unit="mm"),
                     "dims": fact([300, 300], unit="mm")}]


expect_exactly("FN-005", "Furniture clashing with a fixed column is caught",
               _column_clash, "FC-005")


def _duplicate(d):
    d["furniture"].append(piece("F-04", "Table copy", 1500, 1500, 1200, 800))
    d["materials"][0]["applied_to"].append("F-04")


expect_exactly("FN-006", "Illegitimate duplicate piece is caught", _duplicate, "FC-006")


def _clearance_breach(d):
    """Two pieces 300mm apart, with an APPROVED 600mm clearance declared."""
    d["furniture"] = [
        piece("F-01", "Table", 1500, 1500, 1200, 800,
              clearance=fact(600, unit="mm", ref="client brief: 600mm circulation")),
        piece("F-02", "Cabinet", 2400, 1500, 400, 400),
    ]
    d["materials"][0]["applied_to"] = ["F-01", "F-02"]


expect_exactly("FN-007", "Breach of an APPROVED clearance is caught",
               _clearance_breach, "FC-007")


# ===========================================================================
# CLEARANCE POLICY — the engine must invent nothing
# ===========================================================================
def _cl(status, src, value=600, **extra):
    d = copy.deepcopy(BASE)
    d["furniture"] = [
        piece("F-01", "Table", 1500, 1500, 1200, 800),
        piece("F-02", "Cabinet", 2400, 1500, 400, 400),
    ]
    d["materials"][0]["applied_to"] = ["F-01", "F-02"]
    cl = {"value": value, "unit": "mm", "status": status, "source_type": src,
          "source_ref": "clearance under test", "recorded_on": TODAY}
    cl.update(extra)
    d["furniture"][0]["clearance"] = cl
    return d


# CL-01: no clearance declared at all -> nothing invented, nothing enforced.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800),
                   piece("F-02", "Cabinet", 2400, 1500, 400, 400)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("CL-01", "No clearance declared: engine invents no rule",
                "PASS" if (_ok and not any(x.rule in ("FC-007", "FC-008") for x in _f))
                else "FAIL", f"findings={[x.rule for x in _f]}"))

# CL-02: UNKNOWN clearance -> INFO gap, never enforced.
_d = _cl("U", "NOT_PROVIDED", None)
_d["furniture"][0]["clearance"] = {
    "value": None, "unit": "mm", "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "clearance not specified", "recorded_on": TODAY,
    "blocking": False, "unknown_id": "U-040"}
_d["registers"]["unknowns"].append(
    {"id": "U-040", "question": "Required clearance around F-01?",
     "blocking": False, "raised_on": TODAY})
_ok, _f = validate_furniture(_d)
_info = [x for x in _f if x.rule == "FC-008" and x.severity == "INFO"]
_errs = [x for x in _f if x.severity == "ERROR"]
RESULTS.append(("CL-02", "UNKNOWN clearance -> INFO gap, no geometric rule",
                "PASS" if (_ok and _info and not _errs) else "FAIL",
                f"ok={_ok} info={len(_info)} err={len(_errs)}"))

# CL-03: a PROPOSED clearance is not enforceable.
_d = _cl("P", "AGENT_PROPOSAL", 600, proposal_id="P-001")
_d["registers"]["proposals"] = [{"id": "P-001", "text": "Propose 600mm clearance",
                                 "state": "OPEN", "raised_on": TODAY}]
_ok, _f = validate_furniture(_d)
RESULTS.append(("CL-03", "PROPOSED clearance is NOT enforced (needs approval)",
                "PASS" if (_ok and any(x.rule == "FC-008" for x in _f)
                           and not any(x.rule == "FC-007" for x in _f)) else "FAIL",
                f"ok={_ok} codes={[x.rule for x in _f]}"))

# CL-04: an unapproved ASSUMPTION is not enforceable.
_d = _cl("A", "AGENT_ASSUMPTION", 600, assumption_id="A-01",
         impact="affects spacing", approval_state="PENDING_APPROVAL")
_d["registers"]["assumptions"] = [{"id": "A-01", "text": "Assume 600mm clearance",
                                   "impact": "affects spacing",
                                   "approval_state": "PENDING_APPROVAL",
                                   "raised_on": TODAY}]
_ok, _f = validate_furniture(_d)
RESULTS.append(("CL-04", "Unapproved ASSUMPTION clearance is NOT enforced",
                "PASS" if (_ok and any(x.rule == "FC-008" for x in _f)) else "FAIL",
                f"ok={_ok} codes={[x.rule for x in _f]}"))

# CL-05: an EXTERNAL_STANDARD figure is not enforceable on its own.
_d = _cl("P", "EXTERNAL_STANDARD", 900, proposal_id="P-002")
_d["furniture"][0]["clearance"]["external"] = {
    "ref": "Published circulation guidance", "retrieved_on": TODAY,
    "applicability_note": "Generic figure; not verified for this project."}
_d["registers"]["proposals"] = [{"id": "P-002", "text": "Standard 900mm aisle",
                                 "state": "OPEN", "raised_on": TODAY}]
_ok, _f = validate_furniture(_d)
RESULTS.append(("CL-05", "EXTERNAL standard is NOT auto-enforced as a project rule",
                "PASS" if (_ok and any(x.rule == "FC-008" for x in _f)) else "FAIL",
                f"ok={_ok} codes={[x.rule for x in _f]}"))

# CL-06: an APPROVED clearance IS enforced.
_d = _cl("C", "USER_APPROVAL", 600, decision_id="DEC-001", approved_by="USER",
         approved_on=TODAY, approved_in_revision="R01")
_d["registers"]["proposals"] = [{"id": "P-003", "text": "600mm clearance",
                                 "state": "APPROVED", "raised_on": TODAY,
                                 "decision_id": "DEC-001"}]
_d["registers"]["decisions"] = [{
    "decision_id": "DEC-001", "title": "Clearance around F-01",
    "linked_proposal": "P-003", "rationale": "Agreed with client for access",
    "alternatives_considered": ["450mm (rejected: too tight)"],
    "approved_by": "USER", "approved_on": TODAY, "approved_in_revision": "R01"}]
_ok, _f = validate_furniture(_d)
RESULTS.append(("CL-06", "APPROVED clearance IS enforced (FC-007 fires)",
                "PASS" if ((not _ok) and any(x.rule == "FC-007" for x in _f)) else "FAIL",
                f"ok={_ok} codes={[x.rule for x in _f]}"))

# CL-07: the engine contains no hard-coded clearance numbers.
_src = (Path(__file__).resolve().parent.parent / "scripts"
        / "validate_furniture.py").read_text(encoding="utf-8")
import re  # noqa: E402
_code = "\n".join(ln for ln in _src.splitlines()
                  if not ln.strip().startswith("#"))
_suspicious = [n for n in re.findall(r"\b(\d{3,4})\b", _code)
               if 200 <= int(n) <= 2000]
RESULTS.append(("CL-07", "No hard-coded clearance/ergonomic numbers in the engine",
                "PASS" if not _suspicious else "FAIL",
                f"found: {sorted(set(_suspicious))}" if _suspicious else "none"))


# ===========================================================================
# ISOLATION / SCOPE PROOFS
# ===========================================================================
_iso = mutate(lambda d: d["furniture"][1].__setitem__("position", fact([1800, 1500], unit="mm")))
_a, _ = validate_master(_iso, SCHEMA)
_b1, _ = validate_references(_iso)
_b2, _ = validate_topology(_iso)
_b3, _ = validate_furniture(_iso)
RESULTS.append(("FI-01", "Overlap is A/B1/B2-valid but B3-invalid",
                "PASS" if (_a and _b1 and _b2 and not _b3) else "FAIL",
                f"A={_a} B1={_b1} B2={_b2} B3={_b3}"))

# FI-02: B3 must not re-report B1's missing material_ref.
_iso = mutate(lambda d: d["furniture"][0].__setitem__("material_ref", "M-99"))
_b1_ok, _b1f = validate_references(_iso)
_b3_ok, _b3f = validate_furniture(_iso)
RESULTS.append(("FI-02", "Missing material_ref owned by XR-003 only; B3 silent",
                "PASS" if ((not _b1_ok) and any(f.rule == "XR-003" for f in _b1f)
                           and _b3_ok) else "FAIL",
                f"B1={[f.rule for f in _b1f]} B3={[f.rule for f in _b3f]}"))

# FI-03: B3 must not re-report B2's wall defects.
_iso = mutate(lambda d: d["walls"].append(wall("W-05", (2000, 2500), (2000, 2500))))
_b2_ok, _b2f = validate_topology(_iso)
_b3_ok, _b3f = validate_furniture(_iso)
RESULTS.append(("FI-03", "Degenerate wall owned by WT-001 only; B3 silent",
                "PASS" if ((not _b2_ok) and any(f.rule == "WT-001" for f in _b2f)
                           and _b3_ok) else "FAIL",
                f"B2={[f.rule for f in _b2f]} B3={[f.rule for f in _b3f]}"))

# FI-04: scope discipline — B3 says nothing about circulation or door swing.
_iso = copy.deepcopy(BASE)
_iso["presence_register"]["openings"] = fact(True, ref="client survey", unit="none",
                                             presence="PRESENT")
_iso["openings"] = [{"id": "D-01", "kind": "door", "host_wall": "W-01",
                     "offset": fact(500, unit="mm"), "width": fact(900, unit="mm"),
                     "height": fact(2100, unit="mm"),
                     "swing": fact("in-left")}]
# A piece sitting right in front of the door: a B5 concern, NOT a B3 one.
_iso["furniture"].append(piece("F-04", "Stool", 950, 700, 400, 400))
_iso["materials"][0]["applied_to"].append("F-04")
_ok, _f = validate_furniture(_iso)
RESULTS.append(("FI-04", "Scope: B3 ignores door-swing obstruction (owned by B5)",
                "PASS" if _ok else "FAIL",
                f"leaked: {[x.rule for x in _f if x.severity=='ERROR']}"))

# FI-05: mutation sweep.
sweep = [
    ("overlap", lambda d: d["furniture"][1].__setitem__("position", fact([1800, 1500], unit="mm"))),
    ("in-wall", lambda d: d["furniture"][0].__setitem__("position", fact([1500, 20], unit="mm"))),
    ("duplicate", _duplicate),
    ("zero-dims", lambda d: d["furniture"][0].__setitem__("dims", fact([0, 800, 750], unit="mm"))),
    ("unknown-dims", _unresolved_dims),
    ("column-clash", _column_clash),
]
missed = [n for n, fn in sweep if validate_furniture(mutate(fn))[0]]
RESULTS.append(("FI-05", "Mutation sweep: every furniture defect detected",
                "PASS" if not missed else "FAIL",
                f"missed: {missed}" if missed else f"{len(sweep)}/{len(sweep)} caught"))

# FI-06: no false positives, repeated runs.
stable = all(validate_furniture(copy.deepcopy(BASE))[0] for _ in range(3))
RESULTS.append(("FI-06", "No false positives on the valid base (3 runs)",
                "PASS" if stable else "FAIL", ""))

# FI-07: empty furniture list is legitimate, not an error.
_empty = copy.deepcopy(BASE)
_empty["furniture"] = []
_empty["materials"][0]["applied_to"] = ["W-01"]
_ok, _ = validate_furniture(_empty)
RESULTS.append(("FI-07", "A room with no furniture is not an error",
                "PASS" if _ok else "FAIL", ""))



# ===========================================================================
# R02 — POSITION REFERENCE & ROTATION SEMANTICS
# GAP-B3-01 / GAP-B3-02 closed by DECLARED DATA. Mandated tests.
# ===========================================================================
from validate_furniture import footprint as _fp   # noqa: E402


def _two(datum_a="CENTER", rot_a=0, datum_b="CENTER", rot_b=0,
         a=(1500, 1500, 2000, 400), b=(1500, 1500, 400, 2000)):
    d = copy.deepcopy(BASE)
    d["furniture"] = [
        piece("F-01", "Sofa", a[0], a[1], a[2], a[3], datum=datum_a, rot=rot_a),
        piece("F-02", "Shelf", b[0], b[1], b[2], b[3], datum=datum_b, rot=rot_b),
    ]
    d["materials"][0]["applied_to"] = ["F-01", "F-02"]
    return d


# --- POSITION -------------------------------------------------------------
# PR-01: CENTER works.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, datum="CENTER")]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("PR-01", "Datum CENTER is accepted and resolvable",
                "PASS" if _ok else "FAIL", f"{[x.rule for x in _f]}"))

# PR-02: CORNER_MIN works.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, datum="CORNER_MIN")]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("PR-02", "Datum CORNER_MIN is accepted and resolvable",
                "PASS" if _ok else "FAIL", f"{[x.rule for x in _f]}"))

# PR-03: SAME coordinates, different datum -> genuinely different geometry.
_c = _fp(1500, 1500, 1200, 800, "CENTER", 0)
_m = _fp(1500, 1500, 1200, 800, "CORNER_MIN", 0)
_x = _fp(1500, 1500, 1200, 800, "CORNER_MAX", 0)
RESULTS.append(("PR-03", "Same coordinates yield different geometry per datum",
                "PASS" if (_c != _m and _m != _x and _c != _x) else "FAIL",
                f"C{_c[0]} MIN{_m[0]} MAX{_x[0]}"))

# PR-04: datum difference CHANGES A VERDICT (proves the engine consumes it).
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "A", 1500, 1500, 1200, 800, datum="CENTER"),
                   piece("F-02", "B", 2400, 1500, 1200, 800, datum="CENTER")]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok_center, _ = validate_furniture(_d)
_d2 = copy.deepcopy(_d)
_d2["furniture"][1]["position_reference"] = fact(
    "CORNER_MIN", ref="client survey: datum declared")
_ok_corner, _ = validate_furniture(_d2)
RESULTS.append(("PR-04", "Datum actually changes the overlap verdict (not cosmetic)",
                "PASS" if (_ok_center != _ok_corner) else "FAIL",
                f"CENTER_ok={_ok_center} CORNER_ok={_ok_corner}"))

# PR-05: absent position_reference must NOT become CENTER.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, datum=_OMIT)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok_s, _ = validate_master(_d, SCHEMA)
_ok, _f = validate_furniture(_d)
_fc009 = [x for x in _f if x.rule == "FC-009"]
RESULTS.append(("PR-05", "Absent datum stays UNKNOWN and blocks judgement",
                "PASS" if (_ok_s and not _ok and _fc009) else "FAIL",
                f"schema={_ok_s} codes={[x.rule for x in _f]}"))

# PR-06: invalid datum value rejected by the schema.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, datum="MIDDLE")]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok_s, _e = validate_master(_d, SCHEMA)
RESULTS.append(("PR-06", "Invalid datum value is rejected by the schema",
                "PASS" if not _ok_s else "FAIL", _e[0][:44] if _e else "accepted!"))

# PR-07: UNKNOWN-status datum blocks judgement.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, datum=_OMIT)]
_d["furniture"][0]["position_reference"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "datum not recorded", "recorded_on": TODAY,
    "blocking": False, "unknown_id": "U-060"}
_d["registers"]["unknowns"].append(
    {"id": "U-060", "question": "Datum for F-01 position?", "blocking": False,
     "raised_on": TODAY})
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("PR-07", "UNKNOWN datum blocks geometric judgement",
                "PASS" if (not _ok and any(x.rule == "FC-009" for x in _f)) else "FAIL",
                f"{[x.rule for x in _f]}"))

# --- ROTATION -------------------------------------------------------------
# RO-01: explicit 0 works.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, rot=0)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("RO-01", "Explicit rotation 0 is accepted and resolvable",
                "PASS" if _ok else "FAIL", f"{[x.rule for x in _f]}"))

# RO-02: 90 degrees genuinely changes the footprint.
_r0 = _fp(1500, 1500, 2000, 400, "CENTER", 0)
_r90 = _fp(1500, 1500, 2000, 400, "CENTER", 90)
_x0 = sorted({round(p[0]) for p in _r0})
_x90 = sorted({round(p[0]) for p in _r90})
RESULTS.append(("RO-02", "Rotation 90 deg genuinely transforms the footprint",
                "PASS" if (_x0 == [500, 2500] and _x90 == [1300, 1700]) else "FAIL",
                f"x0={_x0} x90={_x90}"))

# RO-03: rotation CHANGES AN OVERLAP VERDICT (proves real consumption).
_d_par = _two(rot_a=0, rot_b=0, a=(1500, 1500, 2000, 400), b=(1500, 2200, 2000, 400))
_ok_par, _ = validate_furniture(_d_par)
_d_rot = _two(rot_a=90, rot_b=0, a=(1500, 1500, 2000, 400), b=(1500, 2200, 2000, 400))
_ok_rot, _ = validate_furniture(_d_rot)
RESULTS.append(("RO-03", "Rotation actually changes the overlap verdict",
                "PASS" if (_ok_par and not _ok_rot) else "FAIL",
                f"unrotated_ok={_ok_par} rotated_ok={_ok_rot}"))

# RO-04: absent rotation must NOT become 0.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, rot=_OMIT)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok_s, _ = validate_master(_d, SCHEMA)
_ok, _f = validate_furniture(_d)
# The piece is alone in open floor, so the angle is IMMATERIAL: it is recorded
# as an open item, never silently resolved to 0. Proof it is not read as 0:
# an identical piece declaring 0 explicitly produces NO FC-010 at all.
_f10 = [x for x in _f if x.rule == "FC-010"]
_d0 = copy.deepcopy(BASE)
_d0["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, rot=0)]
_d0["materials"][0]["applied_to"] = ["F-01"]
_, _f0 = validate_furniture(_d0)
RESULTS.append(("RO-04", "Absent rotation is UNKNOWN, never silently read as 0",
                "PASS" if (_ok_s and _f10
                           and not any(x.rule == "FC-010" for x in _f0)) else "FAIL",
                f"absent={[x.rule for x in _f10]} explicit_zero={[x.rule for x in _f0]}"))

# RO-05: invalid rotation values rejected by the schema.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "T", 1500, 1500, 1200, 800, rot="ninety")]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok_a, _ea = validate_master(_d, SCHEMA)
_d2 = copy.deepcopy(BASE)
_d2["furniture"] = [piece("F-01", "T", 1500, 1500, 1200, 800, rot=999)]
_d2["materials"][0]["applied_to"] = ["F-01"]
_ok_b, _eb = validate_master(_d2, SCHEMA)
RESULTS.append(("RO-05", "Invalid rotation (string / out of range) is rejected",
                "PASS" if (not _ok_a and not _ok_b) else "FAIL",
                f"string_ok={_ok_a} range_ok={_ok_b}"))

# RO-06: UNKNOWN rotation blocks a judgement that depends on it.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Sofa", 1500, 1500, 2000, 400, rot=_OMIT),
                   piece("F-02", "Shelf", 1500, 1800, 2000, 400)]
_d["furniture"][0]["rotation"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "orientation not decided", "recorded_on": TODAY,
    "blocking": False, "unknown_id": "U-061"}
_d["registers"]["unknowns"].append(
    {"id": "U-061", "question": "Orientation of F-01?", "blocking": False,
     "raised_on": TODAY})
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("RO-06", "UNKNOWN rotation blocks the dependent geometric judgement",
                "PASS" if (not _ok and any(x.rule == "FC-010" for x in _f)) else "FAIL",
                f"{[x.rule for x in _f]}"))

# RO-07: a PROPOSED rotation is not usable for geometry.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Table", 1500, 1500, 1200, 800, rot=_OMIT)]
_d["furniture"][0]["rotation"] = {
    "value": 45, "unit": "deg", "status": "P", "source_type": "AGENT_PROPOSAL",
    "source_ref": "suggested angle", "recorded_on": TODAY, "proposal_id": "P-010"}
_d["registers"]["proposals"] = [{"id": "P-010", "text": "Angle the table 45 deg",
                                 "state": "OPEN", "raised_on": TODAY}]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
RESULTS.append(("RO-07", "PROPOSED rotation is not used for geometry",
                "PASS" if any(x.rule == "FC-010" for x in _f) else "FAIL",
                f"{[x.rule for x in _f]} (proposed 45 deg never consumed)"))

# --- PROOF OF REAL CONSUMPTION (user condition 5) -------------------------
# A rotated piece must be tested against its TRUE footprint, not an AABB.
# Sofa 2000x400 at 45 deg: an axis-aligned box would span ~1697mm; the true
# rotated rectangle does not reach the probe piece placed in the AABB corner.
_d = copy.deepcopy(BASE)
# The rotated sofa spans AABB x 2151..3849, y 1151..2849, but its body is a
# diagonal band. The AABB's top-LEFT corner (2350, 2700) is inside the box and
# outside the true rectangle — exactly where an AABB check would false-positive.
_d["furniture"] = [piece("F-01", "Sofa", 3000, 2000, 2000, 400, rot=45),
                   piece("F-02", "Probe", 2350, 2700, 200, 200, rot=0)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok_true, _ = validate_furniture(_d)
_poly = _fp(3000, 2000, 2000, 400, "CENTER", 45)
_aabb_x = (min(p[0] for p in _poly), max(p[0] for p in _poly))
_aabb_y = (min(p[1] for p in _poly), max(p[1] for p in _poly))
_probe_in_aabb = (_aabb_x[0] <= 2350 <= _aabb_x[1]
                  and _aabb_y[0] <= 2700 <= _aabb_y[1])
RESULTS.append((
    "RO-08", "Rotated piece uses true polygon, not a bounding box",
    "PASS" if (_ok_true and _probe_in_aabb) else "FAIL",
    f"clear={_ok_true} probe_inside_AABB={_probe_in_aabb}"))

# The same probe placed on the ACTUAL rotated body must be caught.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Sofa", 3000, 2000, 2000, 400, rot=45),
                   piece("F-02", "Probe", 3400, 2400, 200, 200, rot=0)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok_hit, _fh = validate_furniture(_d)
RESULTS.append((
    "RO-09", "A piece on the true rotated body IS caught",
    "PASS" if ((not _ok_hit) and any(x.rule == "FC-003" for x in _fh)) else "FAIL",
    f"{[x.rule for x in _fh]}"))

# Clearance must also honour rotation.
_d = copy.deepcopy(BASE)
_d["furniture"] = [
    piece("F-01", "Sofa", 1500, 1500, 2000, 400, rot=90,
          clearance=fact(600, unit="mm", ref="client brief: 600mm access")),
    piece("F-02", "Stool", 1500, 2900, 400, 400, rot=0),
]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok_cl, _fcl = validate_furniture(_d)
RESULTS.append((
    "RO-10", "Clearance is measured against the rotated footprint",
    "PASS" if ((not _ok_cl) and any(x.rule == "FC-007" for x in _fcl)) else "FAIL",
    f"{[x.rule for x in _fcl]}"))

# FC-006 must not call two differently-rotated pieces duplicates.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Sofa", 1500, 1500, 2000, 400, rot=0),
                   piece("F-02", "Sofa", 1500, 1500, 2000, 400, rot=90)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok_dup, _fd = validate_furniture(_d)
_no_dup = not any(x.rule == "FC-006" for x in _fd)
RESULTS.append((
    "RO-11", "Same footprint at different rotations is not a duplicate",
    "PASS" if _no_dup else "FAIL", f"{[x.rule for x in _fd]}"))

# RO-12: UNKNOWN rotation is IMMATERIAL in open floor -> INFO, not a block.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Stool", 3000, 2000, 400, 400, rot=_OMIT)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
_sev = [x.severity for x in _f if x.rule == "FC-010"]
RESULTS.append(("RO-12", "UNKNOWN rotation does NOT block when it is immaterial",
                "PASS" if (_ok and _sev == ["INFO"]) else "FAIL",
                f"ok={_ok} severity={_sev}"))

# RO-13: same piece, a neighbour inside the worst-case envelope -> blocks.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Stool", 3000, 2000, 400, 400, rot=_OMIT),
                   piece("F-02", "Chair", 3250, 2000, 400, 400)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok, _f = validate_furniture(_d)
_blk = [x for x in _f if x.rule == "FC-010" and x.severity == "ERROR"]
RESULTS.append(("RO-13", "UNKNOWN rotation blocks only on a PROVEN conflict",
                "PASS" if (not _ok and len(_blk) == 1
                           and "PROVEN CONFLICT" in _blk[0].message) else "FAIL",
                f"ok={_ok} blocking={len(_blk)}"))

# --- PROVEN vs POSSIBLE vs NONE (user correction, R03) --------------------
from validate_furniture import guaranteed_rotation_disc as _gdisc  # noqa: E402
from validate_furniture import unknown_rotation_envelope as _env   # noqa: E402
from validate_furniture import _dist_to_poly as _dist_poly         # noqa: E402

# Stool 400x400 about a CENTER pivot: it occupies a disc of r=200 at EVERY
# angle, and can never reach beyond r=283. The band between the two is the
# zone of genuine uncertainty that must NOT be asserted as a collision.
_R_IN = _gdisc(3000, 2000, 400, 400, "CENTER")
_R_OUT = _env(3000, 2000, 400, 400, "CENTER")

# RO-14: obstacle inside the always-occupied disc -> conflict PROVEN -> ERROR.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Stool", 3000, 2000, 400, 400, rot=_OMIT),
                   piece("F-02", "Chair", 3050, 2000, 400, 400)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok, _f = validate_furniture(_d)
_r = [x for x in _f if x.rule == "FC-010"]
RESULTS.append(("RO-14", "Conflict at EVERY orientation is PROVEN -> ERROR",
                "PASS" if (not _ok and len(_r) == 1 and _r[0].severity == "ERROR"
                           and "PROVEN CONFLICT" in _r[0].message) else "FAIL",
                f"ok={_ok} sev={[x.severity for x in _r]}"))

# RO-15: obstacle in the uncertainty band -> POSSIBLE only -> never ERROR.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Stool", 3000, 2000, 400, 400, rot=_OMIT),
                   piece("F-02", "Chair", 3440, 2000, 400, 400)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok, _f = validate_furniture(_d)
_r = [x for x in _f if x.rule == "FC-010"]
_gap = _dist_poly(_fp(3440, 2000, 400, 400, "CENTER", 0.0), 3000, 2000)
RESULTS.append(("RO-15", "Conflict at SOME orientations only is NOT an ERROR",
                "PASS" if (_ok and len(_r) == 1 and _r[0].severity == "INFO"
                           and "POSSIBLE BUT UNPROVEN" in _r[0].message
                           and _R_IN < _gap < _R_OUT) else "FAIL",
                f"ok={_ok} sev={[x.severity for x in _r]} gap={_gap:.0f} "
                f"in={_R_IN:.0f} out={_R_OUT:.0f}"))

# RO-16: nothing reachable at any angle -> no blocking at all.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Stool", 3000, 2000, 400, 400, rot=_OMIT)]
_d["materials"][0]["applied_to"] = ["F-01"]
_ok, _f = validate_furniture(_d)
_r = [x for x in _f if x.rule == "FC-010"]
RESULTS.append(("RO-16", "No orientation can clash -> no blocking",
                "PASS" if (_ok and len(_r) == 1 and _r[0].severity == "INFO"
                           and "NO POSSIBLE CONFLICT" in _r[0].message) else "FAIL",
                f"ok={_ok} sev={[x.severity for x in _r]}"))

# RO-17: inside the screening circle is NOT equivalent to proven collision.
# Same fixture as RO-15: the obstacle IS inside the envelope, yet the verdict
# must not be a proven conflict. This is the exact misreading being corrected.
_d = copy.deepcopy(BASE)
_d["furniture"] = [piece("F-01", "Stool", 3000, 2000, 400, 400, rot=_OMIT),
                   piece("F-02", "Chair", 3440, 2000, 400, 400)]
_d["materials"][0]["applied_to"] = ["F-01", "F-02"]
_ok, _f = validate_furniture(_d)
_r = [x for x in _f if x.rule == "FC-010"]
_inside_circle = _gap < _R_OUT
RESULTS.append(("RO-17", "Inside the screening circle is NOT 'collision proven'",
                "PASS" if (_inside_circle and _ok
                           and not any("PROVEN CONFLICT" in x.message
                                       for x in _r)) else "FAIL",
                f"inside_circle={_inside_circle} ok={_ok} "
                f"proven_claimed={any('PROVEN CONFLICT' in x.message for x in _r)}"))

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B3 — FURNITURE GEOMETRY & CLEARANCE INTEGRITY TEST REPORT")
print("=" * 94)
w = max(len(t[1]) for t in RESULTS)
for tid, title, status, detail in RESULTS:
    mark = "OK  " if status == "PASS" else "FAIL"
    print(f"{mark} {tid:8} {title:<{w}}  {detail[:44]}")
total = len(RESULTS)
passed = sum(1 for r in RESULTS if r[2] == "PASS")
print("-" * 94)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 94)
sys.exit(0 if passed == total else 1)
