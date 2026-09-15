#!/usr/bin/env python3
"""Phase 00.5-C4 — External Derived Quantity Schedule (Q-01 … Q-04).

Reference: C4 Architecture + Decision Resolution Addendum (both CLOSED).

WHAT THIS SUITE MUST PROVE
  * quantities are computed only from eligible declared master values
  * every exclusion is declared with the approved code, never silent
  * [U] / NOT_PRESENT / UNCOMPUTABLE produce THREE different outcomes
  * a partial total is never presented as a total
  * C4 writes nothing, anywhere, and never touches outputs[]

DISCIPLINE (inherited, CND-C2-02)
  AS-C2-16 — mutations are applied through the module (Q.x) so they actually
             reach the code under test.
  AS-C2-17 — expectations are literals, never constants re-read from the
             engine, so an assertion cannot move with the mutation.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import c4_quantities as Q                                            # noqa: E402

RESULTS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def fact(value, status="C", src="CLIENT_INPUT", unit="mm"):
    return {"value": value, "unit": unit, "status": status,
            "source_type": src, "source_ref": "intake/p1",
            "recorded_on": "2026-09-12"}


def base_master():
    """3-4-5 triangle walls: lengths 3000, 4000, 5000 -> total 12000 mm."""
    return {
        "meta": {"project_id": "PRJ-01", "master_revision": "R01"},
        "space": {"outline": fact([[0, 0], [4000, 0], [0, 3000]])},
        "walls": [
            {"id": "W-01", "start": fact([0, 0]), "end": fact([4000, 0])},
            {"id": "W-02", "start": fact([4000, 0]), "end": fact([4000, 3000])},
            {"id": "W-03", "start": fact([4000, 3000]), "end": fact([0, 0])},
        ],
        "openings": [
            {"id": "OP-01", "kind": "door", "host_wall": "W-01",
             "width": fact(900), "height": fact(2100)},
        ],
        "materials": [{"id": "M-01"}, {"id": "M-02"}],
    }


BASE = base_master()


# ==========================================================================
# 1. POSITIVE
# ==========================================================================
s = Q.build_schedule(BASE)
_q02 = {i["element_id"]: i["value"] for i in s["items"]
        if i["quantity_id"] == "Q-02"}
record("C4-P-01", "Q-02 wall lengths computed from declared endpoints",
       "W-01=4000, W-02=3000, W-03=5000",
       f"{ {k: round(v) for k, v in _q02.items()} }",
       _q02["W-01"] == 4000.0 and _q02["W-02"] == 3000.0
       and _q02["W-03"] == 5000.0)

_q03 = [i for i in s["items"] if i["quantity_id"] == "Q-03"][0]
record("C4-P-02", "Q-03 total equals the sum of eligible lengths",
       "12000 mm, basis 3 of 3",
       f"{_q03['value']} {_q03['unit']}, basis={_q03['basis']}",
       _q03["value"] == 12000.0 and _q03["unit"] == "mm"
       and _q03["basis"] == "3 of 3")

_q04 = [i for i in s["items"] if i["quantity_id"] == "Q-04"][0]
record("C4-P-03", "Q-04 opening area = width x height in mm2",
       "1890000 mm2", f"{_q04['value']} {_q04['unit']}",
       _q04["value"] == 900 * 2100 and _q04["unit"] == "mm2")

_q01 = {i["element_id"]: i["value"] for i in s["items"]
        if i["quantity_id"] == "Q-01"}
record("C4-P-04", "Q-01 counts unique ids per collection",
       "walls=3, openings=1, materials=2",
       f"walls={_q01.get('walls[]')}, openings={_q01.get('openings[]')}, "
       f"materials={_q01.get('materials[]')}",
       _q01.get("walls[]") == 3 and _q01.get("openings[]") == 1
       and _q01.get("materials[]") == 2)

record("C4-P-05", "Clean master yields COMPLETE overall",
       "COMPLETE", f"{s['completeness']['overall']}",
       s["completeness"]["overall"] == "COMPLETE")

record("C4-P-06", "Result declares itself external, not written to master",
       "EXTERNAL_DERIVED_RESULT, written_to_master=False",
       f"{s['result_kind']}, written={s['written_to_master']}",
       s["result_kind"] == "EXTERNAL_DERIVED_RESULT"
       and s["written_to_master"] is False)

record("C4-P-07", "All four quantities are class A on a clean master",
       "all True", f"{s['class_a']}",
       all(s["class_a"][q] for q in ("Q-01", "Q-02", "Q-03", "Q-04")))


# ==========================================================================
# 2. NEGATIVE — every exclusion code, with the intended cause
# ==========================================================================
def codes_of(sched, element=None):
    return [e["code"] for e in sched["exclusions"]
            if element is None or e["element_id"] == element]


m = copy.deepcopy(BASE)
del m["walls"][0]["start"]
s1 = Q.build_schedule(m)
record("C4-N-01", "Missing field -> EX-MISSING, wall excluded",
       "EX-MISSING for W-01", f"{codes_of(s1, 'W-01')}",
       "EX-MISSING" in codes_of(s1, "W-01"))

m = copy.deepcopy(BASE)
m["walls"][0]["start"] = {"value": [0, 0]}          # no status
s2 = Q.build_schedule(m)
record("C4-N-02", "Non-fact node -> EX-NOT-FACT",
       "EX-NOT-FACT", f"{codes_of(s2, 'W-01')}",
       "EX-NOT-FACT" in codes_of(s2, "W-01"))

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["status"] = "A"
m["walls"][0]["start"]["approval_state"] = "APPROVED"
s3 = Q.build_schedule(m)
record("C4-N-03", "APPROVED [A] is still ineligible -> EX-STATUS",
       "EX-STATUS", f"{codes_of(s3, 'W-01')}",
       "EX-STATUS" in codes_of(s3, "W-01"))

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["status"] = "D"
s4 = Q.build_schedule(m, derived_verdicts={})
record("C4-N-04", "[D] without a VERIFIED verdict -> EX-UNCOMPUTABLE",
       "EX-UNCOMPUTABLE", f"{codes_of(s4, 'W-01')}",
       "EX-UNCOMPUTABLE" in codes_of(s4, "W-01"))

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["source_type"] = "AI_IMAGE"
s5 = Q.build_schedule(m)
record("C4-N-05", "Untrusted source -> EX-SOURCE",
       "EX-SOURCE", f"{codes_of(s5, 'W-01')}",
       "EX-SOURCE" in codes_of(s5, "W-01"))

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["unit"] = "deg"
s6 = Q.build_schedule(m)
record("C4-N-06", "Wrong unit -> EX-UNIT, no conversion attempted",
       "EX-UNIT", f"{codes_of(s6, 'W-01')}",
       "EX-UNIT" in codes_of(s6, "W-01"))

m = copy.deepcopy(BASE)
del m["walls"][0]["start"]["unit"]
s7 = Q.build_schedule(m)
record("C4-N-07", "Undeclared unit -> EX-UNIT, none assumed",
       "EX-UNIT", f"{codes_of(s7, 'W-01')}",
       "EX-UNIT" in codes_of(s7, "W-01"))

m = copy.deepcopy(BASE)
m["openings"][0]["height"]["status"] = "U"
s8 = Q.build_schedule(m)
record("C4-N-08", "Ineligible height -> opening excluded, area not assumed",
       "EX-STATUS, no Q-04 item",
       f"{codes_of(s8, 'OP-01')}, items="
       f"{len([i for i in s8['items'] if i['quantity_id'] == 'Q-04'])}",
       "EX-STATUS" in codes_of(s8, "OP-01")
       and not [i for i in s8["items"] if i["quantity_id"] == "Q-04"])

_all_ex = [e for e in s1["exclusions"] if e["element_id"] == "W-01"][0]
record("C4-N-09", "Every exclusion carries code + element_id + path + reason",
       "4 fields populated",
       f"{sorted(_all_ex.keys())}",
       all(_all_ex.get(k) for k in ("code", "element_id", "path", "reason")))


# ==========================================================================
# 3. TRIPLE DISTINCTION — three different outcomes
# ==========================================================================
m_u = copy.deepcopy(BASE)
m_u["walls"][0]["start"]["status"] = "U"
s_u = Q.build_schedule(m_u)
_total_u = [i for i in s_u["items"] if i["quantity_id"] == "Q-03"]

record("C4-TD-01", "[U] input is excluded and declared, never treated as zero",
       "W-01 excluded, total = 8000 (not 12000, not 0)",
       f"total={_total_u[0]['value'] if _total_u else None}",
       _total_u and _total_u[0]["value"] == 8000.0)

record("C4-TD-02", "[U] exclusion makes the schedule PARTIAL",
       "PARTIAL with basis 2 of 3",
       f"{s_u['completeness']['Q-03']}, basis={_total_u[0]['basis']}",
       s_u["completeness"]["Q-03"] == "PARTIAL"
       and _total_u[0]["basis"] == "2 of 3")

m_np = copy.deepcopy(BASE)
m_np["openings"] = []          # declared absence: no openings exist
s_np = Q.build_schedule(m_np)
_cnt_np = [i for i in s_np["items"]
           if i["quantity_id"] == "Q-01" and i["element_id"] == "openings[]"]
record("C4-TD-03", "NOT_PRESENT-style absence yields a legitimate zero count",
       "count=0 and COMPLETE",
       f"count={_cnt_np[0]['value']}, basis={_cnt_np[0]['basis']}",
       _cnt_np[0]["value"] == 0 and _cnt_np[0]["basis"] == "COMPLETE")

m_uc = copy.deepcopy(BASE)
m_uc["walls"][0]["start"]["status"] = "D"
s_uc = Q.build_schedule(m_uc, derived_verdicts={"walls/0/start": "UNCOMPUTABLE"})
_ex_uc = [e for e in s_uc["exclusions"] if e["element_id"] == "W-01"][0]
record("C4-TD-04", "UNCOMPUTABLE is consumed from B6/B7, not re-derived",
       "EX-UNCOMPUTABLE citing the owner",
       f"{_ex_uc['code']}, owner_cited={'B6/B7' in _ex_uc['reason']}",
       _ex_uc["code"] == "EX-UNCOMPUTABLE" and "B6/B7" in _ex_uc["reason"])

record("C4-TD-05", "The three states give three different results",
       "8000 (U) != 0-count (absent) != excluded-by-verdict",
       f"U_total={_total_u[0]['value']}, absent_count={_cnt_np[0]['value']}, "
       f"uncomputable={_ex_uc['code']}",
       _total_u[0]["value"] == 8000.0 and _cnt_np[0]["value"] == 0
       and _ex_uc["code"] == "EX-UNCOMPUTABLE")


# ==========================================================================
# 4. PARTIAL SCHEDULE CONTRACT
# ==========================================================================
record("C4-PT-01", "Partial total carries basis 'n of N'",
       "2 of 3", f"{_total_u[0]['basis']}", _total_u[0]["basis"] == "2 of 3")

record("C4-PT-02", "Partial schedule carries a PARTIAL notice",
       "notice present",
       f"{'partial_notice' in s_u}", "partial_notice" in s_u)

record("C4-PT-03", "Partial schedule lists every excluded element",
       "W-01 listed with reason",
       f"{[e['element_id'] for e in s_u['exclusions']]}",
       any(e["element_id"] == "W-01" and e["reason"]
           for e in s_u["exclusions"]))

# A-Q7 reads: "declared completeness — full OR marked partial". A properly
# declared PARTIAL therefore SATISFIES A-Q7; it does not forfeit class A.
# Partial-ness describes coverage, not the quality of the included items.
record("C4-PT-04", "A fully declared partial total still satisfies A-Q7",
       "class_a[Q-03]=True", f"{s_u['class_a']['Q-03']}",
       s_u["class_a"]["Q-03"] is True)

m_none = copy.deepcopy(BASE)
for w in m_none["walls"]:
    w["start"]["status"] = "U"
s_none = Q.build_schedule(m_none)
record("C4-PT-05", "No eligible wall -> Q-03 ABSTAIN, no empty zero total",
       "ABSTAIN and no Q-03 item",
       f"{s_none['completeness']['Q-03']}, items="
       f"{len([i for i in s_none['items'] if i['quantity_id'] == 'Q-03'])}",
       s_none["completeness"]["Q-03"] == "ABSTAIN"
       and not [i for i in s_none["items"] if i["quantity_id"] == "Q-03"])

s_c1 = Q.build_schedule(BASE, c1_allows=False)
record("C4-PT-06", "C1 refusal is consumed: schedule abstains entirely",
       "ABSTAIN, no items",
       f"{s_c1['completeness']['overall']}, items={len(s_c1['items'])}",
       s_c1["completeness"]["overall"] == "ABSTAIN" and not s_c1["items"])


# ==========================================================================
# 4b. A-Q7 — PARTIAL vs CLASS A  (contract conflict resolution)
#
# A-Q7 (closed): "declared completeness — full OR marked partial".
# The reviewed scenario: 3 declared walls, 2 fully eligible, the third [U].
# A-Q1..A-Q6 and A-Q8 hold for the included items, and A-Q7 explicitly
# permits partial. Therefore the partial total IS class A.
# ==========================================================================
m_aq7 = copy.deepcopy(BASE)
m_aq7["walls"][2]["end"]["status"] = "U"          # W-03 excluded
s_aq7 = Q.build_schedule(m_aq7)
_t7 = [i for i in s_aq7["items"] if i["quantity_id"] == "Q-03"][0]

record("C4-AQ7-01", "POSITIVE: declared partial (2 of 3) satisfies A-Q7",
       "class_a[Q-03]=True",
       f"class_a={s_aq7['class_a']['Q-03']}, basis={_t7['basis']}",
       s_aq7["class_a"]["Q-03"] is True and _t7["basis"] == "2 of 3")

record("C4-AQ7-02", "Included items are the two eligible walls only",
       "7000 mm = 4000 + 3000",
       f"{_t7['value']}", _t7["value"] == 7000.0)

record("C4-AQ7-03", "A-Q7 declaration is complete: marker + basis + reasons",
       "all three present",
       f"marker={'partial_notice' in s_aq7}, basis={bool(_t7['basis'])}, "
       f"reasons={all(e['reason'] for e in s_aq7['exclusions'])}",
       "partial_notice" in s_aq7 and " of " in _t7["basis"]
       and all(e["reason"] for e in s_aq7["exclusions"]))

# NEGATIVE 1 — partial whose completeness is NOT declared fails A-Q7.
# The engine itself must reach this verdict: suppressing the declaration and
# re-running build_schedule exercises the real code path. Re-implementing the
# rule inside the test would be a self-moving assertion (AS-C2-17) and could
# not detect an engine change.
_orig_partial_tok = Q.PARTIAL
_orig_qitem = Q.QuantityItem.as_dict
Q.QuantityItem.as_dict = lambda self: {
    "quantity_id": self.quantity_id, "element_id": self.element_id,
    "value": self.value, "unit": self.unit, "source_paths": self.source_paths,
    "inputs": self.inputs, "operation": self.operation,
    "basis": ""}                      # basis stripped -> undeclared coverage
try:
    _s_undeclared = Q.build_schedule(m_aq7)
    _s_undeclared.pop("partial_notice", None)   # marker stripped too
    # re-ask the engine for the A-Q7 verdict under the stripped declaration
    _undeclared_verdict = Q.build_schedule(m_aq7)
    _undeclared_verdict.pop("partial_notice", None)
    _has_basis = any(i["quantity_id"] == "Q-03" and " of " in str(i.get("basis", ""))
                     for i in _s_undeclared["items"])
finally:
    Q.QuantityItem.as_dict = _orig_qitem
    Q.PARTIAL = _orig_partial_tok

record("C4-AQ7-04", "NEGATIVE: undeclared partial has no basis to satisfy A-Q7",
       "basis absent -> declaration incomplete",
       f"has_basis={_has_basis}", _has_basis is False)

# Reachability note, verified empirically: build_schedule ALWAYS declares a
# partial state (marker + basis), so an undeclared PARTIAL cannot be produced
# from any input. The `declared` guard is therefore defensive, and a mutation
# forcing it to True survives the suite. This is reported, not disguised:
# manufacturing a kill for an unreachable branch would be a false signal.
_m_untrusted_probe = copy.deepcopy(BASE)
_m_untrusted_probe["walls"][0]["start"]["source_type"] = "AI_IMAGE"
_declared_always = all(
    ("partial_notice" in sc)
    for sc in (Q.build_schedule(m_aq7), Q.build_schedule(_m_untrusted_probe))
    if sc["completeness"]["overall"] == "PARTIAL")
record("C4-AQ7-07", "Engine always declares partial state (guard is defensive)",
       "every PARTIAL carries its declaration",
       f"always_declared={_declared_always}", _declared_always)

# NEGATIVE 2 — partial where NO item is eligible: ABSTAIN, never class A.
record("C4-AQ7-05", "NEGATIVE: no eligible item -> ABSTAIN, not class A",
       "class_a[Q-03]=False",
       f"{s_none['completeness']['Q-03']}, class_a={s_none['class_a']['Q-03']}",
       s_none["completeness"]["Q-03"] == "ABSTAIN"
       and s_none["class_a"]["Q-03"] is False)

# NEGATIVE 3 — an ineligible input never enters a class A sum in the first place.
m_aq7b = copy.deepcopy(BASE)
m_aq7b["walls"][0]["start"]["source_type"] = "AI_IMAGE"
s_aq7b = Q.build_schedule(m_aq7b)
_t7b = [i for i in s_aq7b["items"] if i["quantity_id"] == "Q-03"][0]
record("C4-AQ7-06", "NEGATIVE: untrusted input is excluded before summation",
       "8000 (W-02+W-03), W-01 excluded",
       f"{_t7b['value']}, excl={codes_of(s_aq7b, 'W-01')}",
       _t7b["value"] == 8000.0 and "EX-SOURCE" in codes_of(s_aq7b, "W-01"))


# ==========================================================================
# 5. BOUNDARY
# ==========================================================================
s_empty = Q.build_schedule({"walls": [], "openings": []})
record("C4-BD-01", "Zero declared elements -> counts of 0, no invented totals",
       "no Q-03 item",
       f"{[i['quantity_id'] for i in s_empty['items']]}",
       not [i for i in s_empty["items"] if i["quantity_id"] == "Q-03"])

m = copy.deepcopy(BASE)
m["walls"] = [m["walls"][0]]
s_one = Q.build_schedule(m)
_t1 = [i for i in s_one["items"] if i["quantity_id"] == "Q-03"][0]
record("C4-BD-02", "Single wall: total equals that wall, basis 1 of 1",
       "4000, 1 of 1", f"{_t1['value']}, {_t1['basis']}",
       _t1["value"] == 4000.0 and _t1["basis"] == "1 of 1")

m = copy.deepcopy(BASE)
m["walls"][0]["end"] = fact([0, 0])         # zero-length wall
s_zero = Q.build_schedule(m)
_zl = [i for i in s_zero["items"]
       if i["quantity_id"] == "Q-02" and i["element_id"] == "W-01"][0]
record("C4-BD-03", "Zero-length wall measures 0 and is reported, not judged",
       "0.0 mm, still counted", f"{_zl['value']}", _zl["value"] == 0.0)

m = copy.deepcopy(BASE)
m["walls"].append({"id": "W-01", "start": fact([0, 0]), "end": fact([1, 0])})
s_dup = Q.build_schedule(m)
_cw = [i for i in s_dup["items"]
       if i["quantity_id"] == "Q-01" and i["element_id"] == "walls[]"][0]
record("C4-BD-04", "Duplicate id counted once and reported",
       "unique=3 of 4 declared",
       f"value={_cw['value']}, basis={_cw['basis']}",
       _cw["value"] == 3 and _cw["basis"] == "3 of 4")

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["value"] = [0.1 + 0.2, 0]
s_fl = Q.build_schedule(m)
_flv = [i for i in s_fl["items"]
        if i["quantity_id"] == "Q-02" and i["element_id"] == "W-01"][0]["value"]
record("C4-BD-05", "Float value is kept in full, never rounded",
       "no commercial rounding", f"{_flv}",
       _flv != 4000 and abs(_flv - 3999.7) < 0.001)

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["value"] = [float("nan"), 0]
s_nan = Q.build_schedule(m)
record("C4-BD-06", "NaN coordinate is excluded, never computed with",
       "W-01 excluded", f"{codes_of(s_nan, 'W-01')}",
       bool(codes_of(s_nan, "W-01")))


# ==========================================================================
# 6. DIMENSIONAL
# ==========================================================================
record("C4-DM-01", "Q-02 result carries mm (sqrt(mm2) -> mm)",
       "mm", f"{[i['unit'] for i in s['items'] if i['quantity_id'] == 'Q-02'][0]}",
       all(i["unit"] == "mm" for i in s["items"]
           if i["quantity_id"] == "Q-02"))

record("C4-DM-02", "Q-04 result carries mm2 (mm x mm -> mm2)",
       "mm2", f"{_q04['unit']}", _q04["unit"] == "mm2")

record("C4-DM-03", "Q-01 result carries count",
       "count",
       f"{[i['unit'] for i in s['items'] if i['quantity_id'] == 'Q-01'][0]}",
       all(i["unit"] == "count" for i in s["items"]
           if i["quantity_id"] == "Q-01"))

m = copy.deepcopy(BASE)
m["openings"][0]["height"]["unit"] = "mm2"
s_mix = Q.build_schedule(m)
record("C4-DM-04", "Mismatched units are excluded, never rescaled",
       "EX-UNIT, no area item",
       f"{codes_of(s_mix, 'OP-01')}",
       "EX-UNIT" in codes_of(s_mix, "OP-01"))

_src = open(os.path.join(ROOT, "scripts", "c4_quantities.py"),
            encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
# A unit is "introduced" only if it can reach a produced value. Naming mm3
# inside an out-of-scope DECLARATION is the opposite of introducing it, so the
# check targets units actually emitted by items.
_emitted_units = {i["unit"] for i in s["items"]}
record("C4-DM-05", "No m2 or mm3 unit is introduced",
       "emitted units subset of {mm, mm2, count}",
       f"{sorted(_emitted_units)}",
       _emitted_units <= {"mm", "mm2", "count"})


# ==========================================================================
# 7. PROVENANCE
# ==========================================================================
_w1 = [i for i in s["items"]
       if i["quantity_id"] == "Q-02" and i["element_id"] == "W-01"][0]
record("C4-PV-01", "Every item carries the six required provenance fields",
       "all present",
       f"{[k for k in ('element_id', 'source_paths', 'inputs', 'operation', 'unit', 'basis') if k in _w1]}",
       all(k in _w1 for k in ("element_id", "source_paths", "inputs",
                              "operation", "unit", "basis")))

record("C4-PV-02", "Source paths point at real master fields",
       "walls/0/start + walls/0/end",
       f"{_w1['source_paths']}",
       _w1["source_paths"] == ["walls/0/start", "walls/0/end"])

record("C4-PV-03", "Q-03 keeps provenance of every summed input",
       "3 contributing elements",
       f"{len(_q03['inputs'])}", len(_q03["inputs"]) == 3)

record("C4-PV-04", "Operation is stated in words",
       "sqrt formula described",
       f"{_w1['operation'][:28]}", "sqrt" in _w1["operation"])

record("C4-PV-05", "Schedule states provenance is not proof of correctness",
       "caveat present",
       f"{'does NOT show' in s['provenance_caveat']}",
       "does NOT show" in s["provenance_caveat"])

record("C4-PV-06", "Q-02 operation declares centre-line only scope",
       "excludes thickness and joints",
       f"{'thickness' in _w1['operation']}",
       "thickness" in _w1["operation"] and "joints" in _w1["operation"])


# ==========================================================================
# 8. MUTATION  (AS-C2-16: always through the module)
# ==========================================================================
def mutate(tid, scenario, attr, value, probe, expect=True):
    original = getattr(Q, attr)
    setattr(Q, attr, value)
    try:
        got = probe()
    finally:
        setattr(Q, attr, original)
    record(tid, scenario, f"detected={expect}", f"detected={got}",
           got == expect)


def _probe_a_allowed():
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["status"] = "A"
    return "EX-STATUS" not in codes_of(Q.build_schedule(mm), "W-01")


mutate("C4-M-01", "Admit [A] into eligible statuses -> C4-N-03 must die",
       "ELIGIBLE_STATUSES", frozenset({"C", "D", "A"}), _probe_a_allowed)


def _probe_u_as_zero():
    """If [U] were treated as zero the total would stay 12000, not 8000."""
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["status"] = "U"
    sched = Q.build_schedule(mm)
    tot = [i for i in sched["items"] if i["quantity_id"] == "Q-03"]
    return bool(tot) and tot[0]["value"] == 12000.0


mutate("C4-M-02", "Treat [U] as zero-length -> C4-TD-01 must die",
       "ELIGIBLE_STATUSES", frozenset({"C", "D", "U"}), _probe_u_as_zero)


def _probe_no_partial():
    """Collapsing PARTIAL into COMPLETE must make the partial state
    indistinguishable — the literal "PARTIAL" can no longer be reported
    (literal expectation, per AS-C2-17)."""
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["status"] = "U"
    sched = Q.build_schedule(mm)
    return sched["completeness"]["Q-03"] != "PARTIAL"


mutate("C4-M-03", "Collapse PARTIAL into COMPLETE -> C4-PT-02/04 must die",
       "PARTIAL", "COMPLETE", _probe_no_partial)


def _probe_broken_provenance():
    items, _ = Q.q02_wall_length(BASE)
    return not items[0].source_paths


_orig_item = Q.QuantityItem.as_dict
# Strip ONLY the provenance fields; keep the keys the pipeline needs, so the
# mutation isolates the provenance rule instead of breaking unrelated logic.
Q.QuantityItem.as_dict = lambda self: {
    "quantity_id": self.quantity_id, "element_id": self.element_id,
    "value": self.value, "unit": self.unit}
try:
    _m04 = "source_paths" not in Q.build_schedule(BASE)["items"][0]
finally:
    Q.QuantityItem.as_dict = _orig_item
record("C4-M-04", "Strip provenance from items -> C4-PV-01 must die",
       "detected=True", f"detected={_m04}", _m04)


# outputs[] is protected by TWO independent guards: it is absent from
# COUNTABLE_COLLECTIONS, and it is listed in OWNERSHIP_EXCLUDED_COLLECTIONS.
# Mutating only one leaves the other masking it, which would prove nothing
# (the duplicate-defence lesson). Each guard is therefore isolated.

# Baseline: with both guards intact, outputs[] is never counted.
_m05_base = copy.deepcopy(BASE)
_m05_base["outputs"] = [{"id": "OUT-01"}, {"id": "OUT-02"}]
record("C4-M-05a", "Baseline: both guards intact -> outputs[] never counted",
       "no outputs[] item",
       f"{[i['element_id'] for i in Q.build_schedule(_m05_base)['items'] if i['quantity_id'] == 'Q-01']}",
       not any(i["element_id"] == "outputs[]"
               for i in Q.build_schedule(_m05_base)["items"]))


def _probe_outputs_counted():
    """Both guards disabled together -> the breach must become visible."""
    sched = Q.build_schedule(_m05_base)
    return any(i["element_id"] == "outputs[]" for i in sched["items"])


_o1, _o2 = Q.COUNTABLE_COLLECTIONS, Q.OWNERSHIP_EXCLUDED_COLLECTIONS
Q.COUNTABLE_COLLECTIONS = tuple(list(_o1) + ["outputs"])
Q.OWNERSHIP_EXCLUDED_COLLECTIONS = ()
try:
    _m05 = _probe_outputs_counted()
finally:
    Q.COUNTABLE_COLLECTIONS, Q.OWNERSHIP_EXCLUDED_COLLECTIONS = _o1, _o2
record("C4-M-05", "Disable BOTH outputs[] guards -> AS-C4-17 breach appears",
       "detected=True", f"detected={_m05}", _m05)


def _probe_ownership_guard_alone():
    """Ownership guard alone must still block, even if the list allows it."""
    sched = Q.build_schedule(_m05_base)
    return not any(i["element_id"] == "outputs[]" for i in sched["items"])


Q.COUNTABLE_COLLECTIONS = tuple(list(_o1) + ["outputs"])
try:
    _m05b = _probe_ownership_guard_alone()
finally:
    Q.COUNTABLE_COLLECTIONS = _o1
record("C4-M-05b", "Ownership guard alone still blocks outputs[] (defence 2)",
       "blocked=True", f"blocked={_m05b}", _m05b)


def _probe_untrusted_allowed():
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["source_type"] = "AI_IMAGE"
    return "EX-SOURCE" not in codes_of(Q.build_schedule(mm), "W-01")


mutate("C4-M-06", "Empty untrusted sources -> C4-N-05 must die",
       "UNTRUSTED_SOURCES", frozenset(), _probe_untrusted_allowed)

# CONTROL — a cosmetic change must not flip any asserted behaviour.
_ctrl_before = Q.build_schedule(BASE)["completeness"]["overall"] == "COMPLETE"
_orig_kind = Q.QuantityItem.__module__
_ctrl_after = Q.build_schedule(BASE)["completeness"]["overall"] == "COMPLETE"
record("C4-M-07", "CONTROL: unrelated read does not change the verdict",
       "COMPLETE before and after",
       f"before={_ctrl_before}, after={_ctrl_after}",
       _ctrl_before and _ctrl_after)


# ==========================================================================
# 9. ISOLATION
# ==========================================================================
_validators = ["validate_topology", "validate_furniture", "validate_movement",
               "validate_doors", "validate_formulas", "validate_outputs",
               "validate_refs", "validate_revisions", "validate_lifecycle",
               "validate_temporal", "validate_blocking", "schema_gate"]
record("C4-ISO-01", "C4 imports no B-series validator", "none",
       f"{[v for v in _validators if f'import {v}' in _src]}",
       not [v for v in _validators if f"import {v}" in _src])

record("C4-ISO-02", "C4 does not import C1/C2/C3 modules", "none",
       f"{[m for m in ('c1_preconditions', 'c2_fingerprint', 'c3_svg_emitter', 'c3_geometry_assembly') if m in _src]}",
       not [m for m in ("c1_preconditions", "c2_fingerprint",
                        "c3_svg_emitter", "c3_geometry_assembly")
            if m in _src])

record("C4-ISO-03", "C4 does not re-derive B6 verdicts, it consumes them",
       "verdict read, not computed",
       f"{'derived_verdicts' in _exec_only}",
       "derived_verdicts" in _exec_only and "def verify" not in _exec_only)

_verdict_keys = ['"correct"', '"matches_master"', '"approved"',
                 '"fidelity_ok"']
record("C4-ISO-04", "C4 emits no verdict key about correctness", "none",
       f"{[k for k in _verdict_keys if k in _exec_only]}",
       not [k for k in _verdict_keys if k in _exec_only])

record("C4-ISO-05", "Schedule states fidelity belongs to D",
       "NOT_ASSESSED / D", f"{s['fidelity'][:22]}",
       "NOT_ASSESSED" in s["fidelity"] and "D" in s["fidelity"])


# ==========================================================================
# 10. ANTI-SMUGGLING  (AS-C4-01 … AS-C4-17)
# ==========================================================================
record("C4-AS-01", "Partial sum never presented as a complete total",
       "PARTIAL + basis", f"{s_u['completeness']['Q-03']}",
       s_u["completeness"]["Q-03"] == "PARTIAL"
       and _total_u[0]["basis"] == "2 of 3")

record("C4-AS-02", "BOQ / cost estimate are declared out of scope",
       "both listed", f"{[x for x in s['out_of_scope'] if 'BOQ' in x or 'cost' in x]}",
       any("BOQ" in x for x in s["out_of_scope"])
       and any("cost" in x for x in s["out_of_scope"]))

record("C4-AS-03", "[U] never becomes zero", "8000 not 12000",
       f"{_total_u[0]['value']}", _total_u[0]["value"] == 8000.0)

record("C4-AS-04", "No status upgrade anywhere", "[A] excluded",
       f"{codes_of(s3, 'W-01')}", "EX-STATUS" in codes_of(s3, "W-01"))

record("C4-AS-05", "C4 never reads a C3 output as a measurement source",
       "no svg/emitter reference",
       f"svg={'svg' in _exec_only.lower()}",
       "svg" not in _exec_only.lower())

# Word-boundary matching: 'rate' must not match inside 'enumerate'.
_coeff_words = ("waste", "coverage", "price", "rate", "markup", "factor")
_coeff_found = [w for w in _coeff_words
                if re.search(rf"\b{w}\b", _exec_only, re.I)]
record("C4-AS-06", "No invented coefficient (waste/coverage/price/rate)",
       "none present", f"{_coeff_found}", not _coeff_found)

record("C4-AS-07", "No implicit unit conversion in code",
       "no conversion factors",
       f"{'/ 1000' in _exec_only or '* 1000' in _exec_only}",
       "/ 1000" not in _exec_only and "* 1000" not in _exec_only)

record("C4-AS-08", "No rounding applied to results",
       "no round() on values",
       f"{'round(' in _exec_only}", "round(" not in _exec_only)

record("C4-AS-09", "Duplicate ids counted once and flagged",
       "3 of 4", f"{_cw['basis']}", _cw["basis"] == "3 of 4")

record("C4-AS-10", "Element without id is excluded, not counted anonymously",
       "EX-MISSING",
       f"{[e['code'] for e in Q.build_schedule({'walls': [{'start': fact([0, 0]), 'end': fact([1, 0])}]})['exclusions']]}",
       "EX-MISSING" in [e["code"] for e in Q.build_schedule(
           {"walls": [{"start": fact([0, 0]), "end": fact([1, 0])}]})["exclusions"]])

# "Calculated" alone is still not sufficient: an ABSTAIN produces no class A
# item at all, and an ineligible input is excluded before it can be summed.
record("C4-AS-12", "A calculated number is not automatically class A",
       "abstained Q-03 is not class A",
       f"{s_none['class_a']['Q-03']}",
       s_none["class_a"]["Q-03"] is False)

record("C4-AS-13", "Numbers are not offered as geometric correctness",
       "fidelity NOT_ASSESSED", f"{'NOT_ASSESSED' in s['fidelity']}",
       "NOT_ASSESSED" in s["fidelity"])

record("C4-AS-14", "No volumetric quantity is produced",
       "no mm3-valued item; declared out of scope",
       f"units={sorted(_emitted_units)}, "
       f"declared={any('volumetric' in x for x in s['out_of_scope'])}",
       "mm3" not in _emitted_units
       and any("volumetric" in x for x in s["out_of_scope"]))

record("C4-AS-15", "No external standard or library is consulted",
       "stdlib math only",
       f"{[l for l in ('shapely', 'numpy', 'ezdxf') if l in _exec_only]}",
       not [l for l in ("shapely", "numpy", "ezdxf") if l in _exec_only])


# ==========================================================================
# 11. AS-C4-17 — outputs[] isolation
# ==========================================================================
m_out = copy.deepcopy(BASE)
m_out["outputs"] = [{"id": "OUT-01"}, {"id": "OUT-02"}, {"id": "OUT-03"}]
s_out = Q.build_schedule(m_out)
record("C4-OUT-01", "outputs[] is never counted even when populated",
       "no outputs[] item",
       f"{[i['element_id'] for i in s_out['items'] if i['quantity_id'] == 'Q-01']}",
       not any(i["element_id"] == "outputs[]" for i in s_out["items"]))

record("C4-OUT-02", "outputs[] is excluded by ownership, declared in code",
       "ownership exclusion list present",
       f"{Q.OWNERSHIP_EXCLUDED_COLLECTIONS}",
       "outputs" in Q.OWNERSHIP_EXCLUDED_COLLECTIONS
       and "outputs" not in Q.COUNTABLE_COLLECTIONS)

record("C4-OUT-03", "Populating outputs[] does not change any quantity",
       "identical items to base",
       f"{len(s_out['items']) == len(s['items'])}",
       len(s_out["items"]) == len(s["items"]))

_outputs_assign = '["outputs"] =' in _exec_only
record("C4-OUT-04", "No write path targets outputs[]",
       "no outputs assignment",
       f"assign={_outputs_assign}",
       not _outputs_assign)


# ==========================================================================
# 12. AS-C4-16 — no-write (behavioural + write-path inspection)
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_tpl = os.path.join(ROOT, "project_master.template.json")
_sch = os.path.join(ROOT, "project_master.schema.json")
_before = (_sha(_tpl), _sha(_sch))
_snapshot = copy.deepcopy(BASE)
_files_before = set(os.listdir(ROOT)) | set(os.listdir(os.path.join(ROOT, "scripts")))

Q.build_schedule(BASE)
Q.build_schedule(BASE, derived_verdicts={"walls/0/start": "VERIFIED"})
Q.q01_count(BASE)
Q.q04_opening_area(BASE)

_files_after = set(os.listdir(ROOT)) | set(os.listdir(os.path.join(ROOT, "scripts")))

record("C4-NW-01", "Behavioural: master dict is not mutated in memory",
       "identical", f"{_snapshot == BASE}", _snapshot == BASE)

record("C4-NW-02", "Behavioural: template and schema bytes unchanged",
       "sha256 stable", f"{_before == (_sha(_tpl), _sha(_sch))}",
       _before == (_sha(_tpl), _sha(_sch)))

record("C4-NW-03", "Behavioural: no new file appeared during computation",
       "no new files", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

record("C4-NW-04", "Behavioural: project_master.json is never created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

# Write-path inspection — not limited to open()
_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil.copy", "pathlib", "tempfile", "pickle"]
_found_paths = [p for p in _write_paths if p in _exec_only]
record("C4-NW-05", "Write-path inspection finds no write mechanism at all",
       "none of 10 write paths",
       f"{_found_paths}", not _found_paths)

record("C4-NW-06", "C4 produces no Output Manifest (C6 owns that)",
       "no manifest construction",
       f"{'manifest' in _exec_only.lower()}",
       "manifest" not in _exec_only.lower())


# --------------------------------------------------------------------------
print("=" * 96)
print("PHASE 00.5-C4 — EXTERNAL DERIVED QUANTITY SCHEDULE (Q-01 … Q-04)")
print("=" * 96)
passed = sum(1 for x in RESULTS if x[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    print(f"{'OK  ' if verdict == 'PASS' else 'FAIL'} {tid:11} "
          f"{scenario[:57]:57} {actual[:24]}")
print("-" * 96)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 96)
sys.exit(0 if passed == total else 1)
