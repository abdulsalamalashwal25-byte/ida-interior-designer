#!/usr/bin/env python3
"""
00.5-C6 — CONTRACT CONSTANTS & SEMANTIC BOUNDARIES

Reference (all CLOSED):
  00.5-C6-ARCHITECTURE-CLOSURE-REPORT.md
  00.5-C6-ARCHITECTURE-CLOSURE-REVISION-R02.md
  00.5-C6-ARCHITECTURE-CLOSURE-REVISION-R03.md
  00.5-C6-GATE1-IMPLEMENTATION-PLAN-AND-TEST-CONTRACT.md  (Gate 1 APPROVED)

C6 IS
  A Manifest / Evidence Assembler with the fewest possible semantics.
      Preserve -> Compare mechanically -> Count mechanically -> Assemble -> Stop.

C6 IS NOT
  validator · fidelity checker · engineering judge · approval engine ·
  governance engine · designer · geometry engine · quantity engine ·
  fingerprint authority · identity authority.

THIS MODULE holds the vocabulary only. It contains no assembly, no comparison,
no counting and no judgement — so that the allowed values live in exactly one
place and cannot drift.
"""

# --------------------------------------------------------------------------
# NOT_SET — the single value C6 itself may introduce.
#
# It means, and only means:
#     "the producer did not declare this field / the value never reached C6".
#
# It is NOT: failed · invalid · rejected · incomplete · unknown ·
#            not applicable · an engineering fact of any kind.
# It is NOT interchangeable with UNKNOWN (owned by B7), NOT_PRESENT (a
# declared absence in the master) or ABSTAIN (a layer's own decision).
# --------------------------------------------------------------------------
NOT_SET = "NOT_SET"

NOT_SET_MEANS = ("the producer did not declare this field, or the value did "
                 "not reach C6")
NOT_SET_DOES_NOT_MEAN = ("failed", "invalid", "rejected", "incomplete",
                         "unknown", "not applicable")

# --- producers -------------------------------------------------------------
OWNER_C3 = "C3"
OWNER_C4 = "C4"
OWNER_C5 = "C5"
KNOWN_OWNERS = (OWNER_C3, OWNER_C4, OWNER_C5)

# --- the three INDEPENDENT status-like fields ------------------------------
# Separate on purpose: C4 has no `status` at all, C3 has no completeness
# notion, and only C5 declares `coverage`. Carrying one field's value in
# another field's slot would rename its meaning (AS-C6-23).
STATUS_VALUES = ("EMITTED", "ABSTAIN", NOT_SET)
COVERAGE_VALUES = ("COMPLETE", "PARTIAL", NOT_SET)
COMPLETENESS_VALUES = ("COMPLETE", "PARTIAL", "ABSTAIN", NOT_SET)

# Which producer is entitled to declare which field. A producer absent from a
# list must carry NOT_SET there — never a derived value.
DECLARES_STATUS = (OWNER_C3, OWNER_C5)
DECLARES_COVERAGE = (OWNER_C5,)
DECLARES_COMPLETENESS = (OWNER_C4,)

# --- class / channel -------------------------------------------------------
CLASS_VALUES = ("A", "B", "C", NOT_SET)

# producer_channel stays NOT_SET in this version: no producer emits the field
# and no Contract Registry exists (DEC-C6-11 is out of scope). Inferring it
# from a contract name, a format, an SVG comment, a filename, a missing class
# or C6's own knowledge is forbidden (AS-C6-24).
PRODUCER_CHANNEL_VALUES = (NOT_SET,)
FORBIDDEN_CHANNEL_SOURCES = ("contract", "format", "svg_comment", "filename",
                             "missing_class", "c6_internal_knowledge",
                             "naming_convention")

# --- boundaries owned elsewhere -------------------------------------------
FIDELITY_VALUE = "NOT_ASSESSED"          # D owns the judgement
FIDELITY_OWNER = "D"

FINGERPRINT_VALUE = "NOT_ISSUED"         # C2 owns it; issuance is blocked
FINGERPRINT_OWNER = "C2"

APPROVAL_MANAGED_BY = "E"                # architectural ownership metadata
APPROVAL_OWNER = "E"

IDENTITY_OWNER = "E"                     # official output_id belongs to E

DETERMINISM_DEFAULT = {"D0": NOT_SET,
                       "D1": "NOT_ESTABLISHED",
                       "D2": "NOT_CLAIMED"}

# --- parent / provenance ---------------------------------------------------
PARENT_PRESENT = "PRESENT"
PARENT_MISSING = "MISSING"
PARENT_EVIDENCE_VALUES = (PARENT_PRESENT, PARENT_MISSING)

# --- revision comparison (mechanical metadata, never a verdict) ------------
DIV_NONE_OBSERVED = "NONE_OBSERVED"
DIV_OBSERVED = "OBSERVED"
DIV_NOT_DETERMINABLE = "NOT_DETERMINABLE"
DIVERGENCE_VALUES = (DIV_NONE_OBSERVED, DIV_OBSERVED, DIV_NOT_DETERMINABLE)

# --- manifest header -------------------------------------------------------
MANIFEST_KIND = "EXTERNAL_OUTPUT_MANIFEST"
MANIFEST_CONTRACT_VERSION = "C6-L2-R03"
ASSEMBLED_BY = "C6"

# Required member fields (Gate 1 section 16). Optional ones appear only when
# the producer declared them.
REQUIRED_MEMBER_FIELDS = (
    "source_owner", "source_status", "source_coverage", "source_completeness",
    "producer_channel", "declared_class", "contract", "format",
    "approval_managed_by", "approval_value", "parent_ref", "parent_evidence",
    "fidelity", "engineering_fingerprint", "determinism", "output_id",
)

OPTIONAL_MEMBER_FIELDS = (
    "source_completeness_detail", "omissions", "exclusions",
    "parameters_admitted", "parameters_rejected", "lineage_evidence",
    "environment_evidence", "capability", "limitations",
    "production_timestamp", "evidence_timestamp",
)

# --- notices that travel WITH the manifest --------------------------------
NOTICES = (
    "provenance is not fidelity",
    "lineage is not engineering identity",
    "the existence of this manifest is not evidence of fidelity",
    "the three aggregate counters are mechanical and separate; they are not "
    "to be combined",
    "NOT_SET declares an absent input, it is not a verdict",
    "revision_view is mechanical comparison metadata, not an engineering "
    "verdict",
    "approval_managed_by is architectural ownership metadata, not an "
    "approval state",
    "this manifest is assembled evidence, not a verdict",
)
