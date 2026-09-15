#!/usr/bin/env python3
"""Phase 00.5-B5 — Door Swing & Doorway Integrity.

SCOPE (owned here):
  1. the host wall of a door resolves well enough to locate the aperture
  2. aperture dimensions are used ONLY when known and trustworthy
  3. swing is honoured ONLY when explicitly represented in the master
  4. swing arc vs other doors, vs furniture, vs the doorway threshold
  5. an explicit verdict per door: PASS / ERROR / UNKNOWN / INFO

NOT OWNED HERE (consumed, never re-implemented):
  - existence of any referenced id                 -> B1  (XR-001)
  - opening overruns wall / negative offset /
    two openings overlapping on one wall           -> B2  (WT-008/009/010)
  - furniture-vs-furniture / wall / column overlap -> B3  (FC-003/004/005)
  - declared circulation path behaviour            -> B4  (MV-*)
  - status & source legitimacy                     -> A
  - formula correctness -> B6 · blocking gate -> B7

HARD RULES:
  * no default rotation, no default hinge, no default opening side
  * no invented door width, height or standard
  * an absent swing is a GAP, never an assumed direction
  * no swept volume is built when the swing is not represented
  * UNKNOWN never auto-escalates to ERROR
  * ERROR only on a conflict provable from the declared data
  * detect / classify / report only — never repair, never rearrange
"""

import math

from validate_furniture import (  # noqa: F401
    footprint,
    rect_overlap,
    _dist_to_poly,
    _point_in_poly,
    _seg_seg_dist,
    _segments_cross,
    _fact_value,
    _is_unresolved,
    _xy,
    _wd,
    VALID_DATUMS,
    GEOMETRY_USABLE_STATUSES,
    TRUSTED_SOURCES,
    OVERLAP_TOLERANCE_MM,
)

# --------------------------------------------------------------------------
# Constants — tolerances and discretisation only. NO door dimension, NO angle.
# --------------------------------------------------------------------------
GEOM_TOLERANCE_MM = 1.0
ARC_SEGMENTS = 12          # polygon fidelity when approximating the swept arc
# Strict relative margin applied to the CIRCUMSCRIBED hull so that containment
# of the true sector is robust, not merely tangent. Purely a numerical safety
# factor: it is NOT a clearance, an ergonomic figure or a design value.
CONTAINMENT_MARGIN = 1e-9
VALID_HINGES = ("START", "END")
VALID_SIDES = ("POSITIVE", "NEGATIVE")

PASS = "PASS"
ERROR = "ERROR"
UNKNOWN = "UNKNOWN"
INFO = "INFO"


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"[{self.severity}] {self.rule} {self.location}: {self.message}"


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def aperture_geometry(wall, offset, width):
    """Locate the aperture on its host wall.

    Returns (p_start, p_end, unit_along, unit_normal) or None. Uses the same
    host_wall + offset convention B2 already enforces; nothing is invented.
    """
    a = _xy(_fact_value(wall.get("start")))
    b = _xy(_fact_value(wall.get("end")))
    if a is None or b is None:
        return None
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L <= GEOM_TOLERANCE_MM:
        return None
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -uy, ux
    p0 = (a[0] + ux * offset, a[1] + uy * offset)
    p1 = (a[0] + ux * (offset + width), a[1] + uy * (offset + width))
    return p0, p1, (ux, uy), (nx, ny)


def swing_polygon(pivot, leaf_vec, side_sign, angle_deg, steps=ARC_SEGMENTS,
                  mode="INNER"):
    """Polygonal approximation of the swept sector of a leaf.

    mode="INNER"  : INSCRIBED. Every point is inside the true sector, so an
                    intersection with it PROVES a real collision.
    mode="OUTER"  : CIRCUMSCRIBED. The true sector is entirely inside it, so
                    NO intersection with it PROVES real clearance.

    The two together sandwich the exact sector. Neither one alone is a decision
    procedure: the inscribed hull can miss a real touch (it under-covers by the
    sagitta), and the circumscribed hull can report a touch that is not real.
    Built strictly from declared values; nothing here supplies a default.
    """
    R = math.hypot(leaf_vec[0], leaf_vec[1])
    if R <= 0 or steps < 1:
        return [pivot]
    step = math.radians(abs(angle_deg)) / steps
    # Pushing the vertices out by 1/cos(step/2) lifts every chord onto or past
    # the true arc, which is what makes the OUTER hull a containing hull.
    # The bare 1/cos(step/2) scale makes each chord TANGENT to the true arc,
    # i.e. containment with zero margin, where boundary ties can fall either
    # way. A small strict margin makes the containment robust rather than
    # marginal. It widens the undecidable band slightly, which is the
    # conservative direction (never a false PASS).
    scale = ((1.0 / math.cos(step / 2.0)) * (1.0 + CONTAINMENT_MARGIN)
             if mode == "OUTER" else 1.0)
    pts = [pivot]
    for i in range(steps + 1):
        t = math.radians(angle_deg * i / steps) * side_sign
        ca, sa = math.cos(t), math.sin(t)
        vx = (leaf_vec[0] * ca - leaf_vec[1] * sa) * scale
        vy = (leaf_vec[0] * sa + leaf_vec[1] * ca) * scale
        pts.append((pivot[0] + vx, pivot[1] + vy))
    return pts


def arc_uncertainty_mm(leaf_len, angle_deg, steps=ARC_SEGMENTS):
    """Radial width of the undecidable band between the two hulls (sagitta)."""
    if leaf_len <= 0 or steps < 1:
        return 0.0
    step = math.radians(abs(angle_deg)) / steps
    return leaf_len * ((1.0 / math.cos(step / 2.0)) * (1.0 + CONTAINMENT_MARGIN)
                       - 1.0)


def _poly_overlap(p1, p2):
    """Overlap test for convex-ish polygons via edge crossing + containment."""
    for pt in p2:
        if _point_in_poly(pt, p1):
            return True
    for pt in p1:
        if _point_in_poly(pt, p2):
            return True
    n1, n2 = len(p1), len(p2)
    for i in range(n1):
        for j in range(n2):
            if _segments_cross(p1[i], p1[(i + 1) % n1],
                               p2[j], p2[(j + 1) % n2]):
                return True
    return False


def _trusted(node):
    return (isinstance(node, dict) and not _is_unresolved(node)
            and node.get("status") in GEOMETRY_USABLE_STATUSES
            and node.get("source_type") in TRUSTED_SOURCES)


def _collect_furniture(data):
    """Resolved furniture footprints, consumed from B3's own geometry.

    A piece whose datum or rotation is UNKNOWN is NOT given an assumed
    orientation; it is returned separately so it can only yield UNKNOWN.
    """
    known, unresolved = [], []
    for i, f in enumerate(data.get("furniture") or []):
        fid = f.get("id") or f"furniture/{i}"
        pos, dim = f.get("position"), f.get("dims")
        if _is_unresolved(pos) or _is_unresolved(dim):
            unresolved.append((fid, "geometry UNKNOWN"))
            continue
        c, wd = _xy(_fact_value(pos)), _wd(_fact_value(dim))
        if c is None or wd is None or wd[0] <= 0 or wd[1] <= 0:
            unresolved.append((fid, "geometry malformed"))
            continue
        pr, rn = f.get("position_reference"), f.get("rotation")
        datum = _fact_value(pr) if isinstance(pr, dict) else None
        if not (isinstance(pr, dict) and not _is_unresolved(pr)
                and pr.get("status") in GEOMETRY_USABLE_STATUSES
                and datum in VALID_DATUMS):
            unresolved.append((fid, "position_reference UNKNOWN"))
            continue
        if not (isinstance(rn, dict) and not _is_unresolved(rn)
                and rn.get("status") in GEOMETRY_USABLE_STATUSES):
            unresolved.append((fid, "rotation UNKNOWN"))
            continue
        try:
            rot = float(_fact_value(rn))
        except (TypeError, ValueError):
            unresolved.append((fid, "rotation malformed"))
            continue
        known.append((fid, footprint(c[0], c[1], wd[0], wd[1], datum, rot)))
    return known, unresolved


# --------------------------------------------------------------------------
# Main check
# --------------------------------------------------------------------------
def check_doors(data):
    findings = []
    verdicts = {}

    openings = data.get("openings") or []
    doors = [(i, o) for i, o in enumerate(openings)
             if o.get("kind") == "door"]
    if not doors:
        return findings, verdicts

    walls = {w.get("id"): w for w in (data.get("walls") or [])}
    known_furn, unresolved_furn = _collect_furniture(data)

    resolved = {}          # did -> aperture geometry
    arcs = {}              # did -> swept polygon

    for i, op in doors:
        did = op.get("id") or f"openings/{i}"
        loc = f"openings/{i} ({did})"
        state = None

        # ---- DS-001 host wall usable for geometry ------------------------
        host = op.get("host_wall")
        wall = walls.get(host)
        if wall is None:
            findings.append(Finding(
                "DS-001", loc,
                f"host_wall '{host}' does not resolve to a wall, so the "
                f"aperture cannot be located. Existence of the reference "
                f"itself is owned by B1/XR-001.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        if _is_unresolved(wall.get("start")) or _is_unresolved(wall.get("end")):
            findings.append(Finding(
                "DS-001", loc,
                f"host wall '{host}' has UNKNOWN geometry, so the aperture "
                f"cannot be located. No position is assumed.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue

        # ---- DS-002 aperture dimensions known AND trusted ----------------
        off_node, w_node = op.get("offset"), op.get("width")
        if not _trusted(off_node) or not _trusted(w_node):
            findings.append(Finding(
                "DS-002", loc,
                "offset or width is UNKNOWN or not from a trusted source, so "
                "the aperture is not dimensioned. Door sizes are never "
                "invented.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        try:
            offset = float(_fact_value(off_node))
            width = float(_fact_value(w_node))
        except (TypeError, ValueError):
            findings.append(Finding(
                "DS-002", loc, "offset or width is malformed; no geometry.",
                severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        if width <= 0:
            findings.append(Finding(
                "DS-002", loc, f"aperture width is not positive ({width})."))
            verdicts[did] = ERROR
            continue

        geom = aperture_geometry(wall, offset, width)
        if geom is None:
            findings.append(Finding(
                "DS-001", loc,
                f"host wall '{host}' is degenerate; the aperture cannot be "
                f"placed.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        resolved[did] = (geom, wall, loc)

        # ---- DS-003 / DS-004 / DS-005 swing representation ---------------
        sw = op.get("swing")
        if sw is None:
            findings.append(Finding(
                "DS-003", loc,
                "no swing is declared for this door. The opening geometry is "
                "therefore NOT represented: no arc is computed, no direction "
                "is assumed, and no swing conflict can be reported. Recorded "
                "as a representation GAP.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        if _is_unresolved(sw) or sw.get("status") not in GEOMETRY_USABLE_STATUSES:
            findings.append(Finding(
                "DS-003", loc,
                f"swing is [{sw.get('status')}] and not usable for geometry. "
                f"No arc is built and no direction is assumed.",
                severity="INFO"))
            verdicts[did] = UNKNOWN
            continue

        val = _fact_value(sw)
        if not isinstance(val, dict):
            findings.append(Finding(
                "DS-004", loc,
                "swing is declared but its structure is insufficient to build "
                "an arc (hinge, side and angle are all required). Nothing is "
                "guessed; recorded as a representation GAP.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        hinge, side, angle = val.get("hinge"), val.get("side"), val.get("angle")
        if hinge is None or side is None or angle is None:
            missing = [k for k, v in (("hinge", hinge), ("side", side),
                                      ("angle", angle)) if v is None]
            findings.append(Finding(
                "DS-004", loc,
                f"swing is missing {missing}; the arc cannot be built and the "
                f"missing part is NOT defaulted.", severity="INFO"))
            verdicts[did] = UNKNOWN
            continue
        if hinge not in VALID_HINGES or side not in VALID_SIDES:
            findings.append(Finding(
                "DS-005", loc,
                f"swing declares hinge='{hinge}' side='{side}', which are not "
                f"valid values {VALID_HINGES} / {VALID_SIDES}."))
            verdicts[did] = ERROR
            continue
        # bool is a subclass of int: True must not slip through as 1 degree.
        if isinstance(angle, bool) or not isinstance(angle, (int, float)):
            findings.append(Finding(
                "DS-005", loc,
                f"swing angle must be a number in degrees; got "
                f"{type(angle).__name__}. A malformed angle never reaches the "
                f"geometry."))
            verdicts[did] = ERROR
            continue
        angle = float(angle)
        if angle != angle or angle in (float("inf"), float("-inf")):
            findings.append(Finding(
                "DS-005", loc, "swing angle is not a finite number."))
            verdicts[did] = ERROR
            continue
        unit = sw.get("unit")
        if unit is not None and unit != "deg":
            findings.append(Finding(
                "DS-005", loc,
                f"swing is declared with unit '{unit}'; the angle is "
                f"interpreted in degrees only and is not converted by guess."))
            verdicts[did] = ERROR
            continue
        if not (0 < angle <= 180):
            findings.append(Finding(
                "DS-005", loc,
                f"swing angle {angle} is outside the representable range "
                f"(0, 180]."))
            verdicts[did] = ERROR
            continue

        p0, p1, u, n = geom
        pivot = p0 if hinge == "START" else p1
        far = p1 if hinge == "START" else p0
        leaf = (far[0] - pivot[0], far[1] - pivot[1])
        sign = 1.0 if side == "POSITIVE" else -1.0
        # Orient so the sweep travels towards the declared side of the wall.
        # DEFECT-B5-01 (found and fixed before shipping): the sign was
        # inverted, so POSITIVE swept towards the NEGATIVE normal. Verified
        # independently: rotating the leaf by +angle moves it towards +n when
        # cross(leaf, n) > 0.
        cross = leaf[0] * n[1] - leaf[1] * n[0]
        direction = sign * (1.0 if cross > 0 else -1.0)
        leaf_len = math.hypot(leaf[0], leaf[1])
        arcs[did] = {
            "inner": swing_polygon(pivot, leaf, direction, angle, mode="INNER"),
            "outer": swing_polygon(pivot, leaf, direction, angle, mode="OUTER"),
            "band": arc_uncertainty_mm(leaf_len, angle),
        }
        verdicts[did] = PASS

    # ---- DS-006 arc vs arc ----------------------------------------------
    # PROVEN   : the two INSCRIBED hulls already overlap -> real collision.
    # UNDECIDED: only the CIRCUMSCRIBED hulls overlap -> inside the sagitta
    #            band; NOT asserted as a collision and NOT cleared either.
    # CLEAR    : the OUTER hulls miss -> proven clear, because the true sectors
    #            are contained in them.
    ids = sorted(arcs.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if _poly_overlap(arcs[a]["inner"], arcs[b]["inner"]):
                findings.append(Finding(
                    "DS-006", f"openings ({a}, {b})",
                    f"the swing arcs of '{a}' and '{b}' overlap: the two "
                    f"leaves can collide. Proven on the INSCRIBED hulls, which "
                    f"lie strictly inside the true sectors, so the collision "
                    f"is real and not an artefact of the approximation."))
                verdicts[a] = ERROR
                verdicts[b] = ERROR
            elif _poly_overlap(arcs[a]["outer"], arcs[b]["outer"]):
                band = max(arcs[a]["band"], arcs[b]["band"])
                findings.append(Finding(
                    "DS-006", f"openings ({a}, {b})",
                    f"the arcs of '{a}' and '{b}' clear each other on the "
                    f"inscribed hulls but touch on the circumscribed hulls: "
                    f"the outcome falls inside the {band:.2f} mm polygon "
                    f"approximation band. Clearance is NOT proven and a "
                    f"collision is NOT asserted.", severity="INFO"))
                for k in (a, b):
                    if verdicts.get(k) == PASS:
                        verdicts[k] = UNKNOWN

    # ---- DS-007 arc vs furniture ----------------------------------------
    for did, arc in arcs.items():
        loc = resolved[did][2]
        hit, maybe = [], []
        for fid, poly in known_furn:
            if _poly_overlap(arc["inner"], poly):
                hit.append(fid)
            elif _poly_overlap(arc["outer"], poly):
                maybe.append(fid)
        if hit:
            findings.append(Finding(
                "DS-007", loc,
                f"the swing arc is obstructed by furniture {sorted(hit)}. "
                f"Proven on the INSCRIBED hull, so the clash is real and not "
                f"an artefact of the arc approximation. Footprints are "
                f"consumed from B3; static overlap itself remains owned by B3."))
            verdicts[did] = ERROR
        if maybe:
            findings.append(Finding(
                "DS-007", loc,
                f"furniture {sorted(maybe)} clears the inscribed hull but not "
                f"the circumscribed one: the result lies inside the "
                f"{arc['band']:.2f} mm arc approximation band. Clearance is "
                f"NOT proven; no collision is asserted.", severity="INFO"))
            if verdicts.get(did) == PASS:
                verdicts[did] = UNKNOWN
        if unresolved_furn:
            near = [f"'{fid}' ({why})" for fid, why in unresolved_furn]
            findings.append(Finding(
                "DS-007", loc,
                f"furniture with unresolved geometry exists: "
                f"{', '.join(sorted(near))}. Whether it fouls this arc cannot "
                f"be decided; this is NOT reported as clear.",
                severity="INFO"))
            if verdicts.get(did) == PASS:
                verdicts[did] = UNKNOWN

    # ---- DS-008 threshold obstruction (no swing needed) ------------------
    # ERROR requires all three: a resolvable aperture, a resolvable obstacle,
    # and a PROVEN geometric intersection between them. Proximity alone is
    # never sufficient. Furniture standing across the
    # aperture blocks it even when no swing is represented. This is NOT
    # FC-004 (which owns furniture inside the wall BODY) and NOT B4 (which
    # only judges DECLARED paths).
    for did, (geom, wall, loc) in resolved.items():
        p0, p1, u, n = geom
        blockers = []
        for fid, poly in known_furn:
            # STRICTLY an intersection test. No distance threshold, no
            # proximity margin, no design opinion: the obstacle must actually
            # cross the aperture segment or contain one of its ends. Furniture
            # merely NEAR the doorway is deliberately not reported here.
            crosses = any(
                _segments_cross(p0, p1, poly[k], poly[(k + 1) % len(poly)])
                for k in range(len(poly)))
            if crosses or _point_in_poly(p0, poly) or _point_in_poly(p1, poly):
                blockers.append(fid)
        if blockers:
            findings.append(Finding(
                "DS-008", loc,
                f"the doorway threshold is obstructed by {sorted(blockers)}: "
                f"the aperture itself is not clear, independently of any "
                f"swing."))
            verdicts[did] = ERROR

    # ---- DS-009 explicit verdict ----------------------------------------
    for did in sorted(verdicts):
        findings.append(Finding(
            "DS-009", f"openings ({did})",
            f"verdict: {verdicts[did]}.", severity="INFO"))

    return findings, verdicts


def validate_doors(data):
    findings, verdicts = check_doors(data)
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings, verdicts


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: validate_doors.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs, verdicts = validate_doors(payload)
    print("DOOR INTEGRITY:", "PASS" if ok else f"FAIL ({len(fs)} finding(s))")
    for f in fs:
        print(" ", f)
    sys.exit(0 if ok else 1)
