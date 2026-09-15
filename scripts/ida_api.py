#!/usr/bin/env python3
"""
ida_api.py — Agent Interfaces · High-Level Python API
واجهات الوكيل · الواجهة البرمجية عالية المستوى

WHAT THIS IS
  The single programmatic entry point of the Interior Designer Agent.
  It wires the owning engines together into usable operations and returns
  plain JSON-serialisable dicts. The CLI (`ida.py`) and any future UI call
  this module — nothing else needs to import the engines directly.

WHAT THIS IS NOT (boundaries inherited from the architecture)
  * It re-implements NO rule. Every judgement is produced by its owning
    engine and carried verbatim (same discipline as C6 / Phase 01 G3-G4).
  * It invents NO value, upgrades NO status, approves NOTHING.
  * It writes NO master file by itself: mutating helpers return the updated
    structure (or explicitly say they saved), and the caller persists.
  * Approvals come only from the USER and only through explicit calls.

OPERATION MAP (operation -> owning engine)
  run_intake        -> p1_intake (G1)            readiness gate, no master yet
  run_phase01       -> p1_pipeline (G1..G5)      intake -> validated master
  validate_all      -> schema_gate + B1..B11    carried via p1_validate
  readiness         -> schema_gate + B7         final approval readiness
  project_status    -> reader (no verdicts)     dashboard over the master
  gate_plan         -> c1_preconditions (C1)    may this output be generated?
  generate_plan     -> C1 gate + c3_svg (C3)    Class A floor plan (SVG)
  build_quantities  -> c4_quantities (C4)       external quantity schedule
  present_class_b   -> c5_presentation (C5)     Class B from the A assembly
  assemble_manifest -> c6_manifest (C6)         evidence assembly, no verdict
  assess_fidelity   -> d_report (D)             output-vs-GA fidelity
  existing_state    -> sa_existing_state (O-1)  analytical evidence, not Class A
  record_* / apply  -> registers + e_* rules    governance, USER authority only
  caption_for       -> schema_gate lint         language-policy-safe captions

All functions are import-safe on Python 3.11+ with stdlib only, except
the schema layer which requires `jsonschema` (see requirements.txt).
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ida_workspace as WS                                    # noqa: E402
import p1_intake as G1                                        # noqa: E402
import p1_pipeline as PIPE                                    # noqa: E402
import p1_validate as G34                                     # noqa: E402
import p1_readiness as G5                                     # noqa: E402

# Engines imported lazily where an optional dependency is involved.
_schema_gate = None


def _schema():
    global _schema_gate
    if _schema_gate is None:
        import schema_gate as SG
        _schema_gate = SG
    return _schema_gate


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class IDAError(RuntimeError):
    """Base error for interface-level refusals."""


class GovernanceError(IDAError):
    """A governance boundary refused the requested act."""


class Abstained(IDAError):
    """The operation abstained (a legitimate, non-error outcome).

    Carries the machine-readable record in `.record`.
    """

    def __init__(self, message, record=None):
        super().__init__(message)
        self.record = record or {}


# ---------------------------------------------------------------------------
# Master IO
# ---------------------------------------------------------------------------

def load_master(path):
    """Load a project master, stripping documentation keys.

    Raises IDAError when the file is missing or is not valid JSON.
    Loading judges nothing — validation is a separate, explicit step.
    """
    if not os.path.exists(path):
        raise IDAError("master file not found: %s" % path)
    try:
        data = WS.load_json(path)
    except ValueError as exc:
        raise IDAError("master file is not valid JSON: %s (%s)" % (path, exc))
    return WS.strip_private(data)


def save_master(master, path):
    """Persist a master dict. Returns the path written."""
    return WS.save_json(master, path)


# ---------------------------------------------------------------------------
# Phase 01 — intake -> validated master
# ---------------------------------------------------------------------------

def run_intake(answers, field_specs):
    """G1: may population begin? Returns the G1 record (JSON-safe)."""
    answers = WS.strip_private(answers or {})
    return G1.evaluate_intake(answers, field_specs or [])


def run_phase01(answers, field_specs, recorded_on=None, template=None):
    """Full Phase 01 pipeline. Returns (master_or_None, run_record).

    `recorded_on` defaults to today (UTC). `template` defaults to the
    system template. Nothing is written to disk.
    """
    answers = WS.strip_private(answers or {})
    when = recorded_on or WS.utc_today()
    return PIPE.run_phase01(answers, field_specs or [], when, template)


def run_phase01_from_files(intake_path, specs_path, recorded_on=None):
    """Convenience: read intake + specs from disk, run the pipeline."""
    answers = WS.strip_private(WS.load_json(intake_path))
    specs = WS.load_json(specs_path)
    return run_phase01(answers, specs, recorded_on)


# ---------------------------------------------------------------------------
# Validation (carried verdicts — ownership stays with the engines)
# ---------------------------------------------------------------------------

def _count_by_severity(refs):
    counts = {}
    for ref in refs or []:
        sev = ref.get("severity") or "UNKNOWN"
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def validate_all(master):
    """Run A (schema gate) + B1..B11 (rule validators).

    Returns a JSON-safe report. Verdicts are carried exactly as issued:
    this function never re-grades a severity and never softens an ERROR.

    INTERFACE COMPLETION (documented, upstream defect flagged — see
    AGENT-INTERFACES.md section on the G3 carrier): the Phase 01 G3 carrier
    expects Finding objects, but schema_gate.validate_master returns plain
    strings, so the carried G3 refs arrive EMPTY (rule/location/message/
    severity all null) and G3 error_count is always 0 — a schema-invalid
    master would report PASS. The interface therefore ALSO consumes the
    schema gate's own boolean verdict via validate_master() directly and
    fails the summary when the schema itself rejects the master. That is
    not a reinterpretation: ok=False IS the engine's verdict, and every
    invariant is documented by the engine as "a hard error".
    """
    SG = _schema()
    g3 = G34.run_schema_gate(master)
    g4 = G34.run_rule_validators(master)
    schema_ok, schema_errors = SG.validate_master(master or {})
    schema_errors = [str(e) for e in (schema_errors or [])]
    total_errors = (len(schema_errors) + g4.get("error_count", 0))
    g3_carrier_empty = all(
        ref.get("severity") is None and ref.get("message") is None
        for ref in (g3.get("finding_references") or []))
    return {
        "report_kind": "VALIDATION_REPORT",
        "layers": {"A": "schema_gate", "B1-B11": "rule validators"},
        "schema_gate": g3,
        "schema_gate_direct": {
            "consumed_from": "schema_gate.validate_master (ok, errors)",
            "ok": bool(schema_ok),
            "error_count": len(schema_errors),
            "errors": schema_errors,
        },
        "rules": g4,
        "summary": {
            "result": "FAIL" if total_errors else "PASS",
            "total_errors": total_errors,
            "schema_errors": len(schema_errors),
            "rule_errors": g4.get("error_count", 0),
            "schema_severity_counts": _count_by_severity(
                g3.get("finding_references")),
            "rule_severity_counts": _count_by_severity(
                g4.get("finding_references")),
            "reinterpreted": False,
            "softened": False,
        },
        "g3_carrier_note": (
            "the G3 carrier refs arrived empty (a known Phase 01 carrier "
            "gap: schema errors are strings, not Findings) — the interface "
            "therefore reports schema_gate_direct alongside them"
            if (g3_carrier_empty and schema_errors) else
            "carried refs are reported verbatim; schema_gate_direct carries "
            "the schema gate's own boolean verdict"),
        "note": "verdicts are carried as issued; ownership stays with "
                "schema_gate and the B-series validators",
    }


def readiness(master):
    """Final-approval readiness: A's gate plus B7's integrity view."""
    SG = _schema()
    import validate_blocking as B7
    ready, blockers = SG.final_approval_readiness(master)
    b7_report = B7.readiness_report(master)
    return {
        "report_kind": "READINESS_REPORT",
        "ready_for_final_approval": bool(ready and b7_report.get(
            "ready_for_final_approval")),
        "final_approval_gate": {
            "ready": bool(ready),
            "blockers": list(blockers),
            "blocker_count": len(blockers),
            "computed_by": "schema_gate.final_approval_readiness",
        },
        "blocking_integrity": b7_report,
        "note": "ready=false is a legitimate result, not a failure. "
                "Blockers are declared in full and never bypassed.",
    }


# ---------------------------------------------------------------------------
# Status dashboard (a reader — it issues no verdict of its own)
# ---------------------------------------------------------------------------

def _register_list(master, key):
    regs = (master or {}).get("registers") or {}
    items = regs.get(key) or []
    return items if isinstance(items, list) else []


def project_status(master):
    """A read-only dashboard over the master. Issues no verdicts.

    Readiness verdicts inside are consumed from `readiness()` and labelled
    with their producer.
    """
    master = master or {}
    meta = master.get("meta") or {}
    unknowns = _register_list(master, "unknowns")
    assumptions = _register_list(master, "assumptions")
    proposals = _register_list(master, "proposals")
    decisions = _register_list(master, "decisions")
    crs = _register_list(master, "change_requests")
    objections = _register_list(master, "objections")
    changelog = _register_list(master, "changelog")
    outputs = master.get("outputs") or []

    blocking_unknowns = [u for u in unknowns if u.get("blocking") is True]
    open_crs = [c for c in crs if c.get("state") not in CR_SETTLED]
    open_objections = [o for o in objections
                       if o.get("state") not in OBJ_SETTLED]

    try:
        ready = readiness(master)
    except Exception as exc:  # readiness needs jsonschema; report honestly
        ready = {"report_kind": "READINESS_REPORT",
                 "ready_for_final_approval": None,
                 "error": "%s: %s" % (type(exc).__name__, exc)}

    presence = master.get("presence_register") or {}
    presence_states = {k: (v or {}).get("presence") for k, v in presence.items()
                       if isinstance(v, dict)}

    return {
        "report_kind": "PROJECT_STATUS",
        "meta": {
            "project_id": meta.get("project_id"),
            "project_name": meta.get("project_name"),
            "revision": meta.get("master_revision") or meta.get("revision"),
            "geometry_version": meta.get("geometry_version"),
            "status": meta.get("status"),
            "track": meta.get("track"),
            "units": meta.get("units"),
            "is_test_project": meta.get("is_test_project"),
        },
        "counts": {
            "walls": len(master.get("walls") or []),
            "openings": len(master.get("openings") or []),
            "columns": len(master.get("columns") or []),
            "zones": len(master.get("zones") or []),
            "furniture": len(master.get("furniture") or []),
            "materials": len(master.get("materials") or []),
            "cameras": len(master.get("cameras") or []),
            "outputs": len(outputs),
        },
        "registers": {
            "unknowns_total": len(unknowns),
            "unknowns_blocking": len(blocking_unknowns),
            "unknowns": [{"id": u.get("id"), "question": u.get("question"),
                          "blocking": u.get("blocking")}
                         for u in unknowns],
            "assumptions_total": len(assumptions),
            "assumptions_pending": len(
                [a for a in assumptions
                 if a.get("approval_state") != "APPROVED"]),
            "proposals_total": len(proposals),
            "decisions_total": len(decisions),
            "change_requests_open": len(open_crs),
            "objections_open": len(open_objections),
        },
        "presence_register": presence_states,
        "readiness": {
            "ready_for_final_approval": ready.get("ready_for_final_approval"),
            "blockers": (ready.get("final_approval_gate") or {}).get(
                "blockers", []),
            "computed_by": "schema_gate.final_approval_readiness via "
                           "ida_api.readiness",
        },
        "changelog_tail": changelog[-5:] if changelog else [],
    }


# ---------------------------------------------------------------------------
# Generation — Class A floor plan (C1 gate + C3 emitter)
# ---------------------------------------------------------------------------

def _verdicts_from_validation(validation_report):
    """Adapt carried ERROR findings into C1 OwnerVerdicts.

    Scope is honestly None (UNPROVEN_SCOPE): the current engines do not
    produce a structured scope, and guessing one is forbidden. The result
    is fail-closed by construction — documented, not hidden.
    """
    import c1_preconditions as C1
    verdicts = []
    # The schema gate's own rejection (see validate_all's interface
    # completion note). A schema failure IS an ERROR by the engine's own
    # definition ("each returns a hard error") — carrying it as such is
    # consumption, not re-grading.
    direct = (validation_report or {}).get("schema_gate_direct") or {}
    for err in direct.get("errors") or []:
        verdicts.append(C1.OwnerVerdict(
            rule="A/SCHEMA", severity="ERROR", layer="A",
            message=str(err)[:300], scope=None))
    g3 = (validation_report or {}).get("schema_gate") or {}
    for ref in g3.get("finding_references") or []:
        if ref.get("severity") != "ERROR":
            continue
        verdicts.append(C1.OwnerVerdict(
            rule=str(ref.get("rule") or "A/SCHEMA"),
            severity="ERROR", layer="A",
            message=str(ref.get("message") or ref.get("location") or ""),
            scope=None))
    g4 = (validation_report or {}).get("rules") or {}
    for ref in g4.get("finding_references") or []:
        if ref.get("severity") != "ERROR":
            continue
        verdicts.append(C1.OwnerVerdict(
            rule=str(ref.get("rule") or "UNKNOWN"),
            severity="ERROR", layer=str(ref.get("layer") or "?"),
            message=str(ref.get("message") or ""),
            scope=None))
    return verdicts


def _decision_to_dict(decision):
    return {
        "output_id": decision.output_id,
        "class": decision.cls,
        "decision": decision.decision,
        "allowed": bool(decision.allowed),
        "reasons": [{"code": r.code, "message": r.message,
                     "source_layer": r.source_layer,
                     "scope_basis": r.scope_basis, "affected": r.affected,
                     "lift": r.lift} for r in decision.reasons],
    }


def gate_plan(master, output_id="PLAN-01", validation_report=None):
    """C1: may the Class A floor plan be generated? Never generates.

    Feeds the gate with (a) carried owner ERRORs from validation (run when
    not supplied), (b) the B7 uncertainty map consumed verbatim, and
    (c) the svg capability. Returns the decision as a JSON-safe dict.
    """
    import c1_preconditions as C1
    import validate_blocking as B7
    if validation_report is None:
        validation_report = validate_all(master)
    verdicts = _verdicts_from_validation(validation_report)
    try:
        uncertainty = B7.build_uncertainty_map(master)
    except Exception:
        uncertainty = {}
    req = C1.OutputRequest(
        output_id, C1.CLASS_A, view_type="floor-plan/tier-0+1",
        requires_paths=("space/outline",),
        shared_geometry=("space/outline",),
        requires_camera=False, requires_capability="svg")
    decision = C1.evaluate_request(
        master, req, verdicts, capabilities={"svg": True},
        uncertainty=uncertainty)
    record = _decision_to_dict(decision)
    record["abstention_text"] = C1.abstention_report([decision])
    record["inputs"] = {
        "owner_error_verdicts": len(verdicts),
        "uncertainty_paths": sorted(uncertainty.keys())
        if isinstance(uncertainty, dict) else [],
        "capabilities": {"svg": True},
        "note": "owner verdicts carry no structured scope, so every ERROR "
                "blocks conservatively as UNPROVEN_SCOPE (fail-closed, "
                "declared — never a claim that the model is invalid)",
    }
    return record


def generate_plan(master, output_id="PLAN-01", output_view="FloorPlan",
                  run_fidelity=True, skip_gate=False):
    """Generate the Class A floor plan SVG (Tier 0 + Tier 1).

    Steps: C1 gate (unless skipped explicitly) -> C3 emit -> evidence pack
    -> environment evidence -> D fidelity assessment. Returns a bundle dict
    with `svg`, `assembly`, `evidence`, `fidelity`, `gate` and `identity`.

    Raises Abstained when the C1 gate or the C3 emitter refuses. The SVG
    text is returned EXACTLY as emitted — never post-processed, because any
    added element would sit outside the fidelity-measured contract.
    """
    import c1_preconditions as C1
    import c3_svg_emitter as EM
    import c2_environment as ENV
    import d_report as D

    gate = None
    if not skip_gate:
        gate = gate_plan(master, output_id)
        if not gate.get("allowed"):
            raise Abstained(
                "C1 abstained for '%s': %s" % (
                    output_id,
                    "; ".join(r["code"] + " @ " + str(r["affected"])
                              for r in gate["reasons"]) or "no reason given"),
                record={"gate": gate})

    identity = WS.identity_of(master)
    record = EM.emit_svg(master, identity=identity)
    if record.get("status") != "EMITTED" or not record.get("svg"):
        abs_info = record.get("abstention") or {}
        raise Abstained(
            "C3 abstained for '%s': %s" % (
                output_id, abs_info.get("message") or abs_info.get("code")
                or "emitter refused"),
            record={"gate": gate, "emission": {
                "status": record.get("status"),
                "abstention": abs_info}})

    env = ENV.capture_environment()
    bundle = {
        "bundle_kind": "CLASS_A_PLAN_BUNDLE",
        "output_id": output_id,
        "class": "A",
        "view": output_view,
        "identity": identity,
        "gate": gate,
        "gate_skipped": bool(skip_gate),
        "status": record.get("status"),
        "svg": record.get("svg"),
        "assembly": record.get("assembly"),
        "capability": record.get("capability"),
        "determinism": record.get("determinism"),
        "engineering_fingerprint": record.get("engineering_fingerprint"),
        "evidence": EM.evidence_pack(record, environment=env),
        "environment": env,
        "notices": [
            "SVG text is exactly as emitted by C3 — never post-processed.",
            "Fidelity is judged by D against the GA assembly, not by "
            "provenance and not by element counts.",
            "DESIGN INTENT — NOT FOR CONSTRUCTION.",
        ],
    }
    if run_fidelity:
        bundle["fidelity"] = D.assess(
            record.get("assembly"), record.get("svg"), output_class="A")
    else:
        bundle["fidelity"] = {"verdict": "NOT_ASSESSED",
                              "reason": "fidelity assessment was not requested"}
    return bundle


# ---------------------------------------------------------------------------
# Quantities (C4), Presentation (C5), Manifest (C6), Fidelity (D)
# ---------------------------------------------------------------------------

def build_quantities(master, c1_allows=True):
    """C4: external derived quantity schedule (Q-01..Q-04)."""
    import c4_quantities as Q
    return Q.build_schedule(master, c1_allows=c1_allows)


def present_class_b(ga_artifact, parameters=None, identity=None,
                    declared_by="caller"):
    """C5: Class B presentation SVG from the GA assembly of the A path.

    `ga_artifact` MUST be bundle['assembly'] from `generate_plan` — C5 never
    re-assembles and never reads the master.
    """
    import c5_presentation as C5
    return C5.emit_class_b(ga_artifact, parameters=parameters,
                           identity=identity, declared_by=declared_by)


def assess_fidelity(ga_artifact, svg_text, output_class="A", output_status=None):
    """D: assess one output against the GA artifact it claims to represent."""
    import d_report as D
    return D.assess(ga_artifact, svg_text, output_class=output_class,
                    output_status=output_status)


def assess_pair(ga_artifact, a_svg, b_svg):
    """D: assess A and B, each directly against GA (never B against A)."""
    import d_report as D
    return D.assess_pair(ga_artifact, a_svg, b_svg)


def assemble_manifest(records, identity=None, environment=None):
    """C6: assemble an external evidence manifest over producer records.

    `records` is a list of (owner, record) pairs, e.g. ("C3", a_record).
    The manifest preserves, counts and compares mechanically — it issues
    no verdict of any kind.
    """
    import c6_manifest as C6
    return C6.assemble_manifest(records, identity=identity,
                                environment_evidence=environment)


def environment_evidence():
    """C2: capture the execution environment honestly (NOT_SET, never guessed)."""
    import c2_environment as ENV
    return {"environment": ENV.capture_environment(),
            "env_fingerprint": ENV.env_fingerprint(),
            "note": "ENV-FP is contextual evidence. Different ENV-FP is not "
                    "proof of a different engineering result; same ENV-FP is "
                    "not proof of correctness. The fidelity verdict is D's."}


def existing_state(master):
    """Phase 01 SA Unit 1 (O-1): existing-state analysis.

    Analytical evidence — not Class A, not engineering truth, not a
    geometry source. Unknowns are shown AS unknowns.
    """
    import sa_existing_state as SA
    return SA.analyse_existing_state(master)


# ---------------------------------------------------------------------------
# Governance — proposals, decisions, objections, change requests
#
# Entry shapes below are EXACTLY the schema's (proposal_entry,
# decision_entry, cr_entry, objection_entry, changelog_entry): required
# fields, enums and length minima are enforced at the boundary so the
# interface can never write a register entry the schema would reject.
# State field is `state` (not `status`) per the schema; B10 owns the
# lifecycle coherence of these states.
# ---------------------------------------------------------------------------

# Schema state enums (consumed, never extended).
PROP_OPEN = "OPEN"
PROP_APPROVED = "APPROVED"
CR_PENDING = "PENDING_APPROVAL"
CR_DRAFT = "DRAFT"
CR_APPROVED = "APPROVED"
CR_APPLIED = "APPLIED"
CR_REJECTED = "REJECTED"
CR_SETTLED = ("APPLIED", "REJECTED")
OBJ_OPEN = "OPEN"
OBJ_SETTLED = ("WITHDRAWN", "USER_OVERRIDE", "ACCEPTED")


def _next_id(prefix, entries, field="id"):
    nums = []
    for entry in entries or []:
        raw = str((entry or {}).get(field) or "")
        if raw.startswith(prefix + "-"):
            try:
                nums.append(int(raw.split("-")[1]))
            except (ValueError, IndexError):
                pass
    return "%s-%03d" % (prefix, (max(nums) if nums else 0) + 1)


def _require_user(actor):
    if actor != "USER":
        raise GovernanceError(
            "approval authority belongs to the USER alone; "
            "actor '%s' cannot approve" % actor)


def _require_text(name, value, minimum):
    text = str(value or "")
    if len(text.strip()) < minimum:
        raise GovernanceError(
            "%s needs at least %d characters (schema minimum); refusing "
            "to write an entry the schema would reject" % (name, minimum))
    return value


def record_proposal(master, text, raised_on=None):
    """Register a [P] proposal (state OPEN). A proposal is never a decision.

    Returns (master, entry). Promotion happens only via `record_decision`
    with explicit USER approval, which flips the proposal to APPROVED and
    links it back to the decision.
    """
    _require_text("proposal text", text, 5)
    master = master or {}
    regs = master.setdefault("registers", {})
    proposals = regs.setdefault("proposals", [])
    entry = {
        "id": _next_id("P", proposals),
        "text": text,
        "state": PROP_OPEN,
        "raised_on": raised_on or WS.utc_today(),
    }
    proposals.append(entry)
    return master, entry


def record_decision(master, title, linked_proposal, rationale,
                    alternatives_considered=None, linked_elements=None,
                    actor="USER", approved_on=None, approved_in_revision=None,
                    user_override_of=None):
    """Record a USER decision with its full Decision Record.

    The schema REQUIRES every decision to rest on a proposal, so
    linked_proposal is mandatory and must name an OPEN proposal — a
    decision on a settled or missing proposal is refused (B10 RL-001/002
    own this coherence rule; the interface refuses to write the violation
    in the first place). Rationale documents WHY (schema minimum 10 chars).
    No implicit approval: this function must be CALLED explicitly — nothing
    in the pipeline calls it.
    """
    _require_user(actor)
    _require_text("decision title", title, 3)
    _require_text("decision rationale", rationale, 10)
    if not approved_on:
        raise GovernanceError("approved_on is mandatory for a decision")
    if not approved_in_revision:
        raise GovernanceError("approved_in_revision is mandatory for a "
                              "decision")
    master = master or {}
    regs = master.setdefault("registers", {})
    decisions = regs.setdefault("decisions", [])
    proposals = {str(p.get("id")): p
                 for p in regs.get("proposals", []) or []}
    prop = proposals.get(str(linked_proposal))
    if prop is None:
        raise GovernanceError(
            "linked proposal '%s' does not exist in registers.proposals" %
            linked_proposal)
    if prop.get("state") != PROP_OPEN:
        raise GovernanceError(
            "proposal '%s' is %s, not OPEN — a decision cannot rest on a "
            "settled proposal" % (linked_proposal, prop.get("state")))
    entry = {
        "decision_id": _next_id("DEC", decisions, field="decision_id"),
        "title": title,
        "linked_proposal": str(linked_proposal),
        "rationale": rationale,
        "alternatives_considered": list(alternatives_considered or []),
        "approved_by": "USER",
        "approved_on": approved_on,
        "approved_in_revision": approved_in_revision,
    }
    if linked_elements:
        entry["linked_elements"] = list(linked_elements)
    if user_override_of:
        entry["user_override_of"] = user_override_of
    decisions.append(entry)
    # Link back: the proposal now points at its decision (B1 XR-011 owns
    # the bidirectional integrity of this link).
    prop["state"] = PROP_APPROVED
    prop["decision_id"] = entry["decision_id"]
    return master, entry


def record_objection(master, decision_under_objection, problem, impact,
                     alternative, raised_on=None):
    """Raise a professional objection (OBJ-xxx, state OPEN).

    NOTE (B10 RL-003): an OPEN objection that names a standing decision is
    itself a lifecycle ERROR until it is resolved, withdrawn, accepted or
    explicitly overridden — that is the point of an objection, not a bug.
    Objections are never deleted; settlement changes `state`, keeping the
    objection visible in history.
    """
    _require_text("decision_under_objection", decision_under_objection, 3)
    _require_text("objection problem", problem, 10)
    _require_text("objection impact", impact, 5)
    _require_text("objection alternative", alternative, 5)
    master = master or {}
    regs = master.setdefault("registers", {})
    objections = regs.setdefault("objections", [])
    entry = {
        "id": _next_id("OBJ", objections),
        "decision_under_objection": decision_under_objection,
        "problem": problem,
        "impact": impact,
        "alternative": alternative,
        "state": OBJ_OPEN,
        "raised_on": raised_on or WS.utc_today(),
    }
    objections.append(entry)
    return master, entry


def record_change_request(master, target_element, current_value,
                          proposed_value, reason, impact,
                          classification="MINOR", alternatives=None,
                          raised_on=None):
    """Open a Change Request for a confirmed element (state PENDING_APPROVAL).

    MINOR and MAJOR alike wait for USER approval. No Auto-Apply: nothing
    in this module applies a CR implicitly — application happens only via
    `apply_approved_change` with an APPROVED CR.
    """
    _require_text("target_element", target_element, 2)
    _require_text("CR reason", reason, 5)
    _require_text("CR impact", impact, 5)
    if classification not in ("MINOR", "MAJOR"):
        raise GovernanceError(
            "CR classification must be MINOR or MAJOR (schema enum); "
            "got '%s'" % classification)
    master = master or {}
    regs = master.setdefault("registers", {})
    crs = regs.setdefault("change_requests", [])
    entry = {
        "id": _next_id("CR", crs),
        "target_element": target_element,
        "current_value": current_value,
        "proposed_value": proposed_value,
        "reason": reason,
        "impact": impact,
        "classification": classification,
        "state": CR_PENDING,
        "raised_on": raised_on or WS.utc_today(),
    }
    if alternatives:
        entry["alternatives"] = list(alternatives)
    crs.append(entry)
    return master, entry


def approve_change_request(master, cr_id, actor="USER", approved_on=None):
    """Approve a CR awaiting approval (DRAFT or PENDING_APPROVAL -> APPROVED).

    USER only, explicit call only. The schema carries no approved_by field
    on a CR, so authorship is enforced at call time (non-USER actors are
    refused) rather than persisted — see GAP-02.
    """
    _require_user(actor)
    if not approved_on:
        raise GovernanceError("approved_on is mandatory to approve a CR")
    master = master or {}
    for cr in _register_list(master, "change_requests"):
        if str(cr.get("id")) == str(cr_id):
            if cr.get("state") not in (CR_DRAFT, CR_PENDING):
                raise GovernanceError(
                    "CR '%s' is %s; only a DRAFT or PENDING_APPROVAL CR can "
                    "be approved" % (cr_id, cr.get("state")))
            cr["state"] = CR_APPROVED
            cr["approved_on"] = approved_on
            return master, cr
    raise GovernanceError("CR '%s' not found" % cr_id)


def _resolve_container(master, path):
    """Resolve 'a/b/0/c' to (container, key). Lists addressable by index."""
    parts = [p for p in str(path).split("/") if p != ""]
    if not parts:
        raise GovernanceError("empty path")
    node = master
    for part in parts[:-1]:
        if isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                raise GovernanceError("path '%s' does not resolve" % path)
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise GovernanceError("path '%s' does not resolve" % path)
    last = parts[-1]
    if isinstance(node, list):
        try:
            return node, int(last)
        except ValueError:
            raise GovernanceError("path '%s' does not resolve" % path)
    if isinstance(node, dict):
        return node, last
    raise GovernanceError("path '%s' does not resolve" % path)


def apply_approved_change(master, cr_id, path, new_fact,
                          applied_in_revision=None):
    """Apply an APPROVED CR to one master path. The ONLY writer of [C] facts.

    Requires: the CR exists, is APPROVED, and carries approved_on (approval
    authorship is enforced at approve-time — non-USER actors are refused —
    because the schema carries no approved_by on a CR; see GAP-02). The new
    fact must be a tagged fact (status + source_type + source_ref +
    recorded_on); a [C] fact additionally requires a USER-backed source
    (CLIENT_INPUT or USER_APPROVAL). The CR flips to APPLIED with
    applied_in_revision, and a CR_APPLIED changelog entry records cr_id
    (B10 RL-006 forbids an APPLIED CR with no changelog event, and B9 CR2
    requires cr_id on the entry). Anything else raises GovernanceError.
    Returns (master, applied_record).
    """
    master = master or {}
    cr = None
    for item in _register_list(master, "change_requests"):
        if str(item.get("id")) == str(cr_id):
            cr = item
            break
    if cr is None:
        raise GovernanceError("CR '%s' not found" % cr_id)
    if cr.get("state") != CR_APPROVED:
        raise GovernanceError(
            "CR '%s' is %s, not APPROVED; No Auto-Apply — an unapproved CR "
            "changes nothing" % (cr_id, cr.get("state")))
    if not cr.get("approved_on"):
        raise GovernanceError(
            "CR '%s' lacks an approval record; refusing to apply" % cr_id)

    if not isinstance(new_fact, dict):
        raise GovernanceError("new_fact must be a tagged fact object")
    for field in ("status", "source_type", "source_ref", "recorded_on"):
        if field not in new_fact:
            raise GovernanceError(
                "new_fact misses '%s': no value without status and source" %
                field)
    if new_fact.get("status") == "C" and new_fact.get("source_type") not in (
            "CLIENT_INPUT", "USER_APPROVAL"):
        raise GovernanceError(
            "[C] facts come only from CLIENT_INPUT or USER_APPROVAL; "
            "got '%s'" % new_fact.get("source_type"))
    if new_fact.get("status") == "C" and new_fact.get(
            "source_type") == "USER_APPROVAL":
        # RULES.md 4 / schema F3: approval-sourced [C] needs its full
        # Decision Record. Refused at the boundary so the interface can
        # never write a fact the schema would reject.
        for field in ("decision_id", "approved_by", "approved_on",
                      "approved_in_revision"):
            if field not in new_fact:
                raise GovernanceError(
                    "a [C]/USER_APPROVAL fact needs '%s' (full Decision "
                    "Record); refusing to write a fact the schema would "
                    "reject" % field)
        if new_fact.get("approved_by") != "USER":
            raise GovernanceError("approved_by accepts USER only")

    container, key = _resolve_container(master, path)
    old = container[key] if (
        isinstance(container, list) and 0 <= key < len(container)
    ) else container.get(key)
    container[key] = copy.deepcopy(new_fact)

    meta = master.get("meta") or {}
    revision = (applied_in_revision
                or meta.get("master_revision") or meta.get("revision"))
    cr["state"] = CR_APPLIED
    cr["applied_in_revision"] = revision

    changelog = master.setdefault("registers", {}).setdefault("changelog", [])
    changelog.append({
        "revision": revision,
        "date": WS.utc_today(),
        "type": "CR_APPLIED",
        "summary": "CR %s applied to %s" % (cr_id, path),
        "cr_id": cr_id,
    })
    return master, {"cr_id": cr_id, "path": path,
                    "previous": copy.deepcopy(old),
                    "applied": copy.deepcopy(new_fact)}


# ---------------------------------------------------------------------------
# Captions — the language policy as a reusable interface
# ---------------------------------------------------------------------------

def caption_for(cls, view_name, revision, extra=""):
    """Build the approved guarantee caption for an output of class A/B/C.

    Returns {"caption": ..., "problems": [...]}. Class C captions are linted:
    match/100% language is forbidden there and reported as problems.
    """
    SG = _schema()
    templates = {
        "A": "Class A — DESIGN-ACCURATE. Deterministic geometric match to "
             "Design Master %s — testable." % revision,
        "B": "Class B — PRESENTATION VISUAL. Geometry deterministically "
             "derived from Design Master %s; visual treatment may differ. "
             "Not a substitute for Class A." % revision,
        "C": "Class C — AI MOOD. Not geometrically guaranteed. Non-binding "
             "inspiration only — never a geometric source.",
    }
    base = templates.get(cls, "Unclassified output — no guarantee stated.")
    caption = "%s — %s" % (view_name, base) if view_name else base
    if extra:
        caption = "%s %s" % (caption, extra)
    return {"caption": caption,
            "problems": SG.lint_caption(cls, caption)}
