#!/usr/bin/env python3
"""Gate 00.5-B11 — Temporal Integrity / Chronological Coherence.

WHY THIS LAYER EXISTS
---------------------
The schema REQUIRES a date on almost every record it stores: `recorded_on`
on every fact, `raised_on` on every register entry, `approved_on` on every
decision, `created_on` on the project, `frozen_on` on the freeze,
`retrieved_on` on every external reference. A survey of all eleven earlier
engines showed that `raised_on`, `approved_on` and `recorded_on` are read by
NO engine at all. The only date readers are B8 (`generated_on` vs
`created_on`, for outputs) and B9 (`date` INSIDE the changelog, RT-006).

So the model stores time and then ignores it — which the ratified precedent
forbids: "a field must not be stored while the engine ignores it". Twelve
corrupt-chronology fixtures were run through A + B1..B10 together and every
one passed. That is the residual responsibility this layer owns.

WHAT IT IS NOT
--------------
B11 checks the INTERNAL CONSISTENCY of declared dates. It has no external
clock and no access to reality:

  * A completely fabricated history that is internally consistent PASSES.
  * B11 cannot tell whether a date is TRUE, only whether it contradicts
    another date in the same file.
  * Dates are day-resolution. Two events on the same day are NOT ordered,
    and B11 never infers an order for them.
  * B11 never repairs, reorders or writes anything. It reports.

Rules: TI-001 .. TI-008. No standards, no tolerances, no design judgement.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_gate import iter_facts                                 # noqa: E402


# --------------------------------------------------------------------------
# Vocabulary (mirrors the schema; nothing invented here)
# --------------------------------------------------------------------------
_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

META_FROZEN = "FROZEN"
META_DRAFT = "DRAFT"

# Register key -> the date field the schema requires on that entry.
REGISTER_RAISED = {
    "unknowns": "raised_on",
    "assumptions": "raised_on",
    "proposals": "raised_on",
    "change_requests": "raised_on",
    "objections": "raised_on",
}

# CR states that mean the request was never carried out, so a post-freeze
# change cannot be justified by them. (State semantics themselves are B10's.)
CR_STATES_NOT_APPLIED = {"DRAFT", "PENDING_APPROVAL", "REJECTED", "DEFERRED"}


class Finding:
    """A temporal inconsistency. Severity ERROR blocks; WARN informs."""

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"<{self.severity} {self.rule} @ {self.location}>"

    def __str__(self):
        return f"[{self.severity}] {self.rule} @ {self.location}: {self.message}"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _meta(data):
    return data.get("meta") or {}


def _regs(data):
    return data.get("registers") or {}


def _entries(data, key):
    return _regs(data).get(key) or []


def _date(node, field):
    """Return a comparable ISO date string, or None when absent/malformed.

    The schema already enforces the YYYY-MM-DD shape (that is A's rule), so
    B11 only needs the value to be a well-formed string before comparing.
    A missing date is NOT an error here: requiredness is A's rule too.
    """
    if not isinstance(node, dict):
        return None
    v = node.get(field)
    if not isinstance(v, str) or not _ISO_DATE.match(v):
        # DEF-B11-01 (found by TI-I08, fixed in R01): a length check alone
        # accepted "12/09/2026", which then sorted BEFORE every ISO date and
        # produced a phantom TI-004. A malformed date is A's rule to reject;
        # B11 must not reinterpret it as a point in time.
        return None
    return v


def _before(a, b):
    """True when date a is strictly earlier than date b.

    ISO YYYY-MM-DD sorts correctly as text. Equality is deliberately NOT a
    violation: day resolution cannot order two events on the same day, and
    B11 refuses to invent an order it cannot observe.
    """
    return a is not None and b is not None and a < b


def _all_declared_dates(data):
    """Every date the FILE itself declares, used to derive 'the future'.

    B11 has no external clock. The latest date declared anywhere in the file
    is the only defensible notion of 'now' available to it. Anything beyond
    that horizon is a claim the file itself cannot support.
    """
    dates = []
    meta = _meta(data)
    for f in ("created_on", "frozen_on"):
        d = _date(meta, f)
        if d:
            dates.append(d)
    for key in REGISTER_RAISED:
        for e in _entries(data, key):
            for f in ("raised_on", "resolved_on", "approved_on"):
                d = _date(e, f)
                if d:
                    dates.append(d)
    for e in _entries(data, "decisions"):
        d = _date(e, "approved_on")
        if d:
            dates.append(d)
    for e in _entries(data, "changelog"):
        d = _date(e, "date")
        if d:
            dates.append(d)
    for _, fact in iter_facts(data):
        for f in ("recorded_on", "approved_on"):
            d = _date(fact, f)
            if d:
                dates.append(d)
        ext = fact.get("external")
        if isinstance(ext, dict):
            d = _date(ext, "retrieved_on")
            if d:
                dates.append(d)
    # outputs[].generated_on is deliberately NOT read here. B8 already owns
    # the relationship between an output's date and meta.created_on (OR rule),
    # and DEF-B11-02 (found by TI-I07) showed that consuming it here made B11
    # a second judge of output dates. B11 stays out of the outputs array.
    return dates


# --------------------------------------------------------------------------
# TI-001 / TI-002 — causal order across registers
# --------------------------------------------------------------------------
def check_causal_order(data):
    """A record cannot be settled before the record that caused it exists."""
    findings = []

    proposals = {p.get("id"): p for p in _entries(data, "proposals")
                 if isinstance(p, dict) and p.get("id")}
    decisions = {d.get("decision_id"): d for d in _entries(data, "decisions")
                 if isinstance(d, dict) and d.get("decision_id")}

    # TI-001: decision approved before its proposal was raised.
    for i, dec in enumerate(_entries(data, "decisions")):
        if not isinstance(dec, dict):
            continue
        pid = dec.get("linked_proposal")
        prop = proposals.get(pid)
        if prop is None:
            continue            # a dangling link is B1's rule XR-010
        approved = _date(dec, "approved_on")
        raised = _date(prop, "raised_on")
        if _before(approved, raised):
            findings.append(Finding(
                "TI-001", f"registers/decisions/{i} ({dec.get('decision_id')})",
                f"approved on {approved}, but its proposal '{pid}' was not "
                f"raised until {raised}. A decision cannot predate the "
                f"proposal it decides. Either the dates are wrong or the "
                f"link is. B11 reports the contradiction and picks neither."))

    # TI-002: objection raised before the decision it objects to was approved.
    for i, o in enumerate(_entries(data, "objections")):
        if not isinstance(o, dict):
            continue
        did = o.get("decision_under_objection")
        dec = decisions.get(did)
        if dec is None:
            continue            # dangling reference is B1's rule
        raised = _date(o, "raised_on")
        approved = _date(dec, "approved_on")
        if _before(raised, approved):
            findings.append(Finding(
                "TI-002", f"registers/objections/{i} ({o.get('id')})",
                f"raised on {raised}, but decision '{did}' was not approved "
                f"until {approved}. An objection to a decision that did not "
                f"exist yet cannot be what the record claims it is."))

    return findings


# --------------------------------------------------------------------------
# TI-003 — a question cannot be answered before it is asked
# --------------------------------------------------------------------------
def check_resolution_order(data):
    findings = []

    for i, u in enumerate(_entries(data, "unknowns")):
        if not isinstance(u, dict):
            continue
        raised = _date(u, "raised_on")
        resolved = _date(u, "resolved_on")
        if _before(resolved, raised):
            findings.append(Finding(
                "TI-003", f"registers/unknowns/{i} ({u.get('id')})",
                f"resolved on {resolved} but only raised on {raised}. The "
                f"answer predates the question, so the resolution record "
                f"cannot be trusted to describe this unknown."))

    for i, c in enumerate(_entries(data, "change_requests")):
        if not isinstance(c, dict):
            continue
        raised = _date(c, "raised_on")
        approved = _date(c, "approved_on")
        if _before(approved, raised):
            findings.append(Finding(
                "TI-003", f"registers/change_requests/{i} ({c.get('id')})",
                f"approved on {approved} but only raised on {raised}. A "
                f"change request cannot be approved before it is requested."))

    return findings


# --------------------------------------------------------------------------
# TI-004 / TI-005 / TI-006 — the project envelope and the horizon
# --------------------------------------------------------------------------
def check_envelope(data):
    """Nothing predates the project, and nothing outruns the file's horizon."""
    findings = []
    meta = _meta(data)
    created = _date(meta, "created_on")

    # ---- TI-004: content dated before the project existed ----------------
    if created:
        for key, field in REGISTER_RAISED.items():
            for i, e in enumerate(_entries(data, key)):
                d = _date(e, field)
                if _before(d, created):
                    findings.append(Finding(
                        "TI-004", f"registers/{key}/{i} ({e.get('id')})",
                        f"{field} is {d}, before the project was created on "
                        f"{created}. A record cannot predate the file that "
                        f"contains it."))

        for i, dec in enumerate(_entries(data, "decisions")):
            d = _date(dec, "approved_on")
            if _before(d, created):
                findings.append(Finding(
                    "TI-004",
                    f"registers/decisions/{i} ({dec.get('decision_id')})",
                    f"approved_on is {d}, before the project was created on "
                    f"{created}."))

        for path, fact in iter_facts(data):
            d = _date(fact, "recorded_on")
            if _before(d, created):
                findings.append(Finding(
                    "TI-004", path,
                    f"recorded_on is {d}, before the project was created on "
                    f"{created}. The value claims to predate the project."))

    # ---- TI-005: a fact approved before it was recorded ------------------
    for path, fact in iter_facts(data):
        recorded = _date(fact, "recorded_on")
        approved = _date(fact, "approved_on")
        if _before(approved, recorded):
            findings.append(Finding(
                "TI-005", path,
                f"approved_on {approved} precedes recorded_on {recorded}. "
                f"The value was approved before it was written down, so the "
                f"approval cannot have been given for this value."))

    # ---- TI-006: beyond the horizon the file itself declares -------------
    # B11 owns no clock. The newest date in the file is the only 'now' it can
    # justify, so it flags what lies strictly beyond that, and only when the
    # file offers a meaningful horizon (more than a single date).
    dates = _all_declared_dates(data)
    if len(set(dates)) > 1:
        horizon = max(dates)
        anchors = {created, _date(meta, "frozen_on")}
        if horizon not in anchors:
            for path, fact in iter_facts(data):
                for field in ("recorded_on", "approved_on"):
                    d = _date(fact, field)
                    if d == horizon and d != created:
                        others = [x for x in dates if x != horizon]
                        if others and horizon > max(others):
                            findings.append(Finding(
                                "TI-006", path,
                                f"{field} is {d}, later than every other "
                                f"date declared in this file (next is "
                                f"{max(others)}). B11 has no external clock; "
                                f"it reports that this date cannot be "
                                f"corroborated by anything else in the "
                                f"model.", severity="WARN"))

        for path, fact in iter_facts(data):
            ext = fact.get("external")
            if not isinstance(ext, dict):
                continue
            d = _date(ext, "retrieved_on")
            if d and created and d > horizon_of_others(dates, d):
                findings.append(Finding(
                    "TI-006", f"{path}/external",
                    f"retrieved_on is {d}, later than every other date in "
                    f"the file. An external reference cannot have been "
                    f"retrieved after the project's own latest record.",
                    severity="WARN"))

    return findings


def horizon_of_others(dates, this):
    """The newest date in the file other than `this` (empty -> ''), helper
    for TI-006 so a single outlier is measured against the rest."""
    others = [d for d in dates if d != this]
    return max(others) if others else ""


# --------------------------------------------------------------------------
# TI-007 / TI-008 — freeze semantics in time
# --------------------------------------------------------------------------
def check_freeze_time(data):
    """Freezing stops the clock on approved content."""
    findings = []
    meta = _meta(data)
    status = meta.get("status")
    frozen_on = _date(meta, "frozen_on")

    # ---- TI-008: the freeze flag and the freeze date must agree ----------
    if status == META_FROZEN and meta.get("frozen_on") is None:
        findings.append(Finding(
            "TI-008", "meta/frozen_on",
            "status is FROZEN but no frozen_on date is recorded, so nothing "
            "in the file says WHEN the master was frozen and no later record "
            "can be judged against the freeze."))

    if status == META_DRAFT and meta.get("frozen_on") is not None:
        findings.append(Finding(
            "TI-008", "meta/frozen_on",
            f"frozen_on is {meta.get('frozen_on')} while status is DRAFT. "
            f"The file carries a freeze date without being frozen, so it is "
            f"unclear whether the content is still open to change."))

    created = _date(meta, "created_on")
    if _before(frozen_on, created):
        findings.append(Finding(
            "TI-008", "meta/frozen_on",
            f"frozen_on {frozen_on} precedes created_on {created}. The "
            f"project was frozen before it existed."))

    # ---- TI-007: content dated after the freeze without a CR -------------
    if status != META_FROZEN or not frozen_on:
        return findings

    # Which CRs could legitimately justify a post-freeze change? Only ones
    # the register itself says were carried out. Whether that CR state is
    # internally coherent is B10's rule, not B11's.
    live_cr = [c for c in _entries(data, "change_requests")
               if isinstance(c, dict)
               and c.get("state") not in CR_STATES_NOT_APPLIED]

    for path, fact in iter_facts(data):
        d = _date(fact, "recorded_on")
        if not _before(frozen_on, d):
            continue
        if live_cr:
            continue           # a change route exists; linking it is B1/B10
        findings.append(Finding(
            "TI-007", path,
            f"recorded_on is {d}, after the master was frozen on "
            f"{frozen_on}, and no change request in the register accounts "
            f"for a change at that time. Content moved after the freeze "
            f"without the route the freeze exists to enforce."))

    return findings


# --------------------------------------------------------------------------
# Report (descriptive only — no verdict, no repair)
# --------------------------------------------------------------------------
def temporal_report(data):
    """A plain description of the time declared in the file."""
    dates = _all_declared_dates(data)
    meta = _meta(data)
    return {
        "created_on": _date(meta, "created_on"),
        "frozen_on": _date(meta, "frozen_on"),
        "status": meta.get("status"),
        "earliest_declared": min(dates) if dates else None,
        "latest_declared": max(dates) if dates else None,
        "distinct_dates": len(set(dates)),
    }


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def validate_temporal(data):
    """Return (ok, findings). ok is False only when an ERROR was found."""
    findings = []
    findings += check_causal_order(data)
    findings += check_resolution_order(data)
    findings += check_envelope(data)
    findings += check_freeze_time(data)
    ok = not any(f.severity == "ERROR" for f in findings)
    return ok, findings


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("usage: validate_temporal.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_temporal(payload)
    for f in fs:
        print(f"{f.severity:5} {f.rule} [{f.location}] {f.message}")
    print(f"\nB11 temporal integrity: {'PASS' if ok else 'FAIL'} "
          f"({len(fs)} finding(s))")
    sys.exit(0 if ok else 1)
