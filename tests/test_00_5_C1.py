#!/usr/bin/env python3
"""Phase 00.5-C1 — Generation Preconditions (Gate of Abstention) test suite.

Reference: 00.5-C1-GENERATION-PRECONDITIONS.md R05 (APPROVED/CLOSED).

Discipline (standing rules):
  * every rule gets a POSITIVE and a NEGATIVE case;
  * the negative proves the INTENDED rule fired (assert on the reason CODE,
    never merely on "blocked");
  * mutation tests prove the suite dies when the rule is disabled, and a
    CONTROL mutation proves the deaths are caused by the mutated rule;
  * isolation tests prove C1 does not re-implement A/B1..B11.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import io
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import c1_preconditions as C1                                        # noqa: E402
from c1_preconditions import (                                       # noqa: E402
    OutputRequest, OwnerVerdict, evaluate, evaluate_request,
    abstention_report,
    ALLOWED, ABSTAIN, OWNER_DECLARED, PATH_DERIVED, UNPROVEN_SCOPE,
    SCOPE_MODEL_WIDE, SCOPE_PATH, SCOPE_OUTPUT,
    BLK_LAYER_ERROR, BLK_PRESENCE_UNKNOWN, BLK_UNKNOWN_FIELD, BLK_UNAPPROVED,
    BLK_UNCOMPUTABLE, BLK_DEPENDENCY, BLK_MISSING_GEOMETRY, BLK_NO_CAMERA,
    BLK_NO_CAPABILITY, BLK_VERSION_MISMATCH, BLK_UNTRUSTED_SOURCE)
from validate_blocking import build_uncertainty_map                  # noqa: E402
from schema_gate import final_approval_readiness                     # noqa: E402

RESULTS = []
TODAY = "2026-09-12"


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


# --------------------------------------------------------------------------
# Fixture — reuse B6's BASE, already accepted by A/B1..B7.
# --------------------------------------------------------------------------
_src = open(os.path.join(HERE, "test_00_5_B6.py"), encoding="utf-8").read()
_ns = {"__name__": "b6fixture", "__file__": os.path.join(HERE, "test_00_5_B6.py")}
try:
    with redirect_stdout(io.StringIO()):
        exec(compile(_src, "test_00_5_B6.py", "exec"), _ns)
except SystemExit:
    pass

BASE = _ns["BASE"]
fact = _ns["fact"]
unknown_fact = _ns["unknown_fact"]
confirmed_absent = _ns["confirmed_absent"]

CAMERA = {"id": "CAM-01", "pos": [0, 0, 1600], "target": [1000, 1000, 1200],
          "fov_deg": 60, "status": "C"}

CAPS_ALL = {"dxf": True, "svg": True, "glb": True, "pptx": True}
CAPS_NO_DXF = {"dxf": False, "svg": True, "glb": True, "pptx": True}


# ---- requested outputs (owned by the CALLER; C1 never reads outputs[]) ----
def plan_A(oid="OUT-PLAN-A"):
    return OutputRequest(oid, "A", "PLAN",
                         requires_paths=("space/outline",),
                         shared_geometry=("space/outline",),
                         requires_capability="svg")


def plan_B(oid="OUT-PLAN-B"):
    return OutputRequest(oid, "B", "PLAN_PRESENTATION",
                         requires_paths=("space/outline",),
                         shared_geometry=("space/outline",),
                         requires_capability="svg")


def section_A(oid="OUT-SECT-A"):
    return OutputRequest(oid, "A", "SECTION",
                         requires_paths=("space/outline",
                                         "space/ceiling_height"),
                         shared_geometry=("space/outline",),
                         requires_capability="svg")


def perspective_A(oid="OUT-PERSP-A"):
    return OutputRequest(oid, "A", "PERSPECTIVE",
                         requires_paths=("space/outline",
                                         "space/ceiling_height"),
                         shared_geometry=("space/outline",),
                         requires_camera=True, requires_capability="svg")


def furniture_A(oid="OUT-FURN-A"):
    return OutputRequest(oid, "A", "FURNITURE_PLAN",
                         requires_paths=("space/outline",
                                         "presence_register/existing_furniture"),
                         shared_geometry=("space/outline",),
                         requires_capability="svg")


def dxf_A(oid="OUT-DXF-A"):
    return OutputRequest(oid, "A", "PLAN",
                         requires_paths=("space/outline",),
                         shared_geometry=("space/outline",),
                         requires_capability="dxf")


def umap(data):
    return build_uncertainty_map(data)


def decide(data, req, verdicts=(), caps=None):
    return evaluate_request(data, req, verdicts,
                            capabilities=caps if caps is not None else CAPS_ALL,
                            uncertainty=umap(data))


def with_cam(data):
    d = copy.deepcopy(data)
    d["cameras"] = [dict(CAMERA)]
    return d


# ==========================================================================
# 1. POSITIVE
# ==========================================================================
_d = with_cam(BASE)
_r = decide(_d, plan_A())
record("C1-P-01", "Clean master, Floor Plan A, all inputs [C]",
       ALLOWED, _r.decision, _r.allowed)

_r = decide(_d, plan_B())
record("C1-P-02", "Clean master, Floor Plan B (presentation)",
       ALLOWED, _r.decision, _r.allowed)

_r = decide(_d, section_A())
record("C1-P-03", "Section A with confirmed ceiling_height",
       ALLOWED, _r.decision, _r.allowed)

_r = decide(_d, perspective_A())
record("C1-P-04", "Perspective A with a confirmed camera",
       ALLOWED, _r.decision, _r.allowed)

# The fixture carries a DECLARED-ONLY unknown (orientation_north). It must NOT
# block an output that does not consume it  (anti over-blocking, AS-C1-06).
_um = umap(_d)
_r = decide(_d, plan_A())
record("C1-P-05", "Irrelevant declared UNKNOWN (orientation_north) present",
       f"{ALLOWED}; unknown seen by B7",
       f"{_r.decision}; b7_saw={'space/orientation_north' in _um}",
       _r.allowed and "space/orientation_north" in _um)

_r = decide(_d, furniture_A())
record("C1-P-06", "NOT_PRESENT furniture is a usable fact",
       ALLOWED, _r.decision, _r.allowed)

_ready, _blk = final_approval_readiness(_d)
record("C1-P-07", "Fixture is genuinely gate-clean (A layer agrees)",
       "ready=True, blockers=0", f"ready={_ready}, blockers={len(_blk)}",
       _ready and not _blk)


# ==========================================================================
# 2. NEGATIVE — each asserts the INTENDED code fired
# ==========================================================================
def neg(tid, scenario, mutate, req, expect_code, verdicts=(), caps=None):
    d = with_cam(BASE)
    mutate(d)
    r = decide(d, req, verdicts, caps)
    ok = (not r.allowed) and (expect_code in r.codes())
    record(tid, scenario, f"{ABSTAIN} + {expect_code}",
           f"{r.decision} + {r.codes()}", ok)
    return r


neg("C1-N-01", "ceiling_height = [U] -> Section A",
    lambda d: d["space"].__setitem__("ceiling_height", unknown_fact("U-777")),
    section_A(), BLK_UNKNOWN_FIELD)

neg("C1-N-02", "ceiling_height [D] UNCOMPUTABLE -> Section A",
    lambda d: d["space"].__setitem__("ceiling_height", {
        "value": None, "status": "D", "source_type": "DERIVED_CALC",
        "source_ref": "calc", "recorded_on": TODAY,
        "derived_from": ["space/missing_base"], "formula": "base + 100",
        "derivation_type": "ARITHMETIC"}),
    section_A(), BLK_UNCOMPUTABLE)

# A [D] whose input is [U] is reported by B7 as UNCOMPUTABLE (propagated via
# derived_from). C1 consumes that verdict verbatim -> A-BLK-07. Asserting
# A-BLK-05 here would have meant C1 re-deriving the cause itself, which is
# exactly what C1 must NOT do.
_n03 = neg("C1-N-03", "unresolved derived_from (dependency on an [U]) -> Section A",
           lambda d: (
               d["registers"]["unknowns"].append(
                   {"id": "U-778", "question": "slab?", "blocking": False,
                    "raised_on": TODAY}),
               d["space"].__setitem__("slab_thickness", unknown_fact("U-778")),
               d["space"].__setitem__("ceiling_height", {
                   "value": 2700, "unit": "mm", "status": "D",
                   "source_type": "DERIVED_CALC", "source_ref": "calc",
                   "recorded_on": TODAY, "derived_from": ["space/slab_thickness"],
                   "formula": "3000 - slab_thickness",
                   "derivation_type": "ARITHMETIC"})),
           section_A(), BLK_UNCOMPUTABLE)

# ...and prove the block really came from the propagated dependency, not from
# some unrelated check: the reason must name B7 as the judging layer.
_via_b7 = any(r.source_layer == "B7" and r.code == BLK_UNCOMPUTABLE
              for r in _n03.reasons)
record("C1-N-03b", "...and that verdict is consumed from B7, not recomputed",
       "reason attributed to B7", f"from_b7={_via_b7}", _via_b7)

neg("C1-N-04", "unapproved proposal [P] -> Section A",
    lambda d: d["space"].__setitem__("ceiling_height", {
        "value": 2700, "unit": "mm", "status": "P",
        "source_type": "AGENT_PROPOSAL", "source_ref": "agent",
        "recorded_on": TODAY, "proposal_id": "PR-01"}),
    section_A(), BLK_UNAPPROVED)

neg("C1-N-05", "unapproved assumption [A] PENDING -> Section A",
    lambda d: d["space"].__setitem__("ceiling_height", {
        "value": 2700, "unit": "mm", "status": "A",
        "source_type": "AGENT_ASSUMPTION", "source_ref": "assumed",
        "recorded_on": TODAY, "assumption_id": "A-01",
        "approval_state": "PENDING_APPROVAL"}),
    section_A(), BLK_UNAPPROVED)

neg("C1-N-06", "missing required geometry (outline absent) -> Plan A",
    lambda d: d["space"].pop("outline"),
    plan_A(), BLK_MISSING_GEOMETRY)

neg("C1-N-07", "no camera defined -> Perspective A",
    lambda d: d.__setitem__("cameras", []),
    perspective_A(), BLK_NO_CAMERA)

neg("C1-N-08", "capability 'dxf' unavailable -> DXF Plan A",
    lambda d: None, dxf_A(), BLK_NO_CAPABILITY, caps=CAPS_NO_DXF)

_stale = OwnerVerdict("XR-017", "ERROR", "B1",
                      "fingerprint geometry_version != master; stale model",
                      scope={"kind": SCOPE_OUTPUT, "outputs": ["OUT-PLAN-A"]},
                      code=BLK_VERSION_MISMATCH)
neg("C1-N-09", "stale revision/geometry mismatch (owner-scoped) -> that output",
    lambda d: None, plan_A(), BLK_VERSION_MISMATCH, verdicts=[_stale])

neg("C1-N-10", "untrusted source AI_IMAGE on a required path -> Plan A",
    lambda d: d["space"].__setitem__("outline", fact(
        [[0, 0], [6000, 0], [6000, 4000], [0, 4000]], unit="mm",
        src="AI_IMAGE", ref="render.png")),
    plan_A(), BLK_UNTRUSTED_SOURCE)

neg("C1-N-11", "presence UNKNOWN on a consumed element -> Furniture Plan A",
    lambda d: (
        d["registers"]["unknowns"].append(
            {"id": "U-779", "question": "existing furniture?",
             "blocking": False, "raised_on": TODAY}),
        d["presence_register"].__setitem__("existing_furniture", {
            "value": None, "status": "C", "source_type": "CLIENT_INPUT",
            "source_ref": "not surveyed", "recorded_on": TODAY,
            "presence": "UNKNOWN"})),
    furniture_A(), BLK_PRESENCE_UNKNOWN)


# ==========================================================================
# 3. BOUNDARY
# ==========================================================================
_d = copy.deepcopy(BASE)
_d["cameras"] = []
_p, _q = decide(_d, plan_A()), decide(_d, perspective_A())
record("C1-BD-01", "No camera: Floor Plan A vs Perspective A",
       "plan=ALLOWED, perspective=ABSTAIN",
       f"plan={_p.decision}, persp={_q.decision}",
       _p.allowed and not _q.allowed and BLK_NO_CAMERA in _q.codes())

_d = with_cam(BASE)
_d["space"]["ceiling_height"] = unknown_fact("U-780")
_d["registers"]["unknowns"].append({"id": "U-780", "question": "height?",
                                    "blocking": False, "raised_on": TODAY})
_p, _s = decide(_d, plan_A()), decide(_d, section_A())
record("C1-BD-02", "ceiling_height UNKNOWN: Floor Plan vs Section",
       "plan=ALLOWED, section=ABSTAIN",
       f"plan={_p.decision}, section={_s.decision}",
       _p.allowed and not _s.allowed and BLK_UNKNOWN_FIELD in _s.codes())

_pb = decide(_d, plan_B())
record("C1-BD-03", "ceiling_height UNKNOWN must NOT block Floor Plan B",
       ALLOWED, _pb.decision, _pb.allowed)

# one element broken must not touch an unrelated output
_d = with_cam(BASE)
_d["registers"]["unknowns"].append({"id": "U-781", "question": "furniture?",
                                    "blocking": False, "raised_on": TODAY})
_d["presence_register"]["existing_furniture"] = {
    "value": None, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "not surveyed", "recorded_on": TODAY, "presence": "UNKNOWN"}
_f, _p = decide(_d, furniture_A()), decide(_d, plan_A())
record("C1-BD-04", "Single-element problem does not affect unrelated output",
       "furniture=ABSTAIN, plan=ALLOWED",
       f"furniture={_f.decision}, plan={_p.decision}",
       (not _f.allowed) and _p.allowed)

# shared geometry breaks A AND B
_d = with_cam(BASE)
_d["registers"]["unknowns"].append({"id": "U-782", "question": "outline?",
                                    "blocking": False, "raised_on": TODAY})
_d["space"]["outline"] = unknown_fact("U-782")
_a, _b = decide(_d, plan_A()), decide(_d, plan_B())
record("C1-BD-05", "Shared geometry failure blocks BOTH A and B",
       "A=ABSTAIN, B=ABSTAIN", f"A={_a.decision}, B={_b.decision}",
       (not _a.allowed) and (not _b.allowed))

# NOT_PRESENT vs UNKNOWN
_d1 = with_cam(BASE)                                   # NOT_PRESENT (fixture)
_d2 = copy.deepcopy(_d1)
_d2["registers"]["unknowns"].append({"id": "U-783", "question": "furniture?",
                                     "blocking": False, "raised_on": TODAY})
_d2["presence_register"]["existing_furniture"] = {
    "value": None, "status": "C", "source_type": "CLIENT_INPUT",
    "source_ref": "not surveyed", "recorded_on": TODAY, "presence": "UNKNOWN"}
_np, _un = decide(_d1, furniture_A()), decide(_d2, furniture_A())
record("C1-BD-06", "NOT_PRESENT passes, UNKNOWN blocks (triple distinction)",
       "NOT_PRESENT=ALLOWED, UNKNOWN=ABSTAIN",
       f"NOT_PRESENT={_np.decision}, UNKNOWN={_un.decision}",
       _np.allowed and not _un.allowed
       and BLK_PRESENCE_UNKNOWN in _un.codes())

# approved [A] vs [C]/[D]
_d = with_cam(BASE)
_d["space"]["ceiling_height"] = {
    "value": 2800, "unit": "mm", "status": "A",
    "source_type": "AGENT_ASSUMPTION", "source_ref": "assumed typical",
    "recorded_on": TODAY, "assumption_id": "A-02",
    "approval_state": "APPROVED", "approved_by": "USER",
    "approved_on": TODAY}
_appr = decide(_d, section_A())
_d2 = with_cam(BASE)                                   # [C] control
_conf = decide(_d2, section_A())
record("C1-BD-07", "APPROVED [A] is NOT eligible for class A; [C] is",
       "approved[A]=ABSTAIN, [C]=ALLOWED",
       f"approved[A]={_appr.decision}, [C]={_conf.decision}",
       (not _appr.allowed) and BLK_UNAPPROVED in _appr.codes()
       and _conf.allowed)

_d = with_cam(BASE)
_d["space"]["ceiling_height"] = {
    "value": 2800, "unit": "mm", "status": "D", "source_type": "DERIVED_CALC",
    "source_ref": "derivation", "recorded_on": TODAY,
    "derived_from": ["space/floor_level"], "formula": "floor_level + 2800",
    "derivation_type": "ARITHMETIC"}
_r = decide(_d, section_A())
record("C1-BD-08", "VERIFIED [D] is eligible for class A",
       ALLOWED, _r.decision, _r.allowed)


# ==========================================================================
# 4. SCOPE — the three categories, and no invention
# ==========================================================================
_d = with_cam(BASE)
_mw = OwnerVerdict("OWNER-MW", "ERROR", "A",
                   "shared geometry corrupted for the whole master",
                   scope={"kind": SCOPE_MODEL_WIDE}, code=BLK_LAYER_ERROR)
_res = evaluate(_d, [plan_A(), section_A(), perspective_A(), plan_B()],
                verdicts=[_mw], capabilities=CAPS_ALL, uncertainty=umap(_d))
_all_blocked = all(not r.allowed for r in _res)
_all_owner = all(OWNER_DECLARED in r.bases() for r in _res)
record("C1-SC-01", "A: owner declares MODEL_WIDE -> comprehensive block",
       "all ABSTAIN, basis=OWNER_DECLARED",
       f"blocked={_all_blocked}, basis_ok={_all_owner}",
       _all_blocked and _all_owner)

_pathv = OwnerVerdict("OWNER-PATH", "ERROR", "B2",
                      "problem confined to ceiling_height",
                      scope={"kind": SCOPE_PATH,
                             "paths": ["space/ceiling_height"]},
                      code=BLK_LAYER_ERROR)
_res = evaluate(_d, [plan_A(), section_A()], verdicts=[_pathv],
                capabilities=CAPS_ALL, uncertainty=umap(_d))
_plan, _sect = _res
record("C1-SC-02", "B: owner declares PATH scope -> only consumers affected",
       "plan=ALLOWED, section=ABSTAIN",
       f"plan={_plan.decision}, section={_sect.decision}",
       _plan.allowed and not _sect.allowed
       and OWNER_DECLARED in _sect.bases())

_outv = OwnerVerdict("OWNER-OUT", "ERROR", "B1", "stale fingerprint",
                     scope={"kind": SCOPE_OUTPUT, "outputs": ["OUT-SECT-A"]},
                     code=BLK_VERSION_MISMATCH)
_res = evaluate(_d, [plan_A(), section_A()], verdicts=[_outv],
                capabilities=CAPS_ALL, uncertainty=umap(_d))
record("C1-SC-03", "B: owner declares OUTPUT scope -> only that output",
       "plan=ALLOWED, section=ABSTAIN",
       f"plan={_res[0].decision}, section={_res[1].decision}",
       _res[0].allowed and not _res[1].allowed)

_nosc = OwnerVerdict("OWNER-NOSCOPE", "ERROR", "B3",
                     "clearance rule violated", scope=None,
                     code=BLK_LAYER_ERROR)
_res = evaluate(_d, [plan_A(), section_A()], verdicts=[_nosc],
                capabilities=CAPS_ALL, uncertainty=umap(_d))
_fc = all((not r.allowed) and UNPROVEN_SCOPE in r.bases() for r in _res)
record("C1-SC-04", "C: no trustworthy scope -> UNPROVEN_SCOPE + fail-closed",
       "all ABSTAIN, basis=UNPROVEN_SCOPE",
       f"failclosed={_fc}", _fc)

# fail-closed must NOT be dressed up as "model invalid"
_msg = " ".join(r.message for r in _res[0].reasons)
record("C1-SC-05", "UNPROVEN_SCOPE is declared honestly, not as model-invalid",
       "message says scope not proven",
       f"has_disclaimer={'scope not proven' in _msg}",
       "scope not proven" in _msg)

# free-text location is NOT a scope contract
_loctxt = OwnerVerdict("OWNER-LOC", "ERROR", "B2",
                       "problem at space/ceiling_height", scope=None,
                       code=BLK_LAYER_ERROR)
_r = decide(_d, plan_A(), verdicts=[_loctxt])
record("C1-SC-06", "Free-text location must NOT be parsed into a scope",
       f"{ABSTAIN} + UNPROVEN_SCOPE (no narrowing)",
       f"{_r.decision} + {_r.bases()}",
       (not _r.allowed) and UNPROVEN_SCOPE in _r.bases())

# non-ERROR severity is consumed as-is and does not block
_warn = OwnerVerdict("OWNER-WARN", "WARN", "B4", "advisory only",
                     scope={"kind": SCOPE_MODEL_WIDE}, code=BLK_LAYER_ERROR)
_r = decide(_d, plan_A(), verdicts=[_warn])
record("C1-SC-07", "WARN/INFO severity is not escalated to a block",
       ALLOWED, _r.decision, _r.allowed)

# project-level blocker is not automatically universal (C1-FIX-03)
_pblk = OwnerVerdict("A-BLOCKER", "ERROR", "A", "camera unknown",
                     scope={"kind": SCOPE_OUTPUT, "outputs": ["OUT-PERSP-A"]},
                     code=BLK_LAYER_ERROR)
_res = evaluate(_d, [plan_A(), perspective_A()], project_blockers=[_pblk],
                capabilities=CAPS_ALL, uncertainty=umap(_d))
record("C1-SC-08", "Project-level blocker is not a universal output block",
       "plan=ALLOWED, perspective=ABSTAIN",
       f"plan={_res[0].decision}, persp={_res[1].decision}",
       _res[0].allowed and not _res[1].allowed)


# ==========================================================================
# 5. MUTATION — break each rule, the suite must notice. Plus a CONTROL.
# ==========================================================================
def mutate(tid, scenario, attr, value, probe, expect_flip=True):
    original = getattr(C1, attr)
    setattr(C1, attr, value)
    try:
        flipped = probe()
    finally:
        setattr(C1, attr, original)
    ok = (flipped == expect_flip)
    record(tid, scenario, f"detected={expect_flip}", f"detected={flipped}", ok)


def _probe_approved_A_blocked_by_status_rule():
    """Isolate the status-eligibility rule.

    An APPROVED [A] is caught by TWO independent defences: the status rule
    (ELIGIBLE_STATUSES) and the untrusted-source rule (AGENT_ASSUMPTION).
    To prove the status rule is load-bearing we must neutralise the other
    defence, otherwise the mutation is masked and the test proves nothing.
    """
    d = with_cam(BASE)
    d["space"]["ceiling_height"] = {
        "value": 2800, "unit": "mm", "status": "A",
        # deliberately a TRUSTED source so only the [A] status can block
        "source_type": "CLIENT_INPUT", "source_ref": "client stated approx",
        "recorded_on": TODAY, "assumption_id": "A-03",
        "approval_state": "APPROVED"}
    return decide(d, section_A()).allowed


# Baseline: with the rule intact the approved [A] must be blocked.
_m01_base = _probe_approved_A_blocked_by_status_rule()
record("C1-M-01a", "Baseline: approved [A] blocked by the status rule alone",
       "blocked (allowed=False)", f"allowed={_m01_base}", not _m01_base)

mutate("C1-M-01", "Allow [A] into class A -> BD-07 must die",
       "ELIGIBLE_STATUSES", frozenset({"C", "D", "A"}),
       _probe_approved_A_blocked_by_status_rule)


def _probe_untrusted_allowed():
    d = with_cam(BASE)
    d["space"]["outline"] = fact([[0, 0], [1, 0], [1, 1], [0, 1]], unit="mm",
                                 src="AI_IMAGE", ref="render.png")
    return decide(d, plan_A()).allowed


mutate("C1-M-02", "Empty UNTRUSTED_SOURCES -> N-10 must die",
       "UNTRUSTED_SOURCES", frozenset(), _probe_untrusted_allowed)


def _probe_unproven_allowed():
    d = with_cam(BASE)
    v = OwnerVerdict("X", "ERROR", "B3", "no scope", scope=None)
    return decide(d, plan_A(), verdicts=[v]).allowed


def _open_scope(verdict, req):
    return False, UNPROVEN_SCOPE          # "no scope -> ignore it" (wrong)


mutate("C1-M-03", "Turn fail-closed into fail-open -> SC-04 must die",
       "_scope_hits", _open_scope, _probe_unproven_allowed)


def _probe_modelwide_narrowed():
    d = with_cam(BASE)
    v = OwnerVerdict("X", "ERROR", "A", "model wide",
                     scope={"kind": SCOPE_MODEL_WIDE})
    res = evaluate(d, [plan_A(), section_A()], verdicts=[v],
                   capabilities=CAPS_ALL, uncertainty=umap(d))
    return any(r.allowed for r in res)


def _narrow_modelwide(verdict, req):
    return False, OWNER_DECLARED          # ignore MODEL_WIDE (wrong)


mutate("C1-M-04", "Ignore MODEL_WIDE scope -> SC-01 must die",
       "_scope_hits", _narrow_modelwide, _probe_modelwide_narrowed)

# CONTROL: a mutation unrelated to the asserted rules must NOT flip them.
_ctrl_before = decide(with_cam(BASE), plan_A()).allowed
_orig_abst = C1.ABSTAIN
C1.ABSTAIN = "ABSTAIN_RENAMED"
_ctrl_after = decide(with_cam(BASE), plan_A()).allowed
C1.ABSTAIN = _orig_abst
record("C1-M-05", "CONTROL: cosmetic change does not flip a positive verdict",
       "allowed before and after",
       f"before={_ctrl_before}, after={_ctrl_after}",
       _ctrl_before and _ctrl_after)


# ==========================================================================
# 6. ISOLATION — C1 must not re-implement A/B1..B11
# ==========================================================================
_engine_src = open(os.path.join(ROOT, "scripts", "c1_preconditions.py"),
                   encoding="utf-8").read()

_forbidden_imports = ["validate_topology", "validate_furniture",
                      "validate_movement", "validate_doors",
                      "validate_formulas", "validate_outputs",
                      "validate_refs", "validate_revisions",
                      "validate_lifecycle", "validate_temporal",
                      "validate_blocking", "schema_gate"]
_imported = [m for m in _forbidden_imports
             if f"import {m}" in _engine_src or f"from {m}" in _engine_src]
record("C1-ISO-01", "C1 engine imports no validator (pure consumer)",
       "no validator imports", f"found={_imported}", not _imported)

# C1 must not itself detect a B2 topology defect.
_d = with_cam(BASE)
_d["walls"][0]["start"] = [0, 0]
_d["walls"][0]["end"] = [0, 0]                     # degenerate wall (B2's job)
_r = decide(_d, plan_A())
record("C1-ISO-02", "C1 does NOT detect a B2 geometry defect by itself",
       "ALLOWED (C1 has no topology rules)", _r.decision, _r.allowed)

# ...but blocks the moment B2's owner hands it a scoped verdict.
_v = OwnerVerdict("WT-001", "ERROR", "B2", "degenerate wall W-01",
                  scope={"kind": SCOPE_PATH, "paths": ["space/outline"]},
                  code=BLK_LAYER_ERROR)
_r2 = decide(_d, plan_A(), verdicts=[_v])
record("C1-ISO-03", "C1 blocks when the OWNER supplies the verdict",
       ABSTAIN, _r2.decision, not _r2.allowed)

# Foreign rule IDs must not be re-implemented. Strip comments first: a
# comment naming an owner is documentation, not re-implementation.
_code_only = "\n".join(
    ln.split("#")[0] for ln in _engine_src.splitlines()
    if not ln.strip().startswith("#"))
_rule_ids = ["WT-0", "FC-0", "MV-0", "DS-0", "FM-0", "OR-0", "XR-0",
             "RV-0", "LC-0", "TI-0", "UB-0", "INV-"]
_leaked = [r for r in _rule_ids if r in _code_only]
record("C1-ISO-04", "C1 does not hard-code other layers' rule IDs",
       "no foreign rule IDs in executable code", f"leaked={_leaked}",
       not _leaked)

# Severity is consumed, never re-graded. The engine may STORE an incoming
# severity on its adapter (that is consumption); what it must never do is
# assign a severity VALUE of its own.
_regrades = ('.severity = "' in _code_only or ".severity = '" in _code_only)
_reads_severity = ".severity" in _code_only
record("C1-ISO-05", "C1 never assigns a severity value of its own",
       "reads severity, assigns no literal",
       f"regrades={_regrades}, reads={_reads_severity}",
       (not _regrades) and _reads_severity)

# C1 does not read outputs[] from the master
_reads_outputs = ('data.get("outputs")' in _engine_src
                  or "data.get('outputs')" in _engine_src
                  or 'data["outputs"]' in _engine_src)
record("C1-ISO-06", "C1 never reads or writes master['outputs'] (GAP-C-06)",
       "no outputs[] access", f"reads_outputs={_reads_outputs}",
       not _reads_outputs)


# ==========================================================================
# 7. ANTI-SMUGGLING
# ==========================================================================
_d = with_cam(BASE)
_d["space"]["ceiling_height"] = {
    "value": 2800, "unit": "mm", "status": "A",
    "source_type": "AGENT_ASSUMPTION", "source_ref": "assumed",
    "recorded_on": TODAY, "assumption_id": "A-04",
    "approval_state": "APPROVED", "approved_by": "USER"}
_r = decide(_d, section_A())
record("C1-AS-01", "Approved assumption cannot enter class A",
       f"{ABSTAIN} + {BLK_UNAPPROVED}", f"{_r.decision} + {_r.codes()}",
       (not _r.allowed) and BLK_UNAPPROVED in _r.codes())

_d = with_cam(BASE)
_d["space"]["ceiling_height"] = {
    "value": 2700, "unit": "mm", "status": "P", "source_type": "AGENT_PROPOSAL",
    "source_ref": "agent", "recorded_on": TODAY, "proposal_id": "PR-02"}
_r = decide(_d, section_A())
record("C1-AS-02", "Proposal cannot enter class A",
       f"{ABSTAIN} + {BLK_UNAPPROVED}", f"{_r.decision} + {_r.codes()}",
       (not _r.allowed) and BLK_UNAPPROVED in _r.codes())

_d = with_cam(BASE)
_d["space"]["outline"] = fact([[0, 0], [1, 0], [1, 1], [0, 1]], unit="mm",
                              src="AI_IMAGE", ref="mood.png")
_ra, _rb = decide(_d, plan_A()), decide(_d, plan_B())
record("C1-AS-03", "AI image cannot feed class A or class B",
       "both ABSTAIN + A-BLK-13",
       f"A={_ra.codes()}, B={_rb.codes()}",
       (not _ra.allowed) and (not _rb.allowed)
       and BLK_UNTRUSTED_SOURCE in _ra.codes()
       and BLK_UNTRUSTED_SOURCE in _rb.codes())

# a presentation parameter may not alter geometry: B declares the SAME
# geometry paths as A, so it cannot silently substitute its own.
_pa, _pb = plan_A(), plan_B()
record("C1-AS-04", "Class B consumes the same master geometry as A",
       "identical shared geometry",
       f"A={_pa.shared_geometry}, B={_pb.shared_geometry}",
       _pa.shared_geometry == _pb.shared_geometry)

# B may not be an independent geometry source when shared geometry fails
_d = with_cam(BASE)
_d["registers"]["unknowns"].append({"id": "U-790", "question": "outline?",
                                    "blocking": False, "raised_on": TODAY})
_d["space"]["outline"] = unknown_fact("U-790")
_rb = decide(_d, plan_B())
record("C1-AS-05", "B cannot substitute for a blocked A on broken geometry",
       ABSTAIN, _rb.decision, not _rb.allowed)

# capability missing must abstain, never silently downgrade the class
_r = decide(with_cam(BASE), dxf_A(), caps=CAPS_NO_DXF)
_downgraded = _r.cls != "A"
record("C1-AS-06", "Missing capability abstains; no silent downgrade",
       f"{ABSTAIN}, class stays A",
       f"{_r.decision}, class={_r.cls}",
       (not _r.allowed) and not _downgraded
       and BLK_NO_CAPABILITY in _r.codes())

# an abstention must be explicit in the report, never a half-finished artefact
_txt = abstention_report([_r])
record("C1-AS-07", "Abstention is declared explicitly with a lift path",
       "report states ABSTAINED + reason + how to lift",
       f"has_abstained={'ABSTAINED' in _txt}, has_lift={'to lift:' in _txt}",
       "ABSTAINED" in _txt and "to lift:" in _txt)

record("C1-AS-08", "C1 produces no artefact file (gate only)",
       "no file-writing calls in engine",
       f"open={'open(' in _engine_src}, write={'.write(' in _engine_src}",
       "open(" not in _engine_src and ".write(" not in _engine_src)


# ==========================================================================
# 8. NO-WRITE
# ==========================================================================
def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


_master_tpl = os.path.join(ROOT, "project_master.template.json")
_schema_p = os.path.join(ROOT, "project_master.schema.json")
_before = (_sha(_master_tpl), _sha(_schema_p))

_d = with_cam(BASE)
_snapshot = copy.deepcopy(_d)
evaluate(_d, [plan_A(), section_A(), perspective_A(), plan_B(), dxf_A()],
         verdicts=[_stale, _nosc], capabilities=CAPS_NO_DXF,
         uncertainty=umap(_d))
_after = (_sha(_master_tpl), _sha(_schema_p))

record("C1-NW-01", "Running C1 does not modify the in-memory model",
       "model byte-identical", f"identical={_snapshot == _d}",
       _snapshot == _d)
record("C1-NW-02", "Running C1 does not modify master template or schema",
       "sha256 unchanged", f"unchanged={_before == _after}",
       _before == _after)

_pm = os.path.join(ROOT, "project_master.json")
record("C1-NW-03", "C1 never creates project_master.json",
       "absent or untouched", f"exists={os.path.exists(_pm)}",
       not os.path.exists(_pm))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-C1 — GENERATION PRECONDITIONS (GATE OF ABSTENTION) REPORT")
print("=" * 94)
passed = sum(1 for r in RESULTS if r[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    mark = "OK  " if verdict == "PASS" else "FAIL"
    print(f"{mark} {tid:10} {scenario[:56]:56} {actual[:30]}")
print("-" * 94)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 94)
sys.exit(0 if passed == total else 1)
