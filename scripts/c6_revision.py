#!/usr/bin/env python3
"""
00.5-C6 — REVISION COMPARISON (mechanical metadata only)

Compares the master_revision values that members DECLARED. The output is
`mechanical comparison metadata` and never a verdict.

MEANINGS — strictly bounded
  comparable=false          : revision data is incomplete for a full
                              comparison. NOT invalid/failed/rejected/
                              inconsistent/unapproved.
  divergence=OBSERVED       : the declared values differ. NOT an engineering
                              conflict, geometry error, fidelity failure or
                              approval failure.
  divergence=NONE_OBSERVED  : the declared values match. NOT "the design is
                              correct".
  divergence=NOT_DETERMINABLE : not enough data to compare.

FORBIDDEN
  choosing the latest revision · rejecting a revision · merging revisions into
  a new one · hiding a difference · issuing any engineering, fidelity or
  approval verdict.

MEASURED LIMIT
  C3 records carry no master_revision field at all (it exists only inside SVG
  comment text), so NOT_DETERMINABLE is the common outcome today. That is a
  description of the available data, not a defect in the output.
"""

from c6_contract import (
    NOT_SET, DIV_NONE_OBSERVED, DIV_OBSERVED, DIV_NOT_DETERMINABLE,
)


def declared_revision(member):
    """Read a declared master_revision, else NOT_SET. Never inferred."""
    if not isinstance(member, dict):
        return NOT_SET
    if member.get("master_revision"):
        return member["master_revision"]
    lineage = member.get("lineage_evidence")
    if isinstance(lineage, dict) and lineage.get("master_revision"):
        rev = lineage["master_revision"]
        return rev if rev != NOT_SET else NOT_SET
    return NOT_SET


def compare_revisions(members):
    """Return mechanical comparison metadata over declared revisions."""
    declared = {}
    for i, m in enumerate(members or []):
        key = (m.get("source_owner") if isinstance(m, dict) else None) or f"member_{i}"
        if key in declared:
            key = f"{key}_{i}"
        declared[key] = declared_revision(m)

    values = [v for v in declared.values() if v != NOT_SET]
    missing = [k for k, v in declared.items() if v == NOT_SET]

    if not members:
        comparable, divergence = False, DIV_NOT_DETERMINABLE
    elif missing:
        comparable, divergence = False, DIV_NOT_DETERMINABLE
    elif len(set(values)) <= 1:
        comparable, divergence = True, DIV_NONE_OBSERVED
    else:
        comparable, divergence = True, DIV_OBSERVED

    return {
        "declared_revisions": declared,
        "members_without_declared_revision": missing,
        "comparable": comparable,
        "divergence": divergence,
        "metadata_kind": "mechanical comparison metadata",
        "note": ("Compares declared master_revision values only. "
                 "comparable=false means the available revision data does not "
                 "permit a full comparison; it does not mean the outputs are "
                 "invalid. divergence=OBSERVED means the declared values "
                 "differ; it does not mean an engineering conflict exists."),
        "is_verdict": False,
    }
