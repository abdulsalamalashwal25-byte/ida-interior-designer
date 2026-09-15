#!/usr/bin/env python3
"""
00.5-C4 — EXTERNAL DERIVED QUANTITY SCHEDULE  (Q-01 … Q-04)

Reference: 00.5-C4-QUANTITY-SCHEDULES-ARCHITECTURE.md  (analysis accepted)
           00.5-C4-DECISION-RESOLUTION-ADDENDUM.md     (CLOSED)

OWN-C4-01 (binding)
  The schedule is an EXTERNAL DERIVED RESULT. It lives outside
  project_master.json. No computed quantity is ever written back into the
  master, neither as a [D] nor in any other representation. The direction is
  strictly one-way:  master -> C4 -> external schedule -> D.

WHAT C4 OWNS
  Computing Q-01 Count, Q-02 Individual Wall Length, Q-03 Total Wall Length,
  Q-04 Opening Area from values DECLARED in the master.

WHAT C4 DOES NOT OWN
  * integrity of declared [D] values            -> B6 (consumed as-is)
  * the blocking / unknown verdict              -> B7 (consumed as-is)
  * whether generation is permitted             -> C1 (consumed as-is)
  * whether the schedule matches the master     -> D
  * outputs[] and governance                    -> E
  * the Output Manifest                         -> C6
  C4 issues no `correct`, `matches_master`, `approved` or `fidelity_ok`.

MEASUREMENT SOURCE
  The master only. C3 output (SVG) is a derived representation and is never
  measured (AS-C4-05).

DIMENSIONAL ALGEBRA
  Borrowed from B6, not reinvented: mm+-mm -> mm, mm*mm -> mm2,
  mm2/mm -> mm, sqrt(mm2) -> mm. Nothing is ever converted.

'A calculated number is not automatically Class A.' Every item must satisfy
A-Q1..A-Q8 together.
"""

import math

# --- eligibility -----------------------------------------------------------
ELIGIBLE_STATUSES = frozenset({"C", "D"})

UNTRUSTED_SOURCES = frozenset({
    "AI_IMAGE", "EXTERNAL_STANDARD", "EXTERNAL_LIBRARY",
    "AGENT_PROPOSAL", "AGENT_ASSUMPTION", "NOT_PROVIDED",
})

# --- exclusion codes (approved set) ---------------------------------------
EX_MISSING = "EX-MISSING"
EX_NOT_FACT = "EX-NOT-FACT"
EX_STATUS = "EX-STATUS"
EX_UNCOMPUTABLE = "EX-UNCOMPUTABLE"
EX_SOURCE = "EX-SOURCE"
EX_UNIT = "EX-UNIT"

# --- completeness ----------------------------------------------------------
COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
ABSTAIN = "ABSTAIN"

# --- units (schema enum; no new unit is introduced) ------------------------
U_MM = "mm"
U_MM2 = "mm2"
U_COUNT = "count"

# Countable master collections. outputs[] is EXCLUDED BY OWNERSHIP: it
# belongs to E, and counting it would be an ownership breach (AS-C4-17).
COUNTABLE_COLLECTIONS = ("walls", "openings", "columns", "zones",
                         "circulation", "furniture", "materials",
                         "lighting", "cameras")
OWNERSHIP_EXCLUDED_COLLECTIONS = ("outputs",)


class Exclusion:
    """A declared exclusion. Silent exclusion is forbidden."""

    __slots__ = ("code", "element_id", "path", "reason")

    def __init__(self, code, element_id, path, reason):
        self.code = code
        self.element_id = element_id
        self.path = path
        self.reason = reason

    def as_dict(self):
        return {"code": self.code, "element_id": self.element_id,
                "path": self.path, "reason": self.reason}


class QuantityItem:
    """One computed quantity with full provenance."""

    __slots__ = ("quantity_id", "element_id", "value", "unit",
                 "source_paths", "inputs", "operation", "basis")

    def __init__(self, quantity_id, element_id, value, unit, source_paths,
                 inputs, operation, basis):
        self.quantity_id = quantity_id
        self.element_id = element_id
        self.value = value
        self.unit = unit
        self.source_paths = source_paths
        self.inputs = inputs
        self.operation = operation
        self.basis = basis

    def as_dict(self):
        return {"quantity_id": self.quantity_id, "element_id": self.element_id,
                "value": self.value, "unit": self.unit,
                "source_paths": self.source_paths, "inputs": self.inputs,
                "operation": self.operation, "basis": self.basis}


# --------------------------------------------------------------------------
# Eligibility gate — per INPUT, not per table
# --------------------------------------------------------------------------
def check_eligibility(node, path, element_id, derived_verdicts=None):
    """Return (Value|None, Exclusion|None). Never repairs, never defaults."""
    if node is None:
        return None, Exclusion(EX_MISSING, element_id, path,
                               "field is absent from the master; C4 supplies "
                               "no value for it.")
    if not isinstance(node, dict) or "status" not in node:
        return None, Exclusion(EX_NOT_FACT, element_id, path,
                               "node is not a fact (no status); not usable.")

    status = node.get("status")
    if status not in ELIGIBLE_STATUSES:
        return None, Exclusion(
            EX_STATUS, element_id, path,
            f"status [{status}] is not eligible. Only [C] and [D] qualify; "
            f"an APPROVED [A] is still not eligible.")

    # [D] must carry a VERIFIED verdict. The verdict is B6/B7 property: it is
    # consumed, never recomputed and never re-derived here.
    if status == "D":
        verdict = (derived_verdicts or {}).get(path)
        if verdict != "VERIFIED":
            return None, Exclusion(
                EX_UNCOMPUTABLE, element_id, path,
                f"derived value verdict is '{verdict or 'NOT_PROVIDED'}' "
                f"(owner: B6/B7). C4 consumes this verdict and does not "
                f"re-derive it.")

    src = node.get("source_type")
    if src in UNTRUSTED_SOURCES:
        return None, Exclusion(EX_SOURCE, element_id, path,
                               f"source_type '{src}' is not trustworthy for a "
                               f"class A quantity.")

    if "value" not in node:
        return None, Exclusion(EX_MISSING, element_id, path,
                               "fact carries no value.")
    return node, None


def _require_unit(node, path, element_id, expected):
    """Unit must be declared and match. No implicit conversion (U-1)."""
    unit = node.get("unit")
    if unit is None:
        return Exclusion(EX_UNIT, element_id, path,
                         "unit is not declared; C4 does not assume one.")
    if unit != expected:
        return Exclusion(
            EX_UNIT, element_id, path,
            f"unit '{unit}' does not match the required '{expected}'. "
            f"C4 never converts (B6: nothing is ever converted).")
    return None


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) \
        and v == v and v not in (float("inf"), float("-inf"))


def _coord_pair(v):
    return isinstance(v, (list, tuple)) and len(v) >= 2 \
        and all(_is_number(c) for c in v[:2])


# --------------------------------------------------------------------------
# Q-01 — Count
# --------------------------------------------------------------------------
def q01_count(master, collections=None):
    """Count unique declared element ids per collection.

    outputs[] is never counted: it is owned by E (AS-C4-17).

    `collections` is resolved at CALL time, not bound as a default at import
    time. A default argument would freeze the tuple when the module is first
    loaded, which both hides later configuration and silently masks mutation
    testing (the AS-C2-16 lesson, in its default-argument form).
    """
    if collections is None:
        collections = COUNTABLE_COLLECTIONS
    items, exclusions = [], []
    for coll in collections:
        if coll in OWNERSHIP_EXCLUDED_COLLECTIONS:
            continue
        entries = master.get(coll)
        if entries is None:
            continue
        seen, dupes = [], []
        for i, e in enumerate(entries):
            eid = e.get("id") if isinstance(e, dict) else None
            if not eid:
                exclusions.append(Exclusion(
                    EX_MISSING, None, f"{coll}/{i}/id",
                    "element has no id, so it cannot be counted against an "
                    "identifier."))
                continue
            if eid in seen:
                dupes.append(eid)
                continue
            seen.append(eid)
        total = len(entries)
        items.append(QuantityItem(
            "Q-01", f"{coll}[]", len(seen), U_COUNT,
            [f"{coll}/{i}/id" for i in range(total)],
            [{"collection": coll, "declared_entries": total}],
            "count of unique declared ids",
            COMPLETE if len(seen) == total else f"{len(seen)} of {total}"))
        if dupes:
            for d in dupes:
                exclusions.append(Exclusion(
                    EX_MISSING, d, f"{coll}[id={d}]",
                    "duplicate id counted once; duplication is reported, not "
                    "silently merged."))
    return items, exclusions


# --------------------------------------------------------------------------
# Q-02 — Individual Wall Length
# --------------------------------------------------------------------------
def q02_wall_length(master, derived_verdicts=None):
    """Centre-line length between two declared points. sqrt(mm2) -> mm."""
    items, exclusions = [], []
    for i, w in enumerate(master.get("walls") or []):
        wid = w.get("id")
        base = f"walls/{i}"
        if not wid:
            exclusions.append(Exclusion(EX_MISSING, None, f"{base}/id",
                                        "wall has no id."))
            continue

        s_node, s_ex = check_eligibility(w.get("start"), f"{base}/start", wid,
                                         derived_verdicts)
        if s_ex:
            exclusions.append(s_ex)
            continue
        e_node, e_ex = check_eligibility(w.get("end"), f"{base}/end", wid,
                                         derived_verdicts)
        if e_ex:
            exclusions.append(e_ex)
            continue

        for node, path in ((s_node, f"{base}/start"), (e_node, f"{base}/end")):
            u = _require_unit(node, path, wid, U_MM)
            if u:
                exclusions.append(u)
                break
        else:
            a, b = s_node["value"], e_node["value"]
            if not (_coord_pair(a) and _coord_pair(b)):
                exclusions.append(Exclusion(
                    EX_MISSING, wid, base,
                    "endpoints are not numeric [x, y] pairs."))
                continue
            dx, dy = b[0] - a[0], b[1] - a[1]
            # mm*mm -> mm2 ; sqrt(mm2) -> mm   (B6 algebra, borrowed)
            length = math.sqrt(dx * dx + dy * dy)
            items.append(QuantityItem(
                "Q-02", wid, length, U_MM,
                [f"{base}/start", f"{base}/end"],
                [{"start": list(a[:2]), "end": list(b[:2]), "unit": U_MM}],
                "sqrt(dx^2 + dy^2) — centre line only; excludes thickness "
                "and joints",
                COMPLETE))
    return items, exclusions


# --------------------------------------------------------------------------
# Q-03 — Total Wall Length
# --------------------------------------------------------------------------
def q03_total_wall_length(master, derived_verdicts=None):
    """Sum of eligible Q-02 values. Always governed by the PARTIAL contract."""
    items, exclusions = q02_wall_length(master, derived_verdicts)
    declared = len(master.get("walls") or [])
    eligible = len(items)

    if eligible == 0:
        return None, exclusions, ABSTAIN

    total = 0.0
    for it in items:
        total += it.value          # mm + mm -> mm
    basis = f"{eligible} of {declared}"
    completeness = COMPLETE if eligible == declared else PARTIAL

    item = QuantityItem(
        "Q-03", "walls[]", total, U_MM,
        [p for it in items for p in it.source_paths],
        [{"element_id": it.element_id, "value": it.value, "unit": it.unit}
         for it in items],
        "sum of eligible Q-02 lengths", basis)
    return item, exclusions, completeness


# --------------------------------------------------------------------------
# Q-04 — Opening Area
# --------------------------------------------------------------------------
def q04_opening_area(master, derived_verdicts=None):
    """width x height -> mm2. A non-eligible height is excluded, never assumed."""
    items, exclusions = [], []
    for i, op in enumerate(master.get("openings") or []):
        oid = op.get("id")
        base = f"openings/{i}"
        if not oid:
            exclusions.append(Exclusion(EX_MISSING, None, f"{base}/id",
                                        "opening has no id."))
            continue

        w_node, w_ex = check_eligibility(op.get("width"), f"{base}/width", oid,
                                         derived_verdicts)
        if w_ex:
            exclusions.append(w_ex)
            continue
        h_node, h_ex = check_eligibility(op.get("height"), f"{base}/height",
                                         oid, derived_verdicts)
        if h_ex:
            exclusions.append(h_ex)
            continue

        bad = False
        for node, path in ((w_node, f"{base}/width"),
                           (h_node, f"{base}/height")):
            u = _require_unit(node, path, oid, U_MM)
            if u:
                exclusions.append(u)
                bad = True
                break
        if bad:
            continue

        wv, hv = w_node["value"], h_node["value"]
        if not (_is_number(wv) and _is_number(hv)):
            exclusions.append(Exclusion(EX_MISSING, oid, base,
                                        "width/height are not numeric."))
            continue

        items.append(QuantityItem(
            "Q-04", oid, wv * hv, U_MM2,          # mm * mm -> mm2
            [f"{base}/width", f"{base}/height"],
            [{"width": wv, "height": hv, "unit": U_MM}],
            "width x height", COMPLETE))
    return items, exclusions


# --------------------------------------------------------------------------
# Schedule assembly
# --------------------------------------------------------------------------
def build_schedule(master, derived_verdicts=None, c1_allows=True):
    """Build the external derived quantity schedule.

    Returns a plain dict. Nothing is written anywhere: persisting the result
    is the caller's act, and inserting it into a manifest belongs to C6.
    """
    schedule = {
        "schedule_type": "QUANTITY_SCHEDULE",
        "result_kind": "EXTERNAL_DERIVED_RESULT",
        "written_to_master": False,
        "scope": ["Q-01", "Q-02", "Q-03", "Q-04"],
        "out_of_scope": ["Q-05 floor area (DEC-C4-03 deferred)",
                         "Q-06 wall surface area (DEC-C4-04 deferred)",
                         "material quantities", "volumetric quantities "
                         "(GAP-C4-01: no mm3 unit)", "BOQ", "cost estimate"],
        "items": [], "exclusions": [], "completeness": {},
        "class_a": {},
        "fidelity": "NOT_ASSESSED — matching the schedule against the master "
                    "is owned by D.",
        "provenance_caveat": "Provenance shows a value came from the master. "
                             "It does NOT show the value is correct, nor that "
                             "the source field is correct.",
    }

    if not c1_allows:
        schedule["completeness"] = {"overall": ABSTAIN}
        schedule["abstention"] = {
            "reason": "C1 did not permit this output. C4 consumes that "
                      "decision and does not re-evaluate it."}
        return schedule

    all_items, all_ex = [], []

    c_items, c_ex = q01_count(master)
    all_items += c_items
    all_ex += c_ex

    l_items, l_ex = q02_wall_length(master, derived_verdicts)
    all_items += l_items
    all_ex += l_ex

    total_item, t_ex, t_complete = q03_total_wall_length(master,
                                                         derived_verdicts)
    if total_item is not None:
        all_items.append(total_item)
    schedule["completeness"]["Q-03"] = t_complete

    a_items, a_ex = q04_opening_area(master, derived_verdicts)
    all_items += a_items
    all_ex += a_ex

    declared_openings = len(master.get("openings") or [])
    schedule["completeness"]["Q-04"] = (
        COMPLETE if len(a_items) == declared_openings else
        (ABSTAIN if declared_openings and not a_items else PARTIAL))
    schedule["completeness"]["Q-02"] = (
        COMPLETE if len(l_items) == len(master.get("walls") or []) else
        (ABSTAIN if (master.get("walls") and not l_items) else PARTIAL))

    schedule["items"] = [i.as_dict() for i in all_items]
    schedule["exclusions"] = [e.as_dict() for e in all_ex]

    # Completeness is DECLARED first, because A-Q7 classification depends on
    # the declaration already being present. Declaring after classifying would
    # make the A-Q7 check read a state that does not exist yet.
    overall = ABSTAIN if not schedule["items"] else (
        COMPLETE if all(v == COMPLETE
                        for v in schedule["completeness"].values())
        else PARTIAL)
    schedule["completeness"]["overall"] = overall
    if overall == PARTIAL:
        schedule["partial_notice"] = (
            "PARTIAL — one or more declared elements were excluded. Totals "
            "below are not complete totals; see basis and exclusions.")

    # Class A is decided by A-Q1..A-Q8 ONLY.
    #
    # A-Q7 reads: "declared completeness — full OR marked partial". So a
    # PARTIAL result is class A provided its completeness is properly
    # DECLARED (basis + PARTIAL marker + listed exclusions per section 9).
    # Partial-ness is a property of COVERAGE, not of the quality of the items
    # that were included: two fully eligible walls summed correctly do not
    # become non-class-A because a third wall was [U].
    #
    # What DOES remove class A is an UNDECLARED completeness state, or an
    # ABSTAIN (no eligible item at all, so there is nothing to classify).
    for qid in ("Q-01", "Q-02", "Q-03", "Q-04"):
        comp = schedule["completeness"].get(qid, COMPLETE)
        present = any(i["quantity_id"] == qid for i in schedule["items"])
        if not present or comp == ABSTAIN:
            schedule["class_a"][qid] = False
            continue
        if comp == PARTIAL:
            # A-Q7 is satisfied only when the partial state is fully declared.
            declared = ("partial_notice" in schedule
                        or any(i["quantity_id"] == qid and " of " in
                               str(i.get("basis", "")) for i in
                               schedule["items"]))
            schedule["class_a"][qid] = bool(declared)
            continue
        schedule["class_a"][qid] = True

    return schedule
