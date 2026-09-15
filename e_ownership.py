#!/usr/bin/env python3
"""
00.5-E — G-4 OWNERSHIP REGISTRY

E is the official owner of outputs[]. It issues output identity, holds the
approval state, and drives the output lifecycle.

FIELD OWNERSHIP — applied exactly as approved, not widened
  output_id            -> E            (issued here)
  file · view_type     -> Producer     (carried verbatim)
  class                -> Producer     (immutable; never upgraded)
  approval_state       -> E
  fidelity_state       -> D            (carried, never judged here)
  fingerprint          -> C2           (NOT_ISSUED today)
  derived_from_output  -> E
  supersedes_A         -> E
  approval_assurance   -> E            (DECLARED_ONLY today)

DUAL STATE — DS-1..DS-4
  approval_state and fidelity_state are independent. Neither is ever derived
  from the other. APPROVED does not mean VERIFIED; VERIFIED never raises
  approval. APPROVED + FAILED is legitimate but must be surfaced, never
  hidden and never presented as agreement.

NOT OWNED HERE
  geometry · fidelity judgement · evidence assembly · engineering validity.
  E is a governance layer, not a validator and not a fidelity judge.
"""

import copy

from e_identity import issue_output_id, valid_id, NOT_SET
from e_authorization import (ACTOR_USER, ASSURANCE_DECLARED_ONLY,
                             authorise_approval)
from e_lifecycle import (REGISTERED, EVIDENCE_LINKED, APPROVED, SUPERSEDED,
                         WITHDRAWN, TERMINAL_STATES, evaluate, ALLOWED)

# Classes: producer-declared, immutable, never upgraded.
CLASS_A = "A"
CLASS_B = "B"
CLASS_C = "C"
CLASSES = (CLASS_A, CLASS_B, CLASS_C)

# Fidelity states are D's vocabulary; E carries them and never sets them.
FIDELITY_STATES = ("VERIFIED", "PARTIAL", "NOT_VERIFIABLE", "FAILED",
                   "ABSTAIN", "NOT_ASSESSED")

FINGERPRINT_NOT_ISSUED = "NOT_ISSUED"

IMMUTABLE_FIELDS = ("output_id", "class", "file", "view_type",
                    "generated_on", "fingerprint", "derived_from_output")


class OwnershipError(RuntimeError):
    """Raised on an attempt to breach the ownership contract."""


def register_output(registry, producer_record, issuer="E"):
    """Register a producer artefact and grant it official identity (T-01).

    The producer supplies the artefact and its declared fields. E grants the
    identity: a producer or assembler minting one would be impersonating a
    governance authority.
    """
    existing = [entry.get("output_id") for entry in registry]
    output_id = issue_output_id(existing, issuer=issuer)

    declared_class = (producer_record or {}).get("class", NOT_SET)
    if declared_class not in CLASSES and declared_class != NOT_SET:
        raise OwnershipError(
            f"class '{declared_class}' is not one of {CLASSES}; E does not "
            f"reinterpret a producer's declared class.")

    entry = {
        # --- E-owned identity -------------------------------------------
        "output_id": output_id,
        "identity_issued_by": "E",
        # --- producer-declared, carried verbatim ------------------------
        "file": (producer_record or {}).get("file", NOT_SET),
        "view_type": (producer_record or {}).get("view_type", NOT_SET),
        "class": declared_class,
        "generated_on": (producer_record or {}).get("generated_on", NOT_SET),
        "producer": (producer_record or {}).get("producer", NOT_SET),
        # --- C2-owned; issuance is blocked -------------------------------
        "fingerprint": FINGERPRINT_NOT_ISSUED,
        # --- dual state, independent ------------------------------------
        "approval_state": REGISTERED,
        "fidelity_state": "NOT_ASSESSED",
        # --- E-owned governance ------------------------------------------
        "derived_from_output": (producer_record or {}).get(
            "derived_from_output", NOT_SET),
        "supersedes_A": False,
        "approval_assurance": ASSURANCE_DECLARED_ONLY,
        "evidence_refs": {},
        "lifecycle_history": [{"transition": "T-01", "to": REGISTERED,
                               "authority": "E"}],
    }
    registry.append(entry)
    return entry


def find_output(registry, output_id):
    for entry in registry:
        if entry.get("output_id") == output_id:
            return entry
    return None


def link_evidence(registry, output_id, evidence_refs, actor="E"):
    """T-02: attach evidence REFERENCES. Registrational, not a verdict.

    Linking says references exist. It says nothing about whether the evidence
    is correct, and it grants no acceptance and no approval.
    """
    entry = find_output(registry, output_id)
    if entry is None:
        raise OwnershipError(f"unknown output '{output_id}'")

    decision = evaluate(entry["approval_state"], EVIDENCE_LINKED, actor)
    if decision["result"] != ALLOWED:
        return {"linked": False, "decision": decision}

    entry["evidence_refs"] = copy.deepcopy(evidence_refs or {})
    entry["approval_state"] = EVIDENCE_LINKED
    entry["lifecycle_history"].append(
        {"transition": decision["transition"], "to": EVIDENCE_LINKED,
         "authority": actor})
    return {"linked": True, "decision": decision,
            "note": "evidence references linked; their correctness is not "
                    "asserted by this act"}


def carry_fidelity(registry, output_id, fidelity_state):
    """Carry D's verdict verbatim. E never computes or overrides it."""
    entry = find_output(registry, output_id)
    if entry is None:
        raise OwnershipError(f"unknown output '{output_id}'")
    if fidelity_state not in FIDELITY_STATES:
        raise OwnershipError(
            f"'{fidelity_state}' is not a fidelity state owned by D; E does "
            f"not invent one.")
    entry["fidelity_state"] = fidelity_state
    # DS-1: fidelity never raises approval_state.
    return {"fidelity_state": entry["fidelity_state"],
            "approval_state": entry["approval_state"],
            "note": "fidelity carried from D; approval_state deliberately "
                    "unchanged (DS-1)"}


def transition(registry, output_id, to_state, actor, claimed_as=None):
    """Drive one lifecycle transition under the whitelist and its authority."""
    entry = find_output(registry, output_id)
    if entry is None:
        raise OwnershipError(f"unknown output '{output_id}'")

    decision = evaluate(entry["approval_state"], to_state, actor, claimed_as)
    if decision["result"] != ALLOWED:
        return {"changed": False, "decision": decision,
                "approval_state": entry["approval_state"]}

    if to_state == APPROVED:
        auth = authorise_approval(actor, claimed_as)
        if not auth.granted:
            return {"changed": False, "approval_state":
                    entry["approval_state"],
                    "decision": {"result": "FORBIDDEN",
                                 "code": auth.code, "reason": auth.reason}}

    entry["approval_state"] = to_state
    entry["lifecycle_history"].append(
        {"transition": decision["transition"], "to": to_state,
         "authority": actor})
    return {"changed": True, "decision": decision, "approval_state": to_state}


def set_field(registry, output_id, field, value, actor=ACTOR_USER):
    """Mutate a governance field. Immutable fields are refused."""
    entry = find_output(registry, output_id)
    if entry is None:
        raise OwnershipError(f"unknown output '{output_id}'")
    if field in IMMUTABLE_FIELDS:
        return {"changed": False, "code": "OWN-01",
                "reason": f"'{field}' is immutable once issued. A change of "
                          f"identity-bearing data requires a NEW output with "
                          f"a NEW identity."}
    if entry["approval_state"] in TERMINAL_STATES:
        return {"changed": False, "code": "OWN-02",
                "reason": f"output is {entry['approval_state']} (terminal); "
                          f"its governance record is closed."}
    entry[field] = value
    return {"changed": True, "field": field}


def read_state(registry, output_id):
    """Read the DUAL state. Both halves always travel together (DS-3)."""
    entry = find_output(registry, output_id)
    if entry is None:
        raise OwnershipError(f"unknown output '{output_id}'")
    approval = entry["approval_state"]
    fidelity = entry["fidelity_state"]
    surfaced = (approval == APPROVED and fidelity == "FAILED")
    return {
        "output_id": output_id,
        "approval_state": approval,
        "fidelity_state": fidelity,
        "approval_assurance": entry["approval_assurance"],
        "requires_surfacing": surfaced,
        "surfacing_notice": (
            "APPROVED with a FAILED fidelity verdict: this is a legitimate "
            "governance position and is shown explicitly. It must never be "
            "read as agreement with the master."
            if surfaced else None),
        "caveat": ("approval_state and fidelity_state are independent. "
                   "APPROVED does not mean VERIFIED, and VERIFIED does not "
                   "grant approval."),
    }
