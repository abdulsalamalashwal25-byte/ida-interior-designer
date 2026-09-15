#!/usr/bin/env python3
"""
test_00_5_B1.py — Cross-Reference Integrity acceptance tests.

Discipline enforced here (user condition #3):
  1. Every rule has a POSITIVE test.
  2. Every rule has a NEGATIVE test.
  3. Every negative test asserts the EXACT rule code that fired, and asserts
     that NO OTHER rule fired. A test that passes because the fixture is
     broken in some unrelated way is treated as a FAILURE.
  4. The mutation harness starts from a fully valid base, corrupts exactly
     one reference, and demands exactly one expected failure.
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from schema_gate import validate_master, load_schema          # noqa: E402
from validate_refs import validate_references, build_index    # noqa: E402

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


# ===========================================================================
# A FULLY VALID, RICHLY CROSS-LINKED BASE.
# Every reference in here resolves. This is the control specimen.
# ===========================================================================
BASE = {
    "meta": {
        "project_id": "PRJ-99", "project_name": "XREF TEST ROOM",
        "revision": "R01", "geometry_version": "G-004", "status": "DRAFT",
        "track": "LITE", "units": "mm", "created_on": TODAY,
        "is_test_project": True,
        "test_banner": "TEST PROJECT — NOT A REAL CLIENT PROJECT",
        "not_for_construction": "DESIGN INTENT — NOT FOR CONSTRUCTION",
    },
    "space": {
        "outline": fact([[0, 0], [4000, 0], [4000, 3000], [0, 3000]], unit="mm"),
        "ceiling_height": fact(2800, unit="mm"),
        "orientation_north": {"value": None, "status": "U",
                              "source_type": "NOT_PROVIDED", "source_ref": "not supplied",
                              "recorded_on": TODAY, "blocking": False,
                              "unknown_id": "U-003"},
        "floor_level": fact(0, unit="mm"),
        "services": {"value": 12000000, "unit": "mm2", "status": "D",
                     "source_type": "DERIVED_CALC", "source_ref": "area calc",
                     "recorded_on": TODAY, "derived_from": ["space.outline"],
                     "derivation_type": "ARITHMETIC",
                     "formula": "4000 * 3000 = 12000000"},
    },
    "presence_register": {
        "columns": confirmed_absent("columns"),
        "beams": confirmed_absent("beams"),
        "protrusions": confirmed_absent("protrusions"),
        "level_changes": confirmed_absent("level changes"),
        "services": confirmed_absent("existing services"),
        "existing_furniture": confirmed_absent("existing furniture"),
        "openings": fact(True, ref="client survey: one door", unit="none",
                         presence="PRESENT"),
    },
    "walls": [
        {"id": "W-01", "start": fact([0, 0], unit="mm"), "end": fact([4000, 0], unit="mm"),
         "thickness": fact(200, unit="mm"), "structural": fact(True),
         "finish_ref": "M-01"},
        {"id": "W-02", "start": fact([4000, 0], unit="mm"),
         "end": fact([4000, 3000], unit="mm"),
         "thickness": fact(200, unit="mm"), "structural": fact(True)},
    ],
    "openings": [
        {"id": "D-01", "kind": "door", "host_wall": "W-01",
         "offset": fact(500, unit="mm"), "width": fact(900, unit="mm"),
         "height": fact(2100, unit="mm")},
    ],
    "columns": [],
    "zones": [
        {"id": "Z-01", "name": "Main zone", "function": fact("seating"),
         "boundary": fact([[0, 0], [4000, 0], [4000, 3000], [0, 3000]], unit="mm")},
    ],
    "furniture": [
        {"id": "F-01", "name": "Chair", "zone_ref": "Z-01",
         "position": fact([1000, 1000], unit="mm"),
         "dims": fact([450, 500, 850], unit="mm"), "material_ref": "M-02"},
    ],
    "materials": [
        {"id": "M-01", "name": fact("Wall paint"), "color_hex": fact("#EFEAE3"),
         "applied_to": ["W-01"]},
        {"id": "M-02", "name": fact("Oak veneer"), "color_hex": fact("#B98A56"),
         "applied_to": ["F-01"]},
    ],
    "cameras": [{"id": "CAM-01", "pos": [3000, 2000, 1550],
                 "target": [500, 500, 1100], "fov_deg": 45, "status": "C"}],
    "registers": {
        "unknowns": [{"id": "U-003", "question": "North orientation?",
                      "blocking": False, "raised_on": TODAY}],
        "assumptions": [],
        "proposals": [{"id": "P-001", "text": "Oak veneer for the chair",
                       "state": "APPROVED", "raised_on": TODAY,
                       "decision_id": "DEC-001"}],
        "decisions": [{"decision_id": "DEC-001", "title": "Chair material",
                       "linked_proposal": "P-001", "linked_elements": ["F-01"],
                       "rationale": "Durable and consistent with the joinery palette",
                       "alternatives_considered": ["Laminate (rejected: edge wear)"],
                       "approved_by": "USER", "approved_on": TODAY,
                       "approved_in_revision": "R01"}],
        "change_requests": [],
        "objections": [],
        "changelog": [{"revision": "R01", "date": TODAY, "type": "INITIAL",
                       "summary": "Cross-reference test fixture."}],
    },
    "outputs": [
        {"output_id": "OUT-001", "file": "PRJ99_R01_A_FloorPlan.pdf", "class": "A",
         "view_type": "FloorPlan", "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
         "binding_geometry": True, "binding_visual": True,
         "fingerprint": {"project_id": "PRJ-99", "master_revision": "R01",
                         "master_hash": "a3f9c2", "geometry_version": "G-004",
                         "element_set_hash": "7bd41f", "positions_hash": "c92e08",
                         "materials_hash": "4a1db7", "camera_id": None,
                         "camera_hash": None},
         "generated_on": TODAY},
        {"output_id": "OUT-002", "file": "PRJ99_R01_A_Persp01.png", "class": "A",
         "view_type": "Perspective", "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
         "binding_geometry": True, "binding_visual": True,
         "fingerprint": {"project_id": "PRJ-99", "master_revision": "R01",
                         "master_hash": "a3f9c2", "geometry_version": "G-004",
                         "element_set_hash": "7bd41f", "positions_hash": "c92e08",
                         "materials_hash": "4a1db7", "camera_id": "CAM-01",
                         "camera_hash": "e30f5a"},
         "generated_on": TODAY},
        {"output_id": "OUT-003", "file": "PRJ99_R01_B_Board01.pdf", "class": "B",
         "view_type": "Board",
         "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
         "binding_geometry": True, "binding_visual": False, "supersedes_A": False,
         "derived_from_output": "OUT-001",
         "fingerprint": {"project_id": "PRJ-99", "master_revision": "R01",
                         "master_hash": "a3f9c2", "geometry_version": "G-004",
                         "element_set_hash": "7bd41f", "positions_hash": "c92e08",
                         "materials_hash": "4a1db7", "camera_id": None,
                         "camera_hash": None},
         "generated_on": TODAY},
    ],
}


def mutate(fn):
    d = copy.deepcopy(BASE)
    fn(d)
    return d


# ---------------------------------------------------------------------------
# Isolation harness (user condition #3, final clause)
# ---------------------------------------------------------------------------
def expect_exactly(test_id, title, mutator, expected_rule, expected_count=1):
    """Corrupt ONE thing in a valid base; demand exactly the expected rule."""
    data = mutate(mutator)

    # Guard 1: the mutation must not break the schema. If it does, the XR test
    # would be meaningless — the schema would have caught it first.
    schema_ok, schema_errs = validate_master(data, SCHEMA)
    if not schema_ok:
        RESULTS.append((test_id, title, "FAIL",
                        f"fixture broke the SCHEMA, not just the reference: {schema_errs[0][:70]}"))
        return

    ok, findings = validate_references(data)
    codes = [f.rule for f in findings]
    hit = [c for c in codes if c == expected_rule]
    other = [c for c in codes if c != expected_rule]

    if ok:
        RESULTS.append((test_id, title, "FAIL", "engine accepted it — rule never fired"))
    elif not hit:
        RESULTS.append((test_id, title, "FAIL",
                        f"wrong rule fired: {sorted(set(codes))}"))
    elif other:
        RESULTS.append((test_id, title, "FAIL",
                        f"collateral rules also fired: {sorted(set(other))}"))
    elif len(hit) != expected_count:
        RESULTS.append((test_id, title, "FAIL",
                        f"{expected_rule} fired {len(hit)}x, expected {expected_count}"))
    else:
        RESULTS.append((test_id, title, "PASS",
                        f"{expected_rule} x{len(hit)}, no collateral"))


def expect_clean(test_id, title, data=None):
    data = data if data is not None else copy.deepcopy(BASE)
    schema_ok, schema_errs = validate_master(data, SCHEMA)
    ok, findings = validate_references(data)
    if not schema_ok:
        RESULTS.append((test_id, title, "FAIL", f"schema: {schema_errs[0][:70]}"))
    elif not ok:
        RESULTS.append((test_id, title, "FAIL",
                        f"false positive: {[str(f) for f in findings][:1]}"))
    else:
        RESULTS.append((test_id, title, "PASS", ""))


# ===========================================================================
# POSITIVE TESTS
# ===========================================================================
expect_clean("XP-00", "Fully cross-linked valid base passes cleanly")

expect_clean("XP-01", "Opening on an existing wall is accepted")
expect_clean("XP-02", "Furniture in an existing zone with an existing material passes")

_p = copy.deepcopy(BASE)
_p["walls"][1]["finish_ref"] = "M-01"
expect_clean("XP-03", "Two walls sharing one existing finish is accepted", _p)

_p = copy.deepcopy(BASE)
_p["materials"][0]["applied_to"] = ["W-01", "W-02"]
expect_clean("XP-04", "Material applied to several existing elements is accepted", _p)

_p = copy.deepcopy(BASE)
_p["outputs"].append({
    "output_id": "OUT-004", "file": "b2.pdf", "class": "B", "view_type": "Board",
    "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
    "binding_geometry": True, "binding_visual": False, "supersedes_A": False,
    "derived_from_output": "OUT-002",
    "fingerprint": copy.deepcopy(BASE["outputs"][1]["fingerprint"]),
    "generated_on": TODAY})
expect_clean("XP-05", "Class B descending from a Class A perspective is accepted", _p)

_p = copy.deepcopy(BASE)
_p["registers"]["change_requests"] = [{
    "id": "CR-001", "target_element": "F-01", "current_value": 1000,
    "proposed_value": 1200, "reason": "clearance to the door leaf",
    "impact": "furniture plan", "classification": "MINOR",
    "state": "PENDING_APPROVAL", "raised_on": TODAY}]
expect_clean("XP-06", "CR targeting an existing element is accepted", _p)

_p = copy.deepcopy(BASE)
_p["registers"]["change_requests"] = [{
    "id": "CR-002", "target_element": "F-01", "current_value": 1,
    "proposed_value": 2, "reason": "conflict discovered", "impact": "furniture plan and views",
    "classification": "MINOR", "state": "PENDING_APPROVAL", "raised_on": TODAY}]
_p["furniture"][0]["position"] = fact(
    [1000, 1000], unit="mm",
    conflict={"cr_id": "CR-002", "description": "overlaps the door swing arc"})
expect_clean("XP-07", "KNOWN CONFLICT citing a registered CR is accepted", _p)


# ===========================================================================
# NEGATIVE TESTS — one corruption each, exact rule demanded
# ===========================================================================

def _dup_id(d):
    d["walls"].append({"id": "W-01", "start": fact([0, 3000], unit="mm"),
                       "end": fact([0, 0], unit="mm"),
                       "thickness": fact(200, unit="mm"), "structural": fact(True)})


expect_exactly("XN-000", "Duplicate element id is caught", _dup_id, "XR-000")

expect_exactly("XN-001a", "Opening on a non-existent wall is caught",
               lambda d: d["openings"][0].__setitem__("host_wall", "W-99"), "XR-001")

def _wrong_type_applied(d):
    """TYPE CONFUSION. applied_to is an unpatterned string list, so a material
    can be pointed at a REGISTER RECORD instead of a physical element. The id
    resolves, so no dangling-reference rule fires; only a type check catches it.

    Note: type confusion is UNREACHABLE for prefix-constrained refs such as
    host_wall / zone_ref / material_ref, because the schema pattern already
    forbids a column from carrying a 'W-' id. Verified: attempting it is
    rejected by the schema before this engine ever runs."""
    d["materials"][0]["applied_to"] = ["DEC-001"]


expect_exactly("XN-019", "Material applied to a register record, not an element, is caught",
               _wrong_type_applied, "XR-019")

expect_exactly("XN-002", "Furniture in a non-existent zone is caught",
               lambda d: d["furniture"][0].__setitem__("zone_ref", "Z-77"), "XR-002")

expect_exactly("XN-003", "Furniture with a non-existent material is caught",
               lambda d: d["furniture"][0].__setitem__("material_ref", "M-99"), "XR-003")

expect_exactly("XN-004", "Wall finish pointing at a missing material is caught",
               lambda d: d["walls"][0].__setitem__("finish_ref", "M-88"), "XR-004")

expect_exactly("XN-005", "Material applied to a non-existent element is caught",
               lambda d: d["materials"][0].__setitem__("applied_to", ["W-42"]), "XR-005")

def _ghost_decision(d):
    d["materials"][1]["name"] = {
        "value": "Oak veneer", "status": "C", "source_type": "USER_APPROVAL",
        "source_ref": "approved at gate 05", "recorded_on": TODAY,
        "decision_id": "DEC-404", "approved_by": "USER",
        "approved_on": TODAY, "approved_in_revision": "R01"}


expect_exactly("XN-006", "Fact citing a non-existent Decision Record is caught",
               _ghost_decision, "XR-006")

expect_exactly("XN-007a", "Unregistered unknown_id is caught",
               lambda d: d["space"]["orientation_north"].__setitem__("unknown_id", "U-999"),
               "XR-007")


def _unreg_assumption(d):
    d["space"]["floor_level"] = {
        "value": 50, "unit": "mm", "status": "A",
        "source_type": "AGENT_ASSUMPTION", "source_ref": "assumed screed",
        "recorded_on": TODAY, "assumption_id": "A-77",
        "impact": "affects all vertical dimensions",
        "approval_state": "PENDING_APPROVAL"}


expect_exactly("XN-007b", "Unregistered assumption_id is caught",
               _unreg_assumption, "XR-007")

expect_exactly("XN-008a", "derived_from pointing nowhere is caught",
               lambda d: d["space"]["services"].__setitem__(
                   "derived_from", ["space.does_not_exist"]), "XR-008")

expect_exactly("XN-008b", "derived_from pointing at a non-fact node is caught",
               lambda d: d["space"]["services"].__setitem__(
                   "derived_from", ["meta.project_id"]), "XR-008")


def _conflict_no_cr(d):
    d["furniture"][0]["position"] = fact(
        [1000, 1000], unit="mm",
        conflict={"cr_id": "CR-909", "description": "overlaps the door swing arc"})


expect_exactly("XN-009", "KNOWN CONFLICT citing an unregistered CR is caught",
               _conflict_no_cr, "XR-009")

def _ghost_proposal_link(d):
    """A second decision whose linked_proposal does not exist. The first
    decision/proposal pair stays intact so only XR-010 can fire."""
    d["registers"]["decisions"].append({
        "decision_id": "DEC-002", "title": "Ceiling treatment",
        "linked_proposal": "P-404",
        "rationale": "Selected for acoustic absorption over the seating zone",
        "alternatives_considered": ["Exposed slab (rejected: reverberation)"],
        "approved_by": "USER", "approved_on": TODAY,
        "approved_in_revision": "R01"})


expect_exactly("XN-010a", "Decision linked to a non-existent proposal is caught",
               _ghost_proposal_link, "XR-010")

expect_exactly("XN-010b", "Decision affecting a non-existent element is caught",
               lambda d: d["registers"]["decisions"][0].__setitem__(
                   "linked_elements", ["F-99"]), "XR-010")

expect_exactly("XN-010c", "USER_OVERRIDE citing an unregistered objection is caught",
               lambda d: d["registers"]["decisions"][0].__setitem__(
                   "user_override_of", "OBJ-500"), "XR-010")


def _broken_bidi(d):
    d["registers"]["proposals"].append(
        {"id": "P-002", "text": "Alternative veneer", "state": "APPROVED",
         "raised_on": TODAY, "decision_id": "DEC-001"})


expect_exactly("XN-011", "Broken bidirectional proposal<->decision link is caught",
               _broken_bidi, "XR-011")

expect_exactly("XN-012", "Changelog citing a non-existent CR is caught",
               lambda d: d["registers"]["changelog"].append(
                   {"revision": "R01", "date": TODAY, "type": "CR_APPLIED",
                    "summary": "applied a change", "cr_id": "CR-303"}), "XR-012")


def _cr_ghost_target(d):
    d["registers"]["change_requests"] = [{
        "id": "CR-004", "target_element": "F-55", "current_value": 1,
        "proposed_value": 2, "reason": "relocate the unit",
        "impact": "furniture plan", "classification": "MAJOR",
        "state": "PENDING_APPROVAL", "raised_on": TODAY}]


expect_exactly("XN-013", "CR targeting a non-existent element is caught",
               _cr_ghost_target, "XR-013")

expect_exactly("XN-014a", "Output derived from a non-existent output is caught",
               lambda d: d["outputs"][2].__setitem__("derived_from_output", "OUT-909"),
               "XR-014")

expect_exactly("XN-014b", "Output deriving from itself is caught",
               lambda d: d["outputs"][2].__setitem__("derived_from_output", "OUT-003"),
               "XR-014")


def _b_from_b(d):
    d["outputs"].append({
        "output_id": "OUT-005", "file": "b_from_b.pdf", "class": "B",
        "view_type": "Board",
        "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
        "binding_geometry": True, "binding_visual": False, "supersedes_A": False,
        "derived_from_output": "OUT-003",
        "fingerprint": copy.deepcopy(BASE["outputs"][0]["fingerprint"]),
        "generated_on": TODAY})


expect_exactly("XN-015", "Class B descending from another Class B is caught",
               _b_from_b, "XR-015")

expect_exactly("XN-017a", "Fingerprint from a different project is caught",
               lambda d: d["outputs"][0]["fingerprint"].__setitem__(
                   "project_id", "PRJ-77"), "XR-017")

expect_exactly("XN-017b", "Fingerprint citing an unknown revision is caught",
               lambda d: d["outputs"][0]["fingerprint"].__setitem__(
                   "master_revision", "R09"), "XR-017")

expect_exactly("XN-017c", "Fingerprint from a stale geometry version is caught",
               lambda d: d["outputs"][0]["fingerprint"].__setitem__(
                   "geometry_version", "G-001"), "XR-017")

expect_exactly("XN-018", "Fingerprint citing an undefined camera is caught",
               lambda d: d["outputs"][1]["fingerprint"].__setitem__(
                   "camera_id", "CAM-09"), "XR-018")


# ===========================================================================
# ISOLATION PROOF — the schema alone cannot catch any of this
# ===========================================================================
_iso = mutate(lambda d: d["furniture"][0].__setitem__("material_ref", "M-99"))
schema_ok, _ = validate_master(_iso, SCHEMA)
xr_ok, _ = validate_references(_iso)
RESULTS.append((
    "XI-01",
    "Dangling ref is SCHEMA-VALID but XR-INVALID (proves B1 adds real coverage)",
    "PASS" if (schema_ok and not xr_ok) else "FAIL",
    f"schema_ok={schema_ok}, xr_ok={xr_ok}"))

# Mutation sweep: every single-reference corruption must yield >= 1 finding.
sweep = [
    ("openings[0].host_wall", lambda d: d["openings"][0].__setitem__("host_wall", "W-90")),
    ("furniture[0].zone_ref", lambda d: d["furniture"][0].__setitem__("zone_ref", "Z-90")),
    ("furniture[0].material_ref", lambda d: d["furniture"][0].__setitem__("material_ref", "M-90")),
    ("walls[0].finish_ref", lambda d: d["walls"][0].__setitem__("finish_ref", "M-90")),
    ("materials[0].applied_to", lambda d: d["materials"][0].__setitem__("applied_to", ["W-90"])),
    ("outputs[2].parent", lambda d: d["outputs"][2].__setitem__("derived_from_output", "OUT-90")),
]
missed = [name for name, fn in sweep if validate_references(mutate(fn))[0]]
RESULTS.append(("XI-02", "Mutation sweep: every corrupted reference is detected",
                "PASS" if not missed else "FAIL",
                f"missed: {missed}" if missed else f"{len(sweep)}/{len(sweep)} caught"))

# No-false-positive proof: base must stay clean across repeated validation.
clean_runs = all(validate_references(copy.deepcopy(BASE))[0] for _ in range(3))
RESULTS.append(("XI-03", "No false positives on the valid base (3 runs)",
                "PASS" if clean_runs else "FAIL", ""))

# Index sanity: ids must be unique and complete.
idx, dups = build_index(copy.deepcopy(BASE))
RESULTS.append(("XI-04", "Index builds with zero duplicates on the valid base",
                "PASS" if not dups else "FAIL",
                f"{len(idx)} ids indexed"))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("=" * 92)
print("PHASE 00.5-B1 — CROSS-REFERENCE INTEGRITY TEST REPORT")
print("=" * 92)
w = max(len(t[1]) for t in RESULTS)
for tid, title, status, detail in RESULTS:
    mark = "OK  " if status == "PASS" else "FAIL"
    print(f"{mark} {tid:9} {title:<{w}}  {detail[:44]}")
total = len(RESULTS)
passed = sum(1 for r in RESULTS if r[2] == "PASS")
print("-" * 92)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 92)
sys.exit(0 if passed == total else 1)
