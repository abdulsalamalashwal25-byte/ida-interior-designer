#!/usr/bin/env python3
"""Phase 00.5-B6 — Formula / Derived-Value Integrity test suite.

Discipline carried over from B1..B5:
  * Positive + Negative + Boundary + Unknown + Isolation + Mutation
  * a negative must fail because of the TARGETED rule, not fixture rot
  * UNKNOWN/UNCOMPUTABLE never becomes a guessed value
  * no [D] may smuggle a design decision
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
from validate_doors import validate_doors                     # noqa: E402
from validate_formulas import (                               # noqa: E402
    validate_formulas, parse_formula, evaluate, formula_variables,
    derivation_cycles, VERIFIED, MISMATCH, UNCOMPUTABLE,
    infer_dimension, parse_unit)

SCHEMA = load_schema()
TODAY = "2026-09-12"
RESULTS = []


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


def derived(value, formula, refs, unit="mm", dtype="ARITHMETIC", **kw):
    """A [D] fact shaped exactly as layer A rule F4 requires."""
    f = {"value": value, "status": "D", "source_type": "DERIVED_CALC",
         "source_ref": "computed from declared inputs", "recorded_on": TODAY,
         "unit": unit, "derived_from": refs, "formula": formula,
         "derivation_type": dtype}
    f.update(kw)
    return f


def wall(wid, a, b, thickness=200):
    return {"id": wid, "start": fact(list(a), unit="mm"),
            "end": fact(list(b), unit="mm"),
            "thickness": fact(thickness, unit="mm"), "structural": fact(True)}


# ===========================================================================
# BASE: minimal valid master with numeric inputs available for derivation.
# ===========================================================================
BASE = {
    "meta": {
        "project_id": "PRJ-94", "project_name": "FORMULA TEST ROOM",
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
        "openings": confirmed_absent("openings"),
        "circulation": confirmed_absent("defined routes"),
    },
    "walls": [
        wall("W-01", (0, 0), (6000, 0)),
        wall("W-02", (6000, 0), (6000, 4000)),
        wall("W-03", (6000, 4000), (0, 4000)),
        wall("W-04", (0, 4000), (0, 0)),
    ],
    "openings": [], "columns": [], "zones": [], "furniture": [],
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
                       "summary": "Formula test fixture."}],
    },
    "outputs": [],
}


def with_derived(f, key="floor_level"):
    d = copy.deepcopy(BASE)
    d["space"][key] = f
    return d


def run(d):
    return validate_formulas(d)


def rules_of(findings, severity=None):
    return sorted({f.rule for f in findings
                   if severity is None or f.severity == severity})


# ==========================================================================
# POSITIVE
# ==========================================================================
_d = with_derived(derived(2700, "ceiling_height - 100",
                          ["space.ceiling_height"]))
_ok_s, _es = validate_master(_d, SCHEMA)
_ok, _f, _v = run(_d)
RESULTS.append(("FP-01", "A correct arithmetic [D] verifies",
                "PASS" if (_ok_s and _ok
                           and list(_v.values()) == [VERIFIED]) else "FAIL",
                f"schema={_ok_s} ok={_ok} verdicts={list(_v.values())}"))

# FP-02: multiplication / division with an explicitly different output unit.
_d = copy.deepcopy(BASE)
_d["space"]["floor_area"] = derived(24000000, "width * depth",
                                    ["space.width", "space.depth"], unit="mm2")
_d["space"]["width"] = fact(6000, unit="mm")
_d["space"]["depth"] = fact(4000, unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FP-02", "A multiplicative [D] with its own unit verifies",
                "PASS" if (_ok and VERIFIED in _v.values()) else "FAIL",
                f"ok={_ok} verdicts={list(_v.values())} {rules_of(_f, 'ERROR')}"))

# FP-03: a [D] built on another [D] (valid chain, no cycle).
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(6000, unit="mm")
_d["space"]["half_width"] = derived(3000, "width / 2", ["space.width"])
_d["space"]["quarter_width"] = derived(1500, "half_width / 2",
                                       ["space.half_width"])
_ok, _f, _v = run(_d)
RESULTS.append(("FP-03", "A [D] chained on another [D] verifies",
                "PASS" if (_ok and list(_v.values()).count(VERIFIED) == 2)
                else "FAIL", f"ok={_ok} verdicts={sorted(_v.values())}"))

# FP-04: whitelisted deterministic functions are usable.
_d = with_derived(derived(2800, "max(ceiling_height, 2000)",
                          ["space.ceiling_height"]))
_ok, _f, _v = run(_d)
RESULTS.append(("FP-04", "Whitelisted deterministic functions are allowed",
                "PASS" if (_ok and VERIFIED in _v.values()) else "FAIL",
                f"ok={_ok} {rules_of(_f, 'ERROR')}"))

# FP-05: a master with no [D] at all is not an error.
_ok, _f, _v = run(copy.deepcopy(BASE))
RESULTS.append(("FP-05", "A master with no derived value is not an error",
                "PASS" if (_ok and not _v) else "FAIL",
                f"ok={_ok} verdicts={_v}"))


# ==========================================================================
# NEGATIVE
# ==========================================================================
# FN-01: THE GAP — false arithmetic that A and B1 both accept.
_d = with_derived(derived(9999, "ceiling_height - 100",
                          ["space.ceiling_height"]))
_a_ok, _ = validate_master(_d, SCHEMA)
_b1_ok, _ = validate_references(_d)
_ok, _f, _v = run(_d)
RESULTS.append(("FN-01", "False arithmetic is caught by B6 (A and B1 cannot)",
                "PASS" if (_a_ok and _b1_ok and not _ok
                           and any(x.rule == "FM-007" for x in _f)
                           and list(_v.values()) == [MISMATCH]) else "FAIL",
                f"A={_a_ok} B1={_b1_ok} B6={_ok} {rules_of(_f, 'ERROR')}"))

# FN-02: the stored value is never silently corrected.
_stored = _d["space"]["floor_level"]["value"]
RESULTS.append(("FN-02", "A mismatching stored value is reported, not fixed",
                "PASS" if (_stored == 9999
                           and any("NOT corrected automatically" in x.message
                                   for x in _f)) else "FAIL",
                f"stored_after_run={_stored}"))

# FN-03: hidden input not declared in derived_from.
_d = with_derived(derived(2700, "ceiling_height - secret_offset",
                          ["space.ceiling_height"]))
_ok, _f, _v = run(_d)
RESULTS.append(("FN-03", "An undeclared input in the formula -> FM-002",
                "PASS" if (not _ok and any(x.rule == "FM-002" for x in _f))
                else "FAIL", f"{rules_of(_f, 'ERROR')}"))

# FN-04: a declared input the formula never uses.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(6000, unit="mm")
_d["space"]["floor_level"] = derived(2700, "ceiling_height - 100",
                                     ["space.ceiling_height", "space.width"])
_ok, _f, _v = run(_d)
RESULTS.append(("FN-04", "A declared-but-unused input -> FM-003",
                "PASS" if any(x.rule == "FM-003" for x in _f) else "FAIL",
                f"{rules_of(_f)}"))

# FN-05: mixing units additively is refused, never converted.
_d = copy.deepcopy(BASE)
_d["space"]["height_m"] = fact(3, unit="mm2")     # deliberately incompatible
_d["space"]["floor_level"] = derived(2803, "ceiling_height + height_m",
                                     ["space.ceiling_height", "space.height_m"],
                                     unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FN-05", "Mixed units in an additive formula -> FM-005",
                "PASS" if (not _ok and any(x.rule == "FM-005" for x in _f))
                else "FAIL", f"{rules_of(_f, 'ERROR')}"))

# FN-06: a circular derivation.
_d = copy.deepcopy(BASE)
_d["space"]["a_val"] = derived(1, "b_val + 1", ["space.b_val"])
_d["space"]["b_val"] = derived(1, "a_val + 1", ["space.a_val"])
_ok, _f, _v = run(_d)
RESULTS.append(("FN-06", "Circular derivation -> FM-006, nothing computed",
                "PASS" if (not _ok and any(x.rule == "FM-006" for x in _f)
                           and set(_v.values()) == {UNCOMPUTABLE}) else "FAIL",
                f"ok={_ok} verdicts={set(_v.values())}"))

# FN-07: design judgement smuggled into a [D].
_d = with_derived(derived(2700, "ceiling_height - 100",
                          ["space.ceiling_height"],
                          note="the best looking proportion for this room"))
_ok, _f, _v = run(_d)
RESULTS.append(("FN-07", "Design language inside a [D] -> FM-009",
                "PASS" if (not _ok and any(x.rule == "FM-009" for x in _f))
                else "FAIL", f"{rules_of(_f, 'ERROR')}"))

# FN-08: division by zero yields UNCOMPUTABLE, never a value.
_d = copy.deepcopy(BASE)
_d["space"]["zero"] = fact(0, unit="mm")
_d["space"]["floor_level"] = derived(0, "ceiling_height / zero",
                                     ["space.ceiling_height", "space.zero"])
_ok, _f, _v = run(_d)
RESULTS.append(("FN-08", "Division by zero -> UNCOMPUTABLE, no value invented",
                "PASS" if (UNCOMPUTABLE in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))


# ==========================================================================
# UNKNOWN / INCOMPLETE INPUTS
# ==========================================================================
# FU-01: an input that is [U] makes the result uncomputable.
_d = copy.deepcopy(BASE)
_d["space"]["unknown_in"] = unknown_fact("U-601", "not surveyed")
_d["space"]["floor_level"] = derived(2700, "unknown_in - 100",
                                     ["space.unknown_in"])
_d["registers"]["unknowns"].append(
    {"id": "U-601", "question": "Value?", "blocking": False, "raised_on": TODAY})
_ok, _f, _v = run(_d)
RESULTS.append(("FU-01", "A [U] input -> FM-004 / UNCOMPUTABLE",
                "PASS" if (any(x.rule == "FM-004" for x in _f)
                           and list(_v.values()) == [UNCOMPUTABLE]) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FU-02: a [P] input is not usable either.
_d = copy.deepcopy(BASE)
_d["space"]["proposed_in"] = fact(2500, status="P", src="AGENT_PROPOSAL",
                                  ref="suggested height", unit="mm",
                                  proposal_id="P-060")
_d["registers"]["proposals"] = [{"id": "P-060", "text": "Lower the ceiling",
                                 "state": "OPEN", "raised_on": TODAY}]
_d["space"]["floor_level"] = derived(2400, "proposed_in - 100",
                                     ["space.proposed_in"])
_ok, _f, _v = run(_d)
RESULTS.append(("FU-02", "A [P] input cannot feed a [D]",
                "PASS" if (list(_v.values()) == [UNCOMPUTABLE]
                           and any(x.rule == "FM-004" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FU-03: UNCOMPUTABLE must not be silently replaced by the stored value.
RESULTS.append(("FU-03", "UNCOMPUTABLE never becomes a guessed value",
                "PASS" if all(v != VERIFIED for v in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FU-04: a non-numeric input cannot be derived from.
_d = copy.deepcopy(BASE)
_d["space"]["floor_level"] = derived(1, "outline + 1", ["space.outline"])
_ok, _f, _v = run(_d)
RESULTS.append(("FU-04", "A non-numeric input -> UNCOMPUTABLE",
                "PASS" if (list(_v.values()) == [UNCOMPUTABLE]) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FU-05: LOGICAL_DEDUCTION is recorded, not faked as arithmetic.
_d = with_derived(derived(2700, "ceiling_height - 100",
                          ["space.ceiling_height"],
                          dtype="LOGICAL_DEDUCTION"))
_ok, _f, _v = run(_d)
RESULTS.append(("FU-05", "LOGICAL_DEDUCTION is not evaluated arithmetically",
                "PASS" if (_ok and list(_v.values()) == [UNCOMPUTABLE]) else "FAIL",
                f"ok={_ok} verdicts={list(_v.values())}"))


# ==========================================================================
# BOUNDARY
# ==========================================================================
# FB-01: floating point noise within tolerance still verifies.
_d = with_derived(derived(2700.0000000001, "ceiling_height - 100",
                          ["space.ceiling_height"]))
_ok, _f, _v = run(_d)
RESULTS.append(("FB-01", "Tiny float noise is tolerated",
                "PASS" if (_ok and VERIFIED in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FB-02: a genuinely wrong value just outside tolerance is caught.
_d = with_derived(derived(2700.01, "ceiling_height - 100",
                          ["space.ceiling_height"]))
_ok, _f, _v = run(_d)
RESULTS.append(("FB-02", "A real 0.01mm discrepancy is still a MISMATCH",
                "PASS" if (not _ok and MISMATCH in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FB-03: zero is a legitimate derived result, not treated as missing.
_d = copy.deepcopy(BASE)
_d["space"]["floor_level"] = derived(0, "ceiling_height - ceiling_height",
                                     ["space.ceiling_height"])
_ok, _f, _v = run(_d)
RESULTS.append(("FB-03", "A derived value of exactly 0 verifies normally",
                "PASS" if (_ok and VERIFIED in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FB-04: a negative derived result is arithmetic, not an error.
_d = copy.deepcopy(BASE)
_d["space"]["floor_level"] = derived(-200, "ceiling_height - 3000",
                                     ["space.ceiling_height"])
_ok, _f, _v = run(_d)
RESULTS.append(("FB-04", "A negative derived result is not an arithmetic error",
                "PASS" if (_ok and VERIFIED in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FB-05: a self-referential one-node cycle is detected.
_d = copy.deepcopy(BASE)
_d["space"]["self_val"] = derived(5, "self_val + 0", ["space.self_val"])
_cyc = derivation_cycles(_d)
RESULTS.append(("FB-05", "A self-referencing derivation is a cycle",
                "PASS" if _cyc else "FAIL", f"cycles={len(_cyc)}"))


# ==========================================================================
# SAFETY — the evaluator must never execute arbitrary code
# ==========================================================================
_attacks = ["__import__('os').system('ls')", "open('/etc/passwd').read()",
            "random.random()", "now()", "[x for x in range(3)]",
            "a if b else c", "lambda: 5", "a.__class__", "exec('x=1')"]
_accepted = [a for a in _attacks if parse_formula(a)[0] is not None]
RESULTS.append(("FS-01", "No arbitrary code / non-determinism can be parsed",
                "PASS" if not _accepted else "FAIL",
                f"accepted={_accepted if _accepted else 'none'}"))

# FS-02: the engine never calls eval/exec.
_src = open(os.path.join(ROOT, "scripts", "validate_formulas.py"),
            encoding="utf-8").read()
_tree = __import__("ast").parse(_src)
_calls = [n.func.id for n in __import__("ast").walk(_tree)
          if isinstance(n, __import__("ast").Call)
          and isinstance(n.func, __import__("ast").Name)]
_danger = sorted({c for c in _calls if c in ("eval", "exec", "compile")})
RESULTS.append(("FS-02", "The engine itself never calls eval / exec / compile",
                "PASS" if not _danger else "FAIL", f"found={_danger}"))

# FS-03: the sandbox rejects an unknown function name.
_t, _e = parse_formula("mystery(a)")
RESULTS.append(("FS-03", "An unknown function is refused, not called",
                "PASS" if _t is None else "FAIL", f"err={_e}"))


# ==========================================================================
# ISOLATION
# ==========================================================================
# FI-01: B6 emits only FM-* codes.
_codes = set()
for _case in (derived(9999, "ceiling_height - 100", ["space.ceiling_height"]),
              derived(2700, "ceiling_height - x", ["space.ceiling_height"]),
              derived(2700, "ceiling_height - 100", ["space.ceiling_height"])):
    _codes |= {x.rule for x in run(with_derived(_case))[1]}
RESULTS.append(("FI-01", "B6 emits no XR-* / WT-* / FC-* / MV-* / DS-* code",
                "PASS" if all(c.startswith("FM-") for c in _codes) else "FAIL",
                f"codes={sorted(_codes)}"))

# FI-02: a B6 mismatch leaves A / B1 / B2 / B3 / B4 / B5 clean.
_d = with_derived(derived(9999, "ceiling_height - 100",
                          ["space.ceiling_height"]))
_a = validate_master(_d, SCHEMA)[0]
_b1 = validate_references(_d)[0]
_b2 = validate_topology(_d)[0]
_b3 = validate_furniture(_d)[0]
_b4 = validate_movement(_d)[0]
_b5 = validate_doors(_d)[0]
_ok, _f, _v = run(_d)
RESULTS.append(("FI-02", "A B6 mismatch disturbs no other layer",
                "PASS" if (_a and _b1 and _b2 and _b3 and _b4 and _b5
                           and not _ok) else "FAIL",
                f"A={_a} B1={_b1} B2={_b2} B3={_b3} B4={_b4} B5={_b5} B6={_ok}"))

# FI-03: no earlier layer imports B6 (dependency stays one-way).
_back = []
for _mod in ("schema_gate", "validate_refs", "validate_topology",
             "validate_furniture", "validate_movement", "validate_doors"):
    if "validate_formulas" in open(
            os.path.join(ROOT, "scripts", f"{_mod}.py"), encoding="utf-8").read():
        _back.append(_mod)
RESULTS.append(("FI-03", "No earlier layer imports B6 (one-way dependency)",
                "PASS" if not _back else "FAIL", f"back_refs={_back}"))

# FI-04: B6 does not re-own A's F4 shape rule. A [D] missing formula entirely
# is A's business; B6 stays silent rather than double-reporting.
_d = copy.deepcopy(BASE)
_bare = {"value": 2700, "status": "D", "source_type": "DERIVED_CALC",
         "source_ref": "computed", "recorded_on": TODAY, "unit": "mm"}
_d["space"]["floor_level"] = _bare
_a_ok, _a_errs = validate_master(_d, SCHEMA)
_ok, _f, _v = run(_d)
RESULTS.append(("FI-04", "A [D] missing formula is A's rule, not re-owned by B6",
                "PASS" if ((not _a_ok) and not _f) else "FAIL",
                f"A_rejected={not _a_ok} B6_findings={len(_f)}"))

# FI-05: B6 performs no geometric check. Scan EXECUTABLE code only: the
# module docstring names B2..B5 precisely to disclaim them, and a disclaimer
# must not be mistaken for an implementation.
_ast0 = __import__("ast")
_t0 = _ast0.parse(_src)
for _n0 in _ast0.walk(_t0):
    if (isinstance(_n0, _ast0.Expr) and isinstance(_n0.value, _ast0.Constant)
            and isinstance(_n0.value.value, str)):
        _n0.value.value = ""
_exec_only = _ast0.unparse(_t0).lower()
_geo = [t for t in ("overlap", "footprint", "swing", "circulation",
                    "aperture", "polygon") if t in _exec_only]
RESULTS.append(("FI-05", "B6 contains no geometric logic of its own",
                "PASS" if not _geo else "FAIL", f"terms={_geo}"))

# FI-06: no standards / ergonomics / optimisation DRIVING behaviour. The
# JUDGEMENT_TOKENS list legitimately contains such words because it is the
# detector that REJECTS them, so it is excluded from the scan.
_scan = _exec_only
_start = _scan.find("judgement_tokens")
if _start != -1:
    _end = _scan.find("]", _start)
    _scan = _scan[:_start] + _scan[_end:]
_bad = [t for t in ("ergonom", "standard_", "recommended_clearance",
                    "optimi", "aesthetic") if t in _scan]
RESULTS.append(("FI-06", "No standards / ergonomics / optimisation drive B6",
                "PASS" if not _bad else "FAIL", f"terms={_bad}"))


# ==========================================================================
# MUTATION
# ==========================================================================
_sweep = []
_cases = [
    ("false value", derived(9999, "ceiling_height - 100",
                            ["space.ceiling_height"]), "FM-007"),
    ("hidden input", derived(2700, "ceiling_height - ghost",
                             ["space.ceiling_height"]), "FM-002"),
    ("unparsable", derived(2700, "ceiling_height ~~ 100",
                           ["space.ceiling_height"]), "FM-001"),
    ("judgement", derived(2700, "ceiling_height - 100",
                          ["space.ceiling_height"],
                          note="best option"), "FM-009"),
    ("non-deterministic", derived(2700, "ceiling_height - random()",
                                  ["space.ceiling_height"]), "FM-001"),
]
for _label, _f2, _expect in _cases:
    _got = {x.rule for x in run(with_derived(_f2))[1]}
    _sweep.append((_label, _expect in _got))
RESULTS.append(("FM-M1", "Mutation sweep: every formula defect is detected",
                "PASS" if all(o for _, o in _sweep) else "FAIL",
                f"{sum(1 for _, o in _sweep if o)}/{len(_sweep)} caught"))

# FM-M2: no false positives on a correct [D], repeated.
_clean = [run(with_derived(derived(2700, "ceiling_height - 100",
                                   ["space.ceiling_height"])))[0]
          for _ in range(3)]
RESULTS.append(("FM-M2", "No false positives on a correct derivation (3 runs)",
                "PASS" if all(_clean) else "FAIL", f"{_clean}"))

# FM-M3: changing ONLY the stored value flips the verdict -> proof the engine
# really recomputes instead of trusting the declaration.
_good = run(with_derived(derived(2700, "ceiling_height - 100",
                                 ["space.ceiling_height"])))[2]
_bad2 = run(with_derived(derived(2701, "ceiling_height - 100",
                                 ["space.ceiling_height"])))[2]
RESULTS.append(("FM-M3", "Changing only the stored value flips the verdict",
                "PASS" if (list(_good.values()) == [VERIFIED]
                           and list(_bad2.values()) == [MISMATCH]) else "FAIL",
                f"2700={list(_good.values())} 2701={list(_bad2.values())}"))

# FM-M4: changing ONLY an input value flips the verdict too.
_d = copy.deepcopy(BASE)
_d["space"]["ceiling_height"] = fact(3000, unit="mm")
_d["space"]["floor_level"] = derived(2700, "ceiling_height - 100",
                                     ["space.ceiling_height"])
_ok, _f, _v = run(_d)
RESULTS.append(("FM-M4", "Changing only an input flips the verdict",
                "PASS" if (not _ok and MISMATCH in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))


# ==========================================================================
# R02 — DIMENSIONAL UNIT ALGEBRA  (FD-*)
# ==========================================================================
# FD-01 (mandated): 2000 mm x 3000 mm -> 6000000 mm2
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(6000000, "width * depth",
                               ["space.width", "space.depth"], unit="mm2")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-01", "2000mm x 3000mm -> 6000000 mm2 verifies",
                "PASS" if (_ok and list(_v.values()) == [VERIFIED]) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FD-02 (mandated): the SAME correct number stored as 'mm' must not VERIFY.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(6000000, "width * depth",
                               ["space.width", "space.depth"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-02", "Right number, wrong dimension (mm) is NOT verified",
                "PASS" if (not _ok and VERIFIED not in _v.values()
                           and any(x.rule == "FM-005" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-03: same dimension (L^2) but wrong unit scale -> m2 must not VERIFY.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(6000000, "width * depth",
                               ["space.width", "space.depth"], unit="m2")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-03", "Correct dimension, wrong unit scale (m2) not verified",
                "PASS" if (not _ok and VERIFIED not in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-04 (mandated): 6000000 mm2 / 3000 mm -> 2000 mm
_d = copy.deepcopy(BASE)
_d["space"]["area"] = fact(6000000, unit="mm2")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(2000, "area / depth",
                               ["space.area", "space.depth"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-04", "6000000 mm2 / 3000 mm -> 2000 mm verifies",
                "PASS" if (_ok and list(_v.values()) == [VERIFIED]) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FD-05: the same division stored as mm2 keeps the wrong dimension out.
_d = copy.deepcopy(BASE)
_d["space"]["area"] = fact(6000000, unit="mm2")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(2000, "area / depth",
                               ["space.area", "space.depth"], unit="mm2")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-05", "mm2/mm declared as mm2 is not verified",
                "PASS" if (not _ok and VERIFIED not in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-06 (mandated): adding different dimensions must never pass.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["t"] = fact(1, unit="s")
_d["space"]["probe"] = derived(2001, "width + t",
                               ["space.width", "space.t"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-06", "Adding different dimensions (mm + s) never verifies",
                "PASS" if (not _ok and VERIFIED not in _v.values()
                           and any(x.rule == "FM-005" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-07: same dimension, different unit, added -> needs explicit conversion.
_d = copy.deepcopy(BASE)
_d["space"]["a_m"] = fact(2, unit="m")
_d["space"]["b_mm"] = fact(500, unit="mm")
_d["space"]["probe"] = derived(2500, "a_m + b_mm",
                               ["space.a_m", "space.b_mm"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-07", "m + mm is refused, never silently converted",
                "PASS" if (not _ok and VERIFIED not in _v.values()
                           and any(x.rule == "FM-005" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-08: a compound unit composes correctly (mm / s -> mm/s).
_d = copy.deepcopy(BASE)
_d["space"]["dist"] = fact(1000, unit="mm")
_d["space"]["dur"] = fact(4, unit="s")
_d["space"]["probe"] = derived(250, "dist / dur",
                               ["space.dist", "space.dur"], unit="mm/s")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-08", "Compound unit mm/s composes and verifies",
                "PASS" if (_ok and list(_v.values()) == [VERIFIED]) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FD-09 BOUNDARY: dimensionless ratio (mm/mm) must not claim to be mm.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["depth"] = fact(4000, unit="mm")
_d["space"]["probe"] = derived(0.5, "width / depth",
                               ["space.width", "space.depth"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-09", "A dimensionless ratio cannot be declared as mm",
                "PASS" if (not _ok and VERIFIED not in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-10 BOUNDARY: an unparseable output unit is INFO/unconfirmed, not VERIFIED
# by accident and not an ERROR either.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(6000000, "width * depth",
                               ["space.width", "space.depth"], unit="furlong2")
_ok, _f, _v = run(_d)
_fd10 = [x for x in _f if x.rule == "FM-005"]
RESULTS.append(("FD-10", "An unparseable unit is reported, never assumed right",
                "PASS" if (_fd10 and all(x.severity == "INFO" for x in _fd10))
                else "FAIL",
                f"sev={[x.severity for x in _fd10]}"))

# FD-11 BOUNDARY: units absent entirely -> arithmetic still checked, unit
# explicitly NOT confirmed (no silent pass as 'dimensionally correct').
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000)
_d["space"]["probe"] = derived(1000, "width / 2", ["space.width"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-11", "Missing input unit -> arithmetic checked, unit INFO",
                "PASS" if (VERIFIED in _v.values()
                           and any(x.rule == "FM-005" and x.severity == "INFO"
                                   for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FD-12 NEGATIVE: sqrt of an odd-powered dimension has no expressible unit.
_d = copy.deepcopy(BASE)
_d["space"]["dist"] = fact(100, unit="mm")
_d["space"]["probe"] = derived(10, "sqrt(dist)", ["space.dist"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-12", "sqrt(mm) has no whole dimension -> not verified",
                "PASS" if (VERIFIED not in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FD-13 NO AUTO-FIX: a dimensional error leaves the stored unit untouched.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["depth"] = fact(3000, unit="mm")
_d["space"]["probe"] = derived(6000000, "width * depth",
                               ["space.width", "space.depth"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FD-13", "A unit error is reported, never auto-corrected",
                "PASS" if (_d["space"]["probe"]["unit"] == "mm"
                           and _d["space"]["probe"]["value"] == 6000000)
                else "FAIL",
                f"unit_after={_d['space']['probe']['unit']}"))


# ==========================================================================
# R02 — INPUT ADMISSIBILITY  (FA-*)
# ==========================================================================
# FA-01 (mandated): an unapproved external standard as an input.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["std_gap"] = fact(100, src="EXTERNAL_STANDARD", unit="mm")
_d["space"]["probe"] = derived(2100, "width + std_gap",
                               ["space.width", "space.std_gap"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FA-01", "An unapproved standard as input -> UNCOMPUTABLE",
                "PASS" if (UNCOMPUTABLE in _v.values()
                           and VERIFIED not in _v.values()
                           and any(x.rule == "FM-004" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FA-02: an agent proposal is a decision, not a measured quantity.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["gap"] = fact(100, src="AGENT_PROPOSAL", unit="mm")
_d["space"]["probe"] = derived(2100, "width + gap",
                               ["space.width", "space.gap"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FA-02", "A proposal disguised as a number -> UNCOMPUTABLE",
                "PASS" if (UNCOMPUTABLE in _v.values()
                           and VERIFIED not in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FA-03: an agent assumption likewise cannot feed a derivation.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["gap"] = fact(100, src="AGENT_ASSUMPTION", unit="mm")
_d["space"]["probe"] = derived(2100, "width + gap",
                               ["space.width", "space.gap"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FA-03", "An assumption cannot feed a [D]",
                "PASS" if (UNCOMPUTABLE in _v.values()
                           and VERIFIED not in _v.values()) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FA-04: an undocumented [D] input breaks lineage.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["ghost_derived"] = {
    "value": 100, "status": "D", "unit": "mm",
    "source_type": "DERIVED_CALC", "source_ref": "somewhere",
    "recorded_on": TODAY}
_d["space"]["probe"] = derived(2100, "width + ghost_derived",
                               ["space.width", "space.ghost_derived"],
                               unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FA-04", "An undocumented [D] input -> UNCOMPUTABLE",
                "PASS" if (UNCOMPUTABLE in _v.values()
                           and VERIFIED not in _v.values()
                           and any(x.rule == "FM-004" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FA-05 POSITIVE CONTROL: a genuine confirmed input still verifies, proving
# FA-01..04 reject for the stated reason and not by blanket refusal.
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["gap"] = fact(100, unit="mm")
_d["space"]["probe"] = derived(2100, "width + gap",
                               ["space.width", "space.gap"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FA-05", "A genuine [C] input still verifies (no over-block)",
                "PASS" if (_ok and list(_v.values()) == [VERIFIED]) else "FAIL",
                f"verdicts={list(_v.values())}"))

# FA-06: a properly documented [D] input IS admissible (chained lineage).
_d = copy.deepcopy(BASE)
_d["space"]["width"] = fact(2000, unit="mm")
_d["space"]["half"] = derived(1000, "width / 2", ["space.width"], unit="mm")
_d["space"]["probe"] = derived(3000, "width + half",
                               ["space.width", "space.half"], unit="mm")
_ok, _f, _v = run(_d)
RESULTS.append(("FA-06", "A documented [D] input is admissible",
                "PASS" if (_ok and set(_v.values()) == {VERIFIED}) else "FAIL",
                f"verdicts={list(_v.values())}"))


# ==========================================================================
# R02 — MUTATION ON UNITS AND DIMENSIONS  (FX-*)
# ==========================================================================
# FX-01 (mandated): mutating ONLY the output unit must change the verdict.
def _area_case(out_unit):
    d = copy.deepcopy(BASE)
    d["space"]["width"] = fact(2000, unit="mm")
    d["space"]["depth"] = fact(3000, unit="mm")
    d["space"]["probe"] = derived(6000000, "width * depth",
                                  ["space.width", "space.depth"], unit=out_unit)
    return run(d)

_g_ok, _g_f, _g_v = _area_case("mm2")
_b_ok, _b_f, _b_v = _area_case("mm")
RESULTS.append(("FX-01", "Mutating only the unit flips VERIFIED -> not verified",
                "PASS" if (list(_g_v.values()) == [VERIFIED]
                           and VERIFIED not in _b_v.values()) else "FAIL",
                f"mm2={list(_g_v.values())} mm={list(_b_v.values())}"))

# FX-02: mutating ONLY an input's unit is detected.
def _input_unit_case(u):
    d = copy.deepcopy(BASE)
    d["space"]["a"] = fact(2000, unit="mm")
    d["space"]["b"] = fact(500, unit=u)
    d["space"]["probe"] = derived(2500, "a + b",
                                  ["space.a", "space.b"], unit="mm")
    return run(d)

_u_ok, _u_f, _u_v = _input_unit_case("mm")
_w_ok, _w_f, _w_v = _input_unit_case("deg")
RESULTS.append(("FX-02", "Mutating one input's unit is caught",
                "PASS" if (list(_u_v.values()) == [VERIFIED]
                           and VERIFIED not in _w_v.values()) else "FAIL",
                f"mm={list(_u_v.values())} deg={list(_w_v.values())}"))

# FX-03: a sweep — every dimensional mutation must be caught.
_sweep = [("mm", False), ("mm2", True), ("m2", False), ("deg", False),
          ("count", False), ("none", False), ("mm/s", False)]
_missed = []
for _unit, _should_verify in _sweep:
    _s_ok, _s_f, _s_v = _area_case(_unit)
    _verified = (VERIFIED in _s_v.values())
    if _verified != _should_verify:
        _missed.append(_unit)
RESULTS.append(("FX-03", "Dimensional mutation sweep: only mm2 may verify",
                "PASS" if not _missed else "FAIL",
                f"{len(_sweep) - len(_missed)}/{len(_sweep)} correct"))

# FX-04: mutating an input's SOURCE (fact -> standard) flips admissibility,
# with the numbers left completely untouched.
def _src_case(src):
    d = copy.deepcopy(BASE)
    d["space"]["width"] = fact(2000, unit="mm")
    d["space"]["gap"] = fact(100, src=src, unit="mm")
    d["space"]["probe"] = derived(2100, "width + gap",
                                  ["space.width", "space.gap"], unit="mm")
    return run(d)

_c_ok, _c_f, _c_v = _src_case("CLIENT_INPUT")
_e_ok, _e_f, _e_v = _src_case("EXTERNAL_STANDARD")
RESULTS.append(("FX-04", "Mutating only the input's source flips the verdict",
                "PASS" if (list(_c_v.values()) == [VERIFIED]
                           and UNCOMPUTABLE in _e_v.values()) else "FAIL",
                f"client={list(_c_v.values())} standard={list(_e_v.values())}"))

# FX-05 (added after a surviving mutant): dimensions that share the SAME
# scale factor must still be separated. Neutering the dimension comparison
# passed every earlier test because the scale test happened to cover them;
# s, deg, m, count and kelvin all have scale 1.0, so only a true dimension
# comparison can tell them apart.
_d = copy.deepcopy(BASE)
_d["space"]["t"] = fact(90, unit="s")
_d["space"]["probe"] = derived(90, "t * 1", ["space.t"], unit="deg")
_ok, _f, _v = run(_d)
RESULTS.append(("FX-05", "Same-scale but different dimension (s vs deg) caught",
                "PASS" if (VERIFIED not in _v.values()
                           and any(x.rule == "FM-005" for x in _f)) else "FAIL",
                f"verdicts={list(_v.values())} {rules_of(_f)}"))

# FX-05: the dimensional checker is genuinely wired in — if infer_dimension
# were stubbed out to always agree, FD-02 would silently pass. Prove the code
# path is reachable and decisive.
_probe_dim = infer_dimension(
    __import__("ast").parse("w * d", mode="eval"), {"w": "mm", "d": "mm"})
RESULTS.append(("FX-06", "infer_dimension composes mm x mm into L^2 at 1e-6",
                "PASS" if (_probe_dim[0] == "OK" and _probe_dim[2] == {"L": 2}
                           and abs(_probe_dim[1] - 1e-6) < 1e-18) else "FAIL",
                f"{_probe_dim}"))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-B6 — FORMULA / DERIVED-VALUE INTEGRITY TEST REPORT")
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
