#!/usr/bin/env python3
"""
00.5-C6 — AGGREGATE COUNTS (mechanical only)

Three INDEPENDENT counters over member fields. Nothing else.

NOT PRODUCED HERE
  overall state · unified status · unified completeness · score · severity ·
  pass/fail · weighted state · manifest completeness · any judgement.

The counters are never summed or combined: doing so would invent an aggregate
state that no producer declared (AS-C6-21).

A note that matters: C4 appears under by_source_status.NOT_SET because it does
not declare a `status` field at all — not because it failed.
"""

from c6_contract import (
    NOT_SET, STATUS_VALUES, COVERAGE_VALUES, COMPLETENESS_VALUES,
)


def _count(members, field, allowed):
    counts = {v: 0 for v in allowed}
    for m in members or []:
        value = m.get(field, NOT_SET) if isinstance(m, dict) else NOT_SET
        if value not in counts:
            counts[value] = 0          # report an unexpected value as-is
        counts[value] += 1
    return counts


def aggregate_summary(members):
    """Mechanical counts. Separate, never combined, never judged."""
    return {
        "members_total": len(members or []),
        "by_source_status": _count(members, "source_status", STATUS_VALUES),
        "by_source_coverage": _count(members, "source_coverage",
                                     COVERAGE_VALUES),
        "by_source_completeness": _count(members, "source_completeness",
                                         COMPLETENESS_VALUES),
        "counts_kind": "mechanical counts",
        "note": ("Independent counts of member fields. They are not combined, "
                 "not weighted, and do not express a manifest-level state. A "
                 "member counted under by_source_status.NOT_SET simply does "
                 "not declare that field."),
        "is_verdict": False,
    }
