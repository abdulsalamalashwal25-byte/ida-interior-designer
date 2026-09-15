#!/usr/bin/env python3
"""Phase 00.5-B11 — Temporal Integrity / Chronological Coherence tests.

Discipline: every rule gets a POSITIVE and a NEGATIVE case; each negative
proves the INTENDED rule fired; isolation tests prove B11 does not reach
into A/B1..B10; mutation tests prove the suite dies when the engine is
disabled.

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
from validate_blocking import validate_blocking                    # noqa: E402
from validate_outputs import validate_outputs                      # noqa: E402
from validate_revisions import validate_revisions                  # noqa: E402
from validate_lifecycle import validate_lifecycle                  # noqa: E402
from validate_temporal import (                                    # noqa: E402
    validate_temporal, temporal_report, check_causal_order,
    check_resolution_order, check_envelope, check_freeze_time)

SCHEMA = load_schema()
T0 = "2026-09-12"
EARLY = "2026-01-01"
RESULTS = []

# --------------------------------------------------------------------------
# Fixture — reuse B9's clean(), already accepted by A/B1..B10, so any finding
# here is unambiguously B11's.
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


def prop(pid="P-001", raised=T0, **over):
    p = {"id": pid, "text": "a proposal about the furniture layout",
         "state": "APPROVED", "raised_on": raised, "decision_id": "DEC-001"}
    p.update(over)
    return p


def dec(did="DEC-001", linked="P-001", approved=T0, **over):
    d = {"decision_id": did, "title": "the layout decision",
         "linked_proposal": linked,
         "rationale": "the client approved this option in the meeting",
         "alternatives_considered": ["option a", "option b"],
         "approved_by": "USER", "approved_on": approved,
         "approved_in_revision": "R01"}
    d.update(over)
    return d


def obj(oid="OBJ-001", target="DEC-001", raised=T0, **over):
    o = {"id": oid, "decision_under_objection": target,
         "problem": "this blocks the main corridor",
         "impact": "circulation width drops below the agreed value",
         "alternative": "shift the unit by 200mm", "state": "WITHDRAWN",
         "raised_on": raised}
    o.update(over)
    return o


def unk(uid="U-001", raised=T0, **over):
    u = {"id": uid, "question": "what is the finished ceiling height?",
         "affects": ["space.ceiling_height"], "blocking": False,
         "raised_on": raised}
    u.update(over)
    return u


def cr(cid="CR-001", raised=T0, state="APPROVED", **over):
    c = {"id": cid, "target_element": "space.ceiling_height",
         "current_value": "2800", "proposed_value": "3000",
         "reason": "the client wants a higher ceiling",
         "impact": "affects all sections and elevations",
         "classification": "MAJOR", "state": state, "raised_on": raised}
    c.update(over)
    return c


def fact(value=2800, recorded=T0, **over):
    f = {"value": value, "status": "C", "source_type": "CLIENT_INPUT",
         "source_ref": "the measured survey drawing",
         "recorded_on": recorded, "unit": "mm"}
    f.update(over)
    return f


def frozen(d, on="2026-09-13"):
    """Turn the fixture into a properly frozen project (B9-clean)."""
    d["meta"]["master_hash"] = "a" * 64
    d["meta"]["status"] = "FROZEN"
    d["meta"]["frozen_on"] = on
    d["meta"]["revision"] = "R01"
    d["registers"]["changelog"].append({
        "revision": "R01", "date": on, "type": "FREEZE",
        "summary": "the design master was frozen at revision R01",
        "master_hash_after": "a" * 64})
    return d


def errs(findings):
    return sorted({f.rule for f in findings if f.severity == "ERROR"})


def warns(findings):
    return sorted({f.rule for f in findings if f.severity == "WARN"})


def run(d):
    return validate_temporal(d)


def all_layers(d):
    """Every previously closed gate, to prove B11 findings are exclusive."""
    with redirect_stdout(io.StringIO()):
        return (validate_master(d, SCHEMA)[0], validate_references(d)[0],
                validate_blocking(d)[0], validate_outputs(d)[0],
                validate_revisions(d)[0], validate_lifecycle(d)[0])


# ==========================================================================
# POSITIVE
# ==========================================================================
_d = base()
_ok, _f = run(_d)
RESULTS.append(("TP-01", "A project with coherent dates passes",
                "PASS" if (_ok and not _f) else "FAIL", f"ok={_ok}"))

_d = base()
_d["registers"]["proposals"] = [prop(raised=T0)]
_d["registers"]["decisions"] = [dec(approved="2026-09-13")]
_ok, _f = run(_d)
RESULTS.append(("TP-02", "A decision after its proposal passes every layer",
                "PASS" if (_ok and all(all_layers(_d))) else "FAIL",
                f"B11={_ok} layers={all_layers(_d)}"))

_d = base()
_d["registers"]["proposals"] = [prop()]
_d["registers"]["decisions"] = [dec(approved=T0)]
_ok, _f = run(_d)
RESULTS.append(("TP-03", "Same-day cause and effect is NOT an error",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"{errs(_f)} (day resolution must not invent order)"))

_d = base()
_d["registers"]["unknowns"] = [unk(raised=T0, resolved_on="2026-09-14")]
_ok, _f = run(_d)
RESULTS.append(("TP-04", "An unknown resolved after it was raised passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_d = frozen(base())
_ok, _f = run(_d)
RESULTS.append(("TP-05", "A properly frozen project passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_tpl = json.load(open(os.path.join(ROOT, "project_master.template.json"),
                      encoding="utf-8"))
_tpl = {k: v for k, v in _tpl.items() if not k.startswith("_")}
_ok, _f = run(_tpl)
RESULTS.append(("TP-06", "The shipped template raises no B11 error",
                "PASS" if _ok else "FAIL", f"ok={_ok} {errs(_f)}"))

_rep = temporal_report(base())
RESULTS.append(("TP-07", "The temporal report describes the real dates",
                "PASS" if (_rep["created_on"] and _rep["status"] == "DRAFT"
                           and _rep["frozen_on"] is None) else "FAIL",
                f"{_rep['created_on']}/{_rep['status']}"))

_d = base()
_d["registers"]["change_requests"] = [cr(raised=T0, approved_on="2026-09-15")]
_ok, _f = run(_d)
RESULTS.append(("TP-08", "A CR approved after it was raised passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))


# ==========================================================================
# NEGATIVE — TI-001 / TI-002
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(raised=T0)]
_d["registers"]["decisions"] = [dec(approved=EARLY)]
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("TN-01", "A decision approved before its proposal was raised",
                "PASS" if (not _ok and "TI-001" in errs(_f)
                           and all(_layers)) else "FAIL",
                f"layers={_layers} B11={errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop()]
_d["registers"]["decisions"] = [dec(approved="2026-09-13")]
_d["registers"]["objections"] = [obj(raised=T0)]
_ok, _f = run(_d)
RESULTS.append(("TN-02", "An objection raised before its decision existed",
                "PASS" if (not _ok and "TI-002" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# NEGATIVE — TI-003
# ==========================================================================
_d = base()
_d["registers"]["unknowns"] = [unk(raised=T0, resolved_on=EARLY)]
_ok, _f = run(_d)
RESULTS.append(("TN-03", "An unknown resolved before it was raised",
                "PASS" if (not _ok and "TI-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["change_requests"] = [cr(raised=T0, approved_on=EARLY)]
_ok, _f = run(_d)
RESULTS.append(("TN-04", "A change request approved before it was raised",
                "PASS" if (not _ok and "TI-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# NEGATIVE — TI-004 / TI-005 / TI-006
# ==========================================================================
_d = base()
_d["registers"]["unknowns"] = [unk(raised="2000-01-01")]
_ok, _f = run(_d)
RESULTS.append(("TN-05", "A register entry dated before the project existed",
                "PASS" if (not _ok and "TI-004" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["space"]["ceiling_height"] = fact(recorded="2000-01-01")
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("TN-06", "A fact recorded before the project existed",
                "PASS" if (not _ok and "TI-004" in errs(_f)
                           and all(_layers)) else "FAIL",
                f"layers={_layers} B11={errs(_f)}"))

_d = base()
_d["registers"]["assumptions"] = [
    {"id": "A-001", "text": "assumed slab thickness of 200mm",
     "impact": "affects the finished ceiling height",
     "approval_state": "APPROVED", "raised_on": T0}]
_d["space"]["floor_level"] = fact(
    200, recorded=T0, status="A", source_type="AGENT_ASSUMPTION",
    source_ref="assumed slab thickness", assumption_id="A-001",
    approval_state="APPROVED", approved_by="USER", approved_on=EARLY,
    impact="affects the finished floor level")
_ok, _f = run(_d)
RESULTS.append(("TN-07", "A fact approved before it was ever recorded",
                "PASS" if (not _ok and "TI-005" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["unknowns"] = [unk(raised="2026-09-13")]
_d["space"]["ceiling_height"] = fact(recorded="2099-12-31")
_ok, _f = run(_d)
RESULTS.append(("TN-08", "A date beyond the file's own horizon is surfaced",
                "PASS" if "TI-006" in warns(_f) else "FAIL",
                f"warn={warns(_f)} err={errs(_f)}"))


# ==========================================================================
# NEGATIVE — TI-007 / TI-008
# ==========================================================================
_d = frozen(base(), on="2026-09-13")
_d["space"]["ceiling_height"] = fact(recorded="2026-09-30")
_ok, _f = run(_d)
RESULTS.append(("TN-09", "Content recorded after the freeze with no CR",
                "PASS" if (not _ok and "TI-007" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["meta"]["frozen_on"] = T0
_ok, _f = run(_d)
RESULTS.append(("TN-10", "A freeze date on a DRAFT project",
                "PASS" if (not _ok and "TI-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["meta"]["master_hash"] = "a" * 64
_d["meta"]["status"] = "FROZEN"
_d["meta"]["revision"] = "R01"
_d["registers"]["changelog"].append({
    "revision": "R01", "date": T0, "type": "FREEZE",
    "summary": "the design master was frozen at revision R01",
    "master_hash_after": "a" * 64})
_ok, _f = run(_d)
RESULTS.append(("TN-11", "FROZEN with no frozen_on date at all",
                "PASS" if (not _ok and "TI-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = frozen(base(), on="2000-01-01")
_ok, _f = run(_d)
RESULTS.append(("TN-12", "A project frozen before it was created",
                "PASS" if (not _ok and "TI-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# BOUNDARY
# ==========================================================================
_d = base()
_d["registers"]["unknowns"] = [unk(raised=T0, resolved_on=T0)]
_ok, _f = run(_d)
RESULTS.append(("TB-01", "Raised and resolved on the same day is allowed",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_d = base()
_d["registers"]["unknowns"] = [unk()]
_d["registers"]["unknowns"][0].pop("raised_on")
_ok, _f = run(_d)
RESULTS.append(("TB-02", "A missing date is A's rule, not a B11 error",
                "PASS" if _ok else "FAIL", f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop()]
_d["registers"]["decisions"] = [dec(linked="P-404", approved=EARLY)]
_ok, _f = run(_d)
RESULTS.append(("TB-03", "A dangling link is B1's rule; B11 stays silent",
                "PASS" if "TI-001" not in errs(_f) else "FAIL", f"{errs(_f)}"))

_d = frozen(base(), on="2026-09-13")
_d["registers"]["change_requests"] = [cr(state="APPLIED", approved_on=T0,
                                         applied_in_revision="R01")]
_d["space"]["ceiling_height"] = fact(recorded="2026-09-30")
_ok, _f = run(_d)
RESULTS.append(("TB-04", "A post-freeze change WITH a live CR is allowed",
                "PASS" if "TI-007" not in errs(_f) else "FAIL", f"{errs(_f)}"))

_d = base()
_ok, _f = run(_d)
RESULTS.append(("TB-05", "A single-date file raises no horizon warning",
                "PASS" if not warns(_f) else "FAIL", f"warn={warns(_f)}"))


# ==========================================================================
# ANTI-SMUGGLING
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(raised="2026-09-20")]
_d["registers"]["decisions"] = [dec(approved=T0)]
_ok, _f = run(_d)
RESULTS.append(("TX-01", "Backdating a decision cannot legitimise it",
                "PASS" if (not _ok and "TI-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = frozen(base(), on="2026-09-13")
_d["registers"]["change_requests"] = [cr(state="REJECTED")]
_d["space"]["ceiling_height"] = fact(recorded="2026-09-30")
_ok, _f = run(_d)
RESULTS.append(("TX-02", "A rejected CR cannot license a post-freeze edit",
                "PASS" if (not _ok and "TI-007" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["unknowns"] = [unk(raised=T0, resolved_on=EARLY,
                                   blocking=True)]
_ok, _f = run(_d)
RESULTS.append(("TX-03", "A pre-dated resolution cannot close an unknown",
                "PASS" if (not _ok and "TI-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = base()
_d["registers"]["proposals"] = [prop(raised=T0)]
_d["registers"]["decisions"] = [dec(approved=EARLY)]
_before = copy.deepcopy(_d)
run(_d)
temporal_report(_d)
RESULTS.append(("TX-04", "B11 never mutates the model (no auto-fix)",
                "PASS" if _d == _before else "FAIL",
                f"unchanged={_d == _before}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
_src = open(os.path.join(ROOT, "scripts", "validate_temporal.py"),
            encoding="utf-8").read()
_codes = sorted(set(re.findall(
    r'"(TI|RL|XR|WT|FC|MV|DS|FM|UB|OR|RT|INV)-[0-9]+"', _src)))
RESULTS.append(("TI-I01", "B11 emits only TI-* rule codes",
                "PASS" if _codes == ["TI"] else "FAIL", f"prefixes={_codes}"))

_d = base()
_d["registers"]["proposals"] = [prop(raised=T0)]
_d["registers"]["decisions"] = [dec(approved=EARLY)]
_layers = all_layers(_d)
_ok, _f = run(_d)
RESULTS.append(("TI-I02", "A B11 error leaves A/B1/B7/B8/B9/B10 untouched",
                "PASS" if (all(_layers) and not _ok) else "FAIL",
                f"layers={_layers} B11={_ok}"))

_back = []
for _mod in ("schema_gate", "validate_refs", "validate_topology",
             "validate_furniture", "validate_movement", "validate_doors",
             "validate_formulas", "validate_blocking", "validate_outputs",
             "validate_revisions", "validate_lifecycle"):
    _txt = open(os.path.join(ROOT, "scripts", _mod + ".py"),
                encoding="utf-8").read()
    if "validate_temporal" in _txt:
        _back.append(_mod)
RESULTS.append(("TI-I03", "No earlier layer imports B11",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

_tree = ast.parse(_src)
for _n in ast.walk(_tree):
    if isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Constant) \
            and isinstance(_n.value.value, str):
        _n.value.value = ""
_exec_src = ast.unparse(_tree).lower()
_bad = [t for t in ("clearance", "ergonom", "overlap", "footprint", "swing",
                    "optimi", "tolerance", "fingerprint", "master_hash_after")
        if t in _exec_src]
RESULTS.append(("TI-I04", "B11 holds no geometry, tolerance or hash logic",
                "PASS" if not _bad else "FAIL", f"terms={_bad}"))

# Changelog INTERNAL order stays B9's rule RT-006 — B11 must not re-report it.
_d = base()
_d["registers"]["changelog"].append({
    "revision": "R01", "date": "2020-01-01", "type": "CR_APPLIED",
    "summary": "an entry dated before the previous one", "cr_id": "CR-001"})
_d["registers"]["change_requests"] = [cr(state="APPLIED", approved_on=T0,
                                         applied_in_revision="R01")]
with redirect_stdout(io.StringIO()):
    _b9ok = validate_revisions(_d)[0]
_ok, _f = run(_d)
RESULTS.append(("TI-I05", "Backwards changelog order stays B9's rule RT-006",
                "PASS" if (not _b9ok and "TI-004" not in errs(_f)) else "FAIL",
                f"B9={_b9ok} B11={errs(_f)}"))

# Register STATE coherence stays B10's rule — B11 must stay silent on it.
_d = base()
_d["registers"]["proposals"] = [prop(state="REJECTED")]
_d["registers"]["decisions"] = [dec(approved="2026-09-13")]
with redirect_stdout(io.StringIO()):
    _b10ok = validate_lifecycle(_d)[0]
_ok, _f = run(_d)
RESULTS.append(("TI-I06", "Rejected-proposal state stays B10's rule",
                "PASS" if (not _b10ok and _ok) else "FAIL",
                f"B10={_b10ok} B11={_ok}"))

# Output generated_on vs created_on stays B8's rule.
_src_b8 = open(os.path.join(ROOT, "scripts", "validate_outputs.py"),
               encoding="utf-8").read()
RESULTS.append(("TI-I07", "outputs.generated_on stays B8's rule",
                "PASS" if ("generated_on" in _src_b8
                           and "generated_on" not in ast.unparse(_tree))
                else "FAIL", "B11 does not judge output dates"))

# Date FORMAT stays A's rule.
_d = base()
_d["registers"]["unknowns"] = [unk(raised="12/09/2026")]
with redirect_stdout(io.StringIO()):
    _aok = validate_master(_d, SCHEMA)[0]
_ok, _f = run(_d)
RESULTS.append(("TI-I08", "Malformed date shape stays A's rule",
                "PASS" if (not _aok and _ok) else "FAIL",
                f"A={_aok} B11={_ok}"))


# ==========================================================================
# MUTATION
# ==========================================================================
_d = base()
_d["registers"]["proposals"] = [prop(raised=T0)]
_d["registers"]["decisions"] = [dec(approved=EARLY)]
RESULTS.append(("TM-01", "check_causal_order alone fires",
                "PASS" if any(f.rule == "TI-001"
                              for f in check_causal_order(_d)) else "FAIL",
                "isolated rule fires"))

_d = base()
_d["registers"]["unknowns"] = [unk(raised=T0, resolved_on=EARLY)]
RESULTS.append(("TM-02", "check_resolution_order alone fires",
                "PASS" if any(f.rule == "TI-003"
                              for f in check_resolution_order(_d)) else "FAIL",
                "isolated rule fires"))

_d = base()
_d["space"]["ceiling_height"] = fact(recorded="2000-01-01")
RESULTS.append(("TM-03", "check_envelope alone fires",
                "PASS" if any(f.rule == "TI-004"
                              for f in check_envelope(_d)) else "FAIL",
                "isolated rule fires"))

_d = base()
_d["meta"]["frozen_on"] = T0
RESULTS.append(("TM-04", "check_freeze_time alone fires",
                "PASS" if any(f.rule == "TI-008"
                              for f in check_freeze_time(_d)) else "FAIL",
                "isolated rule fires"))

# TM-05: moving ONLY the decision date flips the verdict.
_good = base()
_good["registers"]["proposals"] = [prop(raised=T0)]
_good["registers"]["decisions"] = [dec(approved="2026-09-13")]
_bad = copy.deepcopy(_good)
_bad["registers"]["decisions"][0]["approved_on"] = EARLY
RESULTS.append(("TM-05", "Moving only the decision date flips the verdict",
                "PASS" if (run(_good)[0] and not run(_bad)[0]) else "FAIL",
                f"after={run(_good)[0]} before={run(_bad)[0]}"))

# TM-06: moving ONLY the freeze date flips the verdict.
_good = frozen(base(), on="2026-09-13")
_bad = copy.deepcopy(_good)
_bad["meta"]["frozen_on"] = "2000-01-01"
RESULTS.append(("TM-06", "Moving only the freeze date flips the verdict",
                "PASS" if (run(_good)[0] and not run(_bad)[0]) else "FAIL",
                f"valid={run(_good)[0]} predating={run(_bad)[0]}"))

# TM-07: sweep — every temporal defect must be detected.
def _sweep(mod):
    d = base()
    d["registers"]["proposals"] = [prop(raised=T0)]
    d["registers"]["decisions"] = [dec(approved="2026-09-13")]
    mod(d)
    return run(d)[0]


_cases = [
    lambda d: d["registers"]["decisions"][0].update({"approved_on": EARLY}),
    lambda d: (d["registers"].__setitem__("objections", [obj(raised=T0)]),
               d["registers"]["decisions"][0].update(
                   {"approved_on": "2026-09-20"})),
    lambda d: d["registers"].__setitem__(
        "unknowns", [unk(raised=T0, resolved_on=EARLY)]),
    lambda d: d["registers"].__setitem__(
        "change_requests", [cr(raised=T0, approved_on=EARLY)]),
    lambda d: d["registers"].__setitem__("unknowns", [unk(raised="2000-01-01")]),
    lambda d: d["space"].__setitem__("ceiling_height",
                                     fact(recorded="2000-01-01")),
    lambda d: d["meta"].__setitem__("frozen_on", T0),
]
_missed = [i for i, m in enumerate(_cases) if _sweep(m)]
RESULTS.append(("TM-07", "Temporal-defect sweep: all detected",
                "PASS" if not _missed else "FAIL",
                f"{len(_cases) - len(_missed)}/{len(_cases)} caught"))

# TM-08: a full, coherent project history must stay clean (no false positive).
_d = frozen(base(), on="2026-09-20")
_d["registers"]["proposals"] = [prop(raised=T0)]
_d["registers"]["decisions"] = [dec(approved="2026-09-13")]
_d["registers"]["objections"] = [obj(raised="2026-09-14")]
_d["registers"]["unknowns"] = [unk(raised=T0, resolved_on="2026-09-13")]
_d["registers"]["change_requests"] = [cr(raised="2026-09-13",
                                         approved_on="2026-09-14")]
_ok, _f = run(_d)
RESULTS.append(("TM-08", "A complete, coherent timeline stays clean",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B11 — TEMPORAL INTEGRITY / CHRONOLOGY TEST REPORT")
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
