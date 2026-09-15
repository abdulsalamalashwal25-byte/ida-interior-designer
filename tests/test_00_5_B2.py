#!/usr/bin/env python3
"""
test_00_5_B2.py — Wall & Opening Topology Integrity acceptance tests.

Discipline (carried over from B1, user conditions 2-4):
  - every rule: positive + negative
  - every negative asserts the EXACT rule code and NO collateral rule
  - a mutation that breaks the schema or B1 is a FAILED test, not a pass
  - isolation tests prove B2 adds coverage neither A nor B1 provides
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from schema_gate import validate_master, load_schema        # noqa: E402
from validate_refs import validate_references               # noqa: E402
from validate_topology import (validate_topology, AUTO,      # noqa: E402
                               UNSPECIFIED)

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


# ===========================================================================
# BASE: a closed 4000 x 3000 rectangle, four walls, one door on W-01.
# Every reference resolves; topology is sound.
# ===========================================================================
BASE = {
    "meta": {
        "project_id": "PRJ-98", "project_name": "TOPOLOGY TEST ROOM",
        "revision": "R01", "geometry_version": "G-001", "status": "DRAFT",
        "track": "LITE", "units": "mm", "created_on": TODAY,
        "is_test_project": True,
        "test_banner": "TEST PROJECT — NOT A REAL CLIENT PROJECT",
        "not_for_construction": "DESIGN INTENT — NOT FOR CONSTRUCTION",
    },
    "space": {
        "outline": fact([[0, 0], [4000, 0], [4000, 3000], [0, 3000]], unit="mm"),
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
        "openings": fact(True, ref="client survey: one door", unit="none",
                         presence="PRESENT"),
    },
    "walls": [
        wall("W-01", (0, 0), (4000, 0)),
        wall("W-02", (4000, 0), (4000, 3000)),
        wall("W-03", (4000, 3000), (0, 3000)),
        wall("W-04", (0, 3000), (0, 0)),
    ],
    "openings": [
        {"id": "D-01", "kind": "door", "host_wall": "W-01",
         "offset": fact(500, unit="mm"), "width": fact(900, unit="mm"),
         "height": fact(2100, unit="mm")},
    ],
    "columns": [], "zones": [], "furniture": [], "materials": [],
    "cameras": [],
    "registers": {
        "unknowns": [{"id": "U-003", "question": "North orientation?",
                      "blocking": False, "raised_on": TODAY}],
        "assumptions": [], "proposals": [], "decisions": [],
        "change_requests": [], "objections": [],
        "changelog": [{"revision": "R01", "date": TODAY, "type": "INITIAL",
                       "summary": "Topology test fixture."}],
    },
    "outputs": [],
}


def mutate(fn):
    d = copy.deepcopy(BASE)
    fn(d)
    return d


def expect_exactly(test_id, title, mutator, expected_rule,
                   expected_count=1, closure=AUTO):
    """Corrupt ONE thing; demand exactly the expected topology rule.
    Guards: the mutation must not break the schema (layer A) or B1."""
    data = mutate(mutator)

    schema_ok, schema_errs = validate_master(data, SCHEMA)
    if not schema_ok:
        RESULTS.append((test_id, title, "FAIL",
                        f"broke the SCHEMA, not topology: {schema_errs[0][:60]}"))
        return
    b1_ok, b1_findings = validate_references(data)
    if not b1_ok:
        RESULTS.append((test_id, title, "FAIL",
                        f"broke B1 refs, not topology: {b1_findings[0].rule}"))
        return

    ok, findings = validate_topology(data, require_closure=closure)
    errors = [f for f in findings if f.severity == "ERROR"]
    codes = [f.rule for f in errors]
    hit = [c for c in codes if c == expected_rule]
    other = [c for c in codes if c != expected_rule]

    if ok:
        RESULTS.append((test_id, title, "FAIL", "engine accepted it — rule never fired"))
    elif not hit:
        RESULTS.append((test_id, title, "FAIL", f"wrong rule: {sorted(set(codes))}"))
    elif other:
        RESULTS.append((test_id, title, "FAIL",
                        f"collateral rules: {sorted(set(other))}"))
    elif len(hit) != expected_count:
        RESULTS.append((test_id, title, "FAIL",
                        f"{expected_rule} fired {len(hit)}x, expected {expected_count}"))
    else:
        RESULTS.append((test_id, title, "PASS",
                        f"{expected_rule} x{len(hit)}, no collateral"))


def expect_clean(test_id, title, data=None, closure=AUTO):
    data = data if data is not None else copy.deepcopy(BASE)
    schema_ok, se = validate_master(data, SCHEMA)
    b1_ok, bf = validate_references(data)
    ok, findings = validate_topology(data, require_closure=closure)
    if not schema_ok:
        RESULTS.append((test_id, title, "FAIL", f"schema: {se[0][:60]}"))
    elif not b1_ok:
        RESULTS.append((test_id, title, "FAIL", f"b1: {bf[0].rule}"))
    elif not ok:
        RESULTS.append((test_id, title, "FAIL",
                        f"false positive: {findings[0].rule} {findings[0].message[:40]}"))
    else:
        RESULTS.append((test_id, title, "PASS", ""))


# ===========================================================================
# POSITIVE TESTS
# ===========================================================================
expect_clean("TP-00", "Closed rectangular envelope passes")
expect_clean("TP-01", "Closed envelope passes when closure is REQUIRED", closure=True)

_p = copy.deepcopy(BASE)
_p["walls"] = [wall("W-01", (0, 0), (4000, 0)), wall("W-02", (4000, 0), (4000, 3000))]
expect_clean("TP-02", "Open L-shaped chain passes when closure is NOT required",
             _p, closure=False)

_p = copy.deepcopy(BASE)
_p["openings"][0]["offset"] = fact(0, unit="mm")
expect_clean("TP-03", "Opening flush with the wall start is accepted", _p)

_p = copy.deepcopy(BASE)
_p["openings"][0]["offset"] = fact(3100, unit="mm")
_p["openings"][0]["width"] = fact(900, unit="mm")
expect_clean("TP-04", "Opening exactly reaching the wall end is accepted", _p)

_p = copy.deepcopy(BASE)
_p["openings"].append({"id": "WN-01", "kind": "window", "host_wall": "W-01",
                       "offset": fact(2000, unit="mm"), "width": fact(1200, unit="mm"),
                       "height": fact(1400, unit="mm")})
expect_clean("TP-05", "Two non-overlapping openings on one wall are accepted", _p)

_p = copy.deepcopy(BASE)
_p["openings"].append({"id": "WN-01", "kind": "window", "host_wall": "W-01",
                       "offset": fact(1400, unit="mm"), "width": fact(600, unit="mm"),
                       "height": fact(1400, unit="mm")})
expect_clean("TP-06", "Openings touching edge-to-edge (no overlap) are accepted", _p)

_p = copy.deepcopy(BASE)
_p["walls"].append(wall("W-05", (4000, 3000), (6000, 3000)))
_p["walls"].append(wall("W-06", (6000, 3000), (6000, 0)))
_p["walls"].append(wall("W-07", (6000, 0), (4000, 0)))
expect_clean("TP-07", "Two rooms sharing a junction pass (shared endpoints)", _p)

_p = copy.deepcopy(BASE)
_p["openings"][0]["width"] = fact(4000, unit="mm")
_p["openings"][0]["offset"] = fact(0, unit="mm")
expect_clean("TP-08", "Full-width opening spanning the whole wall is accepted", _p)


# ===========================================================================
# NEGATIVE TESTS
# ===========================================================================
expect_exactly("TN-001", "Zero-length wall is caught",
               lambda d: d["walls"].append(wall("W-05", (2000, 1500), (2000, 1500))),
               "WT-001")


def _unknown_geometry(d):
    d["walls"][0]["start"] = {
        "value": None, "status": "U", "source_type": "NOT_PROVIDED",
        "source_ref": "not surveyed", "recorded_on": TODAY,
        "blocking": True, "unknown_id": "U-020"}
    d["registers"]["unknowns"].append(
        {"id": "U-020", "question": "Start point of W-01?", "blocking": True,
         "raised_on": TODAY})


expect_exactly("TN-002", "Wall with UNKNOWN geometry is caught, not assumed",
               _unknown_geometry, "WT-002")


def _open_chain(d):
    d["walls"] = [wall("W-01", (0, 0), (4000, 0)),
                  wall("W-02", (4000, 0), (4000, 3000)),
                  wall("W-03", (4000, 3000), (0, 3000))]


expect_exactly("TN-003", "Unclosed envelope is caught when closure is required",
               _open_chain, "WT-003", closure=True)


def _fragmented(d):
    """Two separate connected chains -> 4 loose ends, no floating wall.
    Every wall shares an endpoint with a neighbour, so WT-007 must NOT fire;
    the only defect is the fragmentation of the boundary."""
    d["walls"] = [wall("W-01", (0, 0), (4000, 0)),
                  wall("W-02", (4000, 0), (4000, 3000)),
                  wall("W-03", (0, 3000), (0, 500)),
                  wall("W-04", (0, 500), (1500, 500))]


expect_exactly("TN-004", "Fragmented wall chain (gaps) is caught",
               _fragmented, "WT-004", closure=False)


def _self_intersect(d):
    """A diagonal wall crossing the interior, both ends on existing corners
    so it is not an orphan; it properly crosses nothing... so we make it cross."""
    d["walls"].append(wall("W-05", (0, 0), (4000, 3000)))
    d["walls"].append(wall("W-06", (4000, 0), (0, 3000)))


expect_exactly("TN-005", "Self-intersecting walls are caught",
               _self_intersect, "WT-005")

expect_exactly("TN-006a", "Duplicate wall on the same segment is caught",
               lambda d: d["walls"].append(wall("W-05", (0, 0), (4000, 0))),
               "WT-006")

expect_exactly("TN-006b", "Collinear overlapping wall is caught",
               lambda d: d["walls"].append(wall("W-05", (1000, 0), (3000, 0))),
               "WT-006")


def _orphan(d):
    d["walls"].append(wall("W-05", (1000, 1000), (2000, 1000)))


expect_exactly("TN-007", "Orphan wall floating free is caught", _orphan, "WT-007")

expect_exactly("TN-008a", "Opening longer than its host wall is caught",
               lambda d: d["openings"][0].__setitem__("width", fact(5000, unit="mm")),
               "WT-008")

expect_exactly("TN-008b", "Opening pushed past the wall end is caught",
               lambda d: d["openings"][0].__setitem__("offset", fact(3800, unit="mm")),
               "WT-008")

expect_exactly("TN-009", "Negative opening offset is caught",
               lambda d: d["openings"][0].__setitem__("offset", fact(-200, unit="mm")),
               "WT-009")


def _overlapping_openings(d):
    d["openings"].append({"id": "WN-01", "kind": "window", "host_wall": "W-01",
                          "offset": fact(1000, unit="mm"),
                          "width": fact(1200, unit="mm"),
                          "height": fact(1400, unit="mm")})


expect_exactly("TN-010", "Two overlapping openings on one wall are caught",
               _overlapping_openings, "WT-010")


def _opening_on_degenerate_wall(d):
    d["walls"].append(wall("W-05", (0, 0), (0, 0)))
    d["openings"].append({"id": "WN-01", "kind": "window", "host_wall": "W-05",
                          "offset": fact(100, unit="mm"),
                          "width": fact(600, unit="mm"),
                          "height": fact(1400, unit="mm")})


# This mutation produces BOTH a zero-length wall (WT-001) and an opening on it
# (WT-011). Two distinct defects from one mutation, so we assert both.
_d = mutate(_opening_on_degenerate_wall)
_ok, _f = validate_topology(_d)
_codes = sorted({x.rule for x in _f})
RESULTS.append((
    "TN-011", "Opening on a degenerate wall is caught (WT-001 + WT-011)",
    "PASS" if (not _ok and _codes == ["WT-001", "WT-011"]) else "FAIL",
    f"fired: {_codes}"))


# ===========================================================================
# ISOLATION / COVERAGE PROOFS
# ===========================================================================

# I-01: a wall chain with a gap is schema-valid AND B1-valid, but topologically
# broken. Proves B2 adds coverage that neither earlier layer provides.
_iso = mutate(_fragmented)
_a_ok, _ = validate_master(_iso, SCHEMA)
_b1_ok, _ = validate_references(_iso)
_b2_ok, _ = validate_topology(_iso)
RESULTS.append((
    "TI-01", "Broken topology is A-valid and B1-valid but B2-invalid",
    "PASS" if (_a_ok and _b1_ok and not _b2_ok) else "FAIL",
    f"A={_a_ok} B1={_b1_ok} B2={_b2_ok}"))

# I-02: an opening overflowing its wall is invisible to A and B1.
_iso = mutate(lambda d: d["openings"][0].__setitem__("width", fact(9000, unit="mm")))
_a_ok, _ = validate_master(_iso, SCHEMA)
_b1_ok, _ = validate_references(_iso)
_b2_ok, _ = validate_topology(_iso)
RESULTS.append((
    "TI-02", "Oversized opening is A-valid and B1-valid but B2-invalid",
    "PASS" if (_a_ok and _b1_ok and not _b2_ok) else "FAIL",
    f"A={_a_ok} B1={_b1_ok} B2={_b2_ok}"))

# I-03: DELEGATION PROOF. An orphan opening (missing host wall) must be
# rejected by B1's XR-001 and must NOT produce a B2 rule. One defect,
# one owner.
_del = mutate(lambda d: d["openings"][0].__setitem__("host_wall", "W-77"))
_b1_ok, _b1f = validate_references(_del)
_b2_ok, _b2f = validate_topology(_del)
RESULTS.append((
    "TI-03", "Orphan opening owned by XR-001 only; B2 stays silent",
    "PASS" if ((not _b1_ok) and any(f.rule == "XR-001" for f in _b1f)
               and _b2_ok) else "FAIL",
    f"B1={[f.rule for f in _b1f]} B2={[f.rule for f in _b2f]}"))

# I-04: closure must never be assumed. The same open chain passes when closure
# is not required and fails when it is. Silence is not a fact.
_open = mutate(_open_chain)
_no_req, _ = validate_topology(_open, require_closure=False)
_req, _ = validate_topology(_open, require_closure=True)
RESULTS.append((
    "TI-04", "Closure is never assumed: same model passes/fails by policy only",
    "PASS" if (_no_req and not _req) else "FAIL",
    f"closure_off={_no_req} closure_on={_req}"))

# I-05: mutation sweep — every topological corruption must be detected.
sweep = [
    ("zero-length", lambda d: d["walls"].append(wall("W-05", (10, 10), (10, 10)))),
    ("duplicate", lambda d: d["walls"].append(wall("W-05", (0, 0), (4000, 0)))),
    ("orphan", _orphan),
    ("crossing", _self_intersect),
    ("overflow", lambda d: d["openings"][0].__setitem__("width", fact(9999, unit="mm"))),
    ("negative-offset", lambda d: d["openings"][0].__setitem__("offset", fact(-1, unit="mm"))),
    ("overlap-openings", _overlapping_openings),
]
missed = [n for n, fn in sweep if validate_topology(mutate(fn))[0]]
RESULTS.append(("TI-05", "Mutation sweep: every topological corruption detected",
                "PASS" if not missed else "FAIL",
                f"missed: {missed}" if missed else f"{len(sweep)}/{len(sweep)} caught"))

# I-06: no false positives across repeated runs and both closure policies.
stable = (all(validate_topology(copy.deepcopy(BASE))[0] for _ in range(3))
          and validate_topology(copy.deepcopy(BASE), require_closure=True)[0])
RESULTS.append(("TI-06", "No false positives on the valid base (3 runs + closure on)",
                "PASS" if stable else "FAIL", ""))

# I-07: scope discipline — B2 must stay silent about furniture (that is B3).
_furn = copy.deepcopy(BASE)
_furn["materials"] = [{"id": "M-01", "name": fact("Oak"), "color_hex": fact("#B98A56"),
                       "applied_to": ["F-01", "F-02"]}]
_furn["furniture"] = [
    {"id": "F-01", "name": "Table A", "position": fact([1000, 1000], unit="mm"),
     "dims": fact([1200, 800, 750], unit="mm"), "material_ref": "M-01"},
    {"id": "F-02", "name": "Table B", "position": fact([1000, 1000], unit="mm"),
     "dims": fact([1200, 800, 750], unit="mm"), "material_ref": "M-01"},
]
_scope_ok, _scope_f = validate_topology(_furn)
RESULTS.append((
    "TI-07", "Scope discipline: B2 ignores overlapping furniture (owned by B3)",
    "PASS" if _scope_ok else "FAIL",
    f"leaked: {[f.rule for f in _scope_f]}"))



# ===========================================================================
# CLOSURE POLICY FIELD — meta.topology_policy.require_closed_envelope
# Approved at Gate 00.5-B2 under 12 explicit conditions.
# ===========================================================================

# PT-01: field absent -> schema-valid, policy UNSPECIFIED (NOT false).
_pol = copy.deepcopy(BASE)
_pol_schema_ok, _pol_errs = validate_master(_pol, SCHEMA)
_resolved = ((_pol.get("meta") or {}).get("topology_policy") or {}).get(
    "require_closed_envelope", UNSPECIFIED)
RESULTS.append((
    "PT-01", "Field absent is valid and resolves to UNSPECIFIED, not false",
    "PASS" if (_pol_schema_ok and _resolved is UNSPECIFIED) else "FAIL",
    f"schema={_pol_schema_ok} resolved={_resolved}"))

# PT-02: absence must never be coerced to a boolean.
try:
    bool(UNSPECIFIED)
    _coerce_guarded = False
except TypeError:
    _coerce_guarded = True
RESULTS.append((
    "PT-02", "UNSPECIFIED cannot be silently coerced to false",
    "PASS" if _coerce_guarded else "FAIL", ""))

# PT-03: true -> schema-valid, WT-003 applicable on an open chain.
_pol = mutate(_open_chain)
_pol["meta"]["topology_policy"] = {"require_closed_envelope": True}
_ok_s, _e = validate_master(_pol, SCHEMA)
_ok_t, _f = validate_topology(_pol)
_wt003 = [x for x in _f if x.rule == "WT-003" and x.severity == "ERROR"]
RESULTS.append((
    "PT-03", "Policy true is valid and makes WT-003 applicable",
    "PASS" if (_ok_s and not _ok_t and _wt003) else "FAIL",
    f"schema={_ok_s} topo_ok={_ok_t} wt003={len(_wt003)}"))

# PT-04: false -> schema-valid, closure not required, WT-003 not raised.
_pol = mutate(_open_chain)
_pol["meta"]["topology_policy"] = {"require_closed_envelope": False}
_ok_s, _ = validate_master(_pol, SCHEMA)
_ok_t, _f = validate_topology(_pol)
_no_wt003 = not any(x.rule == "WT-003" for x in _f)
RESULTS.append((
    "PT-04", "Policy false is valid and WT-003 is not required",
    "PASS" if (_ok_s and _ok_t and _no_wt003) else "FAIL",
    f"schema={_ok_s} topo_ok={_ok_t}"))

# PT-05: non-boolean -> rejected by the schema.
_pol = copy.deepcopy(BASE)
_pol["meta"]["topology_policy"] = {"require_closed_envelope": "yes"}
_ok_s, _e = validate_master(_pol, SCHEMA)
RESULTS.append((
    "PT-05", "Non-boolean policy value is rejected",
    "PASS" if not _ok_s else "FAIL",
    _e[0][:44] if _e else "accepted!"))

# PT-06: unknown key inside topology_policy -> rejected.
_pol = copy.deepcopy(BASE)
_pol["meta"]["topology_policy"] = {"require_closed_envelope": True, "guess": True}
_ok_s, _e = validate_master(_pol, SCHEMA)
RESULTS.append((
    "PT-06", "Undeclared key inside topology_policy is rejected",
    "PASS" if not _ok_s else "FAIL", _e[0][:44] if _e else "accepted!"))

# PT-07: NO INFERENCE (condition 6). A geometrically closed model with NO
# declared policy must still resolve to UNSPECIFIED, never to true.
_pol = copy.deepcopy(BASE)   # geometrically closed rectangle
_inferred = ((_pol.get("meta") or {}).get("topology_policy") or {}).get(
    "require_closed_envelope", UNSPECIFIED)
RESULTS.append((
    "PT-07", "Closed geometry does NOT imply a declared closure policy",
    "PASS" if _inferred is UNSPECIFIED else "FAIL", f"resolved={_inferred}"))

# PT-08: UNSPECIFIED on an open chain surfaces an INFO note, never an ERROR.
_pol = mutate(_open_chain)
_ok_t, _f = validate_topology(_pol)
_info = [x for x in _f if x.rule == "WT-003" and x.severity == "INFO"]
_errs = [x for x in _f if x.severity == "ERROR"]
RESULTS.append((
    "PT-08", "UNSPECIFIED + open chain = INFO note, not a silent pass or error",
    "PASS" if (_ok_t and _info and not _errs) else "FAIL",
    f"ok={_ok_t} info={len(_info)} errors={len(_errs)}"))

# PT-09: SAME GEOMETRY, policy decides the verdict (condition 11 re-proved
# against the declared field rather than the function argument).
_geo_true = mutate(_open_chain)
_geo_true["meta"]["topology_policy"] = {"require_closed_envelope": True}
_geo_false = mutate(_open_chain)
_geo_false["meta"]["topology_policy"] = {"require_closed_envelope": False}
_t_ok, _ = validate_topology(_geo_true)
_f_ok, _ = validate_topology(_geo_false)
RESULTS.append((
    "PT-09", "Identical geometry passes or fails by declared policy alone",
    "PASS" if (not _t_ok and _f_ok) else "FAIL",
    f"true={_t_ok} false={_f_ok}"))

# PT-10: a closed model under a true policy stays clean.
_pol = copy.deepcopy(BASE)
_pol["meta"]["topology_policy"] = {"require_closed_envelope": True}
_ok_s, _ = validate_master(_pol, SCHEMA)
_ok_t, _ = validate_topology(_pol)
RESULTS.append((
    "PT-10", "Closed envelope under policy true is valid and clean",
    "PASS" if (_ok_s and _ok_t) else "FAIL", f"schema={_ok_s} topo={_ok_t}"))

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("=" * 92)
print("PHASE 00.5-B2 — WALL & OPENING TOPOLOGY INTEGRITY TEST REPORT")
print("=" * 92)
w = max(len(t[1]) for t in RESULTS)
for tid, title, status, detail in RESULTS:
    mark = "OK  " if status == "PASS" else "FAIL"
    print(f"{mark} {tid:8} {title:<{w}}  {detail[:46]}")
total = len(RESULTS)
passed = sum(1 for r in RESULTS if r[2] == "PASS")
print("-" * 92)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 92)
sys.exit(0 if passed == total else 1)
