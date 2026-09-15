#!/usr/bin/env python3
"""
validate_refs.py — Phase 00.5-B1: Cross-Reference Integrity

The schema validates the SHAPE of an id ("^M-[0-9]{2,3}$").
It cannot validate the EXISTENCE of the thing that id points at.
This engine closes that gap.

Scope of B1 (deliberately narrow):
  - dangling references      (pointing at something that does not exist)
  - duplicate ids            (an id that resolves to two different things)
  - invalid parent/child     (relationship exists but is semantically illegal)
  - reference cycles         (A derives from B derives from A)
  - fingerprint coherence    (a view claiming a revision/version/camera that does not exist)
  - bidirectional integrity  (proposal->decision must point back)

NOT in scope for B1 (later sub-phases):
  B2 wall closure · B3 overlap · B4 circulation · B5 door swing
  B6 formula arithmetic · B7 blocking-gate integration

Every finding carries a rule code so a test can prove THAT rule fired.
"""

import re
from collections import defaultdict

# --------------------------------------------------------------------------
# Element collections and their id prefixes
# --------------------------------------------------------------------------
COLLECTIONS = {
    "walls": "W",
    "openings": ("D", "WN"),
    "columns": "C",
    "zones": "Z",
    "furniture": "F",
    "materials": "M",
    "lighting": "L",
    "cameras": "CAM",
}

REGISTERS = {
    "unknowns": "id",
    "assumptions": "id",
    "proposals": "id",
    "decisions": "decision_id",
    "change_requests": "id",
    "objections": "id",
}


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
# Index building
# --------------------------------------------------------------------------
def build_index(data):
    """Map every declared id -> (collection, object). Also detect duplicates."""
    index = {}
    duplicates = []
    for coll in COLLECTIONS:
        for i, item in enumerate(data.get(coll) or []):
            if not isinstance(item, dict):
                continue
            eid = item.get("id")
            if eid is None:
                continue
            if eid in index:
                duplicates.append((eid, index[eid][0], coll, i))
            else:
                index[eid] = (coll, item)

    regs = data.get("registers") or {}
    for reg, key in REGISTERS.items():
        for i, item in enumerate(regs.get(reg) or []):
            if not isinstance(item, dict):
                continue
            rid = item.get(key)
            if rid is None:
                continue
            if rid in index:
                duplicates.append((rid, index[rid][0], f"registers.{reg}", i))
            else:
                index[rid] = (f"registers.{reg}", item)

    for i, o in enumerate(data.get("outputs") or []):
        if not isinstance(o, dict):
            continue
        oid = o.get("output_id")
        if oid is None:
            continue
        if oid in index:
            duplicates.append((oid, index[oid][0], "outputs", i))
        else:
            index[oid] = ("outputs", o)

    return index, duplicates


def _is_fact(node):
    return isinstance(node, dict) and "status" in node and "source_type" in node


def iter_facts(node, path=""):
    if _is_fact(node):
        yield path, node
        return
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_facts(v, f"{path}/{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_facts(v, f"{path}/{i}")


def resolve_fact_path(data, ref):
    """Resolve 'space.outline' or 'walls.W-01.thickness' or 'walls/0/thickness'."""
    parts = [p for p in re.split(r"[./]", ref.strip()) if p]
    cur = data
    for p in parts:
        if isinstance(cur, list):
            hit = None
            if p.isdigit() and int(p) < len(cur):
                hit = cur[int(p)]
            else:
                for item in cur:
                    if isinstance(item, dict) and item.get("id") == p:
                        hit = item
                        break
            if hit is None:
                return None
            cur = hit
        elif isinstance(cur, dict):
            if p not in cur:
                return None
            cur = cur[p]
        else:
            return None
    return cur


# --------------------------------------------------------------------------
# XR rules
# --------------------------------------------------------------------------
def check_cross_references(data):
    findings = []
    index, duplicates = build_index(data)
    regs = data.get("registers") or {}

    def exists(ref):
        return ref in index

    def kind_of(ref):
        return index[ref][0] if ref in index else None

    # ---- XR-000 duplicate ids -------------------------------------------
    for eid, first, second, i in duplicates:
        findings.append(Finding(
            "XR-000", f"{second}/{i}",
            f"duplicate id '{eid}' — already declared in '{first}'. "
            f"An id must resolve to exactly one thing."))

    # ---- XR-001 opening.host_wall ---------------------------------------
    for i, op in enumerate(data.get("openings") or []):
        hw = op.get("host_wall")
        if hw is None:
            continue
        if not exists(hw):
            findings.append(Finding(
                "XR-001", f"openings/{i} ({op.get('id')})",
                f"host_wall '{hw}' does not exist. Opening is hosted on a phantom wall."))
        elif kind_of(hw) != "walls":
            findings.append(Finding(
                "XR-001", f"openings/{i} ({op.get('id')})",
                f"host_wall '{hw}' resolves to '{kind_of(hw)}', not a wall."))

    # ---- XR-002 furniture.zone_ref --------------------------------------
    for i, f in enumerate(data.get("furniture") or []):
        zr = f.get("zone_ref")
        if zr is None:
            continue
        if not exists(zr):
            findings.append(Finding(
                "XR-002", f"furniture/{i} ({f.get('id')})",
                f"zone_ref '{zr}' does not exist."))
        elif kind_of(zr) != "zones":
            findings.append(Finding(
                "XR-002", f"furniture/{i} ({f.get('id')})",
                f"zone_ref '{zr}' resolves to '{kind_of(zr)}', not a zone."))

    # ---- XR-003 furniture.material_ref ----------------------------------
    for i, f in enumerate(data.get("furniture") or []):
        mr = f.get("material_ref")
        if mr is None:
            continue
        if not exists(mr):
            findings.append(Finding(
                "XR-003", f"furniture/{i} ({f.get('id')})",
                f"material_ref '{mr}' does not exist. Element has no real material."))
        elif kind_of(mr) != "materials":
            findings.append(Finding(
                "XR-003", f"furniture/{i} ({f.get('id')})",
                f"material_ref '{mr}' resolves to '{kind_of(mr)}', not a material."))

    # ---- XR-004 wall.finish_ref -----------------------------------------
    for i, w in enumerate(data.get("walls") or []):
        fr = w.get("finish_ref")
        if fr is None:
            continue
        if not exists(fr):
            findings.append(Finding(
                "XR-004", f"walls/{i} ({w.get('id')})",
                f"finish_ref '{fr}' does not exist."))
        elif kind_of(fr) != "materials":
            findings.append(Finding(
                "XR-004", f"walls/{i} ({w.get('id')})",
                f"finish_ref '{fr}' resolves to '{kind_of(fr)}', not a material."))

    # ---- XR-005 material.applied_to -------------------------------------
    # applied_to is an unpatterned string list, so BOTH dangling refs and
    # type-confusion are reachable here (unlike the prefix-constrained refs).
    APPLICABLE = {"walls", "openings", "columns", "zones", "furniture", "lighting"}
    for i, mat in enumerate(data.get("materials") or []):
        for j, tgt in enumerate(mat.get("applied_to") or []):
            loc = f"materials/{i} ({mat.get('id')}).applied_to[{j}]"
            if not exists(tgt):
                findings.append(Finding(
                    "XR-005", loc, f"applied to '{tgt}' which does not exist."))
            elif kind_of(tgt) not in APPLICABLE:
                findings.append(Finding(
                    "XR-019", loc,
                    f"applied to '{tgt}' which is a '{kind_of(tgt)}' entry, not a "
                    f"physical element. A material cannot be applied to a record."))

    # ---- XR-006 fact.decision_id ----------------------------------------
    decision_ids = {d.get("decision_id") for d in regs.get("decisions") or []}
    for path, fact in iter_facts(data):
        did = fact.get("decision_id")
        if did and did not in decision_ids:
            findings.append(Finding(
                "XR-006", path,
                f"decision_id '{did}' has no Decision Record. Approval claimed "
                f"without evidence."))

    # ---- XR-007 fact.assumption_id / proposal_id / unknown_id -----------
    a_ids = {a.get("id") for a in regs.get("assumptions") or []}
    p_ids = {p.get("id") for p in regs.get("proposals") or []}
    u_ids = {u.get("id") for u in regs.get("unknowns") or []}
    for path, fact in iter_facts(data):
        aid = fact.get("assumption_id")
        if aid and aid not in a_ids:
            findings.append(Finding(
                "XR-007", path,
                f"assumption_id '{aid}' is not in the assumptions register. "
                f"An undeclared assumption is an invented fact."))
        pid = fact.get("proposal_id")
        if pid and pid not in p_ids:
            findings.append(Finding(
                "XR-007", path,
                f"proposal_id '{pid}' is not in the proposals register."))
        uid = fact.get("unknown_id")
        if uid and uid not in u_ids:
            findings.append(Finding(
                "XR-007", path,
                f"unknown_id '{uid}' is not in the unknowns register. "
                f"An unregistered unknown is invisible to the gate."))

    # ---- XR-008 fact.derived_from ---------------------------------------
    for path, fact in iter_facts(data):
        if fact.get("status") != "D":
            continue
        for ref in fact.get("derived_from") or []:
            target = resolve_fact_path(data, ref)
            if target is None:
                findings.append(Finding(
                    "XR-008", path,
                    f"derived_from '{ref}' does not resolve to anything in the master."))
            elif not _is_fact(target):
                findings.append(Finding(
                    "XR-008", path,
                    f"derived_from '{ref}' resolves to a non-fact node. A derivation "
                    f"must be traceable to a provenance-wrapped value."))

    # ---- XR-009 fact.conflict.cr_id -------------------------------------
    cr_ids = {c.get("id") for c in regs.get("change_requests") or []}
    for path, fact in iter_facts(data):
        conf = fact.get("conflict")
        if isinstance(conf, dict):
            cid = conf.get("cr_id")
            if cid and cid not in cr_ids:
                findings.append(Finding(
                    "XR-009", path,
                    f"KNOWN CONFLICT cites '{cid}' which is not in the change-request "
                    f"register. The conflict has no route to resolution."))

    # ---- XR-010 decision -> proposal (and back) -------------------------
    for i, d in enumerate(regs.get("decisions") or []):
        lp = d.get("linked_proposal")
        if lp and lp not in p_ids:
            findings.append(Finding(
                "XR-010", f"registers/decisions/{i} ({d.get('decision_id')})",
                f"linked_proposal '{lp}' does not exist."))
        uo = d.get("user_override_of")
        o_ids = {o.get("id") for o in regs.get("objections") or []}
        if uo and uo not in o_ids:
            findings.append(Finding(
                "XR-010", f"registers/decisions/{i} ({d.get('decision_id')})",
                f"user_override_of '{uo}' is not a registered objection."))
        for j, el in enumerate(d.get("linked_elements") or []):
            if not exists(el):
                findings.append(Finding(
                    "XR-010", f"registers/decisions/{i}.linked_elements[{j}]",
                    f"decision affects '{el}' which does not exist."))

    # ---- XR-011 proposal -> decision, bidirectional ---------------------
    for i, p in enumerate(regs.get("proposals") or []):
        did = p.get("decision_id")
        if not did:
            continue
        if did not in decision_ids:
            findings.append(Finding(
                "XR-011", f"registers/proposals/{i} ({p.get('id')})",
                f"decision_id '{did}' does not exist."))
            continue
        dec = next(d for d in regs["decisions"] if d.get("decision_id") == did)
        if dec.get("linked_proposal") != p.get("id"):
            findings.append(Finding(
                "XR-011", f"registers/proposals/{i} ({p.get('id')})",
                f"broken bidirectional link: proposal points at {did}, but {did} "
                f"points back at '{dec.get('linked_proposal')}'."))

    # ---- XR-012 changelog.cr_id -----------------------------------------
    for i, c in enumerate(regs.get("changelog") or []):
        cid = c.get("cr_id")
        if cid and cid not in cr_ids:
            findings.append(Finding(
                "XR-012", f"registers/changelog/{i}",
                f"changelog cites CR '{cid}' which does not exist."))

    # ---- XR-013 cr.target_element ---------------------------------------
    for i, c in enumerate(regs.get("change_requests") or []):
        tgt = c.get("target_element")
        if not tgt:
            continue
        head = re.split(r"[ .(/]", tgt.strip())[0]
        if re.match(r"^(W|D|WN|C|Z|F|M|L|CAM)-[0-9]+$", head) and not exists(head):
            findings.append(Finding(
                "XR-013", f"registers/change_requests/{i} ({c.get('id')})",
                f"targets element '{head}' which does not exist."))

    # ---- XR-014 output.derived_from_output + parent/child validity ------
    outputs = data.get("outputs") or []
    out_by_id = {o.get("output_id"): o for o in outputs if isinstance(o, dict)}
    for i, o in enumerate(outputs):
        parent = o.get("derived_from_output")
        if parent is None:
            continue
        if parent == o.get("output_id"):
            findings.append(Finding(
                "XR-014", f"outputs/{i} ({o.get('output_id')})",
                "output derives from itself."))
            continue
        if parent not in out_by_id:
            findings.append(Finding(
                "XR-014", f"outputs/{i} ({o.get('output_id')})",
                f"derived_from_output '{parent}' does not exist."))
            continue
        # parent/child semantic validity: a Class B must descend from Class A
        if o.get("class") == "B" and out_by_id[parent].get("class") != "A":
            findings.append(Finding(
                "XR-015", f"outputs/{i} ({o.get('output_id')})",
                f"Class B output derives from Class {out_by_id[parent].get('class')} "
                f"'{parent}'. A presentation visual must descend from a "
                f"DESIGN-ACCURATE parent, never from another visual or an AI image."))

    # ---- XR-016 reference cycles in outputs -----------------------------
    # A direct self-reference is already reported by XR-014; excluded here so a
    # single defect yields a single rule code.
    self_refs = {o.get("output_id") for o in outputs
                 if isinstance(o, dict) and o.get("derived_from_output") == o.get("output_id")}
    for oid in out_by_id:
        if oid in self_refs:
            continue
        seen, cur = [], oid
        while cur is not None:
            if cur in seen:
                findings.append(Finding(
                    "XR-016", f"outputs ({oid})",
                    f"cyclic derivation chain: {' -> '.join(seen + [cur])}"))
                break
            seen.append(cur)
            nxt = out_by_id.get(cur, {}).get("derived_from_output")
            cur = nxt if (nxt in out_by_id and nxt not in self_refs) else None

    # ---- XR-017 fingerprint coherence -----------------------------------
    meta = data.get("meta") or {}
    known_revisions = {meta.get("revision")} | {
        c.get("revision") for c in regs.get("changelog") or []}
    known_revisions.discard(None)
    cam_ids = {c.get("id") for c in data.get("cameras") or []}
    for i, o in enumerate(outputs):
        fp = o.get("fingerprint") or {}
        loc = f"outputs/{i} ({o.get('output_id')})"
        if fp.get("project_id") and fp["project_id"] != meta.get("project_id"):
            findings.append(Finding(
                "XR-017", loc,
                f"fingerprint project_id '{fp['project_id']}' != master "
                f"'{meta.get('project_id')}'. Output belongs to another project."))
        if fp.get("master_revision") and fp["master_revision"] not in known_revisions:
            findings.append(Finding(
                "XR-017", loc,
                f"fingerprint cites revision '{fp['master_revision']}' which does not "
                f"exist in this master (known: {sorted(known_revisions)})."))
        if fp.get("geometry_version") and fp["geometry_version"] != meta.get("geometry_version"):
            findings.append(Finding(
                "XR-017", loc,
                f"fingerprint geometry_version '{fp['geometry_version']}' != master "
                f"'{meta.get('geometry_version')}'. View is from a stale model."))
        cid = fp.get("camera_id")
        if cid and cid not in cam_ids:
            findings.append(Finding(
                "XR-018", loc,
                f"fingerprint cites camera '{cid}' which is not defined. The view "
                f"cannot be reproduced."))

    return findings


def validate_references(data):
    """Return (ok, findings)."""
    findings = check_cross_references(data)
    return (len([f for f in findings if f.severity == "ERROR"]) == 0), findings


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: validate_refs.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs = validate_references(payload)
    print("CROSS-REFERENCE INTEGRITY:", "PASS" if ok else f"FAIL ({len(fs)} finding(s))")
    for f in fs:
        print(" ", f)
    sys.exit(0 if ok else 1)
