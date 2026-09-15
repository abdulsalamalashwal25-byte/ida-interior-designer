#!/usr/bin/env python3
"""
00.5-F — REFERENCE USAGE PATH  (R03 Amendment 1)

Two paths lead out of Project Usage:

  PATH A — Reference Context
      Project Usage -> Reference Context
      Produces NO [P], NO [C], and NO design decision.
      It is a legitimate, COMPLETE end state — not a shortfall and not a
      temporary stage.

  PATH B — Decision-affecting
      Project Usage -> [P] Proposal -> USER Decision/Approval (via E) -> [C]

BINDING RULES
  UP-6  Reference usage does NOT create a [P] by itself.
  UP-7  Moving from path A to path B is an EXPLICIT act. It never happens
        through elapsed time or repeated citation.
  UP-8  F does not decide which path applies. Determining that a reference
        influenced a decision is an act OUTSIDE F.

  UP-1  Reference -> [D] directly            FORBIDDEN
  UP-2  External library -> [D] automatically FORBIDDEN
  UP-3  External standard -> [D] automatically FORBIDDEN
  UP-4  Reference -> [C] directly            FORBIDDEN
  UP-5  F -> promotion of any kind           FORBIDDEN

WHY F CANNOT MAKE A [D] — structural, not verbal
  B6 requires a [D] to carry `formula` and `derived_from`, otherwise it is an
  "undocumented derived value, lineage unverifiable" (FM-004). A [D] is the
  RESULT of a documented derivation governed by B6 — not a status granted to
  a value because it came from a library.
"""

# --- usage paths -----------------------------------------------------------
PATH_A_CONTEXT = "REFERENCE_CONTEXT"
PATH_B_DECISION_AFFECTING = "DECISION_AFFECTING"

USAGE_PATHS = (PATH_A_CONTEXT, PATH_B_DECISION_AFFECTING)

# --- project statuses. F may name them; F may never assign them. ----------
STATUS_P = "P"      # proposal — created only on path B, by an act outside F
STATUS_C = "C"      # confirmed — only USER approval via E
STATUS_D = "D"      # derived — B6 territory, never F

FORBIDDEN_FOR_F = (STATUS_C, STATUS_D)

ACCEPTED = "ACCEPTED"
REFUSED = "REFUSED"

# refusal codes
UP_NO_DERIVED = "UP-01"        # attempted Reference -> [D]
UP_NO_CONFIRMED = "UP-04"      # attempted Reference -> [C]
UP_NO_PROMOTION = "UP-05"      # attempted promotion by F
UP_NO_AUTO_PROPOSAL = "UP-06"  # attempted automatic [P] from mere usage
UP_NOT_F_DECISION = "UP-08"    # F asked to decide the path itself


class UsageError(RuntimeError):
    """Raised when F is asked to do something it must never do."""


def record_usage(attribute_ref, path, declared_by=None, rationale=None):
    """Record how a reference attribute is used in a project.

    `path` MUST be supplied by the caller. F never infers it: deciding that a
    reference influenced a decision is an act outside F (UP-8).
    """
    if path not in USAGE_PATHS:
        return {
            "result": REFUSED, "code": UP_NOT_F_DECISION,
            "reason": (f"usage path must be declared by the caller as one of "
                       f"{USAGE_PATHS}. F does not determine whether a "
                       f"reference influenced a decision."),
        }

    if path == PATH_A_CONTEXT:
        return {
            "result": ACCEPTED,
            "usage_path": PATH_A_CONTEXT,
            "attribute_ref": attribute_ref,
            "declared_by": declared_by,
            "rationale": rationale,
            "produces_proposal": False,
            "produces_confirmed": False,
            "produces_design_decision": False,
            "is_complete_end_state": True,
            "note": ("reference context only. This is a legitimate, complete "
                     "end state — not a shortfall and not a temporary stage "
                     "(UP-6)."),
        }

    # PATH B — F records that a proposal is REQUIRED. It does not make one.
    return {
        "result": ACCEPTED,
        "usage_path": PATH_B_DECISION_AFFECTING,
        "attribute_ref": attribute_ref,
        "declared_by": declared_by,
        "rationale": rationale,
        "proposal_required": True,
        "proposal_created_by_f": False,
        "next_step": "[P] Proposal -> USER Decision/Approval via E -> [C]",
        "note": ("F records that this usage affects a decision and therefore "
                 "requires a proposal. F does not create the proposal, does "
                 "not approve it, and does not confirm it."),
    }


def promote(attribute_ref, target_status):
    """Always refuses. F owns no promotion whatsoever (UP-1..UP-5)."""
    if target_status == STATUS_D:
        raise UsageError(
            f"{UP_NO_DERIVED}: F cannot create [D] and cannot grant a "
            f"reference eligibility to become [D]. A derived value requires "
            f"formula + derived_from and is governed by B6.")
    if target_status == STATUS_C:
        raise UsageError(
            f"{UP_NO_CONFIRMED}: F cannot create [C]. Confirmation follows "
            f"USER decision/approval through E.")
    raise UsageError(
        f"{UP_NO_PROMOTION}: F owns no promotion of any kind. Reference "
        f"status transitions belong to A/B7 and approval belongs to E.")


def auto_proposal_attempt(attribute_ref):
    """Refused: usage alone never yields a proposal (UP-6)."""
    return {
        "result": REFUSED, "code": UP_NO_AUTO_PROPOSAL,
        "reason": ("Reference Usage is not a Proposal automatically. A "
                   "proposal arises only when a caller declares the usage "
                   "decision-affecting (path B), which is an act outside F."),
    }


def path_transition(from_path, to_path, declared_by=None):
    """A -> B is an explicit act, never time-based or citation-count based."""
    if from_path == PATH_A_CONTEXT and to_path == PATH_B_DECISION_AFFECTING:
        if not declared_by:
            return {"result": REFUSED, "code": UP_NOT_F_DECISION,
                    "reason": ("moving from reference context to "
                               "decision-affecting requires an explicit "
                               "declaring actor outside F (UP-7).")}
        return {"result": ACCEPTED, "from": from_path, "to": to_path,
                "declared_by": declared_by,
                "note": "explicit act recorded; F did not infer it"}
    if from_path == to_path:
        return {"result": ACCEPTED, "from": from_path, "to": to_path,
                "note": "no change"}
    return {"result": REFUSED, "code": UP_NOT_F_DECISION,
            "reason": f"'{from_path}' -> '{to_path}' is not a recognised "
                      f"usage-path transition."}
