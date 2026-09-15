#!/usr/bin/env python3
"""Agent Interfaces — smoke suite for ida_api / ida CLI / workspace.

WHAT THIS SUITE MUST PROVE
  * the workspace layer creates the documented layout and refuses overwrite
  * intake + pipeline run through the API with the approved lifecycle
  * validate_all is truthful on schema-invalid masters (interface completion:
    the G3 carrier gap must not surface as PASS)
  * generation (plan / quantities / B / fidelity / manifest / O-1) works
    end to end on a synthetic TEST master
  * governance helpers enforce USER-only approval and No Auto-Apply
  * the CLI answers --help, emits JSON, and uses the documented exit codes

All data below is synthetic and exists only to exercise the interfaces.
TEST PROJECT — NOT A REAL CLIENT PROJECT.

Python 3.11 compatible (no 3.12-only f-string syntax).
"""

import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ida_api as API                                          # noqa: E402
import ida_workspace as WS                                     # noqa: E402

RESULTS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


WHEN = "2026-09-15"
REF = "interface test fixture (TEST)"

SPECS = [
    {"field": "meta.project_id", "classification": "BLOCKING"},
    {"field": "space.outline", "classification": "BLOCKING"},
    {"field": "space.ceiling_height", "classification": "BLOCKING"},
    {"field": "openings.presence", "classification": "BLOCKING"},
    {"field": "meta.project_name", "classification": "NON_BLOCKING"},
]

ANSWERS = {
    "meta.project_id": "PRJ-01",
    "meta.project_name": "Interface Test",
    "space.outline": [[0, 0], [6000, 0], [6000, 4000], [0, 4000]],
    "space.ceiling_height": 2800,
    "openings.presence": "NOT_PRESENT",
}


def fact(value, unit="mm"):
    return {"value": value, "unit": unit, "status": "C",
            "source_type": "CLIENT_INPUT", "source_ref": REF,
            "recorded_on": WHEN}


def walled_master():
    master, _rec = API.run_phase01(dict(ANSWERS), SPECS, WHEN)
    corners = [[0, 0], [6000, 0], [6000, 4000], [0, 4000]]
    walls = []
    for i in range(4):
        walls.append({
            "id": "W-%02d" % (i + 1),
            "start": fact(corners[i]),
            "end": fact(corners[(i + 1) % 4]),
            "thickness": fact(200),
            "structural": fact(False, unit="none"),
        })
    master["walls"] = walls
    master["meta"]["is_test_project"] = True
    master, _ = WS.ensure_test_banner(master)
    return WS.strip_private(master)


# ==========================================================================
# 1. WORKSPACE
# ==========================================================================
try:
    WS.check_project_id("PRJ-01")
    _ws01 = True
except ValueError:
    _ws01 = False
record("IF-WS-01", "PRJ-01 accepted as a project id", "accepted",
       str(_ws01), _ws01)

_ws02 = False
try:
    WS.check_project_id("PRJ-DEMO")
except ValueError:
    _ws02 = True
record("IF-WS-02", "PRJ-DEMO rejected (schema pattern)", "rejected",
       str(_ws02), _ws02)

_tmp = tempfile.mkdtemp(prefix="ida_ws_")
_paths = WS.init_project(os.path.join(_tmp, "PRJ-01"), "PRJ-01",
                         project_name="T", is_test=True)
_ws03 = all(os.path.isdir(_paths[k])
            for k in ("views_A", "views_B", "views_C", "reports")) \
    and os.path.exists(_paths["intake"]) \
    and os.path.exists(_paths["field_specs"])
record("IF-WS-03", "init creates views A/B/C + intake + specs", "created",
       str(_ws03), _ws03)

_ws04 = False
try:
    WS.init_project(os.path.join(_tmp, "PRJ-01"), "PRJ-01")
except FileExistsError:
    _ws04 = True
record("IF-WS-04", "init refuses to overwrite a workspace", "refused",
       str(_ws04), _ws04)

_fn = WS.output_filename("PRJ-01", "R01", "A", "FloorPlan", "svg")
record("IF-WS-05", "output filename follows PRJ_REV_CLASS_View.ext",
       "PRJ-01_R01_A_FloorPlan.svg", _fn, _fn == "PRJ-01_R01_A_FloorPlan.svg")

_m, _b = WS.ensure_test_banner({"meta": {"is_test_project": True}})
record("IF-WS-06", "test banner is the fixed literal",
       WS.TEST_BANNER, str(_m["meta"].get("test_banner")),
       _b is True and _m["meta"]["test_banner"] == WS.TEST_BANNER)

_m2, _b2 = WS.ensure_test_banner({"meta": {"is_test_project": False}})
record("IF-WS-07", "real projects are untouched by the banner", "untouched",
       str(_b2), _b2 is False and "test_banner" not in _m2["meta"])

_specs = WS.default_field_specs()
_blocking = sorted(s["field"] for s in _specs
                   if s.get("classification") == "BLOCKING")
record("IF-WS-08", "default specs block on outline/ceiling/openings",
       "3 blocking incl. outline", str(_blocking),
       "space.outline" in _blocking
       and "space.ceiling_height" in _blocking
       and "openings.presence" in _blocking)


# ==========================================================================
# 2. INTAKE + PIPELINE THROUGH THE API
# ==========================================================================
_g1 = API.run_intake(dict(ANSWERS), SPECS)
record("IF-P1-01", "complete intake proceeds", "PROCEED",
       str(_g1["verdict"]), _g1["verdict"] == "PROCEED")

_bad = dict(ANSWERS)
del _bad["space.outline"]
_g1b = API.run_intake(_bad, SPECS)
record("IF-P1-02", "missing BLOCKING field abstains", "ABSTAIN",
       str(_g1b["verdict"]), _g1b["verdict"] == "ABSTAIN")

_master, _rec = API.run_phase01(dict(ANSWERS), SPECS, WHEN)
record("IF-P1-03", "pipeline returns a master + lifecycle trace",
       "trace from NOT_STARTED", str(_rec.get("lifecycle_trace")),
       _master is not None
       and (_rec.get("lifecycle_trace") or [None])[0] == "NOT_STARTED")

record("IF-P1-04", "pipeline writes nothing to disk",
       "master_written_to_disk False",
       str(_rec.get("master_written_to_disk")),
       _rec.get("master_written_to_disk") is False)


# ==========================================================================
# 3. VALIDATION — including the schema-truthfulness completion
# ==========================================================================
DEMO = walled_master()

_rep = API.validate_all(DEMO)
record("IF-V-01", "clean TEST master validates PASS",
       "PASS 0 errors", str(_rep["summary"]),
       _rep["summary"]["result"] == "PASS"
       and _rep["summary"]["total_errors"] == 0
       and _rep["schema_gate_direct"]["ok"] is True)

_broken = copy.deepcopy(DEMO)
_broken["walls"][0]["thickness"]["value"] = -200
_rep2 = API.validate_all(_broken)
record("IF-V-02", "schema-invalid master FAILs (no false PASS)",
       "FAIL >=1 schema errors", str(_rep2["summary"]),
       _rep2["summary"]["result"] == "FAIL"
       and _rep2["summary"]["schema_errors"] >= 1)

_gate_bad = API.gate_plan(_broken, output_id="PLAN-99",
                          validation_report=_rep2)
record("IF-V-03", "C1 abstains when validation carries ERRORs",
       "allowed False", str(_gate_bad.get("allowed")),
       _gate_bad.get("allowed") is False)

_rdy = API.readiness(DEMO)
record("IF-R-01", "readiness reports blockers honestly",
       "ready False + blockers", "ready=" + str(_rdy.get(
           "ready_for_final_approval")),
       _rdy.get("ready_for_final_approval") is False
       and len((_rdy.get("final_approval_gate") or {}).get("blockers", [])) > 0)

_st = API.project_status(DEMO)
record("IF-S-01", "status counts elements and registers",
       "4 walls 12 unknowns", "walls=" + str(_st["counts"]["walls"])
       + " unknowns=" + str(_st["registers"]["unknowns_total"]),
       _st["counts"]["walls"] == 4
       and _st["registers"]["unknowns_total"] == 12)


# ==========================================================================
# 4. GENERATION END TO END
# ==========================================================================
_gate = API.gate_plan(DEMO)
record("IF-G-01", "C1 allows the plan on a clean master", "allowed True",
       str(_gate.get("allowed")), _gate.get("allowed") is True)

_bundle = API.generate_plan(DEMO, output_id="PLAN-01")
_svg_ok = (_bundle.get("svg") or "").startswith("<?xml") \
    and (_bundle.get("svg") or "").rstrip().endswith("</svg>")
record("IF-G-02", "plan emits well-formed SVG + VERIFIED fidelity",
       "svg + VERIFIED", str(_bundle.get("fidelity", {}).get("verdict")),
       _svg_ok and _bundle.get("fidelity", {}).get("verdict") == "VERIFIED")

_bare, _ = API.run_phase01(dict(ANSWERS), SPECS, WHEN)
_g03 = False
try:
    API.generate_plan(WS.strip_private(_bare))
except API.Abstained:
    _g03 = True
record("IF-G-03", "plan abstains when no wall is eligible", "Abstained",
       str(_g03), _g03)

_sched = API.build_quantities(DEMO)
_q02 = {i["element_id"]: i["value"] for i in _sched.get("items", [])
        if i.get("quantity_id") == "Q-02"}
_q03 = [i["value"] for i in _sched.get("items", [])
        if i.get("quantity_id") == "Q-03"]
record("IF-G-04", "Q-02/Q-03 lengths from declared endpoints",
       "6000/4000 + total 20000",
       str(_q02) + " total=" + str(_q03),
       _q02.get("W-01") == 6000.0 and _q02.get("W-02") == 4000.0
       and _q03 == [20000.0])

_b = API.present_class_b(_bundle["assembly"],
                         parameters={"color": "#111111",
                                     "wallpaper": "silk"},
                         identity=_bundle["identity"])
record("IF-G-05", "Class B emits; out-of-contract param rejected",
       "EMITTED + 1 rejected",
       str(_b.get("status")) + " rej=" + str(len(
           _b.get("parameters_rejected", []))),
       _b.get("status") == "EMITTED"
       and len(_b.get("parameters_rejected", [])) == 1
       and (_b.get("svg") or "").rstrip().endswith("</svg>"))

_pair = API.assess_pair(_bundle["assembly"], _bundle["svg"], _b["svg"])
record("IF-G-06", "D verifies A and B each against GA",
       "VERIFIED + VERIFIED",
       str(_pair["A"].get("verdict")) + " + " + str(
           _pair["B"].get("verdict")),
       _pair["A"].get("verdict") == "VERIFIED"
       and _pair["B"].get("verdict") == "VERIFIED")

_mani = API.assemble_manifest([("C3", _bundle), ("C5", _b),
                               ("C4", _sched)],
                              identity=_bundle["identity"])
record("IF-G-07", "manifest assembles 3 members, issues no verdict",
       "3 members, is_verdict False",
       str(len(_mani.get("members", []))) + " " + str(
           _mani.get("is_verdict")),
       len(_mani.get("members", [])) == 3
       and _mani.get("is_verdict") is False)

_o1 = API.existing_state(DEMO)
record("IF-G-08", "O-1 analyses as ANALYTICAL_EVIDENCE (not Class A)",
       "ANALYSED", str(_o1.get("status")) + " " + str(
           _o1.get("output_class")),
       _o1.get("status") == "ANALYSED"
       and _o1.get("output_class") == "ANALYTICAL_EVIDENCE"
       and _o1.get("is_class_a") is False)


# ==========================================================================
# 5. GOVERNANCE
# ==========================================================================
_gov = copy.deepcopy(DEMO)
_gov, _prop = API.record_proposal(
    _gov, "Adopt porcelain large-format matte floor")
record("IF-E-01", "proposal registered OPEN (never a decision)",
       "P-001 OPEN", str(_prop.get("id")) + " " + str(_prop.get("state")),
       _prop.get("id") == "P-001" and _prop.get("state") == "OPEN"
       and set(_prop) == {"id", "text", "state", "raised_on"})

_e02 = False
try:
    API.record_decision(copy.deepcopy(_gov), "Bad decision", "P-001",
                        rationale="", approved_on=WHEN,
                        approved_in_revision="R01")
except API.GovernanceError:
    _e02 = True
record("IF-E-02", "decision without rationale is refused", "refused",
       str(_e02), _e02)

_e03 = False
try:
    API.record_decision(copy.deepcopy(_gov), "Bad actor", "P-001",
                        rationale="a long enough reason here",
                        approved_on=WHEN, approved_in_revision="R01",
                        actor="AGENT")
except API.GovernanceError:
    _e03 = True
record("IF-E-03", "non-USER approval is refused", "refused",
       str(_e03), _e03)

_gov, _dec = API.record_decision(
    _gov, "Approve porcelain floor", "P-001",
    rationale="dense traffic plus fewer visual joints in a tight space",
    alternatives_considered=["engineered parquet (refused: moisture)"],
    approved_on=WHEN, approved_in_revision="R01")
_prop_after = [p for p in _gov["registers"]["proposals"]
               if p.get("id") == "P-001"][0]
record("IF-E-04", "USER decision links proposal both ways",
       "DEC-001 + proposal APPROVED",
       str(_dec.get("decision_id")) + " " + str(_prop_after.get("state")),
       _dec.get("decision_id") == "DEC-001"
       and _dec.get("approved_by") == "USER"
       and _prop_after.get("state") == "APPROVED"
       and _prop_after.get("decision_id") == "DEC-001")

_e04b = False
try:
    API.record_decision(copy.deepcopy(_gov), "Second bite", "P-001",
                        rationale="another long enough reason here",
                        approved_on=WHEN, approved_in_revision="R01")
except API.GovernanceError:
    _e04b = True
record("IF-E-05", "second decision on a settled proposal refused",
       "refused", str(_e04b), _e04b)

_gov, _cr = API.record_change_request(
    _gov, "space/ceiling_height", 2800, 2900,
    reason="client asked for a higher ceiling",
    impact="re-check door heights and lighting drops",
    classification="MINOR")
_e05 = False
try:
    API.apply_approved_change(copy.deepcopy(_gov), _cr["id"],
                              "space/ceiling_height", fact(2900))
except API.GovernanceError:
    _e05 = True
record("IF-E-06", "unapproved CR changes nothing (No Auto-Apply)",
       "refused", str(_e05), _e05)

_gov, _ = API.approve_change_request(_gov, _cr["id"], actor="USER",
                                     approved_on=WHEN)
_gov, _applied = API.apply_approved_change(_gov, _cr["id"],
                                            "space/ceiling_height",
                                            fact(2900))
_last_log = _gov["registers"]["changelog"][-1]
record("IF-E-07", "APPROVED CR applies + logs cr_id",
       "value 2900 + CR_APPLIED",
       str(_gov["space"]["ceiling_height"].get("value")),
       _gov["space"]["ceiling_height"].get("value") == 2900
       and _gov["registers"]["change_requests"][0]["state"] == "APPLIED"
       and _last_log["type"] == "CR_APPLIED"
       and _last_log.get("cr_id") == _cr["id"])

_gov2 = copy.deepcopy(DEMO)
_gov2, _cr2 = API.record_change_request(
    _gov2, "space/ceiling_height", 2800, 2900,
    reason="client asked for a higher ceiling",
    impact="re-check door heights", classification="MINOR")
_gov2, _ = API.approve_change_request(_gov2, _cr2["id"], actor="USER",
                                      approved_on=WHEN)
_e07 = False
try:
    _bad_fact = fact(2900)
    _bad_fact["source_type"] = "AGENT_PROPOSAL"
    API.apply_approved_change(_gov2, _cr2["id"], "space/ceiling_height",
                              _bad_fact)
except API.GovernanceError:
    _e07 = True
record("IF-E-08", "[C] from AGENT_PROPOSAL is refused on apply", "refused",
       str(_e07), _e07)

_gov, _obj = API.record_objection(
    _gov, "PENDING-LAYOUT",
    problem="entry corridor pinches below a comfortable clear width",
    impact="circulation comfort at peak use",
    alternative="shift the zone boundary 300mm east")
record("IF-E-09", "objection raised OPEN with full record", "OBJ-001 OPEN",
       str(_obj.get("id")) + " " + str(_obj.get("state")),
       _obj.get("id") == "OBJ-001" and _obj.get("state") == "OPEN")

_rep_gov = API.validate_all(_gov)
record("IF-E-10", "governed master still validates clean",
       "PASS", str(_rep_gov["summary"]),
       _rep_gov["summary"]["result"] == "PASS")

_gov3 = copy.deepcopy(_gov)
_gov3, _ = API.record_objection(
    _gov3, "DEC-001",
    problem="floor choice ignores the acoustic brief entirely",
    impact="brief compliance for the studio", alternative="acoustic vinyl")
_rep_rl = API.validate_all(_gov3)
_rl003 = [r for r in _rep_rl["rules"].get("finding_references", [])
          if r.get("rule") == "RL-003" and r.get("severity") == "ERROR"]
record("IF-E-11", "OPEN objection vs standing decision raises RL-003",
       "RL-003 ERROR", "count=" + str(len(_rl003)), len(_rl003) == 1)

_gov4 = copy.deepcopy(DEMO)
_gov4, _cr4 = API.record_change_request(
    _gov4, "space/ceiling_height", 2800, 2900,
    reason="approval-sourced change",
    impact="re-check door heights", classification="MINOR")
_gov4, _ = API.approve_change_request(_gov4, _cr4["id"], actor="USER",
                                      approved_on=WHEN)
_e12 = False
try:
    _appr_fact = fact(2900)
    _appr_fact["source_type"] = "USER_APPROVAL"
    API.apply_approved_change(_gov4, _cr4["id"], "space/ceiling_height",
                              _appr_fact)
except API.GovernanceError:
    _e12 = True
record("IF-E-12", "[C]/USER_APPROVAL without Decision Record refused",
       "refused", str(_e12), _e12)



# ==========================================================================
# 6. CAPTIONS
# ==========================================================================
_cap_a = API.caption_for("A", "FloorPlan", "R01")
record("IF-L-01", "Class A caption carries no lint problems", "no problems",
       str(_cap_a["problems"]), _cap_a["problems"] == [])

_cap_c = API.caption_for("C", "Mood01", "R01", extra="identical 100% match")
record("IF-L-02", "Class C rejects match/100% language", "linted",
       str(len(_cap_c["problems"])), len(_cap_c["problems"]) > 0)


# ==========================================================================
# 7. CLI
# ==========================================================================
IDA = os.path.join(ROOT, "ida.py")
_cli_dir = tempfile.mkdtemp(prefix="ida_cli_")
_cli_master = os.path.join(_cli_dir, "master.json")
with open(_cli_master, "w", encoding="utf-8") as _h:
    json.dump(DEMO, _h)


def run_cli(argv):
    return subprocess.run([sys.executable, IDA] + argv,
                          capture_output=True, text=True)


_p = run_cli(["--help"])
record("IF-CLI-01", "CLI answers --help with exit 0", "exit 0",
       "exit " + str(_p.returncode), _p.returncode == 0)

_p = run_cli(["status", "--master", _cli_master, "--json"])
_cli02 = False
try:
    _payload = json.loads(_p.stdout)
    _cli02 = _payload.get("report_kind") == "PROJECT_STATUS"
except ValueError:
    _cli02 = False
record("IF-CLI-02", "status --json emits a parseable report",
       "PROJECT_STATUS", "exit " + str(_p.returncode),
       _p.returncode == 0 and _cli02)

_broken_path = os.path.join(_cli_dir, "broken.json")
with open(_broken_path, "w", encoding="utf-8") as _h:
    json.dump(_broken, _h)
_p = run_cli(["validate", "--master", _broken_path])
record("IF-CLI-03", "validate exits 1 on a schema-invalid master",
       "exit 1", "exit " + str(_p.returncode), _p.returncode == 1)

_bad_intake = os.path.join(_cli_dir, "intake.json")
_specs_path = os.path.join(_cli_dir, "specs.json")
with open(_bad_intake, "w", encoding="utf-8") as _h:
    json.dump({"meta.project_id": "PRJ-01"}, _h)
with open(_specs_path, "w", encoding="utf-8") as _h:
    json.dump(SPECS, _h)
_p = run_cli(["intake", "--intake", _bad_intake, "--specs", _specs_path])
record("IF-CLI-04", "intake abstention exits 3 (domain refusal)",
       "exit 3", "exit " + str(_p.returncode), _p.returncode == 3)

_p = run_cli(["plan", "--master", _broken_path,
              "--svg-out", os.path.join(_cli_dir, "x.svg")])
record("IF-CLI-05", "plan abstains (exit 3) on an invalid master",
       "exit 3", "exit " + str(_p.returncode), _p.returncode == 3)

_p = run_cli(["init", "PRJ-XX", "--dir", os.path.join(_cli_dir, "ws")])
record("IF-CLI-06", "init rejects an id outside the schema pattern",
       "exit 1", "exit " + str(_p.returncode), _p.returncode == 1)


# --------------------------------------------------------------------------
print("=" * 94)
print("AGENT INTERFACES — ida_api / ida CLI / workspace SMOKE REPORT")
print("=" * 94)
passed = sum(1 for r in RESULTS if r[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    mark = "OK  " if verdict == "PASS" else "FAIL"
    print(mark + " " + tid.ljust(10) + " " + scenario[:56].ljust(56)
          + " " + actual[:30])
print("-" * 94)
print("TOTAL: " + str(passed) + "/" + str(total) + " passed")
print("=" * 94)
sys.exit(0 if passed == total else 1)
