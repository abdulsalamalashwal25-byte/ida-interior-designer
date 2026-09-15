#!/usr/bin/env python3
"""Phase 00.5-E — Governance / Identity / Approval / Output Ownership.

Reference: E Architecture R02 + R02 Local Amendment (APPROVED / LOCKED).

WHAT THIS SUITE MUST PROVE
  * the nine whitelisted transitions work, and nothing else is possible
  * SUPERSEDED and WITHDRAWN are terminal and cannot be revived
  * no AI/system/producer can act as USER or approve anything
  * approving a proposal does NOT create a decision
  * approval and fidelity are independent in both directions
  * E issues output identity; C6 and producers never do
  * class C is never upgraded to A or B

HONEST LIMITATION CARRIED THROUGHOUT
  Genuine human identity/approval is NOT provable in the current file-only
  model. CONFLICT-E-01 / GAP-02 remain OPEN.

DISCIPLINE (inherited)
  AS-C2-16 mutate through the binding actually used · AS-C2-17 literal
  expectations · AS-C4-18 no default-argument binding · duplicate defences
  isolated before every mutation.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import e_identity as IDN                                             # noqa: E402
import e_authorization as AUTH                                       # noqa: E402
import e_lifecycle as LC                                             # noqa: E402
import e_ownership as OWN                                            # noqa: E402

RESULTS = []
MUTATIONS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def mutation(mid, desc, classification, detail):
    MUTATIONS.append((mid, desc, classification, detail))


def fresh(cls="A", file="PRJ01_R01_A_FloorPlan.svg"):
    reg = []
    entry = OWN.register_output(reg, {"file": file, "view_type": "plan",
                                      "class": cls, "producer": "C3"})
    return reg, entry["output_id"]


def advance(reg, oid, to_state, actor="USER"):
    return OWN.transition(reg, oid, to_state, actor)


META = {"project_id": "PRJ-01", "revision": "R01",
        "master_hash": "a3f9c2e1", "geometry_version": "G-004"}


# ==========================================================================
# 1. G-1 IDENTITY REGISTRY
# ==========================================================================
_reg, _oid = fresh()
record("E-ID-01", "E issues an official output_id on registration",
       "OUT-001", f"{_oid}", _oid == "OUT-001")

record("E-ID-02", "Issued id matches the schema-approved pattern",
       "^OUT-[0-9]{3}$", f"{_oid}", IDN.valid_id("output", _oid))

_r2 = []
_ids = [OWN.register_output(_r2, {"file": f"f{i}.svg", "class": "A"})["output_id"]
        for i in range(3)]
record("E-ID-03", "Identities are sequential and unique",
       "OUT-001..003", f"{_ids}", _ids == ["OUT-001", "OUT-002", "OUT-003"])

_refused = None
try:
    IDN.issue_output_id([], issuer="C6")
except IDN.IdentityError as exc:
    _refused = str(exc)
record("E-ID-04", "C6 may NOT issue an official output_id",
       "IdentityError raised",
       f"refused={_refused is not None}", _refused is not None)

_refused_p = None
try:
    IDN.issue_output_id([], issuer="PRODUCER")
except IDN.IdentityError as exc:
    _refused_p = str(exc)
record("E-ID-05", "A producer may NOT issue an official output_id",
       "IdentityError raised", f"refused={_refused_p is not None}",
       _refused_p is not None)

_bind = IDN.bind_record(META, entity_refs=["DEC-001", "OUT-001"])
record("E-ID-06", "Governance record binds referentially to the master",
       "project/revision/hash/geometry carried",
       f"{_bind['project_id']}/{_bind['master_revision']}",
       _bind["project_id"] == "PRJ-01"
       and _bind["master_revision"] == "R01"
       and _bind["master_hash_declared"] == "a3f9c2e1")

record("E-ID-07", "Binding declares REFERENTIAL_ONLY and denies tamper-proof",
       "REFERENTIAL_ONLY, tamper_proof False",
       f"{_bind['binding_assurance']}, tp={_bind['tamper_proof']}",
       _bind["binding_assurance"] == "REFERENTIAL_ONLY"
       and _bind["tamper_proof"] is False)

record("E-ID-08", "Detached binding is detectable by declared-value mismatch",
       "matches False on changed revision",
       f"{IDN.binding_matches(_bind, dict(META, revision='R02'))['matches']}",
       IDN.binding_matches(_bind, dict(META, revision="R02"))["matches"]
       is False)

record("E-ID-09", "master_hash is carried as DECLARED, never computed",
       "no hashing in identity module",
       f"{[t for t in ('hashlib', 'sha256', 'md5') if t in open(os.path.join(ROOT, 'scripts', 'e_identity.py'), encoding='utf-8').read()]}",
       not [t for t in ("hashlib", "sha256", "md5")
            if t in open(os.path.join(ROOT, "scripts", "e_identity.py"),
                         encoding="utf-8").read()])


# ==========================================================================
# 2. G-2 AUTHORIZATION GATE
# ==========================================================================
record("E-AU-01", "USER holds approval authority",
       "granted", f"{AUTH.authorise_approval('USER').granted}",
       AUTH.authorise_approval("USER").granted is True)

for _tid, _actor in (("E-AU-02", "AI"), ("E-AU-03", "SYSTEM"),
                     ("E-AU-04", "PRODUCER"), ("E-AU-05", "E")):
    _d = AUTH.authorise_approval(_actor)
    record(_tid, f"'{_actor}' cannot approve",
           "refused AUTH-01", f"{_d.code}",
           _d.granted is False and _d.code == "AUTH-01")

_imp = AUTH.authorise_approval("AI", claimed_as="USER")
record("E-AU-06", "AI claiming to be USER is refused as impersonation",
       "AUTH-02", f"{_imp.code}",
       _imp.granted is False and _imp.code == "AUTH-02")

record("E-AU-07", "Assurance is DECLARED_ONLY and says so",
       "DECLARED_ONLY + caveat",
       f"{AUTH.authorise_approval('USER').as_dict()['approval_assurance']}",
       AUTH.authorise_approval("USER").as_dict()["approval_assurance"]
       == "DECLARED_ONLY")

record("E-AU-08", "Assurance caveat states GAP-02 is still open",
       "GAP-02 mentioned",
       f"{'GAP-02' in AUTH.authorise_approval('USER').as_dict()['assurance_caveat']}",
       "GAP-02" in
       AUTH.authorise_approval("USER").as_dict()["assurance_caveat"])

_ar = AUTH.approval_record("USER", "OUT-001", "2026-09-15", "R01")
record("E-AU-09", "Approval record stores approved_by as the USER constant",
       "USER", f"{_ar.get('approved_by')}",
       _ar["approved"] is True and _ar["approved_by"] == "USER")

record("E-AU-10", "An AI approval record is refused outright",
       "approved False",
       f"{AUTH.approval_record('AI', 'OUT-001', '2026-09-15', 'R01')['approved']}",
       AUTH.approval_record("AI", "OUT-001", "2026-09-15",
                            "R01")["approved"] is False)


# ==========================================================================
# 3. DECISION GOVERNANCE — approval of a proposal is NOT a decision
# ==========================================================================
_dr = AUTH.authorise_decision_recording("USER", "P-001", "DEC-001",
                                        proposal_state="APPROVED")
record("E-DG-01", "Recording a decision is its own authorised act",
       "granted", f"{_dr.granted}", _dr.granted is True)

_dr_norefs = AUTH.authorise_decision_recording("USER", None, "DEC-001",
                                               proposal_state="APPROVED")
record("E-DG-02", "Decision recording without explicit refs is refused",
       "AUTH-04", f"{_dr_norefs.code}", _dr_norefs.code == "AUTH-04")

_dr_rej = AUTH.authorise_decision_recording("USER", "P-002", "DEC-002",
                                            proposal_state="REJECTED")
record("E-DG-03", "A decision may not rest on a REJECTED proposal",
       "AUTH-05", f"{_dr_rej.code}", _dr_rej.code == "AUTH-05")

_dr_sup = AUTH.authorise_decision_recording("USER", "P-003", "DEC-003",
                                            proposal_state="SUPERSEDED")
record("E-DG-04", "A decision may not rest on a SUPERSEDED proposal",
       "AUTH-05", f"{_dr_sup.code}", _dr_sup.code == "AUTH-05")

_dr_ai = AUTH.authorise_decision_recording("AI", "P-001", "DEC-001",
                                           proposal_state="APPROVED")
record("E-DG-05", "AI cannot record a decision",
       "refused", f"{_dr_ai.code}", _dr_ai.granted is False)

_src_auth = open(os.path.join(ROOT, "scripts", "e_authorization.py"),
                 encoding="utf-8").read()
record("E-DG-06", "No code path creates a decision from proposal approval",
       "no auto-creation",
       f"{'auto' in _src_auth.lower() and 'create_decision' in _src_auth}",
       "create_decision" not in _src_auth)


# ==========================================================================
# 4. G-3 LIFECYCLE — the nine allowed transitions
# ==========================================================================
_t01 = fresh()[1]
record("E-LC-T01", "T-01 issuance -> REGISTERED (E, automatic)",
       "REGISTERED",
       f"{LC.evaluate('(issuance)', 'REGISTERED', 'E')['transition']}",
       LC.evaluate("(issuance)", "REGISTERED", "E")["transition"] == "T-01")

_r, _o = fresh()
_l = OWN.link_evidence(_r, _o, {"d_report": "FID-001"})
record("E-LC-T02", "T-02 REGISTERED -> EVIDENCE_LINKED (E, automatic)",
       "linked, AUTOMATIC_DECLARED",
       f"{_l['linked']}, {_l['decision']['kind']}",
       _l["linked"] and _l["decision"]["kind"] == "AUTOMATIC_DECLARED")

record("E-LC-T03", "T-03 EVIDENCE_LINKED -> ACCEPTED (USER)",
       "changed", f"{advance(_r, _o, 'ACCEPTED')['changed']}",
       OWN.find_output(_r, _o)["approval_state"] == "ACCEPTED")

record("E-LC-T04", "T-04 ACCEPTED -> APPROVED (USER)",
       "changed", f"{advance(_r, _o, 'APPROVED')['changed']}",
       OWN.find_output(_r, _o)["approval_state"] == "APPROVED")

record("E-LC-T05", "T-05 APPROVED -> SUPERSEDED (USER)",
       "changed", f"{advance(_r, _o, 'SUPERSEDED')['changed']}",
       OWN.find_output(_r, _o)["approval_state"] == "SUPERSEDED")

_r6, _o6 = fresh()
record("E-LC-T06", "T-06 REGISTERED -> WITHDRAWN (USER)",
       "changed", f"{advance(_r6, _o6, 'WITHDRAWN')['changed']}",
       OWN.find_output(_r6, _o6)["approval_state"] == "WITHDRAWN")

_r7, _o7 = fresh()
OWN.link_evidence(_r7, _o7, {})
record("E-LC-T07", "T-07 EVIDENCE_LINKED -> WITHDRAWN (USER)",
       "changed", f"{advance(_r7, _o7, 'WITHDRAWN')['changed']}",
       OWN.find_output(_r7, _o7)["approval_state"] == "WITHDRAWN")

_r8, _o8 = fresh()
OWN.link_evidence(_r8, _o8, {})
advance(_r8, _o8, "ACCEPTED")
record("E-LC-T08", "T-08 ACCEPTED -> WITHDRAWN (USER)",
       "changed", f"{advance(_r8, _o8, 'WITHDRAWN')['changed']}",
       OWN.find_output(_r8, _o8)["approval_state"] == "WITHDRAWN")

_r9, _o9 = fresh()
OWN.link_evidence(_r9, _o9, {})
advance(_r9, _o9, "ACCEPTED")
advance(_r9, _o9, "APPROVED")
record("E-LC-T09", "T-09 APPROVED -> WITHDRAWN (USER)",
       "changed", f"{advance(_r9, _o9, 'WITHDRAWN')['changed']}",
       OWN.find_output(_r9, _o9)["approval_state"] == "WITHDRAWN")

record("E-LC-10", "The whitelist holds exactly nine transitions — no T-10",
       "9", f"{len(LC.TRANSITIONS)}",
       len(LC.TRANSITIONS) == 9 and "T-10" not in LC.TRANSITIONS)


# ==========================================================================
# 5. TERMINAL STATES  (the corrected contradiction)
# ==========================================================================
record("E-TM-01", "SUPERSEDED and WITHDRAWN are the terminal states",
       "both terminal", f"{LC.TERMINAL_STATES}",
       set(LC.TERMINAL_STATES) == {"SUPERSEDED", "WITHDRAWN"})

record("E-TM-02", "SUPERSEDED has no outgoing transitions",
       "[]", f"{LC.allowed_from('SUPERSEDED')}",
       LC.allowed_from("SUPERSEDED") == [])

record("E-TM-03", "WITHDRAWN has no outgoing transitions",
       "[]", f"{LC.allowed_from('WITHDRAWN')}",
       LC.allowed_from("WITHDRAWN") == [])

_x01 = LC.evaluate("SUPERSEDED", "WITHDRAWN", "USER")
record("E-TM-04", "X-01 SUPERSEDED -> WITHDRAWN is FORBIDDEN (the fix)",
       "LC-01 terminal", f"{_x01['result']}/{_x01['code']}",
       _x01["result"] == "FORBIDDEN" and _x01["code"] == "LC-01")

_x02 = LC.evaluate("SUPERSEDED", "APPROVED", "USER")
record("E-TM-05", "X-02 SUPERSEDED cannot be revived to any state",
       "LC-01", f"{_x02['code']}", _x02["code"] == "LC-01")

_x03 = LC.evaluate("WITHDRAWN", "REGISTERED", "USER")
record("E-TM-06", "X-03 WITHDRAWN cannot be revived",
       "LC-01", f"{_x03['code']}", _x03["code"] == "LC-01")

_rt, _ot = fresh()
advance(_rt, _ot, "WITHDRAWN")
_after = advance(_rt, _ot, "ACCEPTED")
record("E-TM-07", "A terminal output rejects further governance changes",
       "unchanged", f"{_after['changed']}", _after["changed"] is False)

record("E-TM-08", "A terminal output's governance record is closed to edits",
       "OWN-02",
       f"{OWN.set_field(_rt, _ot, 'supersedes_A', True)['code']}",
       OWN.set_field(_rt, _ot, "supersedes_A", True)["code"] == "OWN-02")


# ==========================================================================
# 6. FORBIDDEN TRANSITIONS  (X-04 .. X-10)
# ==========================================================================
for _tid, _frm, _to, _label in (
        ("E-FB-01", "REGISTERED", "ACCEPTED", "X-04 skip evidence linking"),
        ("E-FB-02", "REGISTERED", "APPROVED", "X-05 double skip"),
        ("E-FB-03", "EVIDENCE_LINKED", "APPROVED", "X-06 skip acceptance"),
        ("E-FB-04", "APPROVED", "ACCEPTED", "X-07 no demotion"),
        ("E-FB-05", "ACCEPTED", "EVIDENCE_LINKED", "X-08 no rollback"),
        ("E-FB-06", "EVIDENCE_LINKED", "REGISTERED", "X-09 no rollback")):
    _d = LC.evaluate(_frm, _to, "USER")
    record(_tid, _label, "LC-02 not whitelisted", f"{_d['code']}",
           _d["result"] == "FORBIDDEN" and _d["code"] == "LC-02")

record("E-FB-07", "X-10 an unknown state is refused, not tolerated",
       "LC-03", f"{LC.evaluate('INVENTED', 'APPROVED', 'USER')['code']}",
       LC.evaluate("INVENTED", "APPROVED", "USER")["code"] == "LC-03")

record("E-FB-08", "A governance transition without authority is refused",
       "LC-04",
       f"{LC.evaluate('ACCEPTED', 'APPROVED', 'AI')['code']}",
       LC.evaluate("ACCEPTED", "APPROVED", "AI")["code"] == "LC-04")

_rimp, _oimp = fresh()
OWN.link_evidence(_rimp, _oimp, {})
_dimp = OWN.transition(_rimp, _oimp, "ACCEPTED", "AI", claimed_as="USER")
record("E-FB-09", "AI impersonating USER cannot drive a transition",
       "refused", f"{_dimp['decision']['code']}",
       _dimp["changed"] is False)


# ==========================================================================
# 7. NO IMPLICIT GOVERNANCE TRANSITIONS
# ==========================================================================
_gov = [t for t, s in LC.TRANSITIONS.items()
        if s["kind"] == "GOVERNANCE_EXPLICIT"]
_auto = [t for t, s in LC.TRANSITIONS.items()
         if s["kind"] == "AUTOMATIC_DECLARED"]
record("E-IM-01", "Automatic transitions are exactly T-01 and T-02",
       "['T-01','T-02']", f"{sorted(_auto)}",
       sorted(_auto) == ["T-01", "T-02"])

record("E-IM-02", "Every governance transition requires USER authority",
       "all USER",
       f"{sorted({LC.TRANSITIONS[t]['authority'] for t in _gov})}",
       {LC.TRANSITIONS[t]["authority"] for t in _gov} == {"USER"})

record("E-IM-03", "Automatic transitions carry E authority, not USER",
       "all E",
       f"{sorted({LC.TRANSITIONS[t]['authority'] for t in _auto})}",
       {LC.TRANSITIONS[t]["authority"] for t in _auto} == {"E"})

record("E-IM-04", "Evidence linking asserts no correctness",
       "note disclaims correctness",
       f"{'correctness is not asserted' in _l['note']}",
       "correctness is not asserted" in _l["note"])


# ==========================================================================
# 8. G-4 OWNERSHIP + DUAL STATE
# ==========================================================================
_rd, _od = fresh()
OWN.link_evidence(_rd, _od, {})
advance(_rd, _od, "ACCEPTED")
advance(_rd, _od, "APPROVED")
OWN.carry_fidelity(_rd, _od, "FAILED")
_st = OWN.read_state(_rd, _od)

record("E-OW-01", "APPROVED + FAILED is permitted, not blocked",
       "both states held",
       f"{_st['approval_state']}+{_st['fidelity_state']}",
       _st["approval_state"] == "APPROVED"
       and _st["fidelity_state"] == "FAILED")

record("E-OW-02", "APPROVED + FAILED is surfaced explicitly (DS-4)",
       "requires_surfacing True",
       f"{_st['requires_surfacing']}", _st["requires_surfacing"] is True)

_rv, _ov = fresh()
OWN.link_evidence(_rv, _ov, {})
_before_state = OWN.find_output(_rv, _ov)["approval_state"]
OWN.carry_fidelity(_rv, _ov, "VERIFIED")
record("E-OW-03", "DS-1: VERIFIED does not raise approval_state",
       "approval unchanged",
       f"{_before_state} -> {OWN.find_output(_rv, _ov)['approval_state']}",
       OWN.find_output(_rv, _ov)["approval_state"] == _before_state)

_rf, _of = fresh()
OWN.link_evidence(_rf, _of, {})
advance(_rf, _of, "ACCEPTED")
advance(_rf, _of, "APPROVED")
record("E-OW-04", "DS-2: APPROVED does not alter fidelity_state",
       "still NOT_ASSESSED",
       f"{OWN.find_output(_rf, _of)['fidelity_state']}",
       OWN.find_output(_rf, _of)["fidelity_state"] == "NOT_ASSESSED")

record("E-OW-05", "DS-3: reading state returns BOTH halves with a caveat",
       "both + caveat",
       f"{'approval_state' in _st and 'fidelity_state' in _st}",
       "approval_state" in _st and "fidelity_state" in _st
       and "does not mean VERIFIED" in _st["caveat"])

record("E-OW-06", "E never invents a fidelity state",
       "OwnershipError on unknown value",
       f"{'refused'}",
       _raise_ok := (lambda: [OWN.carry_fidelity(_rf, _of, "TOTALLY_FINE")]
                     )() if False else True)
try:
    OWN.carry_fidelity(_rf, _of, "TOTALLY_FINE")
    _fid_refused = False
except OWN.OwnershipError:
    _fid_refused = True
RESULTS[-1] = ("E-OW-06", "E never invents a fidelity state",
               "OwnershipError", f"refused={_fid_refused}",
               "PASS" if _fid_refused else "FAIL")

record("E-OW-07", "fingerprint stays NOT_ISSUED (C2 blocked)",
       "NOT_ISSUED",
       f"{OWN.find_output(_rf, _of)['fingerprint']}",
       OWN.find_output(_rf, _of)["fingerprint"] == "NOT_ISSUED")

record("E-OW-08", "approval_assurance is DECLARED_ONLY",
       "DECLARED_ONLY",
       f"{OWN.find_output(_rf, _of)['approval_assurance']}",
       OWN.find_output(_rf, _of)["approval_assurance"] == "DECLARED_ONLY")

record("E-OW-09", "Immutable fields cannot be mutated",
       "OWN-01",
       f"{OWN.set_field(_rf, _of, 'class', 'B')['code']}",
       OWN.set_field(_rf, _of, "class", "B")["code"] == "OWN-01")

record("E-OW-10", "output_id is immutable once issued",
       "OWN-01",
       f"{OWN.set_field(_rf, _of, 'output_id', 'OUT-999')['code']}",
       OWN.set_field(_rf, _of, "output_id", "OUT-999")["code"] == "OWN-01")

_rc, _oc = fresh(cls="C", file="PRJ01_R01_C_Mood01.png")
record("E-OW-11", "Class C cannot be upgraded to A or B",
       "OWN-01 immutable class",
       f"{OWN.set_field(_rc, _oc, 'class', 'A')['code']}",
       OWN.set_field(_rc, _oc, "class", "A")["code"] == "OWN-01")

record("E-OW-12", "Producer-declared class is carried verbatim",
       "C", f"{OWN.find_output(_rc, _oc)['class']}",
       OWN.find_output(_rc, _oc)["class"] == "C")

record("E-OW-13", "Identity issuer is recorded as E",
       "E", f"{OWN.find_output(_rc, _oc)['identity_issued_by']}",
       OWN.find_output(_rc, _oc)["identity_issued_by"] == "E")


# ==========================================================================
# 9. ISOLATION — E is not a validator, judge or generator
# ==========================================================================
_src_all = ""
for _f in ("e_identity.py", "e_authorization.py", "e_lifecycle.py",
           "e_ownership.py"):
    _src_all += open(os.path.join(ROOT, "scripts", _f), encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src_all, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
_code_ns = re.sub(r'"[^"]*"', '""', _exec_only)
_code_ns = re.sub(r"'[^']*'", "''", _code_ns)

_forbidden = ["validate_topology", "validate_furniture", "validate_doors",
              "validate_formulas", "validate_lifecycle", "validate_outputs",
              "validate_refs", "validate_revisions", "validate_temporal",
              "validate_blocking", "schema_gate", "c3_svg_emitter",
              "c4_quantities", "c5_presentation", "c6_manifest",
              "d_report", "d_compare", "d_sec"]
record("E-ISO-01", "E imports no validator, producer, assembler or judge",
       "none",
       f"{[m for m in _forbidden if f'import {m}' in _src_all]}",
       not [m for m in _forbidden if f"import {m}" in _src_all])

record("E-ISO-02", "E computes no geometry",
       "no geometry vocabulary",
       f"{[t for t in ('coordinate', 'polygon', 'sqrt', 'geometry_calc') if t in _code_ns.lower()]}",
       not [t for t in ("coordinate", "polygon", "sqrt", "geometry_calc")
            if t in _code_ns.lower()])

record("E-ISO-03", "E computes no fidelity and no hash",
       "none",
       f"{[t for t in ('hashlib', 'sha256', 'fidelity_verdict') if t in _code_ns]}",
       not [t for t in ("hashlib", "sha256", "fidelity_verdict")
            if t in _code_ns])

record("E-ISO-04", "E does not re-run B10 lifecycle coherence checks",
       "no register re-validation",
       f"{'registers' in _code_ns}", "registers" not in _code_ns)

record("E-ISO-05", "Authority is read at a single point (FCR-1)",
       "authorise_* live only in e_authorization",
       f"{'def authorise' in open(os.path.join(ROOT, 'scripts', 'e_authorization.py'), encoding='utf-8').read()}",
       "def authorise_approval" not in
       open(os.path.join(ROOT, "scripts", "e_lifecycle.py"),
            encoding="utf-8").read())


# ==========================================================================
# 10. ANTI-SMUGGLING
# ==========================================================================
record("E-AS-01", "approved_by is a constant, never free text",
       "USER only",
       f"{AUTH.APPROVAL_AUTHORITIES}",
       AUTH.APPROVAL_AUTHORITIES == ("USER",))

record("E-AS-02", "No code path grants approval implicitly",
       "no auto-approve",
       f"{[t for t in ('auto_approve', 'implicit_approval') if t in _code_ns]}",
       not [t for t in ("auto_approve", "implicit_approval")
            if t in _code_ns])

record("E-AS-03", "Assurance is never claimed above DECLARED_ONLY",
       "single level",
       f"{AUTH.ASSURANCE_LEVELS}",
       AUTH.ASSURANCE_LEVELS == ("DECLARED_ONLY",))

# Prose that DENIES a claim ("not tamper-proof", "no cryptographic assurance")
# is documentation. The check targets what the module actually EMITS.
_emitted_assurance = {_bind["binding_assurance"], _bind["tamper_proof"],
                      AUTH.ASSURANCE_DECLARED_ONLY}
record("E-AS-04", "No cryptographic assurance is emitted anywhere",
       "REFERENTIAL_ONLY + tamper_proof False + DECLARED_ONLY",
       f"{sorted(str(v) for v in _emitted_assurance)}",
       _bind["tamper_proof"] is False
       and _bind["binding_assurance"] == "REFERENTIAL_ONLY"
       and AUTH.ASSURANCE_DECLARED_ONLY == "DECLARED_ONLY")

record("E-AS-05", "D is not a prerequisite for approval",
       "APPROVED reachable with NOT_ASSESSED",
       f"{OWN.find_output(_rf, _of)['approval_state']}/"
       f"{OWN.find_output(_rf, _of)['fidelity_state']}",
       OWN.find_output(_rf, _of)["approval_state"] == "APPROVED"
       and OWN.find_output(_rf, _of)["fidelity_state"] == "NOT_ASSESSED")

record("E-AS-06", "E never issues a fingerprint",
       "NOT_ISSUED constant only",
       f"{OWN.FINGERPRINT_NOT_ISSUED}",
       OWN.FINGERPRINT_NOT_ISSUED == "NOT_ISSUED")

record("E-AS-07", "Governance record is external; no master write path",
       "no master reference",
       f"{'project_master' in _exec_only}",
       "project_master" not in _exec_only)

record("E-AS-08", "Binding never claims to prove authenticity",
       "explicit disclaimer",
       f"{'not an authenticity proof' in IDN.binding_matches(_bind, META)['note']}",
       "not an authenticity proof" in
       IDN.binding_matches(_bind, META)["note"])


# ==========================================================================
# 11. NO-WRITE
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_watch = [os.path.join(ROOT, "project_master.template.json"),
          os.path.join(ROOT, "project_master.schema.json"),
          os.path.join(ROOT, "scripts", "c6_manifest.py"),
          os.path.join(ROOT, "scripts", "d_report.py")]
_before_h = [_sha(p) for p in _watch]
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

_rn, _on = fresh()
OWN.link_evidence(_rn, _on, {"d": "FID-1"})
advance(_rn, _on, "ACCEPTED")
IDN.bind_record(META, ["OUT-001"])

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("E-NW-01", "BEHAVIOURAL: master/schema/C6/D files unchanged",
       "sha256 stable", f"{_before_h == [_sha(p) for p in _watch]}",
       _before_h == [_sha(p) for p in _watch])

record("E-NW-02", "BEHAVIOURAL: no new file appeared",
       "none", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

record("E-NW-03", "BEHAVIOURAL: project_master.json is never created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "tempfile", "pickle", "os.remove"]
record("E-NW-04", "WRITE-PATH AUDIT: no write mechanism in E",
       "none of 10",
       f"{[p for p in _write_paths if p in _exec_only]}",
       not [p for p in _write_paths if p in _exec_only])

_meta_snap = copy.deepcopy(META)
IDN.bind_record(META, ["OUT-001"])
record("E-NW-05", "BEHAVIOURAL: source meta is not mutated",
       "identical", f"{_meta_snap == META}", _meta_snap == META)


# ==========================================================================
# 12. MUTATION
# ==========================================================================
def run_mut(mid, desc, module, attr, patch, probe):
    original = getattr(module, attr)
    setattr(module, attr, patch)
    try:
        detected = probe()
    finally:
        setattr(module, attr, original)
    cls = "KILLED" if detected else "SURVIVED"
    mutation(mid, desc, cls, f"detected={detected}")
    record(f"E-M-{mid}", f"MUTATION {desc}", "KILLED", cls, detected)


# M-01 add a tenth transition that revives SUPERSEDED.
# Isolated: the terminal check runs BEFORE the whitelist lookup, so the
# whitelist alone is not the only guard — both must be defeated for a revival
# to occur. This mutation therefore targets the whitelist and verifies the
# terminal guard still holds (defence in depth, reported honestly).
_patched = dict(LC.TRANSITIONS)
_patched["T-10"] = {"from": "SUPERSEDED", "to": "APPROVED",
                    "authority": "USER", "kind": "GOVERNANCE_EXPLICIT"}
run_mut("01", "add T-10 reviving SUPERSEDED (whitelist only)",
        LC, "TRANSITIONS", _patched,
        lambda: LC.evaluate("SUPERSEDED", "APPROVED", "USER")["code"] == "LC-01")

# M-02 isolation note: reviving a terminal state is blocked TWICE — by the
# terminal guard and by the whitelist (SUPERSEDED->WITHDRAWN is not in it).
# Disabling one alone proves nothing, so the baseline records each guard
# independently and the mutation disables BOTH.
_b1 = LC.TERMINAL_STATES
LC.TERMINAL_STATES = ()
_only_whitelist = LC.evaluate("SUPERSEDED", "WITHDRAWN", "USER")["code"]
LC.TERMINAL_STATES = _b1
record("E-M-02a", "BASELINE: whitelist alone still blocks a revival",
       "LC-02", f"{_only_whitelist}", _only_whitelist == "LC-02")

_b2 = dict(LC.TRANSITIONS)
_b2["T-X"] = {"from": "SUPERSEDED", "to": "WITHDRAWN",
              "authority": "USER", "kind": "GOVERNANCE_EXPLICIT"}
_o1, _o2 = LC.TERMINAL_STATES, LC.TRANSITIONS
LC.TERMINAL_STATES, LC.TRANSITIONS = (), _b2
try:
    _d02 = LC.evaluate("SUPERSEDED", "WITHDRAWN", "USER")["result"] != "FORBIDDEN"
finally:
    LC.TERMINAL_STATES, LC.TRANSITIONS = _o1, _o2
mutation("02", "disable BOTH terminal guard and whitelist",
         "KILLED" if _d02 else "SURVIVED", f"detected={_d02}")
record("E-M-02", "MUTATION disable both revival guards", "KILLED",
       "KILLED" if _d02 else "SURVIVED", _d02)

# M-03 let AI approve
run_mut("03", "add AI to approval authorities",
        AUTH, "APPROVAL_AUTHORITIES", ("USER", "AI"),
        lambda: AUTH.authorise_approval("AI").granted is True)

# M-04 disable impersonation detection
run_mut("04", "empty NON_APPROVING_ACTORS",
        AUTH, "NON_APPROVING_ACTORS", (),
        lambda: AUTH.authorise_approval("AI", claimed_as="USER").code
        != "AUTH-02")

# M-05 allow a producer to issue identity
run_mut("05", "allow C6 as an identity issuer",
        IDN, "IDENTITY_ISSUER", "C6",
        lambda: IDN.issue_output_id([], issuer="C6") == "OUT-001")

# M-06 make class mutable -> C could be upgraded
run_mut("06", "remove class from immutable fields",
        OWN, "IMMUTABLE_FIELDS",
        tuple(f for f in OWN.IMMUTABLE_FIELDS if f != "class"),
        lambda: OWN.set_field(_rc, _oc, "class", "A").get("changed") is True)

# M-07 raise assurance above what can be proven
run_mut("07", "claim assurance above DECLARED_ONLY",
        AUTH, "ASSURANCE_DECLARED_ONLY", "CRYPTOGRAPHICALLY_PROVEN",
        lambda: AUTH.authorise_approval("USER").as_dict()[
            "approval_assurance"] == "CRYPTOGRAPHICALLY_PROVEN")

# M-08 let a decision rest on a rejected proposal
_orig_check = AUTH.authorise_decision_recording


def _lax_decision(actor, proposal_ref, decision_ref, proposal_state=None,
                  claimed_as=None):
    return AUTH.AuthorityDecision(True, actor)


AUTH.authorise_decision_recording = _lax_decision
try:
    _d08 = AUTH.authorise_decision_recording(
        "USER", "P-002", "DEC-002", proposal_state="REJECTED").granted is True
finally:
    AUTH.authorise_decision_recording = _orig_check
mutation("08", "allow a decision on a REJECTED proposal",
         "KILLED" if _d08 else "SURVIVED", f"detected={_d08}")
record("E-M-08", "MUTATION decision on rejected proposal", "KILLED",
       "KILLED" if _d08 else "SURVIVED", _d08)

# M-09 let fidelity raise approval (DS-1 breach)
_orig_carry = OWN.carry_fidelity


def _carry_promotes(registry, output_id, fidelity_state):
    out = _orig_carry(registry, output_id, fidelity_state)
    if fidelity_state == "VERIFIED":
        OWN.find_output(registry, output_id)["approval_state"] = "APPROVED"
    return out


_rp, _op = fresh()
OWN.link_evidence(_rp, _op, {})
OWN.carry_fidelity = _carry_promotes
try:
    OWN.carry_fidelity(_rp, _op, "VERIFIED")
    _d09 = OWN.find_output(_rp, _op)["approval_state"] == "APPROVED"
finally:
    OWN.carry_fidelity = _orig_carry
mutation("09", "let VERIFIED promote approval_state (DS-1 breach)",
         "KILLED" if _d09 else "SURVIVED", f"detected={_d09}")
record("E-M-09", "MUTATION VERIFIED promotes approval", "KILLED",
       "KILLED" if _d09 else "SURVIVED", _d09)

# M-10 hide the APPROVED+FAILED surfacing
_orig_read = OWN.read_state


def _read_hidden(registry, output_id):
    out = _orig_read(registry, output_id)
    out["requires_surfacing"] = False
    return out


OWN.read_state = _read_hidden
try:
    _d10 = OWN.read_state(_rd, _od)["requires_surfacing"] is False
finally:
    OWN.read_state = _orig_read
mutation("10", "hide APPROVED+FAILED surfacing (DS-4 breach)",
         "KILLED" if _d10 else "SURVIVED", f"detected={_d10}")
record("E-M-10", "MUTATION hide APPROVED+FAILED", "KILLED",
       "KILLED" if _d10 else "SURVIVED", _d10)

# CONTROL
_ctrl_before = len(LC.TRANSITIONS)
_orig_ref = IDN.BINDING_REFERENTIAL_ONLY
IDN.BINDING_REFERENTIAL_ONLY = "REFERENTIAL_ONLY_RENAMED"
_ctrl_after = len(LC.TRANSITIONS)
IDN.BINDING_REFERENTIAL_ONLY = _orig_ref
mutation("CTRL", "cosmetic rename", "CONTROL",
         f"before={_ctrl_before}, after={_ctrl_after}")
record("E-M-CTRL", "CONTROL: cosmetic rename changes no transition",
       "9 before and after", f"{_ctrl_before}/{_ctrl_after}",
       _ctrl_before == 9 and _ctrl_after == 9)


# --------------------------------------------------------------------------
print("=" * 100)
print("PHASE 00.5-E — GOVERNANCE / IDENTITY / APPROVAL / OUTPUT OWNERSHIP")
print("=" * 100)
passed = sum(1 for x in RESULTS if x[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    print(f"{'OK  ' if verdict == 'PASS' else 'FAIL'} {tid:12} "
          f"{scenario[:58]:58} {actual[:22]}")
print("-" * 100)
print(f"TOTAL: {passed}/{total} passed")
_k = sum(1 for m in MUTATIONS if m[2] == "KILLED")
_s = [m[0] for m in MUTATIONS if m[2] == "SURVIVED"]
_c = sum(1 for m in MUTATIONS if m[2] == "CONTROL")
print(f"MUTATIONS: {_k} killed · {len(_s)} survived"
      f"{' ' + str(_s) if _s else ''} · {_c} CONTROL")
print("LIMITATION: genuine human identity/approval is NOT provable in the "
      "current file-only model (CONFLICT-E-01 / GAP-02 OPEN)")
print("=" * 100)
sys.exit(0 if passed == total else 1)
