#!/usr/bin/env python3
"""Phase 00.5-B9 — Revision / Changelog Traceability Integrity.

HOW THIS RESPONSIBILITY WAS ESTABLISHED (not inferred from the name):
  Phase 00 never mentions a "B9". The B-series is a decomposition we chose,
  and the Specification's own roadmap after 00.5 is C/D/E/F. So the scope was
  derived by PROBING for a responsibility no engine owns, and one was found:

  The schema stores traceability fields — master_hash_before/after,
  geometry_version_before/after, tests_rerun, regressions_found,
  output_diff_explained — but layer A enforces them for TECHNICAL_FIX only
  (rule TF1), plus cr_id for CR_APPLIED (rule CR2). INITIAL, FREEZE and
  REGENERATION carry NO proof obligation, and nothing reconciles the
  changelog against meta. Five such cases pass A, B1, B6, B7 and B8 together.

WHAT B9 OWNS:
  The internal coherence of the revision history: that meta and the changelog
  tell the SAME story, that a freeze is recorded, that a regeneration explains
  itself, and that the record runs forward in time.

WHAT B9 DOES NOT OWN (consumed, never re-implemented):
  - TF1 / CR2 obligations and meta's own shape        -> A
  - existence of cr_id / referenced entities          -> B1 (XR-012 etc.)
  - topology B2 · furniture B3 · movement B4 · doors B5
  - arithmetic B6 · uncertainty transitions B7
  - output provenance and representation              -> B8
  - approval impersonation / identity governance      -> 00.5-E

DECLARED CAPABILITY LIMIT:
  B9 does NOT recompute a hash from content. It cannot prove master_hash is
  truthful — only that the story is internally consistent. Recorded as a
  Capability Gap, never presented as verification of the hash itself.

HARD RULES:
  * detect / classify / report only — no auto-fix, no invented history
  * no design standard, no tolerance, no clearance
  * a missing optional field is UNSPECIFIED, never assumed false
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Entry types that exist in the schema. B9 invents none of them.
TYPE_INITIAL = "INITIAL"
TYPE_CR_APPLIED = "CR_APPLIED"
TYPE_TECHNICAL_FIX = "TECHNICAL_FIX"
TYPE_FREEZE = "FREEZE"
TYPE_REGENERATION = "REGENERATION"

META_FROZEN = "FROZEN"


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"<{self.severity} {self.rule} @ {self.location}>"


def _changelog(data):
    entries = (data.get("registers") or {}).get("changelog") or []
    return [e for e in entries if isinstance(e, dict)]


def _meta(data):
    return data.get("meta") or {}


# --------------------------------------------------------------------------
# RT-001 / RT-002 — meta and the changelog must tell the same story
# --------------------------------------------------------------------------
def check_revision_coherence(data):
    findings = []
    meta = _meta(data)
    entries = _changelog(data)
    if not entries:
        # An empty changelog is a legitimate starting state, not a defect.
        return findings

    logged = {e.get("revision") for e in entries if e.get("revision")}
    current = meta.get("revision")

    if current and current not in logged:
        findings.append(Finding(
            "RT-001", "meta/revision",
            f"meta.revision is '{current}' but the changelog never mentions "
            f"it (records: {sorted(logged)}). A revision that exists in the "
            f"master and nowhere in its history has no traceable origin."))

    # RT-002 is the mirror: the log cites a revision the master denies. Only
    # meaningful when the entry is not part of a forward history, so it is
    # reported as INFO unless the master itself is FROZEN (a closed story).
    if current:
        unknown = sorted(r for r in logged if r and r > current)
        if unknown:
            sev = "ERROR" if meta.get("status") == META_FROZEN else "WARN"
            findings.append(Finding(
                "RT-002", "registers/changelog",
                f"changelog records revision(s) {unknown} that are ahead of "
                f"meta.revision '{current}'. The history claims changes the "
                f"master does not carry.", severity=sev))
    return findings


# --------------------------------------------------------------------------
# RT-003 / RT-004 — a freeze is an event that must be recorded and match
# --------------------------------------------------------------------------
def check_freeze_record(data):
    findings = []
    meta = _meta(data)
    entries = _changelog(data)
    freezes = [e for e in entries if e.get("type") == TYPE_FREEZE]

    if meta.get("status") == META_FROZEN and not freezes:
        findings.append(Finding(
            "RT-003", "meta/status",
            "meta.status is FROZEN but the changelog contains no FREEZE "
            "entry. The most consequential event in the project's life left "
            "no trace in its history."))

    master_hash = meta.get("master_hash")
    for i, e in enumerate(freezes):
        loc = f"registers/changelog/{i} (FREEZE)"
        after = e.get("master_hash_after")
        if after and master_hash and after != master_hash:
            findings.append(Finding(
                "RT-004", loc,
                f"FREEZE records master_hash_after '{after[:12]}…' but "
                f"meta.master_hash is '{master_hash[:12]}…'. The frozen "
                f"fingerprint and the master disagree about what was frozen. "
                f"B9 does not recompute either hash; it reports the conflict."))
        if master_hash and not after:
            findings.append(Finding(
                "RT-004", loc,
                "FREEZE entry records no master_hash_after while the master "
                "carries a hash, so the freeze cannot be tied to a state.",
                severity="WARN"))
    return findings


# --------------------------------------------------------------------------
# RT-005 / RT-008 — regeneration and regression honesty
# --------------------------------------------------------------------------
def check_proof_obligations(data):
    """Obligations for entry types A's rule TF1 does NOT cover.

    TECHNICAL_FIX is deliberately skipped: it belongs to A, and re-checking it
    here would duplicate ownership.
    """
    findings = []
    for i, e in enumerate(_changelog(data)):
        etype = e.get("type")
        loc = f"registers/changelog/{i} ({etype})"

        if etype == TYPE_TECHNICAL_FIX:
            continue                      # owned by A — rule TF1

        if etype == TYPE_REGENERATION and not e.get("output_diff_explained"):
            findings.append(Finding(
                "RT-005", loc,
                "REGENERATION changes generated artefacts but carries no "
                "output_diff_explained. A regeneration whose difference is "
                "unexplained cannot be distinguished from a silent design "
                "change."))

        # RT-008: an admitted regression outside the one type A polices.
        if e.get("regressions_found") is True:
            findings.append(Finding(
                "RT-008", loc,
                f"entry of type {etype} records regressions_found=true. A "
                f"recorded regression must not be swallowed by the history; "
                f"B9 surfaces it and does not resolve it."))

        # An explicit false is a claim; absence is UNSPECIFIED, not false.
        if e.get("tests_rerun") is False and etype in (
                TYPE_CR_APPLIED, TYPE_REGENERATION, TYPE_FREEZE):
            findings.append(Finding(
                "RT-008", loc,
                f"entry of type {etype} states tests_rerun=false. A change "
                f"admitted into the history without re-running the suite is "
                f"an untested change.", severity="WARN"))
    return findings


# --------------------------------------------------------------------------
# RT-006 / RT-007 — the record must run forward from a single start
# --------------------------------------------------------------------------
def check_chronology(data):
    findings = []
    entries = _changelog(data)
    if not entries:
        return findings

    dated = [(i, e) for i, e in enumerate(entries) if e.get("date")]
    for (i_prev, prev), (i_cur, cur) in zip(dated, dated[1:]):
        if str(cur["date"]) < str(prev["date"]):
            findings.append(Finding(
                "RT-006", f"registers/changelog/{i_cur}",
                f"entry dated {cur['date']} follows an entry dated "
                f"{prev['date']}. The history runs backwards, so cause and "
                f"effect cannot be established."))

    initials = [i for i, e in enumerate(entries)
                if e.get("type") == TYPE_INITIAL]
    if len(initials) > 1:
        findings.append(Finding(
            "RT-007", "registers/changelog",
            f"{len(initials)} INITIAL entries at positions {initials}. A "
            f"project has exactly one beginning."))
    if entries and not initials:
        findings.append(Finding(
            "RT-007", "registers/changelog",
            "the changelog has entries but no INITIAL one, so the history "
            "does not record where it started.", severity="WARN"))
    return findings


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def traceability_report(data):
    """A summary of the recorded history. A report, never applied to data."""
    entries = _changelog(data)
    meta = _meta(data)
    return {
        "meta_revision": meta.get("revision"),
        "meta_status": meta.get("status"),
        "entries": len(entries),
        "types": sorted({e.get("type") for e in entries if e.get("type")}),
        "revisions_logged": sorted({e.get("revision") for e in entries
                                    if e.get("revision")}),
        "freeze_recorded": any(e.get("type") == TYPE_FREEZE for e in entries),
    }


def validate_revisions(data):
    """Return (ok, findings). Detect / classify / report only."""
    findings = []
    findings += check_revision_coherence(data)
    findings += check_freeze_record(data)
    findings += check_proof_obligations(data)
    findings += check_chronology(data)
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("usage: validate_revisions.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_revisions(payload)
    for f in fs:
        print(f"{f.severity:5} {f.rule} [{f.location}] {f.message}")
    print()
    print("traceability:", traceability_report(payload))
    sys.exit(0 if ok else 1)
