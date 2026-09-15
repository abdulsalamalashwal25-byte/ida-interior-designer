#!/usr/bin/env python3
"""
00.5-F — SOURCE / REFERENCE ITEM / REFERENCE ATTRIBUTE / EVIDENCE

Reference (APPROVED / LOCKED):
  00.5-F-ARCHITECTURE-LIBRARY-REFERENCE-STANDARDS.md   (R01)
  00.5-F-ARCHITECTURE-SPECIFICATION-R02.md             (R02)
  00.5-F-ARCHITECTURE-SPECIFICATION-R03.md             (R03)

WHAT F OWNS
  Describing external sources: their declared identity, their SCOPED
  authority, what verification was actually performed, whether they are still
  valid, whether they apply, and how they conflict.

  F describes; F does not decide.

WHAT F NEVER DOES
  * create [D] — a derived value needs formula + derived_from and is governed
    by B6. F cannot produce one and cannot grant eligibility for one.
  * create [C] — confirmation comes from USER approval through E.
  * promote anything, silently or otherwise.
  * certify compliance, publisher identity, or cryptographic authenticity.

source_type IS DESCRIPTIVE ONLY (R02 / ST-1..ST-5)
  It grants no trust, no authority, no verification, no validity, no
  applicability and no compliance. Authority is attribute-scoped, never a
  global rank for a source.
"""

# --- source_type: a descriptive label. NOT a trust level, NOT a rank. -----
# Kept as a vocabulary for description only. DEC-F-01 was REFRAMED: there is
# no Global Source Trust Enum in V1.
SOURCE_TYPES = (
    "OFFICIAL_MANUFACTURER", "OFFICIAL_STANDARD_AUTHORITY",
    "VERIFIED_TECHNICAL_DOCUMENT", "TRUSTED_REFERENCE_DATABASE",
    "SECONDARY_REFERENCE", "USER_PROVIDED", "AGENT_RESEARCH",
    "AI_GENERATED", "UNKNOWN_UNVERIFIED",
)

SOURCE_TYPE_IS_DESCRIPTIVE_ONLY = True

# Sources that can never be used as engineering evidence, whatever else is
# recorded about them.
NEVER_ENGINEERING_EVIDENCE = ("AI_GENERATED",)

NOT_SET = "NOT_SET"

# --- verification (R02 section 8) ------------------------------------------
UNVERIFIED = "UNVERIFIED"                 # the default, always
CITATION_RECORDED = "CITATION_RECORDED"
RETRIEVED = "RETRIEVED"
CONTENT_CHECKED = "CONTENT_CHECKED"
UNREACHABLE = "UNREACHABLE"
CONTRADICTED = "CONTRADICTED"
NOT_VERIFIABLE = "NOT_VERIFIABLE"

VERIFICATION_STATES = (UNVERIFIED, CITATION_RECORDED, RETRIEVED,
                       CONTENT_CHECKED, UNREACHABLE, CONTRADICTED,
                       NOT_VERIFIABLE)

# What CONTENT_CHECKED means — and the seven things it does NOT mean.
CONTENT_CHECKED_MEANS = (
    "the content was retrieved, the material was read, and it was compared "
    "against the recorded reference claim, by the verification means "
    "available")
CONTENT_CHECKED_DOES_NOT_MEAN = (
    "the source did not err",
    "the publisher is authentic",
    "the data is true in reality",
    "the product matches reality",
    "the information suits this project",
    "the information satisfies a code",
    "any compliance verification took place",
)

# --- validity (R02 section 9) ----------------------------------------------
VALIDITY_UNKNOWN = "VALIDITY_UNKNOWN"     # default
CURRENT = "CURRENT"
SUPERSEDED = "SUPERSEDED"
EXPIRED = "EXPIRED"
WITHDRAWN = "WITHDRAWN"

VALIDITY_STATES = (VALIDITY_UNKNOWN, CURRENT, SUPERSEDED, EXPIRED, WITHDRAWN)

# --- applicability (R02 section 10) ----------------------------------------
APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"   # default
APPLICABLE_DECLARED = "APPLICABLE_DECLARED"
NOT_APPLICABLE = "NOT_APPLICABLE"
PARTIALLY_APPLICABLE = "PARTIALLY_APPLICABLE"

APPLICABILITY_STATES = (APPLICABILITY_UNKNOWN, APPLICABLE_DECLARED,
                        NOT_APPLICABLE, PARTIALLY_APPLICABLE)

APPLICABILITY_DIMENSIONS = ("country", "region", "market", "supplier",
                            "currency", "units", "project_type", "standard",
                            "law")

# --- authority (R02 section 7 · R03 amendment 2) ---------------------------
AUTHORITATIVE = "AUTHORITATIVE"
NOT_AUTHORITATIVE = "NOT_AUTHORITATIVE"


class Source:
    """An external source, described. Its identity is DECLARED, not proven."""

    __slots__ = ("source_id", "source_type", "source_identity",
                 "source_version", "document_reference", "citation",
                 "retrieved_on", "retrieved_by", "authority_scope",
                 "verification_state", "validity")

    def __init__(self, source_id, source_type=NOT_SET, source_identity=NOT_SET,
                 source_version=NOT_SET, document_reference=NOT_SET,
                 citation=NOT_SET, retrieved_on=NOT_SET, retrieved_by=NOT_SET,
                 authority_scope=None, verification_state=None,
                 validity=None):
        # Resolved at CALL time, not frozen as a default at import time.
        # A default argument would pin the constant when the module is first
        # loaded, which both hides later configuration and silently masks
        # mutation testing (AS-C4-18).
        if verification_state is None:
            verification_state = UNVERIFIED
        if validity is None:
            validity = VALIDITY_UNKNOWN
        self.source_id = source_id
        self.source_type = source_type
        # Declared by whoever supplied it. F does not verify publisher
        # identity and never claims to (GAP-F-02 remains OPEN).
        self.source_identity = source_identity
        self.source_version = source_version
        self.document_reference = document_reference
        self.citation = citation
        self.retrieved_on = retrieved_on
        self.retrieved_by = retrieved_by
        # [{attribute, authoritative, basis}] — absence means NOT_AUTHORITATIVE
        self.authority_scope = list(authority_scope or [])
        self.verification_state = verification_state
        self.validity = validity

    def as_dict(self):
        return {"source_id": self.source_id, "source_type": self.source_type,
                "source_type_is_descriptive_only": True,
                "source_identity_declared": self.source_identity,
                "source_version": self.source_version,
                "document_reference": self.document_reference,
                "citation": self.citation, "retrieved_on": self.retrieved_on,
                "retrieved_by": self.retrieved_by,
                "authority_scope": list(self.authority_scope),
                "verification_state": self.verification_state,
                "validity": self.validity}


class ReferenceItem:
    """The thing a source refers to (a product, a material, a clause)."""

    __slots__ = ("item_id", "source_id", "name", "snapshot_id")

    def __init__(self, item_id, source_id, name=NOT_SET, snapshot_id=NOT_SET):
        self.item_id = item_id
        self.source_id = source_id
        self.name = name
        self.snapshot_id = snapshot_id

    def as_dict(self):
        return {"item_id": self.item_id, "source_id": self.source_id,
                "name": self.name, "snapshot_id": self.snapshot_id}


class ReferenceAttribute:
    """One attribute taken from an item — the unit of authority AND checking.

    A value here is a REFERENCE VALUE. It is not a project fact, and it has no
    status in the master's vocabulary.
    """

    __slots__ = ("attribute_id", "item_id", "attribute", "value", "unit",
                 "evidence_ref")

    def __init__(self, attribute_id, item_id, attribute, value=NOT_SET,
                 unit=NOT_SET, evidence_ref=NOT_SET):
        self.attribute_id = attribute_id
        self.item_id = item_id
        self.attribute = attribute
        self.value = value
        self.unit = unit
        self.evidence_ref = evidence_ref

    def as_dict(self):
        return {"attribute_id": self.attribute_id, "item_id": self.item_id,
                "attribute": self.attribute, "value": self.value,
                "unit": self.unit, "evidence_ref": self.evidence_ref,
                "is_project_fact": False,
                "note": "a reference value, not a project fact"}


class Evidence:
    """Supporting material. Its existence does not make the claim true."""

    __slots__ = ("evidence_id", "kind", "locator", "note")

    def __init__(self, evidence_id, kind, locator=NOT_SET, note=NOT_SET):
        self.evidence_id = evidence_id
        self.kind = kind
        self.locator = locator
        self.note = note

    def as_dict(self):
        return {"evidence_id": self.evidence_id, "kind": self.kind,
                "locator": self.locator, "note": self.note,
                "supports_claim": True, "proves_claim": False,
                "caveat": "evidence supports a recorded claim; it does not "
                          "prove the claim is true"}


# --------------------------------------------------------------------------
# Authority — attribute-scoped only (R03 amendment 2)
# --------------------------------------------------------------------------
def authority_for(source, attribute):
    """Is this source authoritative for THIS attribute?

    Absence of an entry means NOT_AUTHORITATIVE. Being outside the declared
    scope is NOT a violation by the source: the source never claimed
    authority there. It simply means the value is not eligible for
    authoritative use from this source for this attribute.
    """
    for entry in source.authority_scope:
        if entry.get("attribute") == attribute:
            authoritative = bool(entry.get("authoritative"))
            return {
                "attribute": attribute,
                "result": AUTHORITATIVE if authoritative
                else NOT_AUTHORITATIVE,
                "basis": entry.get("basis", NOT_SET),
                "declared": True,
                "is_source_violation": False,
                "note": ("declared authoritative for this attribute"
                         if authoritative else
                         "declared NOT authoritative for this attribute; the "
                         "value may still be used as reference context"),
            }
    return {
        "attribute": attribute,
        "result": NOT_AUTHORITATIVE,
        "basis": NOT_SET,
        "declared": False,
        "is_source_violation": False,
        "note": ("no authority declared for this attribute, so it defaults to "
                 "NOT_AUTHORITATIVE. This is not a violation by the source — "
                 "the source made no claim here. The value remains usable as "
                 "reference context only."),
    }


def verification_report(source):
    """What verification actually happened — and what it does not imply."""
    return {
        "verification_state": source.verification_state,
        "means": (CONTENT_CHECKED_MEANS
                  if source.verification_state == CONTENT_CHECKED else NOT_SET),
        "does_not_mean": list(CONTENT_CHECKED_DOES_NOT_MEAN),
        "boundaries": [
            "CITATION_RECORDED is not RETRIEVED",
            "RETRIEVED is not a verified source",
            "CONTENT_CHECKED is not engineering truth",
        ],
        "citation_authenticity": "NOT_VERIFIED — GAP-F-02 remains OPEN",
    }


def applicability_report(declared_state=None, dimensions=None):
    """Applicability is DECLARED by a human, never inferred by F."""
    state = declared_state or APPLICABILITY_UNKNOWN
    if state not in APPLICABILITY_STATES:
        state = APPLICABILITY_UNKNOWN
    described = {d: (dimensions or {}).get(d, NOT_SET)
                 for d in APPLICABILITY_DIMENSIONS}
    return {
        "state": state,
        "dimensions_described": described,
        "inferred_by_f": False,
        "note": ("F describes applicability dimensions. It never infers that "
                 "a source applies because it is global or official. "
                 "Declaring applicability is a governance/user act."),
    }
