#!/usr/bin/env python3
"""
00.5-D — SEMANTIC EXTRACTION CONTRACT (SEC)

Reference (CLOSED): 00.5-D-ARCHITECTURE-AND-CLOSURE-REPORT.md
                    00.5-D-GATE1-IMPLEMENTATION-PLAN-AND-TEST-CONTRACT.md
                    00.5-D-GATE1-AMENDMENT-R02.md

WHAT THIS DOES
  Extracts geometry from an output artefact (SVG text) according to an
  explicit contract, so that "fidelity" is a measurement rather than an
  opinion.

WHAT THIS NEVER DOES
  It does not rebuild geometry, does not resolve transforms, does not infer
  a value that is not written in the artefact, and does not modify anything.

SUPPORTED PRIMITIVES  (measured: A and B emit only these)
  line    -> x1 y1 x2 y2
  polygon -> points="x,y x,y ..."

UNSUPPORTED — reported, never interpreted
  path · circle · rect · ellipse · polyline · text · use · and ANY element
  under a transform. A transform means the written coordinate is not the
  effective coordinate; computing it would be geometry reconstruction.

NUMERIC POLICY (DEC-D-03 as amended)
  V1 parses numeric SVG values using floating-point representation and then
  compares parsed values exactly. This is NOT a claim that floating point
  represents every possible decimal value with unlimited precision.
      6000 == 6000.0      exact parsed-value equality
      6000 != 5999.9      no hidden tolerance
      NaN / inf / -inf / overflow (1e309 -> inf)  =>  malformed
"""

import re

# --- extraction status vocabulary -----------------------------------------
OK = "OK"
MALFORMED = "MALFORMED"
UNSUPPORTED = "UNSUPPORTED"

SUPPORTED_PRIMITIVES = ("line", "polygon")
UNSUPPORTED_PRIMITIVES = ("path", "circle", "rect", "ellipse", "polyline",
                          "text", "use", "image", "tspan")

# A transform anywhere on the element or an ancestor group makes the written
# coordinates non-effective.
TRANSFORM_ATTR = "transform"

_TAG_RE = re.compile(r"<(?P<tag>[a-zA-Z][\w-]*)(?P<attrs>[^>]*?)/?>")
_ATTR_RE = re.compile(r'(?P<name>[\w:-]+)\s*=\s*"(?P<value>[^"]*)"')
_GROUP_OPEN_RE = re.compile(r"<g\b(?P<attrs>[^>]*)>")
_GROUP_CLOSE_RE = re.compile(r"</g\s*>")


def parse_number(text):
    """Parse one numeric token. Returns (value, status).

    Non-finite results are MALFORMED — including overflow such as '1e309',
    which Python parses to inf rather than raising.
    """
    if text is None:
        return None, MALFORMED
    s = str(text).strip()
    if not s:
        return None, MALFORMED
    try:
        value = float(s)
    except (ValueError, TypeError, OverflowError):
        return None, MALFORMED
    if value != value:                       # NaN
        return None, MALFORMED
    if value in (float("inf"), float("-inf")):
        return None, MALFORMED
    return value, OK


def _attrs_of(chunk):
    return {m.group("name"): m.group("value") for m in _ATTR_RE.finditer(chunk)}


def _transform_spans(svg_text):
    """Character ranges covered by any <g> carrying a transform attribute."""
    spans = []
    stack = []
    pos = 0
    while pos < len(svg_text):
        nxt_open = _GROUP_OPEN_RE.search(svg_text, pos)
        nxt_close = _GROUP_CLOSE_RE.search(svg_text, pos)
        if not nxt_open and not nxt_close:
            break
        if nxt_open and (not nxt_close or nxt_open.start() < nxt_close.start()):
            has_tf = TRANSFORM_ATTR in _attrs_of(nxt_open.group("attrs"))
            stack.append((nxt_open.end(), has_tf))
            pos = nxt_open.end()
        else:
            if stack:
                start, has_tf = stack.pop()
                if has_tf:
                    spans.append((start, nxt_close.start()))
            pos = nxt_close.end()
    return spans


def _in_transform(index, spans):
    return any(a <= index <= b for a, b in spans)


def extract(svg_text):
    """Extract geometry from SVG text according to the contract.

    Returns a dict with elements, outline, unsupported entries, extraction
    failures and the normalisations that were applied (always declared).
    """
    result = {
        "readable": False,
        "elements": [],            # supported, id-bearing, parsed
        "outline": None,
        "unsupported": [],         # id + reason, counterpart IS present
        "extraction_failures": [],
        "normalizations_applied": [
            "numeric tokens parsed to floating-point for comparison "
            "(representation only; no rounding, no tolerance)",
            "whitespace around coordinate separators ignored",
            "comments and presentation attributes excluded from comparison",
        ],
    }

    if not isinstance(svg_text, str) or "<svg" not in svg_text:
        result["extraction_failures"].append(
            {"reason": "artefact is not readable SVG text"})
        return result

    result["readable"] = True
    tf_spans = _transform_spans(svg_text)

    for m in _TAG_RE.finditer(svg_text):
        tag = m.group("tag")
        if tag in ("svg", "g", "defs", "title", "desc"):
            continue

        attrs = _attrs_of(m.group("attrs"))
        eid = attrs.get("data-id")
        under_tf = _in_transform(m.start(), tf_spans) or TRANSFORM_ATTR in attrs

        if tag not in SUPPORTED_PRIMITIVES:
            result["unsupported"].append({
                "id": eid, "primitive": tag, "counterpart_present": True,
                "reason": f"primitive '{tag}' is not supported by the SEC; "
                          f"its geometry is not interpreted"})
            continue

        if under_tf:
            # The written coordinate is not the effective one. Resolving it
            # would be geometry reconstruction, which D must never perform.
            result["unsupported"].append({
                "id": eid, "primitive": tag, "counterpart_present": True,
                "reason": "element is under a transform; the written "
                          "coordinates are not the effective coordinates and "
                          "D does not resolve them"})
            continue

        if tag == "line":
            coords, status, bad = [], OK, None
            for key in ("x1", "y1", "x2", "y2"):
                value, st = parse_number(attrs.get(key))
                if st != OK:
                    status, bad = MALFORMED, key
                    break
                coords.append(value)
            if status != OK:
                result["unsupported"].append({
                    "id": eid, "primitive": tag, "counterpart_present": True,
                    "reason": f"attribute '{bad}' is malformed "
                              f"({attrs.get(bad)!r}); not interpreted"})
                continue
            result["elements"].append({
                "id": eid, "primitive": "line",
                "points": [[coords[0], coords[1]], [coords[2], coords[3]]],
                "kind": attrs.get("data-kind"),
            })

        elif tag == "polygon":
            raw = attrs.get("points")
            if raw is None:
                result["unsupported"].append({
                    "id": eid, "primitive": tag, "counterpart_present": True,
                    "reason": "polygon has no points attribute"})
                continue
            pts, bad = [], None
            for token in raw.split():
                parts = token.split(",")
                if len(parts) != 2:
                    bad = token
                    break
                x, sx = parse_number(parts[0])
                y, sy = parse_number(parts[1])
                if sx != OK or sy != OK:
                    bad = token
                    break
                pts.append([x, y])
            if bad is not None:
                result["unsupported"].append({
                    "id": eid, "primitive": tag, "counterpart_present": True,
                    "reason": f"polygon point {bad!r} is malformed; "
                              f"not interpreted"})
                continue
            entry = {"id": eid, "primitive": "polygon", "points": pts}
            if eid is None:
                result["outline"] = entry
            else:
                result["elements"].append(entry)

    return result


def ga_reference(ga_artifact):
    """Project the GA artifact into the same comparable shape.

    This is a READ of what C3 already produced — not a re-assembly. No
    coordinate is computed here.
    """
    ref = {"elements": [], "outline": None, "declared_omissions": []}
    if not isinstance(ga_artifact, dict):
        return ref

    outline = ga_artifact.get("outline")
    if isinstance(outline, dict) and isinstance(outline.get("value"), list):
        ref["outline"] = {"id": None, "primitive": "polygon",
                          "points": [list(p[:2]) for p in outline["value"]]}

    for wall in ga_artifact.get("walls") or []:
        try:
            start = wall["start"]["value"]
            end = wall["end"]["value"]
        except (KeyError, TypeError):
            continue
        ref["elements"].append({
            "id": wall.get("id"), "primitive": "line",
            "points": [list(start[:2]), list(end[:2])], "kind": None})

    for op in ga_artifact.get("openings") or []:
        if "p0" not in op or "p1" not in op:
            continue
        ref["elements"].append({
            "id": op.get("id"), "primitive": "line",
            "points": [list(op["p0"][:2]), list(op["p1"][:2])],
            "kind": op.get("kind")})

    for entry in ga_artifact.get("not_represented") or []:
        ref["declared_omissions"].append(entry)

    return ref
