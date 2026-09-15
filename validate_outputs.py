#!/usr/bin/env python3
"""Phase 00.5-B8 — Output / Representation Integrity.

WHAT B8 OWNS:
  The integrity of how truth that already exists in the SSOT is REPRESENTED
  when it leaves the system. An output may never claim more certainty, more
  authority or more provenance than the master it was built from.

  Authority flows ONE WAY:   MASTER -> class A -> class B -> class C
  It never flows back. A generated artefact does not become a source of truth
  by the mere fact that it was generated.

WHAT B8 DOES NOT OWN (consumed, never re-implemented):
  - class <-> guarantee <-> binding_* consistency (O1/O2/O3)  -> A (schema)
  - class C "100% / مطابق" caption language (lint_caption)    -> A
  - derived_from_output linkage, output cycles, fingerprint
    coherence (XR-014/015/016/017/018)                        -> B1
  - arithmetic of a [D]                                       -> B6
  - uncertainty state transitions and blocking                -> B7
  - wall/furniture/movement/door geometry                     -> B2..B5
  - approval impersonation / identity / authority             -> 00.5-E

HARD LIMIT — DECLARED, NOT HIDDEN:
  B8 does NOT open the produced file. It cannot prove that plan.dxf actually
  contains the geometry the master describes. It validates the CLAIMS an
  output makes about its source, never the pixels or the vectors. Geometric
  fidelity of the artefact itself is an explicit Capability Gap.

HARD RULES:
  * detect / classify / report only — no auto-fix, no regeneration
  * UNKNOWN is not automatically an ERROR: severity is output-aware
  * no design standard, no clearance, no tolerance invented here
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_gate import iter_facts                              # noqa: E402
from validate_blocking import build_uncertainty_map             # noqa: E402

# --------------------------------------------------------------------------
# Representation layers. Every token below already exists in the schema —
# nothing is invented because it "seemed useful".
# --------------------------------------------------------------------------
CLASS_DERIVED = "A"        # deterministic geometric match
CLASS_PRESENTATION = "B"   # geometry derived, visual treatment may differ
CLASS_NON_AUTHORITATIVE = "C"

GUARANTEE_BY_CLASS = {
    CLASS_DERIVED: "DETERMINISTIC_GEOMETRIC_MATCH",
    CLASS_PRESENTATION: "GEOMETRY_DERIVED_VISUAL_TREATMENT_MAY_DIFFER",
    CLASS_NON_AUTHORITATIVE: "NOT_GEOMETRICALLY_GUARANTEED_NON_BINDING",
}

# Authority a representation may carry. Output-aware, exactly as B7 is
# dependency-aware: "UNKNOWN = ERROR for everything" is explicitly rejected.
AUTH_AUTHORITATIVE = "AUTHORITATIVE"    # class A, binding geometry
AUTH_DERIVED = "DERIVED"                # class B
AUTH_INDICATIVE = "INDICATIVE"          # class C with a fingerprint
AUTH_NON_BINDING = "NON_BINDING"        # class C, guarantees nothing

# A source_type that can never, by itself, establish a confirmed fact.
NON_AUTHORITATIVE_SOURCES = {"AI_IMAGE"}

# Language that asserts finality or construction authority. This is NOT the
# class-C "100%/مطابق" list — that one belongs to A's lint_caption. These
# words claim APPROVAL STATUS, which is a different failure mode.
AUTHORITY_LANGUAGE = re.compile(
    r"(for\s+construction|as[\s-]?built|final(?!\s*ly)|issued\s+for|"
    r"approved|tender|contract\s+document|"
    r"للتنفيذ|نهائي|معتمد|كما\s+نُفِّذ)",
    re.IGNORECASE)

# A hash made only of one repeated character carries no provenance.
_EMPTY_HASH = re.compile(r"^(.)\1{15,}$")

UNCERTAIN_STATUSES = {"U", "P", "A"}


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"<{self.severity} {self.rule} @ {self.location}>"


def _outputs(data):
    return [o for o in (data.get("outputs") or []) if isinstance(o, dict)]


def classify_authority(out):
    """Which authority level a representation may legitimately claim."""
    cls = out.get("class")
    if cls == CLASS_DERIVED and out.get("binding_geometry"):
        return AUTH_AUTHORITATIVE
    if cls == CLASS_PRESENTATION:
        return AUTH_DERIVED
    if cls == CLASS_NON_AUTHORITATIVE:
        return AUTH_INDICATIVE if out.get("fingerprint") else AUTH_NON_BINDING
    return AUTH_NON_BINDING


def _binding(out):
    return bool(out.get("binding_geometry")) or \
        out.get("guarantee") == GUARANTEE_BY_CLASS[CLASS_DERIVED]


# --------------------------------------------------------------------------
# OR-001 / OR-002 — an output may not out-claim its source
# --------------------------------------------------------------------------
def check_certainty_claims(data):
    """A binding representation may not rest on uncertain master content
    without that uncertainty remaining visible.

    The uncertainty map comes from B7 — B8 does not recompute what is
    uncertain, it only judges how the OUTPUT represents it.
    """
    findings = []
    outs = _outputs(data)
    if not outs:
        return findings

    uncertain = build_uncertainty_map(data)
    if not uncertain:
        return findings

    uncomputable = {p: why for p, (kind, why) in uncertain.items()
                    if kind == "UNCOMPUTABLE"}
    unknown = {p: why for p, (kind, why) in uncertain.items()
               if kind != "UNCOMPUTABLE"}

    for out in outs:
        oid = out.get("output_id", "<output>")
        loc = f"outputs/{oid}"
        auth = classify_authority(out)
        caption = out.get("caption") or ""
        discloses = bool(re.search(
            r"(unknown|unresolved|uncomputable|provisional|indicative|"
            r"غير\s*معروف|غير\s*محسوم|مبدئي)", caption, re.IGNORECASE))

        if auth in (AUTH_AUTHORITATIVE, AUTH_DERIVED):
            if uncomputable:
                findings.append(Finding(
                    "OR-002", loc,
                    f"output is {auth} and represents a master that still "
                    f"contains UNCOMPUTABLE values "
                    f"({sorted(uncomputable)[:2]}). A value B6 could not "
                    f"compute must not be presented as an established figure. "
                    f"B8 does not recompute it and does not remove it."))
            if unknown:
                findings.append(Finding(
                    "OR-001", loc,
                    f"output is {auth} (class {out.get('class')}) while the "
                    f"master still holds uncertain content "
                    f"({sorted(unknown)[:2]}). A representation may not claim "
                    f"more certainty than its source."))
        else:
            # Non-binding: uncertainty is acceptable, but silence about it is
            # reported as INFO — recorded, never escalated into an error.
            if (uncertain and not discloses):
                findings.append(Finding(
                    "OR-009", loc,
                    f"output is {auth}: uncertainty in the master is allowed "
                    f"here and does NOT block. Recorded only: the caption "
                    f"does not mention that the model is still incomplete.",
                    severity="INFO"))
    return findings


# --------------------------------------------------------------------------
# OR-003 / OR-004 / OR-005 — provenance must survive the transformation
# --------------------------------------------------------------------------
def _lineage_related(outs, a_id, b_id):
    """True when one output descends from the other via derived_from_output.

    A class-B presentation IS the same view of the same model state as its
    class-A parent, so the two legitimately share a fingerprint. Only
    UNRELATED artefacts claiming the same provenance are a contradiction.
    (The validity of the link itself is XR-014/015 — B1's rule, not B8's.)
    """
    by_id = {o.get("output_id"): o for o in outs}

    def ancestors(start):
        seen, cur = set(), by_id.get(start, {}).get("derived_from_output")
        while cur and cur not in seen:
            seen.add(cur)
            cur = by_id.get(cur, {}).get("derived_from_output")
        return seen

    return b_id in ancestors(a_id) or a_id in ancestors(b_id)


def check_provenance(data):
    findings = []
    meta = data.get("meta") or {}
    seen_fp = {}
    outs_all = _outputs(data)

    for out in _outputs(data):
        oid = out.get("output_id", "<output>")
        loc = f"outputs/{oid}"
        fp = out.get("fingerprint") or {}

        # OR-003: a fingerprint that carries no real trace.
        # NOTE: existence/coherence of fingerprint FIELDS is XR-017/018 (B1).
        # B8 only asks whether the trace is substantive.
        empty = [k for k, v in fp.items()
                 if isinstance(v, str) and _EMPTY_HASH.match(v)]
        if empty:
            findings.append(Finding(
                "OR-003", loc,
                f"fingerprint fields {sorted(empty)} are placeholder values "
                f"that bind this output to nothing. Provenance was lost in "
                f"the transformation from master to output; the file cannot "
                f"be traced back to the data it claims to represent."))

        if not fp and _binding(out):
            findings.append(Finding(
                "OR-003", loc,
                "a binding output carries no fingerprint at all: there is no "
                "link back to the master it claims to represent."))

        # OR-004: the same fingerprint on two different files.
        key = tuple(sorted((k, v) for k, v in fp.items()
                           if isinstance(v, (str, int, float))))
        if key:
            clash = (key in seen_fp and seen_fp[key][1] != out.get("file")
                     and not _lineage_related(outs_all, seen_fp[key][0], oid))
            if clash:
                findings.append(Finding(
                    "OR-004", loc,
                    f"identical fingerprint to output '{seen_fp[key][0]}' but "
                    f"a different file ('{out.get('file')}' vs "
                    f"'{seen_fp[key][1]}'). Two different artefacts cannot "
                    f"both be the same view of the same model; at least one "
                    f"misrepresents its provenance."))
            else:
                seen_fp[key] = (oid, out.get("file"))

        # OR-005: an output cannot predate the master it derives from.
        gen = out.get("generated_on")
        created = meta.get("created_on")
        if gen and created and str(gen) < str(created):
            findings.append(Finding(
                "OR-005", loc,
                f"generated_on {gen} precedes the master's created_on "
                f"{created}. An output cannot be derived from data that did "
                f"not yet exist."))
    return findings


# --------------------------------------------------------------------------
# OR-006 / OR-007 — an output must not look more final than the project is
# --------------------------------------------------------------------------
def check_authority_language(data):
    findings = []
    meta = data.get("meta") or {}
    frozen = meta.get("status") == "FROZEN"
    is_test = bool(meta.get("is_test_project"))
    banner = (meta.get("test_banner") or "TEST PROJECT").upper()

    for out in _outputs(data):
        oid = out.get("output_id", "<output>")
        loc = f"outputs/{oid}"
        caption = out.get("caption") or ""

        # OR-006: finality language while the master is not frozen.
        hit = AUTHORITY_LANGUAGE.search(caption)
        if hit and not frozen:
            findings.append(Finding(
                "OR-006", loc,
                f"caption claims authority ('{hit.group(0)}') while "
                f"meta.status is {meta.get('status')}. A representation may "
                f"not present itself as final or construction-ready while the "
                f"master it came from is not."))

        # OR-007: a test project must not emit an unmarked deliverable.
        if is_test and caption and banner.split()[0] not in caption.upper() \
                and "TEST" not in caption.upper():
            findings.append(Finding(
                "OR-007", loc,
                f"this is a TEST PROJECT but the caption carries no test "
                f"marking. A test artefact that escapes without its banner "
                f"can be mistaken for a real deliverable.",
                severity="WARN"))
    return findings


# --------------------------------------------------------------------------
# OR-008 — reverse contamination: an artefact becoming a source of truth
# --------------------------------------------------------------------------
def check_reverse_contamination(data):
    """PRESENTATION -> MASTER and AI_IMAGE -> CONFIRMED FACT are forbidden.

    No rule authorising such a promotion exists, and B8 does not invent one.
    """
    findings = []
    out_ids = {o.get("output_id") for o in _outputs(data)}
    out_files = {o.get("file") for o in _outputs(data)}

    for path, fact in iter_facts(data):
        status = fact.get("status")
        src_type = fact.get("source_type")
        src_ref = str(fact.get("source_ref") or "")

        # An AI image can never establish a confirmed or derived fact.
        if src_type in NON_AUTHORITATIVE_SOURCES and status in ("C", "D"):
            findings.append(Finding(
                "OR-008", path,
                f"fact is [{status}] but its source_type is {src_type}. An AI "
                f"visual is NOT geometry and cannot establish a confirmed "
                f"fact. Authority flows master -> output, never back."))

        # A fact whose evidence is an output is contaminated in reverse.
        if status in ("C", "D"):
            cited = [o for o in out_ids if o and o in src_ref] + \
                    [f for f in out_files if f and f in src_ref]
            if cited:
                findings.append(Finding(
                    "OR-008", path,
                    f"fact is [{status}] and cites generated artefact(s) "
                    f"{sorted(set(cited))} as its source. A generated output "
                    f"does not become a source of truth by being generated; "
                    f"the master is the only SSOT."))
    return findings


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def representation_report(data):
    """Authority level of every output. A report, never applied to the data."""
    return {o.get("output_id"): classify_authority(o) for o in _outputs(data)}


def validate_outputs(data):
    """Return (ok, findings). Detect / classify / report only."""
    findings = []
    findings += check_certainty_claims(data)
    findings += check_provenance(data)
    findings += check_authority_language(data)
    findings += check_reverse_contamination(data)
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("usage: validate_outputs.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_outputs(payload)
    for f in fs:
        print(f"{f.severity:5} {f.rule} [{f.location}] {f.message}")
    print()
    print("authority map:", representation_report(payload))
    sys.exit(0 if ok else 1)
