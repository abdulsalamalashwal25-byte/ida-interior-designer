#!/usr/bin/env python3
"""
00.5-C5 — PRESENTATION LAYER (CLASS B OUTPUTS)

Reference (all CLOSED):
  00.5-C5-ARCHITECTURE-REPORT.md
  00.5-C5-ARCHITECTURE-RESOLUTION-ADDENDUM.md
  00.5-C5-ARCHITECTURE-CLOSURE-REPORT.md
  00.5-C5-IMPLEMENTATION-PLAN-AND-TEST-CONTRACT.md  (Gate 1 approved)

MISSION (single)
  Apply DECLARED presentation parameters to the SAME geometry that feeds the
  class A path, producing a class B output, without touching the geometry.

  C5 dresses. It does not draw.

GA HANDOFF (DEC-C5-01 CLOSED)
  The only geometric input is the GA Artifact already published by the class A
  path at record["assembly"]. C5 never calls assemble(), never re-assembles,
  never reads the master, and never parses C3's SVG as a measurement source.
  The artifact is treated as immutable: C5 works on a copy (H-2).

PARAMETERS (GAP-C-09 APPROVED WITH CONDITION)
  Exactly six: color, line_weight, shadow, label, sheet_order, print_scale.
  PP-1..PP-8 apply. PP-8 is absolute: no invented semantic, unit, default or
  interpretation. An absent parameter means NOTHING is applied — never a
  silent default.

PRINT SCALE (DEC-C5-02 CLOSED + SC-1)
  Only page/container size, viewport and presentation framing are allowed.
  Anything that would scale coordinates, change units, dimensions, positions
  or topology is a disguised geometric transform and is REJECTED.

TRUTH BOUNDARY (DEC-C5-08 CLOSED)
  C5 records what it received and what it applied. It does NOT certify that B
  has not deviated geometrically from A. That judgement belongs to D.
  Generator != Independent Verifier.

NOT OWNED HERE
  fidelity verdict -> D | outputs[] and governance -> E | manifest -> C6
  engineering fingerprint -> blocked (DEC-C2-01/02/03/05/06/08 open)
  geometry correctness -> B2..B5 via the master

C5 writes no file. It returns a representation plus evidence; persisting is
the caller's act.
"""

import copy

# --- the six approved parameters. This tuple is the WHOLE contract. --------
APPROVED_PARAMETERS = ("color", "line_weight", "shadow", "label",
                       "sheet_order", "print_scale")

# Parameter admission verdicts
ADMITTED = "ADMITTED"
REJECTED = "REJECTED"

# Rejection reason codes
RJ_OUT_OF_CONTRACT = "RJ-01"      # not among the six (PP-2)
RJ_UNKNOWN = "RJ-02"              # unknown/unnamed parameter (PP-3)
RJ_NO_SEMANTIC = "RJ-03"          # value whose meaning the contract does not
                                  # define (PP-8)
RJ_MISSING_UNIT = "RJ-04"         # unit required by the meaning, not supplied
                                  # (PP-8) — never assumed
RJ_GEOMETRY_IMPACT = "RJ-05"      # would alter extracted geometry (SC-1/5-B)
RJ_LABEL_CARRIES_NUMBER = "RJ-06"  # label carrying a computed dimension

# Element-level omission codes that indicate genuine PARTIAL coverage.
# NR-05 is deliberately EXCLUDED: it marks out-of-contract tiers and is
# present even on a complete assembly, so counting it would make every output
# PARTIAL and drain the marker of meaning (OBS-C5-02, measured).
PARTIAL_OMISSION_CODES = ("NR-01", "NR-02", "NR-03", "NR-04", "NR-06")
OUT_OF_CONTRACT_CODE = "NR-05"

COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
ABSTAIN = "ABSTAIN"
EMITTED = "EMITTED"

CLASS_B = "B"

# print_scale keys that only affect the viewing container, never the geometry.
FRAMING_KEYS = ("page_size", "viewport", "framing")

# Units the contract defines a meaning for. line_weight without one of these
# is rejected rather than guessed (PP-8).
LINE_WEIGHT_UNITS = ("mm", "px", "pt")


class ParameterVerdict:
    """Admission record for a single presentation parameter."""

    __slots__ = ("name", "value", "declared_by", "verdict", "code", "reason")

    def __init__(self, name, value, declared_by, verdict, code=None,
                 reason=None):
        self.name = name
        self.value = value
        self.declared_by = declared_by
        self.verdict = verdict
        self.code = code
        self.reason = reason

    def as_dict(self):
        return {"name": self.name, "value": self.value,
                "declared_by": self.declared_by, "verdict": self.verdict,
                "code": self.code, "reason": self.reason}


# --------------------------------------------------------------------------
# Parameter admission — PP-1 .. PP-8
# --------------------------------------------------------------------------
def _reject(name, value, who, code, reason):
    return ParameterVerdict(name, value, who, REJECTED, code, reason)


def admit_parameter(name, value, declared_by="caller"):
    """Admit or reject one parameter. Never repairs, never assumes."""
    if not name or not isinstance(name, str):
        return _reject(name, value, declared_by, RJ_UNKNOWN,
                       "parameter has no usable name; C5 does not guess what "
                       "was intended.")

    if name not in APPROVED_PARAMETERS:
        return _reject(
            name, value, declared_by, RJ_OUT_OF_CONTRACT,
            f"'{name}' is not among the six approved presentation parameters "
            f"{APPROVED_PARAMETERS}. Out of contract until explicitly "
            f"approved; section 5-B is not widened here.")

    if value is None:
        return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                       f"'{name}' was supplied without a value. C5 does not "
                       f"substitute a default (PP-1/PP-8).")

    # ---- per-parameter meaning checks (PP-8: no invented semantics) -------
    if name == "line_weight":
        # The contract does not define a unit for line_weight, so a bare
        # number has no defined meaning. Rejected, never assumed.
        if isinstance(value, dict):
            unit = value.get("unit")
            if unit is None:
                return _reject(name, value, declared_by, RJ_MISSING_UNIT,
                               "line_weight requires an explicit unit; the "
                               "contract defines none, so C5 does not assume "
                               "one (PP-8).")
            if unit not in LINE_WEIGHT_UNITS:
                return _reject(
                    name, value, declared_by, RJ_NO_SEMANTIC,
                    f"unit '{unit}' has no meaning defined in the contract "
                    f"for line_weight; C5 does not interpret it (PP-8).")
            if not isinstance(value.get("value"), (int, float)) or \
                    isinstance(value.get("value"), bool):
                return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                               "line_weight value is not numeric.")
        else:
            return _reject(
                name, value, declared_by, RJ_MISSING_UNIT,
                "line_weight was supplied as a bare value with no unit. The "
                "contract defines no default unit, so it is rejected rather "
                "than interpreted (PP-8).")

    elif name == "label":
        if not isinstance(value, str):
            return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                           "label must be presentational text.")
        # A label carrying a computed dimension would produce engineering
        # information — the Tier 3 risk excluded from the approved contract.
        if any(ch.isdigit() for ch in value):
            return _reject(
                name, value, declared_by, RJ_LABEL_CARRIES_NUMBER,
                "label contains a numeric token. A label carrying a dimension "
                "would emit engineering information (Tier 3 is out of "
                "contract), so it is rejected rather than sanitised.")

    elif name == "print_scale":
        # SC-1: framing only. Any coordinate/unit effect is a disguised
        # geometric transform.
        if not isinstance(value, dict):
            return _reject(
                name, value, declared_by, RJ_NO_SEMANTIC,
                "print_scale must declare a framing container; a bare scale "
                "value has no contract meaning and could imply coordinate "
                "scaling (SC-1).")
        offending = [k for k in value
                     if k not in FRAMING_KEYS]
        if offending:
            return _reject(
                name, value, declared_by, RJ_GEOMETRY_IMPACT,
                f"print_scale keys {offending} fall outside framing "
                f"{FRAMING_KEYS}. Anything able to scale coordinates or "
                f"change units is a disguised geometric transform (SC-1).")
        if not value:
            return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                           "print_scale declared with no framing content.")

    elif name == "color":
        if not isinstance(value, str):
            return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                           "color must be a declared colour token/string.")

    elif name == "shadow":
        if not isinstance(value, (bool, str)):
            return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                           "shadow must be a declared on/off or named setting.")

    elif name == "sheet_order":
        if isinstance(value, bool) or not isinstance(value, int):
            return _reject(name, value, declared_by, RJ_NO_SEMANTIC,
                           "sheet_order must be an integer ordering value.")

    return ParameterVerdict(name, value, declared_by, ADMITTED)


def admit_parameters(params, declared_by="caller"):
    """Admit a whole parameter set. Absent parameters are simply absent."""
    verdicts = []
    for name, value in (params or {}).items():
        verdicts.append(admit_parameter(name, value, declared_by))
    return verdicts


# --------------------------------------------------------------------------
# Coverage — PARTIAL derives from element omissions only (OBS-C5-02)
# --------------------------------------------------------------------------
def coverage_of(ga):
    """Return (state, element_omissions). NR-05 never implies PARTIAL."""
    omissions = [n for n in (ga.get("not_represented") or [])
                 if n.get("code") in PARTIAL_OMISSION_CODES]
    if not (ga.get("walls") or []):
        return ABSTAIN, omissions
    return (PARTIAL if omissions else COMPLETE), omissions


# --------------------------------------------------------------------------
# Lineage evidence — CONDITION-01
# --------------------------------------------------------------------------
def lineage_evidence(ga, identity=None, digest_fn=None):
    """Lineage evidence ONLY. Deliberately not an artifact identity.

    Per CONDITION-01 this must never be called artifact_id, never be treated
    as an engineering fingerprint, and never be presented as a solution to
    unique GA identity. Any final judgement on linkage belongs outside C5.
    """
    ident = identity or {}
    ev = {
        "project_id": ident.get("project_id", "NOT_SET"),
        "master_revision": ident.get("master_revision", "NOT_SET"),
        "contract_tiers": list(ga.get("contract_tiers") or []),
        "status": "PROVISIONAL",
        "usable_as_evidence": False,
        "note": ("Lineage evidence only. This is NOT an artifact_id, NOT an "
                 "engineering fingerprint, and does NOT establish a unique "
                 "GA identity or an A-to-B linkage claim. Final judgement "
                 "on linkage and fidelity lies outside C5."),
    }
    if digest_fn is not None:
        try:
            d = digest_fn(ga)
            ev["provisional_digest"] = d.get("digest") if isinstance(d, dict) \
                else None
            ev["digest_status"] = "PROVISIONAL"
        except Exception:
            ev["provisional_digest"] = None
            ev["digest_status"] = "NOT_AVAILABLE"
    return ev


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------
def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _num(v):
    """Copy a coordinate verbatim. No rounding, no quantization (rule 8)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return str(v) if isinstance(v, int) else repr(float(v))


def _style_for(admitted):
    """Build style attributes from ADMITTED parameters only.

    Nothing is substituted for an absent parameter (PP-1): the attribute is
    simply not emitted.
    """
    style = {}
    for v in admitted:
        if v.name == "color":
            style["stroke"] = v.value
        elif v.name == "line_weight":
            # Only the contract-defined shape {value, unit} is emitted. Any
            # other shape has no defined meaning, so it is skipped rather
            # than interpreted (PP-8).
            if isinstance(v.value, dict):
                style["stroke-width"] = v.value.get("value")
    return style


def _style_attrs(style):
    return "".join(f' {k}="{_esc(val)}"' for k, val in sorted(style.items())
                   if val is not None)


def emit_class_b(ga_artifact, parameters=None, identity=None,
                 declared_by="caller", digest_fn=None):
    """Produce a class B SVG from the GA artifact published by the A path.

    `ga_artifact` MUST be record["assembly"] from the class A emission.
    It is treated as read-only: C5 works on a deep copy (H-2).
    """
    record = {
        "class": CLASS_B,
        "format": "svg",
        "contract": "presentation/class-b/tier-0+1",
        "status": None,
        "svg": None,
        "abstention": None,
        "parameters_admitted": [],
        "parameters_rejected": [],
        "coverage": None,
        "omissions": [],
        "lineage_evidence": None,
        "geometry_source": "GA artifact published by the class A path "
                           "(record['assembly'])",
        "fidelity": "NOT_ASSESSED — whether B deviates geometrically from A "
                    "is judged by D. Generator != Independent Verifier.",
        "engineering_fingerprint": "NOT_ISSUED (blocked: DEC-C2-01/02/03/"
                                   "05/06/08)",
        "determinism": {"D0": "OBSERVED_IN_MEASURED_CASE",
                        "D0_provable": "NOT_ESTABLISHED",
                        "D1": "NOT_ESTABLISHED", "D2": "NOT_CLAIMED"},
    }

    if not isinstance(ga_artifact, dict):
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C5-ABS-01",
            "message": "no GA artifact supplied. C5 does not assemble "
                       "geometry and has no alternate source."}
        return record

    # H-2: never mutate what the caller handed over.
    ga = copy.deepcopy(ga_artifact)

    verdicts = admit_parameters(parameters, declared_by)
    admitted = [v for v in verdicts if v.verdict == ADMITTED]
    rejected = [v for v in verdicts if v.verdict == REJECTED]
    record["parameters_admitted"] = [v.as_dict() for v in admitted]
    record["parameters_rejected"] = [v.as_dict() for v in rejected]
    record["lineage_evidence"] = lineage_evidence(ga, identity, digest_fn)

    coverage, omissions = coverage_of(ga)
    record["coverage"] = coverage
    record["omissions"] = omissions

    if coverage == ABSTAIN or ga.get("outline") is None:
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C5-ABS-02",
            "message": "the GA artifact carries no eligible geometry to "
                       "present. C5 does not produce an empty B output that "
                       "could be read as a design."}
        return record

    outline = ga["outline"]["value"]
    style = _style_for(admitted)
    stroke = _style_attrs(style)

    xs, ys = [], []
    for p in outline:
        xs.append(p[0])
        ys.append(p[1])
    for w in ga.get("walls") or []:
        for pt in (w["start"]["value"], w["end"]["value"]):
            xs.append(pt[0])
            ys.append(pt[1])

    if any(_num(v) is None for v in xs + ys):
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C5-ABS-03",
            "message": "a coordinate in the artifact is not serialisable "
                       "verbatim; C5 abstains rather than transform it."}
        return record

    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    if max_x - min_x <= 0 or max_y - min_y <= 0:
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C5-ABS-04",
            "message": "artifact geometry has no extent on one axis; a "
                       "viewBox cannot be framed without inventing padding."}
        return record

    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="{_num(min_x)} {_num(min_y)} '
             f'{_num(max_x - min_x)} {_num(max_y - min_y)}">')
    L.append("  <!-- CLASS B — PRESENTATION VISUAL. Geometry is taken "
             "unchanged from the class A geometry assembly. -->")
    L.append("  <!-- Geometrically binding, aesthetically non-binding "
             "(Phase 00 section 10). -->")
    ident = identity or {}
    L.append(f'  <!-- project_id: {_esc(ident.get("project_id", "NOT_SET"))} '
             f'| master_revision: '
             f'{_esc(ident.get("master_revision", "NOT_SET"))} -->')
    L.append("  <!-- engineering fingerprint: NOT_ISSUED -->")
    L.append("  <!-- fidelity: NOT_ASSESSED — owned by D -->")

    if coverage == PARTIAL:
        L.append("  <!-- ===== PARTIAL ===== This presentation covers only "
                 "the elements represented in the source assembly. It is NOT "
                 "a complete design. Omitted elements are listed below. -->")

    pts = " ".join(f"{_num(x)},{_num(y)}" for x, y in
                   ((p[0], p[1]) for p in outline))
    L.append('  <g id="space-outline">')
    L.append(f'    <polygon points="{pts}" fill="none"{stroke or " stroke=\"\""}'
             f' data-provenance="{_esc(ga["outline"].get("provenance", ""))}"/>')
    L.append("  </g>")

    L.append('  <g id="walls">')
    for w in ga.get("walls") or []:
        a, b = w["start"]["value"], w["end"]["value"]
        L.append(f'    <line x1="{_num(a[0])}" y1="{_num(a[1])}" '
                 f'x2="{_num(b[0])}" y2="{_num(b[1])}"{stroke} '
                 f'data-id="{_esc(w["id"])}" data-tier="{_esc(w.get("tier"))}"/>')
    L.append("  </g>")

    L.append('  <g id="openings">')
    for o in ga.get("openings") or []:
        p0, p1 = o["p0"], o["p1"]
        L.append(f'    <line x1="{_num(p0[0])}" y1="{_num(p0[1])}" '
                 f'x2="{_num(p1[0])}" y2="{_num(p1[1])}"{stroke} '
                 f'data-id="{_esc(o["id"])}" data-kind="{_esc(o.get("kind"))}" '
                 f'data-tier="{_esc(o.get("tier"))}"/>')
    L.append("  </g>")

    for v in admitted:
        if v.name == "label":
            L.append(f'  <!-- label: {_esc(v.value)} -->')
        elif v.name == "shadow":
            L.append(f'  <!-- shadow: {_esc(v.value)} -->')
        elif v.name == "sheet_order":
            L.append(f'  <!-- sheet_order: {_esc(v.value)} -->')
        elif v.name == "print_scale":
            L.append(f'  <!-- framing (container only, geometry untouched): '
                     f'{_esc(sorted(v.value.items()))} -->')

    if omissions:
        L.append("  <!-- OMITTED ELEMENTS (declared, not silently dropped):")
        for n in omissions:
            L.append(f"       [{n.get('code')}] {_esc(n.get('target'))}: "
                     f"{_esc(n.get('message'))}")
        L.append("  -->")

    if rejected:
        L.append("  <!-- REJECTED PARAMETERS (declared, not applied):")
        for v in rejected:
            L.append(f"       [{v.code}] {_esc(v.name)}: {_esc(v.reason)}")
        L.append("  -->")

    L.append("</svg>")

    record["status"] = EMITTED
    record["svg"] = "\n".join(L) + "\n"
    return record


def presentation_evidence(record):
    """Evidence for D. Contains no verdict of its own."""
    return {
        "class": record.get("class"),
        "geometry_source": record.get("geometry_source"),
        "lineage_evidence": record.get("lineage_evidence"),
        "parameters_admitted": record.get("parameters_admitted"),
        "parameters_rejected": record.get("parameters_rejected"),
        "coverage": record.get("coverage"),
        "omissions": record.get("omissions"),
        "determinism": record.get("determinism"),
        "engineering_fingerprint": record.get("engineering_fingerprint"),
        "fidelity_verdict": "NOT_PROVIDED — D owns the judgement on whether B "
                            "deviates from the class A geometry.",
        "note": "C5 records what it received and what it applied. It does not "
                "certify geometric agreement between B and A.",
    }
