#!/usr/bin/env python3
"""Phase 00.5-B9 — Revision / Changelog Traceability Integrity test suite.

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
from validate_revisions import (                                   # noqa: E402
    validate_revisions, traceability_report, check_revision_coherence,
    check_freeze_record, check_proof_obligations, check_chronology)

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []

# --------------------------------------------------------------------------
# Fixture — reuse B8's clean() (already accepted by A/B1/B6/B7/B8).
# --------------------------------------------------------------------------
_b8_src = open(os.path.join(HERE, "test_00_5_B8.py"), encoding="utf-8").read()
_b8 = {"__name__": "b8fixture",
       "__file__": os.path.join(HERE, "test_00_5_B8.py")}
try:
    with redirect_stdout(io.StringIO()):
        exec(compile(_b8_src, "test_00_5_B8.py", "exec"), _b8)
except SystemExit:
    pass

clean = _b8["clean"]
H_MASTER = _b8["H_MASTER"]


def initial(date="2026-09-10", revision="R01"):
    return {"revision": revision, "date": date, "type": "INITIAL",
            "summary": "initial issue of the master"}


def entry(etype, date="2026-09-12", revision="R01", **over):
    e = {"revision": revision, "date": date, "type": etype,
         "summary": f"{etype} entry recorded for traceability"}
    e.update(over)
    return e


def errs(findings):
    return sorted({f.rule for f in findings if f.severity == "ERROR"})


def run(d):
    return validate_revisions(d)


def all_layers(d):
    return (validate_master(d, SCHEMA)[0], validate_references(d)[0],
            validate_formulas(d)[0], validate_blocking(d)[0],
            validate_outputs(d)[0])


# ==========================================================================
# POSITIVE
# ==========================================================================
_d = clean()
_d["registers"]["changelog"] = [initial()]
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("RP-01", "A coherent single-revision history passes",
                "PASS" if (_ok and all(_layers)) else "FAIL",
                f"B9={_ok} layers={_layers}"))

_d = clean()
_d["registers"]["changelog"] = []
_ok, _f = run(_d)
RESULTS.append(("RP-02", "An empty changelog is a legitimate start, not a defect",
                "PASS" if (_ok and not _f) else "FAIL", f"ok={_ok}"))

_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [
    initial(), entry("FREEZE", date="2026-09-13", master_hash_after=H_MASTER)]
_ok, _f = run(_d)
RESULTS.append(("RP-03", "A properly recorded freeze passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [
    initial(),
    entry("REGENERATION", output_diff_explained="views re-exported, "
                                                "geometry unchanged")]
_ok, _f = run(_d)
RESULTS.append(("RP-04", "A REGENERATION that explains its diff passes",
                "PASS" if (_ok and not errs(_f)) else "FAIL", f"{errs(_f)}"))

_tpl = json.load(open(os.path.join(ROOT, "project_master.template.json"),
                      encoding="utf-8"))
_tpl = {k: v for k, v in _tpl.items() if not k.startswith("_")}
_ok, _f = run(_tpl)
RESULTS.append(("RP-05", "The shipped template raises no B9 error",
                "PASS" if _ok else "FAIL", f"ok={_ok} {errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [initial()]
_rep = traceability_report(_d)
RESULTS.append(("RP-06", "The traceability report describes the real history",
                "PASS" if (_rep["entries"] == 1
                           and _rep["types"] == ["INITIAL"]
                           and _rep["freeze_recorded"] is False) else "FAIL",
                f"{_rep}"))


# ==========================================================================
# NEGATIVE — RT-001 / RT-002
# ==========================================================================
_d = clean()
_d["meta"]["revision"] = "R07"
_d["registers"]["changelog"] = [initial()]
_ok, _f = run(_d)
_layers = all_layers(_d)
RESULTS.append(("RN-01", "A revision absent from its own history is caught",
                "PASS" if (not _ok and "RT-001" in errs(_f)
                           and all(_layers)) else "FAIL",
                f"layers={_layers} B9={errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [initial(revision="R99")]
_ok, _f = run(_d)
RESULTS.append(("RN-02", "A history ahead of the master is surfaced",
                "PASS" if any(x.rule in ("RT-001", "RT-002") for x in _f)
                else "FAIL", f"{[ (x.rule,x.severity) for x in _f ]}"))

# On a FROZEN master the same drift is an ERROR, not a warning.
_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [
    initial(), entry("FREEZE", date="2026-09-13", master_hash_after=H_MASTER),
    entry("CR_APPLIED", revision="R09", cr_id="CR-001")]
_ok, _f = run(_d)
RESULTS.append(("RN-03", "On a FROZEN master a future revision is an ERROR",
                "PASS" if (not _ok and "RT-002" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))


# ==========================================================================
# NEGATIVE — RT-003 / RT-004 (freeze)
# ==========================================================================
_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [initial()]
_ok, _f = run(_d)
RESULTS.append(("RN-04", "A freeze with no FREEZE entry is caught",
                "PASS" if (not _ok and "RT-003" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [
    initial(), entry("FREEZE", date="2026-09-13", master_hash_after="9" * 64)]
_ok, _f = run(_d)
RESULTS.append(("RN-05", "A freeze hash contradicting meta is caught",
                "PASS" if (not _ok and "RT-004" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [initial(), entry("FREEZE", date="2026-09-13")]
_ok, _f = run(_d)
_warn = [x for x in _f if x.rule == "RT-004" and x.severity == "WARN"]
RESULTS.append(("RN-06", "A freeze with no recorded hash is surfaced as WARN",
                "PASS" if _warn else "FAIL", f"warn={len(_warn)}"))


# ==========================================================================
# NEGATIVE — RT-005 / RT-008 (proof obligations)
# ==========================================================================
_d = clean()
_d["registers"]["changelog"] = [initial(), entry("REGENERATION")]
_ok, _f = run(_d)
RESULTS.append(("RN-07", "REGENERATION without an explained diff is caught",
                "PASS" if (not _ok and "RT-005" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [
    initial(), entry("CR_APPLIED", cr_id="CR-001", regressions_found=True)]
_d["registers"]["change_requests"] = [{
    "id": "CR-001", "title": "a change", "target_element": "space.outline",
    "reason": "client asked for a wider room", "state": "APPROVED",
    "raised_on": TODAY}]
_ok, _f = run(_d)
RESULTS.append(("RN-08", "An admitted regression is never swallowed",
                "PASS" if (not _ok and "RT-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [
    initial(), entry("REGENERATION", tests_rerun=False,
                     output_diff_explained="re-exported views only")]
_ok, _f = run(_d)
_warn = [x for x in _f if x.rule == "RT-008" and x.severity == "WARN"]
RESULTS.append(("RN-09", "tests_rerun=false is surfaced as a WARN",
                "PASS" if _warn else "FAIL", f"warn={len(_warn)}"))


# ==========================================================================
# NEGATIVE — RT-006 / RT-007 (chronology)
# ==========================================================================
_d = clean()
_d["registers"]["changelog"] = [
    initial(date="2026-09-14"), entry("FREEZE", date="2026-09-10")]
_ok, _f = run(_d)
RESULTS.append(("RN-10", "A backwards history is caught",
                "PASS" if (not _ok and "RT-006" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [initial(date="2026-09-10"),
                                initial(date="2026-09-11")]
_ok, _f = run(_d)
RESULTS.append(("RN-11", "Two beginnings are caught",
                "PASS" if (not _ok and "RT-007" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [entry("CR_APPLIED", cr_id="CR-001")]
_d["registers"]["change_requests"] = [{
    "id": "CR-001", "title": "a change", "target_element": "space.outline",
    "reason": "client asked for a wider room", "state": "APPROVED",
    "raised_on": TODAY}]
_ok, _f = run(_d)
_warn = [x for x in _f if x.rule == "RT-007"]
RESULTS.append(("RN-12", "A history with no beginning is surfaced",
                "PASS" if _warn else "FAIL", f"{[x.severity for x in _warn]}"))


# ==========================================================================
# BOUNDARY
# ==========================================================================
_d = clean()
_d["registers"]["changelog"] = [initial(date="2026-09-10"),
                                entry("FREEZE", date="2026-09-10")]
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-10"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"][1]["master_hash_after"] = H_MASTER
_ok, _f = run(_d)
RESULTS.append(("RB-01", "Same-day entries are not a backwards history",
                "PASS" if "RT-006" not in errs(_f) else "FAIL", f"{errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [initial(), entry("REGENERATION",
                                                 output_diff_explained="")]
_ok, _f = run(_d)
RESULTS.append(("RB-02", "An empty diff explanation counts as missing",
                "PASS" if "RT-005" in errs(_f) else "FAIL", f"{errs(_f)}"))

# A missing optional field is UNSPECIFIED, never assumed false.
_d = clean()
_d["registers"]["changelog"] = [initial(), entry(
    "CR_APPLIED", cr_id="CR-001",
    output_diff_explained="wall moved 100mm as approved")]
_d["registers"]["change_requests"] = [{
    "id": "CR-001", "title": "a change", "target_element": "space.outline",
    "reason": "client asked for a wider room", "state": "APPROVED",
    "raised_on": TODAY}]
_ok, _f = run(_d)
RESULTS.append(("RB-03", "Absent tests_rerun is UNSPECIFIED, not false",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))

_d = clean()
_d["meta"]["status"] = "DRAFT"
_d["registers"]["changelog"] = [initial(), entry("FREEZE", date="2026-09-13",
                                                 master_hash_after=H_MASTER)]
_ok, _f = run(_d)
RESULTS.append(("RB-04", "A FREEZE entry on a DRAFT master is not fabricated into an error",
                "PASS" if "RT-003" not in errs(_f) else "FAIL", f"{errs(_f)}"))


# ==========================================================================
# ANTI-SMUGGLING
# ==========================================================================
_d = clean()
_d["meta"]["revision"] = "R05"
_d["registers"]["changelog"] = [initial()]
_ok, _f = run(_d)
RESULTS.append(("RX-01", "Bumping a revision without recording it fails",
                "PASS" if (not _ok and "RT-001" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = "7" * 64
_d["registers"]["changelog"] = [
    initial(), entry("FREEZE", date="2026-09-13", master_hash_after=H_MASTER)]
_ok, _f = run(_d)
RESULTS.append(("RX-02", "Swapping the frozen hash afterwards is caught",
                "PASS" if (not _ok and "RT-004" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_d["registers"]["changelog"] = [
    initial(), entry("REGENERATION", regressions_found=True,
                     output_diff_explained="regenerated")]
_ok, _f = run(_d)
RESULTS.append(("RX-03", "A regression cannot hide inside a REGENERATION",
                "PASS" if (not _ok and "RT-008" in errs(_f)) else "FAIL",
                f"{errs(_f)}"))

_d = clean()
_snapshot = copy.deepcopy(_d)
_d["meta"]["revision"] = "R07"
_d["registers"]["changelog"] = [initial()]
_before = copy.deepcopy(_d)
run(_d)
traceability_report(_d)
RESULTS.append(("RX-04", "B9 never mutates the model (no auto-fix)",
                "PASS" if _d == _before else "FAIL",
                f"unchanged={_d == _before}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
_src = open(os.path.join(ROOT, "scripts", "validate_revisions.py"),
            encoding="utf-8").read()
_codes = sorted(set(re.findall(
    r'"(RT|XR|WT|FC|MV|DS|FM|UB|OR|INV)-[0-9]+"', _src)))
RESULTS.append(("RI-01", "B9 emits only RT-* rule codes",
                "PASS" if _codes == ["RT"] else "FAIL", f"prefixes={_codes}"))

_d = clean()
_d["meta"]["revision"] = "R07"
_d["registers"]["changelog"] = [initial()]
_layers = all_layers(_d)
_ok, _f = run(_d)
RESULTS.append(("RI-02", "A B9 error leaves A/B1/B6/B7/B8 untouched",
                "PASS" if (all(_layers) and not _ok) else "FAIL",
                f"layers={_layers} B9={_ok}"))

_back = []
for _mod in ("schema_gate", "validate_refs", "validate_topology",
             "validate_furniture", "validate_movement", "validate_doors",
             "validate_formulas", "validate_blocking", "validate_outputs"):
    _txt = open(os.path.join(ROOT, "scripts", _mod + ".py"),
                encoding="utf-8").read()
    if "validate_revisions" in _txt:
        _back.append(_mod)
RESULTS.append(("RI-03", "No earlier layer imports B9",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

_tree = ast.parse(_src)
for _n in ast.walk(_tree):
    if isinstance(_n, ast.Expr) and isinstance(_n.value, ast.Constant) \
            and isinstance(_n.value.value, str):
        _n.value.value = ""
_exec_src = ast.unparse(_tree).lower()
_bad = [t for t in ("clearance", "ergonom", "overlap", "footprint",
                    "swing", "optimi", "tolerance", "derived_from",
                    "presence")
        if t in _exec_src]
RESULTS.append(("RI-04", "B9 holds no geometry, tolerance or other layer's field",
                "PASS" if not _bad else "FAIL", f"terms={_bad}"))

# TECHNICAL_FIX obligations must stay A's rule TF1 — B9 must not re-check it.
_d = clean()
_d["registers"]["changelog"] = [
    initial(),
    entry("TECHNICAL_FIX", master_hash_before="a" * 64,
          master_hash_after="b" * 64, geometry_version_before="G-001",
          geometry_version_after="G-001", tests_rerun=True,
          regressions_found=False, output_diff_explained="script fix")]
_a = validate_master(_d, SCHEMA)[0]
_ok, _f = run(_d)
RESULTS.append(("RI-05", "TECHNICAL_FIX obligations stay A's rule (TF1)",
                "PASS" if (not _a and "RT-008" not in errs(_f)) else "FAIL",
                f"A={_a} B9={errs(_f)}"))

# cr_id existence stays B1's rule XR-012 — B9 must stay silent about it.
_d = clean()
_d["registers"]["changelog"] = [initial(),
                                entry("CR_APPLIED", cr_id="CR-404")]
_b1 = validate_references(_d)[0]
_ok, _f = run(_d)
RESULTS.append(("RI-06", "A dangling cr_id stays B1's rule (XR-012)",
                "PASS" if (not _b1 and _ok) else "FAIL",
                f"B1={_b1} B9={_ok} {errs(_f)}"))


# ==========================================================================
# MUTATION
# ==========================================================================
_d = clean()
_d["meta"]["revision"] = "R07"
_d["registers"]["changelog"] = [initial()]
RESULTS.append(("RM-01", "check_revision_coherence alone fires",
                "PASS" if any(f.rule == "RT-001"
                              for f in check_revision_coherence(_d))
                else "FAIL", "isolated rule fires"))

_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [initial()]
RESULTS.append(("RM-02", "check_freeze_record alone fires",
                "PASS" if any(f.rule == "RT-003"
                              for f in check_freeze_record(_d)) else "FAIL",
                "isolated rule fires"))

_d = clean()
_d["registers"]["changelog"] = [initial(), entry("REGENERATION")]
RESULTS.append(("RM-03", "check_proof_obligations alone fires",
                "PASS" if any(f.rule == "RT-005"
                              for f in check_proof_obligations(_d))
                else "FAIL", "isolated rule fires"))

_d = clean()
_d["registers"]["changelog"] = [initial(date="2026-09-14"),
                                entry("FREEZE", date="2026-09-01")]
RESULTS.append(("RM-04", "check_chronology alone fires",
                "PASS" if any(f.rule == "RT-006"
                              for f in check_chronology(_d)) else "FAIL",
                "isolated rule fires"))

# RM-05: flipping ONLY meta.revision flips the verdict.
_good = clean()
_good["registers"]["changelog"] = [initial()]
_bad = copy.deepcopy(_good)
_bad["meta"]["revision"] = "R07"
RESULTS.append(("RM-05", "Flipping only meta.revision flips the verdict",
                "PASS" if (run(_good)[0] and not run(_bad)[0]) else "FAIL",
                f"good={run(_good)[0]} bad={run(_bad)[0]}"))

# RM-06: flipping ONLY meta.status flips the freeze requirement.
_draft = clean()
_draft["registers"]["changelog"] = [initial()]
_frozen = copy.deepcopy(_draft)
_frozen["meta"]["status"] = "FROZEN"
_frozen["meta"]["frozen_on"] = "2026-09-13"
_frozen["meta"]["master_hash"] = H_MASTER
RESULTS.append(("RM-06", "Only meta.status decides the freeze obligation",
                "PASS" if (run(_draft)[0] and not run(_frozen)[0]) else "FAIL",
                f"draft={run(_draft)[0]} frozen={run(_frozen)[0]}"))

# RM-07: sweep — every traceability defect must be detected.
def _case(mod):
    d = clean()
    d["registers"]["changelog"] = [initial()]
    mod(d)
    return run(d)[0]


def _m_rev(d):
    d["meta"]["revision"] = "R07"


def _m_freeze(d):
    d["meta"]["status"] = "FROZEN"
    d["meta"]["frozen_on"] = "2026-09-13"
    d["meta"]["master_hash"] = H_MASTER


def _m_regen(d):
    d["registers"]["changelog"].append(entry("REGENERATION"))


def _m_back(d):
    d["registers"]["changelog"].append(entry("FREEZE", date="2020-01-01"))


def _m_twice(d):
    d["registers"]["changelog"].append(initial(date="2026-09-11"))


_sweep = [_m_rev, _m_freeze, _m_regen, _m_back, _m_twice]
_missed = [i for i, m in enumerate(_sweep) if _case(m)]
RESULTS.append(("RM-07", "Traceability-defect sweep: all detected",
                "PASS" if not _missed else "FAIL",
                f"{len(_sweep) - len(_missed)}/{len(_sweep)} caught"))

# RM-08: no false positive on a fully coherent, frozen, regenerated history.
_d = clean()
_d["meta"]["status"] = "FROZEN"
_d["meta"]["frozen_on"] = "2026-09-13"
_d["meta"]["master_hash"] = H_MASTER
_d["registers"]["changelog"] = [
    initial(date="2026-09-10"),
    entry("REGENERATION", date="2026-09-11",
          output_diff_explained="views re-exported, geometry identical",
          tests_rerun=True, regressions_found=False),
    entry("FREEZE", date="2026-09-13", master_hash_after=H_MASTER)]
_ok, _f = run(_d)
RESULTS.append(("RM-08", "A complete, honest history raises nothing",
                "PASS" if (_ok and not errs(_f)) else "FAIL",
                f"ok={_ok} {errs(_f)}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B9 — REVISION / CHANGELOG TRACEABILITY TEST REPORT")
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
