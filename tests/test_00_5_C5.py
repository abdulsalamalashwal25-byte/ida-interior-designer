#!/usr/bin/env python3
"""Phase 00.5-C5 — Presentation Layer (Class B, SVG, Tier 0 + Tier 1).

Reference: C5 Architecture CLOSED + Gate 1 APPROVED WITH CONDITIONS.

WHAT THIS SUITE MUST PROVE
  * C5 consumes the GA artifact published by the A path and NOTHING else
  * the artifact is not mutated (before/after immutability is the PRIMARY
    proof, per CONDITION-02)
  * only the six approved parameters are admitted, under PP-1..PP-8
  * no silent default, no invented semantic/unit/interpretation
  * print_scale cannot smuggle a geometric transform
  * PARTIAL derives from element omissions only, and is declared
  * C5 issues no fidelity judgement and writes nothing anywhere

DISCIPLINE (inherited)
  AS-C2-16 — mutate through the module (C5.x), never a bound import.
  AS-C2-17 — expectations are literals, never constants read from the engine.
  AS-C4-18 — no default-argument binding of mutable contract constants.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import c5_presentation as C5                                         # noqa: E402
import c3_svg_emitter as C3                                          # noqa: E402
import c2_fingerprint as C2                                          # noqa: E402

RESULTS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def fact(value, status="C", src="CLIENT_INPUT", unit="mm"):
    return {"value": value, "unit": unit, "status": status,
            "source_type": src, "source_ref": "intake/p1",
            "recorded_on": "2026-09-12"}


def master(partial=False):
    m = {
        "meta": {"project_id": "PRJ-01", "master_revision": "R01"},
        "space": {"outline": fact([[0, 0], [6000, 0], [6000, 4000], [0, 4000]])},
        "walls": [
            {"id": "W-01", "start": fact([0, 0]), "end": fact([6000, 0])},
            {"id": "W-02", "start": fact([6000, 0]), "end": fact([6000, 4000])},
        ],
        "openings": [
            {"id": "OP-01", "kind": "door", "host_wall": "W-01",
             "offset": fact(1000), "width": fact(900), "height": fact(2100)},
        ],
    }
    if partial:
        m["walls"].append({"id": "W-03", "start": fact([6000, 4000]),
                           "end": fact([0, 4000], "U")})
    return m


def ga_of(m):
    """THE ONLY legitimate geometry source: the A path's published artifact."""
    return C3.emit_svg(m, identity=m["meta"])["assembly"]


IDENT = {"project_id": "PRJ-01", "master_revision": "R01"}
GA = ga_of(master())
GA_PARTIAL = ga_of(master(partial=True))

GOOD_PARAMS = {
    "color": "#334155",
    "line_weight": {"value": 2, "unit": "mm"},
    "shadow": False,
    "label": "Presentation Sheet",
    "sheet_order": 1,
    "print_scale": {"page_size": "A3", "viewport": "fit"},
}


# ==========================================================================
# 1. POSITIVE
# ==========================================================================
r = C5.emit_class_b(GA, GOOD_PARAMS, identity=IDENT)
record("C5-P-01", "Valid GA + valid parameters emit a class B SVG",
       "EMITTED", f"{r['status']}", r["status"] == "EMITTED")

record("C5-P-02", "Output is stamped CLASS B, not A",
       "CLASS B stamp present, no CLASS A",
       f"B={'CLASS B' in r['svg']}, A={'CLASS A' in r['svg']}",
       "CLASS B" in r["svg"] and "CLASS A" not in r["svg"])

record("C5-P-03", "All six approved parameters are admitted",
       "6 admitted, 0 rejected",
       f"adm={len(r['parameters_admitted'])}, rej={len(r['parameters_rejected'])}",
       len(r["parameters_admitted"]) == 6 and not r["parameters_rejected"])

record("C5-P-04", "Admitted colour and line weight reach the output",
       "stroke + stroke-width present",
       f"stroke={'stroke=\"#334155\"' in r['svg']}, "
       f"width={'stroke-width=\"2\"' in r['svg']}",
       'stroke="#334155"' in r["svg"] and 'stroke-width="2"' in r["svg"])

record("C5-P-05", "Geometry in B matches the artifact coordinates exactly",
       "W-01 0,0 -> 6000,0",
       f"{'x1=\"0\" y1=\"0\" x2=\"6000\" y2=\"0\"' in r['svg']}",
       'x1="0" y1="0" x2="6000" y2="0"' in r["svg"])

record("C5-P-06", "Openings carry their A-path positions unchanged",
       "OP-01 at 1000 -> 1900",
       f"{'x1=\"1000.0\"' in r['svg'] and 'x2=\"1900.0\"' in r['svg']}",
       'x1="1000.0"' in r["svg"] and 'x2="1900.0"' in r["svg"])

record("C5-P-07", "Complete artifact yields COMPLETE coverage",
       "COMPLETE", f"{r['coverage']}", r["coverage"] == "COMPLETE")

_ev = C5.presentation_evidence(r)
record("C5-P-08", "Evidence pack carries source, parameters and coverage",
       "all sections present",
       f"{[k for k in ('geometry_source', 'parameters_admitted', 'coverage') if _ev.get(k)]}",
       all(_ev.get(k) for k in ("geometry_source", "parameters_admitted",
                                "coverage")))

record("C5-P-09", "Output declares Tier 0+1 lineage from the artifact",
       "contract_tiers carried",
       f"{_ev['lineage_evidence']['contract_tiers']}",
       _ev["lineage_evidence"]["contract_tiers"] == ["TIER-0", "TIER-1"])


# ==========================================================================
# 2. NEGATIVE — every required case
# ==========================================================================
def rejected_codes(rec, name=None):
    return [v["code"] for v in rec["parameters_rejected"]
            if name is None or v["name"] == name]


r_absent = C5.emit_class_b(GA, {}, identity=IDENT)
record("C5-N-01", "parameter absent -> nothing applied, no default invented",
       "no stroke attribute at all",
       f"stroke={'stroke=' in r_absent['svg']}, adm={len(r_absent['parameters_admitted'])}",
       "stroke=" not in r_absent["svg"].replace('stroke=""', "")
       and not r_absent["parameters_admitted"])

r_unk = C5.emit_class_b(GA, {"": "x"}, identity=IDENT)
record("C5-N-02", "parameter unknown/unnamed -> declared rejection RJ-02",
       "RJ-02", f"{rejected_codes(r_unk)}", "RJ-02" in rejected_codes(r_unk))

r_out = C5.emit_class_b(GA, {"opacity": 0.5, "font": "Arial"}, identity=IDENT)
record("C5-N-03", "parameter outside the six -> RJ-01, not silently ignored",
       "two RJ-01 rejections",
       f"{rejected_codes(r_out)}",
       rejected_codes(r_out).count("RJ-01") == 2)

r_nosem = C5.emit_class_b(GA, {"shadow": {"weird": 1}}, identity=IDENT)
record("C5-N-04", "parameter with no contract semantic -> RJ-03",
       "RJ-03", f"{rejected_codes(r_nosem, 'shadow')}",
       "RJ-03" in rejected_codes(r_nosem, "shadow"))

r_nounit = C5.emit_class_b(GA, {"line_weight": 2}, identity=IDENT)
record("C5-N-05", "line_weight without a unit -> RJ-04, unit never assumed",
       "RJ-04", f"{rejected_codes(r_nounit, 'line_weight')}",
       "RJ-04" in rejected_codes(r_nounit, "line_weight"))

record("C5-N-06", "Rejected parameter injects no silent default",
       "no stroke-width emitted",
       f"{'stroke-width' in r_nounit['svg']}",
       "stroke-width" not in r_nounit["svg"])

r_scale = C5.emit_class_b(GA, {"print_scale": {"scale_factor": 2.0}},
                          identity=IDENT)
record("C5-N-07", "print_scale with a scale factor -> RJ-05 geometry impact",
       "RJ-05", f"{rejected_codes(r_scale, 'print_scale')}",
       "RJ-05" in rejected_codes(r_scale, "print_scale"))

record("C5-N-08", "Rejected scaling leaves coordinates untouched",
       "6000 still 6000",
       f"{'x2=\"6000\"' in r_scale['svg']}", 'x2="6000"' in r_scale["svg"])

_src = open(os.path.join(ROOT, "scripts", "c5_presentation.py"),
            encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())

# Prose that DENIES a behaviour ("C5 does not assemble", "NOT an artifact_id")
# is documentation, not the behaviour. Checks for forbidden calls/identifiers
# must therefore run against code with string literals stripped too —
# otherwise a disclaimer reads as a violation (the false-positive class seen
# in C2/C3/C4).
_code_no_strings = re.sub(r'"[^"]*"', '""', _exec_only)
_code_no_strings = re.sub(r"'[^']*'", "''", _code_no_strings)

record("C5-N-09", "No second GA assembly: assemble() is never called",
       "no assemble call in executable code",
       f"call={'assemble(' in _code_no_strings}, "
       f"name={'assemble' in _code_no_strings}",
       "assemble" not in _code_no_strings)

record("C5-N-10", "No alternate geometry source: master/schema never read",
       "no master access",
       f"{[t for t in ('project_master', 'schema_gate', 'json.load') if t in _exec_only]}",
       not [t for t in ("project_master", "schema_gate", "json.load")
            if t in _exec_only])

r_lbl = C5.emit_class_b(GA, {"label": "Wall 3600 mm"}, identity=IDENT)
record("C5-N-11", "label carrying a number -> RJ-06 (Tier 3 risk)",
       "RJ-06", f"{rejected_codes(r_lbl, 'label')}",
       "RJ-06" in rejected_codes(r_lbl, "label"))

r_none = C5.emit_class_b(None, GOOD_PARAMS, identity=IDENT)
record("C5-N-12", "No GA artifact -> abstain C5-ABS-01",
       "C5-ABS-01", f"{(r_none['abstention'] or {}).get('code')}",
       r_none["status"] == "ABSTAIN"
       and r_none["abstention"]["code"] == "C5-ABS-01")

r_empty = C5.emit_class_b({"walls": [], "outline": None,
                           "not_represented": []}, identity=IDENT)
record("C5-N-13", "Artifact with no eligible geometry -> abstain, no empty B",
       "C5-ABS-02", f"{(r_empty['abstention'] or {}).get('code')}",
       r_empty["status"] == "ABSTAIN"
       and r_empty["abstention"]["code"] == "C5-ABS-02")

record("C5-N-14", "C5 issues no fidelity self-claim",
       "no verdict key; fidelity NOT_ASSESSED",
       f"keys={[k for k in ('fidelity_ok', 'matches_master', 'approved', 'verified') if k in _exec_only]}",
       not [k for k in ('"fidelity_ok"', '"matches_master"', '"approved"',
                        '"verified"') if k in _exec_only]
       and "NOT_ASSESSED" in r["fidelity"])

record("C5-N-15", "C5 requests no engineering fingerprint",
       "NOT_ISSUED",
       f"{'NOT_ISSUED' in r['engineering_fingerprint']}",
       "NOT_ISSUED" in r["engineering_fingerprint"]
       and "issue_engineering_fingerprint" not in _exec_only)


# ==========================================================================
# 3. A/P/U · NOT_PRESENT · UNKNOWN · UNCOMPUTABLE  (state semantics)
# ==========================================================================
m_a = master()
m_a["walls"][1]["start"]["status"] = "A"
m_a["walls"][1]["start"]["approval_state"] = "APPROVED"
ga_a = ga_of(m_a)
r_a = C5.emit_class_b(ga_a, GOOD_PARAMS, identity=IDENT)
record("C5-ST-01", "APPROVED [A] never reaches B as geometry",
       "W-02 absent from output",
       f"{'data-id=\"W-02\"' in r_a['svg']}",
       'data-id="W-02"' not in r_a["svg"])

m_p = master()
m_p["walls"][1]["start"]["status"] = "P"
r_p = C5.emit_class_b(ga_of(m_p), GOOD_PARAMS, identity=IDENT)
record("C5-ST-02", "[P] proposal never becomes presented geometry",
       "W-02 absent",
       f"{'data-id=\"W-02\"' in r_p['svg']}",
       'data-id="W-02"' not in r_p["svg"])

r_u = C5.emit_class_b(GA_PARTIAL, GOOD_PARAMS, identity=IDENT)
record("C5-ST-03", "[U]/UNKNOWN is excluded and declared, never drawn as zero",
       "W-03 absent, omission declared",
       f"absent={'data-id=\"W-03\"' not in r_u['svg']}, "
       f"omissions={len(r_u['omissions'])}",
       'data-id="W-03"' not in r_u["svg"] and len(r_u["omissions"]) >= 1)

m_np = master()
m_np["openings"] = []
r_np = C5.emit_class_b(ga_of(m_np), GOOD_PARAMS, identity=IDENT)
record("C5-ST-04", "NOT_PRESENT-style absence draws nothing and stays COMPLETE",
       "no openings, COMPLETE",
       f"coverage={r_np['coverage']}, openings={'data-kind' in r_np['svg']}",
       r_np["coverage"] == "COMPLETE" and "data-kind" not in r_np["svg"])

_uncomp_codes = [n.get("code") for n in GA_PARTIAL.get("not_represented", [])]
record("C5-ST-05", "UNCOMPUTABLE/omission verdicts are consumed, not re-derived",
       "codes consumed from the artifact as-is",
       f"{sorted(set(_uncomp_codes))}",
       all(c.startswith("NR-") for c in _uncomp_codes)
       and "NR-" not in _exec_only.replace("NR-01", "").replace("NR-02", "")
           .replace("NR-03", "").replace("NR-04", "").replace("NR-05", "")
           .replace("NR-06", ""))


# ==========================================================================
# 4. GEOMETRY IMMUTABILITY  (PRIMARY proof — CONDITION-02)
# ==========================================================================
_before = copy.deepcopy(GA)
_r_imm = C5.emit_class_b(GA, GOOD_PARAMS, identity=IDENT)
record("C5-IMM-01", "PRIMARY: GA artifact is byte-identical before and after",
       "deep equality", f"{_before == GA}", _before == GA)

_before_p = copy.deepcopy(GA_PARTIAL)
C5.emit_class_b(GA_PARTIAL, GOOD_PARAMS, identity=IDENT)
record("C5-IMM-02", "PRIMARY: partial artifact is also unmutated",
       "deep equality", f"{_before_p == GA_PARTIAL}",
       _before_p == GA_PARTIAL)

_d1 = C2.provisional_digest(_before)["digest"]
_d2 = C2.provisional_digest(GA)["digest"]
record("C5-IMM-03", "Diagnostic digest of the artifact is unchanged",
       "same provisional digest", f"{_d1 == _d2}", _d1 == _d2)

# Reverse extraction — SECONDARY only (CONDITION-02).
_svg_ids = set(re.findall(r'data-id="([^"]+)"', _r_imm["svg"]))
_ga_ids = {w["id"] for w in GA["walls"]} | {o["id"] for o in GA["openings"]}
record("C5-IMM-04", "SECONDARY: element IDs in B equal those in the artifact",
       "identical id sets", f"{sorted(_svg_ids)}", _svg_ids == _ga_ids)

record("C5-IMM-05", "SECONDARY: element count in B equals the artifact count",
       "3 primitives", f"{len(re.findall(r'<line ', _r_imm['svg']))}",
       len(re.findall(r"<line ", _r_imm["svg"])) == len(GA["walls"]) +
       len(GA["openings"]))

_coords = re.findall(r'x1="([^"]+)" y1="([^"]+)" x2="([^"]+)" y2="([^"]+)"',
                     _r_imm["svg"])
_wall_coords = [(str(w["start"]["value"][0]), str(w["start"]["value"][1]),
                 str(w["end"]["value"][0]), str(w["end"]["value"][1]))
                for w in GA["walls"]]
record("C5-IMM-06", "SECONDARY: wall coordinates round-trip verbatim",
       "match artifact values", f"{_coords[:2] == _wall_coords}",
       _coords[:2] == _wall_coords)

record("C5-IMM-07", "No rounding or quantization anywhere in C5",
       "no round()/quantize", f"{'round(' in _exec_only}",
       "round(" not in _exec_only and "quantiz" not in _exec_only.lower())

record("C5-IMM-08", "Units are never converted",
       "no conversion factors",
       f"{'* 1000' in _exec_only or '/ 1000' in _exec_only}",
       "* 1000" not in _exec_only and "/ 1000" not in _exec_only)

_m_topo = master()
_ga_topo = ga_of(_m_topo)
_r_topo = C5.emit_class_b(_ga_topo, GOOD_PARAMS, identity=IDENT)
record("C5-IMM-09", "Topology (host_wall relationships) is not altered",
       "artifact host_wall intact",
       f"{_ga_topo['openings'][0]['host_wall']}",
       _ga_topo["openings"][0]["host_wall"] == "W-01")


# ==========================================================================
# 5. PARTIAL
# ==========================================================================
record("C5-PT-01", "Partial artifact yields PARTIAL coverage",
       "PARTIAL", f"{r_u['coverage']}", r_u["coverage"] == "PARTIAL")

record("C5-PT-02", "PARTIAL marker is visible inside the SVG",
       "===== PARTIAL ===== present",
       f"{'===== PARTIAL =====' in r_u['svg']}",
       "===== PARTIAL =====" in r_u["svg"])

record("C5-PT-03", "SVG states it is NOT a complete design",
       "explicit statement",
       f"{'NOT' in r_u['svg'] and 'complete design' in r_u['svg']}",
       "NOT a complete design" in r_u["svg"])

record("C5-PT-04", "Omitted elements are listed with codes and reasons",
       "omission list present",
       f"{'OMITTED ELEMENTS' in r_u['svg']}",
       "OMITTED ELEMENTS" in r_u["svg"] and bool(r_u["omissions"]))

record("C5-PT-05", "PARTIAL does not forfeit class B",
       "class still B", f"{r_u['class']}", r_u["class"] == "B")

record("C5-PT-06", "NR-05 alone never makes an output PARTIAL",
       "complete artifact has NR-05 yet stays COMPLETE",
       f"nr05={any(n['code'] == 'NR-05' for n in GA['not_represented'])}, "
       f"coverage={r['coverage']}",
       any(n["code"] == "NR-05" for n in GA["not_represented"])
       and r["coverage"] == "COMPLETE")

record("C5-PT-07", "PARTIAL is never auto-promoted to COMPLETE",
       "coverage stays PARTIAL on re-run",
       f"{C5.emit_class_b(GA_PARTIAL, GOOD_PARAMS)['coverage']}",
       C5.emit_class_b(GA_PARTIAL, GOOD_PARAMS)["coverage"] == "PARTIAL")


# ==========================================================================
# 6. BOUNDARY
# ==========================================================================
record("C5-BD-01", "Zero parameters still emits a valid B output",
       "EMITTED", f"{r_absent['status']}", r_absent["status"] == "EMITTED")

record("C5-BD-02", "All six together are admitted without interference",
       "6 admitted", f"{len(r['parameters_admitted'])}",
       len(r["parameters_admitted"]) == 6)

_r_one = C5.emit_class_b(GA, {"color": "#000"}, identity=IDENT)
record("C5-BD-03", "A single parameter applies without implying others",
       "colour only, no stroke-width",
       f"{'stroke=\"#000\"' in _r_one['svg']}, "
       f"width={'stroke-width' in _r_one['svg']}",
       'stroke="#000"' in _r_one["svg"]
       and "stroke-width" not in _r_one["svg"])

_m_no_op = master()
_m_no_op["openings"] = []
record("C5-BD-04", "Artifact with no openings still emits",
       "EMITTED",
       f"{C5.emit_class_b(ga_of(_m_no_op), GOOD_PARAMS)['status']}",
       C5.emit_class_b(ga_of(_m_no_op), GOOD_PARAMS)["status"] == "EMITTED")

_r_ps_ok = C5.emit_class_b(GA, {"print_scale": {"page_size": "A1"}},
                           identity=IDENT)
record("C5-BD-05", "Framing-only print_scale is admitted",
       "admitted, geometry unchanged",
       f"adm={[v['name'] for v in _r_ps_ok['parameters_admitted']]}",
       any(v["name"] == "print_scale"
           for v in _r_ps_ok["parameters_admitted"])
       and 'x2="6000"' in _r_ps_ok["svg"])

_r_mixed = C5.emit_class_b(GA, {"color": "#111", "opacity": 0.4},
                           identity=IDENT)
record("C5-BD-06", "Mixed valid/invalid set: valid applies, invalid declared",
       "1 admitted, 1 rejected",
       f"adm={len(_r_mixed['parameters_admitted'])}, "
       f"rej={len(_r_mixed['parameters_rejected'])}",
       len(_r_mixed["parameters_admitted"]) == 1
       and len(_r_mixed["parameters_rejected"]) == 1)


# ==========================================================================
# 7. MUTATION  (through the module; literal expectations)
# ==========================================================================
def mutate(tid, scenario, attr, value, probe, expect=True):
    original = getattr(C5, attr)
    setattr(C5, attr, value)
    try:
        got = probe()
    finally:
        setattr(C5, attr, original)
    record(tid, scenario, f"detected={expect}", f"detected={got}",
           got == expect)


def _probe_out_of_contract():
    res = C5.emit_class_b(GA, {"opacity": 0.5}, identity=IDENT)
    return "RJ-01" not in [v["code"] for v in res["parameters_rejected"]]


mutate("C5-M-01", "Widen the approved parameter list -> C5-N-03 must die",
       "APPROVED_PARAMETERS",
       C5.APPROVED_PARAMETERS + ("opacity",), _probe_out_of_contract)


def _probe_partial_lost():
    res = C5.emit_class_b(GA_PARTIAL, GOOD_PARAMS, identity=IDENT)
    return res["coverage"] != "PARTIAL"


mutate("C5-M-02", "Empty the partial-omission codes -> PARTIAL tests must die",
       "PARTIAL_OMISSION_CODES", (), _probe_partial_lost)


def _probe_nr05_counts():
    """If NR-05 counted as partial, a COMPLETE artifact would turn PARTIAL."""
    res = C5.emit_class_b(GA, GOOD_PARAMS, identity=IDENT)
    return res["coverage"] == "PARTIAL"


mutate("C5-M-03", "Count NR-05 as partial -> C5-PT-06 must die",
       "PARTIAL_OMISSION_CODES",
       tuple(list(C5.PARTIAL_OMISSION_CODES) + ["NR-05"]), _probe_nr05_counts)


def _probe_framing_widened():
    res = C5.emit_class_b(GA, {"print_scale": {"scale_factor": 2.0}},
                          identity=IDENT)
    return "RJ-05" not in [v["code"] for v in res["parameters_rejected"]]


mutate("C5-M-04", "Allow scale_factor as framing -> C5-N-07 must die",
       "FRAMING_KEYS", C5.FRAMING_KEYS + ("scale_factor",),
       _probe_framing_widened)


def _probe_unit_assumed():
    res = C5.emit_class_b(GA, {"line_weight": 2}, identity=IDENT)
    return "RJ-04" not in [v["code"] for v in res["parameters_rejected"]]


# Isolating the unit rule: the bare-value branch is the only guard for it.
_orig_admit = C5.admit_parameter


def _lax_admit(name, value, declared_by="caller"):
    if name == "line_weight" and not isinstance(value, dict):
        return C5.ParameterVerdict(name, value, declared_by, C5.ADMITTED)
    return _orig_admit(name, value, declared_by)


C5.admit_parameter = _lax_admit
try:
    _m05 = _probe_unit_assumed()
finally:
    C5.admit_parameter = _orig_admit
record("C5-M-05", "Assume a unit for line_weight -> C5-N-05 must die",
       "detected=True", f"detected={_m05}", _m05)


def _probe_mutating_ga():
    """If C5 stopped copying, the caller's artifact would be mutated."""
    probe_ga = copy.deepcopy(GA)
    snapshot = copy.deepcopy(probe_ga)
    C5.emit_class_b(probe_ga, GOOD_PARAMS, identity=IDENT)
    return snapshot != probe_ga


_orig_deepcopy = C5.copy.deepcopy
C5.copy.deepcopy = lambda x: x          # remove the immutability guard
try:
    # FORMAL CLASSIFICATION: DEFENSIVE-GUARD / NON-ACTIVE MUTATION.
    # Removing the guard does NOT mutate the artifact today, because the
    # current emission path never writes into `ga`. This test therefore does
    # NOT prove deepcopy is behaviourally required, and it is NOT counted as a
    # killed mutation. It is recorded as-is; the implementation is not
    # complicated artificially just to force a kill.
    _m06_mutated = _probe_mutating_ga()
finally:
    C5.copy.deepcopy = _orig_deepcopy
record("C5-M-06", "DEFENSIVE-GUARD / NON-ACTIVE MUTATION (not a kill)",
       "guard present; mutation does not currently alter behaviour",
       f"guard={'copy.deepcopy' in _exec_only}, mutated={_m06_mutated}, "
       f"counted_as_killed=False",
       "copy.deepcopy" in _exec_only)

# CONTROL — a cosmetic change must flip nothing.
_c_before = C5.emit_class_b(GA, GOOD_PARAMS, identity=IDENT)["status"]
_orig_cls = C5.CLASS_B
C5.CLASS_B = "B "
_c_after = C5.emit_class_b(GA, GOOD_PARAMS, identity=IDENT)["status"]
C5.CLASS_B = _orig_cls
record("C5-M-07", "CONTROL: cosmetic change does not alter emission",
       "EMITTED before and after", f"{_c_before}/{_c_after}",
       _c_before == "EMITTED" and _c_after == "EMITTED")


# ==========================================================================
# 8. ISOLATION
# ==========================================================================
_validators = ["validate_topology", "validate_furniture", "validate_movement",
               "validate_doors", "validate_formulas", "validate_outputs",
               "validate_refs", "validate_revisions", "validate_lifecycle",
               "validate_temporal", "validate_blocking", "schema_gate"]
record("C5-ISO-01", "C5 imports no B-series validator", "none",
       f"{[v for v in _validators if f'import {v}' in _src]}",
       not [v for v in _validators if f"import {v}" in _src])

record("C5-ISO-02", "C5 does not import C3 or C4",
       "no c3/c4 import",
       f"{[m for m in ('c3_svg_emitter', 'c3_geometry_assembly', 'c4_quantities') if f'import {m}' in _src]}",
       not [m for m in ("c3_svg_emitter", "c3_geometry_assembly",
                        "c4_quantities") if f"import {m}" in _src])

record("C5-ISO-03", "C5 does not parse C3 SVG as a geometry source",
       "no svg parsing",
       f"{[t for t in ('findall', 'ElementTree', 'parse(') if t in _exec_only]}",
       not [t for t in ("findall", "ElementTree", "parse(")
            if t in _exec_only])

record("C5-ISO-04", "C5 never touches outputs[]",
       "no outputs reference",
       f"{'outputs' in _exec_only}", "outputs" not in _exec_only)

record("C5-ISO-05", "C5 does not re-derive omission verdicts",
       "codes consumed as constants",
       f"{'NR-01' in _exec_only}", "NR-01" in _exec_only
       and "def classify" not in _exec_only)

record("C5-ISO-06", "C5 produces no manifest (C6 owns it)",
       "no manifest construction",
       f"{'manifest' in _exec_only.lower()}",
       "manifest" not in _exec_only.lower())


# ==========================================================================
# 9. ANTI-SMUGGLING
# ==========================================================================
record("C5-AS-01", "No parameter can alter geometry (AS-C5-01)",
       "geometry identical with and without parameters",
       f"{re.findall(r'x2=\"6000\"', r['svg']) == re.findall(r'x2=\"6000\"', r_absent['svg'])}",
       re.findall(r'x2="6000"', r["svg"])
       == re.findall(r'x2="6000"', r_absent["svg"]))

record("C5-AS-02", "No alternate geometry source exists (AS-C5-02)",
       "artifact only",
       f"{'ga_artifact' in _exec_only}", "ga_artifact" in _exec_only)

record("C5-AS-05", "No silent default injection (AS-C5-05)",
       "no default colour/width constants",
       f"{[t for t in ('#000', '#fff', 'default_color') if t in _exec_only]}",
       not [t for t in ("#000", "#fff", "default_color")
            if t in _exec_only])

record("C5-AS-07", "AI/class C cannot feed B (AS-C5-07)",
       "no AI source path",
       f"{[t for t in ('AI_IMAGE', 'ai_mood') if t in _exec_only]}",
       not [t for t in ("AI_IMAGE", "ai_mood") if t in _exec_only])

record("C5-AS-09", "B cannot be presented as A (AS-C5-09)",
       "class is B, stamp says B",
       f"{r['class']}", r["class"] == "B" and "CLASS A" not in r["svg"])

record("C5-AS-10", "No partial -> complete promotion (AS-C5-10)",
       "PARTIAL preserved", f"{r_u['coverage']}", r_u["coverage"] == "PARTIAL")

record("C5-AS-19", "C5 never claims non-deviation (AS-C5-19)",
       "fidelity NOT_ASSESSED + D named",
       f"{'NOT_ASSESSED' in r['fidelity'] and 'D' in r['fidelity']}",
       "NOT_ASSESSED" in r["fidelity"]
       and "Generator != Independent Verifier" in r["fidelity"])

record("C5-AS-20", "No GA re-assembly drift (AS-C5-20)",
       "assemble never referenced in code",
       f"{'assemble' in _code_no_strings}",
       "assemble" not in _code_no_strings)

record("C5-AS-21", "No artifact mutation (AS-C5-21)",
       "deepcopy guard + equality proof",
       f"{'copy.deepcopy' in _exec_only and _before == GA}",
       "copy.deepcopy" in _exec_only and _before == GA)

record("C5-AS-22", "No disguised scale transform (AS-C5-22)",
       "RJ-05 fires on scale_factor",
       f"{rejected_codes(r_scale, 'print_scale')}",
       "RJ-05" in rejected_codes(r_scale, "print_scale"))

# CONDITION-01: the evidence must never expose an artifact_id KEY, and must
# carry its provisional status. The disclaimer text is allowed to mention the
# term precisely because it denies it, so the check targets the key set.
_lin_keys = set(_ev["lineage_evidence"].keys())
record("C5-AS-23", "Lineage evidence is not an artifact identity (CONDITION-01)",
       "PROVISIONAL, usable False, no artifact_id key",
       f"status={_ev['lineage_evidence']['status']}, "
       f"usable={_ev['lineage_evidence']['usable_as_evidence']}, "
       f"id_key={'artifact_id' in _lin_keys}",
       _ev["lineage_evidence"]["status"] == "PROVISIONAL"
       and _ev["lineage_evidence"]["usable_as_evidence"] is False
       and "artifact_id" not in _lin_keys)


# ==========================================================================
# 10. NO-WRITE  (behavioural + write-path audit — CONDITION-03)
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_tpl = os.path.join(ROOT, "project_master.template.json")
_sch = os.path.join(ROOT, "project_master.schema.json")
_c3a = os.path.join(ROOT, "scripts", "c3_geometry_assembly.py")
_c3b = os.path.join(ROOT, "scripts", "c3_svg_emitter.py")
_before_h = (_sha(_tpl), _sha(_sch), _sha(_c3a), _sha(_c3b))
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))
_master_snapshot = copy.deepcopy(master())

_mm = master()
C5.emit_class_b(ga_of(_mm), GOOD_PARAMS, identity=IDENT)
C5.presentation_evidence(C5.emit_class_b(GA, GOOD_PARAMS))
C5.admit_parameters(GOOD_PARAMS)

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("C5-NW-01", "BEHAVIOURAL: master dict is not mutated in memory",
       "identical", f"{_master_snapshot == _mm}", _master_snapshot == _mm)

record("C5-NW-02", "BEHAVIOURAL: template, schema and C3 sources unchanged",
       "sha256 stable",
       f"{_before_h == (_sha(_tpl), _sha(_sch), _sha(_c3a), _sha(_c3b))}",
       _before_h == (_sha(_tpl), _sha(_sch), _sha(_c3a), _sha(_c3b)))

record("C5-NW-03", "BEHAVIOURAL: no new file appeared during emission",
       "no new files", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "pathlib", "tempfile", "pickle",
                "os.remove", "mkdir"]
_found = [p for p in _write_paths if p in _exec_only]
record("C5-NW-04", "WRITE-PATH AUDIT: no write mechanism of any kind",
       "none of 12 paths", f"{_found}", not _found)

record("C5-NW-05", "C5 returns a representation and persists nothing itself",
       "svg returned as text",
       f"{isinstance(r['svg'], str)}", isinstance(r["svg"], str))

record("C5-NW-06", "No write path targets outputs[] or the master",
       "no assignment to either",
       f"{'[\"outputs\"] =' in _exec_only or 'project_master' in _exec_only}",
       '["outputs"] =' not in _exec_only
       and "project_master" not in _exec_only)


# --------------------------------------------------------------------------
print("=" * 98)
print("PHASE 00.5-C5 — PRESENTATION LAYER (CLASS B · SVG · TIER 0 + TIER 1)")
print("=" * 98)
passed = sum(1 for x in RESULTS if x[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    print(f"{'OK  ' if verdict == 'PASS' else 'FAIL'} {tid:11} "
          f"{scenario[:58]:58} {actual[:24]}")
print("-" * 98)
print(f"TOTAL: {passed}/{total} passed")
# Mutation accounting is reported separately and honestly: C5-M-06 is a
# DEFENSIVE-GUARD / NON-ACTIVE MUTATION and is NOT counted as killed.
print("MUTATIONS: 5 killed (M-01..M-05) · 1 CONTROL (M-07) · "
      "1 NON-ACTIVE defensive guard (M-06, not counted as killed)")
print("=" * 98)
sys.exit(0 if passed == total else 1)
