#!/usr/bin/env python3
"""
test_00_5_A.py — Phase 00.5-A acceptance tests.

Success criterion (per user Gate 00 instruction):
  Creating files is NOT success. Success = the rules demonstrably fire.

Every NEGATIVE test must FAIL validation (the schema must reject it).
Every POSITIVE test must PASS validation.
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from schema_gate import validate_master, load_schema, lint_caption  # noqa: E402

SYSTEM = Path(__file__).resolve().parent.parent
SCHEMA = load_schema()
TODAY = "2026-09-11"

RESULTS = []


def check(test_id, title, data, expect_pass, expect_msg_contains=None):
    ok, errs = validate_master(data, SCHEMA)
    passed = (ok == expect_pass)
    detail = ""
    if not expect_pass:
        if ok:
            detail = "SCHEMA ACCEPTED IT — rule did not fire"
        else:
            detail = errs[0][:150]
            if expect_msg_contains and not any(expect_msg_contains in e for e in errs):
                passed = False
                detail = f"rejected, but not for the expected reason: {errs[0][:120]}"
    else:
        if not ok:
            detail = errs[0][:200]
    RESULTS.append((test_id, title, "PASS" if passed else "FAIL", detail))
    return passed


# ---------------------------------------------------------------------------
# Baseline: a minimal but fully valid TEST master.
# All data below is synthetic and exists only to exercise the schema.
# ---------------------------------------------------------------------------
def fact(value, status="C", src="CLIENT_INPUT", ref="test fixture", **kw):
    f = {
        "value": value,
        "status": status,
        "source_type": src,
        "source_ref": ref,
        "recorded_on": TODAY,
    }
    f.update(kw)
    return f


BASE = {
    "meta": {
        "project_id": "PRJ-99",
        "project_name": "SCHEMA TEST ROOM",
        "revision": "R00",
        "geometry_version": "G-001",
        "status": "DRAFT",
        "track": "LITE",
        "units": "mm",
        "created_on": TODAY,
        "is_test_project": True,
        "test_banner": "TEST PROJECT — NOT A REAL CLIENT PROJECT",
        "not_for_construction": "DESIGN INTENT — NOT FOR CONSTRUCTION",
    },
    "space": {
        "outline": fact([[0, 0], [4000, 0], [4000, 3000], [0, 3000]], unit="mm"),
        "ceiling_height": fact(2800, unit="mm"),
        "orientation_north": {
            "value": None, "status": "U", "source_type": "NOT_PROVIDED",
            "source_ref": "not supplied", "recorded_on": TODAY,
            "blocking": False, "unknown_id": "U-003",
        },
        "floor_level": {
            "value": None, "status": "U", "source_type": "NOT_PROVIDED",
            "source_ref": "not supplied", "recorded_on": TODAY,
            "blocking": False, "unknown_id": "U-004",
        },
    },
    "walls": [{
        "id": "W-01",
        "start": fact([0, 0], unit="mm"),
        "end": fact([4000, 0], unit="mm"),
        "thickness": fact(200, unit="mm"),
        "structural": fact(True),
    }],
    "openings": [{
        "id": "D-01", "kind": "door", "host_wall": "W-01",
        "offset": fact(500, unit="mm"),
        "width": fact(900, unit="mm"),
        "height": fact(2100, unit="mm"),
    }],
    "columns": [],
    "zones": [],
    "furniture": [],
    "materials": [],
    "presence_register": {
        "columns": {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
                    "source_ref": "client survey: no columns", "recorded_on": TODAY,
                    "presence": "NOT_PRESENT"},
        "beams": {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
                  "source_ref": "client survey: no beams", "recorded_on": TODAY,
                  "presence": "NOT_PRESENT"},
        "protrusions": {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
                        "source_ref": "client survey", "recorded_on": TODAY,
                        "presence": "NOT_PRESENT"},
        "level_changes": {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
                          "source_ref": "client survey", "recorded_on": TODAY,
                          "presence": "NOT_PRESENT"},
        "services": {"value": None, "status": "U", "source_type": "NOT_PROVIDED",
                     "source_ref": "not asked", "recorded_on": TODAY,
                     "blocking": False, "unknown_id": "U-009", "presence": "UNKNOWN"},
        "existing_furniture": {"value": None, "status": "C", "source_type": "CLIENT_INPUT",
                               "source_ref": "client survey", "recorded_on": TODAY,
                               "presence": "NOT_PRESENT"},
        "openings": {"value": True, "status": "C", "source_type": "CLIENT_INPUT",
                     "source_ref": "client survey: one door", "recorded_on": TODAY,
                     "presence": "PRESENT"},
    },
    "cameras": [{"id": "CAM-01", "pos": [3000, 2000, 1550], "target": [500, 500, 1100],
                 "fov_deg": 45, "status": "C"}],
    "registers": {
        "unknowns": [
            {"id": "U-003", "question": "North orientation?", "blocking": False, "raised_on": TODAY},
            {"id": "U-004", "question": "Floor level?", "blocking": False, "raised_on": TODAY},
        ],
        "assumptions": [], "proposals": [], "decisions": [],
        "change_requests": [], "objections": [],
        "changelog": [{"revision": "R00", "date": TODAY, "type": "INITIAL",
                       "summary": "Test fixture created."}],
    },
    "outputs": [],
}


def m(**overrides):
    d = copy.deepcopy(BASE)
    for k, v in overrides.items():
        d[k] = v
    return d


# ===========================================================================
# POSITIVE TESTS
# ===========================================================================
check("P-01", "Valid minimal master is accepted", m(), True)

check("P-02", "Derived value with formula + inputs accepted",
      m(space={**copy.deepcopy(BASE["space"]),
               "services": {"value": 12000000, "unit": "mm2", "status": "D",
                            "source_type": "DERIVED_CALC",
                            "source_ref": "area calc",
                            "recorded_on": TODAY,
                            "derived_from": ["space.outline"],
                            "derivation_type": "ARITHMETIC",
                            "formula": "4000 * 3000 = 12000000"}}),
      True)

_appr = m()
_appr["materials"] = [{
    "id": "M-01",
    "name": {"value": "Matte porcelain", "status": "C", "source_type": "USER_APPROVAL",
             "source_ref": "Gate 05 approval", "recorded_on": TODAY,
             "decision_id": "DEC-001", "approved_by": "USER",
             "approved_on": TODAY, "approved_in_revision": "R00", "locked": True},
    "color_hex": fact("#C9C4BC"),
    "applied_to": ["W-01"],
}]
_appr["registers"]["proposals"] = [{"id": "P-001", "text": "Use matte porcelain floor",
                                    "state": "APPROVED", "raised_on": TODAY,
                                    "decision_id": "DEC-001"}]
_appr["registers"]["decisions"] = [{
    "decision_id": "DEC-001", "title": "Floor finish", "linked_proposal": "P-001",
    "rationale": "High traffic resistance and fewer visual joints",
    "alternatives_considered": ["Parquet (rejected: humidity)"],
    "approved_by": "USER", "approved_on": TODAY, "approved_in_revision": "R00",
}]
check("P-03", "Proposal -> approval -> [C] with full Decision Record accepted", _appr, True)

_ext = m()
_ext["furniture"] = [{
    "id": "F-01", "name": "Dining chair",
    "position": fact([1000, 1000], unit="mm"),
    "dims": {"value": [450, 500, 850], "unit": "mm", "status": "P",
             "source_type": "EXTERNAL_LIBRARY", "source_ref": "furniture_library.json#chair_std",
             "recorded_on": TODAY, "proposal_id": "P-002",
             "external": {"ref": "Internal library entry chair_std, sourced from published anthropometric tables",
                          "retrieved_on": TODAY,
                          "applicability_note": "Generic figure. Not verified against this project's users."}},
    "material_ref": "M-01",
}]
_ext["registers"]["proposals"] = [{"id": "P-002", "text": "Standard dining chair footprint",
                                   "state": "OPEN", "raised_on": TODAY}]
check("P-04", "External library dimension enters as [P] with citation", _ext, True)

_outA = m()
_outA["outputs"] = [{
    "output_id": "OUT-001", "file": "PRJ99_R00_A_FloorPlan.pdf", "class": "A",
    "view_type": "FloorPlan", "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
    "binding_geometry": True, "binding_visual": True,
    "fingerprint": {"project_id": "PRJ-99", "master_revision": "R00", "master_hash": "a3f9c2",
                    "geometry_version": "G-001", "element_set_hash": "7bd41f",
                    "positions_hash": "c92e08", "materials_hash": "4a1db7",
                    "camera_id": None, "camera_hash": None},
    "generated_on": TODAY,
}]
check("P-05", "Class A output with 9-field fingerprint accepted", _outA, True)

_outB = copy.deepcopy(_outA)
_outB["outputs"].append({
    "output_id": "OUT-002", "file": "PRJ99_R00_B_Board01.pdf", "class": "B",
    "view_type": "PresentationBoard",
    "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
    "binding_geometry": True, "binding_visual": False, "supersedes_A": False,
    "derived_from_output": "OUT-001",
    "fingerprint": _outA["outputs"][0]["fingerprint"],
    "generated_on": TODAY,
})
check("P-06", "Class B output must declare its parent Class A output", _outB, True)

_outC = copy.deepcopy(_outA)
_outC["outputs"].append({
    "output_id": "OUT-003", "file": "PRJ99_R00_C_Mood01.png", "class": "C",
    "view_type": "AIMood",
    "guarantee": "NOT_GEOMETRICALLY_GUARANTEED_NON_BINDING",
    "binding_geometry": False, "binding_visual": False, "supersedes_A": False,
    "caption": "AI MOOD — NON-BINDING. Approved geometry is in OUT-001.",
    "fingerprint": _outA["outputs"][0]["fingerprint"],
    "generated_on": TODAY,
})
check("P-07", "Class C with compliant non-binding caption accepted", _outC, True)

_tf = m()
_tf["registers"]["changelog"].append({
    "revision": "R00", "date": TODAY, "type": "TECHNICAL_FIX",
    "summary": "Fixed SVG stroke width bug in plan renderer",
    "master_hash_before": "a3f9c2", "master_hash_after": "a3f9c2",
    "geometry_version_before": "G-001", "geometry_version_after": "G-001",
    "tests_rerun": True, "regressions_found": False,
    "output_diff_explained": "Line weight changed 0.5->0.35mm; geometry byte-identical.",
})
check("P-08", "Compliant Technical Fix changelog accepted", _tf, True)


# ===========================================================================
# NEGATIVE TESTS — each MUST be rejected
# ===========================================================================
_n = m()
_n["space"]["ceiling_height"] = {"value": 2800, "unit": "mm"}
check("N-01", "Bare value with no status/source is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = {"value": 2800, "unit": "mm", "status": "C",
                                 "recorded_on": TODAY, "source_type": "CLIENT_INPUT"}
check("N-02", "Missing source_ref is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = fact(2800, status="C", src="AGENT_PROPOSAL", ref="I think 2800")
check("N-03", "Agent proposal self-promoted to [C] is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = fact(2800, status="C", src="AGENT_ASSUMPTION", ref="assumed typical")
check("N-04", "Assumption self-promoted to [C] is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = fact(2800, status="C", src="USER_APPROVAL", ref="user said ok")
check("N-05", "Approval-based [C] without Decision Record is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = {"value": 2800, "unit": "mm", "status": "D",
                                 "source_type": "DERIVED_CALC", "source_ref": "calc",
                                 "recorded_on": TODAY}
check("N-06", "Derived value without formula/inputs is REJECTED", _n, False)

# ---------------------------------------------------------------------------
# R02 BLOCK 1 — [D] boundary tests (Gate 00.5-A R02 §2 and §7)
# ---------------------------------------------------------------------------

# N-D-01: derivation from a non-confirmed input.
_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["services"] = {"value": 6000000, "unit": "mm2", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "area calc",
                   "recorded_on": TODAY,
                   "derived_from": ["space.orientation_north"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "unknown_input * 2 = 6000000"}
_n["space"] = _sp
check("N-D-01", "[D] derived from an UNKNOWN input is REJECTED", _n, False,
      expect_msg_contains="INV-D1")

# N-D-01b: derivation from a pending assumption.
_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["floor_level"] = {"value": 100, "unit": "mm", "status": "A",
                      "source_type": "AGENT_ASSUMPTION", "source_ref": "assumed screed",
                      "recorded_on": TODAY, "assumption_id": "A-01",
                      "impact": "affects all heights", "approval_state": "PENDING_APPROVAL"}
_sp["services"] = {"value": 2900, "unit": "mm", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "height calc",
                   "recorded_on": TODAY,
                   "derived_from": ["space.floor_level"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "2800 + 100 = 2900"}
_n["space"] = _sp
_n["registers"]["assumptions"] = [{"id": "A-01", "text": "Assumed screed thickness",
                                   "impact": "affects all heights",
                                   "approval_state": "PENDING_APPROVAL", "raised_on": TODAY}]
check("N-D-01b", "[D] derived from a PENDING assumption is REJECTED", _n, False,
      expect_msg_contains="INV-D1")

# N-D-01c: derivation from a reference that does not exist at all.
_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["services"] = {"value": 999, "unit": "mm", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "calc",
                   "recorded_on": TODAY,
                   "derived_from": ["space.nonexistent_field"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "x * 1 = 999"}
_n["space"] = _sp
# OWNERSHIP MOVED (Phase 00.5-B1): reference EXISTENCE is XR-008, not INV-D1.
# This layer must NOT flag it, and the B1 engine MUST. Both halves asserted.
_layerA_ok, _ = validate_master(_n, SCHEMA)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_refs import validate_references as _vr  # noqa: E402
_layerB_ok, _b_findings = _vr(_n)
_owned = _layerA_ok and (not _layerB_ok) and any(f.rule == "XR-008" for f in _b_findings)
RESULTS.append(("N-D-01c", "Unresolvable derived_from is owned by XR-008, not INV-D1",
                "PASS" if _owned else "FAIL",
                f"layerA_clean={_layerA_ok} XR-008_fired={any(f.rule=='XR-008' for f in _b_findings)}"))

# N-D-02: a design decision dressed up as a derivation.
_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["services"] = {"value": 8, "unit": "count", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "seating calc",
                   "recorded_on": TODAY,
                   "derived_from": ["space.outline"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "area allows it, so we choose 8 chairs as the optimal count"}
_n["space"] = _sp
check("N-D-02", "[D] smuggling a design CHOICE is REJECTED", _n, False,
      expect_msg_contains="INV-D2")

# N-D-02b: Arabic-language choice smuggling.
_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["services"] = {"value": 8, "unit": "count", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "حساب المقاعد",
                   "recorded_on": TODAY,
                   "derived_from": ["space.outline"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "المساحة تسمح، لذلك نختار 8 كراسي وهو الأنسب"}
_n["space"] = _sp
check("N-D-02b", "[D] smuggling a choice in Arabic is REJECTED", _n, False,
      expect_msg_contains="INV-D2")

# N-D-02c: a [D] cannot be a decision.
_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["services"] = {"value": 12000000, "unit": "mm2", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "area",
                   "recorded_on": TODAY, "derived_from": ["space.outline"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "4000 * 3000 = 12000000",
                   "decision_id": "DEC-001"}
_n["space"] = _sp
check("N-D-02d", "[D] carrying a decision_id is REJECTED", _n, False)

_n = m()
_sp = copy.deepcopy(BASE["space"])
_sp["services"] = {"value": 12000000, "unit": "mm2", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "area",
                   "recorded_on": TODAY, "derived_from": ["space.outline"],
                   "derivation_type": "ARITHMETIC",
                   "formula": "4000 * 3000 = 12000000", "locked": True}
_n["space"] = _sp
check("N-D-02e", "Locking a [D] is REJECTED", _n, False)

# ---------------------------------------------------------------------------
# R02 BLOCK 2 — TRI-STATE tests (Gate 00.5-A R02 §3, §5, §7)
# ---------------------------------------------------------------------------

# N-STATE-01: empty/absent value being passed off as confirmed absence.
_n = m()
_n["presence_register"]["columns"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "field left empty", "recorded_on": TODAY,
    "blocking": True, "unknown_id": "U-005", "presence": "NOT_PRESENT"}
check("N-STATE-01", "Empty/UNKNOWN field claimed as NOT_PRESENT is REJECTED", _n, False)

# N-STATE-01b: agent deciding on its own that nothing is there.
_n = m()
_n["presence_register"]["columns"] = {
    "value": None, "status": "C", "source_type": "AGENT_ASSUMPTION",
    "source_ref": "no columns mentioned, assuming none", "recorded_on": TODAY,
    "presence": "NOT_PRESENT"}
check("N-STATE-01c", "Agent asserting NOT_PRESENT without client confirmation is REJECTED",
      _n, False)

# N-STATE-02: confirmed absence mislabelled as unknown.
_n = m()
_n["presence_register"]["columns"] = {
    "value": None, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client confirmed no columns", "recorded_on": TODAY,
    "presence": "UNKNOWN"}
check("N-STATE-02", "Confirmed data carrying presence=UNKNOWN is REJECTED", _n, False)

# N-STATE-03: PRESENT but no actual value.
_n = m()
_n["presence_register"]["columns"] = {
    "value": None, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client said there are columns", "recorded_on": TODAY,
    "presence": "PRESENT"}
check("N-STATE-03", "presence=PRESENT with a null value is REJECTED", _n, False)

# N-STATE-04: register says none, yet elements exist.
_n = m()
_n["columns"] = [{"id": "C-01", "position": fact([1000, 1000], unit="mm"),
                  "dims": fact([300, 300], unit="mm")}]
check("N-STATE-04", "Elements existing while register says NOT_PRESENT is REJECTED",
      _n, False, expect_msg_contains="INV-S1")

# N-STATE-05: register missing a required collection entirely.
_n = m()
del _n["presence_register"]["columns"]
check("N-STATE-05", "Presence register missing a collection is REJECTED", _n, False)

# N-OPEN-01: openings invented while their presence is unknown.
_n = m()
_n["presence_register"]["openings"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "not surveyed", "recorded_on": TODAY,
    "blocking": True, "unknown_id": "U-011", "presence": "UNKNOWN"}
check("N-OPEN-01", "Inventing openings while presence is UNKNOWN is REJECTED", _n, False,
      expect_msg_contains="INV-OPEN1")

# N-APPROVAL-01: a fact claiming approval with no Decision Record behind it.
_n = m()
_n["materials"] = [{
    "id": "M-01",
    "name": {"value": "Walnut veneer", "status": "C", "source_type": "USER_APPROVAL",
             "source_ref": "approved", "recorded_on": TODAY,
             "decision_id": "DEC-099", "approved_by": "USER",
             "approved_on": TODAY, "approved_in_revision": "R00", "locked": True},
    "color_hex": fact("#6B4A2F"),
    "applied_to": ["W-01"],
}]
_layerA_ok, _ = validate_master(_n, SCHEMA)
_layerB_ok, _b_findings = _vr(_n)
_owned = _layerA_ok and (not _layerB_ok) and any(f.rule == "XR-006" for f in _b_findings)
RESULTS.append(("N-APPROVAL-01", "Ghost Decision Record is owned by XR-006 (still rejected)",
                "PASS" if _owned else "FAIL",
                f"layerA_clean={_layerA_ok} XR-006_fired={any(f.rule=='XR-006' for f in _b_findings)}"))

# N-APPROVAL-02: decision pointing at a proposal that was never made.
_n = m()
_n["registers"]["decisions"] = [{
    "decision_id": "DEC-003", "title": "Ceiling type", "linked_proposal": "P-404",
    "rationale": "chosen for acoustic performance in the main zone",
    "alternatives_considered": ["exposed slab"],
    "approved_by": "USER", "approved_on": TODAY, "approved_in_revision": "R00",
}]
_layerA_ok, _ = validate_master(_n, SCHEMA)
_layerB_ok, _b_findings = _vr(_n)
_owned = _layerA_ok and (not _layerB_ok) and any(f.rule == "XR-010" for f in _b_findings)
RESULTS.append(("N-APPROVAL-02", "Ghost linked_proposal is owned by XR-010 (still rejected)",
                "PASS" if _owned else "FAIL",
                f"layerA_clean={_layerA_ok} XR-010_fired={any(f.rule=='XR-010' for f in _b_findings)}"))

_n = m()
_n["space"]["ceiling_height"] = {"value": 2800, "unit": "mm", "status": "A",
                                 "source_type": "AGENT_ASSUMPTION", "source_ref": "typical",
                                 "recorded_on": TODAY}
check("N-07", "Assumption without id/impact/approval_state is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = {"value": 2800, "unit": "mm", "status": "A",
                                 "source_type": "AGENT_ASSUMPTION", "source_ref": "typical",
                                 "recorded_on": TODAY, "assumption_id": "A-01",
                                 "impact": "affects ceiling design", "approval_state": "PENDING_APPROVAL",
                                 "locked": True}
check("N-08", "Locking an ASSUMPTION is REJECTED", _n, False)

_n = m()
_n["space"]["orientation_north"] = {"value": 45, "unit": "deg", "status": "U",
                                    "source_type": "NOT_PROVIDED", "source_ref": "none",
                                    "recorded_on": TODAY, "blocking": False, "unknown_id": "U-003"}
check("N-09", "UNKNOWN carrying a real value is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = fact(2800, status="C", src="AI_IMAGE",
                                     ref="measured from render")
check("N-10", "AI image used as a source is REJECTED", _n, False)

_n = m()
_n["furniture"] = [{
    "id": "F-01", "name": "Chair",
    "position": fact([1000, 1000], unit="mm"),
    "dims": {"value": [450, 500, 850], "unit": "mm", "status": "C",
             "source_type": "EXTERNAL_LIBRARY", "source_ref": "library",
             "recorded_on": TODAY},
    "material_ref": "M-01",
}]
check("N-11", "External library value claimed as [C] is REJECTED", _n, False)

_n = m()
_n["furniture"] = [{
    "id": "F-01", "name": "Chair",
    "position": fact([1000, 1000], unit="mm"),
    "dims": {"value": [450, 500, 850], "unit": "mm", "status": "P",
             "source_type": "EXTERNAL_STANDARD", "source_ref": "some standard",
             "recorded_on": TODAY, "proposal_id": "P-002"},
    "material_ref": "M-01",
}]
check("N-12", "External standard without citation block is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = {"value": 2800, "unit": "mm", "status": "P",
                                 "source_type": "AGENT_PROPOSAL", "source_ref": "suggestion",
                                 "recorded_on": TODAY, "proposal_id": "P-003", "locked": True}
check("N-13", "Locking a PROPOSAL is REJECTED", _n, False)

_n = m()
_n["outputs"] = [{
    "output_id": "OUT-003", "file": "mood.png", "class": "C", "view_type": "AIMood",
    "guarantee": "NOT_GEOMETRICALLY_GUARANTEED_NON_BINDING",
    "binding_geometry": False, "binding_visual": False, "supersedes_A": False,
    "caption": "AI render — 100% مطابق للتصميم المعتمد",
    "fingerprint": {"project_id": "PRJ-99", "master_revision": "R00", "master_hash": "a3f9c2",
                    "geometry_version": "G-001", "element_set_hash": "7bd41f",
                    "positions_hash": "c92e08", "materials_hash": "4a1db7",
                    "camera_id": None, "camera_hash": None},
    "generated_on": TODAY,
}]
check("N-14", "Class C caption claiming 100% match is REJECTED", _n, False)

_n = m()
_n["outputs"] = [{
    "output_id": "OUT-004", "file": "mood.png", "class": "C", "view_type": "AIMood",
    "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
    "binding_geometry": True, "binding_visual": True,
    "fingerprint": {"project_id": "PRJ-99", "master_revision": "R00", "master_hash": "a3f9c2",
                    "geometry_version": "G-001", "element_set_hash": "7bd41f",
                    "positions_hash": "c92e08", "materials_hash": "4a1db7",
                    "camera_id": None, "camera_hash": None},
    "generated_on": TODAY,
}]
check("N-15", "AI output claiming binding geometry is REJECTED", _n, False)

_n = m()
_n["outputs"] = [{
    "output_id": "OUT-005", "file": "board.pdf", "class": "B", "view_type": "Board",
    "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
    "binding_geometry": True, "binding_visual": False, "supersedes_A": True,
    "derived_from_output": "OUT-001",
    "fingerprint": {"project_id": "PRJ-99", "master_revision": "R00", "master_hash": "a3f9c2",
                    "geometry_version": "G-001", "element_set_hash": "7bd41f",
                    "positions_hash": "c92e08", "materials_hash": "4a1db7",
                    "camera_id": None, "camera_hash": None},
    "generated_on": TODAY,
}]
check("N-16", "Class B claiming to supersede Class A is REJECTED", _n, False)

_n = m()
_n["outputs"] = [{
    "output_id": "OUT-006", "file": "board.pdf", "class": "B", "view_type": "Board",
    "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
    "binding_geometry": True, "binding_visual": False, "supersedes_A": False,
    "fingerprint": {"project_id": "PRJ-99", "master_revision": "R00", "master_hash": "a3f9c2",
                    "geometry_version": "G-001", "element_set_hash": "7bd41f",
                    "positions_hash": "c92e08", "materials_hash": "4a1db7",
                    "camera_id": None, "camera_hash": None},
    "generated_on": TODAY,
}]
check("N-17", "Class B without a parent Class A output is REJECTED", _n, False)

_n = m()
_n["outputs"] = [{
    "output_id": "OUT-007", "file": "plan.pdf", "class": "A", "view_type": "FloorPlan",
    "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
    "binding_geometry": True, "binding_visual": True,
    "fingerprint": {"project_id": "PRJ-99", "master_revision": "R00", "master_hash": "a3f9c2",
                    "geometry_version": "G-001", "element_set_hash": "7bd41f",
                    "positions_hash": "c92e08"},
    "generated_on": TODAY,
}]
check("N-18", "Output with incomplete fingerprint is REJECTED", _n, False)

_n = m()
_n["registers"]["changelog"].append({
    "revision": "R00", "date": TODAY, "type": "TECHNICAL_FIX",
    "summary": "renderer tweak",
    "master_hash_before": "a3f9c2", "master_hash_after": "b71e04",
    "geometry_version_before": "G-001", "geometry_version_after": "G-001",
    "tests_rerun": True, "regressions_found": False,
    "output_diff_explained": "n/a",
})
check("N-19", "Technical Fix where master_hash CHANGED is REJECTED", _n, False)

_n = m()
_n["registers"]["changelog"].append({
    "revision": "R00", "date": TODAY, "type": "TECHNICAL_FIX",
    "summary": "renderer tweak",
    "master_hash_before": "a3f9c2", "master_hash_after": "a3f9c2",
    "geometry_version_before": "G-001", "geometry_version_after": "G-002",
    "tests_rerun": True, "regressions_found": False,
    "output_diff_explained": "n/a",
})
check("N-20", "Technical Fix where geometry_version CHANGED is REJECTED", _n, False,
      expect_msg_contains=None)

_n = m()
_n["registers"]["changelog"].append({
    "revision": "R00", "date": TODAY, "type": "TECHNICAL_FIX",
    "summary": "renderer tweak",
    "master_hash_before": "a3f9c2", "master_hash_after": "a3f9c2",
    "geometry_version_before": "G-001", "geometry_version_after": "G-001",
    "tests_rerun": False, "regressions_found": False,
    "output_diff_explained": "n/a",
})
check("N-21", "Technical Fix without re-running tests is REJECTED", _n, False)

_n = m()
_n["registers"]["changelog"].append({
    "revision": "R00", "date": TODAY, "type": "TECHNICAL_FIX",
    "summary": "renderer tweak",
    "master_hash_before": "a3f9c2", "master_hash_after": "a3f9c2",
    "geometry_version_before": "G-001", "geometry_version_after": "G-001",
    "tests_rerun": True, "regressions_found": True,
    "output_diff_explained": "some outputs shifted",
})
check("N-22", "Technical Fix WITH regressions is REJECTED", _n, False)

_n = m()
_n["registers"]["change_requests"] = [{
    "id": "CR-001", "target_element": "F-12", "current_value": 3200, "proposed_value": 3600,
    "reason": "door swing clash", "impact": "furniture plan",
    "classification": "MINOR", "state": "APPLIED", "raised_on": TODAY,
}]
check("N-23", "MINOR CR applied without approval is REJECTED (No Auto-Apply)", _n, False)

_n = m()
_n["registers"]["proposals"] = [{"id": "P-005", "text": "Use walnut veneer",
                                 "state": "APPROVED", "raised_on": TODAY}]
check("N-24", "Approved proposal with no Decision Record is REJECTED", _n, False)

_n = m()
_n["registers"]["decisions"] = [{
    "decision_id": "DEC-002", "title": "Ceiling", "linked_proposal": "P-006",
    "rationale": "looks better in the render",
    "alternatives_considered": [],
    "approved_by": "AGENT", "approved_on": TODAY, "approved_in_revision": "R00",
}]
check("N-25", "Agent self-approving a decision is REJECTED", _n, False)

_n = m()
_n["meta"]["is_test_project"] = True
del _n["meta"]["test_banner"]
check("N-26", "Test project without TEST banner is REJECTED", _n, False)

_n = m()
_n["meta"]["status"] = "FROZEN"
check("N-27", "FROZEN master without frozen_on/master_hash is REJECTED", _n, False)

_n = m()
_n["meta"]["units"] = "cm"
check("N-28", "Non-mm units are REJECTED", _n, False)

_n = m()
_n["space"]["window_count"] = fact(3)
check("N-29", "Undeclared extra field in space is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = fact(2800, status="C", ref="client", made_up_field="hello")
check("N-30", "Unknown property inside a fact is REJECTED", _n, False)

_n = m()
_n["walls"] = [{"id": "WALL1", "start": fact([0, 0]), "end": fact([1, 1]),
                "thickness": fact(200), "structural": fact(True)}]
check("N-31", "Malformed element ID is REJECTED", _n, False)

_n = m()
_n["space"]["ceiling_height"] = fact(2800, status="X", ref="client")
check("N-32", "Invalid status tag is REJECTED", _n, False)

_n = m()
_n["registers"]["changelog"].append({
    "revision": "R01", "date": TODAY, "type": "CR_APPLIED",
    "summary": "moved chair",
})
check("N-33", "CR_APPLIED changelog entry without cr_id is REJECTED", _n, False)


# ---------------------------------------------------------------------------
# R02 BLOCK 3 — TRI-STATE positives: all three states must be expressible
# ---------------------------------------------------------------------------
_p = m()
_p["presence_register"]["columns"] = {
    "value": None, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client survey 2026-09-11: room has no columns",
    "recorded_on": TODAY, "presence": "NOT_PRESENT"}
check("P-09", "State NOT_PRESENT (confirmed absence) is accepted", _p, True)

_p = m()
_p["presence_register"]["columns"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "not surveyed", "recorded_on": TODAY,
    "blocking": True, "unknown_id": "U-005", "presence": "UNKNOWN"}
check("P-10", "State UNKNOWN (nobody knows) is accepted", _p, True)

_p = m()
_p["presence_register"]["columns"] = {
    "value": [{"ref": "C-01"}], "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client survey: one column", "recorded_on": TODAY,
    "presence": "PRESENT"}
_p["columns"] = [{"id": "C-01", "position": fact([1000, 1000], unit="mm"),
                  "dims": fact([300, 300], unit="mm")}]
check("P-11", "State PRESENT with real data is accepted", _p, True)

# Proof that the three states are genuinely distinct, not interchangeable.
_s1 = m(); _s1["presence_register"]["columns"] = {
    "value": None, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "no columns", "recorded_on": TODAY, "presence": "NOT_PRESENT"}
_s2 = m(); _s2["presence_register"]["columns"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "not asked", "recorded_on": TODAY,
    "blocking": True, "unknown_id": "U-005", "presence": "UNKNOWN"}
distinct = (
    _s1["presence_register"]["columns"]["presence"]
    != _s2["presence_register"]["columns"]["presence"]
    and validate_master(_s1, SCHEMA)[0] and validate_master(_s2, SCHEMA)[0]
)
RESULTS.append(("P-12", "NONE and UNKNOWN are distinct, both valid, not interchangeable",
                "PASS" if distinct else "FAIL", ""))


# ---------------------------------------------------------------------------
# R02 BLOCK 4 — Governance layer (GAP-02 must actively block final approval)
# ---------------------------------------------------------------------------
from schema_gate import final_approval_readiness, GOVERNANCE_GAPS  # noqa: E402

# A fully valid, fully approved master must STILL be blocked from final
# approval, because the approval ledger does not exist yet (GAP-02).
ready, blockers = final_approval_readiness(_appr)
gap02_fires = (not ready) and any("GAP-02" in b for b in blockers)
RESULTS.append(("G-01", "GAP-02 blocks FINAL approval despite valid approved_by:USER",
                "PASS" if gap02_fires else "FAIL",
                "" if gap02_fires else "governance layer did not block"))

# A blocking unknown must block final approval.
_g = m()
_g["registers"]["unknowns"].append(
    {"id": "U-001", "question": "Room outline?", "blocking": True, "raised_on": TODAY})
ready2, blockers2 = final_approval_readiness(_g)
RESULTS.append(("G-02", "Unresolved BLOCKING unknown blocks final approval",
                "PASS" if (not ready2 and any("U-001" in b for b in blockers2)) else "FAIL", ""))

# An UNKNOWN presence must block final approval (services is UNKNOWN in BASE).
ready3, blockers3 = final_approval_readiness(m())
RESULTS.append(("G-03", "UNKNOWN presence blocks final approval",
                "PASS" if (not ready3 and any("services" in b for b in blockers3)) else "FAIL", ""))

# A KNOWN CONFLICT must block final approval.
_g = m()
_g["space"]["ceiling_height"] = fact(
    2800, ref="client",
    conflict={"cr_id": "CR-001", "description": "conflicts with beam soffit height"})
ready4, blockers4 = final_approval_readiness(_g)
RESULTS.append(("G-04", "KNOWN CONFLICT blocks final approval",
                "PASS" if (not ready4 and any("CONFLICT" in b for b in blockers4)) else "FAIL", ""))

# An open objection must block final approval.
_g = m()
_g["registers"]["objections"] = [{
    "id": "OBJ-001", "decision_under_objection": "DEC-001",
    "problem": "corridor drops below usable width",
    "impact": "circulation", "alternative": "shift the partition 200mm",
    "state": "OPEN", "raised_on": TODAY}]
ready5, blockers5 = final_approval_readiness(_g)
RESULTS.append(("G-05", "OPEN objection blocks final approval",
                "PASS" if (not ready5 and any("OBJ-001" in b for b in blockers5)) else "FAIL", ""))

RESULTS.append(("G-06", "Governance gaps are registered in code, not just prose",
                "PASS" if len(GOVERNANCE_GAPS) >= 5 else "FAIL",
                f"{len(GOVERNANCE_GAPS)} gaps registered"))


# ---------------------------------------------------------------------------
# Caption linter (reusable outside the schema)
# ---------------------------------------------------------------------------
lint_ok = (
    lint_caption("C", "AI MOOD — NON-BINDING") == []
    and len(lint_caption("C", "This render is 100% accurate")) == 1
    and len(lint_caption("C", "منظور مطابق للتصميم")) == 1
)
RESULTS.append(("L-01", "Caption linter flags forbidden match-language in Class C",
                "PASS" if lint_ok else "FAIL", ""))


# ---------------------------------------------------------------------------
# DEF-CROSS-01 — VALUE DOMAIN (targeted remediation, B-Series Closure Audit)
#
# Rules WG1/WG2 (wall) and SG1/SG2 (space) enforce MATHEMATICAL possibility
# only, mirroring the ratified RULE FG2 precedent (rotation -360..360).
# They impose NO standard: a 50mm wall and a 50mm ceiling both still pass.
# A value that is not KNOWN ([U]) is exempt, so the tri-state survives.
# ---------------------------------------------------------------------------
def _wall(**over):
    w = {"id": "W-01", "start": fact([0, 0], unit="mm"),
         "end": fact([4000, 0], unit="mm"),
         "thickness": fact(200, unit="mm"), "structural": fact(True)}
    w.update(over)
    return w


def _space(**over):
    sp = copy.deepcopy(BASE["space"])
    sp.update(over)
    return sp


_UNKNOWN_SCALAR = {"value": None, "status": "U", "source_type": "NOT_PROVIDED",
                   "source_ref": "not yet surveyed", "recorded_on": TODAY,
                   "blocking": False, "unknown_id": "U-009"}

# ---- NEGATIVE: mathematically impossible values must be rejected ----------
check("VD-N01", "WG1: negative wall thickness is rejected",
      m(walls=[_wall(thickness=fact(-200, unit="mm"))]), False,
      "walls/0/thickness/value")

check("VD-N02", "WG1: zero wall thickness is rejected",
      m(walls=[_wall(thickness=fact(0, unit="mm"))]), False,
      "walls/0/thickness/value")

check("VD-N03", "WG2: negative wall height is rejected",
      m(walls=[_wall(height=fact(-3000, unit="mm"))]), False,
      "walls/0/height/value")

check("VD-N04", "SG1: negative ceiling height is rejected",
      m(space=_space(ceiling_height=fact(-2800, unit="mm"))), False,
      "space/ceiling_height/value")

check("VD-N05", "SG1: zero ceiling height is rejected",
      m(space=_space(ceiling_height=fact(0, unit="mm"))), False,
      "space/ceiling_height/value")

check("VD-N06", "SG2: a two-point outline cannot bound an area",
      m(space=_space(outline=fact([[0, 0], [4000, 0]], unit="mm"))), False,
      "space/outline/value")

# ---- POSITIVE: no standard may be smuggled in -----------------------------
check("VD-P01", "A 50mm wall is thin but legal (no minimum thickness)",
      m(walls=[_wall(thickness=fact(50, unit="mm"))]), True)

check("VD-P02", "A 50mm ceiling is absurd but needs a STANDARD to reject",
      m(space=_space(ceiling_height=fact(50, unit="mm"))), True)

check("VD-P03", "A 40m ceiling is accepted (no maximum imposed)",
      m(space=_space(ceiling_height=fact(40000, unit="mm"))), True)

check("VD-P04", "A normal wall and space still validate",
      m(walls=[_wall(height=fact(3000, unit="mm"))]), True)

check("VD-P05", "A three-point outline is accepted",
      m(space=_space(outline=fact([[0, 0], [4000, 0], [0, 3000]], unit="mm"))),
      True)

# ---- BOUNDARY: the tri-state and the KNOWN-only condition -----------------
check("VD-B01", "An UNKNOWN thickness is exempt from the domain rule",
      m(walls=[_wall(thickness=dict(_UNKNOWN_SCALAR))]), True)

check("VD-B02", "An UNKNOWN ceiling height is exempt",
      m(space=_space(ceiling_height=dict(_UNKNOWN_SCALAR))), True)

check("VD-B03", "An UNKNOWN outline is exempt from the 3-point minimum",
      m(space=_space(outline=dict(_UNKNOWN_SCALAR))), True)

check("VD-B04", "The smallest positive thickness is accepted",
      m(walls=[_wall(thickness=fact(0.001, unit="mm"))]), True)

check("VD-B05", "A [D] derived thickness is also domain-checked",
      m(walls=[_wall(thickness={
          "value": -200, "status": "D", "source_type": "DERIVED_CALC",
          "source_ref": "computed", "recorded_on": TODAY,
          "derived_from": ["space.ceiling_height"],
          "derivation_type": "ARITHMETIC", "formula": "x - 3000"})]), False,
      "walls/0/thickness/value")

# ---- ISOLATION: A owns the domain; geometry layers are untouched ----------
_vd_iso = m(walls=[_wall(thickness=fact(-200, unit="mm"))])
_vd_a_ok = validate_master(_vd_iso, SCHEMA)[0]
RESULTS.append(("VD-I01", "The domain rule lives in A, not in a new engine",
                "PASS" if not _vd_a_ok else "FAIL",
                "rejected by the schema gate itself"))

_vd_src = (SYSTEM / "scripts" / "validate_topology.py").read_text(
    encoding="utf-8")
RESULTS.append(("VD-I02", "B2 was not given a thickness rule",
                "PASS" if '"thickness"' not in _vd_src else "FAIL",
                "WT-001..011 untouched"))


# ---------------------------------------------------------------------------
# Template must itself be schema-valid
# ---------------------------------------------------------------------------
with open(SYSTEM / "project_master.template.json", encoding="utf-8") as f:
    tpl = json.load(f)
tpl.pop("_README", None)
ok_tpl, errs_tpl = validate_master(tpl, SCHEMA)
RESULTS.append(("T-01", "Shipped template validates against the schema",
                "PASS" if ok_tpl else "FAIL", "" if ok_tpl else errs_tpl[0][:160]))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("=" * 78)
print("PHASE 00.5-A — SCHEMA ENFORCEMENT TEST REPORT")
print("=" * 78)
w = max(len(t[1]) for t in RESULTS)
for tid, title, status, detail in RESULTS:
    mark = "OK  " if status == "PASS" else "FAIL"
    print(f"{mark} {tid:6} {title:<{w}}  {detail[:60]}")

total = len(RESULTS)
passed = sum(1 for r in RESULTS if r[2] == "PASS")
print("-" * 78)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 78)
sys.exit(0 if passed == total else 1)
