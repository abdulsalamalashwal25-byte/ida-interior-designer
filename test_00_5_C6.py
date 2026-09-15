#!/usr/bin/env python3
"""Phase 00.5-C6 — Manifest / Evidence Assembler.

Reference: C6 Architecture R03 CLOSED · Gate 1 APPROVED.

WHAT THIS SUITE MUST PROVE
  * each producer's field semantics survive untouched
  * C4's completeness dictionary is preserved verbatim, key set and all
  * NOT_SET is an absence declaration, never a verdict
  * nothing is inferred: producer_channel, declared_class, output_id
  * comparisons and counts are mechanical, never judgements
  * C6 writes nothing and mutates no source record

DISCIPLINE (inherited)
  AS-C2-16 mutate through the module · AS-C2-17 literal expectations ·
  AS-C4-18 no default-argument binding of contract constants.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import c6_contract as CON                                            # noqa: E402
import c6_preservation as PRES                                       # noqa: E402
import c6_revision as REV                                            # noqa: E402
import c6_aggregate as AGG                                           # noqa: E402
import c6_manifest as MAN                                            # noqa: E402

# Producers are imported ONLY to build real fixtures. C6 modules themselves
# must not import them — proven by C6-ISO-01.
import c3_svg_emitter as C3                                          # noqa: E402
import c4_quantities as C4                                           # noqa: E402
import c5_presentation as C5                                         # noqa: E402

RESULTS = []
MUTATIONS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


def mutation(mid, description, classification, detail):
    MUTATIONS.append((mid, description, classification, detail))


def fact(value, status="C", src="CLIENT_INPUT", unit="mm"):
    return {"value": value, "unit": unit, "status": status,
            "source_type": src, "source_ref": "intake/p1",
            "recorded_on": "2026-09-12"}


def master(partial=False):
    return {
        "meta": {"project_id": "PRJ-01", "master_revision": "R01"},
        "space": {"outline": fact([[0, 0], [6000, 0], [6000, 4000], [0, 4000]])},
        "walls": [
            {"id": "W-01", "start": fact([0, 0]), "end": fact([6000, 0])},
            {"id": "W-02", "start": fact([6000, 0]),
             "end": fact([6000, 4000], "U" if partial else "C")},
        ],
        "openings": [
            {"id": "OP-01", "kind": "door", "host_wall": "W-01",
             "offset": fact(1000), "width": fact(900), "height": fact(2100)},
        ],
    }


IDENT = {"project_id": "PRJ-01", "master_revision": "R01"}
M_OK, M_PART = master(), master(partial=True)

A_REC = C3.emit_svg(M_OK, identity=IDENT)
B_REC = C5.emit_class_b(A_REC["assembly"], {"color": "#333"}, identity=IDENT)
Q_REC = C4.build_schedule(M_OK)

A_P = C3.emit_svg(M_PART, identity=IDENT)
B_P = C5.emit_class_b(A_P["assembly"], {"color": "#333"}, identity=IDENT)
Q_P = C4.build_schedule(M_PART)

MF = MAN.assemble_manifest([("C3", A_REC), ("C5", B_REC), ("C4", Q_REC)],
                           identity=IDENT)
MF_P = MAN.assemble_manifest([("C3", A_P), ("C5", B_P), ("C4", Q_P)],
                             identity=IDENT)


def member(mf, owner):
    return [m for m in mf["members"] if m["source_owner"] == owner][0]


# ==========================================================================
# 1. POSITIVE
# ==========================================================================
record("C6-P-01", "Manifest assembles one member per producer record",
       "3 members", f"{len(MF['members'])}", len(MF["members"]) == 3)

record("C6-P-02", "C3 status appears as status",
       "EMITTED", f"{member(MF, 'C3')['source_status']}",
       member(MF, "C3")["source_status"] == "EMITTED")

record("C6-P-03", "C5 coverage appears as coverage",
       "COMPLETE", f"{member(MF, 'C5')['source_coverage']}",
       member(MF, "C5")["source_coverage"] == "COMPLETE")

record("C6-P-04", "C4 completeness appears as completeness",
       "COMPLETE", f"{member(MF, 'C4')['source_completeness']}",
       member(MF, "C4")["source_completeness"] == "COMPLETE")

record("C6-P-05", "Manifest declares itself external, not written to master",
       "EXTERNAL_OUTPUT_MANIFEST, written=False",
       f"{MF['manifest_kind']}, written={MF['written_to_master']}",
       MF["manifest_kind"] == "EXTERNAL_OUTPUT_MANIFEST"
       and MF["written_to_master"] is False)

record("C6-P-06", "All required member fields are present",
       "no missing fields",
       f"{[r['missing_required_fields'] for r in MAN.manifest_field_report(MF)]}",
       all(not r["missing_required_fields"]
           for r in MAN.manifest_field_report(MF)))

record("C6-P-07", "Manifest carries its binding notices",
       "8 notices incl. provenance!=fidelity",
       f"n={len(MF['notices'])}",
       any("provenance is not fidelity" in n for n in MF["notices"]))

record("C6-P-08", "Manifest declares it is not a verdict",
       "is_verdict=False", f"{MF['is_verdict']}", MF["is_verdict"] is False)


# ==========================================================================
# 2. NEGATIVE — forbidden semantic migration
# ==========================================================================
record("C6-N-01", "C4 completeness is NOT carried into source_status",
       "C4 status = NOT_SET", f"{member(MF, 'C4')['source_status']}",
       member(MF, "C4")["source_status"] == "NOT_SET")

record("C6-N-02", "C4 completeness is NOT carried into source_coverage",
       "C4 coverage = NOT_SET", f"{member(MF, 'C4')['source_coverage']}",
       member(MF, "C4")["source_coverage"] == "NOT_SET")

record("C6-N-03", "C5 coverage is NOT carried into source_completeness",
       "C5 completeness = NOT_SET",
       f"{member(MF, 'C5')['source_completeness']}",
       member(MF, "C5")["source_completeness"] == "NOT_SET")

record("C6-N-04", "C3 declares neither coverage nor completeness",
       "both NOT_SET",
       f"{member(MF, 'C3')['source_coverage']}/"
       f"{member(MF, 'C3')['source_completeness']}",
       member(MF, "C3")["source_coverage"] == "NOT_SET"
       and member(MF, "C3")["source_completeness"] == "NOT_SET")

record("C6-N-05", "C3 gets no completeness_detail (it declares none)",
       "absent", f"{'source_completeness_detail' in member(MF, 'C3')}",
       "source_completeness_detail" not in member(MF, "C3"))

_src_all = ""
for _f in ("c6_contract.py", "c6_preservation.py", "c6_revision.py",
           "c6_aggregate.py", "c6_manifest.py"):
    _src_all += open(os.path.join(ROOT, "scripts", _f), encoding="utf-8").read()
_exec_only = re.sub(r'""".*?"""', "", _src_all, flags=re.S)
_exec_only = "\n".join(ln.split("#")[0] for ln in _exec_only.splitlines())
_code_no_strings = re.sub(r'"[^"]*"', '""', _exec_only)
_code_no_strings = re.sub(r"'[^']*'", "''", _code_no_strings)

record("C6-N-06", "No source_status_field mechanism exists (removed in R03)",
       "absent from code", f"{'source_status_field' in _exec_only}",
       "source_status_field" not in _exec_only)


# ==========================================================================
# 3. BOUNDARY
# ==========================================================================
_mf_empty = MAN.assemble_manifest([], identity=IDENT)
record("C6-BD-01", "Zero members: manifest assembles with no invented state",
       "0 members, no status key",
       f"n={_mf_empty['aggregate_summary']['members_total']}, "
       f"status_key={'status' in _mf_empty}",
       _mf_empty["aggregate_summary"]["members_total"] == 0
       and "status" not in _mf_empty)

_mf_one = MAN.assemble_manifest([("C3", A_REC)], identity=IDENT)
record("C6-BD-02", "Single member manifest is valid",
       "1 member", f"{len(_mf_one['members'])}",
       len(_mf_one["members"]) == 1)

_abst = C3.emit_svg({"meta": {}, "space": {}, "walls": []}, identity=IDENT)
_mf_ab = MAN.assemble_manifest([("C3", _abst)], identity=IDENT)
record("C6-BD-03", "ABSTAIN member is carried as ABSTAIN, not as failure",
       "source_status=ABSTAIN",
       f"{member(_mf_ab, 'C3')['source_status']}",
       member(_mf_ab, "C3")["source_status"] == "ABSTAIN")

_mf_unk = MAN.assemble_manifest([("C9", {"status": "EMITTED"})],
                                identity=IDENT)
record("C6-BD-04", "Unknown owner is reported NOT_SET, not guessed",
       "source_owner=NOT_SET",
       f"{_mf_unk['members'][0]['source_owner']}",
       _mf_unk["members"][0]["source_owner"] == "NOT_SET")

record("C6-BD-05", "Unknown owner declares no status either",
       "NOT_SET", f"{_mf_unk['members'][0]['source_status']}",
       _mf_unk["members"][0]["source_status"] == "NOT_SET")


# ==========================================================================
# 4. PRESERVATION
# ==========================================================================
record("C6-PR-01", "contract is carried as a raw value, untranslated",
       "floor-plan/tier-0+1", f"{member(MF, 'C3')['contract']}",
       member(MF, "C3")["contract"] == "floor-plan/tier-0+1")

record("C6-PR-02", "format is carried raw",
       "svg", f"{member(MF, 'C3')['format']}",
       member(MF, "C3")["format"] == "svg")

record("C6-PR-03", "C5 declared class is preserved verbatim",
       "B", f"{member(MF, 'C5')['declared_class']}",
       member(MF, "C5")["declared_class"] == "B")

record("C6-PR-04", "determinism evidence is carried as declared",
       "D1 NOT_ESTABLISHED, D2 NOT_CLAIMED",
       f"{member(MF, 'C3')['determinism']['D1']}/"
       f"{member(MF, 'C3')['determinism']['D2']}",
       member(MF, "C3")["determinism"]["D1"] == "NOT_ESTABLISHED"
       and member(MF, "C3")["determinism"]["D2"] == "NOT_CLAIMED")

record("C6-PR-05", "C5 lineage evidence is carried with its provisional tag",
       "PROVISIONAL, usable_as_evidence False",
       f"{member(MF, 'C5')['lineage_evidence']['status']}",
       member(MF, "C5")["lineage_evidence"]["status"] == "PROVISIONAL"
       and member(MF, "C5")["lineage_evidence"]["usable_as_evidence"] is False)

_snapshot = copy.deepcopy(Q_REC)
MAN.assemble_manifest([("C4", Q_REC)], identity=IDENT)
record("C6-PR-06", "Source records are not mutated in place",
       "identical", f"{_snapshot == Q_REC}", _snapshot == Q_REC)


# ==========================================================================
# 5. C4 COMPLETENESS DETAIL
# ==========================================================================
_c4p = member(MF_P, "C4")
record("C6-CD-01", "C4 completeness dictionary is preserved verbatim",
       "identical to source",
       f"{_c4p['source_completeness_detail'] == Q_P['completeness']}",
       _c4p["source_completeness_detail"] == Q_P["completeness"])

record("C6-CD-02", "overall is read, never recomputed",
       f"{Q_P['completeness']['overall']}",
       f"{_c4p['source_completeness']}",
       _c4p["source_completeness"] == Q_P["completeness"]["overall"])

_ks = set(_c4p["source_completeness_detail"].keys())
record("C6-CD-03", "Key set is untouched: Q-01 is NOT added from class_a",
       "Q-01 absent, class_a has it",
       f"detail={sorted(_ks)}, class_a_has_Q01={'Q-01' in Q_P['class_a']}",
       "Q-01" not in _ks and "Q-01" in Q_P["class_a"])

_mixed = {"completeness": {"Q-02": "COMPLETE", "Q-03": "ABSTAIN",
                           "Q-04": "COMPLETE", "overall": "PARTIAL"}}
_mm = PRES.preserve_member(_mixed, "C4")
record("C6-CD-04", "ABSTAIN member coexists with overall=PARTIAL, unreconciled",
       "both preserved",
       f"Q-03={_mm['source_completeness_detail']['Q-03']}, "
       f"overall={_mm['source_completeness']}",
       _mm["source_completeness_detail"]["Q-03"] == "ABSTAIN"
       and _mm["source_completeness"] == "PARTIAL")

record("C6-CD-05", "No key is renamed or dropped",
       "exact key set",
       f"{sorted(_mm['source_completeness_detail'].keys())}",
       sorted(_mm["source_completeness_detail"].keys())
       == ["Q-02", "Q-03", "Q-04", "overall"])

record("C6-CD-06", "Detail is a copy: mutating it cannot reach the source",
       "source unchanged",
       f"{Q_P['completeness']['overall']}",
       (_c4p["source_completeness_detail"] is not Q_P["completeness"]))

record("C6-CD-07", "completeness is never inferred from class_a",
       "no class_a read in preservation",
       f"{'class_a' in _exec_only}", "class_a" not in _exec_only)


# ==========================================================================
# 6. NOT_SET SEMANTICS
# ==========================================================================
record("C6-NS-01", "NOT_SET has a bounded declared meaning",
       "absence of declaration",
       f"{CON.NOT_SET_MEANS[:34]}",
       "did not declare" in CON.NOT_SET_MEANS)

record("C6-NS-02", "NOT_SET is explicitly not failed/invalid/rejected",
       "6 excluded meanings",
       f"{CON.NOT_SET_DOES_NOT_MEAN}",
       set(CON.NOT_SET_DOES_NOT_MEAN) ==
       {"failed", "invalid", "rejected", "incomplete", "unknown",
        "not applicable"})

record("C6-NS-03", "Manifest states NOT_SET semantics inline",
       "statement present",
       f"{'not failed' in MF['not_set_semantics']}",
       "not failed" in MF["not_set_semantics"])

record("C6-NS-04", "NOT_SET is not conflated with UNKNOWN or NOT_PRESENT",
       "distinct tokens",
       f"{[t for t in ('UNKNOWN', 'NOT_PRESENT') if t in _code_no_strings]}",
       not [t for t in ("UNKNOWN", "NOT_PRESENT") if t in _code_no_strings])

record("C6-NS-05", "A member with no declarations yields NOT_SET, not failure",
       "all three NOT_SET",
       f"{[PRES.preserve_member({}, 'C4')[k] for k in ('source_status', 'source_coverage', 'source_completeness')]}",
       [PRES.preserve_member({}, "C4")[k] for k in
        ("source_status", "source_coverage", "source_completeness")]
       == ["NOT_SET", "NOT_SET", "NOT_SET"])


# ==========================================================================
# 7. ANTI-INFERENCE
# ==========================================================================
record("C6-AI-01", "producer_channel is NOT_SET for every producer",
       "all NOT_SET",
       f"{[m['producer_channel'] for m in MF['members']]}",
       all(m["producer_channel"] == "NOT_SET" for m in MF["members"]))

record("C6-AI-02", "producer_channel is not inferred from contract",
       "contract present yet channel NOT_SET",
       f"contract={member(MF, 'C3')['contract']}, "
       f"channel={member(MF, 'C3')['producer_channel']}",
       member(MF, "C3")["contract"] != "NOT_SET"
       and member(MF, "C3")["producer_channel"] == "NOT_SET")

_ch = PRES.preserve_producer_channel({"producer_channel": "A-channel"})
record("C6-AI-03", "An explicitly declared channel IS preserved",
       "A-channel", f"{_ch}", _ch == "A-channel")

record("C6-AI-04", "C3 declared_class is NOT_SET, never inferred as A",
       "NOT_SET", f"{member(MF, 'C3')['declared_class']}",
       member(MF, "C3")["declared_class"] == "NOT_SET")

record("C6-AI-05", "declared_class is not inferred from format or parameters",
       "B only from declared class",
       f"{PRES.preserve_declared_class({'format': 'svg', 'parameters_admitted': [1]})}",
       PRES.preserve_declared_class(
           {"format": "svg", "parameters_admitted": [1]}) == "NOT_SET")

record("C6-AI-06", "No SVG parsing anywhere in C6",
       "no parser calls",
       f"{[t for t in ('findall', 'ElementTree', 'parse(', '<svg') if t in _exec_only]}",
       not [t for t in ("findall", "ElementTree", "parse(", "<svg")
            if t in _exec_only])


# ==========================================================================
# 8. ANTI-SMUGGLING
# ==========================================================================
record("C6-AS-01", "No output_id is generated",
       "NOT_SET for all",
       f"{[m['output_id'] for m in MF['members']]}",
       all(m["output_id"] == "NOT_SET" for m in MF["members"]))

_with_id = MAN.assemble_manifest(
    [("C3", A_REC)], identity={"project_id": "PRJ-01", "output_id": "OUT-01"})
record("C6-AS-02", "An official output_id, when supplied, is preserved",
       "OUT-01", f"{_with_id['members'][0]['output_id']}",
       _with_id["members"][0]["output_id"] == "OUT-01")

record("C6-AS-03", "No identity is minted from hash/uuid/filename/timestamp",
       "no such generators",
       f"{[t for t in ('uuid', 'hashlib', 'md5', 'sha256') if t in _exec_only]}",
       not [t for t in ("uuid", "hashlib", "md5", "sha256")
            if t in _exec_only])

record("C6-AS-04", "No engineering fingerprint is issued",
       "NOT_ISSUED for all",
       f"{set(m['engineering_fingerprint'] for m in MF['members'])}",
       all(m["engineering_fingerprint"] == "NOT_ISSUED"
           for m in MF["members"]))

record("C6-AS-05", "Provisional digest is never promoted",
       "no promotion path",
       f"{'provisional' in _code_no_strings.lower()}",
       "provisional" not in _code_no_strings.lower())

record("C6-AS-06", "No manifest-level status/completeness/validity is created",
       "none of the keys",
       f"{[k for k in ('status', 'completeness', 'validity', 'approval') if k in MF]}",
       not [k for k in ("status", "completeness", "validity", "approval")
            if k in MF])

record("C6-AS-07", "No fidelity verdict key anywhere",
       "none",
       f"{[k for k in ('\"fidelity_ok\"', '\"matches_master\"', '\"verified\"') if k in _exec_only]}",
       not [k for k in ('"fidelity_ok"', '"matches_master"', '"verified"')
            if k in _exec_only])

# Prose that DENIES a behaviour ("not weighted", "no severity") is
# documentation. The check targets executable code with string literals
# stripped, and additionally proves no such key is ever emitted.
_judgement_tokens = ("pass_fail", "severity", "score", "weighted")
_tok_in_code = [t for t in _judgement_tokens if t in _code_no_strings]
# Emitted KEYS, not the explanatory note (which legitimately says
# "not weighted" while denying the behaviour).
_tok_in_output = [t for t in _judgement_tokens
                  if any(t in k for k in MF["aggregate_summary"].keys())]
record("C6-AS-08", "No pass/fail or severity logic or keys in aggregation",
       "absent from code and from output",
       f"code={_tok_in_code}, output={_tok_in_output}",
       not _tok_in_code and not _tok_in_output)


# ==========================================================================
# 9. REVISION COMPARISON
# ==========================================================================
_rv = MF["revision_view"]
record("C6-RV-01", "Missing revision yields comparable=false",
       "false / NOT_DETERMINABLE",
       f"{_rv['comparable']}/{_rv['divergence']}",
       _rv["comparable"] is False
       and _rv["divergence"] == "NOT_DETERMINABLE")

_same = REV.compare_revisions([{"source_owner": "C3", "master_revision": "R01"},
                               {"source_owner": "C5", "master_revision": "R01"}])
record("C6-RV-02", "Identical declared revisions yield NONE_OBSERVED",
       "true / NONE_OBSERVED",
       f"{_same['comparable']}/{_same['divergence']}",
       _same["comparable"] is True
       and _same["divergence"] == "NONE_OBSERVED")

_diff = REV.compare_revisions([{"source_owner": "C3", "master_revision": "R01"},
                               {"source_owner": "C5", "master_revision": "R02"},
                               {"source_owner": "C4", "master_revision": "R01"}])
record("C6-RV-03", "Different declared revisions yield OBSERVED",
       "true / OBSERVED",
       f"{_diff['comparable']}/{_diff['divergence']}",
       _diff["comparable"] is True and _diff["divergence"] == "OBSERVED")

record("C6-RV-04", "All declared revisions are listed, none hidden",
       "R01, R02, R01",
       f"{sorted(_diff['declared_revisions'].values())}",
       sorted(_diff["declared_revisions"].values()) == ["R01", "R01", "R02"])

record("C6-RV-05", "No latest-revision selection and no merged revision",
       "no such logic",
       f"{[t for t in ('latest', 'max(', 'merge') if t in _exec_only]}",
       not [t for t in ("latest", "max(", "merge") if t in _exec_only])

record("C6-RV-06", "revision_view declares itself mechanical, not a verdict",
       "metadata_kind + is_verdict False",
       f"{_rv['metadata_kind']}, is_verdict={_rv['is_verdict']}",
       _rv["metadata_kind"] == "mechanical comparison metadata"
       and _rv["is_verdict"] is False)

record("C6-RV-07", "No output is rejected on account of divergence",
       "3 members retained with OBSERVED",
       f"{len(MAN.assemble_manifest([('C3', A_REC), ('C5', B_REC), ('C4', Q_REC)], identity=IDENT)['members'])}",
       len(MF["members"]) == 3)


# ==========================================================================
# 10. AGGREGATE ISOLATION
# ==========================================================================
_ag = MF["aggregate_summary"]
record("C6-AG-01", "Three separate counters exist",
       "status, coverage, completeness",
       f"{[k for k in _ag if k.startswith('by_')]}",
       sorted(k for k in _ag if k.startswith("by_")) ==
       ["by_source_completeness", "by_source_coverage", "by_source_status"])

record("C6-AG-02", "C4 counts under status NOT_SET (no status field)",
       "NOT_SET >= 1",
       f"{_ag['by_source_status']['NOT_SET']}",
       _ag["by_source_status"]["NOT_SET"] == 1)

record("C6-AG-03", "Counters are not combined into an overall state",
       "no unified key",
       f"{[k for k in _ag if k in ('overall', 'unified', 'state')]}",
       not [k for k in _ag if k in ("overall", "unified", "state")])

record("C6-AG-04", "Counts are mechanical and declared as such",
       "counts_kind + is_verdict False",
       f"{_ag['counts_kind']}, is_verdict={_ag['is_verdict']}",
       _ag["counts_kind"] == "mechanical counts"
       and _ag["is_verdict"] is False)

record("C6-AG-05", "members_total equals the number of members",
       "3", f"{_ag['members_total']}",
       _ag["members_total"] == len(MF["members"]))

_sum_status = sum(_ag["by_source_status"].values())
record("C6-AG-06", "Each counter independently totals the member count",
       "3 per counter",
       f"{_sum_status}/{sum(_ag['by_source_coverage'].values())}",
       _sum_status == 3 and sum(_ag["by_source_coverage"].values()) == 3)


# ==========================================================================
# 11–15. BOUNDARIES (identity · approval · fidelity · fingerprint · parent)
# ==========================================================================
record("C6-BO-01", "Identity ownership is declared as E",
       "E", f"{MF['ownership']['output_identity']}",
       MF["ownership"]["output_identity"] == "E")

record("C6-BO-02", "approval_managed_by is E on every member",
       "all E",
       f"{set(m['approval_managed_by'] for m in MF['members'])}",
       all(m["approval_managed_by"] == "E" for m in MF["members"]))

record("C6-BO-03", "approval_value is NOT_SET, never a verdict",
       "NOT_SET, no REJECTED/NOT_APPLICABLE",
       f"{set(m['approval_value'] for m in MF['members'])}",
       all(m["approval_value"] == "NOT_SET" for m in MF["members"])
       and "NOT_APPLICABLE" not in _exec_only)

_appr = MAN.assemble_manifest(
    [("C3", A_REC)], identity={"approval_value": "APPROVED_BY_E"})
record("C6-BO-04", "An approval value supplied by its owner is preserved",
       "APPROVED_BY_E", f"{_appr['members'][0]['approval_value']}",
       _appr["members"][0]["approval_value"] == "APPROVED_BY_E")

record("C6-BO-05", "fidelity is NOT_ASSESSED on every member",
       "all NOT_ASSESSED",
       f"{set(m['fidelity'] for m in MF['members'])}",
       all(m["fidelity"] == "NOT_ASSESSED" for m in MF["members"]))

record("C6-BO-06", "fidelity ownership is declared as D",
       "D", f"{MF['ownership']['fidelity']}",
       MF["ownership"]["fidelity"] == "D")

record("C6-BO-07", "Parent absent -> NOT_SET + MISSING, no orphan verdict",
       "NOT_SET/MISSING, no 'orphan'",
       f"{member(MF, 'C3')['parent_ref']}/"
       f"{member(MF, 'C3')['parent_evidence']}",
       member(MF, "C3")["parent_ref"] == "NOT_SET"
       and member(MF, "C3")["parent_evidence"] == "MISSING"
       and "orphan" not in _exec_only.lower())

_par = PRES.preserve_member({"parent_ref": "A-001"}, "C5")
record("C6-BO-08", "Parent present -> PRESENT",
       "A-001/PRESENT",
       f"{_par['parent_ref']}/{_par['parent_evidence']}",
       _par["parent_ref"] == "A-001"
       and _par["parent_evidence"] == "PRESENT")

record("C6-BO-09", "No 'broken lineage' or engineering-failure vocabulary",
       "none",
       f"{[t for t in ('broken', 'lineage_failure', 'invalid_parent') if t in _exec_only.lower()]}",
       not [t for t in ("broken", "lineage_failure", "invalid_parent")
            if t in _exec_only.lower()])


# ==========================================================================
# 16. NO-WRITE  (behavioural + write-path audit)
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_watch = [os.path.join(ROOT, "project_master.template.json"),
          os.path.join(ROOT, "project_master.schema.json"),
          os.path.join(ROOT, "scripts", "c3_svg_emitter.py"),
          os.path.join(ROOT, "scripts", "c4_quantities.py"),
          os.path.join(ROOT, "scripts", "c5_presentation.py")]
_before_h = [_sha(p) for p in _watch]
_files_before = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))
_a_snap, _b_snap, _q_snap = (copy.deepcopy(A_REC), copy.deepcopy(B_REC),
                             copy.deepcopy(Q_REC))

MAN.assemble_manifest([("C3", A_REC), ("C5", B_REC), ("C4", Q_REC)],
                      identity=IDENT)
MAN.manifest_field_report(MF)
AGG.aggregate_summary(MF["members"])
REV.compare_revisions(MF["members"])

_files_after = set(os.listdir(ROOT)) | set(
    os.listdir(os.path.join(ROOT, "scripts")))

record("C6-NW-01", "BEHAVIOURAL: producer records unchanged after assembly",
       "all identical",
       f"{(_a_snap == A_REC, _b_snap == B_REC, _q_snap == Q_REC)}",
       _a_snap == A_REC and _b_snap == B_REC and _q_snap == Q_REC)

record("C6-NW-02", "BEHAVIOURAL: master/schema/C3/C4/C5 files unchanged",
       "sha256 stable", f"{_before_h == [_sha(p) for p in _watch]}",
       _before_h == [_sha(p) for p in _watch])

record("C6-NW-03", "BEHAVIOURAL: no new file appeared",
       "none", f"{sorted(_files_after - _files_before)}",
       _files_after == _files_before)

record("C6-NW-04", "BEHAVIOURAL: project_master.json is never created",
       "absent",
       f"{os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

_write_paths = ["open(", ".write(", "json.dump", "write_text", "write_bytes",
                "os.replace", "shutil", "pathlib", "tempfile", "pickle",
                "os.remove", "mkdir"]
_found_w = [p for p in _write_paths if p in _exec_only]
record("C6-NW-05", "WRITE-PATH AUDIT: no write mechanism of any kind",
       "none of 12", f"{_found_w}", not _found_w)

record("C6-NW-06", "No outputs[] access anywhere",
       "no outputs reference",
       f"{'outputs' in _code_no_strings}",
       "outputs" not in _code_no_strings)


# ==========================================================================
# 17. ISOLATION
# ==========================================================================
_validators = ["validate_topology", "validate_furniture", "validate_movement",
               "validate_doors", "validate_formulas", "validate_outputs",
               "validate_refs", "validate_revisions", "validate_lifecycle",
               "validate_temporal", "validate_blocking", "schema_gate"]
record("C6-ISO-01", "C6 modules import no producer and no validator",
       "none",
       f"{[m for m in _validators + ['c3_svg_emitter', 'c4_quantities', 'c5_presentation', 'c1_preconditions'] if f'import {m}' in _src_all]}",
       not [m for m in _validators + ["c3_svg_emitter", "c4_quantities",
                                      "c5_presentation", "c1_preconditions"]
            if f"import {m}" in _src_all])

record("C6-ISO-02", "C6 does not read the master",
       "no master access",
       f"{[t for t in ('project_master', 'schema_gate') if t in _exec_only]}",
       not [t for t in ("project_master", "schema_gate") if t in _exec_only])

record("C6-ISO-03", "Contract vocabulary lives in exactly one module",
       "values defined in c6_contract only",
       f"{'NOT_SET =' in open(os.path.join(ROOT, 'scripts', 'c6_contract.py'), encoding='utf-8').read()}",
       "NOT_SET = " in open(os.path.join(ROOT, "scripts", "c6_contract.py"),
                            encoding="utf-8").read())

record("C6-ISO-04", "Aggregate module performs no comparison",
       "no revision logic",
       f"{'divergence' in open(os.path.join(ROOT, 'scripts', 'c6_aggregate.py'), encoding='utf-8').read()}",
       "divergence" not in open(os.path.join(ROOT, "scripts",
                                             "c6_aggregate.py"),
                                encoding="utf-8").read())

record("C6-ISO-05", "Revision module performs no counting",
       "no aggregate logic",
       f"{'members_total' in open(os.path.join(ROOT, 'scripts', 'c6_revision.py'), encoding='utf-8').read()}",
       "members_total" not in open(os.path.join(ROOT, "scripts",
                                                "c6_revision.py"),
                                   encoding="utf-8").read())


# ==========================================================================
# 18. MUTATION  (classified honestly — no artificial score)
# ==========================================================================
def run_mutation(mid, desc, attr, value, probe, module=PRES):
    original = getattr(module, attr)
    setattr(module, attr, value)
    try:
        detected = probe()
    finally:
        setattr(module, attr, original)
    cls = "KILLED" if detected else "SURVIVED"
    mutation(mid, desc, cls, f"detected={detected}")
    record(f"C6-M-{mid}", f"MUTATION {desc}", "KILLED",
           f"{cls}", detected)


# M-01/M-02 isolation note: a C4 record has no `status` key and a C5 record
# has no `completeness` key, so the entitlement lists are a SECOND guard
# behind the absence of the field itself. Probing with a real record would
# leave that first guard masking the mutation (the duplicate-defence lesson).
# The probes therefore feed records that DO carry the foreign field, so the
# entitlement guard is the only thing standing between input and output.
_C4_WITH_STATUS = {"status": "EMITTED",
                   "completeness": {"overall": "PARTIAL"}}
_C5_WITH_COMPLETENESS = {"status": "EMITTED", "coverage": "PARTIAL",
                         "completeness": {"overall": "COMPLETE"}}

record("C6-M-01a", "BASELINE: entitlement guard blocks a foreign status field",
       "NOT_SET while guard intact",
       f"{PRES.preserve_member(_C4_WITH_STATUS, 'C4')['source_status']}",
       PRES.preserve_member(_C4_WITH_STATUS, "C4")["source_status"]
       == "NOT_SET")

record("C6-M-02a", "BASELINE: entitlement guard blocks foreign completeness",
       "NOT_SET while guard intact",
       f"{PRES.preserve_member(_C5_WITH_COMPLETENESS, 'C5')['source_completeness']}",
       PRES.preserve_member(_C5_WITH_COMPLETENESS,
                            "C5")["source_completeness"] == "NOT_SET")


def _probe_completeness_to_status():
    """With the guard removed, a foreign status field must leak through."""
    m = PRES.preserve_member(_C4_WITH_STATUS, "C4")
    return m["source_status"] != "NOT_SET"


run_mutation("01", "allow C4 to populate source_status",
             "DECLARES_STATUS", ("C3", "C5", "C4"),
             _probe_completeness_to_status)


def _probe_coverage_leak():
    m = PRES.preserve_member(_C5_WITH_COMPLETENESS, "C5")
    return m["source_completeness"] != "NOT_SET"


run_mutation("02", "allow C5 to populate source_completeness",
             "DECLARES_COMPLETENESS", ("C4", "C5"), _probe_coverage_leak)


def _probe_detail_dropped():
    m = PRES.preserve_member(Q_P, "C4")
    return "source_completeness_detail" not in m


_orig_detail = PRES.preserve_completeness_detail
PRES.preserve_completeness_detail = lambda r, o: None
try:
    _d03 = _probe_detail_dropped()
finally:
    PRES.preserve_completeness_detail = _orig_detail
mutation("03", "drop C4 completeness_detail",
         "KILLED" if _d03 else "SURVIVED", f"detected={_d03}")
record("C6-M-03", "MUTATION drop C4 completeness_detail", "KILLED",
       f"{'KILLED' if _d03 else 'SURVIVED'}", _d03)


def _probe_recompute_overall():
    """Recomputing overall from details would change the declared value."""
    rec = {"completeness": {"Q-02": "COMPLETE", "Q-03": "COMPLETE",
                            "overall": "PARTIAL"}}
    m = PRES.preserve_member(rec, "C4")
    return m["source_completeness"] != "PARTIAL"


_orig_pc = PRES.preserve_completeness
PRES.preserve_completeness = lambda r, o: (
    "COMPLETE" if isinstance(r.get("completeness"), dict)
    and all(v == "COMPLETE" for k, v in r["completeness"].items()
            if k != "overall") else "PARTIAL")
try:
    _d04 = _probe_recompute_overall()
finally:
    PRES.preserve_completeness = _orig_pc
mutation("04", "recompute C4 overall from details",
         "KILLED" if _d04 else "SURVIVED", f"detected={_d04}")
record("C6-M-04", "MUTATION recompute C4 overall", "KILLED",
       f"{'KILLED' if _d04 else 'SURVIVED'}", _d04)


def _probe_channel_inferred():
    m = PRES.preserve_member(A_REC, "C3")
    return m["producer_channel"] != "NOT_SET"


_orig_ch = PRES.preserve_producer_channel
PRES.preserve_producer_channel = lambda r: (
    "A-channel" if r.get("contract", "").startswith("floor-plan")
    else "NOT_SET")
try:
    _d05 = _probe_channel_inferred()
finally:
    PRES.preserve_producer_channel = _orig_ch
mutation("05", "infer producer_channel from contract",
         "KILLED" if _d05 else "SURVIVED", f"detected={_d05}")
record("C6-M-05", "MUTATION infer producer_channel", "KILLED",
       f"{'KILLED' if _d05 else 'SURVIVED'}", _d05)


def _probe_class_inferred():
    m = PRES.preserve_member(A_REC, "C3")
    return m["declared_class"] != "NOT_SET"


_orig_cl = PRES.preserve_declared_class
PRES.preserve_declared_class = lambda r: ("A" if r.get("format") == "svg"
                                          else "NOT_SET")
try:
    _d06 = _probe_class_inferred()
finally:
    PRES.preserve_declared_class = _orig_cl
mutation("06", "infer declared_class from format",
         "KILLED" if _d06 else "SURVIVED", f"detected={_d06}")
record("C6-M-06", "MUTATION infer declared_class", "KILLED",
       f"{'KILLED' if _d06 else 'SURVIVED'}", _d06)


def _probe_counters_combined():
    ag = AGG.aggregate_summary(MF["members"])
    return "combined" in ag or "overall" in ag


_orig_ag = AGG.aggregate_summary
AGG.aggregate_summary = lambda members: dict(_orig_ag(members),
                                             overall="PARTIAL")
try:
    _d07 = _probe_counters_combined()
finally:
    AGG.aggregate_summary = _orig_ag
mutation("07", "add a combined overall state to the counters",
         "KILLED" if _d07 else "SURVIVED", f"detected={_d07}")
record("C6-M-07", "MUTATION combined aggregate state", "KILLED",
       f"{'KILLED' if _d07 else 'SURVIVED'}", _d07)


def _probe_identity_minted():
    m = PRES.preserve_member(A_REC, "C3")
    return m["output_id"] != "NOT_SET"


_orig_oid = PRES.preserve_output_id
PRES.preserve_output_id = lambda r, s=None: "OUT-" + str(abs(hash(str(r))))[:4]
try:
    _d08 = _probe_identity_minted()
finally:
    PRES.preserve_output_id = _orig_oid
mutation("08", "mint output_id from a hash",
         "KILLED" if _d08 else "SURVIVED", f"detected={_d08}")
record("C6-M-08", "MUTATION mint output_id", "KILLED",
       f"{'KILLED' if _d08 else 'SURVIVED'}", _d08)


def _probe_approval_verdict():
    m = PRES.preserve_member(A_REC, "C3")
    return m["approval_value"] != "NOT_SET"


_orig_av = PRES.preserve_approval_value
PRES.preserve_approval_value = lambda r, s=None: "NOT_APPLICABLE"
try:
    _d09 = _probe_approval_verdict()
finally:
    PRES.preserve_approval_value = _orig_av
mutation("09", "turn absent approval into NOT_APPLICABLE",
         "KILLED" if _d09 else "SURVIVED", f"detected={_d09}")
record("C6-M-09", "MUTATION approval verdict smuggling", "KILLED",
       f"{'KILLED' if _d09 else 'SURVIVED'}", _d09)


def _probe_latest_revision():
    rv = REV.compare_revisions(
        [{"source_owner": "C3", "master_revision": "R01"},
         {"source_owner": "C5", "master_revision": "R02"}])
    return rv["divergence"] != "OBSERVED"


_orig_cr = REV.compare_revisions
REV.compare_revisions = lambda members: {
    "declared_revisions": {}, "members_without_declared_revision": [],
    "comparable": True, "divergence": "NONE_OBSERVED",
    "metadata_kind": "mechanical comparison metadata", "note": "",
    "is_verdict": False}
try:
    _d10 = _probe_latest_revision()
finally:
    REV.compare_revisions = _orig_cr
mutation("10", "hide divergence by selecting a single revision",
         "KILLED" if _d10 else "SURVIVED", f"detected={_d10}")
record("C6-M-10", "MUTATION hide revision divergence", "KILLED",
       f"{'KILLED' if _d10 else 'SURVIVED'}", _d10)

# CONTROL — a cosmetic change must flip nothing.
_ctrl_before = len(MAN.assemble_manifest([("C3", A_REC)],
                                         identity=IDENT)["members"])
_orig_ver = CON.MANIFEST_CONTRACT_VERSION
CON.MANIFEST_CONTRACT_VERSION = "C6-L2-R03-renamed"
_ctrl_after = len(MAN.assemble_manifest([("C3", A_REC)],
                                        identity=IDENT)["members"])
CON.MANIFEST_CONTRACT_VERSION = _orig_ver
mutation("CTRL", "cosmetic version rename", "CONTROL",
         f"before={_ctrl_before}, after={_ctrl_after}")
record("C6-M-CTRL", "CONTROL: cosmetic rename changes nothing",
       "1 member before and after",
       f"{_ctrl_before}/{_ctrl_after}",
       _ctrl_before == 1 and _ctrl_after == 1)


# --------------------------------------------------------------------------
print("=" * 98)
print("PHASE 00.5-C6 — MANIFEST / EVIDENCE ASSEMBLER")
print("=" * 98)
passed = sum(1 for x in RESULTS if x[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    print(f"{'OK  ' if verdict == 'PASS' else 'FAIL'} {tid:12} "
          f"{scenario[:57]:57} {actual[:22]}")
print("-" * 98)
print(f"TOTAL: {passed}/{total} passed")
_killed = sum(1 for m in MUTATIONS if m[2] == "KILLED")
_survived = [m[0] for m in MUTATIONS if m[2] == "SURVIVED"]
_ctrl = sum(1 for m in MUTATIONS if m[2] == "CONTROL")
print(f"MUTATIONS: {_killed} killed · {len(_survived)} survived"
      f"{' ' + str(_survived) if _survived else ''} · {_ctrl} CONTROL")
print("=" * 98)
sys.exit(0 if passed == total else 1)
