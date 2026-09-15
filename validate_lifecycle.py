#!/usr/bin/env python3
"""Phase 00.5-B10 — Register Lifecycle / Decision-State Integrity.

HOW THIS RESPONSIBILITY WAS ESTABLISHED (not inferred from the name):
  Phase 00 never mentions a "B10". The scope was found by sweeping the rule
  codes every engine actually owns (INV/XR/WT/FC/MV/DS/FM/UB/OR/RT) and then
  inspecting the state machines the schema defines for the registers.

  Result: the state values REJECTED, SUPERSEDED, DEFERRED, APPLIED and
  USER_OVERRIDE appear in NO engine at all. Layer B1 checks that links EXIST
  (XR-010/011/013); layer A checks the SHAPE of an entry. Nobody checks that
  the STATES are logically coherent with one another. Eight such cases pass
  A, B1, B6, B7, B8 and B9 simultaneously.

WHAT B10 OWNS:
  The lifecycle coherence of decisions and their registers: a decision may not
  rest on a rejected proposal, an open objection may not be silently ignored,
  a change request may not be applied in a state that forbids it, and a fact
  may not claim an approval its register denies.

WHAT B10 DOES NOT OWN (consumed, never re-implemented):
  - entry shape / id patterns / required fields        -> A
  - existence of linked ids (XR-010/011/013)           -> B1
  - topology B2 · furniture B3 · movement B4 · doors B5
  - arithmetic B6 · uncertainty transitions B7
  - output representation B8 · changelog traceability  -> B9
  - approval impersonation / identity / authenticity   -> 00.5-E

DECLARED CAPABILITY LIMIT:
  B10 cannot tell whether an approval is GENUINE — that is GAP-02 and belongs
  to 00.5-E. It only checks that the recorded states do not contradict each
  other. A perfectly consistent but entirely fabricated history passes.

HARD RULES:
  * detect / classify / report only — no auto-fix, no state repair
  * a missing optional field is UNSPECIFIED, never assumed
  * no design standard, no tolerance, no geometry
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_gate import iter_facts                                 # noqa: E402

# States that exist in the schema. B10 invents none of them.
PROP_OPEN = "OPEN"
PROP_APPROVED = "APPROVED"
PROP_REJECTED = "REJECTED"
PROP_SUPERSEDED = "SUPERSEDED"

CR_DRAFT = "DRAFT"
CR_PENDING = "PENDING_APPROVAL"
CR_APPROVED = "APPROVED"
CR_REJECTED = "REJECTED"
CR_DEFERRED = "DEFERRED"
CR_APPLIED = "APPLIED"

OBJ_OPEN = "OPEN"
OBJ_WITHDRAWN = "WITHDRAWN"
OBJ_USER_OVERRIDE = "USER_OVERRIDE"
OBJ_ACCEPTED = "ACCEPTED"

APPROVAL_PENDING = "PENDING_APPROVAL"
APPROVAL_APPROVED = "APPROVED"
APPROVAL_REJECTED = "REJECTED"

# A proposal in one of these states is settled: it can no longer be the live
# basis of a decision.
PROPOSAL_CLOSED_AGAINST = {PROP_REJECTED, PROP_SUPERSEDED}

# A change request in one of these states has NOT been authorised to apply.
CR_NOT_APPLICABLE = {CR_DRAFT, CR_PENDING, CR_REJECTED, CR_DEFERRED}


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"<{self.severity} {self.rule} @ {self.location}>"


def _regs(data):
    return data.get("registers") or {}


def _list(data, key):
    return [e for e in (_regs(data).get(key) or []) if isinstance(e, dict)]


# --------------------------------------------------------------------------
# RL-001 / RL-002 — proposal <-> decision state coherence
# --------------------------------------------------------------------------
def check_proposal_decision(data):
    """A decision may only rest on a proposal that is actually live.

    Existence of the link is XR-010/011 (B1). B10 judges the STATE.
    """
    findings = []
    proposals = {p.get("id"): p for p in _list(data, "proposals")}
    decisions = _list(data, "decisions")

    for i, dec in enumerate(decisions):
        did = dec.get("decision_id")
        lp = dec.get("linked_proposal")
        prop = proposals.get(lp)
        if prop is None:
            continue                      # missing link is B1's rule
        state = prop.get("state")
        loc = f"registers/decisions/{i} ({did})"

        if state in PROPOSAL_CLOSED_AGAINST:
            findings.append(Finding(
                "RL-001", loc,
                f"decision {did} rests on proposal '{lp}' whose state is "
                f"{state}. A proposal that was rejected or superseded cannot "
                f"be the basis of a standing decision: Proposal is not "
                f"Decision, and a closed proposal is not a live one."))
        elif state == PROP_OPEN:
            findings.append(Finding(
                "RL-002", loc,
                f"decision {did} already exists while proposal '{lp}' is "
                f"still OPEN. The record shows a decision taken before its "
                f"proposal was settled."))

    # Mirror direction: an APPROVED proposal with no decision recorded.
    decided = {d.get("linked_proposal") for d in decisions}
    for i, p in enumerate(_list(data, "proposals")):
        if p.get("state") == PROP_APPROVED and p.get("id") not in decided:
            findings.append(Finding(
                "RL-002", f"registers/proposals/{i} ({p.get('id')})",
                f"proposal '{p.get('id')}' is APPROVED but no decision "
                f"records it. An approval that produced no decision leaves "
                f"the outcome untraceable.", severity="WARN"))
    return findings


# --------------------------------------------------------------------------
# RL-003 / RL-004 — objections must be answered, overrides must be recorded
# --------------------------------------------------------------------------
def check_objections(data):
    findings = []
    decisions = {d.get("decision_id"): d for d in _list(data, "decisions")}
    overridden = {d.get("user_override_of")
                  for d in _list(data, "decisions") if d.get("user_override_of")}

    for i, obj in enumerate(_list(data, "objections")):
        oid = obj.get("id")
        state = obj.get("state")
        target = obj.get("decision_under_objection")
        loc = f"registers/objections/{i} ({oid})"

        # RL-003: an OPEN objection against a decision that still stands.
        if state == OBJ_OPEN and target in decisions:
            findings.append(Finding(
                "RL-003", loc,
                f"objection {oid} against decision '{target}' is still OPEN "
                f"while that decision stands unchanged. An unanswered "
                f"objection must be resolved, withdrawn, accepted or "
                f"explicitly overridden — never left hanging."))

        # RL-004: a USER_OVERRIDE with no decision recording the override.
        if state == OBJ_USER_OVERRIDE and oid not in overridden:
            findings.append(Finding(
                "RL-004", loc,
                f"objection {oid} is marked USER_OVERRIDE but no decision "
                f"records user_override_of='{oid}'. An override is a human "
                f"act that must leave a trace on the deciding side too."))
    return findings


# --------------------------------------------------------------------------
# RL-005 / RL-006 — change-request lifecycle
# --------------------------------------------------------------------------
def check_change_requests(data):
    findings = []
    crs = {c.get("id"): c for c in _list(data, "change_requests")}

    # Which CRs the changelog claims to have applied. Whether the changelog
    # itself is coherent is B9's rule; here it is only evidence of an event.
    applied_in_log = {}
    for i, e in enumerate((_regs(data).get("changelog") or [])):
        if isinstance(e, dict) and e.get("type") == "CR_APPLIED" and e.get("cr_id"):
            applied_in_log.setdefault(e["cr_id"], i)

    for cid, idx in applied_in_log.items():
        cr = crs.get(cid)
        if cr is None:
            continue                      # dangling cr_id is B1's rule XR-012
        state = cr.get("state")
        if state in CR_NOT_APPLICABLE:
            findings.append(Finding(
                "RL-005", f"registers/change_requests ({cid})",
                f"the changelog records CR '{cid}' as applied, but the change "
                f"request itself is in state {state}. A change that was never "
                f"authorised cannot already be part of the design."))

    # RL-006: a CR that claims to be applied with nothing recording it.
    for i, c in enumerate(_list(data, "change_requests")):
        cid = c.get("id")
        if c.get("state") == CR_APPLIED and cid not in applied_in_log:
            findings.append(Finding(
                "RL-006", f"registers/change_requests/{i} ({cid})",
                f"CR '{cid}' is marked APPLIED but no changelog entry records "
                f"applying it. The design claims a change with no event "
                f"behind it."))
        if c.get("state") == CR_REJECTED and c.get("applied_in_revision"):
            findings.append(Finding(
                "RL-006", f"registers/change_requests/{i} ({cid})",
                f"CR '{cid}' is REJECTED yet carries "
                f"applied_in_revision='{c.get('applied_in_revision')}'. A "
                f"rejected change cannot have been applied."))
    return findings


# --------------------------------------------------------------------------
# RL-007 / RL-008 — a fact may not out-claim its own register entry
# --------------------------------------------------------------------------
def check_fact_register_drift(data):
    findings = []
    assumptions = {a.get("id"): a for a in _list(data, "assumptions")}
    proposals = {p.get("id"): p for p in _list(data, "proposals")}

    for path, fact in iter_facts(data):
        aid = fact.get("assumption_id")
        if aid and aid in assumptions:
            reg_state = assumptions[aid].get("approval_state")
            fact_state = fact.get("approval_state")
            # RL-007: the fact claims an approval the register denies.
            if fact_state and reg_state and fact_state != reg_state:
                findings.append(Finding(
                    "RL-007", path,
                    f"fact records approval_state={fact_state} for assumption "
                    f"'{aid}', but the register records {reg_state}. The data "
                    f"and its own governance record disagree; B10 does not "
                    f"choose a winner, it reports the contradiction."))
            # RL-008: a rejected assumption still feeding live data.
            if reg_state == APPROVAL_REJECTED and fact.get("status") in ("C", "D"):
                findings.append(Finding(
                    "RL-008", path,
                    f"assumption '{aid}' was REJECTED, yet this value is "
                    f"[{fact.get('status')}] and still live. A rejected "
                    f"assumption must not survive as established data."))

        pid = fact.get("proposal_id")
        if pid and pid in proposals:
            pstate = proposals[pid].get("state")
            if pstate in PROPOSAL_CLOSED_AGAINST and fact.get("status") in ("C", "D"):
                findings.append(Finding(
                    "RL-008", path,
                    f"proposal '{pid}' is {pstate}, yet this value is "
                    f"[{fact.get('status')}] and still live. A closed "
                    f"proposal must not persist as confirmed data."))
    return findings


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def lifecycle_report(data):
    """A summary of register states. A report, never applied to the data."""
    def states(key, field):
        return sorted({e.get(field) for e in _list(data, key) if e.get(field)})
    return {
        "proposals": states("proposals", "state"),
        "change_requests": states("change_requests", "state"),
        "objections": states("objections", "state"),
        "assumptions": states("assumptions", "approval_state"),
        "decisions": len(_list(data, "decisions")),
    }


def validate_lifecycle(data):
    """Return (ok, findings). Detect / classify / report only."""
    findings = []
    findings += check_proposal_decision(data)
    findings += check_objections(data)
    findings += check_change_requests(data)
    findings += check_fact_register_drift(data)
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("usage: validate_lifecycle.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_lifecycle(payload)
    for f in fs:
        print(f"{f.severity:5} {f.rule} [{f.location}] {f.message}")
    print()
    print("lifecycle:", lifecycle_report(payload))
    sys.exit(0 if ok else 1)
