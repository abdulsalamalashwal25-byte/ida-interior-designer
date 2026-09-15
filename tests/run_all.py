#!/usr/bin/env python3
"""
run_all.py — regression runner for every completed sub-phase.

Rationale: refactoring during 00.5-B1 silently broke 3 passing tests in the
00.5-A suite (ownership of reference-existence rules moved between layers).
That is exactly the regression class the Technical Fix policy requires us to
detect. From here on, every sub-phase must run this before its Gate Card.
"""

import subprocess
import sys
from pathlib import Path

TESTS = [
    ("00.5-A  Data Model / Schema Gate", "test_00_5_A.py"),
    ("00.5-B1 Cross-Reference Integrity", "test_00_5_B1.py"),
    ("00.5-B2 Wall & Opening Topology", "test_00_5_B2.py"),
    ("00.5-B3 Furniture & Clearance", "test_00_5_B3.py"),
    ("00.5-B4 Movement & Circulation", "test_00_5_B4.py"),
    ("00.5-B5 Door Swing & Doorway", "test_00_5_B5.py"),
    ("00.5-B6 Formula & Derived Value", "test_00_5_B6.py"),
    ("00.5-B7 Unknown & Blocking", "test_00_5_B7.py"),
    ("00.5-B8 Output & Representation", "test_00_5_B8.py"),
    ("00.5-B9 Revision & Changelog", "test_00_5_B9.py"),
    ("00.5-B10 Register Lifecycle", "test_00_5_B10.py"),
    ("00.5-B11 Temporal Integrity", "test_00_5_B11.py"),
    ("00.5-C1 Generation Preconditions", "test_00_5_C1.py"),
    ("00.5-C2 Determinism & Fingerprint", "test_00_5_C2.py"),
    ("00.5-C3 Geometry Emitters (SVG)", "test_00_5_C3.py"),
    ("00.5-C4 Quantity Schedules", "test_00_5_C4.py"),
    ("00.5-C5 Presentation (Class B)", "test_00_5_C5.py"),
    ("00.5-C6 Manifest / Evidence", "test_00_5_C6.py"),
    ("00.5-D  Fidelity Judge", "test_00_5_D.py"),
    ("00.5-E  Governance / Identity", "test_00_5_E.py"),
    ("00.5-F  Reference / Standards", "test_00_5_F.py"),
    ("01      Intake -> Validated Master", "test_01_phase01.py"),
    ("01-SA   Space Analysis · Unit 1", "test_01_space_analysis.py"),
]

HERE = Path(__file__).resolve().parent
rows, all_ok = [], True

for label, fname in TESTS:
    path = HERE / fname
    if not path.exists():
        rows.append((label, "MISSING", "-", "-"))
        all_ok = False
        continue
    proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    tail = [ln for ln in proc.stdout.splitlines() if ln.startswith("TOTAL:")]
    summary = tail[-1] if tail else "no summary"
    passed = proc.returncode == 0
    all_ok &= passed
    rows.append((label, "PASS" if passed else "FAIL", summary, ""))

print("=" * 78)
print("FULL REGRESSION RUN — Interior Designer Agent")
print("=" * 78)
for label, status, summary, _ in rows:
    mark = "OK  " if status == "PASS" else "FAIL"
    print(f"{mark} {label:38} {summary}")
print("-" * 78)
print("REGRESSIONS:", "NONE" if all_ok else "DETECTED")
print("=" * 78)
sys.exit(0 if all_ok else 1)
