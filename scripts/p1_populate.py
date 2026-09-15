#!/usr/bin/env python3
"""
PHASE 01 — G2 · STRUCTURAL POPULATION

Builds project_master.json content from intake answers, starting from the
template. Every value carries a status and a source. Nothing is invented.

STATUS RULES (locked contract)
  [C]  client-confirmed input only, source_type CLIENT_INPUT
  [D]  NEVER created here — a derived value needs formula + derived_from and
       is governed by B6
  [A]  recorded only as AGENT_ASSUMPTION with approval_state PENDING_APPROVAL.
       Phase 01 cannot approve it, cannot turn it into [C], and grants it no
       design or class-A eligibility
  [U]  UNKNOWN — the default for anything not supplied, registered in
       registers.unknowns
  [P]  a declared proposal awaiting the user

THREE-WAY DISTINCTION
  NOT_PRESENT is a positive user confirmation of absence. It is not UNKNOWN
  and it is not a value. Phase 01 never converts one into another.

CONTRADICTIONS
  Declared, never corrected. An inconsistent intake is reported as-is.

THIS MODULE WRITES NO FILE. It returns a structure; persisting it is the
caller's act, and Phase 01 never touches the schema or the template.
"""

import copy
import json
import os

# --- statuses --------------------------------------------------------------
STATUS_C = "C"
STATUS_D = "D"      # never produced here
STATUS_A = "A"
STATUS_U = "U"
STATUS_P = "P"

# --- source types (schema vocabulary; consumed, not extended) -------------
SRC_CLIENT_INPUT = "CLIENT_INPUT"
SRC_AGENT_ASSUMPTION = "AGENT_ASSUMPTION"
SRC_NOT_PROVIDED = "NOT_PROVIDED"

# --- presence vocabulary ---------------------------------------------------
PRESENT = "PRESENT"
NOT_PRESENT = "NOT_PRESENT"
UNKNOWN = "UNKNOWN"

PENDING_APPROVAL = "PENDING_APPROVAL"

CONTRADICTION = "CONTRADICTION"

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "project_master.template.json")


class PopulationError(RuntimeError):
    """Raised when population is asked to do something forbidden."""


def load_template(path=None):
    """Read the template as a starting point. Read-only, never modified."""
    with open(path or TEMPLATE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def make_fact(value, status, source_type, source_ref, recorded_on,
              unit=None, note=None):
    """Build one tagged fact. Every field carries status AND source."""
    if status == STATUS_D:
        raise PopulationError(
            "Phase 01 cannot create a [D]. A derived value requires formula "
            "and derived_from and is governed by B6.")
    fact = {"value": value, "status": status, "source_type": source_type,
            "source_ref": source_ref, "recorded_on": recorded_on}
    if unit is not None:
        fact["unit"] = unit
    if note is not None:
        fact["note"] = note
    return fact


def make_unknown(source_ref, recorded_on, unit=None, note=None):
    """An absent value becomes [U] — declared, never guessed."""
    return make_fact(None, STATUS_U, SRC_NOT_PROVIDED, source_ref,
                     recorded_on, unit=unit,
                     note=note or "not supplied at intake; recorded as "
                                  "UNKNOWN and registered")


def make_assumption(value, source_ref, recorded_on, unit=None, note=None):
    """An [A] is recorded PENDING_APPROVAL. Phase 01 cannot approve it."""
    fact = make_fact(value, STATUS_A, SRC_AGENT_ASSUMPTION, source_ref,
                     recorded_on, unit=unit,
                     note=note or "agent assumption; awaiting approval")
    fact["approval_state"] = PENDING_APPROVAL
    return fact


def register_unknown(master, unknown_id, question, affects, blocking,
                     raised_on):
    """Register an unknown.

    `blocking` is CARRIED from the declared classification. Phase 01 never
    decides it (G1-4 / G1-6.2).
    """
    if blocking not in (True, False):
        raise PopulationError(
            "the blocking flag must be carried from the declared "
            "classification; Phase 01 does not infer it.")
    entry = {"id": unknown_id, "question": question, "affects": affects,
             "blocking": blocking, "raised_on": raised_on}
    master.setdefault("registers", {}).setdefault("unknowns", []).append(entry)
    return entry


def register_assumption(master, assumption_id, text, impact, raised_on):
    """Register an [A]. Always PENDING_APPROVAL; approval belongs to E."""
    entry = {"id": assumption_id, "text": text, "impact": impact,
             "approval_state": PENDING_APPROVAL, "raised_on": raised_on}
    master.setdefault("registers", {}).setdefault("assumptions", []).append(
        entry)
    return entry


def detect_contradictions(intake_answers):
    """Report inconsistencies in the intake. NEVER corrects them.

    Only mathematically checkable inconsistencies are reported, and only
    where the intake supplies the material to check. No design judgement and
    no engineering standard is applied.
    """
    findings = []
    answers = intake_answers if isinstance(intake_answers, dict) else {}

    outline = answers.get("space.outline")
    if isinstance(outline, list) and len(outline) >= 3:
        first, last = outline[0], outline[-1]
        closed = (isinstance(first, (list, tuple))
                  and isinstance(last, (list, tuple))
                  and len(first) >= 2 and len(last) >= 2
                  and first[0] == last[0] and first[1] == last[1])
        distinct_close = (isinstance(first, (list, tuple))
                          and isinstance(last, (list, tuple))
                          and len(first) >= 2 and len(last) >= 2
                          and (first[0] != last[0] or first[1] != last[1]))
        # A polygon may be given closed or open; neither is an error by
        # itself. What IS reportable is a declared edge count that does not
        # match the supplied points.
        declared_edges = answers.get("space.declared_edge_count")
        if isinstance(declared_edges, int):
            actual = len(outline) - (1 if closed else 0)
            if actual != declared_edges:
                findings.append({
                    "code": CONTRADICTION, "field": "space.outline",
                    "detail": (f"declared edge count {declared_edges} does "
                               f"not match {actual} supplied point(s)"),
                    "corrected": False,
                    "note": "declared, not corrected"})
        _ = distinct_close

    presence = answers.get("openings.presence")
    openings = answers.get("openings")
    if presence == NOT_PRESENT and isinstance(openings, list) and openings:
        findings.append({
            "code": CONTRADICTION, "field": "openings.presence",
            "detail": (f"presence declared NOT_PRESENT while {len(openings)} "
                       f"opening(s) were supplied"),
            "corrected": False, "note": "declared, not corrected"})

    return findings


def populate(intake_answers, g1_record, recorded_on, template=None):
    """G2: build the master from intake. Returns (master, population_record).

    Refuses to run when G1 abstained: a blocking field is missing and there
    is nothing legitimate to build.
    """
    if (g1_record or {}).get("verdict") == "ABSTAIN":
        raise PopulationError(
            "G1 abstained: a field declared BLOCKING is absent. Population "
            "does not begin.")

    master = copy.deepcopy(template if template is not None
                           else load_template())
    answers = intake_answers if isinstance(intake_answers, dict) else {}

    tagged, unknowns_registered, assumptions_registered = [], [], []

    # --- meta ------------------------------------------------------------
    for key in ("project_id", "project_name", "is_test_project", "track"):
        supplied = answers.get(f"meta.{key}")
        if supplied is not None and supplied != "":
            master.setdefault("meta", {})[key] = supplied
            tagged.append({"path": f"meta.{key}", "status": STATUS_C,
                           "source_type": SRC_CLIENT_INPUT})

    # --- space.ceiling_height --------------------------------------------
    ch = answers.get("space.ceiling_height")
    if ch is not None and ch != "":
        master["space"]["ceiling_height"] = make_fact(
            ch, STATUS_C, SRC_CLIENT_INPUT, "intake/2.4", recorded_on,
            unit="mm")
        tagged.append({"path": "space/ceiling_height", "status": STATUS_C,
                       "source_type": SRC_CLIENT_INPUT})
    else:
        master["space"]["ceiling_height"] = make_unknown(
            "intake/2.4", recorded_on, unit="mm")
        tagged.append({"path": "space/ceiling_height", "status": STATUS_U,
                       "source_type": SRC_NOT_PROVIDED})

    # --- space.outline -----------------------------------------------------
    outline = answers.get("space.outline")
    if isinstance(outline, list) and outline:
        master["space"]["outline"] = make_fact(
            outline, STATUS_C, SRC_CLIENT_INPUT, "intake/2.2", recorded_on,
            unit="mm")
        tagged.append({"path": "space/outline", "status": STATUS_C,
                       "source_type": SRC_CLIENT_INPUT})
    else:
        master["space"]["outline"] = make_unknown("intake/2.2", recorded_on,
                                                  unit="mm")
        tagged.append({"path": "space/outline", "status": STATUS_U,
                       "source_type": SRC_NOT_PROVIDED})

    # --- openings: the three-way distinction is preserved exactly ---------
    # A presence_register entry is a full fact object carrying `presence`.
    # Phase 01 fills the existing structure; it does not invent a new shape.
    presence = answers.get("openings.presence")
    preg = master.setdefault("presence_register", {})

    if presence == PRESENT:
        for i, op in enumerate(answers.get("openings") or []):
            master.setdefault("openings", []).append(op)
            tagged.append({"path": f"openings/{i}", "status": STATUS_C,
                           "source_type": SRC_CLIENT_INPUT})
        entry = make_fact(None, STATUS_C, SRC_CLIENT_INPUT, "intake/3",
                          recorded_on,
                          note="client declared openings are present")
        entry["presence"] = PRESENT
        preg["openings"] = entry
        tagged.append({"path": "presence_register/openings",
                       "status": STATUS_C, "source_type": SRC_CLIENT_INPUT,
                       "presence": PRESENT})

    elif presence == NOT_PRESENT:
        # A positive confirmation of absence. This is NOT an unknown.
        entry = make_fact(None, STATUS_C, SRC_CLIENT_INPUT, "intake/3",
                          recorded_on,
                          note="client positively confirmed there are no "
                               "openings; this is not an unknown")
        entry["presence"] = NOT_PRESENT
        preg["openings"] = entry
        tagged.append({"path": "presence_register/openings",
                       "status": STATUS_C, "source_type": SRC_CLIENT_INPUT,
                       "presence": NOT_PRESENT})

    else:
        entry = make_unknown("intake/3", recorded_on,
                             note="presence of openings was not declared; "
                                  "unasked is not absent")
        entry["presence"] = UNKNOWN
        preg["openings"] = entry
        tagged.append({"path": "presence_register/openings",
                       "status": STATUS_U, "source_type": SRC_NOT_PROVIDED,
                       "presence": UNKNOWN})

    # --- register every absent NON-BLOCKING field as an unknown -----------
    for i, miss in enumerate((g1_record or {}).get("missing_non_blocking", [])):
        uid = f"U-{i + 1:03d}"
        entry = register_unknown(
            master, uid, f"value for '{miss['field']}' was not supplied",
            miss["field"], False, recorded_on)
        unknowns_registered.append(entry)

    # --- blocking unknowns explicitly declared by the caller --------------
    offset = len(unknowns_registered)
    for j, declared in enumerate(answers.get("declared_blocking_unknowns")
                                 or []):
        uid = f"U-{offset + j + 1:03d}"
        entry = register_unknown(
            master, uid, declared.get("question", "unspecified"),
            declared.get("affects", "unspecified"), True, recorded_on)
        unknowns_registered.append(entry)

    # --- assumptions, if the caller declared any --------------------------
    for k, assumption in enumerate(answers.get("declared_assumptions") or []):
        aid = f"A-{k + 1:03d}"
        entry = register_assumption(
            master, aid, assumption.get("text", "unspecified"),
            assumption.get("impact", "unspecified"), recorded_on)
        assumptions_registered.append(entry)

    contradictions = detect_contradictions(answers)

    record = {
        "gate": "G2",
        "tagged_fields": tagged,
        "unknowns_registered": unknowns_registered,
        "assumptions_registered": assumptions_registered,
        "contradictions": contradictions,
        "unresolved_classification": list(
            (g1_record or {}).get("unresolved_classification", [])),
        "derived_created": 0,
        "confirmed_by_phase01": 0,
        "notes": [
            "every field carries a status and a source",
            "[D] is never created by Phase 01",
            "[A] is recorded PENDING_APPROVAL and is never approved here",
            "NOT_PRESENT, UNKNOWN and a value remain three distinct states",
            "contradictions are declared, never corrected",
        ],
    }
    return master, record
