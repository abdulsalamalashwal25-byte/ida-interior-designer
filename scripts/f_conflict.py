#!/usr/bin/env python3
"""
00.5-F — CONFLICT · VERSION / SUPERSESSION · SNAPSHOT · PROVENANCE

CONFLICT (R02 section 14)
  When two sources disagree, F reports BOTH in full and resolves nothing.
  CF-1 no automatic selection      CF-4 conflict is a legitimate state
  CF-2 no average, range or "nearest"   CF-5 F never resolves it as a design
  CF-3 both sources shown in full        decision (no approved rule exists)
  CF-6 a source outside its authority scope is not preferred

VERSION (R02 section 15)
  A library update NEVER modifies the project. Using a reference pins its
  version and retrieval time. v2 is recorded as superseding v1; it is not
  applied. Project history stays reconstructible.

SNAPSHOT (R02 section 16)
  content_fingerprint stays NOT_ISSUED, respecting C2's blocked fingerprint
  contract. No tamper-proof claim, no claim of capturing everything.

PROVENANCE (R02 sections 17-18)
  Records origin. Claims no cryptographic authenticity, no verified publisher
  identity, no tamper-proof provenance, no absolute source truth.
"""

from f_reference import NOT_SET, NOT_AUTHORITATIVE, authority_for

# --- conflict ---------------------------------------------------------------
USER_DECISION = "USER_DECISION"


def detect_conflict(attribute, claim_a, claim_b):
    """Describe a disagreement between two source claims. Resolves nothing."""
    value_a, value_b = claim_a.get("value"), claim_b.get("value")
    differs = value_a != value_b
    if not differs:
        return {"conflict": False, "attribute": attribute,
                "note": "declared values agree; agreement is not proof"}

    return {
        "conflict": True,
        "attribute": attribute,
        "source_a": {
            "source_identity_declared": claim_a.get("source_identity", NOT_SET),
            "source_version": claim_a.get("source_version", NOT_SET),
            "citation": claim_a.get("citation", NOT_SET),
            "authority_scope_result": claim_a.get("authority_result", NOT_SET),
            "verification_state": claim_a.get("verification_state", NOT_SET),
            "value": value_a, "unit": claim_a.get("unit", NOT_SET)},
        "source_b": {
            "source_identity_declared": claim_b.get("source_identity", NOT_SET),
            "source_version": claim_b.get("source_version", NOT_SET),
            "citation": claim_b.get("citation", NOT_SET),
            "authority_scope_result": claim_b.get("authority_result", NOT_SET),
            "verification_state": claim_b.get("verification_state", NOT_SET),
            "value": value_b, "unit": claim_b.get("unit", NOT_SET)},
        "scope_overlap": (claim_a.get("authority_result") == "AUTHORITATIVE"
                          and claim_b.get("authority_result") == "AUTHORITATIVE"),
        "required_resolution": USER_DECISION,
        "resolved": False,
        "resolved_by_f": False,
        "note": ("F reports both claims in full and selects neither. No "
                 "average, no range, no 'nearest', no preference by source "
                 "type. Resolution is a user decision."),
    }


def preferred_source(conflict):
    """Always refuses. F has no approved rule for resolving conflicts."""
    return {
        "preferred": None,
        "code": "CF-05",
        "reason": ("F does not resolve a conflict as a design decision. No "
                   "approved precedence rule exists (DEC-F-04 is OPEN)."),
    }


# --- version / supersession ------------------------------------------------
def pin_usage(source_id, source_version, retrieved_on):
    """Pin the exact version a project used. This is what stays."""
    return {"source_id": source_id, "source_version": source_version,
            "retrieved_on": retrieved_on, "pinned": True,
            "note": "the project keeps this version; later versions do not "
                    "replace it"}


def register_new_version(pinned, new_version):
    """Record that a newer version exists. It is NEVER applied."""
    return {
        "pinned_version": pinned.get("source_version", NOT_SET),
        "new_version": new_version,
        "relation": "SUPERSEDES",
        "applied_to_project": False,
        "project_changed": False,
        "requires": "explicit user action to adopt",
        "note": ("a library update never modifies the project. Project "
                 "history stays reconstructible."),
    }


# --- snapshot ---------------------------------------------------------------
def snapshot(snapshot_id, source_version=NOT_SET, retrieval_timestamp=NOT_SET,
             citation=NOT_SET, availability_status=NOT_SET):
    """A reference snapshot. No fingerprint contract is invented here."""
    return {
        "snapshot_id": snapshot_id,
        "source_version": source_version,
        "retrieval_timestamp": retrieval_timestamp,
        "citation": citation,
        "availability_status": availability_status,
        # C2 owns fingerprints and issuance is blocked. F invents nothing.
        "content_fingerprint": "NOT_ISSUED",
        "tamper_proof": False,
        "captures_everything": False,
        "note": ("snapshot is a record of what was cited and when. It is not "
                 "tamper-proof and does not claim to capture everything."),
    }


# --- provenance -------------------------------------------------------------
def provenance(source, attribute_ref, usage_context=NOT_SET,
               applicability=NOT_SET):
    """Full provenance of a reference value, with explicit non-claims."""
    return {
        "source_id": source.source_id,
        "source_identity_declared": source.source_identity,
        "source_version": source.source_version,
        "retrieved_on": source.retrieved_on,
        "retrieved_by": source.retrieved_by,
        "reference_id": attribute_ref,
        "citation": source.citation,
        "document_reference": source.document_reference,
        "authority_scope": list(source.authority_scope),
        "verification_state": source.verification_state,
        "validity": source.validity,
        "usage_context": usage_context,
        "applicability": applicability,
        "claims_not_made": [
            "cryptographic authenticity",
            "verified publisher identity",
            "tamper-proof provenance",
            "absolute source truth",
        ],
        "citation_authenticity": "NOT_VERIFIED — GAP-F-02 OPEN",
        "note": ("provenance discloses origin. It does not prove it. Source "
                 "identity is as declared, not as verified."),
    }


# --- standards boundary -----------------------------------------------------
def compliance_claim(*_args, **_kwargs):
    """F never produces a compliance claim or certification."""
    return {
        "compliance_certified": False,
        "code": "GAP-F-01",
        "reason": ("Reference retrieved + content checked is not compliance. "
                   "Standard Reference is not a Requirement; a Requirement is "
                   "not a Compliance Claim; a Compliance Claim is not "
                   "Compliance Verification. Compliance Verification is "
                   "outside F and outside 00.5."),
    }
