#!/usr/bin/env python3
"""
validate_furniture.py — Phase 00.5-B3: Furniture Geometry & Clearance Integrity

SCOPE (fixed by Gate 00.5-B2 approval):
  1. furniture <-> furniture overlap
  2. furniture <-> wall / fixed-element overlap
  3. basic clearance, ONLY where a clearance value is DEFINED and SOURCED
  4. unresolvable [U]/null geometry is never invented and never treated as valid
  5. illegitimate duplicate / co-located pieces
  6. links B3 needs, WITHOUT re-implementing B1's XR rules

EXPLICITLY OUT OF SCOPE:
  circulation (B4) · door swing (B5) · formulas (B6) · aesthetics ·
  ergonomics as a design judgement · furniture re-layout proposals ·
  any modification of the Design Master.

CLEARANCE POLICY (Gate condition, verbatim):
  No clearance number originates from this engine. A clearance is enforced only
  when the master declares it with a trustworthy status. Otherwise it is
  surfaced as UNKNOWN / GAP and NEVER converted into a geometric rule.

DELEGATION (no rule is duplicated):
  - existence of material_ref / zone_ref .............. XR-003 / XR-002 (B1)
  - wall topology and opening placement ............... WT-* (B2)
  - provenance, status tags, locking .................. Layer A
"""

import math

# --------------------------------------------------------------------------
# GEOMETRY SEMANTICS (Gate 00.5-B3 R02)
# GAP-B3-01 and GAP-B3-02 are closed by DECLARED DATA, not by convention.
#   - position_reference states what the coordinate means. Absent => UNKNOWN.
#   - rotation states the angle in degrees. Absent => UNKNOWN, never 0.
# Neither is ever inferred. An unknown value that MATTERS blocks the geometric
# judgement instead of being guessed.
# --------------------------------------------------------------------------
VALID_DATUMS = ("CENTER", "CORNER_MIN", "CORNER_MAX")

OVERLAP_TOLERANCE_MM = 1.0          # touching is not overlapping
ANGLE_TOLERANCE_DEG = 1e-6

# Statuses whose value may be used for a geometric judgement.
GEOMETRY_USABLE_STATUSES = {"C", "D"}

# A clearance is enforceable only from a trustworthy, sourced status.
ENFORCEABLE_STATUSES = {"C", "D"}
TRUSTED_SOURCES = {"CLIENT_INPUT", "USER_APPROVAL", "DERIVED_CALC"}


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __str__(self):
        return f"[{self.severity}] {self.rule} @ {self.location}: {self.message}"

    def __repr__(self):
        return f"<{self.rule} @ {self.location}>"


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _fact_value(node):
    if isinstance(node, dict) and "value" in node:
        return node.get("value")
    return None


def _is_unresolved(node):
    """True when a fact carries no usable value."""
    if not isinstance(node, dict):
        return True
    if node.get("status") == "U":
        return True
    return node.get("value") is None


def _xy(v):
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    try:
        return (float(v[0]), float(v[1]))
    except (TypeError, ValueError):
        return None


def _wd(v):
    """Footprint width/depth from a dims value [w, d, h]."""
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    try:
        return (float(v[0]), float(v[1]))
    except (TypeError, ValueError):
        return None


def footprint(cx, cy, w, d, datum, rotation_deg):
    """Return the footprint as 4 polygon corners, honouring datum AND rotation.

    The datum fixes the local origin; the rotation is applied about the
    position point itself, so both declared values genuinely change the
    geometry that every downstream check consumes.

    Both arguments are MANDATORY. There is deliberately no default: a default
    would silently reintroduce the CENTER / 0-degree assumption that this
    phase exists to eliminate.
    """
    if datum == "CENTER":
        hw, hd = w / 2.0, d / 2.0
        local = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    elif datum == "CORNER_MIN":
        local = [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    elif datum == "CORNER_MAX":
        local = [(-w, -d), (0.0, -d), (0.0, 0.0), (-w, 0.0)]
    else:
        raise ValueError(f"unknown datum {datum!r}")

    if abs(rotation_deg) < ANGLE_TOLERANCE_DEG:
        return [(cx + lx, cy + ly) for lx, ly in local]

    a = math.radians(rotation_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in local]


def _axes(poly):
    """Outward edge normals of a convex polygon (for SAT)."""
    out = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        L = math.hypot(ex, ey)
        if L < 1e-12:
            continue
        out.append((-ey / L, ex / L))
    return out


def _project(poly, axis):
    vals = [p[0] * axis[0] + p[1] * axis[1] for p in poly]
    return min(vals), max(vals)


def rect_overlap(p1, p2, tol=OVERLAP_TOLERANCE_MM):
    """Convex-polygon overlap by the Separating Axis Theorem.

    Works for ANY rotation. Overlapping AREA, not mere contact: a separation of
    at least -tol on any axis counts as separated.
    """
    for axis in _axes(p1) + _axes(p2):
        min1, max1 = _project(p1, axis)
        min2, max2 = _project(p2, axis)
        if min1 >= max2 - tol or min2 >= max1 - tol:
            return False
    return True


def _seg_seg_dist(a, b, c, d):
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    def pt_seg(p, q, r):
        qx, qy = r[0] - q[0], r[1] - q[1]
        L2 = qx * qx + qy * qy
        if L2 < 1e-12:
            return math.hypot(p[0] - q[0], p[1] - q[1])
        t = clamp(((p[0] - q[0]) * qx + (p[1] - q[1]) * qy) / L2, 0.0, 1.0)
        return math.hypot(p[0] - (q[0] + t * qx), p[1] - (q[1] + t * qy))

    return min(pt_seg(a, c, d), pt_seg(b, c, d), pt_seg(c, a, b), pt_seg(d, a, b))


def rect_gap(p1, p2):
    """Shortest distance between two convex polygons (0 if touching)."""
    if rect_overlap(p1, p2, tol=0.0):
        return 0.0
    best = float("inf")
    n1, n2 = len(p1), len(p2)
    for i in range(n1):
        for j in range(n2):
            best = min(best, _seg_seg_dist(
                p1[i], p1[(i + 1) % n1], p2[j], p2[(j + 1) % n2]))
    return best


def unknown_rotation_envelope(cx, cy, w, d, datum):
    """Worst-case reach of a piece whose rotation is UNKNOWN.

    With the datum known but the angle unknown, the piece may occupy ANY
    orientation about its position point. The set of all those footprints is
    bounded by a circle centred on the position point whose radius is the
    farthest footprint corner over the full sweep. Nothing outside that circle
    can be affected by the unknown angle, so rotation is immaterial there.

    This never invents an orientation; it only bounds where the ignorance can
    possibly matter.
    """
    probe = footprint(cx, cy, w, d, datum, 0.0)
    return max(math.hypot(px - cx, py - cy) for px, py in probe)


def guaranteed_rotation_disc(cx, cy, w, d, datum):
    """Radius of the region occupied by the piece in EVERY possible orientation.

    A point at distance r from the pivot is covered whatever the angle only if
    the whole circle of radius r stays inside the footprint. That radius is the
    pivot's distance to the nearest footprint edge, and it is 0 when the pivot
    lies outside the footprint (e.g. some CORNER datums), which correctly means
    "nothing can be proven".

    Anything reaching inside this disc collides under EVERY rotation, so the
    conflict is PROVEN without knowing the angle. Outside it, a conflict may be
    possible but is NOT proven.
    """
    poly = footprint(cx, cy, w, d, datum, 0.0)
    if not _point_in_poly((cx, cy), poly):
        return 0.0
    n = len(poly)
    return min(_seg_seg_dist(poly[i], poly[(i + 1) % n], (cx, cy), (cx, cy))
               for i in range(n))


def _dist_to_poly(poly, cx, cy):
    """Distance from a point to a polygon; 0 when the point is inside it."""
    if _point_in_poly((cx, cy), poly):
        return 0.0
    n = len(poly)
    return min(_seg_seg_dist(poly[i], poly[(i + 1) % n], (cx, cy), (cx, cy))
               for i in range(n))


def _poly_circle_conflict(poly, cx, cy, radius, tol=OVERLAP_TOLERANCE_MM):
    """True when a polygon reaches inside a disc of the given radius."""
    if radius <= 0.0:
        return False
    return _dist_to_poly(poly, cx, cy) < radius - tol


def _segments_cross(p1, q1, p2, q2):
    """True when two segments genuinely intersect (including touching)."""
    def orient(p, q, r):
        v = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if abs(v) < 1e-9:
            return 0
        return 1 if v > 0 else -1

    def on_seg(p, q, r):
        return (min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9 and
                min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9)

    o1, o2 = orient(p1, q1, p2), orient(p1, q1, q2)
    o3, o4 = orient(p2, q2, p1), orient(p2, q2, q1)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_seg(p1, p2, q1):
        return True
    if o2 == 0 and on_seg(p1, q2, q1):
        return True
    if o3 == 0 and on_seg(p2, p1, q2):
        return True
    if o4 == 0 and on_seg(p2, q1, q2):
        return True
    return False


def _point_in_poly(pt, poly):
    """Ray-casting containment test for a convex or simple polygon."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < xin:
                inside = not inside
    return inside


def seg_rect_overlap(a, b, half_t, poly, tol=OVERLAP_TOLERANCE_MM):
    """Does a wall (segment a-b with half-thickness) overlap a footprint polygon?

    The wall body is the segment expanded by half its thickness, so the test is
    the polygon-to-segment distance against that half-thickness.
    """
    # DEFECT-B3-01 (found by FN-004 after the R02 geometry rewrite): the
    # edge-distance test alone MISSES a wall whose centre-line passes straight
    # through the footprint. _seg_seg_dist measures distance between edge
    # segments and returns a large value for a through-going wall whose nearest
    # footprint edges are far away; it does NOT detect crossing. Both
    # containment and true segment crossing must be tested explicitly.
    n = len(poly)
    if _point_in_poly(a, poly) or _point_in_poly(b, poly):
        return True
    for i in range(n):
        if _segments_cross(poly[i], poly[(i + 1) % n], a, b):
            return True
    best = float("inf")
    for i in range(n):
        best = min(best, _seg_seg_dist(poly[i], poly[(i + 1) % n], a, b))
    return best < (half_t - tol)


# --------------------------------------------------------------------------
# B3 rules
# --------------------------------------------------------------------------
def check_furniture(data):
    findings = []
    furniture = data.get("furniture") or []
    walls = data.get("walls") or []
    columns = data.get("columns") or []

    # ---- resolve furniture geometry ------------------------------------
    resolved = {}
    unknown_rot = {}   # pieces parked because their rotation is UNKNOWN
    for i, f in enumerate(furniture):
        fid = f.get("id")
        loc = f"furniture/{i} ({fid})"
        pos_node, dim_node = f.get("position"), f.get("dims")

        if _is_unresolved(pos_node) or _is_unresolved(dim_node):
            findings.append(Finding(
                "FC-001", loc,
                "geometry is not resolvable (position or dims is UNKNOWN/null). "
                "Dimensions must not be inferred; the piece cannot be checked."))
            continue

        c = _xy(_fact_value(pos_node))
        wd = _wd(_fact_value(dim_node))
        if c is None or wd is None:
            findings.append(Finding(
                "FC-001", loc,
                "position or dims is malformed and cannot be interpreted as "
                "geometry. No values are assumed."))
            continue

        w, d = wd
        if w <= 0 or d <= 0:
            findings.append(Finding(
                "FC-002", loc,
                f"non-positive footprint ({w} x {d} mm)."))
            continue

        # ---- FC-009: position datum (GAP-B3-01 closed by declared data) ----
        # Absence is UNKNOWN. It is NOT read as CENTER.
        pr_node = f.get("position_reference")
        if pr_node is None:
            findings.append(Finding(
                "FC-009", loc,
                "position_reference is absent, so the meaning of the position "
                "coordinate is UNKNOWN. It is NOT assumed to be CENTER, and no "
                "geometric judgement is made for this piece."))
            continue
        if _is_unresolved(pr_node) or pr_node.get("status") not in GEOMETRY_USABLE_STATUSES:
            findings.append(Finding(
                "FC-009", loc,
                f"position_reference is [{pr_node.get('status')}] and not usable "
                f"for geometry. The datum must be confirmed before overlap or "
                f"clearance can be judged."))
            continue
        datum = _fact_value(pr_node)
        if datum not in VALID_DATUMS:
            findings.append(Finding(
                "FC-009", loc,
                f"position_reference '{datum}' is not a declared datum "
                f"{VALID_DATUMS}."))
            continue

        # ---- FC-010: rotation (GAP-B3-02 closed by declared data) ---------
        # Absence is UNKNOWN. It is NOT read as 0.
        # An UNKNOWN rotation is NOT resolved to 0. It is deferred: the piece is
        # parked with its worst-case envelope, and FC-010 fires later ONLY if
        # that ignorance actually touches a judgement (materiality test).
        rot_node = f.get("rotation")
        rot, rot_reason = None, None
        if rot_node is None:
            rot_reason = ("rotation is absent, so the orientation is UNKNOWN. "
                          "It is NOT assumed to be 0 degrees.")
        elif _is_unresolved(rot_node) or rot_node.get("status") not in GEOMETRY_USABLE_STATUSES:
            rot_reason = (f"rotation is [{rot_node.get('status')}] and not usable "
                          f"for geometry. The orientation is UNKNOWN.")
        else:
            try:
                rot = float(_fact_value(rot_node))
            except (TypeError, ValueError):
                rot_reason = "rotation value is malformed, so orientation is UNKNOWN."

        if rot is None:
            unknown_rot[fid] = {
                "idx": i, "centre": c, "wd": (w, d), "datum": datum,
                "radius": unknown_rotation_envelope(c[0], c[1], w, d, datum),
                "inner": guaranteed_rotation_disc(c[0], c[1], w, d, datum),
                "reason": rot_reason, "obj": f}
            continue

        resolved[fid] = {"idx": i, "rect": footprint(c[0], c[1], w, d, datum, rot),
                         "centre": c, "wd": (w, d), "datum": datum,
                         "rotation": rot, "obj": f}

    # ---- FC-010 materiality: PROVEN vs POSSIBLE vs NONE -------------------
    # An UNKNOWN angle is classified by two concentric discs about the pivot:
    #   inner (guaranteed) - occupied under EVERY orientation  -> PROVEN  -> ERROR
    #   outer (envelope)   - reachable under SOME orientation  -> POSSIBLE -> INFO
    #   beyond outer       - unreachable at any angle          -> NONE
    # "Inside the envelope" is NEVER read as "collision proven". Where the two
    # discs disagree the conservative verdict is UNCERTAIN, not ERROR.
    for fid, u in unknown_rot.items():
        loc = f"furniture/{u['idx']} ({fid})"
        cx, cy = u["centre"]
        r_out = u["radius"]
        r_in = u["inner"]
        proven, possible = [], []

        def _classify(dist, label, slack=0.0):
            # dist = clearest separation between the obstacle and the pivot.
            if r_in > 0.0 and dist < r_in + slack - OVERLAP_TOLERANCE_MM:
                proven.append(label)
            elif dist < r_out + slack - OVERLAP_TOLERANCE_MM:
                possible.append(label)

        for oid, o in resolved.items():
            _classify(_dist_to_poly(o["rect"], cx, cy), f"furniture '{oid}'")
        for uid, o in unknown_rot.items():
            if uid == fid:
                continue
            sep = math.hypot(o["centre"][0] - cx, o["centre"][1] - cy)
            # The neighbour's own angle is unknown too, so only its guaranteed
            # disc can contribute to a proof; its envelope contributes doubt.
            if r_in > 0.0 and o["inner"] > 0.0 and sep < r_in + o["inner"] - OVERLAP_TOLERANCE_MM:
                proven.append(f"furniture '{uid}' (also unknown angle)")
            elif sep < r_out + o["radius"] - OVERLAP_TOLERANCE_MM:
                possible.append(f"furniture '{uid}' (also unknown angle)")
        for w_ in walls:
            a, b = _xy(_fact_value(w_.get("start"))), _xy(_fact_value(w_.get("end")))
            th = _fact_value(w_.get("thickness"))
            if a is None or b is None or not isinstance(th, (int, float)):
                continue
            _classify(_seg_seg_dist(a, b, (cx, cy), (cx, cy)),
                      f"wall '{w_.get('id')}'", slack=th / 2.0)
        for col in columns:
            cc = _xy(_fact_value(col.get("position")))
            cd = _wd(_fact_value(col.get("dims")))
            if cc is None or cd is None:
                continue
            _classify(_dist_to_poly(
                footprint(cc[0], cc[1], cd[0], cd[1], "CENTER", 0.0), cx, cy),
                f"column '{col.get('id')}'")

        cl = u["obj"].get("clearance")
        if (cl is not None and not _is_unresolved(cl)
                and cl.get("status") in ENFORCEABLE_STATUSES
                and cl.get("source_type") in TRUSTED_SOURCES):
            # A clearance distance cannot be measured from an unknown footprint,
            # but an unmeasurable rule is uncertainty, not a proven breach.
            possible.append("its own declared clearance rule")

        if proven:
            findings.append(Finding(
                "FC-010", loc,
                f"{u['reason']} PROVEN CONFLICT: {', '.join(sorted(set(proven)))} "
                f"lies within the disc this piece occupies at EVERY possible "
                f"orientation (r={r_in:.0f} mm), so the clash holds whatever the "
                f"angle turns out to be. Confirm the angle and the position."))
        elif possible:
            findings.append(Finding(
                "FC-010", loc,
                f"{u['reason']} POSSIBLE BUT UNPROVEN: {', '.join(sorted(set(possible)))} "
                f"lies inside the worst-case envelope (r={r_out:.0f} mm) but "
                f"outside the always-occupied disc (r={r_in:.0f} mm). Some angles "
                f"clash and others do not; this is NOT asserted as a collision. "
                f"Recorded as unresolved geometry pending the angle.",
                severity="INFO"))
        else:
            findings.append(Finding(
                "FC-010", loc,
                f"{u['reason']} NO POSSIBLE CONFLICT: nothing lies within the "
                f"worst-case envelope (r={r_out:.0f} mm), so no rotation could "
                f"cause a clash. Recorded as an open item; NOT treated as 0 "
                f"degrees.",
                severity="INFO"))

    ids = list(resolved.keys())

    # ---- FC-006 illegitimate duplicates ---------------------------------
    # Two DISTINCT pieces occupying the same footprint. Owned here; such a pair
    # is excluded from FC-003 so one defect never yields two codes.
    duplicate_pairs = set()
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            A, B = resolved[ids[i]], resolved[ids[j]]
            if (abs(A["centre"][0] - B["centre"][0]) <= OVERLAP_TOLERANCE_MM and
                    abs(A["centre"][1] - B["centre"][1]) <= OVERLAP_TOLERANCE_MM and
                    abs(A["wd"][0] - B["wd"][0]) <= OVERLAP_TOLERANCE_MM and
                    abs(A["wd"][1] - B["wd"][1]) <= OVERLAP_TOLERANCE_MM and
                    A["datum"] == B["datum"] and
                    abs(A["rotation"] - B["rotation"]) <= ANGLE_TOLERANCE_DEG):
                duplicate_pairs.add((ids[i], ids[j]))
                findings.append(Finding(
                    "FC-006", f"furniture ({ids[i]}, {ids[j]})",
                    f"duplicate pieces: '{ids[i]}' and '{ids[j]}' share the same "
                    f"position and footprint. Either one is redundant or a "
                    f"coordinate is wrong."))

    # ---- FC-003 furniture / furniture overlap ---------------------------
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if (ids[i], ids[j]) in duplicate_pairs:
                continue  # owned by FC-006
            A, B = resolved[ids[i]], resolved[ids[j]]
            if rect_overlap(A["rect"], B["rect"]):
                findings.append(Finding(
                    "FC-003", f"furniture ({ids[i]}, {ids[j]})",
                    f"footprints overlap: '{ids[i]}' and '{ids[j]}' occupy the "
                    f"same floor area."))

    # ---- FC-004 furniture / wall overlap --------------------------------
    for wl in walls:
        wid = wl.get("id")
        s, e = wl.get("start"), wl.get("end")
        if _is_unresolved(s) or _is_unresolved(e):
            continue  # wall geometry defects are owned by WT-002 (B2)
        a, b = _xy(_fact_value(s)), _xy(_fact_value(e))
        if a is None or b is None or (abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9):
            continue  # WT-001 / WT-002 territory
        t_node = wl.get("thickness")
        if _is_unresolved(t_node):
            continue
        try:
            half_t = float(_fact_value(t_node)) / 2.0
        except (TypeError, ValueError):
            continue
        for fid in ids:
            if seg_rect_overlap(a, b, half_t, resolved[fid]["rect"]):
                findings.append(Finding(
                    "FC-004", f"furniture ({fid}) / wall ({wid})",
                    f"'{fid}' overlaps the body of wall '{wid}' "
                    f"(wall thickness {half_t * 2:.0f} mm)."))

    # ---- FC-005 furniture / column overlap ------------------------------
    for col in columns:
        cid = col.get("id")
        p_node, d_node = col.get("position"), col.get("dims")
        if _is_unresolved(p_node) or _is_unresolved(d_node):
            continue
        c = _xy(_fact_value(p_node))
        cd = _wd(_fact_value(d_node))
        if c is None or cd is None:
            continue
        # A column has no datum/rotation field in the schema; its position is
        # its centre by definition of the column object, not by inference.
        crect = footprint(c[0], c[1], cd[0], cd[1], "CENTER", 0.0)
        for fid in ids:
            if rect_overlap(resolved[fid]["rect"], crect):
                findings.append(Finding(
                    "FC-005", f"furniture ({fid}) / column ({cid})",
                    f"'{fid}' overlaps fixed column '{cid}'."))

    # ---- clearance -------------------------------------------------------
    for fid in ids:
        f = resolved[fid]["obj"]
        loc = f"furniture/{resolved[fid]['idx']} ({fid})"
        cl = f.get("clearance")
        if cl is None:
            continue  # nothing declared: nothing to enforce, nothing to invent

        # FC-008: declared but NOT enforceable. Never upgraded into a rule.
        if _is_unresolved(cl):
            findings.append(Finding(
                "FC-008", loc,
                "clearance is declared but UNKNOWN. It is recorded as an open "
                "item and is NOT converted into a geometric rule.",
                severity="INFO"))
            continue
        status = cl.get("status")
        src = cl.get("source_type")
        if status not in ENFORCEABLE_STATUSES or src not in TRUSTED_SOURCES:
            findings.append(Finding(
                "FC-008", loc,
                f"clearance is [{status}] from '{src}' — not an approved value. "
                f"GAP recorded; no clearance rule is applied. Approve it first.",
                severity="INFO"))
            continue
        try:
            req = float(_fact_value(cl))
        except (TypeError, ValueError):
            findings.append(Finding(
                "FC-008", loc,
                "clearance value is malformed; no rule applied.",
                severity="INFO"))
            continue
        if req <= 0:
            continue

        # FC-007: enforce ONLY this declared, approved number.
        for other in ids:
            if other == fid:
                continue
            gap = rect_gap(resolved[fid]["rect"], resolved[other]["rect"])
            if rect_overlap(resolved[fid]["rect"], resolved[other]["rect"]):
                continue  # already reported as FC-003/FC-006
            if gap < req - OVERLAP_TOLERANCE_MM:
                findings.append(Finding(
                    "FC-007", f"furniture ({fid}) / ({other})",
                    f"declared clearance {req:.0f} mm not met: only "
                    f"{gap:.0f} mm to '{other}'."))

    return findings


def validate_furniture(data):
    findings = check_furniture(data)
    return (len([f for f in findings if f.severity == "ERROR"]) == 0), findings


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: validate_furniture.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_furniture(payload)
    print("FURNITURE INTEGRITY:", "PASS" if ok else f"FAIL ({len(fs)} finding(s))")
    for f in fs:
        print(" ", f)
    sys.exit(0 if ok else 1)
