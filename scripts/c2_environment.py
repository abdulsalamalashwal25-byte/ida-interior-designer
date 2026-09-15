#!/usr/bin/env python3
"""
00.5-C2 — ENVIRONMENT EVIDENCE (ENV-FP)
Reference: 00.5-C2-DETERMINISM-FINGERPRINT.md R02 (APPROVED/CLOSED) section 5.1.

WHAT THIS OWNS
  Capturing the execution environment HONESTLY and turning it into evidence.

THE TWO STANDING RULES (R02 section 5.1) — never weakened anywhere:
  * Different ENV-FP  != proof of a different engineering result.
  * Same ENV-FP       != proof of correctness.
  ENV-FP is CONTEXTUAL EVIDENCE. The fidelity verdict belongs to D.

HONESTY RULE
  A value that cannot be read is recorded as the literal string "NOT_SET".
  It is never guessed, never inferred, never omitted. Hiding it is AS-C2-07.

NOTE ON THE ALGORITHM
  DEC-C2-03 is OPEN. SHA-256 is a PROPOSAL only. Everything this module
  produces is therefore tagged PROVISIONAL and must not be presented as a
  final decision. See c2_fingerprint.ENGINEERING_FINGERPRINTS_BLOCKED.
"""

import hashlib
import json
import locale as _locale
import os
import platform
import sys
import time

NOT_SET = "NOT_SET"

# DEC-C2-03 is OPEN. This names the algorithm as a proposal, so that reading
# the code cannot be mistaken for reading a decision.
PROPOSED_HASH_ALGORITHM = "sha256"
HASH_STATUS = "PROPOSED"          # never "APPROVED" until DEC-C2-03 lands

# Libraries whose versions matter to generation. Absence is recorded, not
# hidden: GAP-C-02 says the environment is not reproducible today.
TRACKED_LIBRARIES = ("ezdxf", "trimesh", "reportlab", "shapely", "pptx",
                     "matplotlib", "numpy", "jsonschema")


def _safe(fn):
    try:
        v = fn()
    except Exception:
        return NOT_SET
    if v is None or v == "":
        return NOT_SET
    return v


def library_versions(names=TRACKED_LIBRARIES):
    """Report each tracked library's version, or NOT_SET when unavailable.

    A missing library is evidence (GAP-C-02), not an error to be smoothed over.
    """
    import importlib
    out = {}
    for name in names:
        try:
            mod = importlib.import_module(name)
            out[name] = str(getattr(mod, "__version__", NOT_SET) or NOT_SET)
        except Exception:
            out[name] = NOT_SET
    return out


def capture_environment():
    """Capture the execution environment. Read-only; writes nothing anywhere."""
    return {
        "runtime": {
            "implementation": _safe(platform.python_implementation),
            "version": _safe(lambda: platform.python_version()),
            "executable_hint": _safe(lambda: os.path.basename(sys.executable)),
        },
        "os_arch": {
            "system": _safe(platform.system),
            "release_family": _safe(lambda: platform.system()),
            "machine": _safe(platform.machine),
        },
        "libraries": library_versions(),
        "ordering": {
            # Measured fact: PYTHONHASHSEED is not pinned in this sandbox.
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED") or NOT_SET,
        },
        "locale": {
            "getlocale": _safe(lambda: "|".join(
                str(x) if x else NOT_SET for x in _locale.getlocale())),
            "preferred_encoding": _safe(
                lambda: _locale.getpreferredencoding(False)),
            "LANG": os.environ.get("LANG") or NOT_SET,
            "LC_ALL": os.environ.get("LC_ALL") or NOT_SET,
        },
        "timezone": {
            "TZ": os.environ.get("TZ") or NOT_SET,
            "tzname": _safe(lambda: "|".join(time.tzname)),
        },
        "configuration": {
            # Generation options are declared by the caller; C2 invents none.
            "declared_by_caller": NOT_SET,
        },
    }


def canonical_environment_bytes(env):
    """Canonical form of the environment record (serialization rule, R02 s3)."""
    return json.dumps(env, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def env_fingerprint(env=None):
    """Return the PROVISIONAL environment fingerprint record.

    Marked provisional because DEC-C2-03 (algorithm) is still open. It is
    evidence about the environment only — never about the engineering result.
    """
    env = env if env is not None else capture_environment()
    digest = hashlib.new(PROPOSED_HASH_ALGORITHM,
                         canonical_environment_bytes(env)).hexdigest()
    return {
        "env_fp": digest,
        "algorithm": PROPOSED_HASH_ALGORITHM,
        "algorithm_status": HASH_STATUS,          # PROPOSED, not decided
        "status": "PROVISIONAL",
        "environment": env,
        # The two rules travel WITH the evidence so no consumer can forget them.
        "interpretation_rules": [
            "Different ENV-FP is not proof of a different engineering result.",
            "Same ENV-FP is not proof of correctness.",
        ],
    }


def environments_differ(a, b):
    """Compare two environment fingerprints.

    Returns (differs: bool, differing_keys: list). Deliberately returns FACTS
    only: it states that the environments differ, and never concludes anything
    about the engineering result. That inference is forbidden (R02 s5.1).
    """
    ea, eb = a.get("environment", {}), b.get("environment", {})
    diffs = []

    def walk(pa, da, db):
        keys = sorted(set(da) | set(db))
        for k in keys:
            va, vb = da.get(k, NOT_SET), db.get(k, NOT_SET)
            path = f"{pa}/{k}" if pa else k
            if isinstance(va, dict) or isinstance(vb, dict):
                walk(path, va if isinstance(va, dict) else {},
                     vb if isinstance(vb, dict) else {})
            elif va != vb:
                diffs.append(path)

    walk("", ea, eb)
    return bool(diffs), diffs
