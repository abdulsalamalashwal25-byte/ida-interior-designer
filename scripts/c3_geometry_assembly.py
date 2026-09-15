#!/usr/bin/env python3
"""
00.5-C3 — GEOMETRY ASSEMBLY (GA)  —  Class A, Tier 0 + Tier 1

Reference: 00.5-C3-GEOMETRY-EMITTERS-ARCHITECTURE.md (CLOSED)
           00.5-C3-DECISION-RESOLUTION-ADDENDUM.md   (CLOSED)
Approved Output Contract (DEC-C3-03): Tier 0 + Tier 1
    Tier 0 : space/outline · walls · output identity/provenance ·
             explicit declaration of anything not represented
    Tier 1 : openings (doors / windows)
    OUT OF SCOPE: furniture · dimensions · room names / north / scale

WHAT GA IS
  A faithful transcriber. It copies values that already exist in the master
  into a format-neutral intermediate, and records WHERE each one came from.

WHAT GA IS NOT
  It is not a geometry engine. It computes no new geometry, infers no missing
  value, upgrades no status, and applies no default.

HARD RULES ENFORCED HERE
  * eligible status is {C, D} only — an APPROVED [A] is still NOT eligible
    (C1 FIX-01 / GAP-C-11).
  * every emitted value carries provenance (master path). No path -> no value.
  * no defaults: a missing rotation is NOT 0, absent is NOT centre.
  * numeric values are copied verbatim. C3 owns no quantization policy
    (DEC-C3-01); if a transform would be required, the caller abstains.
  * openings are placed using the host_wall + offset convention that B2/B5
    ALREADY own and enforce. C3 consumes that convention, it does not define
    it, and it re-validates nothing.
  * reads the master only. Writes nothing, anywhere.
"""

# Eligible statuses. [A] (even approved), [P], [U] are NOT eligible for class A.
ELIGIBLE_STATUSES = frozenset({"C", "D"})

# Sources that may not feed a class A output (mirrors C1's list; C3 does not
# re-derive eligibility, it refuses to transcribe what C1 would have blocked).
UNTRUSTED_SOURCES = frozenset({
    "AI_IMAGE", "EXTERNAL_STANDARD", "EXTERNAL_LIBRARY",
    "AGENT_PROPOSAL", "AGENT_ASSUMPTION", "NOT_PROVIDED",
})

TIER0 = "TIER-0"
TIER1 = "TIER-1"

# Reasons for not representing something. Declared, never silent.
NR_INELIGIBLE_STATUS = "NR-01"   # status not in {C, D}
NR_UNTRUSTED_SOURCE = "NR-02"    # source_type not trustworthy for class A
NR_MISSING_FIELD = "NR-03"       # required field absent from the master
NR_NON_NUMERIC = "NR-04"         # value cannot be serialised faithfully
NR_OUT_OF_CONTRACT = "NR-05"     # deliberately outside Tier 0 + Tier 1
NR_UNRESOLVED_HOST = "NR-06"     # opening's host wall not representable


class NotRepresented:
    """A declared omission. The contract requires these to be visible."""

    __slots__ = ("code", "target", "message")

    def __init__(self, code, target, message):
        self.code = code
        self.target = target
        self.message = message

    def as_dict(self):
        return {"code": self.code, "target": self.target,
                "message": self.message}


class Value:
    """A geometric value plus the master path it was transcribed from."""

    __slots__ = ("value", "path", "unit", "status")

    def __init__(self, value, path, unit, status):
        self.value = value
        self.path = path
        self.unit = unit
        self.status = status

    def as_dict(self):
        return {"value": self.value, "provenance": self.path,
                "unit": self.unit, "status": self.status}


class Assembly:
    """Format-neutral geometry, every value carrying provenance."""

    def __init__(self):
        self.outline = None          # Value | None
        self.walls = []              # list of dict
        self.openings = []           # list of dict
        self.not_represented = []    # list of NotRepresented
        self.tiers = (TIER0, TIER1)

    def omit(self, code, target, message):
        self.not_represented.append(NotRepresented(code, target, message))

    def as_dict(self):
        return {
            "contract_tiers": list(self.tiers),
            "outline": self.outline.as_dict() if self.outline else None,
            "walls": self.walls,
            "openings": self.openings,
            "not_represented": [n.as_dict() for n in self.not_represented],
        }


# --------------------------------------------------------------------------
# Fact reading — status and source are checked, never repaired
# --------------------------------------------------------------------------
def _is_fact(node):
    return isinstance(node, dict) and "status" in node


def read_fact(node, path, out):
    """Return a Value, or None plus a declared omission. Never a default."""
    if node is None:
        out.omit(NR_MISSING_FIELD, path, f"'{path}' is absent from the master; "
                 f"C3 does not supply a value for it.")
        return None
    if not _is_fact(node):
        out.omit(NR_MISSING_FIELD, path,
                 f"'{path}' is not a fact node (no status); not transcribed.")
        return None

    status = node.get("status")
    if status not in ELIGIBLE_STATUSES:
        out.omit(NR_INELIGIBLE_STATUS, path,
                 f"'{path}' has status [{status}], which is not eligible for a "
                 f"class A output. Eligible: [C], [D]. An approved [A] is "
                 f"still not eligible (GAP-C-11 open).")
        return None

    src = node.get("source_type")
    if src in UNTRUSTED_SOURCES:
        out.omit(NR_UNTRUSTED_SOURCE, path,
                 f"'{path}' derives from '{src}', which cannot feed a class A "
                 f"output.")
        return None

    if "value" not in node:
        out.omit(NR_MISSING_FIELD, path, f"'{path}' carries no value.")
        return None

    return Value(node["value"], path, node.get("unit"), status)


def _numeric_pair(seq):
    """True when seq is a usable [x, y] pair of real numbers."""
    return (isinstance(seq, (list, tuple)) and len(seq) >= 2
            and all(isinstance(c, (int, float)) and not isinstance(c, bool)
                    for c in seq[:2]))


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def assemble(master):
    """Build the Tier 0 + Tier 1 assembly. Read-only on `master`."""
    ga = Assembly()

    # ---- Tier 0: space outline -------------------------------------------
    space = master.get("space") or {}
    outline = read_fact(space.get("outline"), "space/outline", ga)
    if outline is not None:
        pts = outline.value
        if (isinstance(pts, list) and len(pts) >= 3
                and all(_numeric_pair(p) for p in pts)):
            ga.outline = outline
        else:
            ga.omit(NR_NON_NUMERIC, "space/outline",
                    "outline is not a list of at least three numeric [x, y] "
                    "points; C3 does not repair or complete it.")

    # ---- Tier 0: walls ----------------------------------------------------
    walls = master.get("walls") or []
    wall_index = {}
    for i, w in enumerate(walls):
        wid = w.get("id")
        base = f"walls/{i}"
        if not wid:
            ga.omit(NR_MISSING_FIELD, base, "wall has no id; not transcribed.")
            continue

        start = read_fact(w.get("start"), f"{base}/start", ga)
        end = read_fact(w.get("end"), f"{base}/end", ga)
        if start is None or end is None:
            ga.omit(NR_MISSING_FIELD, f"{base} ({wid})",
                    "wall omitted: start and/or end not eligible.")
            continue
        if not (_numeric_pair(start.value) and _numeric_pair(end.value)):
            ga.omit(NR_NON_NUMERIC, f"{base} ({wid})",
                    "wall endpoints are not numeric [x, y]; not transcribed.")
            continue

        # thickness is transcribed only if eligible; it is never assumed.
        th_node = w.get("thickness")
        thickness = None
        if th_node is not None:
            t = read_fact(th_node, f"{base}/thickness", ga)
            if t is not None and isinstance(t.value, (int, float)) \
                    and not isinstance(t.value, bool):
                thickness = t

        rec = {
            "id": wid,
            "start": start.as_dict(),
            "end": end.as_dict(),
            "thickness": thickness.as_dict() if thickness else None,
            "tier": TIER0,
        }
        ga.walls.append(rec)
        wall_index[wid] = (start.value, end.value)

    # ---- Tier 1: openings -------------------------------------------------
    for i, op in enumerate(master.get("openings") or []):
        oid = op.get("id")
        base = f"openings/{i}"
        if not oid:
            ga.omit(NR_MISSING_FIELD, base, "opening has no id.")
            continue

        host = op.get("host_wall")
        if host not in wall_index:
            ga.omit(NR_UNRESOLVED_HOST, f"{base} ({oid})",
                    f"host wall '{host}' is not among the transcribed walls; "
                    f"the opening cannot be placed without inventing a host.")
            continue

        offset = read_fact(op.get("offset"), f"{base}/offset", ga)
        width = read_fact(op.get("width"), f"{base}/width", ga)
        if offset is None or width is None:
            ga.omit(NR_MISSING_FIELD, f"{base} ({oid})",
                    "opening omitted: offset and/or width not eligible.")
            continue
        if not all(isinstance(v.value, (int, float)) and
                   not isinstance(v.value, bool) for v in (offset, width)):
            ga.omit(NR_NON_NUMERIC, f"{base} ({oid})",
                    "offset/width are not numeric; not transcribed.")
            continue

        a, b = wall_index[host]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            # A degenerate wall is B2's subject matter, not C3's. C3 simply
            # cannot place an opening on it, and says so.
            ga.omit(NR_UNRESOLVED_HOST, f"{base} ({oid})",
                    f"host wall '{host}' has zero length, so a position along "
                    f"it is not defined. C3 reports this; judging the wall "
                    f"itself belongs to B2.")
            continue

        # Convention owned and enforced by B2/B5: offset runs from the wall's
        # start point along the wall vector. C3 consumes it; it defines nothing.
        ux, uy = dx / length, dy / length
        p0 = (a[0] + ux * offset.value, a[1] + uy * offset.value)
        p1 = (a[0] + ux * (offset.value + width.value),
              a[1] + uy * (offset.value + width.value))

        ga.openings.append({
            "id": oid,
            "kind": op.get("kind"),
            "host_wall": host,
            "p0": list(p0),
            "p1": list(p1),
            "offset": offset.as_dict(),
            "width": width.as_dict(),
            "placement_convention": "host_wall + offset from wall start "
                                    "(owned by B2/B5; consumed here)",
            "provenance": [offset.path, width.path,
                           f"walls[id={host}]/start", f"walls[id={host}]/end"],
            "tier": TIER1,
        })

    # ---- declared out-of-contract content (Tier 2/3/4) --------------------
    if master.get("furniture"):
        ga.omit(NR_OUT_OF_CONTRACT, "furniture[]",
                f"{len(master['furniture'])} furniture item(s) exist in the "
                f"master but Tier 2 is outside the approved first contract.")
    if (master.get("space") or {}).get("orientation_north") is not None:
        ga.omit(NR_OUT_OF_CONTRACT, "space/orientation_north",
                "north indicator is Tier 4, outside the approved contract.")
    ga.omit(NR_OUT_OF_CONTRACT, "dimensions",
            "written dimensions are Tier 3 and are not produced: generating "
            "them could introduce a number absent from the master.")
    ga.omit(NR_OUT_OF_CONTRACT, "room names / scale",
            "Tier 4 annotations are outside the approved contract.")

    return ga
