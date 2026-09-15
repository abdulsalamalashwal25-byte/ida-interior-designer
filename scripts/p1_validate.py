#!/usr/bin/env python3
"""
PHASE 01 — G3 · SCHEMA VALIDATION  +  G4 · RULE VALIDATION

Phase 01 CALLS the validators and ASSEMBLES their results as references.

O-3 CONTRACT (A-05) — binding
  * validators are invoked, never re-implemented
  * severity is never reinterpreted
  * an ERROR is never softened, never turned into a WARNING
  * a validator result is never converted into a different result
  * the issuing validator keeps ownership of its own verdict

Phase 01 is a carrier here, exactly as C6 is an assembler: what the layer did
not say, Phase 01 does not say.
"""

import schema_gate
import validate_refs
import validate_topology
import validate_furniture
import validate_movement
import validate_doors
import validate_formulas
import validate_blocking
import validate_outputs
import validate_revisions
import validate_lifecycle
import validate_temporal

PASS = "PASS"
FAIL = "FAIL"

# The B-series, in order, each with the module that OWNS its verdict.
RULE_VALIDATORS = (
    ("B1", "validate_refs", validate_refs.validate_references),
    ("B2", "validate_topology", validate_topology.validate_topology),
    ("B3", "validate_furniture", validate_furniture.validate_furniture),
    ("B4", "validate_movement", validate_movement.validate_movement),
    ("B5", "validate_doors", validate_doors.validate_doors),
    ("B6", "validate_formulas", validate_formulas.validate_formulas),
    ("B7", "validate_blocking", validate_blocking.validate_blocking),
    ("B8", "validate_outputs", validate_outputs.validate_outputs),
    ("B9", "validate_revisions", validate_revisions.validate_revisions),
    ("B10", "validate_lifecycle", validate_lifecycle.validate_lifecycle),
    ("B11", "validate_temporal", validate_temporal.validate_temporal),
)


def _findings_of(result):
    """Extract the findings list from a validator's return value.

    Validators return tuples of differing arity. The findings list is taken
    as-is; nothing in it is altered.
    """
    if isinstance(result, tuple):
        for element in result:
            if isinstance(element, list):
                return element
        return []
    if isinstance(result, list):
        return result
    return []


def _severity_of(finding):
    """Read the severity the validator assigned. Never recompute it."""
    return getattr(finding, "severity", None)


def _as_reference(layer, module_name, finding):
    """Carry one finding as a reference, verbatim."""
    return {
        "layer": layer,
        "owner_module": module_name,
        "rule": getattr(finding, "rule", None),
        "location": getattr(finding, "location", None),
        "message": getattr(finding, "message", None),
        # carried exactly as issued — never reinterpreted (O3-2)
        "severity": _severity_of(finding),
        "verdict_owner": module_name,
    }


def run_schema_gate(master):
    """G3: schema validation. Consumed as issued."""
    result = schema_gate.validate_master(master)
    findings = _findings_of(result)
    refs = [_as_reference("A", "schema_gate", f) for f in findings]
    errors = [r for r in refs if r["severity"] == "ERROR"]
    return {
        "gate": "G3",
        "layer": "A",
        "result": FAIL if errors else PASS,
        "finding_references": refs,
        "error_count": len(errors),
        "reinterpreted": False,
        "note": "schema verdicts are carried as issued; ownership stays with "
                "schema_gate",
    }


def run_rule_validators(master):
    """G4: B1..B11. Each verdict is carried, never converted."""
    all_refs, per_layer = [], {}

    for layer, module_name, fn in RULE_VALIDATORS:
        try:
            result = fn(master)
            findings = _findings_of(result)
            refs = [_as_reference(layer, module_name, f) for f in findings]
        except Exception as exc:               # a validator failure is
            refs = [{                          # reported, never swallowed
                "layer": layer, "owner_module": module_name,
                "rule": "VALIDATOR_EXECUTION_FAILURE",
                "location": None, "message": f"{type(exc).__name__}: {exc}",
                "severity": "ERROR", "verdict_owner": module_name,
            }]
        errors = [r for r in refs if r["severity"] == "ERROR"]
        per_layer[layer] = {"module": module_name, "findings": len(refs),
                            "errors": len(errors),
                            "result": FAIL if errors else PASS}
        all_refs.extend(refs)

    total_errors = [r for r in all_refs if r["severity"] == "ERROR"]
    return {
        "gate": "G4",
        "layers": per_layer,
        "result": FAIL if total_errors else PASS,
        "finding_references": all_refs,
        "error_count": len(total_errors),
        "reinterpreted": False,
        "softened": False,
        "note": ("B-series verdicts are carried as issued. Phase 01 does not "
                 "reinterpret severity and does not soften an ERROR."),
    }
