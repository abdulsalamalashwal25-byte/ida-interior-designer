#!/usr/bin/env python3
"""
00.5-C6 — MEMBER PRESERVATION (no reinterpretation)

Turns one producer record into one manifest member by COPYING what the
producer declared. It performs no comparison, no counting and no assembly.

THE RULE
  C6 carries the meaning of the original field and never moves a value into a
  differently-named slot. A producer that does not declare a field gets
  NOT_SET there — never a value derived from a neighbouring field.

  C3  -> status only        (coverage NOT_SET, completeness NOT_SET)
  C5  -> status + coverage  (completeness NOT_SET)
  C4  -> completeness only  (status NOT_SET, coverage NOT_SET)

WHAT IS FORBIDDEN HERE
  completeness -> status · coverage -> status · status -> coverage ·
  status/coverage -> completeness · recomputing C4's overall · reshaping or
  renaming C4's completeness dictionary · inferring producer_channel ·
  inferring declared_class · generating output_id · issuing fingerprints ·
  producing any approval or fidelity verdict.
"""

import copy

from c6_contract import (
    NOT_SET, OWNER_C3, OWNER_C4, OWNER_C5, KNOWN_OWNERS,
    DECLARES_STATUS, DECLARES_COVERAGE, DECLARES_COMPLETENESS,
    FIDELITY_VALUE, FINGERPRINT_VALUE, APPROVAL_MANAGED_BY,
    DETERMINISM_DEFAULT, PARENT_PRESENT, PARENT_MISSING,
)


def _declared(record, key):
    """Return a declared value, or NOT_SET when the field is absent.

    Absence is reported, never filled in from another field.
    """
    if not isinstance(record, dict):
        return NOT_SET
    if key not in record:
        return NOT_SET
    value = record[key]
    return NOT_SET if value is None else value


def preserve_status(record, owner):
    """status: declared by C3 and C5 only."""
    if owner not in DECLARES_STATUS:
        return NOT_SET
    return _declared(record, "status")


def preserve_coverage(record, owner):
    """coverage: declared by C5 only."""
    if owner not in DECLARES_COVERAGE:
        return NOT_SET
    return _declared(record, "coverage")


def preserve_completeness(record, owner):
    """completeness: declared by C4 only.

    C4's `completeness` is a DICTIONARY, not a scalar (measured). The headline
    value is whatever C4 put under 'overall' — read, never recomputed from the
    per-quantity entries.
    """
    if owner not in DECLARES_COMPLETENESS:
        return NOT_SET
    raw = _declared(record, "completeness")
    if raw is NOT_SET:
        return NOT_SET
    if isinstance(raw, dict):
        return raw.get("overall", NOT_SET)
    return raw


def preserve_completeness_detail(record, owner):
    """The completeness dictionary, copied verbatim.

    Deliberately NOT normalised: its key set legitimately differs from
    class_a's (Q-01 appears in class_a but not in completeness), and an
    'ABSTAIN' member can legitimately coexist with overall='PARTIAL'. Both are
    source facts. Completing, reconciling or reordering them would rewrite
    what C4 declared.
    """
    if owner not in DECLARES_COMPLETENESS:
        return None
    raw = _declared(record, "completeness")
    if isinstance(raw, dict):
        return copy.deepcopy(raw)
    return None


def preserve_declared_class(record):
    """Only an explicitly declared `class`. Never inferred."""
    return _declared(record, "class")


def preserve_producer_channel(record):
    """Only an explicitly declared `producer_channel`.

    No producer emits this field today and no Contract Registry exists, so the
    result is NOT_SET. It is never inferred from contract, format, an SVG
    comment, a filename, a missing class or C6's own knowledge.
    """
    return _declared(record, "producer_channel")


def preserve_output_id(record, supplied_identity=None):
    """An official identity is preserved; otherwise NOT_SET.

    C6 never mints an identity from a hash, filename, contract, UUID or
    timestamp. Official output_id ownership stays with E.
    """
    if isinstance(supplied_identity, dict) and supplied_identity.get("output_id"):
        return supplied_identity["output_id"]
    return _declared(record, "output_id")


def preserve_approval_value(record, supplied_identity=None):
    """Approval only ever arrives from its owner; it is never derived."""
    if isinstance(supplied_identity, dict) and \
            supplied_identity.get("approval_value") is not None:
        return supplied_identity["approval_value"]
    return _declared(record, "approval_value")


def preserve_parent(record):
    """(parent_ref, parent_evidence) — a mechanical presence check only.

    PRESENT/MISSING states whether a reference was received. It is not a
    judgement: no 'orphan', no 'broken lineage', no engineering failure.
    """
    ref = _declared(record, "parent_ref")
    return ref, (PARENT_PRESENT if ref is not NOT_SET else PARENT_MISSING)


def preserve_determinism(record):
    """Determinism evidence is carried exactly as the producer stated it."""
    raw = _declared(record, "determinism")
    if isinstance(raw, dict):
        return copy.deepcopy(raw)
    return dict(DETERMINISM_DEFAULT)


def preserve_member(record, owner, supplied_identity=None):
    """Build one manifest member from one producer record.

    `record` is treated as read-only: everything copied out is a deep copy, so
    the caller's evidence cannot be mutated in place.
    """
    if owner not in KNOWN_OWNERS:
        owner_value = NOT_SET
    else:
        owner_value = owner

    src = copy.deepcopy(record) if isinstance(record, dict) else {}
    parent_ref, parent_evidence = preserve_parent(src)

    member = {
        "source_owner": owner_value,
        # three independent fields — never cross-populated
        "source_status": preserve_status(src, owner),
        "source_coverage": preserve_coverage(src, owner),
        "source_completeness": preserve_completeness(src, owner),
        # boundaries owned elsewhere
        "producer_channel": preserve_producer_channel(src),
        "declared_class": preserve_declared_class(src),
        "contract": _declared(src, "contract"),      # raw value, untranslated
        "format": _declared(src, "format"),          # raw value, untranslated
        "approval_managed_by": APPROVAL_MANAGED_BY,
        "approval_value": preserve_approval_value(src, supplied_identity),
        "parent_ref": parent_ref,
        "parent_evidence": parent_evidence,
        "fidelity": FIDELITY_VALUE,
        "engineering_fingerprint": FINGERPRINT_VALUE,
        "determinism": preserve_determinism(src),
        "output_id": preserve_output_id(src, supplied_identity),
    }

    detail = preserve_completeness_detail(src, owner)
    if detail is not None:
        member["source_completeness_detail"] = detail

    # Optional evidence: carried only when the producer declared it.
    for key in ("omissions", "exclusions", "parameters_admitted",
                "parameters_rejected", "lineage_evidence",
                "environment_evidence", "capability", "limitations",
                "production_timestamp", "evidence_timestamp"):
        if isinstance(src, dict) and key in src and src[key] is not None:
            member[key] = copy.deepcopy(src[key])

    return member
