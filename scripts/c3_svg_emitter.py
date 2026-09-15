#!/usr/bin/env python3
"""
00.5-C3 — SVG EMITTER ADAPTER (EA) + EVIDENCE PACK (EP)

Reference: 00.5-C3-GEOMETRY-EMITTERS-ARCHITECTURE.md   (CLOSED)
           00.5-C3-DECISION-RESOLUTION-ADDENDUM.md     (CLOSED)
Approved: DEC-C3-02 SVG-first · DEC-C3-03 Tier 0 + Tier 1 · DEC-C3-01 numeric

ADAPTER RULES
  * transcribes the assembly verbatim; adds no border, grid, title or padding
    beyond the declared viewBox, and invents no element.
  * DEC-C3-01: values are serialised faithfully. If a value cannot be written
    without a numeric transform that might change it, the emitter ABSTAINS and
    reports. It never rounds silently and owns no quantization policy.
  * the output carries its scope tag, so a Tier 0+1 plan can never be read as
    a complete construction drawing.

CAPABILITY (three levels, all required — addendum section 5)
  1 format capability          : SVG is plain text, stdlib only
  2 approved output contract   : Tier 0 + Tier 1 (APPROVED)
  3 runtime capability         : no third-party dependency for SVG
  Levels are reported per (format x output), never as a blanket claim.

WHAT THIS DOES NOT DO
  * no fidelity verdict. Zero-invention is not fidelity proof. D owns fidelity.
  * no engineering fingerprint (blocked by DEC-C2-01/02/03/05/06/08).
  * no D1/D2 determinism claim.
  * writes no file by itself: it RETURNS text. Persisting is the caller's act.
"""

from c3_geometry_assembly import assemble, TIER0, TIER1

FORMAT_ID = "svg"
CONTRACT_ID = "floor-plan/tier-0+1"

ABSTAIN = "ABSTAIN"
EMITTED = "EMITTED"


def capability_report(contract_approved=True):
    """Capability per (format x output). Never a blanket 'SVG is available'."""
    return {
        "format": FORMAT_ID,
        "output": CONTRACT_ID,
        "level_1_format_capability": True,
        "level_1_detail": "SVG is text; serialised with the standard library.",
        "level_2_approved_output_contract": bool(contract_approved),
        "level_2_detail": "DEC-C3-03 approved Tier 0 + Tier 1.",
        "level_3_runtime_capability": True,
        "level_3_detail": "no third-party dependency required for SVG.",
        "capable": bool(contract_approved),
        "note": "Capability is declared per (format x output). It is not a "
                "claim that any other format or tier is available.",
    }


def _fmt(v):
    """Faithful serialisation of a coordinate (DEC-C3-01).

    Returns (text, ok). ok=False when the value cannot be written without a
    numeric transform that might alter it — the caller must then abstain.
    """
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None, False
    if v != v or v in (float("inf"), float("-inf")):    # NaN / infinities
        return None, False
    if isinstance(v, int):
        return str(v), True
    # repr() round-trips exactly for Python floats: no rounding is applied.
    text = repr(float(v))
    try:
        if float(text) != float(v):
            return None, False
    except (ValueError, OverflowError):
        return None, False
    return text, True


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def emit_svg(master, identity=None):
    """Return an emission record for a Tier 0 + Tier 1 floor plan.

    The record always states its own limits: what was omitted, what capability
    was present, and that no fidelity claim is being made.
    """
    ga = assemble(master)
    cap = capability_report()

    record = {
        "format": FORMAT_ID,
        "contract": CONTRACT_ID,
        "tiers": [TIER0, TIER1],
        "capability": cap,
        "status": None,
        "svg": None,
        "abstention": None,
        "assembly": ga.as_dict(),
        # Inherited claim ceiling — never raised here (CND-C2-04).
        "determinism": {"D0": "OBSERVED_IN_MEASURED_CASE",
                        "D0_provable": "NOT_ESTABLISHED",
                        "D1": "NOT_ESTABLISHED", "D2": "NOT_CLAIMED"},
        "engineering_fingerprint": "NOT_ISSUED (blocked: DEC-C2-01/02/03/"
                                   "05/06/08)",
        "fidelity": "NOT_ASSESSED — output-vs-master fidelity is owned by D; "
                    "zero-invention is not fidelity proof.",
    }

    if ga.outline is None:
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C3-ABS-01",
            "message": "space/outline is not available as an eligible [C]/[D] "
                       "fact, so the Tier 0 frame cannot be drawn. C3 does not "
                       "substitute a boundary.",
        }
        return record

    if not ga.walls:
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C3-ABS-02",
            "message": "no wall is eligible for transcription; a floor plan "
                       "without walls would misrepresent the master.",
        }
        return record

    # ---- collect coordinates, abstaining on any unfaithful number ---------
    pts = [tuple(p[:2]) for p in ga.outline.value]
    segments = []
    for w in ga.walls:
        segments.append((tuple(w["start"]["value"][:2]),
                         tuple(w["end"]["value"][:2]), w["id"]))
    apertures = [(tuple(o["p0"][:2]), tuple(o["p1"][:2]), o["id"], o["kind"])
                 for o in ga.openings]

    for x, y in (list(pts) + [p for s in segments for p in s[:2]]
                 + [p for a in apertures for p in a[:2]]):
        for c in (x, y):
            if not _fmt(c)[1]:
                record["status"] = ABSTAIN
                record["abstention"] = {
                    "code": "C3-ABS-03",
                    "message": f"coordinate {c!r} cannot be serialised without "
                               f"a numeric transform that might change it. "
                               f"C3 abstains rather than round (DEC-C3-01).",
                }
                return record

    # ---- viewBox from the transcribed geometry only -----------------------
    xs = [p[0] for p in pts] + [c[0] for s in segments for c in s[:2]]
    ys = [p[1] for p in pts] + [c[1] for s in segments for c in s[:2]]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    w_box, h_box = max_x - min_x, max_y - min_y
    if w_box <= 0 or h_box <= 0:
        record["status"] = ABSTAIN
        record["abstention"] = {
            "code": "C3-ABS-04",
            "message": "transcribed geometry has no extent in one axis; a "
                       "viewBox cannot be derived without inventing padding.",
        }
        return record

    def fx(v):
        return _fmt(v)[0]

    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="{fx(min_x)} {fx(min_y)} {fx(w_box)} {fx(h_box)}">')

    ident = identity or {}
    L.append("  <!-- CLASS A OUTPUT — SCOPE: Tier 0 + Tier 1 "
             "(outline, walls, openings). "
             "NOT a complete construction drawing. -->")
    L.append(f'  <!-- project_id: {_esc(ident.get("project_id", "NOT_SET"))} '
             f'| master_revision: '
             f'{_esc(ident.get("master_revision", "NOT_SET"))} -->')
    L.append("  <!-- engineering fingerprint: NOT_ISSUED "
             "(DEC-C2-01/02/03/05/06/08 open) -->")
    L.append("  <!-- fidelity: NOT_ASSESSED — owned by D -->")

    L.append('  <g id="space-outline">')
    pts_txt = " ".join(f"{fx(x)},{fx(y)}" for x, y in pts)
    L.append(f'    <polygon points="{pts_txt}" fill="none" stroke="#000" '
             f'stroke-width="1" data-provenance="space/outline"/>')
    L.append("  </g>")

    L.append('  <g id="walls">')
    for (x0, y0), (x1, y1), wid in segments:
        L.append(f'    <line x1="{fx(x0)}" y1="{fx(y0)}" x2="{fx(x1)}" '
                 f'y2="{fx(y1)}" stroke="#000" stroke-width="2" '
                 f'data-id="{_esc(wid)}" data-tier="{TIER0}"/>')
    L.append("  </g>")

    L.append('  <g id="openings">')
    for (x0, y0), (x1, y1), oid, kind in apertures:
        L.append(f'    <line x1="{fx(x0)}" y1="{fx(y0)}" x2="{fx(x1)}" '
                 f'y2="{fx(y1)}" stroke="#fff" stroke-width="3" '
                 f'data-id="{_esc(oid)}" data-kind="{_esc(kind)}" '
                 f'data-tier="{TIER1}"/>')
    L.append("  </g>")

    if ga.not_represented:
        L.append("  <!-- NOT REPRESENTED (declared):")
        for n in ga.not_represented:
            L.append(f"       [{n.code}] {_esc(n.target)}: {_esc(n.message)}")
        L.append("  -->")

    L.append("</svg>")

    record["status"] = EMITTED
    record["svg"] = "\n".join(L) + "\n"
    return record


def evidence_pack(record, environment=None):
    """Evidence for D to judge against. Contains no verdict of its own."""
    ga = record.get("assembly", {})
    coords = []
    for w in ga.get("walls", []):
        coords.append({"element": w["id"], "field": "start",
                       "value": w["start"]["value"],
                       "provenance": w["start"]["provenance"]})
        coords.append({"element": w["id"], "field": "end",
                       "value": w["end"]["value"],
                       "provenance": w["end"]["provenance"]})
    for o in ga.get("openings", []):
        coords.append({"element": o["id"], "field": "offset",
                       "value": o["offset"]["value"],
                       "provenance": o["offset"]["provenance"]})
        coords.append({"element": o["id"], "field": "width",
                       "value": o["width"]["value"],
                       "provenance": o["width"]["provenance"]})
    return {
        "coordinate_table": coords,
        "not_represented": ga.get("not_represented", []),
        "capability": record.get("capability"),
        "determinism": record.get("determinism"),
        "engineering_fingerprint": record.get("engineering_fingerprint"),
        "environment": environment or "NOT_SET",
        "fidelity_verdict": "NOT_PROVIDED — D owns output-vs-master fidelity.",
        "note": "Provenance shows each value came from the master. It does "
                "NOT show the value was placed correctly in the drawing.",
    }
