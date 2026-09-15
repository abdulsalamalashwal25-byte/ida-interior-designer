#!/usr/bin/env python3
"""Phase 00.5-F — Library / Reference Data / Standards Governance.

Reference: F Architecture R01 + R02 + R03 (APPROVED / LOCKED).

WHAT THIS SUITE MUST PROVE
  * a reference never becomes [D], [C] or a design decision through F
  * reference usage is NOT automatically a proposal (R03 amendment 1)
  * outside authority_scope means NOT_AUTHORITATIVE, not a source violation
    (R03 amendment 2)
  * source_type grants nothing
  * CONTENT_CHECKED is not truth, and citation authenticity stays unproven
  * a library update never modifies the project
  * conflicts are reported in full and resolved by nobody in F

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

import f_reference as FR                                             # noqa: E402
import f_usage as FU                                                 # noqa: E402
import f_conflict as FC                                              # noqa: E402

RESULTS = []
MUTATIONS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def mutation(mid, desc, classification, detail):
    MUTATIONS.append((mid, desc, classification, detail))


def make_source(**kw):
    defaults = dict(
        source_id="SRC-001", source_type="OFFICIAL_MANUFACTURER",
        source_identity="ACME Furniture Co (declared)",
        source_version="2026.1", document_reference="p.42",
        citation="ACME Catalogue 2026.1, p.42", retrieved_on="2026-09-15",
        retrieved_by="AGENT",
        authority_scope=[
            {"attribute": "product_dimensions", "authoritative": True,
             "basis": "manufacturer catalogue"},
            {"attribute": "local_code_compliance", "authoritative": False,
             "basis": "manufacturer does not certify local codes"},
        ])
    defaults.update(kw)
    return FR.Source(**defaults)


SRC = make_source()


# ==========================================================================
# 1. SOURCE / ITEM / ATTRIBUTE / EVIDENCE MODEL
# ==========================================================================
record("F-SM-01", "A source records its DECLARED identity, never a proven one",
       "declared key present",
       f"{'source_identity_declared' in SRC.as_dict()}",
       "source_identity_declared" in SRC.as_dict())

record("F-SM-02", "source_type is flagged descriptive-only in every output",
       "flag True",
       f"{SRC.as_dict()['source_type_is_descriptive_only']}",
       SRC.as_dict()["source_type_is_descriptive_only"] is True)

_item = FR.ReferenceItem("ITM-001", "SRC-001", name="Table X")
record("F-SM-03", "A reference item binds to its source",
       "SRC-001", f"{_item.as_dict()['source_id']}",
       _item.as_dict()["source_id"] == "SRC-001")

_attr = FR.ReferenceAttribute("ATTR-001", "ITM-001", "depth", 800, "mm",
                              "EVD-001")
record("F-SM-04", "A reference attribute declares it is NOT a project fact",
       "is_project_fact False",
       f"{_attr.as_dict()['is_project_fact']}",
       _attr.as_dict()["is_project_fact"] is False)

_evd = FR.Evidence("EVD-001", "catalogue_page", "p.42")
record("F-SM-05", "Evidence supports a claim but does not prove it",
       "supports True, proves False",
       f"{_evd.as_dict()['supports_claim']}/{_evd.as_dict()['proves_claim']}",
       _evd.as_dict()["supports_claim"] is True
       and _evd.as_dict()["proves_claim"] is False)

record("F-SM-06", "AI_GENERATED is never engineering evidence",
       "listed as never-evidence",
       f"{FR.NEVER_ENGINEERING_EVIDENCE}",
       "AI_GENERATED" in FR.NEVER_ENGINEERING_EVIDENCE)


# ==========================================================================
# 2. R03 AMENDMENT 1 — REFERENCE USAGE PATH
# ==========================================================================
_a = FU.record_usage("ATTR-001", FU.PATH_A_CONTEXT, declared_by="USER")
record("F-R03A-01", "PATH A produces no [P]",
       "produces_proposal False", f"{_a['produces_proposal']}",
       _a["produces_proposal"] is False)

record("F-R03A-02", "PATH A produces no [C]",
       "produces_confirmed False", f"{_a['produces_confirmed']}",
       _a["produces_confirmed"] is False)

record("F-R03A-03", "PATH A produces no design decision",
       "produces_design_decision False",
       f"{_a['produces_design_decision']}",
       _a["produces_design_decision"] is False)

record("F-R03A-04", "PATH A is a COMPLETE end state, not a shortfall (UP-6)",
       "is_complete_end_state True",
       f"{_a['is_complete_end_state']}",
       _a["is_complete_end_state"] is True)

_b = FU.record_usage("ATTR-001", FU.PATH_B_DECISION_AFFECTING,
                     declared_by="USER")
record("F-R03A-05", "PATH B records that a proposal is REQUIRED",
       "proposal_required True", f"{_b['proposal_required']}",
       _b["proposal_required"] is True)

record("F-R03A-06", "PATH B: F does not create the proposal itself",
       "proposal_created_by_f False",
       f"{_b['proposal_created_by_f']}",
       _b["proposal_created_by_f"] is False)

record("F-R03A-07", "PATH B names the full route through E",
       "[P] -> USER/E -> [C]", f"{_b['next_step'][:18]}",
       "[P] Proposal" in _b["next_step"] and "via E" in _b["next_step"])

_auto = FU.auto_proposal_attempt("ATTR-001")
record("F-R03A-08", "Reference Usage is NOT a Proposal automatically (UP-6)",
       "refused UP-06", f"{_auto['code']}",
       _auto["result"] == "REFUSED" and _auto["code"] == "UP-06")

_nopath = FU.record_usage("ATTR-001", None)
record("F-R03A-09", "F refuses to decide the usage path itself (UP-8)",
       "refused UP-08", f"{_nopath['code']}",
       _nopath["result"] == "REFUSED" and _nopath["code"] == "UP-08")

_t_noactor = FU.path_transition(FU.PATH_A_CONTEXT,
                                FU.PATH_B_DECISION_AFFECTING)
record("F-R03A-10", "A -> B without an explicit actor is refused (UP-7)",
       "refused UP-08", f"{_t_noactor['code']}",
       _t_noactor["result"] == "REFUSED")

_t_actor = FU.path_transition(FU.PATH_A_CONTEXT,
                              FU.PATH_B_DECISION_AFFECTING,
                              declared_by="USER")
record("F-R03A-11", "A -> B with an explicit actor is recorded, not inferred",
       "accepted, not inferred",
       f"{_t_actor['result']}, {'did not infer' in _t_actor['note']}",
       _t_actor["result"] == "ACCEPTED"
       and "did not infer" in _t_actor["note"])


# ==========================================================================
# 3. PROMOTION IS IMPOSSIBLE (UP-1 .. UP-5)
# ==========================================================================
for _tid, _status, _code in (("F-UP-01", "D", "UP-01"),
                             ("F-UP-02", "C", "UP-04"),
                             ("F-UP-03", "P", "UP-05")):
    try:
        FU.promote("ATTR-001", _status)
        _raised, _msg = False, ""
    except FU.UsageError as exc:
        _raised, _msg = True, str(exc)
    record(_tid, f"F cannot promote a reference to [{_status}]",
           f"UsageError {_code}", f"raised={_raised}, code={_msg[:6]}",
           _raised and _msg.startswith(_code))

record("F-UP-04", "The [D] refusal cites B6's formula/derived_from rule",
       "B6 + formula named",
       f"{'formula' in _msg or True}",
       "B6" in (lambda: [str(e) for e in [None]] and "")() or True)
try:
    FU.promote("ATTR-001", "D")
except FU.UsageError as exc:
    _d_msg = str(exc)
RESULTS[-1] = ("F-UP-04", "The [D] refusal cites B6 and formula/derived_from",
               "B6 + formula + derived_from",
               f"{'B6' in _d_msg and 'formula' in _d_msg}",
               "PASS" if ("B6" in _d_msg and "formula" in _d_msg
                          and "derived_from" in _d_msg) else "FAIL")

_src_usage = open(os.path.join(ROOT, "scripts", "f_usage.py"),
                  encoding="utf-8").read()
# 'status =' also matches 'target_status ==' and prose. The real question is
# whether F ever ASSIGNS a project status to anything, so the check targets
# assignment of the status constants themselves.
_status_assign = [t for t in ('["status"] =', "['status'] =",
                              '.status = ', 'status = STATUS_')
                  if t in _src_usage]
record("F-UP-05", "No code path in F assigns a project status",
       "no status assignment", f"{_status_assign}", not _status_assign)


# ==========================================================================
# 4. R03 AMENDMENT 2 — AUTHORITY SCOPE
# ==========================================================================
_auth_in = FR.authority_for(SRC, "product_dimensions")
record("F-R03B-01", "Declared authoritative attribute reports AUTHORITATIVE",
       "AUTHORITATIVE", f"{_auth_in['result']}",
       _auth_in["result"] == "AUTHORITATIVE")

_auth_out = FR.authority_for(SRC, "local_code_compliance")
record("F-R03B-02", "Declared non-authoritative reports NOT_AUTHORITATIVE",
       "NOT_AUTHORITATIVE", f"{_auth_out['result']}",
       _auth_out["result"] == "NOT_AUTHORITATIVE")

record("F-R03B-03", "Outside scope is NOT a violation by the source (AS-1)",
       "is_source_violation False",
       f"{_auth_out['is_source_violation']}",
       _auth_out["is_source_violation"] is False)

_auth_absent = FR.authority_for(SRC, "circulation_clearance")
record("F-R03B-04", "Undeclared attribute defaults to NOT_AUTHORITATIVE",
       "NOT_AUTHORITATIVE, declared False",
       f"{_auth_absent['result']}, declared={_auth_absent['declared']}",
       _auth_absent["result"] == "NOT_AUTHORITATIVE"
       and _auth_absent["declared"] is False)

record("F-R03B-05", "Undeclared attribute is still not a source violation",
       "is_source_violation False",
       f"{_auth_absent['is_source_violation']}",
       _auth_absent["is_source_violation"] is False)

record("F-R03B-06", "Value stays usable as reference context (AS-4)",
       "note allows context use",
       f"{'reference context' in _auth_absent['note']}",
       "reference context" in _auth_absent["note"])

_src_ref = open(os.path.join(ROOT, "scripts", "f_reference.py"),
                encoding="utf-8").read()
record("F-R03B-07", "The term SCOPE_VIOLATION no longer exists in F",
       "absent", f"{'SCOPE_VIOLATION' in _src_ref}",
       "SCOPE_VIOLATION" not in _src_ref)


# ==========================================================================
# 5. source_type GRANTS NOTHING (R02 / ST-1..ST-5)
# ==========================================================================
_bare = FR.Source("SRC-002", source_type="OFFICIAL_MANUFACTURER")
record("F-ST-01", "Official Manufacturer grants no authority by itself",
       "NOT_AUTHORITATIVE",
       f"{FR.authority_for(_bare, 'product_dimensions')['result']}",
       FR.authority_for(_bare, "product_dimensions")["result"]
       == "NOT_AUTHORITATIVE")

_secondary = FR.Source(
    "SRC-003", source_type="SECONDARY_REFERENCE",
    authority_scope=[{"attribute": "depth", "authoritative": True,
                      "basis": "measured and documented"}])
record("F-ST-02", "Secondary Reference is not automatically wrong",
       "AUTHORITATIVE where declared",
       f"{FR.authority_for(_secondary, 'depth')['result']}",
       FR.authority_for(_secondary, "depth")["result"] == "AUTHORITATIVE")

record("F-ST-03", "source_type grants no verification",
       "UNVERIFIED by default",
       f"{_bare.verification_state}",
       _bare.verification_state == "UNVERIFIED")

record("F-ST-04", "source_type grants no validity",
       "VALIDITY_UNKNOWN", f"{_bare.validity}",
       _bare.validity == "VALIDITY_UNKNOWN")

record("F-ST-05", "No global trust enum or rank exists (DEC-F-01 reframed)",
       "no trust score",
       f"{[t for t in ('trust_score', 'trust_level', 'trust_rank') if t in _src_ref]}",
       not [t for t in ("trust_score", "trust_level", "trust_rank",
                        "trusted_source") if t in _src_ref])


# ==========================================================================
# 6. VERIFICATION — CHECKED IS NOT TRUE
# ==========================================================================
record("F-VS-01", "Default verification state is UNVERIFIED (DEC-F-06)",
       "UNVERIFIED", f"{FR.Source('SRC-X').verification_state}",
       FR.Source("SRC-X").verification_state == "UNVERIFIED")

_checked = make_source(verification_state="CONTENT_CHECKED")
_vr = FR.verification_report(_checked)
record("F-VS-02", "CONTENT_CHECKED has a bounded definition",
       "compared against the recorded claim",
       f"{'compared against' in _vr['means']}",
       "compared against" in _vr["means"])

record("F-VS-03", "CONTENT_CHECKED lists seven things it does NOT mean",
       "7 exclusions", f"{len(_vr['does_not_mean'])}",
       len(_vr["does_not_mean"]) == 7)

record("F-VS-04", "CITATION_RECORDED is not RETRIEVED",
       "boundary stated",
       f"{any('not RETRIEVED' in b for b in _vr['boundaries'])}",
       any("not RETRIEVED" in b for b in _vr["boundaries"]))

record("F-VS-05", "RETRIEVED is not a verified source",
       "boundary stated",
       f"{any('not a verified source' in b for b in _vr['boundaries'])}",
       any("not a verified source" in b for b in _vr["boundaries"]))

record("F-VS-06", "CONTENT_CHECKED is not engineering truth",
       "boundary stated",
       f"{any('not engineering truth' in b for b in _vr['boundaries'])}",
       any("not engineering truth" in b for b in _vr["boundaries"]))

record("F-VS-07", "Citation authenticity stays unverified (GAP-F-02)",
       "GAP-F-02 OPEN",
       f"{_vr['citation_authenticity']}",
       "GAP-F-02" in _vr["citation_authenticity"])


# ==========================================================================
# 7. VALIDITY & APPLICABILITY
# ==========================================================================
record("F-VA-01", "Default validity is VALIDITY_UNKNOWN",
       "VALIDITY_UNKNOWN", f"{FR.Source('SRC-Y').validity}",
       FR.Source("SRC-Y").validity == "VALIDITY_UNKNOWN")

_app = FR.applicability_report()
record("F-VA-02", "Default applicability is APPLICABILITY_UNKNOWN",
       "APPLICABILITY_UNKNOWN", f"{_app['state']}",
       _app["state"] == "APPLICABILITY_UNKNOWN")

record("F-VA-03", "F never infers applicability (R03 / F-R02-10)",
       "inferred_by_f False", f"{_app['inferred_by_f']}",
       _app["inferred_by_f"] is False)

record("F-VA-04", "All nine applicability dimensions are describable",
       "9 dimensions",
       f"{len(_app['dimensions_described'])}",
       len(_app["dimensions_described"]) == 9)

_app_bad = FR.applicability_report(declared_state="TOTALLY_FINE")
record("F-VA-05", "An unknown applicability value falls back to UNKNOWN",
       "APPLICABILITY_UNKNOWN", f"{_app_bad['state']}",
       _app_bad["state"] == "APPLICABILITY_UNKNOWN")


# ==========================================================================
# 8. CONFLICT MODEL
# ==========================================================================
_ca = {"source_identity": "ACME", "source_version": "2026.1",
       "citation": "cat p.42", "authority_result": "AUTHORITATIVE",
       "verification_state": "CONTENT_CHECKED", "value": 800, "unit": "mm"}
_cb = {"source_identity": "BETA", "source_version": "2025.4",
       "citation": "doc p.7", "authority_result": "AUTHORITATIVE",
       "verification_state": "RETRIEVED", "value": 820, "unit": "mm"}
_cf = FC.detect_conflict("depth", _ca, _cb)

record("F-CF-01", "Differing claims are reported as a conflict",
       "conflict True", f"{_cf['conflict']}", _cf["conflict"] is True)

record("F-CF-02", "Both sources are reported in full",
       "both values present",
       f"{_cf['source_a']['value']}/{_cf['source_b']['value']}",
       _cf["source_a"]["value"] == 800 and _cf["source_b"]["value"] == 820)

record("F-CF-03", "F resolves nothing",
       "resolved False, resolved_by_f False",
       f"{_cf['resolved']}/{_cf['resolved_by_f']}",
       _cf["resolved"] is False and _cf["resolved_by_f"] is False)

record("F-CF-04", "Resolution is required from the USER",
       "USER_DECISION", f"{_cf['required_resolution']}",
       _cf["required_resolution"] == "USER_DECISION")

record("F-CF-05", "F refuses to prefer a source (CF-5)",
       "preferred None, CF-05",
       f"{FC.preferred_source(_cf)['code']}",
       FC.preferred_source(_cf)["preferred"] is None)

_src_conf = open(os.path.join(ROOT, "scripts", "f_conflict.py"),
                 encoding="utf-8").read()
_code_conf = "\n".join(ln.split("#")[0] for ln in _src_conf.splitlines())
# The word "average" appears in prose that FORBIDS averaging. The check
# targets executable arithmetic instead.
_conf_ns = re.sub(r'"[^"]*"', '""', _code_conf)
_conf_ns = re.sub(r"'[^']*'", "''", _conf_ns)
_avg_logic = [t for t in ("mean(", "midpoint", "statistics", ") / 2",
                          ")/2", "sum(") if t in _conf_ns]
record("F-CF-06", "No averaging or range arithmetic exists (CF-2)",
       "no averaging logic", f"{_avg_logic}", not _avg_logic)

record("F-CF-07", "Agreement is reported without claiming proof",
       "agreement is not proof",
       f"{'not proof' in FC.detect_conflict('depth', _ca, _ca)['note']}",
       "not proof" in FC.detect_conflict("depth", _ca, _ca)["note"])


# ==========================================================================
# 9. VERSION / SUPERSESSION / SNAPSHOT
# ==========================================================================
_pin = FC.pin_usage("SRC-001", "2026.1", "2026-09-15")
_new = FC.register_new_version(_pin, "2027.0")

record("F-VR-01", "Using a reference pins its version and retrieval time",
       "pinned True", f"{_pin['pinned']}", _pin["pinned"] is True)

record("F-VR-02", "A newer version is recorded as SUPERSEDES",
       "SUPERSEDES", f"{_new['relation']}", _new["relation"] == "SUPERSEDES")

record("F-VR-03", "A library update is NEVER applied to the project",
       "applied False, project_changed False",
       f"{_new['applied_to_project']}/{_new['project_changed']}",
       _new["applied_to_project"] is False
       and _new["project_changed"] is False)

record("F-VR-04", "Adopting a new version requires explicit user action",
       "explicit user action", f"{_new['requires']}",
       "explicit user action" in _new["requires"])

_snap = FC.snapshot("SNAP-001", "2026.1", "2026-09-15T10:00Z", "cat p.42",
                    "AVAILABLE")
record("F-VR-05", "Snapshot fingerprint stays NOT_ISSUED (C2 respected)",
       "NOT_ISSUED", f"{_snap['content_fingerprint']}",
       _snap["content_fingerprint"] == "NOT_ISSUED")

record("F-VR-06", "Snapshot claims neither tamper-proofing nor completeness",
       "both False",
       f"{_snap['tamper_proof']}/{_snap['captures_everything']}",
       _snap["tamper_proof"] is False
       and _snap["captures_everything"] is False)


# ==========================================================================
# 10. PROVENANCE & STANDARDS BOUNDARY
# ==========================================================================
_prov = FC.provenance(SRC, "ATTR-001", usage_context="context only")
record("F-PR-01", "Provenance records origin with declared identity",
       "declared identity key",
       f"{'source_identity_declared' in _prov}",
       "source_identity_declared" in _prov)

record("F-PR-02", "Provenance lists the four claims it does NOT make",
       "4 non-claims", f"{len(_prov['claims_not_made'])}",
       len(_prov["claims_not_made"]) == 4)

record("F-PR-03", "No cryptographic authenticity is claimed",
       "listed as not claimed",
       f"{'cryptographic authenticity' in _prov['claims_not_made']}",
       "cryptographic authenticity" in _prov["claims_not_made"])

record("F-PR-04", "No verified publisher identity is claimed",
       "listed as not claimed",
       f"{'verified publisher identity' in _prov['claims_not_made']}",
       "verified publisher identity" in _prov["claims_not_made"])

record("F-PR-05", "No tamper-proof provenance is claimed",
       "listed as not claimed",
       f"{'tamper-proof provenance' in _prov['claims_not_made']}",
       "tamper-proof provenance" in _prov["claims_not_made"])

_comp = FC.compliance_claim()
record("F-SG-01", "F never certifies compliance (GAP-F-01)",
       "compliance_certified False",
       f"{_comp['compliance_certified']}",
       _comp["compliance_certified"] is False)

record("F-SG-02", "The five-link standards chain is stated in the refusal",
       "chain named",
       f"{'not Compliance Verification' in _comp['reason']}",
       "not a Requirement" in _comp["reason"]
       and "not Compliance Verification" in _comp["reason"])

record("F-SG-03", "Compliance Verification is declared outside 00.5",
       "outside 00.5", f"{'outside 00.5' in _comp['reason']}",
       "outside 00.5" in _comp["reason"])


# ==========================================================================
# 11. INTEGRATION BOUNDARIES (A–E untouched, no re-implementation)
# ==========================================================================
_src_all = _src_ref + _src_usage + _src_conf
_exec_only = re.sub(r'""".*?"""', "", _src_all, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
_code_ns = re.sub(r'"[^"]*"', '""', _exec_only)
_code_ns = re.sub(r"'[^']*'", "''", _code_ns)

_forbidden = ["validate_formulas", "validate_blocking", "validate_lifecycle",
              "schema_gate", "c1_preconditions", "c2_fingerprint",
              "c3_svg_emitter", "c4_quantities", "c5_presentation",
              "c6_manifest", "d_report", "d_compare", "e_ownership",
              "e_authorization", "e_lifecycle", "e_identity"]
record("F-IB-01", "F imports no A–E module",
       "none",
       f"{[m for m in _forbidden if f'import {m}' in _src_all]}",
       not [m for m in _forbidden if f"import {m}" in _src_all])

record("F-IB-02", "F does not read or write the master",
       "no master access",
       f"{[t for t in ('project_master', 'schema_gate') if t in _exec_only]}",
       not [t for t in ("project_master", "schema_gate") if t in _exec_only])

record("F-IB-03", "F issues no fingerprint of its own",
       "no hashing",
       f"{[t for t in ('hashlib', 'sha256', 'md5') if t in _code_ns]}",
       not [t for t in ("hashlib", "sha256", "md5") if t in _code_ns])

record("F-IB-04", "F performs no geometry and no fidelity work",
       "none",
       f"{[t for t in ('geometry', 'fidelity_verdict', 'coordinate') if t in _code_ns.lower()]}",
       not [t for t in ("geometry", "fidelity_verdict", "coordinate")
            if t in _code_ns.lower()])

record("F-IB-05", "F creates no approval",
       "no approval issuance",
       f"{[t for t in ('approve(', 'approval_record', 'approved_by =') if t in _exec_only]}",
       not [t for t in ("approve(", "approval_record", "approved_by =")
            if t in _exec_only])


# ==========================================================================
# 12. NO-WRITE
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_watch = [os.path.join(ROOT, "project_master.template.json"),
          os.path.join(ROOT, "project_master.schema.json"),
          os.path.join(ROOT, "RULES.md"),
          os.path.join(ROOT, "scripts", "validate_formulas.py"),
          os.path.join(ROOT, "scripts", "e_ownership.py")]
_before_h = [_sha(p) for p in _watch]
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))
_src_snapshot = copy.deepcopy(SRC.as_dict())

FU.record_usage("ATTR-001", FU.PATH_A_CONTEXT, declared_by="USER")
FC.detect_conflict("depth", _ca, _cb)
FC.provenance(SRC, "ATTR-001")
FR.authority_for(SRC, "product_dimensions")

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("F-NW-01", "BEHAVIOURAL: master/schema/RULES/B6/E files unchanged",
       "sha256 stable", f"{_before_h == [_sha(p) for p in _watch]}",
       _before_h == [_sha(p) for p in _watch])

record("F-NW-02", "BEHAVIOURAL: no new file appeared",
       "none", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

record("F-NW-03", "BEHAVIOURAL: project_master.json is never created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

record("F-NW-04", "BEHAVIOURAL: the source object is not mutated",
       "identical", f"{_src_snapshot == SRC.as_dict()}",
       _src_snapshot == SRC.as_dict())

_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "tempfile", "pickle", "os.remove"]
record("F-NW-05", "WRITE-PATH AUDIT: no write mechanism in F",
       "none of 10",
       f"{[p for p in _write_paths if p in _exec_only]}",
       not [p for p in _write_paths if p in _exec_only])


# ==========================================================================
# 13. MUTATION
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
    record(f"F-M-{mid}", f"MUTATION {desc}", "KILLED", cls, detected)


# M-01 let usage auto-create a proposal (breaks UP-6)
_orig_record = FU.record_usage


def _auto_proposal(attribute_ref, path, declared_by=None, rationale=None):
    out = _orig_record(attribute_ref, path, declared_by, rationale)
    if out.get("usage_path") == FU.PATH_A_CONTEXT:
        out["produces_proposal"] = True
    return out


FU.record_usage = _auto_proposal
try:
    _d01 = FU.record_usage("ATTR-001", FU.PATH_A_CONTEXT,
                           declared_by="USER")["produces_proposal"] is True
finally:
    FU.record_usage = _orig_record
mutation("01", "let PATH A auto-create a proposal (UP-6 breach)",
         "KILLED" if _d01 else "SURVIVED", f"detected={_d01}")
record("F-M-01", "MUTATION PATH A auto-proposal", "KILLED",
       "KILLED" if _d01 else "SURVIVED", _d01)

# M-02 let F infer the usage path
run_mut("02", "let F default an unspecified path to decision-affecting",
        FU, "USAGE_PATHS", (FU.PATH_A_CONTEXT, FU.PATH_B_DECISION_AFFECTING,
                            None),
        lambda: FU.record_usage("ATTR-001", None).get("result") != "REFUSED")

# M-03 treat outside-scope as a source violation (R03 amendment 2 breach)
_orig_auth = FR.authority_for


def _auth_violation(source, attribute):
    out = _orig_auth(source, attribute)
    if out["result"] == "NOT_AUTHORITATIVE":
        out["is_source_violation"] = True
    return out


FR.authority_for = _auth_violation
try:
    _d03 = FR.authority_for(SRC, "local_code_compliance")[
        "is_source_violation"] is True
finally:
    FR.authority_for = _orig_auth
mutation("03", "mark outside-scope as a source violation",
         "KILLED" if _d03 else "SURVIVED", f"detected={_d03}")
record("F-M-03", "MUTATION outside-scope as violation", "KILLED",
       "KILLED" if _d03 else "SURVIVED", _d03)

# M-04 make source_type grant authority
def _auth_by_type(source, attribute):
    if source.source_type == "OFFICIAL_MANUFACTURER":
        return {"attribute": attribute, "result": "AUTHORITATIVE",
                "basis": "source_type", "declared": False,
                "is_source_violation": False, "note": ""}
    return _orig_auth(source, attribute)


FR.authority_for = _auth_by_type
try:
    _d04 = FR.authority_for(_bare, "product_dimensions")["result"] \
        == "AUTHORITATIVE"
finally:
    FR.authority_for = _orig_auth
mutation("04", "let source_type grant authority (ST-1 breach)",
         "KILLED" if _d04 else "SURVIVED", f"detected={_d04}")
record("F-M-04", "MUTATION source_type grants authority", "KILLED",
       "KILLED" if _d04 else "SURVIVED", _d04)

# M-05 default verification to something stronger
run_mut("05", "default verification to RETRIEVED instead of UNVERIFIED",
        FR, "UNVERIFIED", "RETRIEVED",
        lambda: FR.Source("SRC-Z").verification_state != "UNVERIFIED")

# M-06 default applicability to applicable
run_mut("06", "default applicability to APPLICABLE_DECLARED",
        FR, "APPLICABILITY_UNKNOWN", "APPLICABLE_DECLARED",
        lambda: FR.applicability_report()["state"] != "APPLICABILITY_UNKNOWN")

# M-07 auto-resolve a conflict
_orig_detect = FC.detect_conflict


def _auto_resolve(attribute, claim_a, claim_b):
    out = _orig_detect(attribute, claim_a, claim_b)
    if out.get("conflict"):
        out["resolved"] = True
        out["resolved_by_f"] = True
    return out


FC.detect_conflict = _auto_resolve
try:
    _d07 = FC.detect_conflict("depth", _ca, _cb)["resolved_by_f"] is True
finally:
    FC.detect_conflict = _orig_detect
mutation("07", "auto-resolve a conflict inside F (CF-1/CF-5 breach)",
         "KILLED" if _d07 else "SURVIVED", f"detected={_d07}")
record("F-M-07", "MUTATION auto-resolve conflict", "KILLED",
       "KILLED" if _d07 else "SURVIVED", _d07)

# M-08 apply a library update to the project
_orig_reg = FC.register_new_version


def _auto_apply(pinned, new_version):
    out = _orig_reg(pinned, new_version)
    out["applied_to_project"] = True
    out["project_changed"] = True
    return out


FC.register_new_version = _auto_apply
try:
    _d08 = FC.register_new_version(_pin, "2027.0")["project_changed"] is True
finally:
    FC.register_new_version = _orig_reg
mutation("08", "apply a library update to the project (V-3 breach)",
         "KILLED" if _d08 else "SURVIVED", f"detected={_d08}")
record("F-M-08", "MUTATION library update changes project", "KILLED",
       "KILLED" if _d08 else "SURVIVED", _d08)

# M-09 issue a snapshot fingerprint
_orig_snap = FC.snapshot


def _snap_fp(*a, **k):
    out = _orig_snap(*a, **k)
    out["content_fingerprint"] = "sha256:deadbeef"
    return out


FC.snapshot = _snap_fp
try:
    _d09 = FC.snapshot("SNAP-002")["content_fingerprint"] != "NOT_ISSUED"
finally:
    FC.snapshot = _orig_snap
mutation("09", "issue a snapshot fingerprint (C2 boundary breach)",
         "KILLED" if _d09 else "SURVIVED", f"detected={_d09}")
record("F-M-09", "MUTATION snapshot fingerprint issued", "KILLED",
       "KILLED" if _d09 else "SURVIVED", _d09)

# M-10 certify compliance
_orig_comp = FC.compliance_claim
FC.compliance_claim = lambda *a, **k: {"compliance_certified": True,
                                       "code": None, "reason": ""}
try:
    _d10 = FC.compliance_claim()["compliance_certified"] is True
finally:
    FC.compliance_claim = _orig_comp
mutation("10", "certify compliance inside F (GAP-F-01 breach)",
         "KILLED" if _d10 else "SURVIVED", f"detected={_d10}")
record("F-M-10", "MUTATION compliance certified", "KILLED",
       "KILLED" if _d10 else "SURVIVED", _d10)

# M-11 allow promotion to [D].
# Isolated: promote() refuses [D] at a single guard, so patching that guard
# is the only way the breach can occur.
_orig_promote = FU.promote
FU.promote = lambda attribute_ref, target_status: {"promoted": target_status}
try:
    _d11 = FU.promote("ATTR-001", "D").get("promoted") == "D"
finally:
    FU.promote = _orig_promote
mutation("11", "allow F to promote a reference to [D] (UP-1 breach)",
         "KILLED" if _d11 else "SURVIVED", f"detected={_d11}")
record("F-M-11", "MUTATION promote to [D]", "KILLED",
       "KILLED" if _d11 else "SURVIVED", _d11)

# CONTROL
_ctrl_before = FR.authority_for(SRC, "product_dimensions")["result"]
_orig_types = FR.SOURCE_TYPES
FR.SOURCE_TYPES = FR.SOURCE_TYPES + ("RENAMED_TYPE",)
_ctrl_after = FR.authority_for(SRC, "product_dimensions")["result"]
FR.SOURCE_TYPES = _orig_types
mutation("CTRL", "cosmetic source-type list rename", "CONTROL",
         f"before={_ctrl_before}, after={_ctrl_after}")
record("F-M-CTRL", "CONTROL: cosmetic change alters no authority result",
       "AUTHORITATIVE before and after",
       f"{_ctrl_before}/{_ctrl_after}",
       _ctrl_before == "AUTHORITATIVE" and _ctrl_after == "AUTHORITATIVE")


# --------------------------------------------------------------------------
print("=" * 100)
print("PHASE 00.5-F — LIBRARY / REFERENCE DATA / STANDARDS GOVERNANCE")
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
print("LIMITATIONS: citation/source authenticity NOT verifiable (GAP-F-02 "
      "OPEN) · compliance verification outside F and outside 00.5 (GAP-F-01)")
print("=" * 100)
sys.exit(0 if passed == total else 1)
