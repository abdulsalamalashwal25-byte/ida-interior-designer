#!/usr/bin/env python3
"""
PHASE 01 — G5 · READINESS DECLARATION

Consumes schema_gate.final_approval_readiness and DECLARES the result.

WHAT ready=True MEANS (A-04) — and only this
  final_approval_readiness found no blocking condition WITHIN ITS OWN SCOPE.

WHAT IT DOES NOT MEAN
  user approval · E approval · final design approval · engineering
  certification · fidelity verification.

ready=False IS A LEGITIMATE, CORRECT RESULT — not a phase failure. The
failure mode here is hiding a blocking condition or stepping around it.

UNRESOLVED CLASSIFICATION (G1-6.6)
  An unresolved classification is never evidence of readiness. It is carried
  into the declaration so it stays visible.
"""

import schema_gate

READY_DECLARED = "READY_DECLARED"
BLOCKED_DECLARED = "BLOCKED_DECLARED"

READY_TRUE_MEANS = ("final_approval_readiness found no blocking condition "
                    "within its own scope")
READY_TRUE_DOES_NOT_MEAN = (
    "user approval",
    "E approval",
    "final design approval",
    "engineering certification",
    "fidelity verification",
)


def declare_readiness(master, unresolved_classification=None):
    """G5: consume the readiness gate and declare it. Nothing is recomputed."""
    ready, blockers = schema_gate.final_approval_readiness(master)
    unresolved = list(unresolved_classification or [])

    return {
        "gate": "G5",
        "ready": ready,
        "blockers": list(blockers),
        "blocker_count": len(blockers),
        "lifecycle_state": READY_DECLARED if ready else BLOCKED_DECLARED,
        "unresolved_classification": unresolved,
        "unresolved_classification_count": len(unresolved),
        "computed_by": "schema_gate.final_approval_readiness",
        "recomputed_by_phase01": False,
        "ready_true_means": READY_TRUE_MEANS,
        "ready_true_does_not_mean": list(READY_TRUE_DOES_NOT_MEAN),
        "is_phase_failure": False,
        "notes": [
            "ready=False is a correct and legitimate result, not a phase "
            "failure",
            "blocking conditions are declared in full and never hidden or "
            "bypassed",
            "an unresolved classification is never evidence of readiness",
        ],
    }
