#!/usr/bin/env python3
"""
00.5-D — VERDICT MODEL

Turns a comparison report into a field-scoped verdict. D judges; it never
repairs, never regenerates and never rules on the master.

THE FIVE STATES
  VERIFIED        every field in scope was checked and agreed; nothing in
                  scope was left unverifiable
  FAILED          a proven disagreement: a differing value, a genuinely
                  missing element, an invented element, or a duplicate id
  PARTIAL         part verified, part NOT_VERIFIABLE, and nothing failed
  NOT_VERIFIABLE  nothing in scope could be judged
  ABSTAIN         no examination took place at all (no GA, no output,
                  output abstained, out of scope)

PRECEDENCE — binding
      FAILED > PARTIAL > VERIFIED
  One failure is never absorbed into a partial verdict.

  NOT_VERIFIABLE is its own state: it is neither a pass (false PASS) nor a
  failure (false FAIL). Collapsing it either way is the single most dangerous
  error available to this layer.
"""

VERIFIED = "VERIFIED"
FAILED = "FAILED"
PARTIAL = "PARTIAL"
NOT_VERIFIABLE = "NOT_VERIFIABLE"
ABSTAIN = "ABSTAIN"

FIDELITY_SCOPE = ("element_identity", "coordinates", "outline_points",
                  "element_presence")


def sufficiency_gate(ga_ref, extracted, output_status=None):
    """Return (sufficient, reason). Absence of evidence is never evidence."""
    if output_status == "ABSTAIN":
        return False, ("the producing layer abstained, so there is no output "
                       "to judge")
    if not isinstance(ga_ref, dict) or (not ga_ref.get("elements")
                                        and not ga_ref.get("outline")):
        return False, "no GA reference was supplied to compare against"
    if not isinstance(extracted, dict) or not extracted.get("readable"):
        return False, "the output artefact is not readable under the SEC"
    return True, None


def decide(comparison, ga_ref=None, extracted=None, output_status=None,
           scope=None):
    """Produce the field-scoped verdict record."""
    scope = list(scope or FIDELITY_SCOPE)

    sufficient, reason = sufficiency_gate(ga_ref, extracted, output_status)
    if not sufficient:
        return {
            "verdict": ABSTAIN,
            "scope": scope,
            "fields_checked": [],
            "fields_not_verifiable": [],
            "differences": [],
            "evidence": {"normalizations_applied":
                         (extracted or {}).get("normalizations_applied", [])},
            "reason": reason,
            "caveat": "ABSTAIN means no examination took place. It is not a "
                      "pass and not a failure.",
        }

    differences = comparison.get("differences", [])
    not_verifiable = comparison.get("not_verifiable", [])
    matched = comparison.get("matched_elements", [])

    if differences:
        verdict = FAILED
        reason = (f"{len(differences)} proven disagreement(s) between the "
                  f"output and the GA reference")
    elif not matched and not_verifiable:
        verdict = NOT_VERIFIABLE
        reason = ("nothing within scope could be judged; every candidate was "
                  "unverifiable")
    elif not_verifiable:
        verdict = PARTIAL
        reason = (f"{len(matched)} element(s) verified; "
                  f"{len(not_verifiable)} could not be judged")
    elif matched:
        verdict = VERIFIED
        reason = (f"all {len(matched)} element(s) within the declared scope "
                  f"agree with the GA reference")
    else:
        verdict = NOT_VERIFIABLE
        reason = "no comparable element was found within scope"

    # Field-level unverifiability always travels with the verdict, so an
    # overall result can never hide what was not examined (DEC-D-07).
    fields_nv = list(comparison.get("fields_not_verifiable", []))
    for nv in not_verifiable:
        fields_nv.append({"element_id": nv.get("element_id"),
                          "field": nv.get("field"),
                          "counterpart_present": nv.get("counterpart_present"),
                          "reason": nv.get("reason")})

    return {
        "verdict": verdict,
        "scope": scope,
        "fields_checked": list(comparison.get("fields_checked", [])),
        "fields_not_verifiable": fields_nv,
        "differences": differences,
        "evidence": {
            "matched_elements": matched,
            "declared_omissions_applied":
                comparison.get("declared_omissions_applied", []),
            "duplicate_ids": comparison.get("duplicate_ids", []),
            "extra_elements": comparison.get("extra_elements", []),
            "counterpart_index": comparison.get("counterpart_index", {}),
            "normalizations_applied":
                (extracted or {}).get("normalizations_applied", []),
        },
        "reason": reason,
        "caveat": ("This verdict applies ONLY to the fields listed in "
                   "fields_checked. Fields listed as not verifiable were not "
                   "judged and must not be read as agreement."),
    }
