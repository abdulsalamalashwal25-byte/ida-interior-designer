#!/usr/bin/env python3
"""
00.5-D — STRUCTURED FIDELITY REPORT (DEC-D-06)

Assembles the verdict into a structured report and returns it. D writes no
file, modifies nothing, and issues no judgement beyond output-vs-GA fidelity.

BOUNDARIES CARRIED IN EVERY REPORT
  * D judges Output vs GA only. GA vs Master belongs to C3 provenance.
  * provenance, element counts and visual similarity are NOT fidelity.
  * D owns no identity, no fingerprint, no approval and no outputs[].
  * D never repairs, regenerates or proposes a corrected value.
"""

from d_sec import extract, ga_reference
from d_compare import compare
from d_verdict import decide

REPORT_KIND = "FIDELITY_REPORT"
REPORT_CONTRACT_VERSION = "D-V1-R02"

NOTICES = (
    "D judges Output vs GA only; GA vs Master is owned by C3 provenance",
    "provenance is not fidelity",
    "element count is not fidelity",
    "visual similarity is not geometric fidelity",
    "NOT_VERIFIABLE is neither a pass nor a failure",
    "this verdict is bounded by fields_checked",
    "D describes disagreement; it never repairs or regenerates",
)


def assess(ga_artifact, output_svg, output_class="A", output_status=None):
    """Assess one output against the GA artifact it claims to represent."""
    ga_ref = ga_reference(ga_artifact)
    extracted = extract(output_svg)
    comparison = compare(ga_ref, extracted)
    verdict = decide(comparison, ga_ref=ga_ref, extracted=extracted,
                     output_status=output_status)

    return {
        "report_kind": REPORT_KIND,
        "report_contract_version": REPORT_CONTRACT_VERSION,
        "output_class": output_class,
        "reference": "GA artifact (record['assembly'])",
        "verdict": verdict["verdict"],
        "scope": verdict["scope"],
        "fields_checked": verdict["fields_checked"],
        "fields_not_verifiable": verdict["fields_not_verifiable"],
        "differences": verdict["differences"],
        "evidence": verdict["evidence"],
        "reason": verdict["reason"],
        "caveat": verdict["caveat"],
        "repaired": False,
        "regenerated": False,
        "master_assessed": False,
        "notices": list(NOTICES),
    }


def assess_pair(ga_artifact, a_svg, b_svg):
    """Assess A and B, each DIRECTLY against GA (DEC-D-05).

    B is never validated against A as the sole reference; agreement between
    them is recorded as an observation only.
    """
    return {
        "report_kind": REPORT_KIND,
        "report_contract_version": REPORT_CONTRACT_VERSION,
        "reference": "GA artifact (record['assembly'])",
        "A": assess(ga_artifact, a_svg, output_class="A"),
        "B": assess(ga_artifact, b_svg, output_class="B"),
        "note": ("A and B were each compared directly against GA. Agreement "
                 "between A and B is not used as a reference and is not a "
                 "fidelity claim."),
    }
