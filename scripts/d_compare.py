#!/usr/bin/env python3
"""
00.5-D — SEMANTIC COMPARISON

Compares an extracted output against the GA reference. It reports differences
and never repairs, never regenerates and never modifies either side.

EVALUATION ORDER — binding (CORRECTION-01)
  For every GA element that did not appear as a comparable output element:
    [1] extraction failed for a representation reason proven in the output
        (unsupported primitive / transform / malformed)   -> NOT_VERIFIABLE
    [2] covered by a valid declared omission                -> DECLARED_OMISSION
    [3] otherwise                                           -> MISSING (a real failure)

  Step [1] always precedes step [3]: "could not read it" is never rewritten
  as "it is not there" (CORRECTION-02).

POLYGON POINTS — PG-1..PG-7
  Compared in the order declared by the SEC. No cyclic rotation, no reverse
  normalisation, no reordering. A difference in order is recorded as a
  comparison difference WITHOUT claiming that a different starting point
  necessarily means different geometry in all contexts.

NUMERIC — parsed-value equality only. No tolerance, no rounding.
"""

NOT_VERIFIABLE = "NOT_VERIFIABLE"
DECLARED_OMISSION = "DECLARED_OMISSION"
MISSING = "MISSING"
EXTRA = "EXTRA"
DUPLICATE = "DUPLICATE"
MATCH = "MATCH"
DIFFERENT = "DIFFERENT"

# Fields that the current output format cannot carry (GAP-D-01). They are
# declared NOT_VERIFIABLE per field and never re-derived or substituted.
UNEXTRACTABLE_FIELDS = ("host_wall", "offset", "thickness", "units",
                        "provenance")


def values_equal(a, b):
    """Exact parsed-value equality. No tolerance of any kind."""
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return False
    if a != a or b != b:                       # NaN never equals anything
        return False
    if a in (float("inf"), float("-inf")) or b in (float("inf"),
                                                   float("-inf")):
        return False
    return float(a) == float(b)


def points_equal(pa, pb):
    """Ordered, element-wise comparison. Never reordered (PG-1..PG-4)."""
    if not isinstance(pa, list) or not isinstance(pb, list):
        return False, "one side is not a point list"
    if len(pa) != len(pb):
        return False, f"point count differs ({len(pa)} vs {len(pb)})"
    for i, (x, y) in enumerate(zip(pa, pb)):
        if not values_equal(x[0], y[0]) or not values_equal(x[1], y[1]):
            return False, (f"point {i} differs in the declared order: "
                           f"{x} vs {y}")
    return True, None


def _index_by_id(entries):
    index, duplicates = {}, []
    for e in entries:
        eid = e.get("id")
        if eid is None:
            continue
        if eid in index:
            duplicates.append(eid)
        else:
            index[eid] = e
    return index, duplicates


def _omission_covers(omissions, element_id):
    """A declared omission covers an element when it names its identifier."""
    if not element_id:
        return None
    for om in omissions or []:
        target = str(om.get("target", ""))
        message = str(om.get("message", ""))
        if element_id in target or element_id in message:
            return om
    return None


def compare(ga_ref, extracted):
    """Compare GA reference against extracted output. Reports only."""
    report = {
        "differences": [],
        "not_verifiable": [],
        "declared_omissions_applied": [],
        "matched_elements": [],
        "extra_elements": [],
        "duplicate_ids": [],
        "counterpart_index": {},
        "fields_checked": [],
        "fields_not_verifiable": [],
    }

    ga_index, ga_dupes = _index_by_id(ga_ref.get("elements", []))
    out_index, out_dupes = _index_by_id(extracted.get("elements", []))

    # Elements whose counterpart IS present but could not be read.
    unsupported_ids = {}
    for u in extracted.get("unsupported", []):
        if u.get("id"):
            unsupported_ids[u["id"]] = u

    for eid in ga_index:
        report["counterpart_index"][eid] = bool(
            eid in out_index or eid in unsupported_ids)

    if out_dupes:
        report["duplicate_ids"] = sorted(set(out_dupes))
        for d in sorted(set(out_dupes)):
            report["differences"].append({
                "element_id": d, "field": "identity", "kind": DUPLICATE,
                "ga_value": "unique identifier expected",
                "extracted_value": "identifier appears more than once"})
    if ga_dupes:
        report["duplicate_ids"] = sorted(
            set(report["duplicate_ids"]) | set(ga_dupes))

    # ---- every GA element, in the binding evaluation order ---------------
    for eid, ga_el in ga_index.items():
        if eid in out_index:
            out_el = out_index[eid]
            ok, detail = points_equal(ga_el.get("points"),
                                      out_el.get("points"))
            if ok:
                report["matched_elements"].append(eid)
            else:
                report["differences"].append({
                    "element_id": eid, "field": "coordinates",
                    "kind": DIFFERENT,
                    "ga_value": ga_el.get("points"),
                    "extracted_value": out_el.get("points"),
                    "detail": detail})
            continue

        # [1] representation failure proven in the output
        if eid in unsupported_ids:
            u = unsupported_ids[eid]
            report["not_verifiable"].append({
                "element_id": eid, "field": "coordinates",
                "counterpart_present": True,
                "reason": u.get("reason"),
                "note": "extraction failed for a representation reason; this "
                        "is NOT a missing element"})
            continue

        # [2] covered by a declared omission
        om = _omission_covers(ga_ref.get("declared_omissions"), eid)
        if om is not None:
            report["declared_omissions_applied"].append({
                "element_id": eid, "code": om.get("code"),
                "target": om.get("target")})
            continue

        # [3] a real missing element
        report["differences"].append({
            "element_id": eid, "field": "presence", "kind": MISSING,
            "ga_value": "element present in GA",
            "extracted_value": "no counterpart found in output",
            "counterpart_present": False})

    # ---- invented elements ------------------------------------------------
    for eid in out_index:
        if eid not in ga_index:
            report["extra_elements"].append(eid)
            report["differences"].append({
                "element_id": eid, "field": "presence", "kind": EXTRA,
                "ga_value": "no such element in GA",
                "extracted_value": "element present in output"})

    # ---- outline ----------------------------------------------------------
    ga_out, out_out = ga_ref.get("outline"), extracted.get("outline")
    if ga_out and out_out:
        ok, detail = points_equal(ga_out.get("points"), out_out.get("points"))
        if ok:
            report["matched_elements"].append("<outline>")
        else:
            report["differences"].append({
                "element_id": "<outline>", "field": "points",
                "kind": DIFFERENT, "ga_value": ga_out.get("points"),
                "extracted_value": out_out.get("points"), "detail": detail})
    elif ga_out and not out_out:
        report["not_verifiable"].append({
            "element_id": "<outline>", "field": "points",
            "counterpart_present": False,
            "reason": "no comparable outline primitive was extracted"})

    # ---- unsupported without an identifier -------------------------------
    for u in extracted.get("unsupported", []):
        if not u.get("id"):
            report["not_verifiable"].append({
                "element_id": None, "field": "element",
                "counterpart_present": True, "reason": u.get("reason")})

    report["fields_checked"] = ["element_identity", "coordinates",
                                "outline_points", "element_presence"]
    report["fields_not_verifiable"] = [
        {"field": f,
         "reason": "not carried by the output format (GAP-D-01); D does not "
                   "re-derive or substitute it"}
        for f in UNEXTRACTABLE_FIELDS]
    return report
