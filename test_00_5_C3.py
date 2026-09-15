#!/usr/bin/env python3
"""Phase 00.5-C3 — Geometry Emitters (Class A, SVG, Tier 0 + Tier 1).

Reference: C3 Architecture (CLOSED) + Decision Resolution Addendum (CLOSED).
Approved contract: Tier 0 (outline, walls, identity/provenance, declared
omissions) + Tier 1 (openings). Out of scope: furniture, dimensions, Tier 4.

DISCIPLINE (inherited, CND-C2-02)
  AS-C2-16 — mutations must reach the code: probes call THROUGH the module
             (GA.x / EM.x), never through a name bound by `from x import y`.
  AS-C2-17 — no self-moving assertions: expectations are literals, not
             constants re-read from the engine under test.

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

import c3_geometry_assembly as GA                                    # noqa: E402
import c3_svg_emitter as EM                                          # noqa: E402

RESULTS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def fact(value, status="C", src="CLIENT_INPUT", unit="mm"):
    return {"value": value, "unit": unit, "status": status,
            "source_type": src, "source_ref": "intake/p1",
            "recorded_on": "2026-09-12"}


def base_master():
    """A minimal, internally consistent Tier 0+1 fixture."""
    return {
        "meta": {"project_id": "PRJ-01", "master_revision": "R01"},
        "space": {
            "outline": fact([[0, 0], [6000, 0], [6000, 4000], [0, 4000]],
                            unit="mm"),
            "ceiling_height": fact(2800),
        },
        "walls": [
            {"id": "W-01", "start": fact([0, 0]), "end": fact([6000, 0]),
             "thickness": fact(200)},
            {"id": "W-02", "start": fact([6000, 0]), "end": fact([6000, 4000]),
             "thickness": fact(200)},
        ],
        "openings": [
            {"id": "OP-01", "kind": "door", "host_wall": "W-01",
             "offset": fact(1000), "width": fact(900)},
        ],
    }


BASE = base_master()


# ==========================================================================
# 1. POSITIVE
# ==========================================================================
r = EM.emit_svg(BASE, identity=BASE["meta"])
record("C3-P-01", "Clean Tier 0+1 master emits an SVG", "EMITTED",
       f"{r['status']}", r["status"] == "EMITTED")

record("C3-P-02", "SVG is well-formed XML with an svg root",
       "declaration + <svg ... </svg>",
       f"ok={r['svg'].startswith('<?xml') and r['svg'].rstrip().endswith('</svg>')}",
       r["svg"].startswith("<?xml") and r["svg"].rstrip().endswith("</svg>"))

record("C3-P-03", "Both eligible walls are transcribed",
       "W-01 and W-02 present",
       f"n={len(r['assembly']['walls'])}",
       len(r["assembly"]["walls"]) == 2
       and 'data-id="W-01"' in r["svg"] and 'data-id="W-02"' in r["svg"])

record("C3-P-04", "Tier 1 opening is transcribed", "OP-01 present",
       f"n={len(r['assembly']['openings'])}",
       len(r["assembly"]["openings"]) == 1 and 'data-id="OP-01"' in r["svg"])

_op = r["assembly"]["openings"][0]
record("C3-P-05", "Opening placed by B2/B5 offset convention from wall start",
       "p0=[1000,0], p1=[1900,0]",
       f"p0={_op['p0']}, p1={_op['p1']}",
       _op["p0"][:2] == [1000.0, 0.0] and _op["p1"][:2] == [1900.0, 0.0])

record("C3-P-06", "Outline drawn from space/outline with provenance",
       "polygon + data-provenance",
       f"ok={'<polygon' in r['svg'] and 'data-provenance=\"space/outline\"' in r['svg']}",
       "<polygon" in r["svg"]
       and 'data-provenance="space/outline"' in r["svg"])

record("C3-P-07", "Output carries its scope tag",
       "Tier 0 + Tier 1 scope comment",
       f"tagged={'SCOPE: Tier 0 + Tier 1' in r['svg']}",
       "SCOPE: Tier 0 + Tier 1" in r["svg"])

_ep = EM.evidence_pack(r, environment={"runtime": "CPython"})
record("C3-P-08", "Evidence pack lists a coordinate table",
       "6 entries (2 walls x2 + opening x2)",
       f"n={len(_ep['coordinate_table'])}", len(_ep["coordinate_table"]) == 6)


# ==========================================================================
# 2. NEGATIVE — abstention with the intended cause
# ==========================================================================
m = copy.deepcopy(BASE)
m["space"]["outline"]["status"] = "U"
r2 = EM.emit_svg(m)
record("C3-N-01", "[U] outline -> abstain C3-ABS-01", "C3-ABS-01",
       f"{r2['status']}/{(r2['abstention'] or {}).get('code')}",
       r2["status"] == "ABSTAIN" and r2["abstention"]["code"] == "C3-ABS-01")

m = copy.deepcopy(BASE)
for w in m["walls"]:
    w["start"]["status"] = "P"
r3 = EM.emit_svg(m)
record("C3-N-02", "[P] wall endpoints -> no walls -> abstain C3-ABS-02",
       "C3-ABS-02", f"{(r3['abstention'] or {}).get('code')}",
       r3["status"] == "ABSTAIN" and r3["abstention"]["code"] == "C3-ABS-02")

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["status"] = "A"
m["walls"][0]["start"]["approval_state"] = "APPROVED"
r4 = EM.emit_svg(m)
_codes = [n["code"] for n in r4["assembly"]["not_represented"]]
record("C3-N-03", "APPROVED [A] is still ineligible -> NR-01 declared",
       "NR-01 present, wall dropped",
       f"walls={len(r4['assembly']['walls'])}, NR-01={'NR-01' in _codes}",
       len(r4["assembly"]["walls"]) == 1 and "NR-01" in _codes)

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["source_type"] = "AI_IMAGE"
r5 = EM.emit_svg(m)
_codes5 = [n["code"] for n in r5["assembly"]["not_represented"]]
record("C3-N-04", "AI_IMAGE source -> NR-02 declared, not transcribed",
       "NR-02 present", f"{'NR-02' in _codes5}", "NR-02" in _codes5)

m = copy.deepcopy(BASE)
m["openings"][0]["host_wall"] = "W-99"
r6 = EM.emit_svg(m)
_codes6 = [n["code"] for n in r6["assembly"]["not_represented"]]
record("C3-N-05", "Unknown host wall -> NR-06, opening not placed",
       "NR-06, 0 openings",
       f"n={len(r6['assembly']['openings'])}, NR-06={'NR-06' in _codes6}",
       not r6["assembly"]["openings"] and "NR-06" in _codes6)

m = copy.deepcopy(BASE)
m["openings"][0]["offset"]["status"] = "U"
r7 = EM.emit_svg(m)
record("C3-N-06", "[U] offset -> opening omitted, plan still emitted",
       "EMITTED with 0 openings",
       f"{r7['status']}, n={len(r7['assembly']['openings'])}",
       r7["status"] == "EMITTED" and not r7["assembly"]["openings"])

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["value"] = [float("nan"), 0]
r8 = EM.emit_svg(m)
record("C3-N-07", "NaN coordinate -> abstain C3-ABS-03, never rounded",
       "C3-ABS-03", f"{(r8['abstention'] or {}).get('code')}",
       r8["status"] == "ABSTAIN" and r8["abstention"]["code"] == "C3-ABS-03")

m = copy.deepcopy(BASE)
del m["walls"][0]["start"]
r9 = EM.emit_svg(m)
_codes9 = [n["code"] for n in r9["assembly"]["not_represented"]]
record("C3-N-08", "Missing required field -> NR-03, no default supplied",
       "NR-03 present", f"{'NR-03' in _codes9}", "NR-03" in _codes9)


# ==========================================================================
# 3. BOUNDARY
# ==========================================================================
m = copy.deepcopy(BASE)
m["walls"].append({"id": "W-03", "start": fact([100, 100]),
                   "end": fact([100, 100])})
m["openings"].append({"id": "OP-02", "kind": "window", "host_wall": "W-03",
                      "offset": fact(0), "width": fact(500)})
r10 = EM.emit_svg(m)
_ids10 = [o["id"] for o in r10["assembly"]["openings"]]
record("C3-BD-01", "Degenerate host wall -> opening abstains, B2 keeps the verdict",
       "OP-02 absent, plan emitted",
       f"{r10['status']}, openings={_ids10}",
       r10["status"] == "EMITTED" and "OP-02" not in _ids10)

m = copy.deepcopy(BASE)
m["walls"][0]["thickness"]["status"] = "U"
r11 = EM.emit_svg(m)
record("C3-BD-02", "[U] thickness: wall still drawn, thickness not invented",
       "wall present, thickness None",
       f"th={r11['assembly']['walls'][0]['thickness']}",
       r11["assembly"]["walls"][0]["thickness"] is None
       and r11["status"] == "EMITTED")

m = copy.deepcopy(BASE)
m["space"]["outline"]["value"] = [[0, 0], [6000, 0]]
r12 = EM.emit_svg(m)
record("C3-BD-03", "Two-point outline is not a polygon -> abstain",
       "ABSTAIN", f"{r12['status']}", r12["status"] == "ABSTAIN")

m = copy.deepcopy(BASE)
m["openings"][0]["offset"] = fact(0)
r13 = EM.emit_svg(m)
record("C3-BD-04", "Zero offset is a value, not a missing value",
       "opening placed at wall start",
       f"p0={r13['assembly']['openings'][0]['p0'][:2]}",
       r13["assembly"]["openings"][0]["p0"][:2] == [0.0, 0.0])

m = copy.deepcopy(BASE)
m["walls"][0]["start"]["value"] = [0.1 + 0.2, 0]
r14 = EM.emit_svg(m)
record("C3-BD-05", "Float noise is written faithfully, never rounded",
       "0.30000000000000004 in svg",
       f"present={'0.30000000000000004' in r14['svg']}",
       "0.30000000000000004" in r14["svg"])

m = copy.deepcopy(BASE)
m["openings"] = []
r15 = EM.emit_svg(m)
record("C3-BD-06", "No openings at all still yields a valid Tier 0 plan",
       "EMITTED", f"{r15['status']}", r15["status"] == "EMITTED")


# ==========================================================================
# 4. ZERO-INVENTION / PROVENANCE
# ==========================================================================
_wall_ids = {w["id"] for w in r["assembly"]["walls"]}
record("C3-ZI-01", "Output contains no element absent from the master",
       "no extra ids", f"{sorted(_wall_ids)}",
       _wall_ids == {"W-01", "W-02"})

_all_prov = all(w["start"]["provenance"] and w["end"]["provenance"]
                for w in r["assembly"]["walls"])
record("C3-ZI-02", "Every wall coordinate carries a master path",
       "all provenanced", f"{_all_prov}", _all_prov)

record("C3-ZI-03", "Every opening carries the paths it was derived from",
       "offset/width/host paths",
       f"n={len(_op['provenance'])}", len(_op["provenance"]) == 4)

_svg_lines = [ln for ln in r["svg"].splitlines() if "<line" in ln]
record("C3-ZI-04", "Drawn primitives equal transcribed elements (2 walls + 1 opening)",
       "3 lines", f"{len(_svg_lines)}", len(_svg_lines) == 3)

record("C3-ZI-05", "Zero-invention is explicitly NOT offered as fidelity",
       "fidelity NOT_ASSESSED / D-owned",
       f"{r['fidelity'][:24]}",
       "NOT_ASSESSED" in r["fidelity"] and "D" in r["fidelity"])

record("C3-ZI-06", "Evidence pack repeats that provenance != correct placement",
       "caveat present",
       f"{'NOT show the value was placed' in _ep['note']}",
       "NOT show the value was placed" in _ep["note"])

_nr_targets = [n["target"] for n in r["assembly"]["not_represented"]]
record("C3-ZI-07", "Out-of-contract tiers are declared, not silently dropped",
       "dimensions + Tier 4 declared",
       f"{'dimensions' in _nr_targets}",
       "dimensions" in _nr_targets
       and any("scale" in t for t in _nr_targets))

m = copy.deepcopy(BASE)
m["furniture"] = [{"id": "F-01"}, {"id": "F-02"}]
r16 = EM.emit_svg(m)
record("C3-ZI-08", "Furniture present in master is declared out of scope, not drawn",
       "NR-05 for furniture, not in svg",
       f"declared={any(n['target'] == 'furniture[]' for n in r16['assembly']['not_represented'])}",
       any(n["target"] == "furniture[]"
           for n in r16["assembly"]["not_represented"])
       and "F-01" not in r16["svg"])


# ==========================================================================
# 5. MUTATION  (AS-C2-16: always call through the module)
# ==========================================================================
def mutate(tid, scenario, attr, value, probe, module=GA, expect=True):
    original = getattr(module, attr)
    setattr(module, attr, value)
    try:
        got = probe()
    finally:
        setattr(module, attr, original)
    record(tid, scenario, f"detected={expect}", f"detected={got}",
           got == expect)


def _probe_a_eligible():
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["status"] = "A"
    mm["walls"][0]["start"]["approval_state"] = "APPROVED"
    return len(EM.emit_svg(mm)["assembly"]["walls"]) == 2


mutate("C3-M-01", "Allow [A] into eligible statuses -> C3-N-03 must die",
       "ELIGIBLE_STATUSES", frozenset({"C", "D", "A"}), _probe_a_eligible)


def _probe_untrusted():
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["source_type"] = "AI_IMAGE"
    return len(EM.emit_svg(mm)["assembly"]["walls"]) == 2


mutate("C3-M-02", "Empty untrusted sources -> C3-N-04 must die",
       "UNTRUSTED_SOURCES", frozenset(), _probe_untrusted)


def _probe_rounding():
    mm = copy.deepcopy(BASE)
    mm["walls"][0]["start"]["value"] = [0.1 + 0.2, 0]
    return "0.30000000000000004" not in EM.emit_svg(mm)["svg"]


mutate("C3-M-03", "Introduce rounding in _fmt -> C3-BD-05 must die",
       "_fmt", lambda v: (str(round(v, 2)), True)
       if isinstance(v, (int, float)) and not isinstance(v, bool)
       else (None, False),
       _probe_rounding, module=EM)


def _probe_silent_omission():
    """The mutation must remove a DECLARED omission, not just relabel it.

    Replacing the omit() helper with a no-op is the behavioural mutation;
    blanking the reason CODE only renames the record, which would prove
    nothing (the masked-mutation lesson, AS-C2-16).
    """
    return not EM.emit_svg(BASE)["assembly"]["not_represented"]


_orig_omit = GA.Assembly.omit
GA.Assembly.omit = lambda self, code, target, message: None
try:
    _m04 = _probe_silent_omission()
finally:
    GA.Assembly.omit = _orig_omit
record("C3-M-04", "Silence declared omissions -> C3-ZI-07 must die",
       "detected=True", f"detected={_m04}", _m04)

# CONTROL — an unrelated change must not flip the asserted behaviour.
_c_before = EM.emit_svg(BASE)["status"] == "EMITTED"
_orig_cid = EM.CONTRACT_ID
EM.CONTRACT_ID = "renamed/contract"
_c_after = EM.emit_svg(BASE)["status"] == "EMITTED"
EM.CONTRACT_ID = _orig_cid
record("C3-M-05", "CONTROL: cosmetic rename does not change emission",
       "EMITTED before and after", f"before={_c_before}, after={_c_after}",
       _c_before and _c_after)


# ==========================================================================
# 6. ISOLATION
# ==========================================================================
_src = (open(os.path.join(ROOT, "scripts", "c3_geometry_assembly.py"),
             encoding="utf-8").read()
        + open(os.path.join(ROOT, "scripts", "c3_svg_emitter.py"),
               encoding="utf-8").read())
_code_only = "\n".join(ln.split("#")[0] for ln in _src.splitlines()
                       if not ln.strip().startswith("#"))

_validators = ["validate_topology", "validate_furniture", "validate_movement",
               "validate_doors", "validate_formulas", "validate_outputs",
               "validate_refs", "validate_revisions", "validate_lifecycle",
               "validate_temporal", "validate_blocking", "schema_gate"]
_found = [v for v in _validators if f"import {v}" in _src]
record("C3-ISO-01", "C3 imports no B-series validator", "none",
       f"{_found}", not _found)

record("C3-ISO-02", "C3 does not re-run the C1 gate", "no c1 import",
       f"{'c1_preconditions' in _src}", "c1_preconditions" not in _src)

record("C3-ISO-03", "C3 requests no engineering fingerprint",
       "NOT_ISSUED declared",
       f"{'NOT_ISSUED' in r['engineering_fingerprint']}",
       "NOT_ISSUED" in r["engineering_fingerprint"]
       and "issue_engineering_fingerprint" not in _code_only)

record("C3-ISO-04", "C3 does not judge the degenerate wall itself (B2 owns it)",
       "reports inability only",
       f"{'belongs to B2' in _src}", "belongs to B2" in _src)

_verdict_keys = ['"fidelity_ok"', '"matches_master"', '"approved"',
                 '"is_correct"']
record("C3-ISO-05", "C3 emits no fidelity/approval verdict key", "none",
       f"{[k for k in _verdict_keys if k in _code_only]}",
       not [k for k in _verdict_keys if k in _code_only])


# ==========================================================================
# 7. ANTI-SMUGGLING
# ==========================================================================
record("C3-AS-01", "No coordinate is invented for a missing field",
       "NR-03 instead of a value",
       f"{'NR-03' in _codes9}", "NR-03" in _codes9)

record("C3-AS-02", "No status upgrade: [A]/[P]/[U] never become geometry",
       "all three excluded",
       f"A={'NR-01' in _codes}, P_abstain={r3['status']}",
       "NR-01" in _codes and r3["status"] == "ABSTAIN")

# Prose that FORBIDS a default ("a missing rotation is NOT 0") is
# documentation, so the check must target executable code only.
_exec_only = re.sub(r'""".*?"""', "", _src, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
record("C3-AS-03", "No rotation/CENTER default in executable code",
       "neither token in code",
       f"rotation={'rotation' in _exec_only.lower()}, "
       f"center={'center' in _exec_only.lower()}",
       "rotation" not in _exec_only.lower()
       and "center" not in _exec_only.lower())

# ...and positively: an absent optional fact yields None, never a substitute.
_m_norot = copy.deepcopy(BASE)
_m_norot["walls"][0].pop("thickness")
_r_norot = EM.emit_svg(_m_norot)
record("C3-AS-03b", "Absent optional fact yields None, not a filled-in default",
       "thickness is None",
       f"{_r_norot['assembly']['walls'][0]['thickness']}",
       _r_norot["assembly"]["walls"][0]["thickness"] is None)

record("C3-AS-04", "No enrichment: no grid/frame/title added",
       "only declared groups",
       f"{r['svg'].count('<g id=')}", r["svg"].count("<g id=") == 3)

record("C3-AS-05", "Nothing is dropped silently: omissions are declared",
       "not_represented non-empty",
       f"n={len(r['assembly']['not_represented'])}",
       len(r["assembly"]["not_represented"]) >= 2)

record("C3-AS-06", "No D1/D2 claim is raised by C3",
       "D1 NOT_ESTABLISHED, D2 NOT_CLAIMED",
       f"{r['determinism']['D1']}/{r['determinism']['D2']}",
       r["determinism"]["D1"] == "NOT_ESTABLISHED"
       and r["determinism"]["D2"] == "NOT_CLAIMED")

_cap = EM.capability_report()
record("C3-AS-07", "Capability is declared per format x output, not blanket",
       "three levels + scoping note",
       f"capable={_cap['capable']}, scoped={'per (format x output)' in _cap['note']}",
       _cap["level_1_format_capability"] and _cap["level_2_approved_output_contract"]
       and _cap["level_3_runtime_capability"]
       and "per (format x output)" in _cap["note"])

record("C3-AS-08", "Partial output cannot masquerade as a complete drawing",
       "scope tag + NOT a complete construction drawing",
       f"{'NOT a complete construction drawing' in r['svg']}",
       "NOT a complete construction drawing" in r["svg"])

record("C3-AS-09", "Emitter returns text and does not persist it itself",
       "no file write in module",
       f"{'open(' in _code_only}", "open(" not in _code_only)


# ==========================================================================
# 8. NO-WRITE
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_tpl = os.path.join(ROOT, "project_master.template.json")
_sch = os.path.join(ROOT, "project_master.schema.json")
_before_h = (_sha(_tpl), _sha(_sch))
_snapshot = copy.deepcopy(BASE)

EM.emit_svg(BASE)
EM.evidence_pack(EM.emit_svg(BASE))
GA.assemble(BASE)

record("C3-NW-01", "Emission does not mutate the master in memory",
       "identical", f"{_snapshot == BASE}", _snapshot == BASE)
record("C3-NW-02", "Template and schema are untouched",
       "sha256 unchanged", f"{_before_h == (_sha(_tpl), _sha(_sch))}",
       _before_h == (_sha(_tpl), _sha(_sch)))
record("C3-NW-03", "No project_master.json is created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))
record("C3-NW-04", "No outputs[] access anywhere in C3",
       "no outputs[] read or write",
       f"{'outputs' in _code_only}", "outputs" not in _code_only)


# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-C3 — GEOMETRY EMITTERS (CLASS A · SVG · TIER 0 + TIER 1)")
print("=" * 94)
passed = sum(1 for x in RESULTS if x[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    print(f"{'OK  ' if verdict == 'PASS' else 'FAIL'} {tid:10} "
          f"{scenario[:56]:56} {actual[:26]}")
print("-" * 94)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 94)
sys.exit(0 if passed == total else 1)
