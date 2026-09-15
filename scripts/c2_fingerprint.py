#!/usr/bin/env python3
"""
00.5-C2 — CANONICALIZATION & FINGERPRINT INFRASTRUCTURE
Reference: 00.5-C2-DETERMINISM-FINGERPRINT.md R02 (APPROVED/CLOSED).

WHAT THIS MODULE DOES
  It builds the *infrastructure* for canonicalization and fingerprinting, and
  it ENFORCES THE REFUSAL to emit any final engineering fingerprint while the
  governing decisions are open.

  The headline capability of C2 today is not "compute hashes". It is:
      prove that the system ABSTAINS from issuing fingerprints it has no
      mandate to issue.

OPEN DECISIONS THAT BLOCK ENGINEERING FINGERPRINTS  (R02 s16)
      DEC-C2-01  fingerprint count / naming
      DEC-C2-02  quantization policy
      DEC-C2-03  hash algorithm
      DEC-C2-05  master_hash scope
      DEC-C2-06  INPUT-FP vs master_hash
      DEC-C2-08  unit representation semantics
  None of them is decided here. The code does not pick a default, does not
  silently choose, and does not let a test value escape as evidence.
  Choosing any of them inside implementation is AS-C2-13 (hidden decision).

WHAT IS IMPLEMENTABLE NOW (R02 Gate Card, "ما يمكن تنفيذه")
  * serialization / canonical form   (the rule itself is proposed, see below)
  * ordering discipline
  * volatility detection + two-run comparison  (diagnostics, not evidence)
  * refusal machinery + honest declaration

CMR STATUS
  CMR is an architectural DRAFT, not a contract (R02 s2). This module can
  build a canonical *view* for diagnostics, but it must not fix the scope of
  master_hash or of any fingerprint. Nothing here is written to the master.
"""

import hashlib
import json
import unicodedata

# --------------------------------------------------------------------------
# Decision registry — the single source of "what is still undecided".
# Implementation reads this; it never edits it to unblock itself.
# --------------------------------------------------------------------------
PENDING = "PENDING"
NOT_ESTABLISHED = "NOT_ESTABLISHED"
UNDECIDED = "UNDECIDED"
PROVISIONAL = "PROVISIONAL"
TEST_ONLY = "TEST_ONLY"

OPEN_DECISIONS = {
    "DEC-C2-01": "fingerprint count/naming",
    "DEC-C2-02": "quantization policy",
    "DEC-C2-03": "hash algorithm",
    "DEC-C2-05": "master_hash scope",
    "DEC-C2-06": "INPUT-FP vs master_hash semantics",
    "DEC-C2-08": "unit representation semantics",
}

# Decisions that specifically gate ENGINEERING fingerprints.
ENGINEERING_BLOCKING_DECISIONS = ("DEC-C2-01", "DEC-C2-02", "DEC-C2-03",
                                  "DEC-C2-05", "DEC-C2-06", "DEC-C2-08")

# Determinism claim levels — defaults are the honest ones.
D0_OBSERVED = "D0=OBSERVED_IN_MEASURED_CASE"
D0_NOT_CLAIMED = "D0=NOT_CLAIMED"
D1_NOT_ESTABLISHED = "D1=NOT_ESTABLISHED"      # GAP-C-04 / C-14 / C-02
D2_NOT_CLAIMED = "D2=NOT_CLAIMED"

# Quantization: NO number is chosen here. DEC-C2-02 is open.
QUANTIZATION_POLICY = PENDING


class DecisionPendingError(RuntimeError):
    """Raised when code tries to produce output that an open decision blocks."""


def engineering_fingerprints_blocked():
    """Return (blocked, [decision ids]). True while any gating decision is open."""
    blocking = [d for d in ENGINEERING_BLOCKING_DECISIONS if d in OPEN_DECISIONS]
    return bool(blocking), blocking


# --------------------------------------------------------------------------
# Serialization / canonical form  (R02 s3 — itself PROPOSED under GAP-C-04)
# --------------------------------------------------------------------------
CANONICALIZATION_SPEC_ID = NOT_ESTABLISHED     # GAP-C-04 still open


def canonical_bytes(obj):
    """Serialize to the proposed canonical form.

    sort_keys      -> key order cannot change the bytes   (measured)
    separators     -> formatting cannot change the bytes
    ensure_ascii=F -> one byte sequence per text          (measured)
    NFC            -> one normal form per text
    UTF-8, \\n     -> stable encoding and line endings
    """
    return json.dumps(_nfc(obj), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _nfc(obj):
    """Normalise all text to NFC, recursively. Order of containers preserved."""
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {_nfc(k): _nfc(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_nfc(v) for v in obj]
    return obj


def stable_sorted(items, key):
    """Total, explicit ordering. Never rely on set/dict insertion order."""
    return sorted(items, key=key)


# --------------------------------------------------------------------------
# Provisional digest — diagnostics ONLY
# --------------------------------------------------------------------------
def provisional_digest(obj, algorithm="sha256"):
    """A digest for DIAGNOSTIC comparison only.

    Returns a dict that carries its own non-final status, so the value cannot
    be lifted out of context and presented as evidence. DEC-C2-03 is open.
    """
    return {
        "digest": hashlib.new(algorithm, canonical_bytes(obj)).hexdigest(),
        "algorithm": algorithm,
        "algorithm_status": "PROPOSED",
        "status": PROVISIONAL,
        "usable_as_evidence": False,
        "reason": "DEC-C2-03 (hash algorithm) is not decided; "
                  "diagnostic comparison only.",
    }


# --------------------------------------------------------------------------
# THE REFUSAL — the core deliverable of C2 implementation today
# --------------------------------------------------------------------------
def issue_engineering_fingerprint(name, payload, quantization=None,
                                  algorithm=None, scope=None):
    """Attempt to issue a FINAL engineering fingerprint.

    While any gating decision is open this ALWAYS abstains and returns a
    refusal record. It never returns a usable engineering digest, and it never
    invents a quantization value, an algorithm, or a scope in order to proceed.
    """
    blocked, blocking = engineering_fingerprints_blocked()
    supplied = {"quantization": quantization, "algorithm": algorithm,
                "scope": scope}
    if blocked:
        return {
            "requested": name,
            "issued": False,
            "decision": "ABSTAINED",
            "status": NOT_ESTABLISHED,
            "blocking_decisions": blocking,
            "quantization_policy": QUANTIZATION_POLICY,
            "canonicalization_spec": CANONICALIZATION_SPEC_ID,
            "supplied_parameters": supplied,
            "note": ("C2 must not emit a final engineering fingerprint while "
                     "governing decisions are open. Any value supplied by a "
                     "caller is ignored and does not unblock issuance."),
            "usable_as_evidence": False,
        }
    # Unreachable while decisions are open. Kept explicit so that closing the
    # decisions is a deliberate, reviewable act rather than a silent default.
    raise DecisionPendingError(
        "Issuance path requires an approved quantization policy, algorithm, "
        "scope and naming. Implement only after the decisions are approved.")


def determinism_claim(d0_observed_in_case=False):
    """The only determinism claim C2 may currently make."""
    return {
        "D0": D0_OBSERVED if d0_observed_in_case else D0_NOT_CLAIMED,
        "D0_scope": ("single measured case only; no general guarantee"
                     if d0_observed_in_case else "not measured here"),
        "D0_provable": NOT_ESTABLISHED,      # needs SEC — DEC-C2-07
        "semantic_extraction_contract": NOT_ESTABLISHED,
        "D1": D1_NOT_ESTABLISHED,
        "D1_reason": "GAP-C-04 (no canonicalization spec), "
                     "GAP-C-14 (volatile data inside DXF body), "
                     "GAP-C-02 (environment not reproducible)",
        "D2": D2_NOT_CLAIMED,
    }


# --------------------------------------------------------------------------
# Diagnostics — measuring non-determinism without claiming anything
# --------------------------------------------------------------------------
def compare_runs(bytes_a, bytes_b):
    """Compare two raw artefacts. Reports FACTS, draws no conclusion.

    Explicitly does NOT say "deterministic" or "identical output" — byte
    equality is only byte equality (R02 s1, AS-C2-09).
    """
    same = bytes_a == bytes_b
    return {
        "byte_equal": same,
        "size_a": len(bytes_a),
        "size_b": len(bytes_b),
        "interpretation": (
            "Byte equality observed for these two artefacts under one "
            "environment. This is not a D2 claim."
            if same else
            "Bytes differ. This alone says nothing about semantic equality; "
            "D0 requires a Semantic Extraction Contract (DEC-C2-07)."),
        "d2_claimed": False,
    }


def find_volatile_lines(text_a, text_b):
    """Locate differing lines between two text artefacts.

    A diagnostic aid for building a future canonicalization spec. It reports
    WHERE artefacts differ; it does not normalise them and does not decide
    what is volatile — that is part of GAP-C-04 / GAP-C-14.
    """
    la, lb = text_a.splitlines(), text_b.splitlines()
    diffs = []
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            diffs.append({"line": i, "a": x, "b": y})
    return {
        "differing_lines": diffs,
        "count": len(diffs),
        "length_mismatch": len(la) != len(lb),
        "normalised": False,
        "note": "Diagnostic only. Deciding which fields are volatile and how "
                "to normalise them belongs to GAP-C-04 / GAP-C-14.",
    }


# --------------------------------------------------------------------------
# Influence probe — supports Semantic Coverage / Influence Isolation (s12.1)
# --------------------------------------------------------------------------
def influence_probe(before, after, extractor):
    """Did a model edit change the projected view that `extractor` returns?

    Returns a provisional, diagnostic answer used by the SCI tests. The
    extractor is supplied by the CALLER: C2 does not define what the geometric
    scope of any fingerprint is (DEC-C2-05), so it cannot own these projections.
    """
    da = provisional_digest(extractor(before))["digest"]
    db = provisional_digest(extractor(after))["digest"]
    return {
        "changed": da != db,
        "before": da,
        "after": db,
        "status": PROVISIONAL,
        "usable_as_evidence": False,
        "scope_owner": "caller (DEC-C2-05 open — C2 does not define scope)",
    }
