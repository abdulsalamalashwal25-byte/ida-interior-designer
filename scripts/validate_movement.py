#!/usr/bin/env python3
"""Phase 00.5-B4 — Movement & Circulation Integrity.

SCOPE (owned here):
  1. circulation path geometry is resolvable and non-degenerate
  2. path endpoints resolve to real elements and actually touch them
  3. a KNOWN obstacle intersecting a path  -> BLOCKED
  4. an UNKNOWN obstacle that may intersect -> UNKNOWN (never silently passable)
  5. declared minimum width, enforced ONLY when trustworthy
  6. an explicit verdict per path: PASSABLE / BLOCKED / UNKNOWN
  7. circulation must be DECLARED (present / not-present / unknown), never
     silently absent

NOT OWNED HERE (consumed, never re-implemented):
  - existence of any referenced id                 -> B1  (XR-*)
  - wall / opening topology                        -> B2  (WT-*)
  - furniture-vs-furniture / wall / column overlap -> B3  (FC-003/004/005)
  - status & source legitimacy                     -> A
  - door swing arcs                                -> B5  (NOT started here)

This engine contains NO corridor width, NO ergonomic figure and NO standard.
Every enforced number must come from the master, declared and trusted.
It DETECTS, CLASSIFIES and REPORTS. It never moves, widens or rearranges
anything, and it never expresses a design preference.
"""

import math

# Reuse B3's geometry so furniture footprints are resolved in exactly one place.
from validate_furniture import (  # noqa: F401
    footprint,
    guaranteed_rotation_disc,
    unknown_rotation_envelope,
    rect_overlap,
    seg_rect_overlap,
    _dist_to_poly,
    _seg_seg_dist,
    _segments_cross,
    _point_in_poly,
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
# Constants — tolerances only. Deliberately NO width/clearance figures.
# --------------------------------------------------------------------------
JOIN_TOLERANCE_MM = 1.0      # two points count as the same point below this
ENDPOINT_TOLERANCE_MM = 1.0  # path end must actually touch its target
ENFORCEABLE_STATUSES = {"C", "D"}

PASSABLE = "PASSABLE"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"


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
# Helpers
# --------------------------------------------------------------------------
def _polyline(value):
    """Return a list of >=2 valid [x, y] points, or None if not resolvable."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    pts = []
    for p in value:
        q = _xy(p)
        if q is None:
            return None
        pts.append(q)
    return pts


def _segment_list(value):
    """Parse an explicit segment list: [[[x1,y1],[x2,y2]], ...].

    Returns a list of (a, b) tuples, or None if not resolvable. Unlike a
    polyline, this shape CAN express a gap between consecutive segments.
    """
    if not isinstance(value, (list, tuple)) or len(value) < 1:
        return None
    segs = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return None
        a, b = _xy(item[0]), _xy(item[1])
        if a is None or b is None:
            return None
        segs.append((a, b))
    return segs


def _segments(pts):
    return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def _corridor_half_width(path_obj):
    """Declared minimum width, ONLY if trustworthy. Returns (value, reason).

    value is None whenever no rule may be enforced. No number is invented.
    """
    node = path_obj.get("required_width")
    if node is None:
        return None, None
    if _is_unresolved(node):
        return None, ("required_width is declared but UNKNOWN. It is recorded as "
                      "an open item and is NOT converted into a geometric rule.")
    status = node.get("status")
    src = node.get("source_type")
    if status not in ENFORCEABLE_STATUSES or src not in TRUSTED_SOURCES:
        return None, (f"required_width is [{status}] from '{src}' — not an "
                      f"approved value. GAP recorded; no width rule is applied.")
    try:
        val = float(_fact_value(node))
    except (TypeError, ValueError):
        return None, "required_width is malformed; no rule applied."
    if val <= 0:
        return None, "required_width is not positive; no rule applied."
    return val, None


def _resolve_element_geometry(eid, index):
    """Geometry of a referenced element, for endpoint-attachment testing.

    Returns (kind, geometry, resolved_bool). Never invents a position.
    """
    entry = index.get(eid)
    if entry is None:
        return None, None, False
    coll, obj = entry

    if coll == "walls":
        a = _xy(_fact_value(obj.get("start")))
        b = _xy(_fact_value(obj.get("end")))
        if a is None or b is None:
            return "wall", None, False
        return "wall", (a, b), True

    if coll == "openings":
        # Openings are located by host_wall + offset along that wall (the
        # convention B2 already enforces). No absolute position is invented.
        host = obj.get("host_wall")
        off = _fact_value(obj.get("offset"))
        wid = _fact_value(obj.get("width"))
        hw = index.get(host) if host else None
        if hw is None or not isinstance(off, (int, float)):
            return "opening", None, False
        wobj = hw[1]
        a = _xy(_fact_value(wobj.get("start")))
        b = _xy(_fact_value(wobj.get("end")))
        if a is None or b is None:
            return "opening", None, False
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L <= 0:
            return "opening", None, False
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        half = (float(wid) / 2.0) if isinstance(wid, (int, float)) else 0.0
        mid = off + half
        return "opening", (a[0] + ux * mid, a[1] + uy * mid), True

    if coll == "zones":
        b = _fact_value(obj.get("boundary"))
        poly = _polyline(b) if b is not None else None
        if poly is None:
            return "zone", None, False
        return "zone", poly, True

    if coll == "furniture":
        return "furniture", None, False

    return coll, None, False


# --------------------------------------------------------------------------
# Obstacle collection — consumes B3 geometry, owns no collision rule
# --------------------------------------------------------------------------
def _collect_obstacles(data):
    """Split obstacles into KNOWN geometry and UNRESOLVED geometry.

    Furniture footprints are built with B3's own footprint(), honouring the
    declared datum and rotation. A piece whose datum or rotation is UNKNOWN is
    NOT given an assumed orientation: it goes to the unresolved list, where it
    can only produce UNKNOWN, never BLOCKED and never silent passage.
    """
    known, unresolved = [], []

    for i, f in enumerate(data.get("furniture") or []):
        fid = f.get("id") or f"furniture/{i}"
        pos_node, dim_node = f.get("position"), f.get("dims")
        if _is_unresolved(pos_node) or _is_unresolved(dim_node):
            unresolved.append((fid, "furniture geometry is UNKNOWN", None))
            continue
        c = _xy(_fact_value(pos_node))
        wd = _wd(_fact_value(dim_node))
        if c is None or wd is None or wd[0] <= 0 or wd[1] <= 0:
            unresolved.append((fid, "furniture geometry is malformed", None))
            continue

        pr = f.get("position_reference")
        rot_node = f.get("rotation")
        datum = _fact_value(pr) if isinstance(pr, dict) else None
        datum_ok = (isinstance(pr, dict) and not _is_unresolved(pr)
                    and pr.get("status") in GEOMETRY_USABLE_STATUSES
                    and datum in VALID_DATUMS)
        if not datum_ok:
            unresolved.append(
                (fid, "position_reference is UNKNOWN, so the footprint location "
                      "cannot be resolved (it is NOT assumed to be CENTER)",
                 (c, wd, None)))
            continue

        rot_ok = (isinstance(rot_node, dict) and not _is_unresolved(rot_node)
                  and rot_node.get("status") in GEOMETRY_USABLE_STATUSES)
        rot = None
        if rot_ok:
            try:
                rot = float(_fact_value(rot_node))
            except (TypeError, ValueError):
                rot_ok = False
        if not rot_ok:
            # Unknown angle: keep the worst-case reach, claim nothing about it.
            radius = unknown_rotation_envelope(c[0], c[1], wd[0], wd[1], datum)
            unresolved.append(
                (fid, "rotation is UNKNOWN, so the swept footprint cannot be "
                      "resolved (it is NOT assumed to be 0 degrees)",
                 (c, wd, radius)))
            continue

        known.append((fid, "furniture",
                      footprint(c[0], c[1], wd[0], wd[1], datum, rot)))

    for i, col in enumerate(data.get("columns") or []):
        cid = col.get("id") or f"columns/{i}"
        c = _xy(_fact_value(col.get("position")))
        wd = _wd(_fact_value(col.get("dims")))
        if c is None or wd is None:
            unresolved.append((cid, "column geometry is UNKNOWN", None))
            continue
        known.append((cid, "column",
                      footprint(c[0], c[1], wd[0], wd[1], "CENTER", 0.0)))

    return known, unresolved


# --------------------------------------------------------------------------
# Main check
# --------------------------------------------------------------------------
def check_movement(data, index=None):
    findings = []
    paths = data.get("circulation") or []

    # ---- MV-011: silence about circulation is no longer acceptable --------
    # An empty/absent collection is ambiguous: "confirmed none" or "never
    # asked"? The ratified mechanism for that ambiguity is the presence
    # register (Gate 00.5-A R02 section 5), so B4 mandates a declaration here
    # rather than inventing a parallel device. No path is ever invented; the
    # project is simply required to SAY which case applies.
    if not paths:
        pnode = (data.get("presence_register") or {}).get("circulation")
        if pnode is None:
            findings.append(Finding(
                "MV-011", "presence_register",
                "no circulation path is declared and presence_register."
                "circulation is absent. An empty collection is ambiguous: it "
                "may mean 'the client confirmed there is no defined route' or "
                "'nobody has surveyed the movement yet'. Declare PRESENT, "
                "NOT_PRESENT or UNKNOWN. No route is assumed either way."))
            return findings, {}
        presence = pnode.get("presence")
        if presence == "NOT_PRESENT":
            findings.append(Finding(
                "MV-011", "presence_register",
                "circulation is confirmed NOT_PRESENT; no movement judgement "
                "is issued.", severity="INFO"))
            return findings, {}
        if presence == "UNKNOWN" or _is_unresolved(pnode):
            findings.append(Finding(
                "MV-011", "presence_register",
                "circulation presence is UNKNOWN. Movement cannot be judged "
                "and the space is NOT reported as circulation-clear.",
                severity="INFO"))
            return findings, {}
        # presence says PRESENT, yet nothing is declared -> a real gap.
        findings.append(Finding(
            "MV-011", "presence_register",
            "presence_register declares circulation PRESENT, but no path is "
            "declared in the master. The declared routes are missing, not "
            "empty."))
        return findings, {}

    if index is None:
        try:
            from validate_refs import build_index
            index, _ = build_index(data)
        except Exception:
            index = {}

    known_obs, unresolved_obs = _collect_obstacles(data)
    walls = data.get("walls") or []
    verdicts = {}

    for i, path in enumerate(paths):
        pid = path.get("id") or f"circulation/{i}"
        loc = f"circulation/{i} ({pid})"
        blocked_by, uncertain = [], []

        # ---- MV-001 path geometry resolvable ----------------------------
        cl_node = path.get("centerline")
        sg_node = path.get("segments")
        seg_mode = sg_node is not None
        geom_node = sg_node if seg_mode else cl_node
        label = "segments" if seg_mode else "centerline"

        if geom_node is None or _is_unresolved(geom_node):
            findings.append(Finding(
                "MV-001", loc,
                f"{label} is missing or UNKNOWN. The path geometry is not "
                f"invented; no movement judgement is issued."))
            verdicts[pid] = UNKNOWN
            continue

        if seg_mode:
            segs = _segment_list(_fact_value(sg_node))
            if segs is None:
                findings.append(Finding(
                    "MV-001", loc,
                    "segments is malformed: each entry must be two valid "
                    "[x, y] points. No geometry is assumed."))
                verdicts[pid] = UNKNOWN
                continue
            pts = [segs[0][0], segs[-1][1]]
        else:
            pts = _polyline(_fact_value(cl_node))
            if pts is None:
                findings.append(Finding(
                    "MV-001", loc,
                    "centerline is malformed or has fewer than two valid "
                    "points. No geometry is assumed."))
                verdicts[pid] = UNKNOWN
                continue
            segs = _segments(pts)

        # ---- MV-002 degenerate segments ----------------------------------
        degenerate = [j for j, (a, b) in enumerate(segs)
                      if math.hypot(b[0] - a[0], b[1] - a[1]) <= JOIN_TOLERANCE_MM]
        if degenerate:
            findings.append(Finding(
                "MV-002", loc,
                f"segment(s) {degenerate} have zero length; the path geometry is "
                f"not usable."))
            verdicts[pid] = UNKNOWN
            continue

        # ---- MV-003 internal discontinuity (segments representation) ----
        # Reinstated once the master gained an explicit segment list. A gap
        # between consecutive segments is now REPRESENTABLE, so the rule can
        # genuinely fire instead of being dead code.
        if seg_mode:
            breaks = []
            for j in range(len(segs) - 1):
                gap = math.hypot(segs[j][1][0] - segs[j + 1][0][0],
                                 segs[j][1][1] - segs[j + 1][0][1])
                if gap > JOIN_TOLERANCE_MM:
                    breaks.append((j, gap))
            if breaks:
                worst = max(breaks, key=lambda t: t[1])
                findings.append(Finding(
                    "MV-003", loc,
                    f"path is discontinuous: {len(breaks)} gap(s) between "
                    f"consecutive segments, the largest being {worst[1]:.0f} mm "
                    f"after segment {worst[0]}. The route is not traversable as "
                    f"declared, and the gap is NOT closed by assumption."))
                verdicts[pid] = BLOCKED
                continue

        # ---- MV-004 / MV-005 endpoints resolve AND attach ----------------
        endpoint_unknown = False
        for role, key, pt in (("start", "start_ref", pts[0]),
                              ("end", "end_ref", pts[-1])):
            node = path.get(key)
            if node is None or _is_unresolved(node):
                findings.append(Finding(
                    "MV-004", loc,
                    f"{key} is missing or UNKNOWN. A path with an unresolved "
                    f"{role} is not assumed to connect to anything."))
                endpoint_unknown = True
                continue
            target = _fact_value(node)
            kind, geom, ok = _resolve_element_geometry(target, index)
            if kind is None:
                # Existence itself is B1's rule; here it means this path's
                # endpoint cannot be used, which is B4's concern.
                findings.append(Finding(
                    "MV-004", loc,
                    f"{key} points at '{target}', which does not resolve to a "
                    f"known element. Endpoint attachment cannot be verified "
                    f"(element existence itself is owned by B1/XR)."))
                endpoint_unknown = True
                continue
            if not ok:
                findings.append(Finding(
                    "MV-004", loc,
                    f"{key} resolves to '{target}' but its geometry is UNKNOWN, "
                    f"so attachment cannot be verified. Not assumed connected.",
                    severity="INFO"))
                endpoint_unknown = True
                continue

            if kind == "wall":
                dist = _seg_seg_dist(geom[0], geom[1], pt, pt)
            elif kind == "opening":
                dist = math.hypot(pt[0] - geom[0], pt[1] - geom[1])
            elif kind == "zone":
                dist = 0.0 if _point_in_poly(pt, geom) else _dist_to_poly(geom, pt[0], pt[1])
            else:
                dist = None

            if dist is not None and dist > ENDPOINT_TOLERANCE_MM:
                findings.append(Finding(
                    "MV-005", loc,
                    f"the {role} of the path is {dist:.0f} mm away from "
                    f"'{target}', so it does not actually meet it. The path is "
                    f"not treated as connected."))
                verdicts[pid] = BLOCKED
                blocked_by.append(f"detached {role}")

        if pid in verdicts and verdicts[pid] == BLOCKED:
            continue
        if endpoint_unknown:
            verdicts[pid] = UNKNOWN
            continue

        # ---- width rule (declared only) ----------------------------------
        req_w, width_gap_reason = _corridor_half_width(path)
        if width_gap_reason:
            findings.append(Finding(
                "MV-009", loc,
                f"{width_gap_reason} Approve a sourced minimum width before any "
                f"width rule can be enforced.",
                severity="INFO"))

        # ---- MV-006 known obstacles on the path --------------------------
        for oid, kind, poly in known_obs:
            for (a, b) in segs:
                if seg_rect_overlap(a, b, 0.0, poly):
                    blocked_by.append(f"{kind} '{oid}'")
                    break
        if blocked_by:
            findings.append(Finding(
                "MV-006", loc,
                f"path is obstructed by {', '.join(sorted(set(blocked_by)))}. "
                f"The obstacle geometry is consumed from the master (furniture "
                f"overlap rules themselves remain owned by B3)."))

        # ---- MV-007 unresolved obstacles that MIGHT block ----------------
        for oid, reason, approx in unresolved_obs:
            if approx is None:
                uncertain.append(f"'{oid}' ({reason})")
                continue
            c, wd, radius = approx
            if radius is None:
                radius = 0.5 * math.hypot(wd[0], wd[1])
            near = any(_seg_seg_dist(a, b, c, c) < radius - OVERLAP_TOLERANCE_MM
                       for (a, b) in segs)
            if near:
                uncertain.append(f"'{oid}' ({reason})")
        if uncertain:
            findings.append(Finding(
                "MV-007", loc,
                f"obstacle geometry is unresolved near this path: "
                f"{', '.join(sorted(set(uncertain)))}. Passability cannot be "
                f"decided; this is NOT reported as clear and NOT asserted as "
                f"blocked.",
                severity="INFO"))

        # ---- MV-008 enforce declared width against known obstacles -------
        if req_w is not None:
            half = req_w / 2.0
            narrow = []
            for (a, b) in segs:
                for oid, kind, poly in known_obs:
                    gap = min(_seg_seg_dist(a, b, poly[k], poly[(k + 1) % len(poly)])
                              for k in range(len(poly)))
                    if 0.0 < gap < half - OVERLAP_TOLERANCE_MM:
                        narrow.append((oid, gap))
                for w_ in walls:
                    wa = _xy(_fact_value(w_.get("start")))
                    wb = _xy(_fact_value(w_.get("end")))
                    th = _fact_value(w_.get("thickness"))
                    if wa is None or wb is None or not isinstance(th, (int, float)):
                        continue
                    gap = _seg_seg_dist(a, b, wa, wb) - th / 2.0
                    if 0.0 < gap < half - OVERLAP_TOLERANCE_MM:
                        narrow.append((w_.get("id"), gap))
            if narrow:
                worst = min(narrow, key=lambda t: t[1])
                findings.append(Finding(
                    "MV-008", loc,
                    f"declared minimum width {req_w:.0f} mm is not met: only "
                    f"{worst[1] * 2:.0f} mm clear at '{worst[0]}'. This enforces "
                    f"the value declared in the master, not a standard."))
                blocked_by.append(f"width at '{worst[0]}'")

        # ---- MV-010 explicit verdict -------------------------------------
        if blocked_by:
            verdicts[pid] = BLOCKED
        elif uncertain:
            verdicts[pid] = UNKNOWN
        else:
            verdicts[pid] = PASSABLE

    for pid, v in verdicts.items():
        findings.append(Finding(
            "MV-010", f"circulation ({pid})",
            f"verdict: {v}.",
            severity="INFO"))

    return findings, verdicts


def validate_movement(data, index=None):
    findings, verdicts = check_movement(data, index)
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings, verdicts


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: validate_movement.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs, verdicts = validate_movement(payload)
    print("MOVEMENT INTEGRITY:", "PASS" if ok else f"FAIL ({len(fs)} finding(s))")
    for f in fs:
        print(" ", f)
    sys.exit(0 if ok else 1)
