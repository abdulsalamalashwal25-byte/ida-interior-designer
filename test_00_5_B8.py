#!/usr/bin/env python3
"""Phase 00.5-B8 — Output / Representation Integrity test suite.

Discipline: every rule gets a POSITIVE and a NEGATIVE case; the negative
proves the INTENDED rule fired; mutation tests prove the suite dies when the
engine is disabled.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import ast
import copy
import io
import json
import os
import re
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from schema_gate import load_schema, validate_master               # noqa: E402
from validate_refs import validate_references                      # noqa: E402
from validate_formulas import validate_formulas                    # noqa: E402
from validate_blocking import validate_blocking                    # noqa: E402
from validate_outputs import (                                     # noqa: E402
    validate_outputs, representation_report, classify_authority,
    check_certainty_claims, check_provenance, check_authority_language,
    check_reverse_contamination,
    AUTH_AUTHORITATIVE, AUTH_DERIVED, AUTH_INDICATIVE, AUTH_NON_BINDING)

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []

# --------------------------------------------------------------------------
# Fixture — reuse B7's BASE (already accepted by A/B1/B6/B7).
# --------------------------------------------------------------------------
_b7_src = open(os.path.join(HERE, "test_00_5_B7.py"), encoding="utf-8").read()
_b7 = {"__name__": "b7fixture",
       "__file__": os.path.join(HERE, "test_00_5_B7.py")}
try:
    with redirect_stdout(io.StringIO()):
        exec(compile(_b7_src, "test_00_5_B7.py", "exec"), _b7)
except SystemExit:
    pass

_BASE = _b7["BASE"]
derived = _b7["derived"]
CAMERAS = _b7["CAMERAS"]

# Realistic, distinct hashes. A repeated-character placeholder is exactly what
# OR-003 is meant to reject, so the fixture must not use one.
H_MASTER = "fc613b4dfd6736a7bd268c8a0e74ed0d1c04a959f59dd74ef2874983fd443fc9"
H_ELEMS = "b0b17893a51343979e2090deee730538430cff2a88498e3885eb0ba179c58b6b"
H_POS = "f50871d14c198e22c629a383ccd1e1cf0dfe355d4bece706a0407abbd3de7973"
H_MATS = "afba1a0ce1c8af744d1951b94989616cd777a1e709b570c717f957784835dd88"
H_CAM = "89e8b9518d92279489bbdee26f3dc646d921d89a15afbd3a3e0ad695328a3da0"


def fingerprint(**over):
    fp = {"project_id": "PRJ-94", "master_revision": "R01",
          "master_hash": H_MASTER, "geometry_version": "G-001",
          "element_set_hash": H_ELEMS, "positions_hash": H_POS,
          "materials_hash": H_MATS, "camera_id": "CAM-01",
          "camera_hash": H_CAM}
    fp.update(over)
    return fp


def clean():
    """BASE with its only [U] filled, so B7 has nothing to say and any
    finding observed below is unambiguously B8's."""
    d = copy.deepcopy(_BASE)
    d["cameras"] = CAMERAS
    d["space"]["orientation_north"] = {
        "value": 0, "status": "C", "source_type": "CLIENT_INPUT",
        "source_ref": "client brief p.1", "recorded_on": TODAY, "unit": "deg"}
    d["registers"]["unknowns"] = []
    return d


def out_a(**over):
    """Class A — deterministic geometric match (authoritative)."""
    o = {"output_id": "OUT-001", "file": "plan.dxf", "class": "A",
         "view_type": "PLAN", "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
         "binding_geometry": True, "binding_visual": True,
         "fingerprint": fingerprint(), "generated_on": TODAY,
         "caption": "TEST PROJECT — plan view"}
    o.update(over)
    return o


def out_b(**over):
    """Class B — presentation, geometry derived from a class A parent."""
    o = {"output_id": "OUT-002", "file": "view.png", "class": "B",
         "view_type": "PERSPECTIVE",
         "guarantee": "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
         "binding_geometry": True, "binding_visual": False,
         "supersedes_A": False, "derived_from_output": "OUT-001",
         "fingerprint": fingerprint(), "generated_on": TODAY,
         "caption": "TEST PROJECT — indicative visual"}
    o.update(over)
    return o


def out_c(**over):
    """Class C — non-authoritative visual."""
    o = {"output_id": "OUT-009", "file": "mood.png", "class": "C",
         "view_type": "MOOD",
         "guarantee": "NOT_GEOMETRICALLY_GUARANTEED_NON_BINDING",
         "binding_geometry": False, "binding_visual": False,
         "supersedes_A": False, "fingerprint": fingerprint(),
         "generated_on": TODAY,
         "caption": "TEST PROJECT — mood reference only"}
    o.update(over)
    return o


def errs(findings):
    return sorted({f.rule for f in findings if f.severity == "ERROR"})


def run(d):
    return validate_outputs(d)


def all_layers(d):
    a, _ = validate_master(d, SCHEMA)
    b1, _ = validate_references(d)
    b6, _, _ = validate_formulas(d)
    b7, _ = validate_blocking(d)
    return a, b1, b6, b7


# ==========================================================================
# POSITIVE — a legitimate deliverable must pass untouched
# ==========================================================================
_d = clean()
_d["outputs"] = [out_a()]
_ok, _f = run(_d)
_a, _b1, _b6, _b7 = all_layers(_d)
RESULTS.append(("OP-01", "A valid class-A output passes every layer",
                "PASS" if (_ok and _a and _b1 and _b6 and _b7) else "FAIL",
                f"B8={_ok} A={_a} B1={_b1} B6={_b6} B7={_b7}"))

_d = clean()
_d["outputs"] = [out_a(), out_b()]
_ok, _f = run(_d)
RESULTS.append(("OP-02", "A class-B presentation derived from A is accepted",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))

_d = clean()
_d["outputs"] = [out_c()]
_ok, _f = run(_d)
RESULTS.append(("OP-03", "A non-authoritative class-C visual is accepted",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))

_d = clean()
_ok, _f = run(_d)
RESULTS.append(("OP-04", "A master with no outputs raises nothing",
                "PASS" if (_ok and not _f) else "FAIL", f"ok={_ok}"))

_tpl = json.load(open(os.path.join(ROOT, "project_master.template.json"),
                      encoding="utf-8"))
_tpl = {k: v for k, v in _tpl.items() if not k.startswith("_")}
_ok, _f = run(_tpl)
RESULTS.append(("OP-05", "The shipped template raises no B8 error",
                "PASS" if _ok else "FAIL", f"ok={_ok} {errs(_f)}"))

# The four authority levels are real and distinct.
_d = clean()
_d["outputs"] = [out_a(), out_b(), out_c(),
                 out_c(output_id="OUT-010", file="ai.png", fingerprint=None)]
_rep = representation_report(_d)
RESULTS.append(("OP-06", "Authority levels are output-aware, not uniform",
                "PASS" if (_rep.get("OUT-001") == AUTH_AUTHORITATIVE
                           and _rep.get("OUT-002") == AUTH_DERIVED
                           and _rep.get("OUT-009") == AUTH_INDICATIVE
                           and _rep.get("OUT-010") == AUTH_NON_BINDING)
                else "FAIL", f"{_rep}"))


# ==========================================================================
# PROVENANCE — OR-003 / OR-004 / OR-005
# ==========================================================================
_d = clean()
_d["outputs"] = [out_a(fingerprint=fingerprint(master_hash="0" * 64))]
_ok, _f = run(_d)
_a, _b1, _b6, _b7 = all_layers(_d)
RESULTS.append(("OV-01", "A placeholder hash is not provenance",
                "PASS" if (not _ok and "OR-003" in errs(_f)) else "FAIL",
                f"A={_a} B1={_b1} B7={_b7} B8={errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(output_id="OUT-001", file="a.dxf"),
                 out_a(output_id="OUT-002", file="b.dxf")]
_ok, _f = run(_d)
RESULTS.append(("OV-02", "Two different files cannot share one fingerprint",
                "PASS" if (not _ok and "OR-004" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(output_id="OUT-001", file="same.dxf"),
                 out_a(output_id="OUT-002", file="same.dxf")]
_ok, _f = run(_d)
RESULTS.append(("OV-03", "The same file re-listed is not a provenance clash",
                "PASS" if "OR-004" not in errs(_f) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["meta"]["created_on"] = "2026-09-12"
_d["outputs"] = [out_a(generated_on="2020-01-01")]
_ok, _f = run(_d)
RESULTS.append(("OV-04", "An output cannot predate its master",
                "PASS" if (not _ok and "OR-005" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(generated_on=TODAY)]
_ok, _f = run(_d)
RESULTS.append(("OV-05", "Same-day generation is not a time paradox",
                "PASS" if "OR-005" not in errs(_f) else "FAIL", f"{errs(_f)}"))

# BOUNDARY: a real hash that merely repeats a short run is still valid.
_d = clean()
_d["outputs"] = [out_a(fingerprint=fingerprint(
    master_hash="aaaa" + H_MASTER[4:]))]
_ok, _f = run(_d)
RESULTS.append(("OV-06", "A hash with a short repeated run is still valid",
                "PASS" if "OR-003" not in errs(_f) else "FAIL", f"{errs(_f)}"))


# ==========================================================================
# CERTAINTY CLAIMS — OR-001 / OR-002 (propagation from B7/B6)
# ==========================================================================
_d = clean()
_d["space"]["orientation_north"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "not supplied", "recorded_on": TODAY, "blocking": False,
    "unknown_id": "U-300"}
_d["registers"]["unknowns"] = [{"id": "U-300", "question": "north?",
                                "blocking": False, "raised_on": TODAY}]
_d["outputs"] = [out_a()]
_ok, _f = run(_d)
RESULTS.append(("OC-01", "An authoritative output over an UNKNOWN master",
                "PASS" if (not _ok and "OR-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d_unknown = copy.deepcopy(_d)
_d_unknown["outputs"] = [out_c()]
_ok, _f = run(_d_unknown)
RESULTS.append(("OC-02", "The same UNKNOWN under a class-C visual does not block",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))

_d = clean()
_d["space"]["floor_level"] = derived(
    1, "ceiling_height / 0", ["space.ceiling_height"], unit="mm")
_ok6, _f6, _v6 = validate_formulas(_d)
_d["outputs"] = [out_a()]
_ok, _f = run(_d)
RESULTS.append(("OC-03", "UNCOMPUTABLE must not be presented as a figure",
                "PASS" if (not _ok and "OR-002" in errs(_f)) else "FAIL",
                f"B6={list(_v6.values())} B8={errs(_f)}"))

_d2 = copy.deepcopy(_d)
_d2["outputs"] = [out_c()]
_ok, _f = run(_d2)
RESULTS.append(("OC-04", "UNCOMPUTABLE under a non-binding visual is INFO",
                "PASS" if (_ok and any(x.rule == "OR-009"
                                       and x.severity == "INFO" for x in _f))
                else "FAIL", f"ok={_ok}"))

_d = clean()
_d["space"]["orientation_north"] = {
    "value": None, "status": "P", "source_type": "AGENT_PROPOSAL",
    "source_ref": "proposed orientation", "recorded_on": TODAY, "unit": "deg",
    "proposal_id": "P-001"}
_d["registers"]["proposals"] = [{"id": "P-001", "text": "orient north",
                                 "state": "OPEN", "raised_on": TODAY}]
_d["outputs"] = [out_b()]
_ok, _f = run(_d)
RESULTS.append(("OC-05", "A class-B output over a [P] master is caught",
                "PASS" if (not _ok and "OR-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# B8 must NOT re-report a wrong-but-computable value; that verdict is B6's.
_d = clean()
_d["space"]["floor_level"] = derived(
    9999, "ceiling_height - 100", ["space.ceiling_height"], unit="mm")
_d["outputs"] = [out_a()]
_ok, _f = run(_d)
RESULTS.append(("OC-06", "A MISMATCH stays B6's verdict, not B8's",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"B8_errors={errs(_f)}"))


# ==========================================================================
# AUTHORITY LANGUAGE — OR-006 / OR-007
# ==========================================================================
_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — FINAL FOR CONSTRUCTION")]
_ok, _f = run(_d)
RESULTS.append(("OA-01", "'FOR CONSTRUCTION' on a DRAFT master is refused",
                "PASS" if (not _ok and "OR-006" in errs(_f)) else "FAIL",
                f"meta={_d['meta']['status']} {errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — as-built record")]
_ok, _f = run(_d)
RESULTS.append(("OA-02", "'as-built' on a DRAFT master is refused",
                "PASS" if (not _ok and "OR-006" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["outputs"] = [out_a(caption="TEST PROJECT — final issue")]
_ok, _f = run(_d)
RESULTS.append(("OA-03", "The same wording on a FROZEN master is allowed",
                "PASS" if "OR-006" not in errs(_f) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(caption="issue to contractor")]
_ok, _f = run(_d)
_warn = [x for x in _f if x.rule == "OR-007" and x.severity == "WARN"]
RESULTS.append(("OA-04", "A test project artefact without its banner is flagged",
                "PASS" if _warn else "FAIL", f"warn={len(_warn)}"))

_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — plan")]
_ok, _f = run(_d)
RESULTS.append(("OA-05", "A properly banner-marked caption is clean",
                "PASS" if not [x for x in _f if x.rule == "OR-007"] else "FAIL",
                "banner present"))

_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — preliminary layout study")]
_ok, _f = run(_d)
RESULTS.append(("OA-06", "Neutral wording triggers no authority claim",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))


# ==========================================================================
# ANTI-SMUGGLING / REVERSE CONTAMINATION — OR-008
# ==========================================================================
_d = clean()
_d["space"]["ceiling_height"] = {
    "value": 2800, "status": "C", "source_type": "AI_IMAGE",
    "source_ref": "measured from the AI render", "recorded_on": TODAY,
    "unit": "mm"}
_d["outputs"] = [out_c()]
_ok, _f = run(_d)
RESULTS.append(("OS-01", "An AI image cannot establish a CONFIRMED fact",
                "PASS" if (not _ok and "OR-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["space"]["ceiling_height"] = {
    "value": 2800, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "taken from OUT-009 mood.png", "recorded_on": TODAY,
    "unit": "mm"}
_d["outputs"] = [out_c()]
_ok, _f = run(_d)
RESULTS.append(("OS-02", "A fact sourced from a generated output is refused",
                "PASS" if (not _ok and "OR-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["space"]["ceiling_height"] = {
    "value": 2800, "status": "P", "source_type": "AI_IMAGE",
    "source_ref": "concept image suggests a high ceiling",
    "recorded_on": TODAY, "unit": "mm", "proposal_id": "P-002"}
_d["registers"]["proposals"] = [{"id": "P-002", "text": "high ceiling",
                                 "state": "OPEN", "raised_on": TODAY}]
_ok, _f = run(_d)
RESULTS.append(("OS-03", "An AI image may still inform a [P] proposal",
                "PASS" if "OR-008" not in errs(_f) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(), out_b(derived_from_output="OUT-001")]
_ok, _f = run(_d)
RESULTS.append(("OS-04", "Authority flowing master->A->B is legitimate",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_d = clean()
_d["outputs"] = [out_a(fingerprint=None)]
_ok, _f = run(_d)
RESULTS.append(("OS-05", "A binding output with no fingerprint is refused",
                "PASS" if (not _ok and "OR-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_before = copy.deepcopy(_d)
_d["outputs"] = [out_a(caption="TEST PROJECT — FINAL FOR CONSTRUCTION")]
_snapshot = copy.deepcopy(_d)
run(_d)
representation_report(_d)
RESULTS.append(("OS-06", "B8 never mutates the model (no auto-fix)",
                "PASS" if _d == _snapshot else "FAIL",
                f"unchanged={_d == _snapshot}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
_src = open(os.path.join(ROOT, "scripts", "validate_outputs.py"),
            encoding="utf-8").read()
_codes = sorted(set(re.findall(
    r'"(OR|XR|WT|FC|MV|DS|FM|UB|INV)-[0-9]+"', _src)))
RESULTS.append(("OI-01", "B8 emits only OR-* rule codes",
                "PASS" if _codes == ["OR"] else "FAIL", f"prefixes={_codes}"))

_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — FINAL FOR CONSTRUCTION")]
_a, _b1, _b6, _b7 = all_layers(_d)
_ok, _f = run(_d)
RESULTS.append(("OI-02", "A B8 error leaves A / B1 / B6 / B7 untouched",
                "PASS" if (_a and _b1 and _b6 and _b7 and not _ok) else "FAIL",
                f"A={_a} B1={_b1} B6={_b6} B7={_b7} B8={_ok}"))

_back = []
for _mod in ("schema_gate", "validate_refs", "validate_topology",
             "validate_furniture", "validate_movement", "validate_doors",
             "validate_formulas", "validate_blocking"):
    _txt = open(os.path.join(ROOT, "scripts", _mod + ".py"), encoding="utf-8").read()
    if "validate_outputs" in _txt:
        _back.append(_mod)
RESULTS.append(("OI-03", "No earlier layer imports B8",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

_tree = ast.parse(_src)
for _n in ast.walk(_tree):
    if isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Constant) \
            and isinstance(_n.value.value, str):
        _n.value.value = ""
_exec_src = ast.unparse(_tree).lower()
_bad = [t for t in ("clearance", "ergonom", "overlap", "footprint",
                    "swing_arc", "optimi", "tolerance", "mm_min")
        if t in _exec_src]
RESULTS.append(("OI-04", "B8 invents no geometric standard or tolerance",
                "PASS" if not _bad else "FAIL", f"terms={_bad}"))

RESULTS.append(("OI-05", "B8 consumes B7's uncertainty map, not its own",
                "PASS" if "build_uncertainty_map" in _exec_src else "FAIL",
                "delegates to B7"))

# B8 must not re-implement A's class<->guarantee rules (O1/O2/O3).
_d = clean()
_bad_out = out_a(binding_geometry=False)      # violates A's rule O1
_d["outputs"] = [_bad_out]
_a, _, _, _ = all_layers(_d)
_ok, _f = run(_d)
RESULTS.append(("OI-06", "class<->binding consistency stays A's rule",
                "PASS" if (not _a and "OR-001" not in errs(_f)) else "FAIL",
                f"A={_a} B8={errs(_f)}"))

# B8 must not re-implement B1's derived_from_output linkage (XR-014/015).
_d = clean()
_d["outputs"] = [out_b(derived_from_output="OUT-404")]
_a, _b1, _, _ = all_layers(_d)
_ok, _f = run(_d)
RESULTS.append(("OI-07", "Broken output lineage stays B1's rule (XR-014)",
                "PASS" if (not _b1 and not errs(_f)) else "FAIL",
                f"B1={_b1} B8={errs(_f)}"))


# ==========================================================================
# MUTATION — the suite must die when the engine is disabled
# ==========================================================================
_d = clean()
_d["outputs"] = [out_a(fingerprint=fingerprint(master_hash="0" * 64))]
RESULTS.append(("OM-01", "check_provenance alone detects a dead fingerprint",
                "PASS" if any(f.rule == "OR-003"
                              for f in check_provenance(_d)) else "FAIL",
                "isolated rule fires"))

_d = clean()
_d["space"]["orientation_north"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "not supplied", "recorded_on": TODAY, "blocking": False,
    "unknown_id": "U-310"}
_d["registers"]["unknowns"] = [{"id": "U-310", "question": "n?",
                                "blocking": False, "raised_on": TODAY}]
_d["outputs"] = [out_a()]
RESULTS.append(("OM-02", "check_certainty_claims alone blocks the claim",
                "PASS" if any(f.rule == "OR-001"
                              for f in check_certainty_claims(_d)) else "FAIL",
                "isolated rule fires"))

_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — FINAL FOR CONSTRUCTION")]
RESULTS.append(("OM-03", "check_authority_language alone fires",
                "PASS" if any(f.rule == "OR-006"
                              for f in check_authority_language(_d))
                else "FAIL", "isolated rule fires"))

_d = clean()
_d["space"]["ceiling_height"] = {
    "value": 2800, "status": "C", "source_type": "AI_IMAGE",
    "source_ref": "from the render", "recorded_on": TODAY, "unit": "mm"}
RESULTS.append(("OM-04", "check_reverse_contamination alone fires",
                "PASS" if any(f.rule == "OR-008"
                              for f in check_reverse_contamination(_d))
                else "FAIL", "isolated rule fires"))

# OM-05: flipping ONLY the class flips the verdict — nothing else changed.
_d = clean()
_d["space"]["orientation_north"] = {
    "value": None, "status": "U", "source_type": "NOT_PROVIDED",
    "source_ref": "not supplied", "recorded_on": TODAY, "blocking": False,
    "unknown_id": "U-320"}
_d["registers"]["unknowns"] = [{"id": "U-320", "question": "n?",
                                "blocking": False, "raised_on": TODAY}]
_hard = copy.deepcopy(_d)
_hard["outputs"] = [out_a()]
_soft = copy.deepcopy(_d)
_soft["outputs"] = [out_c()]
_hard_ok, _ = run(_hard)
_soft_ok, _ = run(_soft)
RESULTS.append(("OM-05", "Only the output class decides whether it blocks",
                "PASS" if (not _hard_ok and _soft_ok) else "FAIL",
                f"classA={_hard_ok} classC={_soft_ok}"))

# OM-06: flipping ONLY meta.status flips the authority-language verdict.
_d = clean()
_d["outputs"] = [out_a(caption="TEST PROJECT — final issue")]
_draft_ok, _ = run(_d)
_frozen = copy.deepcopy(_d)
_frozen["meta"]["status"] = "FROZEN"
_frozen["meta"]["frozen_on"] = "2026-09-13"
_frozen["meta"]["master_hash"] = H_MASTER
_frozen_ok, _ = run(_frozen)
RESULTS.append(("OM-06", "Only meta.status decides the finality claim",
                "PASS" if (not _draft_ok and _frozen_ok) else "FAIL",
                f"draft={_draft_ok} frozen={_frozen_ok}"))

# OM-07: flipping ONLY source_type flips reverse contamination.
_d = clean()
_ai = copy.deepcopy(_d)
_ai["space"]["ceiling_height"] = {
    "value": 2800, "status": "C", "source_type": "AI_IMAGE",
    "source_ref": "from the render", "recorded_on": TODAY, "unit": "mm"}
_client = copy.deepcopy(_d)
_client["space"]["ceiling_height"] = {
    "value": 2800, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client brief p.1", "recorded_on": TODAY, "unit": "mm"}
_ai_ok, _ = run(_ai)
_cl_ok, _ = run(_client)
RESULTS.append(("OM-07", "Only source_type decides contamination",
                "PASS" if (not _ai_ok and _cl_ok) else "FAIL",
                f"ai={_ai_ok} client={_cl_ok}"))

# OM-08: sweep — every representation defect must be detected.
_cases = [
    ("dead hash", out_a(fingerprint=fingerprint(positions_hash="0" * 64))),
    ("no fingerprint", out_a(fingerprint=None)),
    ("time paradox", out_a(generated_on="2019-01-01")),
    ("authority claim", out_a(caption="TEST PROJECT — for construction")),
]
_missed = [name for name, o in _cases
           if run({**clean(), "outputs": [o]})[0]]
RESULTS.append(("OM-08", "Representation-defect sweep: all detected",
                "PASS" if not _missed else "FAIL",
                f"{len(_cases) - len(_missed)}/{len(_cases)} caught"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B8 — OUTPUT / REPRESENTATION INTEGRITY TEST REPORT")
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
