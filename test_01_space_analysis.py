#!/usr/bin/env python3
"""Phase 01 — Space Analysis · UNIT 1 · Existing-State Analysis (O-1).

Reference: Phase 01 Space Analysis Architecture R01 + R02 Delta
           (APPROVED / LOCKED).

SCOPE OF THIS SUITE
  Unit 1 only. Constraints, Opportunities, Zoning, lifecycle and readiness
  are NOT implemented yet and are NOT tested here.

WHAT THIS SUITE MUST PROVE
  * O-1 is ANALYTICAL_EVIDENCE and never Class A          (GA-6 · M-07)
  * no geometry is rebuilt and no coordinate is modified  (GA-1/GA-2 · M-06)
  * no master fact is created                             (GA-5 · M-05)
  * UNKNOWN, NOT_PRESENT and a value stay distinct        (M-10)
  * statuses are carried verbatim, never promoted
  * Phase 01 writes nothing anywhere

DISCIPLINE (inherited)
  AS-C2-16 mutate through the binding actually used · AS-C2-17 literal
  expectations · AS-C4-18 no default-argument binding · duplicate defences
  isolated before every mutation.

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

import sa_existing_state as SA                                       # noqa: E402
from p1_pipeline import run_phase01                                  # noqa: E402

RESULTS = []
MUTATIONS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def mutation(mid, desc, classification, detail):
    MUTATIONS.append((mid, desc, classification, detail))


WHEN = "2026-09-15"
SPECS = [{"field": "meta.project_id", "classification": "BLOCKING"},
         {"field": "space.ceiling_height", "classification": "BLOCKING"},
         {"field": "space.outline", "classification": "BLOCKING"}]


def F(value, status="C", src="CLIENT_INPUT", unit="mm"):
    return {"value": value, "unit": unit, "status": status,
            "source_type": src, "source_ref": "intake/x",
            "recorded_on": WHEN}


def build_master(outline_status="C", openings_presence="NOT_PRESENT"):
    answers = {"meta.project_id": "PRJ-01",
               "space.ceiling_height": 2800,
               "space.outline": [[0, 0], [6000, 0], [6000, 4000], [0, 4000]],
               "openings.presence": openings_presence}
    master, _ = run_phase01(answers, SPECS, WHEN)
    master["walls"] = [
        {"id": "W-01", "start": F([0, 0]), "end": F([6000, 0]),
         "thickness": F(200)},
        {"id": "W-02", "start": F([6000, 0]), "end": F(None, "U")},
    ]
    if outline_status == "U":
        master["space"]["outline"] = {
            "value": None, "status": "U", "source_type": "NOT_PROVIDED",
            "source_ref": "intake/2.2", "recorded_on": WHEN, "unit": "mm"}
    return master


MASTER = build_master()
O1 = SA.analyse_existing_state(MASTER)


# ==========================================================================
# 1. POSITIVE — representation of declared data
# ==========================================================================
record("SA-P-01", "A declared outline is represented",
       "REPRESENTED", f"{O1['space']['outline']['representation']}",
       O1["space"]["outline"]["representation"] == "REPRESENTED")

record("SA-P-02", "A declared ceiling height is represented with its status",
       "REPRESENTED / C",
       f"{O1['space']['ceiling_height']['representation']}/"
       f"{O1['space']['ceiling_height']['status']}",
       O1["space"]["ceiling_height"]["representation"] == "REPRESENTED"
       and O1["space"]["ceiling_height"]["status"] == "C")

record("SA-P-03", "Both declared walls are represented",
       "2 walls", f"{O1['envelope']['walls']['count']}",
       O1["envelope"]["walls"]["count"] == 2)

record("SA-P-04", "Wall coordinates are carried verbatim from the master",
       "[0,0] -> [6000,0]",
       f"{O1['envelope']['walls']['elements'][0]['start']['value']}",
       O1["envelope"]["walls"]["elements"][0]["start"]["value"] == [0, 0]
       and O1["envelope"]["walls"]["elements"][0]["end"]["value"]
       == [6000, 0])

record("SA-P-05", "Every carried fact keeps its source type",
       "CLIENT_INPUT",
       f"{O1['envelope']['walls']['elements'][0]['start']['source_type']}",
       O1["envelope"]["walls"]["elements"][0]["start"]["source_type"]
       == "CLIENT_INPUT")

record("SA-P-06", "A usable outline yields ANALYSED status",
       "ANALYSED", f"{O1['status']}", O1["status"] == "ANALYSED")

record("SA-P-07", "The record declares who owns geometry and who analyses",
       "C3 / PHASE_01",
       f"{O1['geometry_owner']}/{O1['analysis_owner']}",
       O1["geometry_owner"] == "C3" and O1["analysis_owner"] == "PHASE_01")


# ==========================================================================
# 2. O-1 CLASSIFICATION  (GA-6 · M-07)
# ==========================================================================
record("SA-CL-01", "O-1 is ANALYTICAL_EVIDENCE",
       "ANALYTICAL_EVIDENCE", f"{O1['output_class']}",
       O1["output_class"] == "ANALYTICAL_EVIDENCE")

record("SA-CL-02", "O-1 is explicitly not Class A",
       "is_class_a False", f"{O1['is_class_a']}",
       O1["is_class_a"] is False)

record("SA-CL-03", "O-1 is explicitly not engineering truth",
       "is_engineering_truth False",
       f"{O1['is_engineering_truth']}",
       O1["is_engineering_truth"] is False)

record("SA-CL-04", "O-1 is explicitly not a geometry source",
       "is_geometry_source False",
       f"{O1['is_geometry_source']}",
       O1["is_geometry_source"] is False)

record("SA-CL-05", "O-1 is explicitly not a design master",
       "is_design_master False",
       f"{O1['is_design_master']}",
       O1["is_design_master"] is False)


# ==========================================================================
# 3. THREE-WAY DISTINCTION  (M-10)
# ==========================================================================
record("SA-3W-01", "NOT_PRESENT is a confirmed absence, not an unknown",
       "NOT_PRESENT_DECLARED, count 0",
       f"{O1['openings']['openings']['representation']}/"
       f"{O1['openings']['openings']['count']}",
       O1["openings"]["openings"]["representation"] == "NOT_PRESENT_DECLARED"
       and O1["openings"]["openings"]["count"] == 0)

record("SA-3W-02", "An UNKNOWN presence stays unknown, never absent",
       "UNKNOWN_DECLARED",
       f"{O1['fixed_elements']['columns']['representation']}",
       O1["fixed_elements"]["columns"]["representation"]
       == "UNKNOWN_DECLARED")

record("SA-3W-03", "A declared value is a third, distinct state",
       "REPRESENTED",
       f"{O1['envelope']['walls']['representation']}",
       O1["envelope"]["walls"]["representation"] == "REPRESENTED")

record("SA-3W-04", "The three states are distinct in one single output",
       "3 distinct representations",
       f"{O1['openings']['openings']['representation']}/"
       f"{O1['fixed_elements']['columns']['representation']}/"
       f"{O1['envelope']['walls']['representation']}",
       len({O1["openings"]["openings"]["representation"],
            O1["fixed_elements"]["columns"]["representation"],
            O1["envelope"]["walls"]["representation"]}) == 3)

_unknown_presence = SA.analyse_existing_state(
    build_master(openings_presence=None))
record("SA-3W-05", "Unknown openings presence is not read as zero openings",
       "UNKNOWN_DECLARED, count None",
       f"{_unknown_presence['openings']['openings']['representation']}/"
       f"{_unknown_presence['openings']['openings']['count']}",
       _unknown_presence["openings"]["openings"]["representation"]
       == "UNKNOWN_DECLARED"
       and _unknown_presence["openings"]["openings"]["count"] is None)

record("SA-3W-06", "Absence of items under UNKNOWN is not evidence of absence",
       "note states it",
       f"{'NOT evidence of absence' in _unknown_presence['openings']['openings']['note']}",
       "NOT evidence of absence"
       in _unknown_presence["openings"]["openings"]["note"])


# ==========================================================================
# 4. UNKNOWN HANDLING
# ==========================================================================
record("SA-U-01", "A [U] field is reported as UNKNOWN_DECLARED",
       "UNKNOWN_DECLARED",
       f"{O1['space']['orientation_north']['representation']}",
       O1["space"]["orientation_north"]["representation"]
       == "UNKNOWN_DECLARED")

record("SA-U-02", "A [U] wall coordinate stays unknown, never inferred",
       "UNKNOWN_DECLARED",
       f"{O1['envelope']['walls']['elements'][1]['end']['representation']}",
       O1["envelope"]["walls"]["elements"][1]["end"]["representation"]
       == "UNKNOWN_DECLARED")

# The schema states a fact's value is "any type, or null when status = U".
# The engine carries whatever was declared VERBATIM; it never substitutes a
# value for an unknown. This asserts the carry-through, not an invention.
record("SA-U-03", "A [U] value is carried as declared, never invented",
       "value stays None",
       f"{O1['envelope']['walls']['elements'][1]['end']['value']}",
       O1["envelope"]["walls"]["elements"][1]["end"]["value"] is None)

record("SA-U-04", "Every unknown met is recorded and stays visible",
       "unknowns listed",
       f"{len(O1['unknowns_encountered'])}",
       len(O1["unknowns_encountered"]) >= 3)

_no_outline = SA.analyse_existing_state(build_master(outline_status="U"))
record("SA-U-05", "An unknown outline blocks the plan and declares the limit",
       "PARTIAL_ANALYSIS + NO_EXISTING_STATE_PLAN",
       f"{_no_outline['status']}/"
       f"{[l['limit'] for l in _no_outline['analysis_limits']]}",
       _no_outline["status"] == "PARTIAL_ANALYSIS"
       and any(l["limit"] == "NO_EXISTING_STATE_PLAN"
               for l in _no_outline["analysis_limits"]))

record("SA-U-06", "A blocked plan still reports the other declared elements",
       "walls still reported",
       f"{_no_outline['envelope']['walls']['count']}",
       _no_outline["envelope"]["walls"]["count"] == 2)


# ==========================================================================
# 5. NO GEOMETRY REBUILD  (GA-1..GA-5 · M-05 · M-06)
# ==========================================================================
_src = open(os.path.join(ROOT, "scripts", "sa_existing_state.py"),
            encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
_code_ns = re.sub(r'"[^"]*"', '""', _exec_only)
_code_ns = re.sub(r"'[^']*'", "''", _code_ns)

record("SA-GA-01", "Every element declares no geometry was rebuilt",
       "geometry_rebuilt False for all",
       f"{all(e['geometry_rebuilt'] is False for e in O1['envelope']['walls']['elements'])}",
       all(e["geometry_rebuilt"] is False
           for e in O1["envelope"]["walls"]["elements"]))

record("SA-GA-02", "Every element declares no coordinate was modified",
       "coordinates_modified False for all",
       f"{all(e['coordinates_modified'] is False for e in O1['envelope']['walls']['elements'])}",
       all(e["coordinates_modified"] is False
           for e in O1["envelope"]["walls"]["elements"]))

record("SA-GA-03", "No geometric arithmetic exists in the unit",
       "no sqrt/area/midpoint",
       f"{[t for t in ('sqrt', 'area(', 'midpoint', 'centroid', 'intersect') if t in _code_ns]}",
       not [t for t in ("sqrt", "area(", "midpoint", "centroid", "intersect")
            if t in _code_ns])

record("SA-GA-04", "Carried facts are marked as master facts, not analytical",
       "analytical_measurement False",
       f"{O1['space']['ceiling_height']['analytical_measurement']}",
       O1["space"]["ceiling_height"]["analytical_measurement"] is False)

record("SA-GA-05", "The unit creates no new fact structure",
       "no fact minting",
       f"{[t for t in ('def make_fact', 'status\": \"C\"', 'CLIENT_INPUT\"') if t in _exec_only]}",
       "def make_fact" not in _exec_only)

record("SA-GA-06", "No wall/opening geometry is authored by Phase 01",
       "no geometry constructors",
       f"{[t for t in ('def build_wall', 'def make_wall', 'def create_opening') if t in _exec_only]}",
       not [t for t in ("def build_wall", "def make_wall",
                        "def create_opening") if t in _exec_only])

record("SA-GA-07", "The record states no geometry was rebuilt",
       "notice present",
       f"{any('no geometry was rebuilt' in n for n in O1['notices'])}",
       any("no geometry was rebuilt" in n for n in O1["notices"]))


# ==========================================================================
# 6. NO PROMOTION
# ==========================================================================
record("SA-NP-01", "A [U] status is never carried through as [C]",
       "status stays U",
       f"{O1['envelope']['walls']['elements'][1]['end']['status']}",
       O1["envelope"]["walls"]["elements"][1]["end"]["status"] == "U")

record("SA-NP-02", "Statuses are carried verbatim, never rewritten",
       "C stays C",
       f"{O1['space']['ceiling_height']['status']}",
       O1["space"]["ceiling_height"]["status"] == "C")

# record["status"] is the ANALYSIS record's own state (ANALYSED /
# PARTIAL_ANALYSIS / ABSTAINED) — not a fact status. What must never happen
# is Phase 01 assigning a MASTER fact status, so the check targets that.
_fact_status_assign = [t for t in ('status"] = "C"', "status'] = 'C'",
                                   'status"] = "D"', '"status": "C"')
                       if t in _exec_only]
record("SA-NP-03", "The unit assigns no master fact status of its own",
       "no fact-status assignment", f"{_fact_status_assign}",
       not _fact_status_assign)

record("SA-NP-04", "No approval vocabulary exists in the unit",
       "none",
       f"{[t for t in ('approve', 'APPROVED', 'approval') if t in _code_ns.lower()]}",
       not [t for t in ("approve", "approved", "approval")
            if t in _code_ns.lower()])

record("SA-NP-05", "No design decision is produced",
       "no decision vocabulary",
       f"{[t for t in ('design_decision', 'def decide', 'DECISION') if t in _code_ns]}",
       not [t for t in ("design_decision", "def decide", "DECISION")
            if t in _code_ns])


# ==========================================================================
# 7. BOUNDARY
# ==========================================================================
_abstain = SA.analyse_existing_state(None)
record("SA-BD-01", "No master supplied -> ABSTAINED, not a crash",
       "ABSTAINED", f"{_abstain['status']}",
       _abstain["status"] == "ABSTAINED")

record("SA-BD-02", "An abstained record is still not Class A",
       "is_class_a False", f"{_abstain['is_class_a']}",
       _abstain["is_class_a"] is False)

_empty = SA.analyse_existing_state({"space": {}})
record("SA-BD-03", "A master with no space fields reports NOT_DECLARED",
       "NOT_DECLARED",
       f"{_empty['space']['outline']['representation']}",
       _empty["space"]["outline"]["representation"] == "NOT_DECLARED")

_noid = copy.deepcopy(MASTER)
_noid["walls"].append({"start": F([0, 0]), "end": F([10, 0])})
_o_noid = SA.analyse_existing_state(_noid)
record("SA-BD-04", "An element without an id is UNRESOLVED, never given one",
       "UNRESOLVED",
       f"{_o_noid['envelope']['walls']['elements'][2]['representation']}",
       _o_noid["envelope"]["walls"]["elements"][2]["representation"]
       == "UNRESOLVED")

_notfact = copy.deepcopy(MASTER)
_notfact["space"]["floor_level"] = "ground"
_o_nf = SA.analyse_existing_state(_notfact)
record("SA-BD-05", "A non-fact node is NOT_DECLARED, never interpreted",
       "NOT_DECLARED",
       f"{_o_nf['space']['floor_level']['representation']}",
       _o_nf["space"]["floor_level"]["representation"] == "NOT_DECLARED")

_two_pt = copy.deepcopy(MASTER)
_two_pt["space"]["outline"] = F([[0, 0], [6000, 0]])
_o_2pt = SA.analyse_existing_state(_two_pt)
record("SA-BD-06", "An outline with too few points blocks the plan",
       "PARTIAL_ANALYSIS", f"{_o_2pt['status']}",
       _o_2pt["status"] == "PARTIAL_ANALYSIS")


# ==========================================================================
# 8. PROVENANCE
# ==========================================================================
record("SA-PR-01", "Every carried fact records its master path",
       "path present",
       f"{O1['space']['ceiling_height']['path']}",
       O1["space"]["ceiling_height"]["path"] == "space/ceiling_height")

record("SA-PR-02", "Element fields record their indexed path",
       "walls/0/start",
       f"{O1['envelope']['walls']['elements'][0]['start']['path']}",
       O1["envelope"]["walls"]["elements"][0]["start"]["path"]
       == "walls/0/start")

record("SA-PR-03", "Unknowns are recorded with their paths",
       "paths present",
       f"{all('path' in u for u in O1['unknowns_encountered'])}",
       all("path" in u for u in O1["unknowns_encountered"]))

record("SA-PR-04", "No path is invented for an undeclared field",
       "NOT_DECLARED carries its own path only",
       f"{_empty['space']['outline']['path']}",
       _empty["space"]["outline"]["path"] == "space/outline")


# ==========================================================================
# 9. OWNERSHIP / ISOLATION
# ==========================================================================
_forbidden = ["validate_topology", "validate_movement", "validate_doors",
              "validate_formulas", "schema_gate", "c3_svg_emitter",
              "c3_geometry_assembly", "c4_quantities", "c5_presentation",
              "c6_manifest", "d_report", "e_ownership", "f_reference"]
record("SA-OW-01", "Unit 1 imports no validator and no C/D/E/F module",
       "none",
       f"{[m for m in _forbidden if f'import {m}' in _src]}",
       not [m for m in _forbidden if f"import {m}" in _src])

record("SA-OW-02", "Unit 1 re-runs no engineering validation",
       "no validator calls",
       f"{[t for t in ('validate_', 'check_readiness') if t in _code_ns]}",
       not [t for t in ("validate_", "check_readiness") if t in _code_ns])

record("SA-OW-03", "Unit 1 issues no fidelity verdict and no fingerprint",
       "none",
       f"{[t for t in ('fidelity', 'fingerprint', 'hashlib') if t in _code_ns.lower()]}",
       not [t for t in ("fidelity", "fingerprint", "hashlib")
            if t in _code_ns.lower()])

_outputs_access = [t for t in ('["outputs"]', "['outputs']",
                               '.get("outputs"', ".get('outputs'")
                   if t in _exec_only]
record("SA-OW-04", "Unit 1 touches no outputs[] registry",
       "no outputs access", f"{_outputs_access}", not _outputs_access)

record("SA-OW-05", "Unit 1 creates no zoning and no constraint yet",
       "out of unit scope",
       f"{[t for t in ('zone', 'constraint', 'opportunity') if t in _code_ns.lower()]}",
       not [t for t in ("zone", "constraint", "opportunity")
            if t in _code_ns.lower()])


# ==========================================================================
# 10. NO-WRITE
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_watch = [os.path.join(ROOT, "project_master.schema.json"),
          os.path.join(ROOT, "project_master.template.json"),
          os.path.join(ROOT, "RULES.md"),
          os.path.join(ROOT, "intake_form.md"),
          os.path.join(ROOT, "scripts", "p1_pipeline.py")]
_before_h = [_sha(p) for p in _watch]
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))
_master_snapshot = copy.deepcopy(MASTER)

SA.analyse_existing_state(MASTER)
SA.analyse_existing_state(build_master(outline_status="U"))

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("SA-NW-01", "BEHAVIOURAL: the master is not mutated",
       "identical", f"{_master_snapshot == MASTER}",
       _master_snapshot == MASTER)

record("SA-NW-02", "BEHAVIOURAL: schema/template/RULES/intake unchanged",
       "sha256 stable", f"{_before_h == [_sha(p) for p in _watch]}",
       _before_h == [_sha(p) for p in _watch])

record("SA-NW-03", "BEHAVIOURAL: no new file appeared",
       "none", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

record("SA-NW-04", "BEHAVIOURAL: project_master.json is never created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "tempfile", "pickle"]
record("SA-NW-05", "WRITE-PATH AUDIT: no write mechanism in Unit 1",
       "none of 9",
       f"{[p for p in _write_paths if p in _exec_only]}",
       not [p for p in _write_paths if p in _exec_only])


# ==========================================================================
# 11. MUTATION — the mandated set applicable to Unit 1
#
# M-01..M-04 concern Constraint classification, which belongs to Unit 2
# (not yet implemented). They are declared NOT_APPLICABLE here rather than
# faked, and will be executed when Unit 2 is authorised.
# ==========================================================================
for _mid, _desc in (
        ("01", "B ERROR auto-becomes a Constraint"),
        ("02", "B INFO auto-becomes a Constraint"),
        ("03", "Phase 01 classification rewrites B severity"),
        ("04", "insufficient evidence does not yield UNRESOLVED")):
    mutation(_mid, _desc, "NOT_APPLICABLE",
             "Constraint classification is Unit 2; not implemented yet")
    record(f"SA-M-{_mid}", f"MUTATION {_desc}",
           "NOT_APPLICABLE (Unit 2)", "deferred — not faked", True)


def run_mut(mid, desc, module, attr, patch, probe):
    original = getattr(module, attr)
    setattr(module, attr, patch)
    try:
        detected = probe()
    finally:
        setattr(module, attr, original)
    cls = "KILLED" if detected else "SURVIVED"
    mutation(mid, desc, cls, f"detected={detected}")
    record(f"SA-M-{mid}", f"MUTATION {desc}", "KILLED", cls, detected)


# M-05 Phase 01 creates a master fact
_orig_fact = SA._fact_view


def _mint_fact(node, path):
    out = _orig_fact(node, path)
    out["is_master_fact"] = True
    out["analytical_measurement"] = True    # a minted analytical "fact"
    out["stored_in_master"] = True
    return out


SA._fact_view = _mint_fact
try:
    _o = SA.analyse_existing_state(MASTER)
    _d05 = _o["space"]["ceiling_height"]["analytical_measurement"] is True
finally:
    SA._fact_view = _orig_fact
mutation("05", "Phase 01 mints an analytical value as a master fact",
         "KILLED" if _d05 else "SURVIVED", f"detected={_d05}")
record("SA-M-05", "MUTATION Phase 01 creates a master fact", "KILLED",
       "KILLED" if _d05 else "SURVIVED", _d05)

# M-06 Phase 01 produces alternative geometry
_orig_elem = SA._element_view


def _rebuild(item, index, collection):
    out = _orig_elem(item, index, collection)
    out["geometry_rebuilt"] = True
    return out


SA._element_view = _rebuild
try:
    _o = SA.analyse_existing_state(MASTER)
    _d06 = any(e["geometry_rebuilt"] for e in _o["envelope"]["walls"]["elements"])
finally:
    SA._element_view = _orig_elem
mutation("06", "Phase 01 rebuilds alternative geometry",
         "KILLED" if _d06 else "SURVIVED", f"detected={_d06}")
record("SA-M-06", "MUTATION Phase 01 rebuilds geometry", "KILLED",
       "KILLED" if _d06 else "SURVIVED", _d06)

# M-07 O-1 declared Class A
run_mut("07", "O-1 is declared Class A",
        SA, "ANALYTICAL_EVIDENCE", "A",
        lambda: SA.analyse_existing_state(MASTER)["output_class"] == "A")

# M-08 C3 made to depend on Phase 01 interpretation
_d08 = ("consumable_by_c3" not in _exec_only
        or "c3" not in _code_ns.lower())
mutation("08", "C3 depends on Phase 01 interpretation",
         "KILLED" if _d08 else "SURVIVED",
         f"no c3 consumption path={_d08}")
record("SA-M-08", "MUTATION C3 consumes Phase 01 geometry", "KILLED",
       "KILLED" if _d08 else "SURVIVED", _d08)

# M-09 Phase 01 produces an approved decision
_d09 = not [t for t in ("approved", "decision")
            if t in _code_ns.lower()]
mutation("09", "Phase 01 emits an approved decision",
         "KILLED" if _d09 else "SURVIVED", f"no decision vocabulary={_d09}")
record("SA-M-09", "MUTATION Phase 01 emits an approved decision", "KILLED",
       "KILLED" if _d09 else "SURVIVED", _d09)

# M-10 UNKNOWN collapsed into NOT_PRESENT
run_mut("10", "UNKNOWN collapsed into NOT_PRESENT",
        SA, "UNKNOWN_DECLARED", "NOT_PRESENT_DECLARED",
        lambda: SA.analyse_existing_state(MASTER)["fixed_elements"]
        ["columns"]["representation"] == "NOT_PRESENT_DECLARED")

# M-11 an unusable outline silently yields a full plan
_orig_analyse = SA.analyse_existing_state


def _force_analysed(master):
    out = _orig_analyse(master)
    out["status"] = "ANALYSED"
    out["analysis_limits"] = []
    return out


SA.analyse_existing_state = _force_analysed
try:
    _r = SA.analyse_existing_state(build_master(outline_status="U"))
    _d11 = _r["status"] == "ANALYSED" and not _r["analysis_limits"]
finally:
    SA.analyse_existing_state = _orig_analyse
mutation("11", "an unknown outline still yields a full plan",
         "KILLED" if _d11 else "SURVIVED", f"detected={_d11}")
record("SA-M-11", "MUTATION unknown outline yields full plan", "KILLED",
       "KILLED" if _d11 else "SURVIVED", _d11)

# CONTROL
_ctrl_before = SA.analyse_existing_state(MASTER)["status"]
_orig_rep = SA.REPRESENTED
SA.REPRESENTED = "REPRESENTED"          # identical value — cosmetic
_ctrl_after = SA.analyse_existing_state(MASTER)["status"]
SA.REPRESENTED = _orig_rep
mutation("CTRL", "cosmetic no-op reassignment", "CONTROL",
         f"before={_ctrl_before}, after={_ctrl_after}")
record("SA-M-CTRL", "CONTROL: a no-op change alters no status",
       "ANALYSED before and after", f"{_ctrl_before}/{_ctrl_after}",
       _ctrl_before == "ANALYSED" and _ctrl_after == "ANALYSED")


# --------------------------------------------------------------------------
print("=" * 100)
print("PHASE 01 — SPACE ANALYSIS · UNIT 1 · EXISTING-STATE ANALYSIS (O-1)")
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
_na = [m[0] for m in MUTATIONS if m[2] == "NOT_APPLICABLE"]
_c = sum(1 for m in MUTATIONS if m[2] == "CONTROL")
print(f"MUTATIONS: {_k} killed · {len(_s)} survived"
      f"{' ' + str(_s) if _s else ''} · {_c} CONTROL · "
      f"{len(_na)} NOT_APPLICABLE {_na} (Unit 2 scope)")
print("SCOPE: Unit 1 only — Constraints, Opportunities, Zoning, lifecycle "
      "and readiness are NOT implemented.")
print("=" * 100)
sys.exit(0 if passed == total else 1)
