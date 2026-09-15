#!/usr/bin/env python3
"""
00.5-E — G-3 LIFECYCLE MACHINE

Implements the Output State Machine exactly as corrected in the R02 Local
Amendment. The whitelist below is EXHAUSTIVE: there is no T-10.

ALLOWED TRANSITIONS
  T-01  (issuance)      -> REGISTERED        E     automatic, declared
  T-02  REGISTERED      -> EVIDENCE_LINKED   E     automatic, declared
  T-03  EVIDENCE_LINKED -> ACCEPTED          USER  explicit decision
  T-04  ACCEPTED        -> APPROVED          USER  explicit decision
  T-05  APPROVED        -> SUPERSEDED        USER  explicit decision
  T-06  REGISTERED      -> WITHDRAWN         USER  explicit decision
  T-07  EVIDENCE_LINKED -> WITHDRAWN         USER  explicit decision
  T-08  ACCEPTED        -> WITHDRAWN         USER  explicit decision
  T-09  APPROVED        -> WITHDRAWN         USER  explicit decision

TERMINAL STATES
  SUPERSEDED  -> no outgoing transitions
  WITHDRAWN   -> no outgoing transitions
  Neither may be revived. A later need is met by a NEW output with a NEW
  identity, never by reopening something that ended.

TRANSITION VOCABULARY
  There are no implicit GOVERNANCE transitions. The automatic transitions
  permitted by the contract are enumerated explicitly and are registrational,
  not authority-bearing: T-02 links evidence references and says nothing about
  whether that evidence is correct.
"""

from e_authorization import (ACTOR_USER, ACTOR_E, authorise_transition)

# --- states ----------------------------------------------------------------
REGISTERED = "REGISTERED"
EVIDENCE_LINKED = "EVIDENCE_LINKED"
ACCEPTED = "ACCEPTED"
APPROVED = "APPROVED"
SUPERSEDED = "SUPERSEDED"
WITHDRAWN = "WITHDRAWN"

STATES = (REGISTERED, EVIDENCE_LINKED, ACCEPTED, APPROVED, SUPERSEDED,
          WITHDRAWN)

TERMINAL_STATES = (SUPERSEDED, WITHDRAWN)

ISSUANCE = "(issuance)"

# --- transition kinds ------------------------------------------------------
KIND_AUTOMATIC = "AUTOMATIC_DECLARED"      # registrational, not authority
KIND_GOVERNANCE = "GOVERNANCE_EXPLICIT"    # changes where authority sits

# --- THE WHITELIST — exhaustive. Anything absent is forbidden. -------------
TRANSITIONS = {
    "T-01": {"from": ISSUANCE, "to": REGISTERED,
             "authority": ACTOR_E, "kind": KIND_AUTOMATIC},
    "T-02": {"from": REGISTERED, "to": EVIDENCE_LINKED,
             "authority": ACTOR_E, "kind": KIND_AUTOMATIC},
    "T-03": {"from": EVIDENCE_LINKED, "to": ACCEPTED,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
    "T-04": {"from": ACCEPTED, "to": APPROVED,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
    "T-05": {"from": APPROVED, "to": SUPERSEDED,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
    "T-06": {"from": REGISTERED, "to": WITHDRAWN,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
    "T-07": {"from": EVIDENCE_LINKED, "to": WITHDRAWN,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
    "T-08": {"from": ACCEPTED, "to": WITHDRAWN,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
    "T-09": {"from": APPROVED, "to": WITHDRAWN,
             "authority": ACTOR_USER, "kind": KIND_GOVERNANCE},
}

ALLOWED = "ALLOWED"
FORBIDDEN = "FORBIDDEN"

# Refusal codes
LC_TERMINAL = "LC-01"        # source state is terminal
LC_NOT_WHITELISTED = "LC-02"  # transition absent from the whitelist
LC_UNKNOWN_STATE = "LC-03"   # state outside the vocabulary
LC_NO_AUTHORITY = "LC-04"    # actor lacks the required authority


def is_terminal(state):
    return state in TERMINAL_STATES


def find_transition(from_state, to_state):
    """Return the transition id, or None when it is not whitelisted."""
    for tid, spec in TRANSITIONS.items():
        if spec["from"] == from_state and spec["to"] == to_state:
            return tid
    return None


def evaluate(from_state, to_state, actor, claimed_as=None):
    """Decide whether one transition may occur. Refuses by default."""
    if from_state not in STATES and from_state != ISSUANCE:
        return {"result": FORBIDDEN, "code": LC_UNKNOWN_STATE,
                "reason": f"'{from_state}' is not a known output state."}
    if to_state not in STATES:
        return {"result": FORBIDDEN, "code": LC_UNKNOWN_STATE,
                "reason": f"'{to_state}' is not a known output state."}

    # Terminal states are checked FIRST, so no whitelist entry could ever
    # smuggle an exit from a state that has ended.
    if is_terminal(from_state):
        return {"result": FORBIDDEN, "code": LC_TERMINAL,
                "reason": f"'{from_state}' is terminal: it has no outgoing "
                          f"transitions and cannot be revived. A new output "
                          f"with a new identity is required."}

    tid = find_transition(from_state, to_state)
    if tid is None:
        return {"result": FORBIDDEN, "code": LC_NOT_WHITELISTED,
                "reason": f"'{from_state}' -> '{to_state}' is not in the "
                          f"whitelist. Absent means forbidden, not undefined."}

    spec = TRANSITIONS[tid]
    auth = authorise_transition(actor, spec["authority"], tid, claimed_as)
    if not auth.granted:
        return {"result": FORBIDDEN, "code": LC_NO_AUTHORITY,
                "transition": tid, "reason": auth.reason,
                "authority": auth.as_dict()}

    return {"result": ALLOWED, "transition": tid, "from": from_state,
            "to": to_state, "kind": spec["kind"],
            "authority": auth.as_dict(),
            "note": ("automatic transitions are registrational and carry no "
                     "governance authority"
                     if spec["kind"] == KIND_AUTOMATIC else
                     "explicit governance decision by the named authority")}


def allowed_from(state):
    """Every transition legally available from a state. Empty when terminal."""
    if is_terminal(state):
        return []
    return [tid for tid, spec in TRANSITIONS.items() if spec["from"] == state]
