#!/usr/bin/env python3
"""
00.5-E — G-1 IDENTITY REGISTRY

Reference (APPROVED / LOCKED):
  00.5-E-ARCHITECTURE-AND-CLOSURE-REPORT.md          (R01)
  00.5-E-ARCHITECTURE-AND-CLOSURE-REPORT-R02.md      (R02)
  00.5-E-R02-LOCAL-AMENDMENT-LIFECYCLE.md            (Local Amendment)

WHAT G-1 OWNS
  The official identity of governance entities, and the referential binding
  between an external governance record and the master version it governs.

  E issues official output identity. No producer and no assembler may mint it.

WHAT G-1 DOES NOT OWN
  geometry · fidelity · evidence assembly · engineering correctness ·
  proof of human identity (CONFLICT-E-01 / GAP-02 remain OPEN).

IDENTITY PATTERNS — taken from the existing schema, NOT invented here:
  PRJ-##[#] · DEC-### · P-### · CR-### · OBJ-### · OUT-###

BINDING HONESTY
  The external governance record binds to the master REFERENTIALLY only:
  project_id + revision + DECLARED master_hash + geometry_version + ids.
  The declared master_hash is declared, not computed (C2 is blocked), so this
  binding makes detachment DETECTABLE, not impossible. It is not tamper-proof
  and no cryptographic assurance is claimed.
"""

import re

# --- identity patterns (schema-derived) -----------------------------------
PATTERNS = {
    "project": re.compile(r"^PRJ-[0-9]{2,3}$"),
    "decision": re.compile(r"^DEC-[0-9]{3}$"),
    "proposal": re.compile(r"^P-[0-9]{3}$"),
    "change_request": re.compile(r"^CR-[0-9]{3}$"),
    "objection": re.compile(r"^OBJ-[0-9]{3}$"),
    "output": re.compile(r"^OUT-[0-9]{3}$"),
}

OUTPUT_ID_PREFIX = "OUT-"
NOT_SET = "NOT_SET"

# Binding strength. Honest by construction: referential, never cryptographic.
BINDING_REFERENTIAL_ONLY = "REFERENTIAL_ONLY"

# Only E may issue official identity.
IDENTITY_ISSUER = "E"
FORBIDDEN_ISSUERS = ("C3", "C4", "C5", "C6", "D", "PRODUCER")


class IdentityError(RuntimeError):
    """Raised when identity issuance or validation is attempted illegally."""


def valid_id(kind, value):
    """Structural validity of an identifier against the approved pattern."""
    pattern = PATTERNS.get(kind)
    if pattern is None or not isinstance(value, str):
        return False
    return bool(pattern.match(value))


def issue_output_id(existing_ids, issuer=IDENTITY_ISSUER):
    """Issue the next official output_id. E only.

    Any other issuer is refused: identity is a governance authority, and a
    producer or assembler minting it would be impersonation of that authority.
    """
    if issuer != IDENTITY_ISSUER:
        raise IdentityError(
            f"'{issuer}' may not issue an official output_id. Identity is "
            f"owned by E; producers supply artefacts and evidence only.")

    used = set()
    for value in existing_ids or []:
        if valid_id("output", value):
            used.add(int(value[len(OUTPUT_ID_PREFIX):]))
    nxt = 1
    while nxt in used:
        nxt += 1
    if nxt > 999:
        raise IdentityError("output_id space exhausted under pattern "
                            "^OUT-[0-9]{3}$; this needs a governance decision, "
                            "not a silent widening of the pattern.")
    return f"{OUTPUT_ID_PREFIX}{nxt:03d}"


def bind_record(meta, entity_refs=None):
    """Build the referential binding of an external governance record.

    Every value is READ from meta; nothing is computed, derived or invented.
    """
    meta = meta if isinstance(meta, dict) else {}
    refs = []
    for ref in entity_refs or []:
        refs.append(ref)

    return {
        "project_id": meta.get("project_id", NOT_SET),
        "master_revision": meta.get("revision", NOT_SET),
        # Declared, NOT computed: C2 fingerprint issuance is blocked.
        "master_hash_declared": meta.get("master_hash", NOT_SET),
        "geometry_version": meta.get("geometry_version", NOT_SET),
        "entity_refs": refs,
        "binding_assurance": BINDING_REFERENTIAL_ONLY,
        "tamper_proof": False,
        "note": ("Referential binding only. The master hash is declared by "
                 "the master, not computed by E (C2 is blocked). This makes "
                 "detachment from the governed version DETECTABLE; it does "
                 "not make the record tamper-proof."),
    }


def binding_matches(binding, meta):
    """Mechanical comparison of a binding against a master's meta.

    Reports agreement of DECLARED values. It is not proof of authenticity.
    """
    meta = meta if isinstance(meta, dict) else {}
    checks = {
        "project_id": binding.get("project_id") == meta.get("project_id",
                                                            NOT_SET),
        "master_revision": binding.get("master_revision") == meta.get(
            "revision", NOT_SET),
        "master_hash_declared": binding.get("master_hash_declared") ==
        meta.get("master_hash", NOT_SET),
        "geometry_version": binding.get("geometry_version") == meta.get(
            "geometry_version", NOT_SET),
    }
    return {
        "matches": all(checks.values()),
        "field_results": checks,
        "assurance": BINDING_REFERENTIAL_ONLY,
        "note": "Declared-value comparison only; not an authenticity proof.",
    }
