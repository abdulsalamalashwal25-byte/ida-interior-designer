#!/usr/bin/env python3
"""
PHASE 01 — PIPELINE  ·  INTAKE -> VALIDATED PROJECT MASTER

Runs the five approved gates in order and enforces the approved lifecycle.

    NOT_STARTED
       -> INTAKE_RECEIVED
       -> MASTER_POPULATED
       -> VALIDATED
       -> READY_DECLARED        (ready=True)
          or BLOCKED_DECLARED   (ready=False)

    INTAKE_RECEIVED -> INTAKE_INCOMPLETE -> ABSTAINED   (blocking field absent)

NO IMPLICIT TRANSITIONS. Every state is reached by a gate that ran.

WHAT THIS LAYER IS NOT
  not a designer · not an engineering judge · not a generator · not an
  approval authority. It builds a master from intake, has it validated by the
  owning layers, and declares readiness within its own scope.

It writes no file: the populated master is RETURNED. Persisting it, approving
it, generating from it and judging it belong elsewhere.
"""

from p1_intake import evaluate_intake, ABSTAIN as G1_ABSTAIN
from p1_populate import populate, PopulationError
from p1_validate import run_schema_gate, run_rule_validators, FAIL
from p1_readiness import declare_readiness

# --- lifecycle states ------------------------------------------------------
NOT_STARTED = "NOT_STARTED"
INTAKE_RECEIVED = "INTAKE_RECEIVED"
INTAKE_INCOMPLETE = "INTAKE_INCOMPLETE"
ABSTAINED = "ABSTAINED"
MASTER_POPULATED = "MASTER_POPULATED"
VALIDATED = "VALIDATED"
VALIDATION_FAILED = "VALIDATION_FAILED"
READY_DECLARED = "READY_DECLARED"
BLOCKED_DECLARED = "BLOCKED_DECLARED"

TERMINAL_STATES = (ABSTAINED, READY_DECLARED, BLOCKED_DECLARED,
                   VALIDATION_FAILED)

# VALIDATED means only this — and never any of the rest.
VALIDATED_MEANS = ("the checks required within Phase 01 scope passed: "
                   "A + B1-B11 with no ERROR")
VALIDATED_DOES_NOT_MEAN = (
    "design ready",
    "generation ready",
    "user approved",
    "E approved",
    "engineering correct",
    "fidelity verified",
    "final design approved",
)


def run_phase01(intake_answers, field_specs, recorded_on, template=None):
    """Run Phase 01 end to end. Returns (master_or_None, run_record)."""
    trace = [NOT_STARTED]
    record = {
        "phase": "01",
        "scope": "INTAKE -> VALIDATED PROJECT MASTER",
        "lifecycle_trace": trace,
        "gates": {},
        "master_written_to_disk": False,
        "validated_means": VALIDATED_MEANS,
        "validated_does_not_mean": list(VALIDATED_DOES_NOT_MEAN),
        "not_a_designer": True,
        "not_an_engineering_judge": True,
        "not_a_generator": True,
        "not_an_approval_authority": True,
    }

    # ---- G1 ---------------------------------------------------------------
    g1 = evaluate_intake(intake_answers, field_specs)
    record["gates"]["G1"] = g1
    trace.append(INTAKE_RECEIVED)

    if g1["verdict"] == G1_ABSTAIN:
        trace.append(INTAKE_INCOMPLETE)
        trace.append(ABSTAINED)
        record["state"] = ABSTAINED
        record["abstention_reason"] = g1["abstention_reason"]
        record["note"] = ("a field declared BLOCKING is absent; population "
                          "did not begin. This is an abstention, not a "
                          "partial build.")
        return None, record

    # ---- G2 ---------------------------------------------------------------
    try:
        master, g2 = populate(intake_answers, g1, recorded_on, template)
    except PopulationError as exc:
        trace.append(ABSTAINED)
        record["state"] = ABSTAINED
        record["abstention_reason"] = str(exc)
        return None, record

    record["gates"]["G2"] = g2
    trace.append(MASTER_POPULATED)

    # ---- G3 ---------------------------------------------------------------
    g3 = run_schema_gate(master)
    record["gates"]["G3"] = g3
    if g3["result"] == FAIL:
        trace.append(VALIDATION_FAILED)
        record["state"] = VALIDATION_FAILED
        record["note"] = ("schema validation reported ERROR(s). Phase 01 "
                          "stops and reports; it does not self-correct.")
        return master, record

    # ---- G4 ---------------------------------------------------------------
    g4 = run_rule_validators(master)
    record["gates"]["G4"] = g4
    if g4["result"] == FAIL:
        trace.append(VALIDATION_FAILED)
        record["state"] = VALIDATION_FAILED
        record["note"] = ("rule validation reported ERROR(s). Phase 01 stops "
                          "and reports; it does not modify a rule and does "
                          "not soften a verdict.")
        return master, record

    trace.append(VALIDATED)

    # ---- G5 ---------------------------------------------------------------
    g5 = declare_readiness(
        master, g1.get("unresolved_classification"))
    record["gates"]["G5"] = g5
    trace.append(g5["lifecycle_state"])
    record["state"] = g5["lifecycle_state"]
    record["ready"] = g5["ready"]
    record["note"] = ("readiness declared within Phase 01 scope. "
                      "ready=False is a legitimate result.")
    return master, record


def allowed_next(state):
    """The states legally reachable from here. Empty when terminal."""
    if state in TERMINAL_STATES:
        return []
    transitions = {
        NOT_STARTED: [INTAKE_RECEIVED],
        INTAKE_RECEIVED: [MASTER_POPULATED, INTAKE_INCOMPLETE],
        INTAKE_INCOMPLETE: [ABSTAINED],
        MASTER_POPULATED: [VALIDATED, VALIDATION_FAILED],
        VALIDATED: [READY_DECLARED, BLOCKED_DECLARED],
    }
    return transitions.get(state, [])
