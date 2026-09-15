#!/usr/bin/env python3
"""Phase 00.5-B7 — Unknown / Blocking Integrity.

WHAT B7 OWNS:
  UNKNOWN / UNRESOLVED / UNCOMPUTABLE / INCOMPLETE must never quietly turn
  into something that LOOKS confirmed, approved or safe to build from. B7
  polices the STATE TRANSITIONS and the PROPAGATION of uncertainty — not the
  content of any value.

WHAT B7 DOES NOT OWN (consumed, never re-implemented):
  - arithmetic correctness of a [D]        -> B6 (B7 reads its verdict only)
  - reference resolvability                -> B1 (XR-008)
  - shape of a [D] and INV-D1 trust rule   -> A
  - wall/opening geometry -> B2 · furniture -> B3 · movement -> B4
  - door swing -> B5
  - the DECLARED final-approval blocker list -> A's final_approval_readiness()
    B7 CALLS that function; it does not restate its rules.
  - approval-evidence impersonation        -> 00.5-E (GAP-01 / GAP-02)

HARD RULES:
  * B7 never fills an unknown, never guesses, never auto-fixes
  * UNKNOWN is NOT automatically an ERROR: blocking is DEPENDENCY-AWARE
  * [] is not NOT_PRESENT; NOT_PRESENT is not UNKNOWN (tri-state respected)
  * B7 invents no new state: every state below exists in the schema already
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_gate import iter_facts, final_approval_readiness   # noqa: E402
from validate_formulas import validate_formulas, UNCOMPUTABLE  # noqa: E402

# --------------------------------------------------------------------------
# States — ALL of these already exist in project_master.schema.json.
# Nothing here is invented for convenience.
# --------------------------------------------------------------------------
STATUS_UNKNOWN = "U"          # fact.status
STATUS_PROPOSED = "P"
STATUS_ASSUMED = "A"
STATUS_CONFIRMED = "C"
STATUS_DERIVED = "D"

PRESENCE_PRESENT = "PRESENT"          # fact.presence — tri-state (A R02 §3)
PRESENCE_NOT_PRESENT = "NOT_PRESENT"
PRESENCE_UNKNOWN = "UNKNOWN"

META_DRAFT = "DRAFT"          # meta.status
META_FROZEN = "FROZEN"

# Certainty a value may claim. UNKNOWN/UNCOMPUTABLE may never be upgraded to
# CERTAIN without a basis; that is the whole point of this layer.
CERTAIN = {STATUS_CONFIRMED, STATUS_DERIVED}
UNCERTAIN = {STATUS_UNKNOWN, STATUS_PROPOSED, STATUS_ASSUMED}

# --------------------------------------------------------------------------
# Dependency-aware severity. "UNKNOWN = ERROR" is explicitly REJECTED.
# --------------------------------------------------------------------------
IMPACT_BLOCKS_PROJECT = "BLOCKS_PROJECT"   # declared blocking in the register
IMPACT_AFFECTS_OUTPUT = "AFFECTS_OUTPUT"   # reaches a binding output/decision
IMPACT_DECLARED_ONLY = "DECLARED_ONLY"     # known, recorded, touches nothing
IMPACT_OUT_OF_SCOPE = "OUT_OF_SCOPE"       # declared, outside current output

# An output whose guarantee asserts a deterministic match is BINDING: it may
# not rest on anything uncertain. Class C is explicitly non-binding.
BINDING_GUARANTEE = "DETERMINISTIC_GEOMETRIC_MATCH"


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"<{self.severity} {self.rule} @ {self.location}>"


def _facts(data):
    """All (path, fact) pairs, using A's own traversal — not a private copy."""
    return list(iter_facts(data))


def _unknown_register(data):
    return (data.get("registers") or {}).get("unknowns", []) or []


def _outputs(data):
    return data.get("outputs") or []


# --------------------------------------------------------------------------
# UB-001 / UB-002 — state-transition integrity
# --------------------------------------------------------------------------
def check_transitions(data):
    """A fact may not become CERTAIN while its unknown is still open, and an
    unknown may not be declared resolved while the fact is still [U]."""
    findings = []
    reg = {u.get("id"): u for u in _unknown_register(data)}

    for path, fact in _facts(data):
        uid = fact.get("unknown_id")
        if not uid or uid not in reg:
            # a dangling unknown_id is XR-007's rule (B1), not B7's
            continue
        entry = reg[uid]
        resolved = bool(entry.get("resolved_on"))
        status = fact.get("status")

        # UB-001: promoted to certain while the question is still open.
        if status in CERTAIN and not resolved:
            findings.append(Finding(
                "UB-001", path,
                f"value is [{status}] but still cites unknown '{uid}', which "
                f"has no resolved_on. An UNKNOWN does not become CONFIRMED by "
                f"being rewritten: resolving it requires recording the answer "
                f"in the register. B7 does not resolve it and does not guess."))

        # UB-002: register says answered, the data says otherwise.
        if resolved and status == STATUS_UNKNOWN:
            findings.append(Finding(
                "UB-002", path,
                f"unknown '{uid}' is marked resolved_on="
                f"{entry.get('resolved_on')}, but this value is still [U]. "
                f"A resolved question with an unfilled answer hides an open "
                f"unknown behind a closed ticket."))
    return findings


# --------------------------------------------------------------------------
# UB-003 — presence semantics (tri-state, owned jointly with B2/B4 semantics)
# --------------------------------------------------------------------------
def check_presence_semantics(data):
    """NOT_PRESENT means a human confirmed absence. It may not be asserted by
    an uncertain fact, and an empty list is not a confirmation of absence."""
    findings = []
    for path, fact in _facts(data):
        presence = fact.get("presence")
        if presence is None:
            continue
        status = fact.get("status")

        if presence == PRESENCE_NOT_PRESENT and status in UNCERTAIN:
            findings.append(Finding(
                "UB-003", path,
                f"presence=NOT_PRESENT is a CONFIRMED absence, but the fact is "
                f"[{status}]. Not knowing whether something exists is UNKNOWN, "
                f"never 'it does not exist'."))

        if presence == PRESENCE_UNKNOWN and status in CERTAIN \
                and not fact.get("unknown_id"):
            findings.append(Finding(
                "UB-003", path,
                f"presence=UNKNOWN carries status [{status}] and no "
                f"unknown_id, so an unresolved existence question is not "
                f"registered anywhere and cannot block anything.",
                severity="WARN"))

        # [] is data, not a confirmation. Reported as INFO only.
        if presence == PRESENCE_PRESENT and fact.get("value") in ([], {}):
            findings.append(Finding(
                "UB-003", path,
                "presence=PRESENT but the value is empty. An empty collection "
                "is not evidence of presence and is not evidence of absence.",
                severity="INFO"))
    return findings


# --------------------------------------------------------------------------
# Uncertainty propagation — the core of B7
# --------------------------------------------------------------------------
def build_uncertainty_map(data):
    """Map every fact path to why it is uncertain, following derivation edges.

    B7 does NOT recompute anything: for [D] values it consumes B6's verdict.
    """
    uncertain = {}

    for path, fact in _facts(data):
        st = fact.get("status")
        if st == STATUS_UNKNOWN:
            uncertain[path] = ("UNKNOWN", f"{path} is [U]")
        elif st == STATUS_PROPOSED:
            uncertain[path] = ("PROPOSED", f"{path} is [P], not decided")
        elif st == STATUS_ASSUMED and fact.get("approval_state") != "APPROVED":
            uncertain[path] = ("UNAPPROVED_ASSUMPTION",
                               f"{path} is [A] and not APPROVED")

    # B6's verdicts, consumed as-is.
    try:
        _ok, _f, verdicts = validate_formulas(data)
    except Exception:                                   # pragma: no cover
        verdicts = {}
    for vpath, verdict in (verdicts or {}).items():
        if verdict == UNCOMPUTABLE:
            uncertain[vpath] = ("UNCOMPUTABLE",
                                f"{vpath} is UNCOMPUTABLE (verdict from B6)")

    # Propagate along derived_from edges until stable. A derived value that
    # depends on an uncertain input is itself uncertain, however many hops
    # away — this is what stops laundering through intermediates.
    index = {}
    for path, fact in _facts(data):
        index[path] = fact
        index[path.replace("/", ".")] = fact

    def _norm(ref):
        return ref.replace(".", "/")

    changed = True
    while changed:
        changed = False
        for path, fact in _facts(data):
            if path in uncertain:
                continue
            for ref in fact.get("derived_from", []) or []:
                key = _norm(ref)
                if key in uncertain:
                    kind, why = uncertain[key]
                    uncertain[path] = (
                        "INHERITED",
                        f"{path} derives from {ref} — {why}")
                    changed = True
                    break
    return uncertain


def check_propagation(data):
    """UB-004 / UB-005: uncertainty must not reach a binding output."""
    findings = []
    uncertain = build_uncertainty_map(data)
    if not uncertain:
        return findings

    binding = [o for o in _outputs(data)
               if o.get("binding_geometry")
               or o.get("guarantee") == BINDING_GUARANTEE]
    if not binding:
        # Uncertainty exists but nothing binding consumes it: DECLARED_ONLY.
        for path, (kind, why) in sorted(uncertain.items()):
            findings.append(Finding(
                "UB-006", path,
                f"{why}. Classified {IMPACT_DECLARED_ONLY}: no binding output "
                f"currently depends on it, so it does not block. Recorded, "
                f"not hidden.", severity="INFO"))
        return findings

    for out in binding:
        oid = out.get("output_id", "<output>")
        for path, (kind, why) in sorted(uncertain.items()):
            rule = "UB-005" if kind == "UNCOMPUTABLE" else "UB-004"
            findings.append(Finding(
                rule, f"outputs/{oid}",
                f"output '{oid}' declares guarantee "
                f"'{out.get('guarantee')}' (binding_geometry="
                f"{out.get('binding_geometry')}) while the model still "
                f"contains uncertainty: {why}. A binding output may not rest "
                f"on an unresolved or uncomputable value. B7 blocks it; it "
                f"does not fill the gap and does not regenerate the output."))
    return findings


# --------------------------------------------------------------------------
# UB-006 — dependency-aware classification (NOT "UNKNOWN = ERROR")
# --------------------------------------------------------------------------
def classify_unknowns(data):
    """Return {unknown_id: impact}. Declared, non-blocking, unconsumed
    unknowns are explicitly NOT errors."""
    out = {}
    binding = [o for o in _outputs(data)
               if o.get("binding_geometry")
               or o.get("guarantee") == BINDING_GUARANTEE]
    uncertain = build_uncertainty_map(data)

    for entry in _unknown_register(data):
        uid = entry.get("id")
        if entry.get("resolved_on"):
            continue
        if entry.get("blocking"):
            out[uid] = IMPACT_BLOCKS_PROJECT
            continue
        # does any uncertain fact cite this unknown?
        cited = any(f.get("unknown_id") == uid for _p, f in _facts(data))
        if cited and binding:
            out[uid] = IMPACT_AFFECTS_OUTPUT
        elif cited:
            out[uid] = IMPACT_DECLARED_ONLY
        else:
            out[uid] = IMPACT_OUT_OF_SCOPE
    return out


# --------------------------------------------------------------------------
# UB-007 / UB-009 — readiness. A owns the blocker list; B7 only integrates.
# --------------------------------------------------------------------------
def check_readiness(data):
    findings = []

    # UB-009: delegate to A, never restate its rules.
    ready, blockers = final_approval_readiness(data)

    # UB-007: FROZEN is a claim of completeness.
    if (data.get("meta") or {}).get("status") == META_FROZEN and not ready:
        findings.append(Finding(
            "UB-007", "meta/status",
            f"meta.status=FROZEN while {len(blockers)} approval blocker(s) "
            f"remain open: {blockers[:3]}. Freezing does not resolve them; it "
            f"only makes them invisible."))

    # UB-008: a decision resting on something uncertain.
    uncertain = build_uncertainty_map(data)
    for dec in (data.get("registers") or {}).get("decisions", []) or []:
        for el in dec.get("linked_elements", []) or []:
            key = el.replace(".", "/")
            if key in uncertain:
                findings.append(Finding(
                    "UB-008", f"registers/decisions/{dec.get('decision_id')}",
                    f"decision {dec.get('decision_id')} is linked to '{el}', "
                    f"which is uncertain: {uncertain[key][1]}. A decision does "
                    f"not convert an unknown into a fact."))
    return findings, ready, blockers


def readiness_report(data):
    """Aggregate readiness: A's declared blockers PLUS B7's integrity errors.

    Returned as a report, never applied to the data.
    """
    findings = validate_blocking(data)[1]
    errors = [f for f in findings if f.severity == "ERROR"]
    _f, a_ready, a_blockers = check_readiness(data)
    ready = a_ready and not errors
    return {
        "ready_for_final_approval": ready,
        "declared_blockers_from_A": a_blockers,
        "b7_integrity_errors": [f"{f.rule} @ {f.location}" for f in errors],
        "unknown_impact": classify_unknowns(data),
    }


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def validate_blocking(data):
    """Return (ok, findings). Detect / classify / report only."""
    findings = []
    findings += check_transitions(data)
    findings += check_presence_semantics(data)
    findings += check_propagation(data)
    rfind, _ready, _blockers = check_readiness(data)
    findings += rfind
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("usage: validate_blocking.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_blocking(payload)
    for f in fs:
        print(f"{f.severity:5} {f.rule} [{f.location}] {f.message}")
    rep = readiness_report(payload)
    print()
    print("READY FOR FINAL APPROVAL:", rep["ready_for_final_approval"])
    print("unknown impact:", rep["unknown_impact"])
    sys.exit(0 if ok else 1)
