#!/usr/bin/env python3
"""
PHASE 01 — SPACE ANALYSIS · UNIT 1 · EXISTING-STATE ANALYSIS  (O-1)

Reference (APPROVED / LOCKED):
  PHASE-01-SPACE-ANALYSIS-ARCHITECTURE-R01.md
  PHASE-01-SPACE-ANALYSIS-ARCHITECTURE-R02-DELTA.md

WHAT THIS UNIT DOES
  Represents the existing space EXACTLY as the validated master declares it,
  carrying every status and source through untouched.

GEOMETRY AUTHORITY — A-02 / GA-1..GA-8, non-negotiable
      C3 owns geometric representation.
      Phase 01 owns spatial analysis of declared geometry.
      Phase 01 does NOT become a geometry authority.

  So this unit never rebuilds geometry, never alters a coordinate, never
  mints a reference dimension, never produces alternative wall/opening
  geometry, and never lets an analytical measurement become a master fact.

O-1 IS ANALYTICAL EVIDENCE
  Not Class A. Not engineering truth. Not a geometry source. Not a design
  master. Its class is declared on every emission so it cannot be mistaken.

THREE-WAY DISTINCTION
  UNKNOWN != NOT_PRESENT != VALUE. An unknown is shown AS unknown, never as
  emptiness and never filled by assumption.

WRITES NOTHING. Reads the master, returns a structure.
"""

import copy

# --- output classification -------------------------------------------------
ANALYTICAL_EVIDENCE = "ANALYTICAL_EVIDENCE"

# --- representation states -------------------------------------------------
REPRESENTED = "REPRESENTED"           # declared and carried through
UNKNOWN_DECLARED = "UNKNOWN_DECLARED"  # [U] — shown as unknown
NOT_PRESENT_DECLARED = "NOT_PRESENT_DECLARED"  # positively confirmed absence
UNRESOLVED = "UNRESOLVED"             # cannot be analysed from what exists
NOT_DECLARED = "NOT_DECLARED"         # the master says nothing at all

# --- presence vocabulary (consumed from the master, never invented) -------
PRESENT = "PRESENT"
NOT_PRESENT = "NOT_PRESENT"
UNKNOWN = "UNKNOWN"

# Collections this unit reports on. Each is READ, never authored.
FIXED_ELEMENT_COLLECTIONS = ("columns",)
ENVELOPE_COLLECTIONS = ("walls",)
OPENING_COLLECTIONS = ("openings",)

# space fields carried as declared
SPACE_FIELDS = ("outline", "ceiling_height", "floor_level",
                "orientation_north", "structural_beams", "services")


def _fact_view(node, path):
    """Carry a fact through with its status and source. Never evaluate it."""
    if not isinstance(node, dict) or "status" not in node:
        return {"path": path, "representation": NOT_DECLARED,
                "status": None, "source_type": None, "value": None,
                "note": "no fact declared at this path"}

    status = node.get("status")
    view = {
        "path": path,
        "status": status,                       # carried verbatim
        "source_type": node.get("source_type"),
        "source_ref": node.get("source_ref"),
        "unit": node.get("unit"),
        "value": copy.deepcopy(node.get("value")),
        "analytical_measurement": False,
        "is_master_fact": True,
        "stored_in_master": True,
    }
    if status == "U":
        view["representation"] = UNKNOWN_DECLARED
        view["note"] = ("declared UNKNOWN; shown as unknown and never "
                        "inferred")
    else:
        view["representation"] = REPRESENTED
    return view


def _presence_view(master, key):
    """Read a presence_register entry. The three states stay distinct."""
    entry = (master.get("presence_register") or {}).get(key)
    if not isinstance(entry, dict):
        return {"collection": key, "presence": None,
                "representation": NOT_DECLARED,
                "note": "no presence declared for this collection"}

    presence = entry.get("presence")
    if presence == NOT_PRESENT:
        rep, note = (NOT_PRESENT_DECLARED,
                     "positively confirmed absent; this is NOT an unknown "
                     "and NOT an empty value")
    elif presence == PRESENT:
        rep, note = REPRESENTED, "declared present"
    elif presence == UNKNOWN:
        rep, note = (UNKNOWN_DECLARED,
                     "presence is UNKNOWN; unasked is not absent")
    else:
        rep, note = NOT_DECLARED, "presence value not recognised; not inferred"

    return {"collection": key, "presence": presence, "representation": rep,
            "status": entry.get("status"), "source_type":
            entry.get("source_type"), "note": note}


def _element_view(item, index, collection):
    """Carry one element through. Coordinates are copied, never recomputed."""
    eid = item.get("id") if isinstance(item, dict) else None
    view = {"collection": collection, "index": index, "id": eid,
            "geometry_rebuilt": False, "coordinates_modified": False}

    if eid is None:
        view["representation"] = UNRESOLVED
        view["note"] = ("element has no declared id; it cannot be referenced "
                        "and Phase 01 does not assign one")
        return view

    for field in ("start", "end", "offset", "width", "height", "thickness",
                  "position", "boundary"):
        if isinstance(item, dict) and field in item:
            view[field] = _fact_view(item[field],
                                     f"{collection}/{index}/{field}")

    for plain in ("kind", "host_wall"):
        if isinstance(item, dict) and plain in item:
            view[plain] = item[plain]

    view["representation"] = REPRESENTED
    return view


def analyse_existing_state(master):
    """Build O-1 from the validated master. Read-only, no geometry authored.

    Returns an Existing-State record that declares its own class, its own
    limits, and every unknown it met.
    """
    if not isinstance(master, dict):
        return {
            "output_id": "O-1",
            "output_name": "Existing-State Plan",
            "output_class": ANALYTICAL_EVIDENCE,
            "status": "ABSTAINED",
            "abstention_reason": ("no validated master supplied; Phase 01 "
                                  "does not analyse what it has not been "
                                  "given"),
            "is_class_a": False,
        }

    record = {
        "output_id": "O-1",
        "output_name": "Existing-State Plan",
        # declared on every emission so it can never be mistaken for A
        "output_class": ANALYTICAL_EVIDENCE,
        "is_class_a": False,
        "is_engineering_truth": False,
        "is_geometry_source": False,
        "is_design_master": False,
        "geometry_owner": "C3",
        "analysis_owner": "PHASE_01",
        "status": None,
        "space": {},
        "envelope": {},
        "openings": {},
        "fixed_elements": {},
        "unknowns_encountered": [],
        "analysis_limits": [],
        "notices": [
            "O-1 is analytical evidence, not Class A and not engineering "
            "truth",
            "C3 owns geometric representation; Phase 01 analyses declared "
            "geometry only",
            "no geometry was rebuilt and no coordinate was modified",
            "UNKNOWN, NOT_PRESENT and a value remain three distinct states",
        ],
    }

    # ---- space fields ----------------------------------------------------
    space = master.get("space") or {}
    for field in SPACE_FIELDS:
        if field in space:
            view = _fact_view(space[field], f"space/{field}")
            record["space"][field] = view
            if view["representation"] == UNKNOWN_DECLARED:
                record["unknowns_encountered"].append(
                    {"path": view["path"], "kind": "SPACE_FIELD"})
        else:
            record["space"][field] = {
                "path": f"space/{field}", "representation": NOT_DECLARED,
                "note": "not declared in the master; not inferred"}

    # ---- the outline decides whether a plan can be represented at all ----
    outline = record["space"].get("outline", {})
    outline_usable = (outline.get("representation") == REPRESENTED
                      and isinstance(outline.get("value"), list)
                      and len(outline.get("value") or []) >= 3)

    if not outline_usable:
        record["analysis_limits"].append({
            "limit": "NO_EXISTING_STATE_PLAN",
            "reason": ("space/outline is not a usable declared boundary "
                       f"(representation="
                       f"{outline.get('representation')}); an existing-state "
                       f"plan cannot be represented and is NOT inferred"),
        })

    # ---- envelope: walls -------------------------------------------------
    for coll in ENVELOPE_COLLECTIONS:
        items = master.get(coll)
        presence = _presence_view(master, coll)
        entry = {"presence": presence, "count": None, "elements": []}
        if items is None:
            entry["representation"] = NOT_DECLARED
        else:
            entry["count"] = len(items)
            entry["representation"] = REPRESENTED
            for i, item in enumerate(items):
                ev = _element_view(item, i, coll)
                entry["elements"].append(ev)
                for key, val in ev.items():
                    if isinstance(val, dict) and \
                            val.get("representation") == UNKNOWN_DECLARED:
                        record["unknowns_encountered"].append(
                            {"path": val["path"], "kind": "ELEMENT_FIELD"})
        record["envelope"][coll] = entry

    # ---- openings --------------------------------------------------------
    for coll in OPENING_COLLECTIONS:
        items = master.get(coll)
        presence = _presence_view(master, coll)
        entry = {"presence": presence, "count": None, "elements": []}

        if presence["representation"] == NOT_PRESENT_DECLARED:
            entry["representation"] = NOT_PRESENT_DECLARED
            entry["count"] = 0
            entry["note"] = ("confirmed absent by the client; this is a "
                             "declared fact, not an unknown and not an "
                             "empty value")
        elif presence["representation"] == UNKNOWN_DECLARED:
            entry["representation"] = UNKNOWN_DECLARED
            entry["note"] = ("presence unknown; the absence of items is NOT "
                             "evidence of absence")
            record["unknowns_encountered"].append(
                {"path": f"presence_register/{coll}", "kind": "PRESENCE"})
            record["analysis_limits"].append({
                "limit": f"{coll.upper()}_PRESENCE_UNKNOWN",
                "reason": ("openings presence is unknown, so any analysis "
                           "depending on openings is UNRESOLVED"),
            })
        elif items is not None:
            entry["count"] = len(items)
            entry["representation"] = REPRESENTED
            for i, item in enumerate(items):
                entry["elements"].append(_element_view(item, i, coll))
        else:
            entry["representation"] = NOT_DECLARED

        record["openings"][coll] = entry

    # ---- fixed elements --------------------------------------------------
    for coll in FIXED_ELEMENT_COLLECTIONS:
        items = master.get(coll)
        presence = _presence_view(master, coll)
        entry = {"presence": presence, "count": None, "elements": []}

        if presence["representation"] == NOT_PRESENT_DECLARED:
            entry["representation"] = NOT_PRESENT_DECLARED
            entry["count"] = 0
        elif presence["representation"] == UNKNOWN_DECLARED:
            entry["representation"] = UNKNOWN_DECLARED
            record["unknowns_encountered"].append(
                {"path": f"presence_register/{coll}", "kind": "PRESENCE"})
        elif items is not None:
            entry["count"] = len(items)
            entry["representation"] = REPRESENTED
            for i, item in enumerate(items):
                entry["elements"].append(_element_view(item, i, coll))
        else:
            entry["representation"] = NOT_DECLARED

        record["fixed_elements"][coll] = entry

    # ---- overall status --------------------------------------------------
    if not outline_usable:
        record["status"] = "PARTIAL_ANALYSIS"
        record["status_note"] = ("the space boundary is not usable, so no "
                                 "existing-state plan is represented; the "
                                 "remaining declared elements are still "
                                 "reported")
    else:
        record["status"] = "ANALYSED"
        record["status_note"] = ("existing state represented from declared "
                                 "master data only")

    return record
