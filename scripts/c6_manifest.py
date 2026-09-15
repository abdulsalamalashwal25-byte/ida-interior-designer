#!/usr/bin/env python3
"""
00.5-C6 — MANIFEST ASSEMBLY

Assembles preserved members, mechanical revision metadata and mechanical
counts into one EXTERNAL manifest.

    Preserve -> Compare mechanically -> Count mechanically -> Assemble -> Stop.

NOT CREATED HERE — by contract
  manifest status · manifest completeness · manifest approval ·
  manifest fidelity · manifest validity · output_id · engineering fingerprint.

The manifest is ASSEMBLED EVIDENCE, not a verdict. It is returned as a
structure; C6 writes no file (the caller decides on persistence, and C6 never
touches the master, outputs[], or any producer artefact).
"""

import copy
import datetime

from c6_contract import (
    NOT_SET, MANIFEST_KIND, MANIFEST_CONTRACT_VERSION, ASSEMBLED_BY,
    NOTICES, REQUIRED_MEMBER_FIELDS, APPROVAL_MANAGED_BY, IDENTITY_OWNER,
    FIDELITY_OWNER, FINGERPRINT_OWNER, APPROVAL_OWNER,
)
from c6_preservation import preserve_member
from c6_revision import compare_revisions
from c6_aggregate import aggregate_summary


def _assembly_timestamp():
    """When C6 assembled the manifest — explicitly labelled as such.

    This is NOT a production timestamp and must never be presented as one. No
    producer emits a production timestamp today, so that field stays NOT_SET
    rather than being back-filled from this value.
    """
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def assemble_manifest(records, identity=None, environment_evidence=None):
    """Assemble the external manifest.

    `records` is an iterable of (owner, record) pairs, e.g.
    [("C3", a_record), ("C5", b_record), ("C4", q_schedule)].

    Every record is treated as read-only; members are built from deep copies.
    """
    ident = identity if isinstance(identity, dict) else {}

    members = []
    for entry in (records or []):
        try:
            owner, record = entry
        except (TypeError, ValueError):
            continue
        members.append(preserve_member(record, owner, ident))

    manifest = {
        "manifest_kind": MANIFEST_KIND,
        "manifest_contract_version": MANIFEST_CONTRACT_VERSION,
        "written_to_master": False,
        "assembled_by": ASSEMBLED_BY,
        "project_id": ident.get("project_id", NOT_SET),
        "master_revision": ident.get("master_revision", NOT_SET),
        # labelled so it can never be read as a production time
        "manifest_assembly_timestamp": _assembly_timestamp(),
        "timestamp_kinds": {
            "manifest_assembly_timestamp": "when C6 assembled this manifest",
            "production_timestamp": "owned by the producing layer; NOT_SET "
                                    "when not declared",
            "evidence_timestamp": "owned by the evidence producer; NOT_SET "
                                  "when not declared",
        },
        "revision_view": compare_revisions(members),
        "aggregate_summary": aggregate_summary(members),
        "members": members,
        "ownership": {
            "fidelity": FIDELITY_OWNER,
            "engineering_fingerprint": FINGERPRINT_OWNER,
            "approval": APPROVAL_OWNER,
            "output_identity": IDENTITY_OWNER,
            "outputs_array": "E",
        },
        "environment_evidence": (copy.deepcopy(environment_evidence)
                                 if environment_evidence is not None
                                 else NOT_SET),
        "not_set_semantics": ("NOT_SET declares that a producer did not "
                              "declare the field, or that the value did not "
                              "reach C6. It is not failed, invalid, rejected, "
                              "incomplete, unknown or not-applicable."),
        "notices": list(NOTICES),
        "is_verdict": False,
    }
    return manifest


def manifest_field_report(manifest):
    """Which required fields are present on each member. Diagnostic only."""
    report = []
    for i, m in enumerate(manifest.get("members", [])):
        missing = [f for f in REQUIRED_MEMBER_FIELDS if f not in m]
        report.append({"index": i,
                       "source_owner": m.get("source_owner", NOT_SET),
                       "missing_required_fields": missing,
                       "has_completeness_detail":
                           "source_completeness_detail" in m})
    return report
