#!/usr/bin/env python3
"""
00.5-E — G-2 AUTHORIZATION GATE

The single point through which governance authority is read. Nothing else in
E may decide, on its own, that something is authorised (FCR-1).

WHAT THIS ENFORCES
  * only USER holds approval authority; AI/system/producer never do
  * an AI actor may not claim to be USER
  * governance transitions require the authority the contract names
  * decision recording is an explicit act with explicit references

WHAT THIS CANNOT ENFORCE — declared, not hidden
  CONFLICT-E-01 / GAP-02 remain OPEN. `approved_by = "USER"` prevents
  free-text impersonation, but nothing inside a file can prove a real human
  actually approved. Assurance is therefore DECLARED_ONLY, and this module
  never reports otherwise.

FUTURE-CHANNEL READINESS (FCR-E-01)
  FCR-1 authority is read here and only here.
  FCR-2 approval is stored as a reference, never derived from another field.
  FCR-3 `approval_assurance` is an explicit field; adding an external channel
        later raises it without restructuring E.
"""

# --- actors ----------------------------------------------------------------
ACTOR_USER = "USER"
ACTOR_E = "E"
ACTOR_AI = "AI"
ACTOR_SYSTEM = "SYSTEM"
ACTOR_PRODUCER = "PRODUCER"

# Only these may ever appear as approval authority.
APPROVAL_AUTHORITIES = (ACTOR_USER,)

# Actors that may never be recorded as an approver, under any circumstance.
NON_APPROVING_ACTORS = (ACTOR_AI, ACTOR_SYSTEM, ACTOR_PRODUCER, ACTOR_E)

# Assurance levels. V1 can only ever declare the weakest one honestly.
ASSURANCE_DECLARED_ONLY = "DECLARED_ONLY"
ASSURANCE_LEVELS = (ASSURANCE_DECLARED_ONLY,)

GRANTED = "GRANTED"
REFUSED = "REFUSED"

# Refusal codes
AUTH_NOT_USER = "AUTH-01"          # actor is not USER
AUTH_IMPERSONATION = "AUTH-02"     # a non-approving actor claimed USER
AUTH_WRONG_AUTHORITY = "AUTH-03"   # transition requires a different authority
AUTH_MISSING_REFS = "AUTH-04"      # explicit references absent
AUTH_INELIGIBLE = "AUTH-05"        # target entity is not eligible


class AuthorityDecision:
    """The result of asking the gate. Carries its own honesty caveat."""

    __slots__ = ("granted", "code", "reason", "actor", "assurance")

    def __init__(self, granted, actor, code=None, reason=None):
        self.granted = granted
        self.actor = actor
        self.code = code
        self.reason = reason
        self.assurance = ASSURANCE_DECLARED_ONLY

    def as_dict(self):
        return {
            "result": GRANTED if self.granted else REFUSED,
            "actor": self.actor,
            "code": self.code,
            "reason": self.reason,
            "approval_assurance": self.assurance,
            "assurance_caveat": (
                "DECLARED_ONLY: the recorded actor is structurally "
                "constrained, but no proof exists that a real human performed "
                "this act. GAP-02 remains OPEN."),
        }


def check_actor(actor, claimed_as=None):
    """Reject impersonation before anything else is considered.

    `claimed_as` is what the caller asserts the actor is. An AI, system or
    producer asserting USER is refused outright.
    """
    if actor in NON_APPROVING_ACTORS and claimed_as == ACTOR_USER:
        return AuthorityDecision(
            False, actor, AUTH_IMPERSONATION,
            f"actor '{actor}' claimed to be '{ACTOR_USER}'. A non-human actor "
            f"may never be recorded as the approver.")
    return None


def authorise_approval(actor, claimed_as=None):
    """Authority to APPROVE. USER only, always."""
    impersonation = check_actor(actor, claimed_as)
    if impersonation is not None:
        return impersonation
    if actor not in APPROVAL_AUTHORITIES:
        return AuthorityDecision(
            False, actor, AUTH_NOT_USER,
            f"approval authority is held by {ACTOR_USER} alone; '{actor}' "
            f"cannot approve.")
    return AuthorityDecision(True, actor)


def authorise_transition(actor, required_authority, transition_id,
                         claimed_as=None):
    """Authority for one named lifecycle transition."""
    impersonation = check_actor(actor, claimed_as)
    if impersonation is not None:
        return impersonation
    if actor != required_authority:
        return AuthorityDecision(
            False, actor, AUTH_WRONG_AUTHORITY,
            f"transition {transition_id} requires authority "
            f"'{required_authority}'; '{actor}' does not hold it.")
    return AuthorityDecision(True, actor)


def authorise_decision_recording(actor, proposal_ref, decision_ref,
                                 proposal_state=None, claimed_as=None):
    """Authority to RECORD a decision — an explicit, separate act.

    Approving a proposal does NOT create a decision (DL-1). Recording one is
    its own act, it needs USER authority, and it needs explicit references.
    """
    impersonation = check_actor(actor, claimed_as)
    if impersonation is not None:
        return impersonation
    if actor not in APPROVAL_AUTHORITIES:
        return AuthorityDecision(
            False, actor, AUTH_NOT_USER,
            f"decision recording requires {ACTOR_USER} authority; '{actor}' "
            f"does not hold it.")
    if not proposal_ref or not decision_ref:
        return AuthorityDecision(
            False, actor, AUTH_MISSING_REFS,
            "decision recording requires explicit proposal and decision "
            "references; neither is inferred.")
    if proposal_state in ("REJECTED", "SUPERSEDED"):
        return AuthorityDecision(
            False, actor, AUTH_INELIGIBLE,
            f"the linked proposal is {proposal_state}; a decision may not "
            f"rest on it.")
    return AuthorityDecision(True, actor)


def approval_record(actor, entity_ref, on_date, in_revision):
    """Build an approval record, or refuse. Never inferred from other fields.

    Stored as an explicit reference (FCR-2) carrying its assurance (FCR-3).
    """
    decision = authorise_approval(actor)
    if not decision.granted:
        return {"approved": False, "authority": decision.as_dict()}
    return {
        "approved": True,
        "approved_by": ACTOR_USER,
        "entity_ref": entity_ref,
        "approved_on": on_date,
        "approved_in_revision": in_revision,
        "approval_assurance": ASSURANCE_DECLARED_ONLY,
        "authority": decision.as_dict(),
    }
