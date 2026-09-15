#!/usr/bin/env python3
"""
schema_gate.py — Phase 00.5-A (R02)
Validation gate for project_master.json.

THREE LAYERS, deliberately separated:
  1. SCHEMA      — structural + provenance rules expressible in JSON Schema.
  2. INVARIANTS  — cross-field rules JSON Schema structurally CANNOT express
                   (no $data / sibling comparison in Draft 2020-12).
  3. GOVERNANCE  — rules that cannot be enforced by data at all, only surfaced.
                   These BLOCK FINAL APPROVAL but do not make a file invalid.

Geometric truth is NOT handled here. That is validate.py (Phase 00.5-B).
"""

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SYSTEM_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SYSTEM_DIR / "project_master.schema.json"

# Rules that are deliberately OUT OF SCOPE for the schema layer.
SCHEMA_CANNOT_ENFORCE = [
    "Geometric truth (wall closure, furniture overlap, corridor widths, door swing arcs).",
    "Cross-reference integrity of geometry refs (host_wall / zone_ref existence).",
    "Whether a [D] formula is arithmetically CORRECT (only that it is declared).",
    "Whether a locked value was actually changed between two revisions (needs diffing).",
    "Whether master_hash is the true hash of the file content (needs computation).",
    "Semantic honesty of free text (a rationale can be schema-valid and still be nonsense).",
    "Whether an approval genuinely came from the user (no cryptographic identity available).",
    "Whether an external citation is real or fabricated (URL is not fetched at validation time).",
]

# Governance gaps: known, accepted, deferred. Recorded so the system never forgets.
GOVERNANCE_GAPS = [
    {
        "id": "GAP-01",
        "title": "Source impersonation",
        "detail": "source_ref is free text. The agent could write 'client said X' with no proof.",
        "severity": "HIGH",
        "owner_phase": "00.5-E",
        "mitigation": "Bind every CLIENT_INPUT to a message id / file in 01_INPUTS/.",
    },
    {
        "id": "GAP-02",
        "title": "Approval impersonation",
        "detail": "approved_by:'USER' is written by the agent. The schema stops the agent "
                  "approving under its OWN name; it cannot stop it writing the USER's name.",
        "severity": "HIGH",
        "owner_phase": "00.5-E",
        "mitigation": "External approval ledger, append-only, written only on an explicit "
                      "APPROVE command. Until then final approval is BLOCKED by INV-APPR2.",
    },
    {
        "id": "GAP-03",
        "title": "Free-text semantic honesty",
        "detail": "A rationale of sufficient length passes validation regardless of quality.",
        "severity": "MEDIUM",
        "owner_phase": "Human review at gates",
        "mitigation": "User review. Not automatable.",
    },
    {
        "id": "GAP-04",
        "title": "Citation authenticity",
        "detail": "external.ref / url are not fetched or verified at validation time.",
        "severity": "MEDIUM",
        "owner_phase": "00.5-F",
        "mitigation": "Closed source list, shown to the user before any figure is used.",
    },
    {
        "id": "GAP-B3-01",
        "title": "Furniture position datum is undeclared",
        "detail": "The Phase 00.5-A schema does not say whether furniture.position "
                  "is the centre or a corner of the footprint. B3 declares CENTER as a "
                  "validation convention. The SAME coordinates yield a different "
                  "footprint under a CORNER reading, so overlap verdicts depend on it.",
        "severity": "CLOSED",
        "owner_phase": "Closed in Phase 00.5-B3 R02",
        "mitigation": "RESOLVED: furniture.position_reference added (CENTER / "
                      "CORNER_MIN / CORNER_MAX). Absence = UNKNOWN and blocks "
                      "geometric judgement; CENTER is never assumed.",
    },
    {
        "id": "GAP-B3-02",
        "title": "Furniture rotation is not modelled",
        "detail": "There is no rotation field, so B3 treats every footprint as "
                  "axis-aligned. A rotated piece is checked against the wrong "
                  "rectangle, which can produce both false negatives and false "
                  "positives in overlap and clearance checks.",
        "severity": "CLOSED",
        "owner_phase": "Closed in Phase 00.5-B3 R02",
        "mitigation": "RESOLVED: furniture.rotation added (degrees). Absence = "
                      "UNKNOWN and blocks dependent judgement; 0 is never assumed. "
                      "Engine uses true rotated polygons (SAT), not bounding boxes.",
    },
    {
        "id": "GAP-05",
        "title": "Design-judgement smuggling via [D]",
        "detail": "INV-D2 uses keyword heuristics on the formula text. A carefully worded "
                  "design choice could still be dressed as arithmetic.",
        "severity": "MEDIUM",
        "owner_phase": "00.5-B + human review",
        "mitigation": "Formula re-computation in validate.py; user review at gates.",
    },
]

# Language that betrays a design CHOICE being smuggled into a [D] derivation.
CHOICE_LANGUAGE = re.compile(
    r"(choose|chosen|select|prefer|better|nicer|optimal|recommend|suggest|should be|"
    r"اختيار|نختار|يفضل|أفضل|الأنسب|نقترح|يُستحسن|الأجمل|مناسب)",
    re.IGNORECASE,
)


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Fact walker
# ---------------------------------------------------------------------------
def _is_fact(node):
    return isinstance(node, dict) and "status" in node and "source_type" in node


def iter_facts(node, path=""):
    """Yield (path, fact_dict) for every provenance-wrapped fact in the tree."""
    if _is_fact(node):
        yield path, node
        return
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_facts(v, f"{path}/{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_facts(v, f"{path}/{i}")


def resolve_fact(data, ref):
    """Resolve a derived_from reference like 'space.outline' or 'walls/0/thickness'."""
    parts = re.split(r"[./]", ref.strip())
    cur = data
    for p in parts:
        if isinstance(cur, list):
            if not p.isdigit() or int(p) >= len(cur):
                return None
            cur = cur[int(p)]
        elif isinstance(cur, dict):
            if p not in cur:
                # allow addressing an element by its id, e.g. walls.W-01.thickness
                found = None
                if isinstance(cur, dict):
                    for v in cur.values():
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict) and item.get("id") == p:
                                    found = item
                                    break
                if found is None:
                    return None
                cur = found
            else:
                cur = cur[p]
        else:
            return None
    return cur if _is_fact(cur) else None


# Collections governed by the presence register (Gate 00.5-A R02 §5).
PRESENCE_COLLECTIONS = {
    "columns": "columns",
    "openings": "openings",
}


# ---------------------------------------------------------------------------
# LAYER 2 — INVARIANTS
# ---------------------------------------------------------------------------
def check_invariants(data):
    """Cross-field rules JSON Schema cannot express. Each returns a hard error."""
    problems = []

    # -- INV-TF1 / INV-TF2 : Technical Fix equality obligations -------------
    changelog = (data.get("registers") or {}).get("changelog") or []
    for i, entry in enumerate(changelog):
        if entry.get("type") != "TECHNICAL_FIX":
            continue
        loc = f"registers/changelog/{i}"
        hb, ha = entry.get("master_hash_before"), entry.get("master_hash_after")
        gb, ga = entry.get("geometry_version_before"), entry.get("geometry_version_after")
        if hb != ha:
            problems.append(
                f"[{loc}] INV-TF1 violated: TECHNICAL_FIX changed master_hash "
                f"({hb} -> {ha}). Design Master was modified — this must be a CR, not a fix."
            )
        if gb != ga:
            problems.append(
                f"[{loc}] INV-TF2 violated: TECHNICAL_FIX changed geometry_version "
                f"({gb} -> {ga}). Geometry was modified — this must be a CR, not a fix."
            )

    # -- INV-D1 : a [D] may only be derived from trustworthy inputs ---------
    # Allowed input statuses: C (confirmed), D (already derived), A only if APPROVED.
    for path, fact in iter_facts(data):
        if fact.get("status") != "D":
            continue
        for ref in fact.get("derived_from", []):
            src = resolve_fact(data, ref)
            if src is None:
                # OWNERSHIP: reference EXISTENCE belongs to validate_refs (XR-008,
                # Phase 00.5-B1). This layer only judges the TRUSTWORTHINESS of a
                # reference that does resolve. Skipping here prevents two layers
                # reporting the same defect under different rule codes.
                continue
            st = src.get("status")
            if st in ("U", "P"):
                problems.append(
                    f"[{path}] INV-D1 violated: derived from '{ref}' which is [{st}] "
                    f"(not confirmed). A derivation cannot be more certain than its input."
                )
            elif st == "A" and src.get("approval_state") != "APPROVED":
                problems.append(
                    f"[{path}] INV-D1 violated: derived from assumption '{ref}' that is "
                    f"not APPROVED ({src.get('approval_state')})."
                )

    # -- INV-D2 : [D] must not smuggle a design decision --------------------
    for path, fact in iter_facts(data):
        if fact.get("status") != "D":
            continue
        blob = f"{fact.get('formula', '')} {fact.get('note', '')}"
        if CHOICE_LANGUAGE.search(blob):
            problems.append(
                f"[{path}] INV-D2 violated: [D] formula/note contains choice or preference "
                f"language. A design judgement is a [P] requiring approval, never a [D]."
            )
        if fact.get("derivation_type") == "LOGICAL_DEDUCTION" and not fact.get("note"):
            problems.append(
                f"[{path}] INV-D2 violated: LOGICAL_DEDUCTION requires an explicit note "
                f"proving the deduction is forced, not chosen."
            )

    # -- INV-S1 : presence register must agree with the actual collections --
    preg = data.get("presence_register") or {}
    for coll, key in PRESENCE_COLLECTIONS.items():
        pfact = preg.get(key)
        if pfact is None:
            continue
        items = data.get(coll)
        if items is None:
            continue
        presence = pfact.get("presence")
        n = len(items)
        if presence == "NOT_PRESENT" and n > 0:
            problems.append(
                f"[{coll}] INV-S1 violated: presence_register says NOT_PRESENT but "
                f"{n} item(s) are defined."
            )
        if presence == "PRESENT" and n == 0:
            problems.append(
                f"[{coll}] INV-S1 violated: presence_register says PRESENT but the "
                f"collection is empty. An empty list is not data."
            )
        if presence == "UNKNOWN" and n > 0:
            problems.append(
                f"[{coll}] INV-OPEN1 violated: presence is UNKNOWN yet {n} item(s) exist. "
                f"Elements were invented for something nobody has confirmed."
            )

    # -- INV-APPR1 / INV-APPR3 : REMOVED FROM THIS LAYER (Phase 00.5-B1 refactor).
    #    Verifying that a decision_id / linked_proposal actually EXISTS is a
    #    cross-reference concern. It is now owned exclusively by validate_refs
    #    (XR-006 and XR-010). Duplicating it here produced two rule codes for a
    #    single defect and made "exactly one rule fired" untestable.

    return problems


# ---------------------------------------------------------------------------
# LAYER 3 — GOVERNANCE (does not invalidate the file; blocks FINAL approval)
# ---------------------------------------------------------------------------
def final_approval_readiness(data):
    """Return (ready: bool, blockers: list[str]).

    A schema-valid file is NOT automatically approvable. This is where
    GAP-02 is honoured: a hand-written approval is recorded but is NOT
    sufficient evidence until the 00.5-E approval ledger exists.
    """
    blockers = []

    # Blocking unknowns
    for u in (data.get("registers") or {}).get("unknowns", []):
        if u.get("blocking") and not u.get("resolved_on"):
            blockers.append(f"BLOCKING UNKNOWN {u.get('id')} unresolved: {u.get('question')}")

    # Unknown presence of a structural element
    for key, pfact in (data.get("presence_register") or {}).items():
        if isinstance(pfact, dict) and pfact.get("presence") == "UNKNOWN":
            blockers.append(
                f"PRESENCE UNKNOWN for '{key}' — existence never confirmed or denied."
            )

    # Pending assumptions
    for a in (data.get("registers") or {}).get("assumptions", []):
        if a.get("approval_state") == "PENDING_APPROVAL":
            blockers.append(f"ASSUMPTION {a.get('id')} still pending approval.")

    # Open CRs / objections
    for cr in (data.get("registers") or {}).get("change_requests", []):
        if cr.get("state") in ("DRAFT", "PENDING_APPROVAL"):
            blockers.append(f"CHANGE REQUEST {cr.get('id')} is {cr.get('state')}.")
    for o in (data.get("registers") or {}).get("objections", []):
        if o.get("state") == "OPEN":
            blockers.append(f"OBJECTION {o.get('id')} is OPEN and unanswered.")

    # KNOWN CONFLICT flags
    for path, fact in iter_facts(data):
        if fact.get("conflict"):
            blockers.append(
                f"KNOWN CONFLICT at {path} ({fact['conflict'].get('cr_id')}) unresolved."
            )

    # GAP-02: unverifiable approvals
    approvals = [p for p, f in iter_facts(data) if f.get("approved_by") == "USER"]
    if approvals:
        blockers.append(
            f"GAP-02: {len(approvals)} approval(s) rest on self-written data with no "
            f"approval ledger. Not sufficient for FINAL approval until Phase 00.5-E."
        )

    return (len(blockers) == 0), blockers


# ---------------------------------------------------------------------------
# LAYER 1 + 2 combined
# ---------------------------------------------------------------------------
def validate_master(data, schema=None):
    """Full gate: JSON Schema rules PLUS code-level invariants.
    Return (ok: bool, errors: list[str])."""
    schema = schema or load_schema()
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"[{path}] {err.message}")
    errors.extend(check_invariants(data))
    return (len(errors) == 0), errors


# ---------------------------------------------------------------------------
# Caption lint — the "100%" language policy (Spec R01 §11).
# ---------------------------------------------------------------------------
FORBIDDEN_IN_CLASS_C = re.compile(
    r"(100\s*%|100\s*٪|مطابق|متطابق|identical|exact match|pixel[- ]accurate)",
    re.IGNORECASE,
)

APPROVED_GUARANTEE_LANGUAGE = {
    "A": "Deterministic geometric match to Design Master {rev} — testable.",
    "B": "Geometry deterministically derived from Design Master {rev}; visual treatment "
         "may differ. Not a substitute for Class A.",
    "C": "Not geometrically guaranteed. Non-binding inspiration only.",
}


def lint_caption(cls, text):
    problems = []
    if cls == "C" and FORBIDDEN_IN_CLASS_C.search(text or ""):
        problems.append("Class C caption uses match/100% language — forbidden by Spec R01 §11.")
    return problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: schema_gate.py <master.json>")
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}

    ok, errs = validate_master(payload)
    print("SCHEMA + INVARIANTS:", "PASS" if ok else f"FAIL ({len(errs)} error(s))")
    for e in errs:
        print("  -", e)

    ready, blockers = final_approval_readiness(payload)
    print("\nFINAL APPROVAL READINESS:", "READY" if ready else "BLOCKED")
    for b in blockers:
        print("  !", b)

    sys.exit(0 if ok else 1)
