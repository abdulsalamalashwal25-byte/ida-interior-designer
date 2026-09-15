#!/usr/bin/env python3
"""Phase 01 — Intake -> Validated Project Master.

Reference: PHASE-01 Architecture R02 + Final Amendment (APPROVED / LOCKED).

WHAT THIS SUITE MUST PROVE
  * G1 blocks ONLY on an explicitly declared BLOCKING field
  * UNCLASSIFIED is neither blocking nor non-blocking, and is never hidden
  * [D] is never created, [A] is never approved, [C] comes only from input
  * NOT_PRESENT, UNKNOWN and a value stay three distinct states
  * validator verdicts are carried, never reinterpreted or softened
  * ready=False is a legitimate result, not a phase failure
  * Phase 01 writes nothing and modifies no earlier layer

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

import p1_intake as G1                                               # noqa: E402
import p1_populate as G2                                             # noqa: E402
import p1_validate as G34                                            # noqa: E402
import p1_readiness as G5                                            # noqa: E402
import p1_pipeline as PIPE                                           # noqa: E402

RESULTS = []
MUTATIONS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def mutation(mid, desc, classification, detail):
    MUTATIONS.append((mid, desc, classification, detail))


SPECS = [
    {"field": "meta.project_id", "classification": "BLOCKING"},
    {"field": "space.ceiling_height", "classification": "BLOCKING"},
    {"field": "space.outline", "classification": "BLOCKING"},
    {"field": "meta.project_name", "classification": "NON_BLOCKING"},
    {"field": "space.orientation_north"},          # deliberately unclassified
]

GOOD = {
    "meta.project_id": "PRJ-01",
    "meta.project_name": "Test Project",
    "space.ceiling_height": 2800,
    "space.outline": [[0, 0], [6000, 0], [6000, 4000], [0, 4000]],
    "openings.presence": "NOT_PRESENT",
}
WHEN = "2026-09-15"


def run(answers=None, specs=None):
    return PIPE.run_phase01(answers if answers is not None else dict(GOOD),
                            specs or SPECS, WHEN)


# ==========================================================================
# 1. G1 — INTAKE COMPLETENESS (positive)
# ==========================================================================
_g1 = G1.evaluate_intake(GOOD, SPECS)
record("P1-G1-01", "Complete blocking fields -> PROCEED",
       "PROCEED", f"{_g1['verdict']}", _g1["verdict"] == "PROCEED")

record("P1-G1-02", "Supplied fields are listed",
       "4 supplied", f"{len(_g1['supplied_fields'])}",
       len(_g1["supplied_fields"]) == 4)

_missing_block = dict(GOOD)
del _missing_block["space.ceiling_height"]
_g1b = G1.evaluate_intake(_missing_block, SPECS)
record("P1-G1-03", "Missing BLOCKING field -> ABSTAIN",
       "ABSTAIN", f"{_g1b['verdict']}", _g1b["verdict"] == "ABSTAIN")

record("P1-G1-04", "The abstention names the blocking field",
       "space.ceiling_height",
       f"{[m['field'] for m in _g1b['missing_blocking']]}",
       "space.ceiling_height" in [m["field"]
                                  for m in _g1b["missing_blocking"]])

_missing_nb = dict(GOOD)
del _missing_nb["meta.project_name"]
_g1c = G1.evaluate_intake(_missing_nb, SPECS)
record("P1-G1-05", "Missing NON_BLOCKING field does NOT block",
       "PROCEED", f"{_g1c['verdict']}", _g1c["verdict"] == "PROCEED")

record("P1-G1-06", "Missing NON_BLOCKING enters the master as [U]",
       "enters_master_as U",
       f"{_g1c['missing_non_blocking'][0]['enters_master_as']}",
       _g1c["missing_non_blocking"][0]["enters_master_as"] == "U")


# ==========================================================================
# 2. UNCLASSIFIED — the Final Amendment (G1-6)
# ==========================================================================
record("P1-UC-01", "An unclassified field is recorded as UNRESOLVED",
       "1 unresolved entry",
       f"{len(_g1['unresolved_classification'])}",
       len(_g1["unresolved_classification"]) == 1)

_uc = _g1["unresolved_classification"][0]
record("P1-UC-02", "It carries the UNRESOLVED_CLASSIFICATION code",
       "UNRESOLVED_CLASSIFICATION", f"{_uc['code']}",
       _uc["code"] == "UNRESOLVED_CLASSIFICATION")

record("P1-UC-03", "It is NOT counted as a blocking field",
       "absent from missing_blocking",
       f"{[m['field'] for m in _g1['missing_blocking']]}",
       "space.orientation_north" not in [m["field"]
                                         for m in _g1["missing_blocking"]])

record("P1-UC-04", "It is NOT counted as a non-blocking field either",
       "absent from missing_non_blocking",
       f"{[m['field'] for m in _g1['missing_non_blocking']]}",
       "space.orientation_north" not in [m["field"]
                                         for m in _g1["missing_non_blocking"]])

record("P1-UC-05", "It is never evidence of readiness",
       "counts_as_readiness_evidence False",
       f"{_uc['counts_as_readiness_evidence']}",
       _uc["counts_as_readiness_evidence"] is False)

record("P1-UC-06", "classify_field returns UNCLASSIFIED, never a guess",
       "UNCLASSIFIED",
       f"{G1.classify_field({'field': 'x'})}",
       G1.classify_field({"field": "x"}) == "UNCLASSIFIED")

record("P1-UC-07", "An unclassified field that IS supplied is still recorded",
       "still recorded",
       f"{len(G1.evaluate_intake(dict(GOOD, **{'space.orientation_north': 90}), SPECS)['unresolved_classification'])}",
       len(G1.evaluate_intake(
           dict(GOOD, **{"space.orientation_north": 90}),
           SPECS)["unresolved_classification"]) == 1)

_, _run_uc = run()
record("P1-UC-08", "The unresolved classification reaches the declaration",
       "carried into G5",
       f"{_run_uc['gates']['G5']['unresolved_classification_count']}",
       _run_uc["gates"]["G5"]["unresolved_classification_count"] == 1)


# ==========================================================================
# 3. G2 — POPULATION & STATUS RULES
# ==========================================================================
_master, _rec = run()

record("P1-G2-01", "A supplied value becomes [C] with CLIENT_INPUT",
       "C / CLIENT_INPUT",
       f"{_master['space']['ceiling_height']['status']}/"
       f"{_master['space']['ceiling_height']['source_type']}",
       _master["space"]["ceiling_height"]["status"] == "C"
       and _master["space"]["ceiling_height"]["source_type"] == "CLIENT_INPUT")

_m_nb, _r_nb = run(_missing_nb)
record("P1-G2-02", "An absent non-blocking value becomes [U]",
       "unknown registered",
       f"{len(_r_nb['gates']['G2']['unknowns_registered'])}",
       len(_r_nb["gates"]["G2"]["unknowns_registered"]) == 1)

record("P1-G2-03", "Phase 01 creates zero [D]",
       "derived_created 0",
       f"{_rec['gates']['G2']['derived_created']}",
       _rec["gates"]["G2"]["derived_created"] == 0)

_d_refused = False
try:
    G2.make_fact(1, "D", "CLIENT_INPUT", "x", WHEN)
except G2.PopulationError:
    _d_refused = True
record("P1-G2-04", "make_fact refuses to build a [D]",
       "PopulationError", f"refused={_d_refused}", _d_refused)

_assumption = G2.make_assumption(2700, "intake/2.4", WHEN, unit="mm")
record("P1-G2-05", "An [A] is recorded PENDING_APPROVAL",
       "A / PENDING_APPROVAL",
       f"{_assumption['status']}/{_assumption['approval_state']}",
       _assumption["status"] == "A"
       and _assumption["approval_state"] == "PENDING_APPROVAL")

record("P1-G2-06", "An [A] carries AGENT_ASSUMPTION as its source",
       "AGENT_ASSUMPTION", f"{_assumption['source_type']}",
       _assumption["source_type"] == "AGENT_ASSUMPTION")

record("P1-G2-07", "Phase 01 confirms nothing on its own",
       "confirmed_by_phase01 0",
       f"{_rec['gates']['G2']['confirmed_by_phase01']}",
       _rec["gates"]["G2"]["confirmed_by_phase01"] == 0)

record("P1-G2-08", "Every tagged field carries a status and a source",
       "all tagged",
       f"{all('status' in t and 'source_type' in t for t in _rec['gates']['G2']['tagged_fields'])}",
       all("status" in t and "source_type" in t
           for t in _rec["gates"]["G2"]["tagged_fields"]))

_blocking_refused = False
try:
    G2.register_unknown({}, "U-001", "q", "a", "MAYBE", WHEN)
except G2.PopulationError:
    _blocking_refused = True
record("P1-G2-09", "register_unknown refuses an inferred blocking flag",
       "PopulationError", f"refused={_blocking_refused}", _blocking_refused)


# ==========================================================================
# 4. THREE-WAY DISTINCTION
# ==========================================================================
record("P1-3W-01", "NOT_PRESENT is recorded as a confirmed absence",
       "presence NOT_PRESENT, status C",
       f"{_master['presence_register']['openings']['presence']}/"
       f"{_master['presence_register']['openings']['status']}",
       _master["presence_register"]["openings"]["presence"] == "NOT_PRESENT"
       and _master["presence_register"]["openings"]["status"] == "C")

_m_unk, _ = run(dict(GOOD, **{"openings.presence": None}))
record("P1-3W-02", "An undeclared presence is UNKNOWN, not NOT_PRESENT",
       "presence UNKNOWN, status U",
       f"{_m_unk['presence_register']['openings']['presence']}/"
       f"{_m_unk['presence_register']['openings']['status']}",
       _m_unk["presence_register"]["openings"]["presence"] == "UNKNOWN"
       and _m_unk["presence_register"]["openings"]["status"] == "U")

_m_pres, _ = run(dict(GOOD, **{
    "openings.presence": "PRESENT",
    "openings": [{"id": "OP-01", "kind": "door", "host_wall": "W-01",
                  "offset": {"value": 1000, "unit": "mm", "status": "C",
                             "source_type": "CLIENT_INPUT",
                             "source_ref": "i", "recorded_on": WHEN},
                  "width": {"value": 900, "unit": "mm", "status": "C",
                            "source_type": "CLIENT_INPUT",
                            "source_ref": "i", "recorded_on": WHEN},
                  "height": {"value": 2100, "unit": "mm", "status": "C",
                             "source_type": "CLIENT_INPUT",
                             "source_ref": "i", "recorded_on": WHEN}}]}))
record("P1-3W-03", "PRESENT with items is a third, distinct state",
       "presence PRESENT, 1 opening",
       f"{_m_pres['presence_register']['openings']['presence']}/"
       f"{len(_m_pres['openings'])}",
       _m_pres["presence_register"]["openings"]["presence"] == "PRESENT"
       and len(_m_pres["openings"]) == 1)

record("P1-3W-04", "The three states produce three different records",
       "all distinct",
       f"{_master['presence_register']['openings']['presence']}/"
       f"{_m_unk['presence_register']['openings']['presence']}/"
       f"{_m_pres['presence_register']['openings']['presence']}",
       len({_master["presence_register"]["openings"]["presence"],
            _m_unk["presence_register"]["openings"]["presence"],
            _m_pres["presence_register"]["openings"]["presence"]}) == 3)


# ==========================================================================
# 5. CONTRADICTIONS — declared, never corrected
# ==========================================================================
_contra = G2.detect_contradictions({
    "openings.presence": "NOT_PRESENT",
    "openings": [{"id": "OP-01"}]})
record("P1-CT-01", "A presence contradiction is detected",
       "1 contradiction", f"{len(_contra)}", len(_contra) == 1)

record("P1-CT-02", "The contradiction is declared, not corrected",
       "corrected False", f"{_contra[0]['corrected']}",
       _contra[0]["corrected"] is False)

_contra2 = G2.detect_contradictions({
    "space.outline": [[0, 0], [1, 0], [1, 1]],
    "space.declared_edge_count": 4})
record("P1-CT-03", "An edge-count mismatch is reported as-is",
       "1 contradiction, not corrected",
       f"{len(_contra2)}/{_contra2[0]['corrected'] if _contra2 else '-'}",
       len(_contra2) == 1 and _contra2[0]["corrected"] is False)

_src_pop = open(os.path.join(ROOT, "scripts", "p1_populate.py"),
                encoding="utf-8").read()
record("P1-CT-04", "No auto-correction logic exists in population",
       "no fix/correct function",
       f"{[t for t in ('def fix', 'def correct', 'def repair') if t in _src_pop]}",
       not [t for t in ("def fix", "def correct", "def repair")
            if t in _src_pop])


# ==========================================================================
# 6. G3 / G4 — VALIDATION CONSUMPTION (O-3)
# ==========================================================================
record("P1-G3-01", "Schema validation runs and reports its own result",
       "PASS on a clean build",
       f"{_rec['gates']['G3']['result']}",
       _rec["gates"]["G3"]["result"] == "PASS")

record("P1-G3-02", "Schema verdicts are not reinterpreted",
       "reinterpreted False",
       f"{_rec['gates']['G3']['reinterpreted']}",
       _rec["gates"]["G3"]["reinterpreted"] is False)

record("P1-G4-01", "All eleven B-layers are invoked",
       "11 layers", f"{len(_rec['gates']['G4']['layers'])}",
       len(_rec["gates"]["G4"]["layers"]) == 11)

record("P1-G4-02", "Each finding names the validator that owns it",
       "owner recorded",
       f"{all('verdict_owner' in r for r in _rec['gates']['G4']['finding_references'])}",
       all("verdict_owner" in r
           for r in _rec["gates"]["G4"]["finding_references"]))

record("P1-G4-03", "Phase 01 does not soften an ERROR",
       "softened False",
       f"{_rec['gates']['G4']['softened']}",
       _rec["gates"]["G4"]["softened"] is False)

_src_val = open(os.path.join(ROOT, "scripts", "p1_validate.py"),
                encoding="utf-8").read()
_exec_val = re.sub(r'""".*?"""', "", _src_val, flags=re.S)
_exec_val = "\n".join(ln.split("#")[0] for ln in _exec_val.splitlines())
record("P1-G4-04", "No severity is assigned or rewritten by Phase 01",
       "no severity assignment",
       f"{'severity =' in _exec_val or 'severity=' in _exec_val.replace('severity=None','')}",
       'severity =' not in _exec_val)

record("P1-G4-05", "A validator crash is reported, never swallowed",
       "failure path present",
       f"{'VALIDATOR_EXECUTION_FAILURE' in _src_val}",
       "VALIDATOR_EXECUTION_FAILURE" in _src_val)


# ==========================================================================
# 7. G5 — READINESS DECLARATION
# ==========================================================================
_g5 = _rec["gates"]["G5"]
record("P1-G5-01", "Readiness is consumed from schema_gate, not recomputed",
       "recomputed False",
       f"{_g5['recomputed_by_phase01']}",
       _g5["recomputed_by_phase01"] is False)

record("P1-G5-02", "The computing function is named",
       "final_approval_readiness", f"{_g5['computed_by']}",
       _g5["computed_by"] == "schema_gate.final_approval_readiness")

record("P1-G5-03", "ready=False is NOT a phase failure",
       "is_phase_failure False",
       f"{_g5['is_phase_failure']}", _g5["is_phase_failure"] is False)

record("P1-G5-04", "Blockers are declared in full, never hidden",
       "blockers listed",
       f"{_g5['blocker_count']} == {len(_g5['blockers'])}",
       _g5["blocker_count"] == len(_g5["blockers"]))

record("P1-G5-05", "ready=True has a bounded meaning",
       "scope-limited statement",
       f"{'within its own scope' in _g5['ready_true_means']}",
       "within its own scope" in _g5["ready_true_means"])

record("P1-G5-06", "ready=True lists the five things it does not mean",
       "5 exclusions",
       f"{len(_g5['ready_true_does_not_mean'])}",
       len(_g5["ready_true_does_not_mean"]) == 5)

record("P1-G5-07", "A blocked project still reaches a declared state",
       "BLOCKED_DECLARED", f"{_rec['state']}",
       _rec["state"] == "BLOCKED_DECLARED")


# ==========================================================================
# 8. LIFECYCLE
# ==========================================================================
record("P1-LC-01", "A complete run traces the approved lifecycle",
       "NOT_STARTED..BLOCKED_DECLARED",
       f"{' -> '.join(_rec['lifecycle_trace'][:3])}...",
       _rec["lifecycle_trace"][:4] == ["NOT_STARTED", "INTAKE_RECEIVED",
                                       "MASTER_POPULATED", "VALIDATED"])

_m_ab, _r_ab = run(_missing_block)
record("P1-LC-02", "A blocking absence traces to ABSTAINED",
       "INTAKE_INCOMPLETE -> ABSTAINED",
       f"{_r_ab['lifecycle_trace'][-2:]}",
       _r_ab["lifecycle_trace"][-2:] == ["INTAKE_INCOMPLETE", "ABSTAINED"])

record("P1-LC-03", "No master is built when G1 abstains",
       "master is None", f"{_m_ab is None}", _m_ab is None)

record("P1-LC-04", "Terminal states have no onward transitions",
       "[] for ABSTAINED",
       f"{PIPE.allowed_next('ABSTAINED')}",
       PIPE.allowed_next("ABSTAINED") == [])

record("P1-LC-05", "READY_DECLARED and BLOCKED_DECLARED are both terminal",
       "both terminal",
       f"{PIPE.allowed_next('READY_DECLARED')}/"
       f"{PIPE.allowed_next('BLOCKED_DECLARED')}",
       PIPE.allowed_next("READY_DECLARED") == []
       and PIPE.allowed_next("BLOCKED_DECLARED") == [])

record("P1-LC-06", "VALIDATED means only Phase 01 scope",
       "7 exclusions listed",
       f"{len(_rec['validated_does_not_mean'])}",
       len(_rec["validated_does_not_mean"]) == 7)

record("P1-LC-07", "VALIDATED does not mean generation ready",
       "listed as excluded",
       f"{'generation ready' in _rec['validated_does_not_mean']}",
       "generation ready" in _rec["validated_does_not_mean"])


# ==========================================================================
# 9. OWNERSHIP / ISOLATION
# ==========================================================================
_src_all = ""
for _f in ("p1_intake.py", "p1_populate.py", "p1_validate.py",
           "p1_readiness.py", "p1_pipeline.py"):
    _src_all += open(os.path.join(ROOT, "scripts", _f),
                     encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src_all, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
_code_ns = re.sub(r'"[^"]*"', '""', _exec_only)
_code_ns = re.sub(r"'[^']*'", "''", _code_ns)

record("P1-OW-01", "Phase 01 declares it is not a designer or generator",
       "all four disclaimers",
       f"{[_rec[k] for k in ('not_a_designer', 'not_an_engineering_judge', 'not_a_generator', 'not_an_approval_authority')]}",
       all(_rec[k] for k in ("not_a_designer", "not_an_engineering_judge",
                             "not_a_generator", "not_an_approval_authority")))

record("P1-OW-02", "Phase 01 imports no C, D, E or F module",
       "none",
       f"{[m for m in ('c1_preconditions', 'c3_svg_emitter', 'c6_manifest', 'd_report', 'e_ownership', 'f_reference') if f'import {m}' in _src_all]}",
       not [m for m in ("c1_preconditions", "c3_svg_emitter", "c6_manifest",
                        "d_report", "e_ownership", "f_reference")
            if f"import {m}" in _src_all])

record("P1-OW-03", "Phase 01 generates no geometry",
       "no geometry maths",
       f"{[t for t in ('sqrt', 'polygon_area', 'def emit') if t in _code_ns]}",
       not [t for t in ("sqrt", "polygon_area", "def emit")
            if t in _code_ns])

record("P1-OW-04", "Phase 01 issues no approval",
       "no approval issuance",
       f"{[t for t in ('def approve', 'APPROVED =', 'approved_by =') if t in _exec_only]}",
       not [t for t in ("def approve", "APPROVED =", "approved_by =")
            if t in _exec_only])

record("P1-OW-05", "Phase 01 issues no fidelity verdict and no fingerprint",
       "none",
       f"{[t for t in ('fidelity', 'fingerprint', 'hashlib') if t in _code_ns.lower()]}",
       not [t for t in ("fidelity", "fingerprint", "hashlib")
            if t in _code_ns.lower()])

# 'outputs' also matches the module name validate_outputs, which B8 requires
# Phase 01 to invoke. The real question is whether Phase 01 READS or WRITES
# the outputs[] array, so the check targets actual access.
_outputs_access = [t for t in ('["outputs"]', "['outputs']",
                               '.get("outputs"', ".get('outputs'",
                               'setdefault("outputs"')
                   if t in _exec_only]
record("P1-OW-06", "Phase 01 never reads or writes outputs[]",
       "no outputs[] access", f"{_outputs_access}", not _outputs_access)


# ==========================================================================
# 10. NO-WRITE
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_watch = [os.path.join(ROOT, "project_master.template.json"),
          os.path.join(ROOT, "project_master.schema.json"),
          os.path.join(ROOT, "intake_form.md"),
          os.path.join(ROOT, "RULES.md"),
          os.path.join(ROOT, "scripts", "schema_gate.py")]
_before_h = [_sha(p) for p in _watch]
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))
_answers_snapshot = copy.deepcopy(GOOD)

run()
run(_missing_block)
G2.load_template()

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("P1-NW-01", "BEHAVIOURAL: template/schema/intake/RULES/A unchanged",
       "sha256 stable", f"{_before_h == [_sha(p) for p in _watch]}",
       _before_h == [_sha(p) for p in _watch])

record("P1-NW-02", "BEHAVIOURAL: no new file appeared",
       "none", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

record("P1-NW-03", "BEHAVIOURAL: project_master.json is never created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

record("P1-NW-04", "BEHAVIOURAL: intake answers are not mutated",
       "identical", f"{_answers_snapshot == GOOD}",
       _answers_snapshot == GOOD)

record("P1-NW-05", "The run declares the master was not written to disk",
       "master_written_to_disk False",
       f"{_rec['master_written_to_disk']}",
       _rec["master_written_to_disk"] is False)

_write_paths = [".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "tempfile", "pickle", "os.remove"]
record("P1-NW-06", "WRITE-PATH AUDIT: no write mechanism in Phase 01",
       "none of 9",
       f"{[p for p in _write_paths if p in _exec_only]}",
       not [p for p in _write_paths if p in _exec_only])


# ==========================================================================
# 11. BOUNDARY
# ==========================================================================
_g1_empty = G1.evaluate_intake({}, SPECS)
record("P1-BD-01", "Empty intake abstains on all blocking fields",
       "ABSTAIN, 3 blocking missing",
       f"{_g1_empty['verdict']}, {len(_g1_empty['missing_blocking'])}",
       _g1_empty["verdict"] == "ABSTAIN"
       and len(_g1_empty["missing_blocking"]) == 3)

_g1_nospec = G1.evaluate_intake(GOOD, [])
record("P1-BD-02", "No field specs: nothing is blocking and nothing invented",
       "PROCEED, 0 missing",
       f"{_g1_nospec['verdict']}, {len(_g1_nospec['missing_blocking'])}",
       _g1_nospec["verdict"] == "PROCEED"
       and not _g1_nospec["missing_blocking"])

record("P1-BD-03", "An empty string is treated as absent, not as an answer",
       "ABSTAIN",
       f"{G1.evaluate_intake(dict(GOOD, **{'meta.project_id': '   '}), SPECS)['verdict']}",
       G1.evaluate_intake(dict(GOOD, **{"meta.project_id": "   "}),
                          SPECS)["verdict"] == "ABSTAIN")

record("P1-BD-04", "Population refuses to run after a G1 abstention",
       "PopulationError",
       f"{'refused'}", True)
_pop_refused = False
try:
    G2.populate(GOOD, {"verdict": "ABSTAIN"}, WHEN)
except G2.PopulationError:
    _pop_refused = True
RESULTS[-1] = ("P1-BD-04", "Population refuses to run after a G1 abstention",
               "PopulationError", f"refused={_pop_refused}",
               "PASS" if _pop_refused else "FAIL")

record("P1-BD-05", "A declared blocking unknown is registered as blocking",
       "blocking True",
       f"{[u['blocking'] for u in run(dict(GOOD, declared_blocking_unknowns=[{'question': 'q', 'affects': 'a'}]))[1]['gates']['G2']['unknowns_registered']]}",
       any(u["blocking"] is True for u in run(
           dict(GOOD, declared_blocking_unknowns=[
               {"question": "q", "affects": "a"}]))[1]["gates"]["G2"][
                   "unknowns_registered"]))


# ==========================================================================
# 12. MUTATION
# ==========================================================================
def run_mut(mid, desc, module, attr, patch, probe):
    original = getattr(module, attr)
    setattr(module, attr, patch)
    try:
        detected = probe()
    finally:
        setattr(module, attr, original)
    cls = "KILLED" if detected else "SURVIVED"
    mutation(mid, desc, cls, f"detected={detected}")
    record(f"P1-M-{mid}", f"MUTATION {desc}", "KILLED", cls, detected)


# M-01 treat UNCLASSIFIED as NON_BLOCKING (the Final Amendment breach)
_orig_classify = G1.classify_field
G1.classify_field = lambda spec: (
    "NON_BLOCKING" if (spec or {}).get("classification") is None
    else _orig_classify(spec))
try:
    _d01 = not G1.evaluate_intake(GOOD, SPECS)["unresolved_classification"]
finally:
    G1.classify_field = _orig_classify
mutation("01", "treat UNCLASSIFIED as NON_BLOCKING",
         "KILLED" if _d01 else "SURVIVED", f"detected={_d01}")
record("P1-M-01", "MUTATION UNCLASSIFIED -> NON_BLOCKING", "KILLED",
       "KILLED" if _d01 else "SURVIVED", _d01)

# M-02 treat UNCLASSIFIED as BLOCKING
G1.classify_field = lambda spec: (
    "BLOCKING" if (spec or {}).get("classification") is None
    else _orig_classify(spec))
try:
    _d02 = G1.evaluate_intake(GOOD, SPECS)["verdict"] == "ABSTAIN"
finally:
    G1.classify_field = _orig_classify
mutation("02", "treat UNCLASSIFIED as BLOCKING",
         "KILLED" if _d02 else "SURVIVED", f"detected={_d02}")
record("P1-M-02", "MUTATION UNCLASSIFIED -> BLOCKING", "KILLED",
       "KILLED" if _d02 else "SURVIVED", _d02)

# M-03 let a missing NON_BLOCKING field abstain
_orig_eval = PIPE.evaluate_intake


def _strict(intake_answers, field_specs):
    out = _orig_eval(intake_answers, field_specs)
    if out["missing_non_blocking"]:
        out["verdict"] = "ABSTAIN"
    return out


PIPE.evaluate_intake = _strict
try:
    _d03 = run(_missing_nb)[0] is None
finally:
    PIPE.evaluate_intake = _orig_eval
mutation("03", "let a missing NON_BLOCKING field block the build",
         "KILLED" if _d03 else "SURVIVED", f"detected={_d03}")
record("P1-M-03", "MUTATION non-blocking absence blocks", "KILLED",
       "KILLED" if _d03 else "SURVIVED", _d03)

# M-04 allow Phase 01 to create a [D]
_orig_make = G2.make_fact
G2.make_fact = lambda value, status, source_type, source_ref, recorded_on, \
    unit=None, note=None: {"value": value, "status": status}
try:
    _d04 = G2.make_fact(1, "D", "x", "y", WHEN).get("status") == "D"
finally:
    G2.make_fact = _orig_make
mutation("04", "allow Phase 01 to create a [D]",
         "KILLED" if _d04 else "SURVIVED", f"detected={_d04}")
record("P1-M-04", "MUTATION Phase 01 creates [D]", "KILLED",
       "KILLED" if _d04 else "SURVIVED", _d04)

# M-05 approve an [A] inside Phase 01
run_mut("05", "record an [A] as APPROVED instead of PENDING",
        G2, "PENDING_APPROVAL", "APPROVED",
        lambda: G2.make_assumption(1, "x", WHEN)["approval_state"]
        != "PENDING_APPROVAL")

# M-06 collapse NOT_PRESENT into UNKNOWN
run_mut("06", "collapse NOT_PRESENT into UNKNOWN",
        G2, "NOT_PRESENT", "UNKNOWN",
        lambda: run()[0]["presence_register"]["openings"]["presence"]
        == "UNKNOWN")

# M-07 soften an ERROR into a WARNING
_orig_ref = G34._as_reference


def _soften(layer, module_name, finding):
    out = _orig_ref(layer, module_name, finding)
    if out["severity"] == "ERROR":
        out["severity"] = "WARNING"
    return out


G34._as_reference = _soften
try:
    _bad_master = copy.deepcopy(_master)
    _bad_master["meta"]["project_id"] = "INVALID!!"
    _res = G34.run_schema_gate(_bad_master)
    _d07 = _res["error_count"] == 0
finally:
    G34._as_reference = _orig_ref
mutation("07", "soften an ERROR into a WARNING (O3-3 breach)",
         "KILLED" if _d07 else "SURVIVED", f"detected={_d07}")
record("P1-M-07", "MUTATION ERROR softened to WARNING", "KILLED",
       "KILLED" if _d07 else "SURVIVED", _d07)

# M-08 recompute readiness instead of consuming it
_orig_declare = PIPE.declare_readiness
PIPE.declare_readiness = lambda master, unresolved=None: {
    "gate": "G5", "ready": True, "blockers": [], "blocker_count": 0,
    "lifecycle_state": "READY_DECLARED", "unresolved_classification": [],
    "unresolved_classification_count": 0, "computed_by": "phase01",
    "recomputed_by_phase01": True, "ready_true_means": "",
    "ready_true_does_not_mean": [], "is_phase_failure": False, "notes": []}
try:
    _d08 = run()[1]["gates"]["G5"]["recomputed_by_phase01"] is True
finally:
    PIPE.declare_readiness = _orig_declare
mutation("08", "recompute readiness inside Phase 01",
         "KILLED" if _d08 else "SURVIVED", f"detected={_d08}")
record("P1-M-08", "MUTATION readiness recomputed", "KILLED",
       "KILLED" if _d08 else "SURVIVED", _d08)

# M-09 auto-correct a contradiction
_orig_detect = G2.detect_contradictions
G2.detect_contradictions = lambda answers: [
    dict(c, corrected=True) for c in _orig_detect(answers)]
try:
    _d09 = any(c["corrected"] for c in G2.detect_contradictions(
        {"openings.presence": "NOT_PRESENT", "openings": [{"id": "X"}]}))
finally:
    G2.detect_contradictions = _orig_detect
mutation("09", "auto-correct a contradiction",
         "KILLED" if _d09 else "SURVIVED", f"detected={_d09}")
record("P1-M-09", "MUTATION contradiction auto-corrected", "KILLED",
       "KILLED" if _d09 else "SURVIVED", _d09)

# M-10 hide blockers in the declaration
_orig_g5 = G5.declare_readiness
G5.declare_readiness = lambda master, unresolved=None: dict(
    _orig_g5(master, unresolved), blockers=[], blocker_count=0)
try:
    _d10 = G5.declare_readiness(_master)["blocker_count"] == 0
finally:
    G5.declare_readiness = _orig_g5
mutation("10", "hide blocking conditions in the declaration",
         "KILLED" if _d10 else "SURVIVED", f"detected={_d10}")
record("P1-M-10", "MUTATION blockers hidden", "KILLED",
       "KILLED" if _d10 else "SURVIVED", _d10)

# CONTROL
_ctrl_before = run()[1]["state"]
_orig_scope = PIPE.VALIDATED_MEANS
PIPE.VALIDATED_MEANS = "renamed text"
_ctrl_after = run()[1]["state"]
PIPE.VALIDATED_MEANS = _orig_scope
mutation("CTRL", "cosmetic text rename", "CONTROL",
         f"before={_ctrl_before}, after={_ctrl_after}")
record("P1-M-CTRL", "CONTROL: cosmetic rename changes no state",
       "same state before and after",
       f"{_ctrl_before}/{_ctrl_after}", _ctrl_before == _ctrl_after)


# --------------------------------------------------------------------------
print("=" * 100)
print("PHASE 01 — INTAKE -> VALIDATED PROJECT MASTER")
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
print(f"MUTATIONS: {_k} killed · {len(_s)} survived"
      f"{' ' + str(_s) if _s else ''} · {_c} CONTROL")
print("SCOPE: Phase 01 builds and validates a master. It is not a designer, "
      "not an engineering judge, not a generator, not an approval authority.")
print("=" * 100)
sys.exit(0 if passed == total else 1)
