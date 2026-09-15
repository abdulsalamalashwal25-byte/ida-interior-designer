#!/usr/bin/env python3
"""Phase 00.5-B10 — Register Lifecycle / Decision-State Integrity tests.

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
from validate_outputs import validate_outputs                      # noqa: E402
from validate_revisions import validate_revisions                  # noqa: E402
from validate_lifecycle import (                                   # noqa: E402
    validate_lifecycle, lifecycle_report, check_proposal_decision,
    check_objections, check_change_requests, check_fact_register_drift)

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []

# --------------------------------------------------------------------------
# Fixture — reuse B9's clean() + a valid changelog, so the file is already
# accepted by A/B1/B6/B7/B8/B9 and any finding here is unambiguously B10's.
# --------------------------------------------------------------------------
_b9_src = open(os.path.join(HERE, "test_00_5_B9.py"), encoding="utf-8").read()
_b9 = {"__name__": "b9fixture",
       "__file__": os.path.join(HERE, "test_00_5_B9.py")}
try:
    with redirect_stdout(io.StringIO()):
        exec(compile(_b9_src, "test_00_5_B9.py", "exec"), _b9)
except SystemExit:
    pass

_clean = _b9["clean"]
_initial = _b9["initial"]


def base():
    d = _clean()
    d["registers"]["changelog"] = [_initial()]
    return d


def prop(pid="P-001", state="APPROVED", **over):
    p = {"id": pid, "text": "a proposal about the furniture layout",
         "state": state, "raised_on": TODAY}
    p.update(over)
    return p


def dec(did="DEC-001", linked="P-001", **over):
    d = {"decision_id": did, "title": "layout decision",
         "linked_proposal": linked,
         "rationale": "the client approved this option in the meeting",
         "alternatives_considered": ["option a", "option b"],
         "approved_by": "USER", "approved_on": TODAY,
         "approved_in_revision": "R01"}
    d.update(over)
    return d


def obj(oid="OBJ-001", target="DEC-001", state="OPEN", **over):
    o = {"id": oid, "decision_under_objection": target,
         "problem": "this blocks the main corridor",
         "impact": "circulation width drops below the agreed value",
         "alternative": "shift the unit by 200mm", "state": state,
         "raised_on": TODAY}
    o.update(over)
    return o


def cr(cid="CR-001", state="APPROVED", **over):
    c = {"id": cid, "target_element": "space.ceiling_height",
         "current_value": "2800", "proposed_value": "3000",
         "reason": "the client wants a higher ceiling",
         "impact": "affects all sections and elevations",
         "classification": "MAJOR", "state": state, "raised_on": TODAY}
    c.update(over)
    return c


def cr_log(cid="CR-001", date=TODAY):
    return {"revision": "R01", "date": date, "type": "CR_APPLIED",
            "summary": f"applied change request {cid}", "cr_id": cid}


def assumption(aid="A-001", state="APPROVED"):
    return {"id": aid, "text": "assumed slab thickness of 200mm",
            "impact": "affects the finished ceiling height",
            "approval_state": state, "raised_on": TODAY}


def errs(findings):
    return sorted({f.rule for f in findings if f.severity == "ERROR"})


def run(d):
    return validate_lifecycle(d)


def all_layers(d):
    return (validate_master(d, SCHEMA)[0], validate_references(d)[0],
            validate_formulas(d)[0], validate_blocking(d)[0],
            validate_outputs(d)[0], validate_revisions(d)[0])


# ==========================================================================
# POSITIVE
# ==========================================================================
_d = base()
_ok, _f = run(_d)
RESULTS.append(("LP-01", "A project with empty registers is legitimate",
                "PASS" if (_ok and not _f) else "FAIL", f"ok={_ok}"))

_d = base()
_d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("LP-02", "APPROVED proposal + its decision passes every layer",
                "PASS" if (_ok and all(_layers)) else "FAIL",
                f"B10={_ok} layers={_layers}"))

_d = base()
_d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec(user_override_of="OBJ-001")]
_d["registers"]["objections"] = [obj(state="USER_OVERRIDE")]
_ok, _f = run(_d)
RESULTS.append(("LP-03", "A properly recorded user override passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_d = base()
_d["registers"]["change_requests"] = [cr(state="APPLIED",
                                         approved_on=TODAY,
                                         applied_in_revision="R01")]
_d["registers"]["changelog"] = [_initial(), cr_log()]
_ok, _f = run(_d)
RESULTS.append(("LP-04", "An APPLIED CR with a matching changelog passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_d = base()
_d["registers"]["objections"] = [obj(state="WITHDRAWN")]
_ok, _f = run(_d)
RESULTS.append(("LP-05", "A withdrawn objection blocks nothing",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_tpl = json.load(open(os.path.join(ROOT, "project_master.template.json"),
                      encoding="utf-8"))
_tpl = {k: v for k, v in _tpl.items() if not k.startswith("_")}
_ok, _f = run(_tpl)
RESULTS.append(("LP-06", "The shipped template raises no B10 error",
                "PASS" if _ok else "FAIL", f"ok={_ok} {errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="OPEN")]
_rep = lifecycle_report(_d)
RESULTS.append(("LP-07", "The lifecycle report describes the real states",
                "PASS" if _rep["proposals"] == ["OPEN"] else "FAIL", f"{_rep}"))


# ==========================================================================
# NEGATIVE — RL-001 / RL-002
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("LN-01", "A decision on a REJECTED proposal is caught",
                "PASS" if (not _ok and "RL-001" in errs(_f)
                           and all(_layers)) else "FAIL",
                f"layers={_layers} B10={errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="SUPERSEDED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_ok, _f = run(_d)
RESULTS.append(("LN-02", "A decision on a SUPERSEDED proposal is caught",
                "PASS" if (not _ok and "RL-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="OPEN", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_ok, _f = run(_d)
RESULTS.append(("LN-03", "A decision taken before its proposal closed",
                "PASS" if (not _ok and "RL-002" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="APPROVED")]
_ok, _f = run(_d)
_warn = [x for x in _f if x.rule == "RL-002" and x.severity == "WARN"]
RESULTS.append(("LN-04", "An APPROVED proposal with no decision is surfaced",
                "PASS" if _warn else "FAIL", f"warn={len(_warn)}"))


# ==========================================================================
# NEGATIVE — RL-003 / RL-004
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_d["registers"]["objections"] = [obj(state="OPEN")]
_ok, _f = run(_d)
RESULTS.append(("LN-05", "An OPEN objection against a standing decision",
                "PASS" if (not _ok and "RL-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_d["registers"]["objections"] = [obj(state="USER_OVERRIDE")]
_ok, _f = run(_d)
RESULTS.append(("LN-06", "USER_OVERRIDE with no decision recording it",
                "PASS" if (not _ok and "RL-004" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_d["registers"]["objections"] = [obj(state="ACCEPTED")]
_ok, _f = run(_d)
RESULTS.append(("LN-07", "An ACCEPTED objection is not treated as open",
                "PASS" if "RL-003" not in errs(_f) else "FAIL", f"{errs(_f)}"))


# ==========================================================================
# NEGATIVE — RL-005 / RL-006
# ==========================================================================
for _state in ("DRAFT", "PENDING_APPROVAL", "REJECTED", "DEFERRED"):
    _d = base()
    _d["registers"]["change_requests"] = [cr(state=_state)]
    _d["registers"]["changelog"] = [_initial(), cr_log()]
    _ok, _f = run(_d)
    RESULTS.append((f"LN-08{_state[:2]}",
                    f"A {_state} CR recorded as applied is caught",
                    "PASS" if (not _ok and "RL-005" in errs(_f)) else "FAIL",
                    f"{errs(_f)}"))

_d = base()
_d["registers"]["change_requests"] = [cr(state="APPLIED", approved_on=TODAY,
                                         applied_in_revision="R01")]
_ok, _f = run(_d)
RESULTS.append(("LN-09", "An APPLIED CR with no changelog event is caught",
                "PASS" if (not _ok and "RL-006" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["change_requests"] = [cr(state="REJECTED",
                                         applied_in_revision="R01")]
_ok, _f = run(_d)
RESULTS.append(("LN-10", "A REJECTED CR claiming a revision is caught",
                "PASS" if (not _ok and "RL-006" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# NEGATIVE — RL-007 / RL-008 (fact vs register drift)
# ==========================================================================
_d = base()
_d["registers"]["assumptions"] = [assumption(state="REJECTED")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "A", "source_type": "AGENT_ASSUMPTION",
    "source_ref": "assumed slab thickness", "recorded_on": TODAY,
    "unit": "mm", "assumption_id": "A-001", "approval_state": "APPROVED",
    "impact": "affects the finished floor level"}
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("LN-11", "A fact claiming an approval its register denies",
                "PASS" if (not _ok and "RL-007" in errs(_f)
                           and all(_layers)) else "FAIL",
                f"layers={_layers} B10={errs(_f)}"))

_d = base()
_d["registers"]["assumptions"] = [assumption(state="REJECTED")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client brief p.3", "recorded_on": TODAY, "unit": "mm",
    "assumption_id": "A-001"}
_ok, _f = run(_d)
RESULTS.append(("LN-12", "A REJECTED assumption still feeding live data",
                "PASS" if (not _ok and "RL-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "client brief p.3", "recorded_on": TODAY, "unit": "mm",
    "proposal_id": "P-001"}
_ok, _f = run(_d)
RESULTS.append(("LN-13", "A REJECTED proposal persisting as confirmed data",
                "PASS" if (not _ok and "RL-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# BOUNDARY
# ==========================================================================
_d = base()
_d["registers"]["assumptions"] = [assumption(state="APPROVED")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "A", "source_type": "AGENT_ASSUMPTION",
    "source_ref": "assumed slab thickness", "recorded_on": TODAY,
    "unit": "mm", "assumption_id": "A-001", "approval_state": "APPROVED",
    "impact": "affects the finished floor level"}
_ok, _f = run(_d)
RESULTS.append(("LB-01", "Matching approval states raise nothing",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

# A fact with no approval_state of its own is UNSPECIFIED, not a conflict.
_d = base()
_d["registers"]["assumptions"] = [assumption(state="PENDING_APPROVAL")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "A", "source_type": "AGENT_ASSUMPTION",
    "source_ref": "assumed slab thickness", "recorded_on": TODAY,
    "unit": "mm", "assumption_id": "A-001",
    "impact": "affects the finished floor level",
    "approval_state": "PENDING_APPROVAL"}
_ok, _f = run(_d)
RESULTS.append(("LB-02", "A pending assumption is not a drift",
                "PASS" if "RL-007" not in errs(_f) else "FAIL", f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED")]
_ok, _f = run(_d)
RESULTS.append(("LB-03", "A rejected proposal with no decision is fine",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_d = base()
_d["registers"]["change_requests"] = [cr(state="DEFERRED")]
_ok, _f = run(_d)
RESULTS.append(("LB-04", "A DEFERRED CR that was never applied is fine",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))


# ==========================================================================
# ANTI-SMUGGLING
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_ok, _f = run(_d)
RESULTS.append(("LX-01", "A rejected option cannot be resurrected by decision",
                "PASS" if (not _ok and "RL-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["change_requests"] = [cr(state="REJECTED")]
_d["registers"]["changelog"] = [_initial(), cr_log()]
_ok, _f = run(_d)
RESULTS.append(("LX-02", "A rejected CR cannot slip in via the changelog",
                "PASS" if (not _ok and "RL-005" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_d["registers"]["objections"] = [obj(state="OPEN")]
_ok, _f = run(_d)
RESULTS.append(("LX-03", "An objection cannot be silently ignored",
                "PASS" if (not _ok and "RL-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["assumptions"] = [assumption(state="REJECTED")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "D", "source_type": "DERIVED_CALC",
    "source_ref": "computed from declared inputs", "recorded_on": TODAY,
    "unit": "mm", "assumption_id": "A-001",
    "derived_from": ["space.ceiling_height"],
    "formula": "ceiling_height - 2600", "derivation_type": "ARITHMETIC"}
_ok, _f = run(_d)
RESULTS.append(("LX-04", "A rejected assumption cannot hide behind a [D]",
                "PASS" if (not _ok and "RL-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_before = copy.deepcopy(_d)
run(_d)
lifecycle_report(_d)
RESULTS.append(("LX-05", "B10 never mutates the model (no auto-fix)",
                "PASS" if _d == _before else "FAIL",
                f"unchanged={_d == _before}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
_src = open(os.path.join(ROOT, "scripts", "validate_lifecycle.py"),
            encoding="utf-8").read()
_codes = sorted(set(re.findall(
    r'"(RL|XR|WT|FC|MV|DS|FM|UB|OR|RT|INV)-[0-9]+"', _src)))
RESULTS.append(("LI-01", "B10 emits only RL-* rule codes",
                "PASS" if _codes == ["RL"] else "FAIL", f"prefixes={_codes}"))

_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
_layers = all_layers(_d)
_ok, _f = run(_d)
RESULTS.append(("LI-02", "A B10 error leaves A/B1/B6/B7/B8/B9 untouched",
                "PASS" if (all(_layers) and not _ok) else "FAIL",
                f"layers={_layers} B10={_ok}"))

_back = []
for _mod in ("schema_gate", "validate_refs", "validate_topology",
             "validate_furniture", "validate_movement", "validate_doors",
             "validate_formulas", "validate_blocking", "validate_outputs",
             "validate_revisions"):
    _txt = open(os.path.join(ROOT, "scripts", _mod + ".py"),
                encoding="utf-8").read()
    if "validate_lifecycle" in _txt:
        _back.append(_mod)
RESULTS.append(("LI-03", "No earlier layer imports B10",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

_tree = ast.parse(_src)
for _n in ast.walk(_tree):
    if isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Constant) \
            and isinstance(_n.value.value, str):
        _n.value.value = ""
_exec_src = ast.unparse(_tree).lower()
_bad = [t for t in ("clearance", "ergonom", "overlap", "footprint",
                    "swing", "optimi", "tolerance", "fingerprint",
                    "geometry_version")
        if t in _exec_src]
RESULTS.append(("LI-04", "B10 holds no geometry, tolerance or other layer's field",
                "PASS" if not _bad else "FAIL", f"terms={_bad}"))

# Link EXISTENCE stays B1's rule XR-010/011 — B10 must stay silent.
_d = base()
_d["registers"]["decisions"] = [dec(linked="P-404")]
_b1 = validate_references(_d)[0]
_ok, _f = run(_d)
RESULTS.append(("LI-05", "A dangling linked_proposal stays B1's rule",
                "PASS" if (not _b1 and _ok) else "FAIL",
                f"B1={_b1} B10={_ok} {errs(_f)}"))

# Changelog coherence stays B9's rule — B10 must not re-report it.
_d = base()
_d["meta"]["revision"] = "R07"
_b9 = validate_revisions(_d)[0]
_ok, _f = run(_d)
RESULTS.append(("LI-06", "Changelog/revision coherence stays B9's rule",
                "PASS" if (not _b9 and _ok) else "FAIL",
                f"B9={_b9} B10={_ok}"))

# Entry SHAPE stays A's rule.
_d = base()
_d["registers"]["proposals"] = [{"id": "P-001", "state": "APPROVED",
                                 "raised_on": TODAY}]      # 'text' missing
_a = validate_master(_d, SCHEMA)[0]
RESULTS.append(("LI-07", "Entry shape stays A's rule",
                "PASS" if not _a else "FAIL", f"A={_a}"))


# ==========================================================================
# MUTATION
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec()]
RESULTS.append(("LM-01", "check_proposal_decision alone fires",
                "PASS" if any(f.rule == "RL-001"
                              for f in check_proposal_decision(_d))
                else "FAIL", "isolated rule fires"))

_d = base()
_d["registers"]["decisions"] = [dec()]
_d["registers"]["objections"] = [obj(state="OPEN")]
RESULTS.append(("LM-02", "check_objections alone fires",
                "PASS" if any(f.rule == "RL-003"
                              for f in check_objections(_d)) else "FAIL",
                "isolated rule fires"))

_d = base()
_d["registers"]["change_requests"] = [cr(state="REJECTED")]
_d["registers"]["changelog"] = [_initial(), cr_log()]
RESULTS.append(("LM-03", "check_change_requests alone fires",
                "PASS" if any(f.rule == "RL-005"
                              for f in check_change_requests(_d)) else "FAIL",
                "isolated rule fires"))

_d = base()
_d["registers"]["assumptions"] = [assumption(state="REJECTED")]
_d["space"]["floor_level"] = {
    "value": 200, "status": "A", "source_type": "AGENT_ASSUMPTION",
    "source_ref": "assumed slab", "recorded_on": TODAY, "unit": "mm",
    "assumption_id": "A-001", "approval_state": "APPROVED",
    "impact": "affects levels"}
RESULTS.append(("LM-04", "check_fact_register_drift alone fires",
                "PASS" if any(f.rule == "RL-007"
                              for f in check_fact_register_drift(_d))
                else "FAIL", "isolated rule fires"))

# LM-05: flipping ONLY the proposal state flips the verdict.
_good = base()
_good["registers"]["proposals"] = [prop(state="APPROVED", decision_id="DEC-001")]
_good["registers"]["decisions"] = [dec()]
_bad = copy.deepcopy(_good)
_bad["registers"]["proposals"][0]["state"] = "REJECTED"
RESULTS.append(("LM-05", "Flipping only the proposal state flips the verdict",
                "PASS" if (run(_good)[0] and not run(_bad)[0]) else "FAIL",
                f"approved={run(_good)[0]} rejected={run(_bad)[0]}"))

# LM-06: flipping ONLY the objection state flips the verdict.
_ok_case = base()
_ok_case["registers"]["proposals"] = [prop(decision_id="DEC-001")]
_ok_case["registers"]["decisions"] = [dec()]
_ok_case["registers"]["objections"] = [obj(state="WITHDRAWN")]
_bad_case = copy.deepcopy(_ok_case)
_bad_case["registers"]["objections"][0]["state"] = "OPEN"
RESULTS.append(("LM-06", "Only the objection state decides blocking",
                "PASS" if (run(_ok_case)[0] and not run(_bad_case)[0])
                else "FAIL",
                f"withdrawn={run(_ok_case)[0]} open={run(_bad_case)[0]}"))

# LM-07: sweep — every lifecycle defect must be detected.
def _sweep_case(mod):
    d = base()
    d["registers"]["proposals"] = [prop(decision_id="DEC-001")]
    d["registers"]["decisions"] = [dec()]
    mod(d)
    return run(d)[0]


_sweep = [
    lambda d: d["registers"]["proposals"][0].update({"state": "REJECTED"}),
    lambda d: d["registers"]["proposals"][0].update({"state": "SUPERSEDED"}),
    lambda d: d["registers"]["proposals"][0].update({"state": "OPEN"}),
    lambda d: d["registers"].__setitem__("objections", [obj(state="OPEN")]),
    lambda d: d["registers"].__setitem__(
        "objections", [obj(state="USER_OVERRIDE")]),
    lambda d: (d["registers"].__setitem__(
        "change_requests", [cr(state="DRAFT")]),
        d["registers"]["changelog"].append(cr_log())),
]
_missed = [i for i, m in enumerate(_sweep) if _sweep_case(m)]
RESULTS.append(("LM-07", "Lifecycle-defect sweep: all detected",
                "PASS" if not _missed else "FAIL",
                f"{len(_sweep) - len(_missed)}/{len(_sweep)} caught"))

# LM-08: no false positive on a fully coherent governance history.
_d = base()
_d["registers"]["proposals"] = [
    prop("P-001", "SUPERSEDED"),
    prop("P-002", "APPROVED", decision_id="DEC-001")]
_d["registers"]["decisions"] = [dec("DEC-001", "P-002",
                                    user_override_of="OBJ-001")]
_d["registers"]["objections"] = [obj("OBJ-001", "DEC-001", "USER_OVERRIDE")]
_d["registers"]["change_requests"] = [cr(state="APPLIED", approved_on=TODAY,
                                         applied_in_revision="R01")]
_d["registers"]["changelog"] = [_initial(), cr_log()]
_ok, _f = run(_d)
RESULTS.append(("LM-08", "A complete, coherent governance history is clean",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B10 — REGISTER LIFECYCLE / DECISION-STATE TEST REPORT")
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
