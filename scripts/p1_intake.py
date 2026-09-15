#!/usr/bin/env python3
"""
PHASE 01 — G1 · INTAKE COMPLETENESS

Reference (APPROVED / LOCKED):
  PHASE-01-ARCHITECTURE-SPECIFICATION-R01.md
  PHASE-01-ARCHITECTURE-SPECIFICATION-R02-DELTA.md
  PHASE-01-R02-FINAL-AMENDMENT-A01.md

WHAT G1 DOES
  Reads the intake answers and decides one thing only: may population begin?

THE CLASSIFICATION RULE (A-01 + Final Amendment)
  G1 blocks ONLY when a field that is EXPLICITLY DECLARED blocking is
  missing. Everything else follows from the source's own classification:

      BLOCKING declared + missing      -> ABSTAIN, no population
      NON-BLOCKING declared + missing  -> population continues, field is [U]
      UNCLASSIFIED                     -> UNRESOLVED_CLASSIFICATION

  UNCLASSIFIED is neither blocking nor non-blocking. Phase 01 infers neither
  (G1-6.2), records the gap explicitly (G1-6.4), never uses it as evidence of
  readiness (G1-6.6), and never hides it.

  [U] is not an error and not a failure (G1-3).

WHAT G1 NEVER DOES
  It does not invent a classification (G1-6.5), does not re-implement B7's
  logic (G1-5), and does not create a new mechanism for deciding what is
  blocking (G1-6.7). The classification source stays exactly where it is.
"""

# --- classification vocabulary --------------------------------------------
BLOCKING = "BLOCKING"
NON_BLOCKING = "NON_BLOCKING"
UNCLASSIFIED = "UNCLASSIFIED"

# --- G1 verdicts -----------------------------------------------------------
PROCEED = "PROCEED"
ABSTAIN = "ABSTAIN"

# --- record codes ----------------------------------------------------------
MISSING_BLOCKING = "G1-MISSING-BLOCKING"
MISSING_NON_BLOCKING = "G1-MISSING-NON-BLOCKING"
UNRESOLVED_CLASSIFICATION = "UNRESOLVED_CLASSIFICATION"

UNKNOWN_TOKEN = "U"


def _is_supplied(value):
    """A field counts as supplied only when it carries real content.

    Empty string, None and whitespace are ABSENT — never silently treated as
    an answer.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def classify_field(spec):
    """Read the declared classification. Never infer one.

    The spec is whatever the intake contract supplies. If it does not declare
    a classification, the answer is UNCLASSIFIED — not NON_BLOCKING.
    """
    declared = (spec or {}).get("classification")
    if declared == BLOCKING:
        return BLOCKING
    if declared == NON_BLOCKING:
        return NON_BLOCKING
    return UNCLASSIFIED


def evaluate_intake(intake_answers, field_specs):
    """G1: may population begin?

    `field_specs` is a list of {field, classification} as DECLARED by the
    intake contract. `intake_answers` maps field -> value.

    Returns a record describing every absent field by its declared class,
    plus the G1 verdict. Nothing is inferred and nothing is hidden.
    """
    answers = intake_answers if isinstance(intake_answers, dict) else {}

    missing_blocking = []
    missing_non_blocking = []
    unresolved_classification = []
    supplied = []

    for spec in (field_specs or []):
        field = (spec or {}).get("field")
        if not field:
            continue
        cls = classify_field(spec)
        present = _is_supplied(answers.get(field))

        if cls == UNCLASSIFIED:
            # Recorded whether present or absent: the GAP is the missing
            # classification itself, not the missing value (G1-6.4).
            unresolved_classification.append({
                "field": field,
                "code": UNRESOLVED_CLASSIFICATION,
                "value_supplied": present,
                "reason": ("the intake contract declares no classification "
                           "for this field. Phase 01 does not infer BLOCKING "
                           "and does not infer NON_BLOCKING."),
                "counts_as_readiness_evidence": False,
            })
            if present:
                supplied.append(field)
            continue

        if present:
            supplied.append(field)
            continue

        if cls == BLOCKING:
            missing_blocking.append({
                "field": field, "code": MISSING_BLOCKING,
                "classification": BLOCKING,
                "reason": "a field declared BLOCKING is absent"})
        else:
            missing_non_blocking.append({
                "field": field, "code": MISSING_NON_BLOCKING,
                "classification": NON_BLOCKING,
                "reason": ("a field declared NON_BLOCKING is absent; it "
                           "enters the master as [U] and is registered"),
                "enters_master_as": UNKNOWN_TOKEN})

    verdict = ABSTAIN if missing_blocking else PROCEED

    return {
        "gate": "G1",
        "verdict": verdict,
        "supplied_fields": supplied,
        "missing_blocking": missing_blocking,
        "missing_non_blocking": missing_non_blocking,
        "unresolved_classification": unresolved_classification,
        "abstention_reason": (
            f"{len(missing_blocking)} field(s) declared BLOCKING are absent; "
            f"population does not begin"
            if missing_blocking else None),
        "notes": [
            "[U] is not an error and not a failure",
            "UNCLASSIFIED is neither BLOCKING nor NON_BLOCKING",
            "Phase 01 consumes the declared classification and never "
            "invents one",
            "unresolved classifications are never evidence of readiness and "
            "are never dropped from the record",
        ],
    }
