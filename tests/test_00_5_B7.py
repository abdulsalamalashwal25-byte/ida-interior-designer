#!/usr/bin/env python3
"""Phase 00.5-B7 — Unknown / Blocking Integrity test suite.

Discipline (standing rule): every rule gets a POSITIVE and a NEGATIVE case,
the negative proves the INTENDED rule fired, and mutation tests prove the
suite dies when the engine is disabled.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import io
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from schema_gate import load_schema, validate_master                  # noqa: E402
from validate_refs import validate_references                         # noqa: E402
from validate_formulas import validate_formulas                       # noqa: E402
from validate_blocking import (                                       # noqa: E402
    validate_blocking, readiness_report, classify_unknowns,
    build_uncertainty_map, check_transitions, check_presence_semantics,
    check_propagation, check_readiness,
    IMPACT_BLOCKS_PROJECT, IMPACT_AFFECTS_OUTPUT, IMPACT_DECLARED_ONLY,
    IMPACT_OUT_OF_SCOPE)

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []

# --------------------------------------------------------------------------
# Fixture — reuse B6's validated BASE so B7 is tested against a file the
# earlier layers already accept. Importing it executes B6's report, so stdout
# is suppressed and its sys.exit is absorbed.
# --------------------------------------------------------------------------
_b6_src = open(os.path.join(HERE, "test_00_5_B6.py"), encoding="utf-8").read()
_b6 = {"__name__": "b6fixture",
       "__file__": os.path.join(HERE, "test_00_5_B6.py")}
try:
    with redirect_stdout(io.StringIO()):
        exec(compile(_b6_src, "test_00_5_B6.py", "exec"), _b6)
except SystemExit:
    pass

BASE = _b6["BASE"]
fact = _b6["fact"]
derived = _b6["derived"]

FINGERPRINT = {
    "project_id": "PRJ-94", "master_revision": "R01", "master_hash": "a" * 64,
    "geometry_version": "G-001", "element_set_hash": "b" * 64,
    "positions_hash": "c" * 64, "materials_hash": "d" * 64,
    "camera_id": "CAM-01", "camera_hash": "e" * 64,
}
CAMERAS = [{"id": "CAM-01", "pos": [0, 0, 1600], "target": [1000, 1000, 1200],
            "fov_deg": 60, "status": "C"}]


def binding_output():
    """A class-A output that asserts a deterministic geometric match."""
    return [{"output_id": "OUT-001", "file": "plan.dxf", "class": "A",
             "view_type": "PLAN",
             "guarantee": "DETERMINISTIC_GEOMETRIC_MATCH",
             "binding_geometry": True, "binding_visual": True,
             "fingerprint": FINGERPRINT, "generated_on": TODAY}]


def nonbinding_output():
    """A class-C output that explicitly guarantees nothing."""
    return [{"output_id": "OUT-009", "file": "mood.png", "class": "C",
             "view_type": "MOOD",
             "guarantee": "NOT_GEOMETRICALLY_GUARANTEED_NON_BINDING",
             "binding_geometry": False, "binding_visual": False,
             "fingerprint": FINGERPRINT, "generated_on": TODAY,
             "caption": "indicative only"}]


def unknown_entry(uid, blocking=False, resolved=None, question="open?"):
    e = {"id": uid, "question": question, "blocking": blocking,
         "raised_on": TODAY}
    if resolved:
        e["resolved_on"] = resolved
    return e


def u_fact(uid, blocking=False):
    return {"value": None, "status": "U", "source_type": "NOT_PROVIDED",
            "source_ref": "not supplied", "recorded_on": TODAY,
            "blocking": blocking, "unknown_id": uid}


def errs(findings):
    return sorted({f.rule for f in findings if f.severity == "ERROR"})


def run(d):
    return validate_blocking(d)


# ==========================================================================
# POSITIVE — a legitimate project must not be harassed
# ==========================================================================
# BP-01: the clean fixture raises no blocking error at all.
_d = copy.deepcopy(BASE)
_ok, _f = run(_d)
RESULTS.append(("BP-01", "A clean project produces no blocking error",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} errors={errs(_f)}"))

# BP-02: a declared, non-blocking, unconsumed UNKNOWN is NOT an error.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-050", blocking=False)]
_d["space"]["orientation_north"] = u_fact("U-050")
_ok, _f = run(_d)
RESULTS.append(("BP-02", "A declared non-blocking UNKNOWN is not an error",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} errors={errs(_f)}"))

# BP-03: UNKNOWN feeding only a NON-binding class-C output does not block.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = nonbinding_output()
_d["registers"]["unknowns"] = [unknown_entry("U-051")]
_d["space"]["orientation_north"] = u_fact("U-051")
_ok, _f = run(_d)
RESULTS.append(("BP-03", "UNKNOWN behind a non-binding class-C output is allowed",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} errors={errs(_f)}"))

# BP-04: a properly resolved unknown with a filled value verifies.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-052", resolved="2026-09-13")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client brief p.2", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-052"}
_ok, _f = run(_d)
RESULTS.append(("BP-04", "Resolved unknown + filled value is accepted",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} errors={errs(_f)}"))

# BP-05: the shipped template stays clean under B7.
import json                                                          # noqa: E402
_tpl = json.load(open(os.path.join(ROOT, "project_master.template.json"),
                      encoding="utf-8"))
_tpl = {k: v for k, v in _tpl.items() if not k.startswith("_")}
_ok, _f = run(_tpl)
RESULTS.append(("BP-05", "The shipped template raises no B7 error",
                "PASS" if _ok else "FAIL", f"ok={_ok} errors={errs(_f)}"))


# ==========================================================================
# STATE TRANSITIONS — UB-001 / UB-002
# ==========================================================================
# BT-01: UNKNOWN -> CONFIRMED while the register entry is still open.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-060")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "brief", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-060"}
_okA, _ = validate_master(_d, SCHEMA)
_okB1, _ = validate_references(_d)
_ok, _f = run(_d)
RESULTS.append(("BT-01", "UNKNOWN->CONFIRMED with the question still open",
                "PASS" if (not _ok and "UB-001" in errs(_f)) else "FAIL",
                f"A={_okA} B1={_okB1} B7={_ok} {errs(_f)}"))

# BT-02: the same promotion to [D] is equally refused.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-061")]
_d["space"]["floor_level"] = derived(
    2700, "ceiling_height - 100", ["space.ceiling_height"], unit="mm")
_d["space"]["floor_level"]["unknown_id"] = "U-061"
_ok, _f = run(_d)
RESULTS.append(("BT-02", "UNKNOWN->DERIVED with the question still open",
                "PASS" if (not _ok and "UB-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BT-03: register marked resolved while the value is still [U].
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-062", resolved="2026-09-13")]
_d["space"]["orientation_north"] = u_fact("U-062")
_ok, _f = run(_d)
RESULTS.append(("BT-03", "Unknown 'resolved' while the value is still [U]",
                "PASS" if (not _ok and "UB-002" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BT-04 NEGATIVE-OF-THE-NEGATIVE: it is UB-001 that fires, not a blanket
# refusal — the same file with the unknown resolved passes.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-063", resolved="2026-09-13")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "brief", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-063"}
_ok2, _f2 = run(_d)
RESULTS.append(("BT-04", "Same file passes once the unknown is truly resolved",
                "PASS" if (_ok2 and not errs(_f2)) else "FAIL",
                f"ok={_ok2} {errs(_f2)}"))

# BT-05: a fact with no unknown_id is not B7's business (that is XR-007/B1).
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-064")]
_ok, _f = run(_d)
RESULTS.append(("BT-05", "An unlinked register entry is not forced onto a fact",
                "PASS" if _ok else "FAIL", f"ok={_ok} {errs(_f)}"))


# ==========================================================================
# PRESENCE SEMANTICS — UB-003
# ==========================================================================
# BS-01: NOT_PRESENT asserted by an uncertain fact.
_d = copy.deepcopy(BASE)
_d["presence_register"]["columns"] = {
    "value": None, "status": "U", "presence": "NOT_PRESENT",
    "source_type": "NOT_PROVIDED", "source_ref": "x", "recorded_on": TODAY,
    "blocking": False, "unknown_id": "U-003"}
_d["registers"]["unknowns"] = [unknown_entry("U-003")]
_ok, _f = run(_d)
RESULTS.append(("BS-01", "UNKNOWN may not be re-labelled NOT_PRESENT",
                "PASS" if (not _ok and "UB-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BS-02: a confirmed NOT_PRESENT is perfectly legitimate.
_d = copy.deepcopy(BASE)
_ok, _f = run(_d)
RESULTS.append(("BS-02", "A confirmed NOT_PRESENT is accepted",
                "PASS" if _ok else "FAIL",
                f"presence={BASE['presence_register']['columns'].get('presence')}"))

# BS-03: [] is not treated as a confirmation of absence.
_d = copy.deepcopy(BASE)
_d["presence_register"]["columns"] = {
    "value": [], "status": "C", "presence": "PRESENT",
    "source_type": "CLIENT_INPUT", "source_ref": "brief",
    "recorded_on": TODAY}
_ok, _f = run(_d)
_info = [f for f in _f if f.rule == "UB-003" and f.severity == "INFO"]
RESULTS.append(("BS-03", "An empty list is neither presence nor absence",
                "PASS" if _info else "FAIL",
                f"info={len(_info)}"))

# BS-04: presence=UNKNOWN with no registered unknown is surfaced (WARN).
_d = copy.deepcopy(BASE)
_d["presence_register"]["columns"] = {
    "value": None, "status": "C", "presence": "UNKNOWN",
    "source_type": "CLIENT_INPUT", "source_ref": "brief",
    "recorded_on": TODAY}
_ok, _f = run(_d)
_warn = [f for f in _f if f.rule == "UB-003" and f.severity == "WARN"]
RESULTS.append(("BS-04", "An unregistered UNKNOWN presence is surfaced",
                "PASS" if _warn else "FAIL", f"warn={len(_warn)}"))


# ==========================================================================
# PROPAGATION — UB-004 / UB-005
# ==========================================================================
# BG-01: UNKNOWN -> derived -> binding output. The unknown must not vanish.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["registers"]["unknowns"] = [unknown_entry("U-070")]
_d["space"]["orientation_north"] = u_fact("U-070")
_d["space"]["floor_level"] = derived(
    10, "orientation_north * 1", ["space.orientation_north"], unit="mm")
_ok, _f = run(_d)
RESULTS.append(("BG-01", "UNKNOWN cannot vanish along the chain to an output",
                "PASS" if (not _ok and "UB-004" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BG-02: UNCOMPUTABLE [D] reaching a binding output.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["space"]["floor_level"] = derived(
    7777, "ceiling_height / 0", ["space.ceiling_height"], unit="mm")
_ok6, _f6, _v6 = validate_formulas(_d)
_ok, _f = run(_d)
RESULTS.append(("BG-02", "UNCOMPUTABLE must not reach a binding output",
                "PASS" if (not _ok and "UB-005" in errs(_f)) else "FAIL",
                f"B6={list(_v6.values())} B7={errs(_f)}"))

# BG-03: laundering through TWO intermediate derived hops still blocks.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["registers"]["unknowns"] = [unknown_entry("U-071")]
_d["space"]["orientation_north"] = u_fact("U-071")
_d["space"]["floor_level"] = derived(
    1, "orientation_north * 1", ["space.orientation_north"], unit="mm")
_d["space"]["ceiling_height"] = derived(
    2, "floor_level * 2", ["space.floor_level"], unit="mm")
_ok, _f = run(_d)
_map = build_uncertainty_map(_d)
RESULTS.append(("BG-03", "Uncertainty survives two derivation hops",
                "PASS" if (not _ok and "space/ceiling_height" in _map)
                else "FAIL",
                f"tainted={sorted(_map)[:3]}"))

# BG-04: the same UNKNOWN with NO binding output is INFO, not an error.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-072")]
_d["space"]["orientation_north"] = u_fact("U-072")
_ok, _f = run(_d)
_info = [f for f in _f if f.rule == "UB-006" and f.severity == "INFO"]
RESULTS.append(("BG-04", "Same unknown without a binding output only informs",
                "PASS" if (_ok and _info) else "FAIL",
                f"ok={_ok} info={len(_info)}"))

# BG-05: B7 reads B6's verdict rather than recomputing arithmetic.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["space"]["floor_level"] = derived(
    9999, "ceiling_height - 100", ["space.ceiling_height"], unit="mm")
_ok, _f = run(_d)
_mismatch_claimed = [f for f in _f if "MISMATCH" in f.message.upper()]
RESULTS.append(("BG-05", "A wrong-but-computable value is B6's, not B7's",
                "PASS" if not _mismatch_claimed else "FAIL",
                f"b7_errors={errs(_f)}"))


# ==========================================================================
# DEPENDENCY-AWARE CLASSIFICATION — UB-006
# ==========================================================================
# BC-01: a declared blocking unknown is BLOCKS_PROJECT.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-080", blocking=True)]
_cls = classify_unknowns(_d)
RESULTS.append(("BC-01", "A blocking unknown is classified BLOCKS_PROJECT",
                "PASS" if _cls.get("U-080") == IMPACT_BLOCKS_PROJECT else "FAIL",
                f"{_cls}"))

# BC-02: a cited non-blocking unknown with a binding output AFFECTS_OUTPUT.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["registers"]["unknowns"] = [unknown_entry("U-081")]
_d["space"]["orientation_north"] = u_fact("U-081")
_cls = classify_unknowns(_d)
RESULTS.append(("BC-02", "A cited unknown feeding an output AFFECTS_OUTPUT",
                "PASS" if _cls.get("U-081") == IMPACT_AFFECTS_OUTPUT else "FAIL",
                f"{_cls}"))

# BC-03: cited but nothing binding -> DECLARED_ONLY.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-082")]
_d["space"]["orientation_north"] = u_fact("U-082")
_cls = classify_unknowns(_d)
RESULTS.append(("BC-03", "A cited unknown with no binding output is DECLARED_ONLY",
                "PASS" if _cls.get("U-082") == IMPACT_DECLARED_ONLY else "FAIL",
                f"{_cls}"))

# BC-04: registered but referenced by nothing -> OUT_OF_SCOPE.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-083")]
_cls = classify_unknowns(_d)
RESULTS.append(("BC-04", "An unreferenced unknown is OUT_OF_SCOPE",
                "PASS" if _cls.get("U-083") == IMPACT_OUT_OF_SCOPE else "FAIL",
                f"{_cls}"))

# BC-05: the four impacts are genuinely distinct — "UNKNOWN = ERROR" is not
# the policy.
RESULTS.append(("BC-05", "Four distinct impact levels exist, not one",
                "PASS" if len({IMPACT_BLOCKS_PROJECT, IMPACT_AFFECTS_OUTPUT,
                               IMPACT_DECLARED_ONLY,
                               IMPACT_OUT_OF_SCOPE}) == 4 else "FAIL",
                "4 levels"))

# BC-06: a resolved unknown is classified at all no longer.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-084", resolved="2026-09-13")]
_cls = classify_unknowns(_d)
RESULTS.append(("BC-06", "A resolved unknown no longer carries an impact",
                "PASS" if "U-084" not in _cls else "FAIL", f"{_cls}"))


# ==========================================================================
# READINESS / APPROVAL — UB-007 / UB-008 / UB-009
# ==========================================================================
# BR-01: a blocking unknown prevents final approval.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-090", blocking=True)]
_rep = readiness_report(_d)
RESULTS.append(("BR-01", "A blocking UNKNOWN prevents final approval",
                "PASS" if not _rep["ready_for_final_approval"] else "FAIL",
                f"blockers={len(_rep['declared_blockers_from_A'])}"))

# BR-02: an UNCOMPUTABLE blocking dependency prevents approval.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["space"]["floor_level"] = derived(
    1, "ceiling_height / 0", ["space.ceiling_height"], unit="mm")
_rep = readiness_report(_d)
RESULTS.append(("BR-02", "An UNCOMPUTABLE dependency prevents approval",
                "PASS" if (not _rep["ready_for_final_approval"]
                           and _rep["b7_integrity_errors"]) else "FAIL",
                f"{_rep['b7_integrity_errors'][:2]}"))

# BR-03: FROZEN while blockers remain open.
_d = copy.deepcopy(BASE)
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = "f" * 64
_d["registers"]["unknowns"] = [unknown_entry("U-091", blocking=True)]
_ok, _f = run(_d)
RESULTS.append(("BR-03", "FROZEN with open blockers is refused",
                "PASS" if (not _ok and "UB-007" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BR-04: B7 DELEGATES the declared blocker list to A (UB-009), never restates
# it — the report must carry A's own blockers verbatim.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry(
    "U-092", blocking=True, question="is there a beam?")]
_rep = readiness_report(_d)
RESULTS.append(("BR-04", "B7 reuses A's blocker list instead of duplicating it",
                "PASS" if any("U-092" in b
                              for b in _rep["declared_blockers_from_A"])
                else "FAIL", f"{_rep['declared_blockers_from_A'][:1]}"))

# BR-05: no blocking condition -> readiness is not vetoed BY B7. A may still
# veto for its own governance reasons (GAP-02), which is A's right.
_d = copy.deepcopy(BASE)
_ok, _f = run(_d)
_rep = readiness_report(_d)
RESULTS.append(("BR-05", "With no blocking condition B7 adds no veto",
                "PASS" if (_ok and not _rep["b7_integrity_errors"]) else "FAIL",
                f"b7_errors={_rep['b7_integrity_errors']}"))

# BR-06: a decision linked to an uncertain element.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-093")]
_d["space"]["orientation_north"] = u_fact("U-093")
_d["registers"]["decisions"] = [{
    "decision_id": "DEC-001", "title": "orient the layout",
    "linked_proposal": "P-001", "rationale": "because the north is known",
    "alternatives_considered": ["a", "b"], "approved_by": "USER",
    "approved_on": TODAY, "approved_in_revision": "R01",
    "linked_elements": ["space.orientation_north"]}]
_ok, _f = run(_d)
RESULTS.append(("BR-06", "A decision resting on an UNKNOWN is flagged",
                "PASS" if (not _ok and "UB-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# ANTI-SMUGGLING
# ==========================================================================
# BX-01: deleting the source to hide an unknown.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-100")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "brief", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-100"}
_ok, _f = run(_d)
RESULTS.append(("BX-01", "Rewriting a [U] as [C] does not launder it",
                "PASS" if (not _ok and "UB-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BX-02: substituting a default value for an unknown.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-101")]
_d["space"]["orientation_north"] = {
    "value": 0, "status": "C", "source_type": "AGENT_ASSUMPTION",
    "source_ref": "assumed default", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-101"}
_ok, _f = run(_d)
RESULTS.append(("BX-02", "A default value cannot stand in for an UNKNOWN",
                "PASS" if (not _ok and "UB-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BX-03: null re-labelled NOT_PRESENT without a basis.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-102")]
_d["presence_register"]["services"] = {
    "value": None, "status": "U", "presence": "NOT_PRESENT",
    "source_type": "NOT_PROVIDED", "source_ref": "x", "recorded_on": TODAY,
    "blocking": False, "unknown_id": "U-102"}
_ok, _f = run(_d)
RESULTS.append(("BX-03", "null cannot become NOT_PRESENT without a basis",
                "PASS" if (not _ok and "UB-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

# BX-04: hiding a blocking dependency behind an intermediate derived value.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["registers"]["unknowns"] = [unknown_entry("U-103", blocking=True)]
_d["space"]["orientation_north"] = u_fact("U-103", blocking=True)
_d["space"]["floor_level"] = derived(
    5, "orientation_north + 5", ["space.orientation_north"], unit="mm")
_ok, _f = run(_d)
_rep = readiness_report(_d)
RESULTS.append(("BX-04", "A blocking dependency cannot hide behind a [D]",
                "PASS" if (not _ok
                           and not _rep["ready_for_final_approval"]) else "FAIL",
                f"{errs(_f)}"))

# BX-05: B7 changes nothing — no auto-fix anywhere.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-104")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "brief", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-104"}
_before = copy.deepcopy(_d)
run(_d)
readiness_report(_d)
classify_unknowns(_d)
RESULTS.append(("BX-05", "B7 never mutates the model (no auto-fix)",
                "PASS" if _d == _before else "FAIL",
                f"unchanged={_d == _before}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
# BI-01: B7 emits only UB-* codes.
_src = open(os.path.join(ROOT, "scripts", "validate_blocking.py"),
            encoding="utf-8").read()
import re                                                            # noqa: E402
_codes = sorted(set(re.findall(r'"(UB|XR|WT|FC|MV|DS|FM|INV)-[0-9]+"', _src)))
RESULTS.append(("BI-01", "B7 emits only UB-* rule codes",
                "PASS" if _codes == ["UB"] else "FAIL", f"prefixes={_codes}"))

# BI-02: a B7 failure disturbs no earlier layer.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-110")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "brief", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-110"}
_a, _ = validate_master(_d, SCHEMA)
_b1, _ = validate_references(_d)
_b6, _, _ = validate_formulas(_d)
_b7, _ = run(_d)
RESULTS.append(("BI-02", "A B7 error leaves A / B1 / B6 untouched",
                "PASS" if (_a and _b1 and _b6 and not _b7) else "FAIL",
                f"A={_a} B1={_b1} B6={_b6} B7={_b7}"))

# BI-03: no earlier layer imports B7 (dependency stays one-way).
_back = []
for _mod in ("schema_gate", "validate_refs", "validate_topology",
             "validate_furniture", "validate_movement", "validate_doors",
             "validate_formulas"):
    _txt = open(os.path.join(ROOT, "scripts", _mod + ".py"),
                encoding="utf-8").read()
    if "validate_blocking" in _txt:
        _back.append(_mod)
RESULTS.append(("BI-03", "No earlier layer imports B7",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

# BI-04: B7 contains no geometry and no design vocabulary.
import ast                                                           # noqa: E402
_tree = ast.parse(_src)
for _n in ast.walk(_tree):
    if isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Constant) \
            and isinstance(_n.value.value, str):
        _n.value.value = ""
_exec_src = ast.unparse(_tree).lower()
_bad = [t for t in ("clearance", "ergonom", "overlap", "footprint",
                    "swing_arc", "optimi", "aesthetic", "recommended")
        if t in _exec_src]
RESULTS.append(("BI-04", "B7 holds no geometry, standards or design opinion",
                "PASS" if not _bad else "FAIL", f"terms={_bad}"))

# BI-05: B7 does not recompute arithmetic — it imports B6's verdict.
RESULTS.append(("BI-05", "B7 consumes B6's verdict instead of recomputing",
                "PASS" if ("validate_formulas" in _exec_src
                           and "ast.parse" not in _exec_src) else "FAIL",
                "delegates to B6"))

# BI-06: B7 delegates the declared blocker list to A.
RESULTS.append(("BI-06", "B7 calls A's final_approval_readiness",
                "PASS" if "final_approval_readiness" in _exec_src else "FAIL",
                "delegates to A"))


# ==========================================================================
# MUTATION — the suite must die when the engine is disabled
# ==========================================================================
# BM-01: transition guard.
_d = copy.deepcopy(BASE)
_d["registers"]["unknowns"] = [unknown_entry("U-120")]
_d["space"]["orientation_north"] = {
    "value": 90, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "brief", "recorded_on": TODAY, "unit": "deg",
    "unknown_id": "U-120"}
RESULTS.append(("BM-01", "check_transitions alone detects the promotion",
                "PASS" if any(f.rule == "UB-001"
                              for f in check_transitions(_d)) else "FAIL",
                "isolated rule fires"))

# BM-02: propagation guard, in isolation.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["outputs"] = binding_output()
_d["registers"]["unknowns"] = [unknown_entry("U-121")]
_d["space"]["orientation_north"] = u_fact("U-121")
RESULTS.append(("BM-02", "check_propagation alone blocks the binding output",
                "PASS" if any(f.severity == "ERROR"
                              for f in check_propagation(_d)) else "FAIL",
                "isolated rule fires"))

# BM-03: presence guard, in isolation.
_d = copy.deepcopy(BASE)
_d["presence_register"]["columns"] = {
    "value": None, "status": "U", "presence": "NOT_PRESENT",
    "source_type": "NOT_PROVIDED", "source_ref": "x",
    "recorded_on": TODAY, "blocking": False}
RESULTS.append(("BM-03", "check_presence_semantics alone fires",
                "PASS" if any(f.rule == "UB-003"
                              for f in check_presence_semantics(_d))
                else "FAIL", "isolated rule fires"))

# BM-04: readiness gate, in isolation.
_d = copy.deepcopy(BASE)
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = "f" * 64
_d["registers"]["unknowns"] = [unknown_entry("U-122", blocking=True)]
_rf, _rready, _rbl = check_readiness(_d)
RESULTS.append(("BM-04", "check_readiness alone refuses a false FROZEN",
                "PASS" if (any(f.rule == "UB-007" for f in _rf)
                           and not _rready) else "FAIL",
                f"ready={_rready}"))

# BM-05: flipping ONE field flips the verdict, nothing else changed.
_base_case = copy.deepcopy(BASE)
_base_case["registers"]["unknowns"] = [unknown_entry("U-123")]
_base_case["space"]["orientation_north"] = u_fact("U-123")
_clean_ok, _ = run(_base_case)
_mutated = copy.deepcopy(_base_case)
_mutated["space"]["orientation_north"]["status"] = "C"
_mutated["space"]["orientation_north"]["value"] = 90
_mut_ok, _mut_f = run(_mutated)
RESULTS.append(("BM-05", "Flipping only status [U]->[C] flips the verdict",
                "PASS" if (_clean_ok and not _mut_ok) else "FAIL",
                f"clean={_clean_ok} mutated={_mut_ok} {errs(_mut_f)}"))

# BM-06: flipping ONLY the output's binding flag changes the outcome.
_d = copy.deepcopy(BASE)
_d["cameras"] = CAMERAS
_d["registers"]["unknowns"] = [unknown_entry("U-124")]
_d["space"]["orientation_north"] = u_fact("U-124")
_d["outputs"] = nonbinding_output()
_soft_ok, _ = run(_d)
_d2 = copy.deepcopy(_d)
_d2["outputs"] = binding_output()
_hard_ok, _hard_f = run(_d2)
RESULTS.append(("BM-06", "Only the binding flag decides blocking",
                "PASS" if (_soft_ok and not _hard_ok) else "FAIL",
                f"nonbinding={_soft_ok} binding={_hard_ok}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B7 — UNKNOWN / BLOCKING INTEGRITY TEST REPORT")
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
