#!/usr/bin/env python3
"""Phase 00.5-C2 — Determinism, Canonicalization & Environment Evidence suite.

Reference: 00.5-C2-DETERMINISM-FINGERPRINT.md R02 (APPROVED/CLOSED).

WHAT THIS SUITE PROVES
  Not "C2 computes fingerprints" — it proves the opposite where it matters:
  that C2 REFUSES to issue engineering fingerprints while DEC-C2-01/02/03/
  05/06/08 are open, and that the infrastructure it does provide is honest
  about its own limits.

Discipline: positive + negative per rule; negatives assert the INTENDED
cause; mutations kill the suite and a CONTROL proves the kills are targeted.

TEST PROJECT — NOT A REAL CLIENT PROJECT
"""

import copy
import hashlib
import io
import json
import os
import sys
import unicodedata
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import c2_fingerprint as FP                                          # noqa: E402
import c2_environment as ENV                                         # noqa: E402
from c2_fingerprint import (                                         # noqa: E402
    canonical_bytes, provisional_digest, stable_sorted,
    issue_engineering_fingerprint, determinism_claim, compare_runs,
    find_volatile_lines, influence_probe, engineering_fingerprints_blocked,
    OPEN_DECISIONS, QUANTIZATION_POLICY, CANONICALIZATION_SPEC_ID,
    PENDING, NOT_ESTABLISHED, PROVISIONAL)

RESULTS = []


def record(tid, scenario, expected, actual, ok):
    RESULTS.append((tid, scenario, expected, actual, "PASS" if ok else "FAIL"))


# --------------------------------------------------------------------------
# Fixture — reuse B6's BASE (already accepted by A/B1..B7). Read-only here.
# --------------------------------------------------------------------------
_src = open(os.path.join(HERE, "test_00_5_B6.py"), encoding="utf-8").read()
_ns = {"__name__": "b6fx", "__file__": os.path.join(HERE, "test_00_5_B6.py")}
try:
    with redirect_stdout(io.StringIO()):
        exec(compile(_src, "test_00_5_B6.py", "exec"), _ns)
except SystemExit:
    pass

BASE = _ns["BASE"]

# ---- caller-supplied projections (C2 does NOT own these: DEC-C2-05 open) --
# TEST-ONLY quantization. Tagged, and never allowed to produce evidence.
TEST_ONLY_DP = 3                      # TEST-ONLY — NOT a DEC-C2-02 decision


def _q(v):
    """TEST-ONLY rounding used purely to make SCI probes comparable."""
    return round(v, TEST_ONLY_DP) if isinstance(v, (int, float)) else v


def x_elements(d):
    """Projection: which element ids exist."""
    return {"walls": stable_sorted([w.get("id") for w in d.get("walls") or []],
                                   key=str),
            "materials": stable_sorted([m.get("id") for m in
                                        d.get("materials") or []], key=str)}


def x_positions(d):
    """Projection: where things are (TEST-ONLY quantization)."""
    out = []
    for w in stable_sorted(d.get("walls") or [], key=lambda w: str(w.get("id"))):
        out.append({"id": w.get("id"),
                    "start": [_q(v) for v in (w.get("start") or [])],
                    "end": [_q(v) for v in (w.get("end") or [])]})
    return out


def x_materials(d):
    """Projection: element -> material binding."""
    out = []
    for m in stable_sorted(d.get("materials") or [],
                           key=lambda m: str(m.get("id"))):
        out.append({"id": m.get("id"),
                    "applied_to": stable_sorted(m.get("applied_to") or [],
                                                key=str)})
    return out


def x_cameras(d):
    out = []
    for c in stable_sorted(d.get("cameras") or [], key=lambda c: str(c.get("id"))):
        out.append({"id": c.get("id"), "pos": [_q(v) for v in c.get("pos") or []],
                    "target": [_q(v) for v in c.get("target") or []],
                    "fov": _q(c.get("fov_deg"))})
    return out


CAM = {"id": "CAM-01", "pos": [0, 0, 1600], "target": [1000, 1000, 1200],
       "fov_deg": 60, "status": "C"}


def with_cam(d):
    e = copy.deepcopy(d)
    e["cameras"] = [dict(CAM)]
    return e


# ==========================================================================
# 1. POSITIVE — infrastructure that works today
# ==========================================================================
_a = {"b": 1, "a": 2, "z": [3, 1]}
_b = {"a": 2, "z": [3, 1], "b": 1}
record("C2-P-01", "Canonical form: key order does not change the bytes",
       "identical bytes", f"equal={canonical_bytes(_a) == canonical_bytes(_b)}",
       canonical_bytes(_a) == canonical_bytes(_b))

_d1 = provisional_digest(_a)["digest"]
_d2 = provisional_digest(_b)["digest"]
record("C2-P-02", "Provisional digest is stable across key reordering",
       "same digest", f"equal={_d1 == _d2}", _d1 == _d2)

_ids = ["W-10", "W-02", "W-01", "W-21", "W-03"]
record("C2-P-03", "stable_sorted gives a total, reproducible order",
       "sorted deterministically",
       f"{stable_sorted(_ids, key=str)}",
       stable_sorted(_ids, key=str) == ["W-01", "W-02", "W-03", "W-10", "W-21"])

_env = ENV.capture_environment()
_envfp = ENV.env_fingerprint(_env)
record("C2-P-04", "ENV-FP captures runtime/os/libs/seed/locale/tz",
       "all sections present",
       f"keys={sorted(_env.keys())}",
       set(_env) == {"runtime", "os_arch", "libraries", "ordering", "locale",
                     "timezone", "configuration"})

record("C2-P-05", "ENV-FP is reproducible within one environment",
       "same env_fp", f"equal={ENV.env_fingerprint(_env)['env_fp'] == _envfp['env_fp']}",
       ENV.env_fingerprint(_env)["env_fp"] == _envfp["env_fp"])

_txt = canonical_bytes({"n": "غرفة"}).decode("utf-8")
record("C2-P-06", "Unicode is emitted as NFC UTF-8, not escaped",
       "literal Arabic, no \\u escapes",
       f"has_literal={'غرفة' in _txt}, has_escape={'\\\\u' in _txt}",
       "غرفة" in _txt and "\\u" not in _txt)

_claim = determinism_claim(d0_observed_in_case=True)
record("C2-P-07", "Determinism claim is scoped, never generalised",
       "D0 observed-only, D1 NOT_ESTABLISHED, D2 NOT_CLAIMED",
       f"{_claim['D0']} | {_claim['D1']} | {_claim['D2']}",
       "OBSERVED" in _claim["D0"] and _claim["D1"].endswith("NOT_ESTABLISHED")
       and _claim["D2"].endswith("NOT_CLAIMED"))


# ==========================================================================
# 2. NEGATIVE — the refusal machinery
# ==========================================================================
_blocked, _blk = engineering_fingerprints_blocked()
record("C2-N-01", "Engineering fingerprints are blocked while decisions open",
       "blocked=True with 6 decisions",
       f"blocked={_blocked}, n={len(_blk)}",
       _blocked and set(_blk) == {"DEC-C2-01", "DEC-C2-02", "DEC-C2-03",
                                  "DEC-C2-05", "DEC-C2-06", "DEC-C2-08"})

_r = issue_engineering_fingerprint("master_hash", {"any": "payload"})
record("C2-N-02", "Issuing master_hash abstains, returns no digest",
       "issued=False, no digest key",
       f"issued={_r['issued']}, has_digest={'digest' in _r}",
       _r["issued"] is False and "digest" not in _r)

record("C2-N-03", "Refusal names the blocking decisions explicitly",
       "blocking_decisions listed",
       f"{_r['blocking_decisions']}",
       len(_r["blocking_decisions"]) == 6)

record("C2-N-04", "Refusal is not usable as evidence",
       "usable_as_evidence=False",
       f"{_r['usable_as_evidence']}", _r["usable_as_evidence"] is False)

record("C2-N-05", "Quantization policy is PENDING, no number chosen",
       PENDING, f"{QUANTIZATION_POLICY}", QUANTIZATION_POLICY == PENDING)

record("C2-N-06", "Canonicalization spec id is NOT_ESTABLISHED (GAP-C-04)",
       NOT_ESTABLISHED, f"{CANONICALIZATION_SPEC_ID}",
       CANONICALIZATION_SPEC_ID == NOT_ESTABLISHED)

_pd = provisional_digest({"x": 1})
record("C2-N-07", "Provisional digest declares it is not evidence",
       "status=PROVISIONAL, usable=False",
       f"{_pd['status']}, usable={_pd['usable_as_evidence']}",
       _pd["status"] == PROVISIONAL and _pd["usable_as_evidence"] is False)

record("C2-N-08", "Hash algorithm is carried as PROPOSED, not decided",
       "algorithm_status=PROPOSED",
       f"{_pd['algorithm_status']} / {ENV.HASH_STATUS}",
       _pd["algorithm_status"] == "PROPOSED" and ENV.HASH_STATUS == "PROPOSED")


# ==========================================================================
# 3. BOUNDARY
# ==========================================================================
record("C2-BD-01", "float noise: 0.1+0.2 != 0.3 is visible to canonical form",
       "different bytes",
       f"equal={canonical_bytes({'v': 0.1+0.2}) == canonical_bytes({'v': 0.3})}",
       canonical_bytes({"v": 0.1 + 0.2}) != canonical_bytes({"v": 0.3}))

record("C2-BD-02", "float saturation: 1e16+1 collapses to 1e16",
       "collapse observed", f"{repr(1e16+1.0)}", (1e16 + 1.0) == 1e16)

_n1 = provisional_digest({"v": 1000.0000000000001})["digest"]
_n2 = provisional_digest({"v": 1000.0})["digest"]
record("C2-BD-03", "Un-quantized float noise changes the digest (why DEC-C2-02 matters)",
       "digests differ", f"differ={_n1 != _n2}", _n1 != _n2)

# TEST-ONLY quantization boundary — explicitly not a decision
record("C2-BD-04", "TEST-ONLY quantization hides sub-threshold change",
       "6000.0004 == 6000.0 at TEST-ONLY dp=3",
       f"{_q(6000.0004)} vs {_q(6000.0)}", _q(6000.0004) == _q(6000.0))

record("C2-BD-05", "TEST-ONLY quantization keeps supra-threshold change",
       "6000.5 != 6000.0", f"{_q(6000.5)} vs {_q(6000.0)}",
       _q(6000.5) != _q(6000.0))

_nfd = unicodedata.normalize("NFD", "غرفة")
record("C2-BD-06", "NFC/NFD normalise to one canonical byte sequence",
       "same bytes", f"equal={canonical_bytes({'n': _nfd}) == canonical_bytes({'n': 'غرفة'})}",
       canonical_bytes({"n": _nfd}) == canonical_bytes({"n": "غرفة"}))

_empty = issue_engineering_fingerprint("positions_hash", {})
record("C2-BD-07", "Empty payload still abstains (no trivial fingerprint)",
       "issued=False", f"issued={_empty['issued']}", not _empty["issued"])


# ==========================================================================
# 4. SEMANTIC COVERAGE / INFLUENCE ISOLATION  (R02 s12.1)
# ==========================================================================
_b0 = with_cam(BASE)

# --- influence: changes that MUST be visible ---
_g = copy.deepcopy(_b0)
_g["walls"][0]["end"] = [6500, 0]
record("SCI-01", "geometry change is visible to the positions projection",
       "changed=True", f"{influence_probe(_b0, _g, x_positions)['changed']}",
       influence_probe(_b0, _g, x_positions)["changed"])

_e = copy.deepcopy(_b0)
_e["walls"].append({"id": "W-99", "start": [0, 0], "end": [10, 0],
                    "height": {"value": 2800, "unit": "mm", "status": "C",
                               "source_type": "CLIENT_INPUT",
                               "source_ref": "x", "recorded_on": "2026-09-12"}})
record("SCI-02", "adding an element changes the element-set projection",
       "changed=True", f"{influence_probe(_b0, _e, x_elements)['changed']}",
       influence_probe(_b0, _e, x_elements)["changed"])

_p = copy.deepcopy(_b0)
_p["walls"][1]["start"] = [6000, 5]
record("SCI-03", "position change is visible to the positions projection",
       "changed=True", f"{influence_probe(_b0, _p, x_positions)['changed']}",
       influence_probe(_b0, _p, x_positions)["changed"])

_m = copy.deepcopy(_b0)
_m["materials"][0]["applied_to"] = ["W-02"]
record("SCI-04", "material re-binding is visible to the materials projection",
       "changed=True", f"{influence_probe(_b0, _m, x_materials)['changed']}",
       influence_probe(_b0, _m, x_materials)["changed"])

_c = copy.deepcopy(_b0)
_c["cameras"][0]["fov_deg"] = 75
record("SCI-05", "camera change is visible to the camera projection",
       "changed=True", f"{influence_probe(_b0, _c, x_cameras)['changed']}",
       influence_probe(_b0, _c, x_cameras)["changed"])

# --- isolation: changes that MUST NOT be visible ---
_note = copy.deepcopy(_b0)
_note["walls"][0]["note"] = "editorial typo fix"
_iso_note = [influence_probe(_b0, _note, x)["changed"]
             for x in (x_elements, x_positions, x_materials, x_cameras)]
record("SCI-06", "editorial note changes no geometric projection",
       "all False", f"{_iso_note}", not any(_iso_note))

_pres = copy.deepcopy(_b0)
_pres["presentation"] = {"line_weight": 0.35, "shadow": True,
                         "palette": "warm"}
_iso_pres = [influence_probe(_b0, _pres, x)["changed"]
             for x in (x_elements, x_positions, x_materials, x_cameras)]
record("SCI-07", "presentation parameters change no geometric projection",
       "all False", f"{_iso_pres}", not any(_iso_pres))

_ts = copy.deepcopy(_b0)
_ts["meta"]["exported_on"] = "2026-09-14T01:02:03Z"
_iso_ts = [influence_probe(_b0, _ts, x)["changed"]
           for x in (x_elements, x_positions, x_materials, x_cameras)]
record("SCI-08", "timestamp change enters no geometric projection",
       "all False", f"{_iso_ts}", not any(_iso_ts))

_ord_ = copy.deepcopy(_b0)
_ord_["walls"] = list(reversed(_ord_["walls"]))
_ord_["materials"][0] = {k: v for k, v in
                         reversed(list(_ord_["materials"][0].items()))}
_iso_ord = [influence_probe(_b0, _ord_, x)["changed"]
            for x in (x_elements, x_materials)]
record("SCI-09", "array/key reordering changes no projection (total order)",
       "all False", f"{_iso_ord}", not any(_iso_ord))

# SCI-10 — units. NOT decided here.
record("SCI-10", "unit representation semantics deferred to DEC-C2-08",
       "DEC-C2-08 open, no ruling taken",
       f"open={'DEC-C2-08' in OPEN_DECISIONS}",
       "DEC-C2-08" in OPEN_DECISIONS)


# ==========================================================================
# 5. MUTATION
# ==========================================================================
def mutate(tid, scenario, attr, value, probe, module=FP, expect=True):
    """Mutate a module attribute and confirm the probe notices.

    IMPORTANT: probes must reach the mutated attribute THROUGH THE MODULE
    (FP.x / ENV.x). A name bound by `from module import x` is resolved at
    import time, so patching module.x would never reach it and the mutation
    would be silently masked — a defect found and fixed in this suite.
    """
    original = getattr(module, attr)
    setattr(module, attr, value)
    try:
        got = probe()
    finally:
        setattr(module, attr, original)
    record(tid, scenario, f"detected={expect}", f"detected={got}", got == expect)


def _probe_unsorted():
    return FP.canonical_bytes(_a) != FP.canonical_bytes(_b)


mutate("C2-M-01", "Disable sort_keys -> C2-P-01 must die",
       "canonical_bytes",
       lambda o: json.dumps(o, sort_keys=False, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8"),
       _probe_unsorted)


def _probe_refusal_dies():
    """Emptying the registry must make the refusal STOP refusing.

    It must still never hand back a usable digest: the issuance path raises
    DecisionPendingError instead. Either way the refusal test C2-N-02 is no
    longer satisfied, which is what this mutation proves.
    """
    try:
        res = issue_engineering_fingerprint("master_hash", {"a": 1})
    except FP.DecisionPendingError:
        return True                     # refusal record no longer produced
    return res.get("issued") is not False


mutate("C2-M-02", "Empty the open-decision registry -> refusal tests must die",
       "OPEN_DECISIONS", {}, _probe_refusal_dies)


def _probe_no_silent_digest():
    """Even with the registry emptied, no usable digest may escape."""
    try:
        res = issue_engineering_fingerprint("x", {})
    except FP.DecisionPendingError:
        return True                     # fails loudly — acceptable
    return res.get("usable_as_evidence") is False


mutate("C2-M-03", "Closing decisions never yields a silent usable digest",
       "OPEN_DECISIONS", {}, _probe_no_silent_digest)


def _probe_ascii():
    t = FP.canonical_bytes({"n": "غرفة"}).decode("utf-8")
    return "\\u" in t


mutate("C2-M-04", "Force ensure_ascii -> C2-P-06 must die",
       "canonical_bytes",
       lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True).encode("utf-8"),
       _probe_ascii)


# Baseline: the unset seed is reported with the literal token "NOT_SET".
_seed_now = ENV.capture_environment()["ordering"]["PYTHONHASHSEED"]
record("C2-M-05a", "Baseline: unset PYTHONHASHSEED reported as literal NOT_SET",
       "NOT_SET", f"{_seed_now}", _seed_now == "NOT_SET")


def _probe_env_hidden():
    """Compare against the LITERAL token, not ENV.NOT_SET.

    Comparing against ENV.NOT_SET would move with the mutation and mask it.
    """
    e = ENV.capture_environment()
    return e["ordering"]["PYTHONHASHSEED"] != "NOT_SET"


mutate("C2-M-05", "Replace the NOT_SET token -> honesty test must die",
       "NOT_SET", "unknown-ish", _probe_env_hidden, module=ENV)

# CONTROL — an unrelated change must not flip the asserted rules.
_ctrl_before = canonical_bytes(_a) == canonical_bytes(_b)
_orig = FP.PROVISIONAL
FP.PROVISIONAL = "PROVISIONAL_RENAMED"
_ctrl_after = canonical_bytes(_a) == canonical_bytes(_b)
FP.PROVISIONAL = _orig
record("C2-M-06", "CONTROL: cosmetic rename does not flip canonical equality",
       "True before and after", f"before={_ctrl_before}, after={_ctrl_after}",
       _ctrl_before and _ctrl_after)


# ==========================================================================
# 6. ISOLATION
# ==========================================================================
_fp_src = open(os.path.join(ROOT, "scripts", "c2_fingerprint.py"),
               encoding="utf-8").read()
_env_src = open(os.path.join(ROOT, "scripts", "c2_environment.py"),
                encoding="utf-8").read()
_both = _fp_src + _env_src
_code_only = "\n".join(ln.split("#")[0] for ln in _both.splitlines()
                       if not ln.strip().startswith("#"))

_validators = ["validate_topology", "validate_furniture", "validate_movement",
               "validate_doors", "validate_formulas", "validate_outputs",
               "validate_refs", "validate_revisions", "validate_lifecycle",
               "validate_temporal", "validate_blocking", "schema_gate"]
_imported = [m for m in _validators if f"import {m}" in _both]
record("C2-ISO-01", "C2 imports no validator (does not re-run B-series)",
       "none", f"found={_imported}", not _imported)

record("C2-ISO-02", "C2 does not import C1 (no gate duplication)",
       "no c1 import", f"found={'c1_preconditions' in _both}",
       "c1_preconditions" not in _both)

# C2 must not RETURN a fidelity/approval verdict. Prose that disclaims
# ownership ("the fidelity verdict belongs to D") is documentation, so the
# check targets emitted keys, not the presence of a word in text.
_verdict_keys = ['"fidelity"', '"matches_master"', '"is_correct"',
                 '"approved"', '"verdict"', '"correct"']
_leak = [k for k in _verdict_keys if k in _code_only]
record("C2-ISO-03", "C2 emits no fidelity/approval verdict key (that is D/E)",
       "no verdict keys returned", f"leaked={_leak}", not _leak)

# ...and prove it positively: nothing C2 returns answers "does it match?"
_probe_keys = set(issue_engineering_fingerprint("master_hash", {})) \
    | set(provisional_digest({"a": 1})) | set(compare_runs(b"a", b"b"))
_verdictish = {k for k in _probe_keys
               if k in {"fidelity", "matches_master", "approved", "verdict"}}
record("C2-ISO-03b", "No returned record carries a fidelity/approval field",
       "none", f"found={sorted(_verdictish)}", not _verdictish)

record("C2-ISO-04", "C2 does not define fingerprint scope (DEC-C2-05 open)",
       "scope owned by caller",
       f"{influence_probe(_b0, _b0, x_elements)['scope_owner'][:24]}",
       "caller" in influence_probe(_b0, _b0, x_elements)["scope_owner"])

record("C2-ISO-05", "Diagnostics draw no determinism conclusion",
       "d2_claimed=False",
       f"{compare_runs(b'a', b'a')['d2_claimed']}",
       compare_runs(b"a", b"a")["d2_claimed"] is False)


# ==========================================================================
# 7. ANTI-SMUGGLING
# ==========================================================================
_r2 = issue_engineering_fingerprint(
    "positions_hash", {"p": 1}, quantization=3, algorithm="sha256",
    scope="everything")
record("C2-AS-01", "Caller-supplied quantization/algorithm cannot unblock issuance",
       "issued=False despite parameters",
       f"issued={_r2['issued']}, supplied={bool(_r2['supplied_parameters'])}",
       not _r2["issued"])

record("C2-AS-02", "No open decision is silently closed by the code",
       "6 decisions still open", f"n={len(OPEN_DECISIONS)}",
       set(OPEN_DECISIONS) == {"DEC-C2-01", "DEC-C2-02", "DEC-C2-03",
                               "DEC-C2-05", "DEC-C2-06", "DEC-C2-08"})

_cl = determinism_claim(d0_observed_in_case=True)
record("C2-AS-03", "D0-provable is never asserted (SEC not approved)",
       NOT_ESTABLISHED, f"{_cl['D0_provable']}",
       _cl["D0_provable"] == NOT_ESTABLISHED)

record("C2-AS-04", "D2 is never claimed even when bytes happen to match",
       "d2_claimed=False on equal bytes",
       f"{compare_runs(b'same', b'same')['d2_claimed']}",
       compare_runs(b"same", b"same")["d2_claimed"] is False)

_e1 = ENV.env_fingerprint()
_e2 = copy.deepcopy(_e1)
_e2["environment"]["libraries"]["ezdxf"] = "9.9.9"
_differs, _keys = ENV.environments_differ(_e1, _e2)
record("C2-AS-05", "ENV drift is reported as environment difference only",
       "differs=True, no engineering conclusion",
       f"differs={_differs}, keys={_keys}",
       _differs and _keys == ["libraries/ezdxf"])

_rules = " ".join(_e1["interpretation_rules"]).lower()
record("C2-AS-06", "ENV-FP carries both interpretation rules with it",
       "different!=proof, same!=correctness",
       f"has_both={'not proof of a different' in _rules and 'not proof of correctness' in _rules}",
       "not proof of a different" in _rules and "not proof of correctness" in _rules)

record("C2-AS-07", "Provisional digest cannot be mistaken for evidence",
       "explicit reason present",
       f"has_reason={'DEC-C2-03' in _pd['reason']}",
       "DEC-C2-03" in _pd["reason"])

record("C2-AS-08", "Volatility diagnostics do not normalise or decide",
       "normalised=False",
       f"{find_volatile_lines('a\\nb', 'a\\nc')['normalised']}",
       find_volatile_lines("a\nb", "a\nc")["normalised"] is False)

_tags = ("TEST-ONLY" in open(os.path.join(HERE, "test_00_5_C2.py"),
                             encoding="utf-8").read())
record("C2-AS-09", "Test-only quantization is tagged TEST-ONLY in the suite",
       "tag present", f"tagged={_tags}", _tags)


# ==========================================================================
# 8. NO-WRITE
# ==========================================================================
def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


_tpl = os.path.join(ROOT, "project_master.template.json")
_sch = os.path.join(ROOT, "project_master.schema.json")
_before = (_sha(_tpl), _sha(_sch))

_snapshot = copy.deepcopy(_b0)
ENV.env_fingerprint()
provisional_digest(_b0)
issue_engineering_fingerprint("master_hash", _b0)
influence_probe(_b0, _b0, x_positions)
compare_runs(b"x", b"y")

_after = (_sha(_tpl), _sha(_sch))
record("C2-NW-01", "C2 does not mutate the in-memory model",
       "model identical", f"identical={_snapshot == _b0}", _snapshot == _b0)
record("C2-NW-02", "C2 does not modify template or schema",
       "sha256 unchanged", f"unchanged={_before == _after}", _before == _after)
record("C2-NW-03", "C2 never creates project_master.json",
       "absent", f"exists={os.path.exists(os.path.join(ROOT, 'project_master.json'))}",
       not os.path.exists(os.path.join(ROOT, "project_master.json")))

_writes = ("open(" in _code_only and "w" in _code_only.split("open(")[1][:12]) \
    if "open(" in _code_only else False
record("C2-NW-04", "C2 modules contain no file-write call",
       "no write mode open()", f"writes={_writes}", not _writes)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
print("=" * 94)
print("PHASE 00.5-C2 — DETERMINISM / CANONICALIZATION / ENVIRONMENT EVIDENCE")
print("=" * 94)
passed = sum(1 for r in RESULTS if r[4] == "PASS")
total = len(RESULTS)
for tid, scenario, expected, actual, verdict in RESULTS:
    mark = "OK  " if verdict == "PASS" else "FAIL"
    print(f"{mark} {tid:10} {scenario[:55]:55} {actual[:29]}")
print("-" * 94)
print(f"TOTAL: {passed}/{total} passed")
print("=" * 94)
sys.exit(0 if passed == total else 1)
