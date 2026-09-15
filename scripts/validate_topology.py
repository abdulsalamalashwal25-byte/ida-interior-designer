#!/usr/bin/env python3
"""
validate_topology.py — Phase 00.5-B2: Wall & Opening Topology Integrity

SCOPE (fixed by Gate 00.5-B1 approval):
  - wall polygon continuity
  - polygon closure when closure is required
  - impermissible gaps
  - self-intersections
  - duplicate / overlapping walls that affect topology
  - opening lies within the extent of its host wall
  - orphan openings and orphan walls

EXPLICITLY OUT OF SCOPE (do not add here):
  furniture overlap (B3) · clearance (B3) · circulation (B4) · door swing (B5)
  ergonomics · formulas (B6) · material validation · any design judgement.

DELEGATION: "every opening references an existing wall" is in the B2 brief but
is already owned by XR-001 in Phase 00.5-B1. It is NOT re-implemented here.
This engine skips openings whose host wall is missing and lets B1 reject them,
so a single defect never produces two rule codes.

All geometry is planar (x, y) in millimetres. Tolerance is explicit, never
guessed, and is a validation tolerance only — it is NOT a design decision.
"""

import math

# Tolerance for treating two coordinates as the same point.
# Declared, not inferred. Surveys are recorded in whole millimetres.
JOIN_TOLERANCE_MM = 1.0


class _Sentinel:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __bool__(self):
        # Guard against a caller accidentally treating UNSPECIFIED as false.
        raise TypeError(
            "closure policy is UNSPECIFIED and must not be coerced to a boolean; "
            "absence of a declared policy is not a declaration of 'false'.")


# AUTO  = caller did not pass a policy; read it from the master.
# UNSPECIFIED = no policy is declared anywhere. Distinct from False.
AUTO = _Sentinel("AUTO")
UNSPECIFIED = _Sentinel("UNSPECIFIED")


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


# ---------------------------------------------------------------------------
# Geometry helpers (pure functions, no design semantics)
# ---------------------------------------------------------------------------
def _pt(v):
    """Coerce a fact value to a 2D point, or None if not resolvable."""
    if not isinstance(v, (list, tuple)) or len(v) < 2:
        return None
    try:
        return (float(v[0]), float(v[1]))
    except (TypeError, ValueError):
        return None


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def same_point(a, b, tol=JOIN_TOLERANCE_MM):
    return dist(a, b) <= tol


def _orient(p, q, r):
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if abs(val) < 1e-9:
        return 0
    return 1 if val > 0 else -1


def _on_seg(p, q, r):
    return (min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9 and
            min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9)


def segments_properly_intersect(p1, q1, p2, q2):
    """True when two segments cross at a point interior to at least one of them.
    Shared endpoints (normal wall joints) are NOT intersections."""
    shared = sum(1 for a in (p1, q1) for b in (p2, q2) if same_point(a, b))
    if shared:
        return False
    o1, o2 = _orient(p1, q1, p2), _orient(p1, q1, q2)
    o3, o4 = _orient(p2, q2, p1), _orient(p2, q2, q1)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_seg(p1, p2, q1):
        return True
    if o2 == 0 and _on_seg(p1, q2, q1):
        return True
    if o3 == 0 and _on_seg(p2, p1, q2):
        return True
    if o4 == 0 and _on_seg(p2, q1, q2):
        return True
    return False


def collinear_overlap(p1, q1, p2, q2):
    """True when two segments are collinear AND share more than a point."""
    if _orient(p1, q1, p2) != 0 or _orient(p1, q1, q2) != 0:
        return False
    dx, dy = q1[0] - p1[0], q1[1] - p1[1]
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return False
    ux, uy = dx / L, dy / L

    def proj(pt):
        return (pt[0] - p1[0]) * ux + (pt[1] - p1[1]) * uy

    a0, a1 = 0.0, L
    b0, b1 = sorted((proj(p2), proj(q2)))
    lo, hi = max(a0, b0), min(a1, b1)
    return (hi - lo) > JOIN_TOLERANCE_MM


def wall_geometry(wall):
    """Return (start, end) or None when the geometry is not resolvable."""
    s = wall.get("start") or {}
    e = wall.get("end") or {}
    if not isinstance(s, dict) or not isinstance(e, dict):
        return None
    if s.get("status") == "U" or e.get("status") == "U":
        return None
    a, b = _pt(s.get("value")), _pt(e.get("value"))
    if a is None or b is None:
        return None
    return (a, b)


def _fact_value(node):
    if isinstance(node, dict) and "value" in node:
        return node.get("value")
    return None


# ---------------------------------------------------------------------------
# Topology rules
# ---------------------------------------------------------------------------
def check_topology(data, require_closure=AUTO):
    """Validate wall/opening topology.

    require_closure: AUTO        -> read meta.topology_policy (default)
                     True/False  -> explicit declared policy
                     UNSPECIFIED -> no policy declared
    A closed envelope is a PROJECT FACT, never an assumption by this engine.
    """
    findings = []
    walls = data.get("walls") or []
    openings = data.get("openings") or []

    # Closure policy resolution (approved at Gate 00.5-B2).
    # TRI-STATE, mirroring the presence tri-state of Phase 00.5-A:
    #   True         -> declared policy: closure required, WT-003 applicable
    #   False        -> declared policy: closure not required
    #   UNSPECIFIED  -> no policy declared. NOT the same as False.
    # The policy is READ ONLY from the declared field or the explicit argument.
    # It is NEVER inferred from the model's own geometry (Gate condition 6):
    # a model that happens to look closed does not thereby declare a policy.
    if require_closure is AUTO:
        policy = ((data.get("meta") or {}).get("topology_policy") or {})
        require_closure = policy.get("require_closed_envelope", UNSPECIFIED)

    # ---- geometry resolution -------------------------------------------
    geo = {}
    for i, w in enumerate(walls):
        wid = w.get("id")
        g = wall_geometry(w)
        loc = f"walls/{i} ({wid})"
        if g is None:
            findings.append(Finding(
                "WT-002", loc,
                "wall geometry is not resolvable (start/end is UNKNOWN or null). "
                "Topology cannot be verified and must not be assumed."))
            continue
        a, b = g
        if same_point(a, b):
            findings.append(Finding(
                "WT-001", loc,
                f"zero-length wall: start and end are the same point {a}."))
            continue
        geo[wid] = (a, b)

    # ---- WT-005 self-intersection --------------------------------------
    # DEFECT-B2-01 (found by adversarial test TN-006b): a collinear overlap also
    # satisfies the generic segment-intersection predicate, so one defect was
    # reported under two codes. Collinear overlap is a DUPLICATION defect owned
    # by WT-006; WT-005 is reserved for genuine transversal crossings.
    ids = list(geo.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a1, b1 = geo[ids[i]]
            a2, b2 = geo[ids[j]]
            if collinear_overlap(a1, b1, a2, b2):
                continue  # owned by WT-006
            if segments_properly_intersect(a1, b1, a2, b2):
                findings.append(Finding(
                    "WT-005", f"walls ({ids[i]}, {ids[j]})",
                    f"walls cross each other at a non-endpoint. The boundary "
                    f"self-intersects."))

    # ---- WT-006 duplicate / collinear overlap ---------------------------
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a1, b1 = geo[ids[i]]
            a2, b2 = geo[ids[j]]
            if (same_point(a1, a2) and same_point(b1, b2)) or \
               (same_point(a1, b2) and same_point(b1, a2)):
                findings.append(Finding(
                    "WT-006", f"walls ({ids[i]}, {ids[j]})",
                    "duplicate wall: both occupy the same segment."))
            elif collinear_overlap(a1, b1, a2, b2):
                findings.append(Finding(
                    "WT-006", f"walls ({ids[i]}, {ids[j]})",
                    "walls are collinear and overlap along a shared length."))

    # ---- endpoint connectivity ------------------------------------------
    if geo:
        endpoints = {}
        for wid, (a, b) in geo.items():
            for pt in (a, b):
                key = None
                for k in endpoints:
                    if same_point(k, pt):
                        key = k
                        break
                if key is None:
                    key = pt
                    endpoints[key] = []
                endpoints[key].append(wid)

        # WT-007 orphan wall: neither endpoint touches any other wall.
        # DEFECT-B2-02 (found by TN-006b): a wall lying ON another wall's body,
        # or crossing it, is geometrically CONNECTED even though its endpoints
        # meet nothing. Reporting it as "floating free" was factually wrong and
        # produced a collateral code on top of WT-006. Such walls are excluded
        # here and remain owned by WT-006 / WT-005.
        for wid, (a, b) in geo.items():
            touching = set()
            for pt in (a, b):
                for k, owners in endpoints.items():
                    if same_point(k, pt):
                        touching |= {o for o in owners if o != wid}
            body_contact = any(
                collinear_overlap(a, b, *geo[other])
                or segments_properly_intersect(a, b, *geo[other])
                for other in geo if other != wid)
            if not touching and not body_contact and len(geo) > 1:
                findings.append(Finding(
                    "WT-007", f"walls ({wid})",
                    "orphan wall: neither endpoint connects to any other wall."))

        # WT-004 / WT-003 : loose ends
        loose = [k for k, owners in endpoints.items() if len(owners) == 1]

        # WT-004 — fragmentation is INDEPENDENT of the closure policy.
        # DEFECT-B2-04 (found while wiring the policy field): the policy branch
        # previously swallowed this check, so an UNSPECIFIED policy silently
        # hid a genuinely broken chain. More than two loose ends means the
        # boundary is in disconnected pieces, whether or not it must close.
        if len(loose) > 2:
            findings.append(Finding(
                "WT-004", "walls",
                f"{len(loose)} unconnected wall endpoints — the chain is "
                f"fragmented at {[tuple(round(c, 1) for c in p) for p in loose[:4]]}."))

        # WT-003 — closure is judged ONLY against a declared policy.
        if require_closure is UNSPECIFIED and loose:
            findings.append(Finding(
                "WT-003", "walls",
                f"{len(loose)} unconnected endpoint(s) present, but no closure "
                f"policy is declared (meta.topology_policy.require_closed_envelope "
                f"is absent). UNSPECIFIED is not 'false' — declare the policy "
                f"before this can be judged.",
                severity="INFO"))
        elif require_closure is True and loose:
            findings.append(Finding(
                "WT-003", "walls",
                f"closed envelope is required but the wall chain is open: "
                f"{len(loose)} unconnected endpoint(s) at "
                f"{[tuple(round(c, 1) for c in p) for p in loose[:4]]}."))

    # ---- openings --------------------------------------------------------
    wall_by_id = {w.get("id"): w for w in walls}
    for i, op in enumerate(openings):
        oid = op.get("id")
        hw = op.get("host_wall")
        loc = f"openings/{i} ({oid})"

        # DELEGATED to XR-001 (B1): missing host wall. Skip, do not duplicate.
        if hw not in wall_by_id:
            continue

        if hw not in geo:
            # DEFECT-B2-03 (found by TN-002): the host wall's own defect is
            # already reported as WT-001/WT-002. Restating it here duplicated a
            # single root cause under a second code. WT-011 is therefore raised
            # as a NON-BLOCKING consequence note, not an independent error, so
            # the opening is still visibly unverifiable without double-counting.
            findings.append(Finding(
                "WT-011", loc,
                f"position not verifiable: host wall '{hw}' is itself invalid "
                f"(see WT-001/WT-002 for '{hw}').",
                severity="INFO"))
            continue

        a, b = geo[hw]
        wall_len = dist(a, b)
        offset = _fact_value(op.get("offset"))
        width = _fact_value(op.get("width"))

        if offset is None or width is None:
            # UNKNOWN offset/width is a data-completeness matter, not topology.
            continue
        try:
            offset = float(offset)
            width = float(width)
        except (TypeError, ValueError):
            continue

        if offset < 0:
            findings.append(Finding(
                "WT-009", loc,
                f"negative offset ({offset} mm): the opening starts before the "
                f"wall begins."))
            continue

        if width <= 0:
            findings.append(Finding(
                "WT-008", loc,
                f"non-positive width ({width} mm)."))
            continue

        if offset + width > wall_len + JOIN_TOLERANCE_MM:
            findings.append(Finding(
                "WT-008", loc,
                f"opening exceeds its host wall: offset {offset:.0f} + width "
                f"{width:.0f} = {offset + width:.0f} mm > wall length "
                f"{wall_len:.0f} mm on '{hw}'."))

    # ---- WT-010 overlapping openings on the same wall -------------------
    by_wall = {}
    for i, op in enumerate(openings):
        hw = op.get("host_wall")
        if hw not in geo:
            continue
        o = _fact_value(op.get("offset"))
        w = _fact_value(op.get("width"))
        if o is None or w is None:
            continue
        try:
            o, w = float(o), float(w)
        except (TypeError, ValueError):
            continue
        if o < 0 or w <= 0:
            continue
        by_wall.setdefault(hw, []).append((o, o + w, op.get("id"), i))

    for hw, spans in by_wall.items():
        spans.sort()
        for k in range(len(spans) - 1):
            s1, e1, id1, _ = spans[k]
            s2, e2, id2, idx2 = spans[k + 1]
            if s2 < e1 - JOIN_TOLERANCE_MM:
                findings.append(Finding(
                    "WT-010", f"openings ({id1}, {id2}) on {hw}",
                    f"openings overlap on the same wall: '{id1}' spans "
                    f"{s1:.0f}-{e1:.0f} mm, '{id2}' spans {s2:.0f}-{e2:.0f} mm."))

    return findings


def validate_topology(data, require_closure=AUTO):
    findings = check_topology(data, require_closure)
    return (len([f for f in findings if f.severity == "ERROR"]) == 0), findings


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: validate_topology.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_topology(payload)
    print("TOPOLOGY INTEGRITY:", "PASS" if ok else f"FAIL ({len(fs)} finding(s))")
    for f in fs:
        print(" ", f)
    sys.exit(0 if ok else 1)
