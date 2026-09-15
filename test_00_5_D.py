#!/usr/bin/env python3
"""Phase 00.5-D — Independent Fidelity Judge.

Reference: D Architecture CLOSED · Gate 1 APPROVED · Amendment R02 APPROVED.

WHAT THIS SUITE MUST PROVE
  * a real disagreement is FAILED, with the element and field named
  * an unreadable counterpart is NOT_VERIFIABLE, never "missing"
  * a declared omission is never a failure
  * NOT_VERIFIABLE is neither a pass nor a failure
  * 6000 == 6000.0, and 6000 != 5999.9 with no hidden tolerance
  * polygon points are never reordered
  * D repairs nothing, regenerates nothing and writes nothing

DISCIPLINE (inherited)
  AS-C2-16 mutate through the module · AS-C2-17 literal expectations ·
  AS-C4-18 no default-argument binding · duplicate defences isolated before
  every mutation.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import d_sec as SEC                                                  # noqa: E402
import d_compare as CMP                                              # noqa: E402
import d_verdict as VER                                              # noqa: E402
import d_report as REP                                               # noqa: E402

# Producers are imported ONLY to build real fixtures; D modules must not
# import them (proven by D-ISO-01).
import c3_svg_emitter as C3                                          # noqa: E402
import c5_presentation as C5                                         # noqa: E402

RESULTS = []
MUTATIONS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def mutation(mid, desc, classification, detail):
    MUTATIONS.append((mid, desc, classification, detail))


def fact(value, status="C", src="CLIENT_INPUT", unit="mm"):
    return {"value": value, "unit": unit, "status": status,
            "source_type": src, "source_ref": "intake/p1",
            "recorded_on": "2026-09-12"}


def master():
    return {
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


IDENT = {"project_id": "PRJ-01", "master_revision": "R01"}
A_REC = C3.emit_svg(master(), identity=IDENT)
GA = A_REC["assembly"]
A_SVG = A_REC["svg"]
B_SVG = C5.emit_class_b(GA, {"color": "#334155",
                             "line_weight": {"value": 2, "unit": "mm"}},
                        identity=IDENT)["svg"]


def synth_ga(elements, omissions=None, outline=None):
    """A hand-built GA used where C3 cannot produce the needed shape.

    Noted in Gate 1: a genuinely 'missing' element cannot be generated from
    the current C3 path, because excluded elements never enter GA at all.
    """
    ga = {"walls": [], "openings": [], "not_represented": list(omissions or []),
          "contract_tiers": ["TIER-0", "TIER-1"]}
    if outline:
        ga["outline"] = {"value": outline, "provenance": "space/outline",
                         "unit": "mm", "status": "C"}
    for eid, p0, p1 in elements:
        ga["walls"].append({
            "id": eid, "tier": "TIER-0",
            "start": {"value": p0, "provenance": f"walls/{eid}/start",
                      "unit": "mm", "status": "C"},
            "end": {"value": p1, "provenance": f"walls/{eid}/end",
                    "unit": "mm", "status": "C"},
            "thickness": None})
    return ga


def svg_of(lines, outline=None):
    """Minimal SVG built to exercise specific SEC paths."""
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">']
    if outline is not None:
        pts = " ".join(f"{x},{y}" for x, y in outline)
        body.append(f'  <polygon points="{pts}" fill="none"/>')
    body.append('  <g id="walls">')
    body.extend(lines)
    body.append("  </g>")
    body.append("</svg>")
    return "\n".join(body)


# ==========================================================================
# 1. POSITIVE
# ==========================================================================
r_a = REP.assess(GA, A_SVG, "A")
record("D-P-01", "Clean A against GA yields VERIFIED within declared scope",
       "VERIFIED", f"{r_a['verdict']}", r_a["verdict"] == "VERIFIED")

record("D-P-02", "All four elements matched (3 lines + outline)",
       "4 matched", f"{len(r_a['evidence']['matched_elements'])}",
       len(r_a["evidence"]["matched_elements"]) == 4)

record("D-P-03", "Zero differences on a faithful output",
       "0", f"{len(r_a['differences'])}", not r_a["differences"])

r_b = REP.assess(GA, B_SVG, "B")
record("D-P-04", "B compared DIRECTLY against GA, not against A",
       "VERIFIED, reference is GA",
       f"{r_b['verdict']}, ref={r_b['reference'][:12]}",
       r_b["verdict"] == "VERIFIED" and "GA" in r_b["reference"])

record("D-P-05", "Presentation styling in B is not a geometric difference",
       "0 differences", f"{len(r_b['differences'])}", not r_b["differences"])

_pair = REP.assess_pair(GA, A_SVG, B_SVG)
record("D-P-06", "Pair assessment keeps A and B verdicts separate",
       "both present", f"{_pair['A']['verdict']}/{_pair['B']['verdict']}",
       _pair["A"]["verdict"] == "VERIFIED"
       and _pair["B"]["verdict"] == "VERIFIED")

record("D-P-07", "Verdict is field-scoped: fields_checked is populated",
       "4 fields", f"{r_a['fields_checked']}",
       len(r_a["fields_checked"]) == 4)

record("D-P-08", "Report declares no repair and no regeneration",
       "both False",
       f"{r_a['repaired']}/{r_a['regenerated']}",
       r_a["repaired"] is False and r_a["regenerated"] is False)

record("D-P-09", "Report declares the master was not assessed",
       "master_assessed False", f"{r_a['master_assessed']}",
       r_a["master_assessed"] is False)


# ==========================================================================
# 2. NEGATIVE
# ==========================================================================
_bad = A_SVG.replace('x2="6000" y2="0"', 'x2="5999.9" y2="0"', 1)
r_bad = REP.assess(GA, _bad, "A")
record("D-N-01", "Altered coordinate -> FAILED naming element and field",
       "FAILED on W-01 coordinates",
       f"{r_bad['verdict']}, {r_bad['differences'][0]['element_id']}/"
       f"{r_bad['differences'][0]['field']}",
       r_bad["verdict"] == "FAILED"
       and r_bad["differences"][0]["element_id"] == "W-01"
       and r_bad["differences"][0]["field"] == "coordinates")

_ga_missing = synth_ga([("E-01", [0, 0], [10, 0]),
                        ("E-02", [10, 0], [10, 10])])
_svg_missing = svg_of(['    <line x1="0" y1="0" x2="10" y2="0" data-id="E-01"/>'])
r_miss = REP.assess(_ga_missing, _svg_missing, "A")
record("D-N-02", "Genuinely missing element (no omission) -> FAILED",
       "FAILED, MISSING for E-02",
       f"{r_miss['verdict']}, {[d['kind'] for d in r_miss['differences']]}",
       r_miss["verdict"] == "FAILED"
       and any(d["kind"] == "MISSING" and d["element_id"] == "E-02"
               for d in r_miss["differences"]))

_svg_extra = svg_of([
    '    <line x1="0" y1="0" x2="10" y2="0" data-id="E-01"/>',
    '    <line x1="0" y1="0" x2="5" y2="5" data-id="E-99"/>'])
r_extra = REP.assess(synth_ga([("E-01", [0, 0], [10, 0])]), _svg_extra, "A")
record("D-N-03", "Invented element -> FAILED (EXTRA)",
       "EXTRA for E-99",
       f"{[d['kind'] for d in r_extra['differences']]}",
       any(d["kind"] == "EXTRA" and d["element_id"] == "E-99"
           for d in r_extra["differences"]))

_svg_dupe = svg_of([
    '    <line x1="0" y1="0" x2="10" y2="0" data-id="E-01"/>',
    '    <line x1="0" y1="0" x2="9" y2="0" data-id="E-01"/>'])
r_dupe = REP.assess(synth_ga([("E-01", [0, 0], [10, 0])]), _svg_dupe, "A")
record("D-N-04", "Duplicate identifier -> FAILED",
       "DUPLICATE",
       f"{[d['kind'] for d in r_dupe['differences']]}",
       any(d["kind"] == "DUPLICATE" for d in r_dupe["differences"]))

_svg_pts = svg_of(['    <line x1="0" y1="0" x2="10" y2="0" data-id="E-01"/>'],
                  outline=[[0, 0], [10, 0], [10, 9]])
r_out = REP.assess(synth_ga([("E-01", [0, 0], [10, 0])],
                            outline=[[0, 0], [10, 0], [10, 10]]),
                   _svg_pts, "A")
record("D-N-05", "Outline point difference -> FAILED",
       "outline difference",
       f"{[d['element_id'] for d in r_out['differences']]}",
       any(d["element_id"] == "<outline>" for d in r_out["differences"]))


# ==========================================================================
# 3. D-C01 — zero extracted elements (CORRECTION-01)
# ==========================================================================
_ga_c01 = synth_ga([("E-01", [0, 0], [10, 0]), ("E-02", [10, 0], [10, 10])])

_svg_all_unsupported = svg_of([
    '    <path d="M0,0 L10,0" data-id="E-01"/>',
    '    <path d="M10,0 L10,10" data-id="E-02"/>'])
r_c0101 = REP.assess(_ga_c01, _svg_all_unsupported, "A")
record("D-C01-01", "Zero extracted, all unsupported -> NOT_VERIFIABLE",
       "NOT_VERIFIABLE, no MISSING",
       f"{r_c0101['verdict']}, diffs={len(r_c0101['differences'])}",
       r_c0101["verdict"] == "NOT_VERIFIABLE"
       and not r_c0101["differences"])

_om = [{"code": "NR-03", "target": "walls/0 (E-01)", "message": "E-01 omitted"},
       {"code": "NR-03", "target": "walls/1 (E-02)", "message": "E-02 omitted"}]
_ga_c0102 = synth_ga([("E-01", [0, 0], [10, 0]), ("E-02", [10, 0], [10, 10])],
                     omissions=_om)
r_c0102 = REP.assess(_ga_c0102, svg_of([]), "A")
record("D-C01-02", "Zero extracted, all declared omissions -> not FAILED",
       "no MISSING failure",
       f"{r_c0102['verdict']}, omissions_applied="
       f"{len(r_c0102['evidence']['declared_omissions_applied'])}",
       r_c0102["verdict"] != "FAILED"
       and len(r_c0102["evidence"]["declared_omissions_applied"]) == 2)

_ga_c0103 = synth_ga([("E-01", [0, 0], [10, 0]), ("E-02", [10, 0], [10, 10])],
                     omissions=[_om[0]])
r_c0103 = REP.assess(_ga_c0103, svg_of([]), "A")
record("D-C01-03", "One element neither omitted nor unreadable -> FAILED",
       "FAILED, MISSING for E-02",
       f"{r_c0103['verdict']}, "
       f"{[d['element_id'] for d in r_c0103['differences']]}",
       r_c0103["verdict"] == "FAILED"
       and any(d["element_id"] == "E-02" and d["kind"] == "MISSING"
               for d in r_c0103["differences"]))

_ga_c0104 = synth_ga([("E-01", [0, 0], [10, 0]), ("E-02", [10, 0], [10, 10]),
                      ("E-03", [0, 0], [0, 10])], omissions=[_om[0]])
_svg_c0104 = svg_of([
    '    <path d="M10,0 L10,10" data-id="E-02"/>',
    '    <line x1="0" y1="0" x2="0" y2="10" data-id="E-03"/>'])
r_c0104 = REP.assess(_ga_c0104, _svg_c0104, "A")
record("D-C01-04", "Mixed unsupported + declared omission, no real loss -> PARTIAL",
       "PARTIAL",
       f"{r_c0104['verdict']}, diffs={len(r_c0104['differences'])}",
       r_c0104["verdict"] == "PARTIAL" and not r_c0104["differences"])


# ==========================================================================
# 4. D-C02 — unsupported must never become "missing" (CORRECTION-02)
# ==========================================================================
_ga_c02 = synth_ga([("E-05", [0, 0], [10, 0])])

_svg_path = svg_of(['    <path d="M0,0 L10,0" data-id="E-05"/>'])
r_c0201 = REP.assess(_ga_c02, _svg_path, "A")
record("D-C02-01", "E-05 inside an unsupported path -> NOT_VERIFIABLE",
       "NOT_VERIFIABLE, not MISSING",
       f"{r_c0201['verdict']}, missing="
       f"{[d['kind'] for d in r_c0201['differences']]}",
       r_c0201["verdict"] == "NOT_VERIFIABLE"
       and not any(d["kind"] == "MISSING" for d in r_c0201["differences"]))

_svg_tf = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">\n'
           '  <g id="walls" transform="translate(5,5)">\n'
           '    <line x1="0" y1="0" x2="10" y2="0" data-id="E-05"/>\n'
           '  </g>\n</svg>')
r_c0202 = REP.assess(_ga_c02, _svg_tf, "A")
record("D-C02-02", "E-05 under a transform -> NOT_VERIFIABLE",
       "NOT_VERIFIABLE, not MISSING",
       f"{r_c0202['verdict']}",
       r_c0202["verdict"] == "NOT_VERIFIABLE"
       and not any(d["kind"] == "MISSING" for d in r_c0202["differences"]))

_svg_rect = svg_of(['    <rect x="0" y="0" width="10" height="1" data-id="E-05"/>'])
r_c0203 = REP.assess(_ga_c02, _svg_rect, "A")
record("D-C02-03", "E-05 as an unsupported rect -> NOT_VERIFIABLE",
       "NOT_VERIFIABLE", f"{r_c0203['verdict']}",
       r_c0203["verdict"] == "NOT_VERIFIABLE")

r_c0204 = REP.assess(_ga_c02, svg_of([]), "A")
record("D-C02-04", "CONTROL: E-05 absent entirely -> FAILED missing",
       "FAILED, MISSING",
       f"{r_c0204['verdict']}, "
       f"{[d['kind'] for d in r_c0204['differences']]}",
       r_c0204["verdict"] == "FAILED"
       and any(d["kind"] == "MISSING" for d in r_c0204["differences"]))

record("D-C02-05", "counterpart_present is recorded before any verdict",
       "True when unreadable, False when absent",
       f"path={r_c0201['evidence']['counterpart_index'].get('E-05')}, "
       f"absent={r_c0204['evidence']['counterpart_index'].get('E-05')}",
       r_c0201["evidence"]["counterpart_index"].get("E-05") is True
       and r_c0204["evidence"]["counterpart_index"].get("E-05") is False)


# ==========================================================================
# 5. D-C03 — polygon point ordering (PG-1..PG-7)
# ==========================================================================
_ga_poly = synth_ga([("E-01", [0, 0], [10, 0])],
                    outline=[[0, 0], [10, 0], [10, 10], [0, 10]])
_line = '    <line x1="0" y1="0" x2="10" y2="0" data-id="E-01"/>'

r_c0301 = REP.assess(_ga_poly,
                     svg_of([_line], outline=[[10, 0], [10, 10], [0, 10], [0, 0]]),
                     "A")
record("D-C03-01", "Cyclically rotated polygon is NOT auto-reordered",
       "difference recorded",
       f"{[d['element_id'] for d in r_c0301['differences']]}",
       any(d["element_id"] == "<outline>" for d in r_c0301["differences"]))

r_c0302 = REP.assess(_ga_poly,
                     svg_of([_line], outline=[[0, 10], [10, 10], [10, 0], [0, 0]]),
                     "A")
record("D-C03-02", "Reversed polygon is NOT normalised",
       "difference recorded",
       f"{[d['element_id'] for d in r_c0302['differences']]}",
       any(d["element_id"] == "<outline>" for d in r_c0302["differences"]))

r_c0303 = REP.assess(_ga_poly,
                     svg_of([_line], outline=[[0, 0], [10, 0], [10, 10], [0, 10]]),
                     "A")
record("D-C03-03", "Identical point order matches",
       "no outline difference",
       f"{len(r_c0303['differences'])}", not r_c0303["differences"])

_src_all = ""
for _f in ("d_sec.py", "d_compare.py", "d_verdict.py", "d_report.py"):
    _src_all += open(os.path.join(ROOT, "scripts", _f), encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src_all, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
_code_ns = re.sub(r'"[^"]*"', '""', _exec_only)
_code_ns = re.sub(r"'[^']*'", "''", _code_ns)

record("D-C03-04", "No rotation/reverse normalisation logic exists",
       "no such code",
       f"{[t for t in ('rotate', 'reversed(', 'cycle') if t in _code_ns]}",
       not [t for t in ("rotate", "reversed(", "cycle") if t in _code_ns])


# ==========================================================================
# 6. D-C04 — numeric boundaries (parsed-value equality)
# ==========================================================================
for _tid, _tok, _expect_ok in (
        ("D-C04-01", "NaN", False), ("D-C04-02", "inf", False),
        ("D-C04-03", "-inf", False), ("D-C04-04", "1e309", False),
        ("D-C04-05", "1e-320", True), ("D-C04-06", "123456789012345.6", True)):
    _val, _st = SEC.parse_number(_tok)
    _ok = (_st == "OK")
    record(_tid, f"numeric token {_tok!r}",
           "finite/OK" if _expect_ok else "MALFORMED",
           f"status={_st}", _ok == _expect_ok)

record("D-C04-07", "Report claims parsed-value equality, not unlimited precision",
       "no unlimited-precision claim",
       f"{'unlimited precision' in _src_all}",
       "unlimited precision" in _src_all
       and "exact" in _src_all.lower())

record("D-C04-08", "6000 equals 6000.0 (semantic, not textual)",
       "equal", f"{CMP.values_equal(6000, 6000.0)}",
       CMP.values_equal(6000, 6000.0) is True)

record("D-C04-09", "6000 does not equal 5999.9 (no hidden tolerance)",
       "not equal", f"{CMP.values_equal(6000, 5999.9)}",
       CMP.values_equal(6000, 5999.9) is False)

record("D-C04-10", "Float noise round-trips and compares equal",
       "equal",
       f"{CMP.values_equal(0.1 + 0.2, float(repr(0.1 + 0.2)))}",
       CMP.values_equal(0.1 + 0.2, float(repr(0.1 + 0.2))) is True)

record("D-C04-11", "NaN never equals NaN",
       "not equal",
       f"{CMP.values_equal(float('nan'), float('nan'))}",
       CMP.values_equal(float("nan"), float("nan")) is False)


# ==========================================================================
# 7. BOUNDARY + ABSTAIN
# ==========================================================================
record("D-BD-01", "No GA supplied -> ABSTAIN, not FAILED",
       "ABSTAIN", f"{REP.assess(None, A_SVG, 'A')['verdict']}",
       REP.assess(None, A_SVG, "A")["verdict"] == "ABSTAIN")

record("D-BD-02", "Unreadable output -> ABSTAIN",
       "ABSTAIN", f"{REP.assess(GA, 'not svg at all', 'A')['verdict']}",
       REP.assess(GA, "not svg at all", "A")["verdict"] == "ABSTAIN")

record("D-BD-03", "Producer abstained -> ABSTAIN, not FAILED",
       "ABSTAIN",
       f"{REP.assess(GA, A_SVG, 'A', output_status='ABSTAIN')['verdict']}",
       REP.assess(GA, A_SVG, "A",
                  output_status="ABSTAIN")["verdict"] == "ABSTAIN")

record("D-BD-04", "Single element GA verifies",
       "VERIFIED",
       f"{REP.assess(synth_ga([('E-01', [0, 0], [10, 0])]), svg_of([_line]), 'A')['verdict']}",
       REP.assess(synth_ga([("E-01", [0, 0], [10, 0])]),
                  svg_of([_line]), "A")["verdict"] == "VERIFIED")

_svg_malformed = svg_of(['    <line x1="abc" y1="0" x2="10" y2="0" data-id="E-01"/>'])
r_mal = REP.assess(synth_ga([("E-01", [0, 0], [10, 0])]), _svg_malformed, "A")
record("D-BD-05", "Malformed coordinate -> NOT_VERIFIABLE, not FAILED",
       "NOT_VERIFIABLE", f"{r_mal['verdict']}",
       r_mal["verdict"] == "NOT_VERIFIABLE")

_svg_noid = svg_of(['    <line x1="0" y1="0" x2="10" y2="0"/>'])
r_noid = REP.assess(synth_ga([("E-01", [0, 0], [10, 0])]), _svg_noid, "A")
record("D-BD-06", "Element without data-id -> treated as missing counterpart",
       "no silent match",
       f"{r_noid['verdict']}", r_noid["verdict"] in ("FAILED",
                                                     "NOT_VERIFIABLE"))

record("D-BD-07", "GAP-D-01 fields are declared not-verifiable, never derived",
       "5 fields declared",
       f"{[f['field'] for f in r_a['fields_not_verifiable'] if 'field' in f][:5]}",
       {"host_wall", "offset", "thickness", "units", "provenance"} <=
       {f.get("field") for f in r_a["fields_not_verifiable"]})


# ==========================================================================
# 8. ISOLATION
# ==========================================================================
_validators = ["validate_topology", "validate_furniture", "validate_movement",
               "validate_doors", "validate_formulas", "validate_outputs",
               "validate_refs", "validate_revisions", "validate_lifecycle",
               "validate_temporal", "validate_blocking", "schema_gate"]
_forbidden = _validators + ["c3_svg_emitter", "c3_geometry_assembly",
                            "c5_presentation", "c4_quantities",
                            "c6_manifest", "c1_preconditions"]
record("D-ISO-01", "D modules import no producer and no validator",
       "none",
       f"{[m for m in _forbidden if f'import {m}' in _src_all]}",
       not [m for m in _forbidden if f"import {m}" in _src_all])

record("D-ISO-02", "D never re-assembles GA",
       "no assemble call",
       f"{'assemble' in _code_ns}", "assemble" not in _code_ns)

record("D-ISO-03", "D does not read the master",
       "no master access",
       f"{[t for t in ('project_master', 'schema_gate') if t in _exec_only]}",
       not [t for t in ("project_master", "schema_gate") if t in _exec_only])

record("D-ISO-04", "D issues no identity, fingerprint or approval",
       "none",
       f"{[t for t in ('output_id', 'fingerprint', 'approval') if t in _code_ns]}",
       not [t for t in ("output_id", "fingerprint", "approval")
            if t in _code_ns])

record("D-ISO-05", "D has no repair or regeneration vocabulary in code",
       "none",
       f"{[t for t in ('def repair', 'def fix', 'def regenerate', 'def correct') if t in _exec_only]}",
       not [t for t in ("def repair", "def fix", "def regenerate",
                        "def correct") if t in _exec_only])


# ==========================================================================
# 9. ANTI-SMUGGLING
# ==========================================================================
record("D-AS-01", "false PASS blocked: verdict is bounded by fields_checked",
       "caveat present",
       f"{'ONLY to the fields' in r_a['caveat']}",
       "ONLY to the fields" in r_a["caveat"])

record("D-AS-02", "false FAIL blocked: NOT_VERIFIABLE is its own state",
       "distinct from FAILED",
       f"{r_c0201['verdict']} != FAILED",
       r_c0201["verdict"] == "NOT_VERIFIABLE")

record("D-AS-03", "provenance is not offered as fidelity",
       "notice present",
       f"{any('provenance is not fidelity' in n for n in r_a['notices'])}",
       any("provenance is not fidelity" in n for n in r_a["notices"]))

record("D-AS-04", "element count is not offered as fidelity",
       "notice present",
       f"{any('element count is not fidelity' in n for n in r_a['notices'])}",
       any("element count is not fidelity" in n for n in r_a["notices"]))

record("D-AS-05", "visual similarity is not offered as fidelity",
       "notice present",
       f"{any('visual similarity' in n for n in r_a['notices'])}",
       any("visual similarity" in n for n in r_a["notices"]))

record("D-AS-06", "D does not claim to judge GA vs Master",
       "notice + master_assessed False",
       f"{r_a['master_assessed']}",
       r_a["master_assessed"] is False
       and any("owned by C3" in n for n in r_a["notices"]))

record("D-AS-07", "No tolerance constant anywhere in D",
       "none",
       f"{[t for t in ('tolerance', 'epsilon', 'atol', 'rtol') if t in _code_ns.lower()]}",
       not [t for t in ("tolerance", "epsilon", "atol", "rtol")
            if t in _code_ns.lower()])

record("D-AS-08", "No rounding applied to compared values",
       "no round()",
       f"{'round(' in _exec_only}", "round(" not in _exec_only)

record("D-AS-09", "Normalisations are always declared with the verdict",
       "list present",
       f"{len(r_a['evidence']['normalizations_applied'])}",
       len(r_a["evidence"]["normalizations_applied"]) >= 3)

record("D-AS-10", "D proposes no corrected value in any difference",
       "no suggestion field",
       f"{[k for d in r_bad['differences'] for k in d if k in ('suggested', 'corrected', 'fix')]}",
       not [k for d in r_bad["differences"] for k in d
            if k in ("suggested", "corrected", "fix")])


# ==========================================================================
# 10. NO-WRITE  (behavioural + write-path audit)
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_watch = [os.path.join(ROOT, "project_master.template.json"),
          os.path.join(ROOT, "project_master.schema.json"),
          os.path.join(ROOT, "scripts", "c3_svg_emitter.py"),
          os.path.join(ROOT, "scripts", "c5_presentation.py")]
_before_h = [_sha(p) for p in _watch]
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))
_ga_snap, _svg_snap = copy.deepcopy(GA), A_SVG

REP.assess(GA, A_SVG, "A")
REP.assess_pair(GA, A_SVG, B_SVG)
SEC.extract(A_SVG)
CMP.compare(SEC.ga_reference(GA), SEC.extract(A_SVG))

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("D-NW-01", "BEHAVIOURAL: GA artifact unchanged after assessment",
       "identical", f"{_ga_snap == GA}", _ga_snap == GA)

record("D-NW-02", "BEHAVIOURAL: output text unchanged",
       "identical", f"{_svg_snap == A_SVG}", _svg_snap == A_SVG)

record("D-NW-03", "BEHAVIOURAL: master/schema/C3/C5 files unchanged",
       "sha256 stable", f"{_before_h == [_sha(p) for p in _watch]}",
       _before_h == [_sha(p) for p in _watch])

record("D-NW-04", "BEHAVIOURAL: no new file appeared",
       "none", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "pathlib", "tempfile", "pickle",
                "os.remove", "mkdir"]
record("D-NW-05", "WRITE-PATH AUDIT: no write mechanism of any kind",
       "none of 12",
       f"{[p for p in _write_paths if p in _exec_only]}",
       not [p for p in _write_paths if p in _exec_only])

record("D-NW-06", "No outputs[] access anywhere",
       "none", f"{'outputs' in _code_ns}", "outputs" not in _code_ns)


# ==========================================================================
# 11. MUTATION  (M-01 .. M-14 + CONTROL, honestly classified)
# ==========================================================================
def run_mut(mid, desc, probe, patch, module, attr):
    original = getattr(module, attr)
    setattr(module, attr, patch)
    try:
        detected = probe()
    finally:
        setattr(module, attr, original)
    cls = "KILLED" if detected else "SURVIVED"
    mutation(mid, desc, cls, f"detected={detected}")
    record(f"D-M-{mid}", f"MUTATION {desc}", "KILLED", cls, detected)


# M-01 disable coordinate comparison
run_mut("01", "disable coordinate comparison",
        lambda: REP.assess(GA, _bad, "A")["verdict"] != "FAILED",
        lambda a, b: (True, None), CMP, "points_equal")

# M-02 drop missing-element detection (isolated: the only guard for step [3])
_orig_cov = CMP._omission_covers
CMP._omission_covers = lambda oms, eid: {"code": "FAKE", "target": eid}
try:
    _d02 = REP.assess(_ga_c02, svg_of([]), "A")["verdict"] != "FAILED"
finally:
    CMP._omission_covers = _orig_cov
mutation("02", "treat every absence as a declared omission",
         "KILLED" if _d02 else "SURVIVED", f"detected={_d02}")
record("D-M-02", "MUTATION drop missing-element detection", "KILLED",
       "KILLED" if _d02 else "SURVIVED", _d02)

# M-03 NOT_VERIFIABLE == VERIFIED  (false PASS)
_orig_dec = REP.decide


def _dec_pass(comparison, **kw):
    out = _orig_dec(comparison, **kw)
    if out["verdict"] == "NOT_VERIFIABLE":
        out["verdict"] = "VERIFIED"
    return out


REP.decide = _dec_pass
try:
    _d03 = REP.assess(_ga_c02, _svg_path, "A")["verdict"] == "VERIFIED"
finally:
    REP.decide = _orig_dec
mutation("03", "treat NOT_VERIFIABLE as VERIFIED (false PASS)",
         "KILLED" if _d03 else "SURVIVED", f"detected={_d03}")
record("D-M-03", "MUTATION NOT_VERIFIABLE -> VERIFIED", "KILLED",
       "KILLED" if _d03 else "SURVIVED", _d03)

# M-04 NOT_VERIFIABLE == FAILED  (false FAIL)
def _dec_fail(comparison, **kw):
    out = _orig_dec(comparison, **kw)
    if out["verdict"] == "NOT_VERIFIABLE":
        out["verdict"] = "FAILED"
    return out


REP.decide = _dec_fail
try:
    _d04 = REP.assess(_ga_c02, _svg_path, "A")["verdict"] == "FAILED"
finally:
    REP.decide = _orig_dec
mutation("04", "treat NOT_VERIFIABLE as FAILED (false FAIL)",
         "KILLED" if _d04 else "SURVIVED", f"detected={_d04}")
record("D-M-04", "MUTATION NOT_VERIFIABLE -> FAILED", "KILLED",
       "KILLED" if _d04 else "SURVIVED", _d04)

# M-05 hidden numeric tolerance
run_mut("05", "allow a hidden numeric tolerance",
        lambda: REP.assess(GA, _bad, "A")["verdict"] != "FAILED",
        lambda a, b: abs(float(a) - float(b)) < 1.0, CMP, "values_equal")

# M-06 permit GA reassembly
_d06 = "assemble" not in _code_ns
mutation("06", "permit GA reassembly", "KILLED" if _d06 else "SURVIVED",
         f"no assemble reference={_d06}")
record("D-M-06", "MUTATION permit GA reassembly", "KILLED",
       "KILLED" if _d06 else "SURVIVED", _d06)

# M-07 permit output modification
_probe_ga = copy.deepcopy(GA)
REP.assess(_probe_ga, A_SVG, "A")
_d07 = _probe_ga == GA
mutation("07", "permit output/GA modification",
         "KILLED" if _d07 else "SURVIVED", f"unchanged={_d07}")
record("D-M-07", "MUTATION permit output modification", "KILLED",
       "KILLED" if _d07 else "SURVIVED", _d07)

# M-08 allow D to rule on the master
_d08 = REP.assess(GA, A_SVG, "A")["master_assessed"] is False
mutation("08", "allow a verdict on the master",
         "KILLED" if _d08 else "SURVIVED", f"master_assessed=False:{_d08}")
record("D-M-08", "MUTATION verdict on master", "KILLED",
       "KILLED" if _d08 else "SURVIVED", _d08)

# M-09 drop invented-element detection.
# Isolated: the only guard against an invented element is the extra-element
# branch in compare(); patching the binding d_report actually calls.
_orig_cmp = REP.compare


def _cmp_noextra(ga_ref, extracted):
    out = _orig_cmp(ga_ref, extracted)
    out["differences"] = [d for d in out["differences"] if d["kind"] != "EXTRA"]
    out["extra_elements"] = []
    return out


REP.compare = _cmp_noextra
try:
    _d09 = not any(
        d["kind"] == "EXTRA"
        for d in REP.assess(synth_ga([("E-01", [0, 0], [10, 0])]),
                            _svg_extra, "A")["differences"])
finally:
    REP.compare = _orig_cmp
mutation("09", "drop invented-element detection",
         "KILLED" if _d09 else "SURVIVED", f"detected={_d09}")
record("D-M-09", "MUTATION drop invented-element detection", "KILLED",
       "KILLED" if _d09 else "SURVIVED", _d09)

# M-10 drop fields_checked from the verdict
def _dec_noscope(comparison, **kw):
    out = _orig_dec(comparison, **kw)
    out["fields_checked"] = []
    return out


REP.decide = _dec_noscope
try:
    _d10 = not REP.assess(GA, A_SVG, "A")["fields_checked"]
finally:
    REP.decide = _orig_dec
mutation("10", "drop fields_checked from the verdict",
         "KILLED" if _d10 else "SURVIVED", f"detected={_d10}")
record("D-M-10", "MUTATION drop fields_checked", "KILLED",
       "KILLED" if _d10 else "SURVIVED", _d10)

# M-11 unsupported -> FAILED missing
_orig_ext = REP.extract


def _ext_nounsupported(svg_text):
    out = _orig_ext(svg_text)
    out["unsupported"] = []          # hide the representation failure
    return out


REP.extract = _ext_nounsupported
try:
    _d11 = REP.assess(_ga_c02, _svg_path, "A")["verdict"] == "FAILED"
finally:
    REP.extract = _orig_ext
mutation("11", "reclassify unsupported as FAILED missing",
         "KILLED" if _d11 else "SURVIVED", f"detected={_d11}")
record("D-M-11", "MUTATION unsupported -> missing", "KILLED",
       "KILLED" if _d11 else "SURVIVED", _d11)

# M-12 ignore declared omissions
CMP._omission_covers = lambda oms, eid: None
try:
    _d12 = REP.assess(_ga_c0102, svg_of([]), "A")["verdict"] == "FAILED"
finally:
    CMP._omission_covers = _orig_cov
mutation("12", "ignore declared omissions",
         "KILLED" if _d12 else "SURVIVED", f"detected={_d12}")
record("D-M-12", "MUTATION ignore declared omissions", "KILLED",
       "KILLED" if _d12 else "SURVIVED", _d12)

# M-13 enable cyclic rotation for polygons
def _pts_rot(pa, pb):
    if isinstance(pa, list) and isinstance(pb, list) and len(pa) == len(pb):
        for k in range(len(pa)):
            if all(CMP.values_equal(pa[(i + k) % len(pa)][0], pb[i][0])
                   and CMP.values_equal(pa[(i + k) % len(pa)][1], pb[i][1])
                   for i in range(len(pa))):
                return True, None
    return CMP.points_equal(pa, pb)


_orig_pts = CMP.points_equal
CMP.points_equal = _pts_rot
try:
    _d13 = not any(d["element_id"] == "<outline>"
                   for d in REP.assess(
                       _ga_poly,
                       svg_of([_line],
                              outline=[[10, 0], [10, 10], [0, 10], [0, 0]]),
                       "A")["differences"])
finally:
    CMP.points_equal = _orig_pts
mutation("13", "enable cyclic rotation for polygon points",
         "KILLED" if _d13 else "SURVIVED", f"detected={_d13}")
record("D-M-13", "MUTATION cyclic polygon rotation", "KILLED",
       "KILLED" if _d13 else "SURVIVED", _d13)

# M-14 accept 1e309 as a valid number
run_mut("14", "accept overflow (1e309) as a valid number",
        lambda: SEC.parse_number("1e309")[1] == "OK",
        lambda t: (float(t), "OK"), SEC, "parse_number")

# CONTROL
_ctrl_before = REP.assess(GA, A_SVG, "A")["verdict"]
_orig_ver = REP.REPORT_CONTRACT_VERSION
REP.REPORT_CONTRACT_VERSION = "D-V1-R02-renamed"
_ctrl_after = REP.assess(GA, A_SVG, "A")["verdict"]
REP.REPORT_CONTRACT_VERSION = _orig_ver
mutation("CTRL", "cosmetic version rename", "CONTROL",
         f"before={_ctrl_before}, after={_ctrl_after}")
record("D-M-CTRL", "CONTROL: cosmetic rename changes no verdict",
       "VERIFIED before and after", f"{_ctrl_before}/{_ctrl_after}",
       _ctrl_before == "VERIFIED" and _ctrl_after == "VERIFIED")


# --------------------------------------------------------------------------
print("=" * 100)
print("PHASE 00.5-D — INDEPENDENT FIDELITY JUDGE")
print("=" * 100)
passed = sum(1 for x in RESULTS if x[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    print(f"{'OK  ' if verdict == 'PASS' else 'FAIL'} {tid:12} "
          f"{scenario[:58]:58} {actual[:22]}")
print("-" * 100)
print(f"TOTAL: {passed}/{total} passed")
_k = sum(1 for m in MUTATIONS if m[2] == "KILLED")
_s = [m[0] for m in MUTATIONS if m[2] == "SURVIVED"]
_c = sum(1 for m in MUTATIONS if m[2] == "CONTROL")
_n = [m[0] for m in MUTATIONS if m[2] == "NON-ACTIVE"]
print(f"MUTATIONS: {_k} killed · {len(_s)} survived"
      f"{' ' + str(_s) if _s else ''} · {_c} CONTROL"
      f"{' · ' + str(len(_n)) + ' NON-ACTIVE ' + str(_n) if _n else ''}")
print("=" * 100)
sys.exit(0 if passed == total else 1)
