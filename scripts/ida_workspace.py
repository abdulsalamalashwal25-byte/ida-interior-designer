#!/usr/bin/env python3
"""
ida_workspace.py — Agent Interfaces · Workspace Layer
واجهات الوكيل · طبقة مساحة العمل

WHAT THIS IS
  File-system conventions for one project workspace. Pure helpers:
  creating folders, reading/writing JSON, naming output files.
  It judges nothing and validates nothing — that belongs to the
  owning engines (A / B1..B11 / C1..C6 / D / E / F / Phase 01).

WORKSPACE LAYOUT (created by `ida init`)
  projects/<PRJ>/
    intake.json            answers to the intake form (edited by the user)
    field_specs.json       BLOCKING / NON_BLOCKING classification of fields
    project_master.json    the Single Source of Truth (built by `ida build`)
    05_VIEWS/
      A_accurate/          Class A — DESIGN-ACCURATE (binding geometry)
      B_presentation/      Class B — PRESENTATION VISUAL (geometry from A)
      C_ai_mood/           Class C — AI MOOD (non-binding, never measured)
    reports/               validation / readiness / fidelity / manifest JSON

FILE NAMING (Spec R01 section 10)
  <PRJ>_<REV>_<CLASS>_<View>.<ext>   e.g. PRJ01_R01_A_FloorPlan.svg
"""

import copy
import json
import os
import re
from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SYSTEM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(SYSTEM_DIR, "project_master.template.json")
SCHEMA_PATH = os.path.join(SYSTEM_DIR, "project_master.schema.json")
DEFAULT_PROJECTS_DIR = os.path.join(SYSTEM_DIR, "projects")

VIEWS_DIR = "05_VIEWS"
CLASS_DIRS = {
    "A": os.path.join(VIEWS_DIR, "A_accurate"),
    "B": os.path.join(VIEWS_DIR, "B_presentation"),
    "C": os.path.join(VIEWS_DIR, "C_ai_mood"),
}
REPORTS_DIR = "reports"

INTAKE_FILENAME = "intake.json"
FIELD_SPECS_FILENAME = "field_specs.json"
MASTER_FILENAME = "project_master.json"

# The intake contract vocabulary (consumed from p1_intake, never extended).
BLOCKING = "BLOCKING"
NON_BLOCKING = "NON_BLOCKING"


# ---------------------------------------------------------------------------
# Small IO helpers
# ---------------------------------------------------------------------------

def utc_today():
    """ISO date string (YYYY-MM-DD) in UTC."""
    return date.today().isoformat()


def utc_timestamp():
    """ISO-8601 UTC timestamp, labelled as an interface-layer timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def strip_private(node):
    """Remove top-level keys starting with '_' (guides, READMEs).

    Mirrors the convention used by the engines' own __main__ blocks:
    underscore-prefixed keys are documentation, never data.
    """
    if not isinstance(node, dict):
        return node
    return {k: v for k, v in node.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# Intake contract defaults
# ---------------------------------------------------------------------------

def default_field_specs():
    """The default field classification, aligned with intake_form.md.

    BLOCKING fields stop Phase 01 when absent (G1 abstains).
    NON_BLOCKING fields enter the master as [U] when absent.
    The classification is DECLARED here as the intake contract — Phase 01
    consumes it and never invents its own (G1-6.5).
    """
    return [
        {"field": "meta.project_id", "classification": BLOCKING},
        {"field": "meta.project_name", "classification": NON_BLOCKING},
        {"field": "meta.track", "classification": NON_BLOCKING},
        {"field": "meta.is_test_project", "classification": NON_BLOCKING},
        {"field": "space.outline", "classification": BLOCKING},
        {"field": "space.ceiling_height", "classification": BLOCKING},
        {"field": "openings.presence", "classification": BLOCKING},
        {"field": "space.orientation_north", "classification": NON_BLOCKING},
        {"field": "space.floor_level", "classification": NON_BLOCKING},
    ]


def intake_skeleton(project_id="", project_name=""):
    """An empty intake answer set with an inline guide.

    `_guide` keys are documentation and are stripped before the answers
    reach Phase 01. Empty values count as ABSENT (never as answers).
    """
    return {
        "_guide": {
            "rule": "What you leave empty is recorded as [U] UNKNOWN — never guessed.",
            "units": "Millimetres (mm) only.",
            "outline": "Room outline polygon as [[x,y],...] in mm, e.g. "
                       "[[0,0],[6000,0],[6000,4000],[0,4000]].",
            "openings.presence": "One of: PRESENT / NOT_PRESENT / UNKNOWN. "
                                 "NOT_PRESENT is your positive confirmation "
                                 "that the space has no door or window.",
            "openings": "When PRESENT: a list of opening objects, each with "
                        "id/kind/host_wall/offset/width/height facts.",
        },
        "meta.project_id": project_id,
        "meta.project_name": project_name,
        "meta.track": "FULL",
        "meta.is_test_project": False,
        "space.outline": [],
        "space.ceiling_height": None,
        "space.orientation_north": None,
        "space.floor_level": None,
        "openings.presence": "UNKNOWN",
        "openings": [],
    }


# ---------------------------------------------------------------------------
# Project initialisation
# ---------------------------------------------------------------------------

# Boundary input check, mirroring project_master.schema.json
# ($defs/meta/project_id). The schema remains the judge; this fails fast
# at `ida init` so no workspace is built around an unusable id.
PROJECT_ID_PATTERN = re.compile(r"^PRJ-[0-9]{2,3}$")


def check_project_id(project_id):
    if not PROJECT_ID_PATTERN.match(str(project_id or "")):
        raise ValueError(
            "project id '%s' does not match the schema pattern "
            "'PRJ-NN' (e.g. PRJ-01)" % project_id)
    return project_id

def project_paths(project_dir):
    """Standard paths inside a project workspace."""
    project_dir = os.path.abspath(project_dir)
    paths = {
        "project_dir": project_dir,
        "intake": os.path.join(project_dir, INTAKE_FILENAME),
        "field_specs": os.path.join(project_dir, FIELD_SPECS_FILENAME),
        "master": os.path.join(project_dir, MASTER_FILENAME),
        "views": os.path.join(project_dir, VIEWS_DIR),
        "reports": os.path.join(project_dir, REPORTS_DIR),
    }
    for cls, rel in CLASS_DIRS.items():
        paths["views_" + cls] = os.path.join(project_dir, rel)
    return paths


def init_project(project_dir, project_id, project_name="",
                 track="FULL", is_test=False, overwrite=False):
    """Create a new project workspace. Returns the paths dict.

    Writes intake.json + field_specs.json skeletons and empty view/report
    folders. It does NOT build a master — that is `ida build` (Phase 01).
    Refuses to overwrite an existing workspace unless overwrite=True.
    """
    check_project_id(project_id)
    paths = project_paths(project_dir)
    if os.path.exists(paths["project_dir"]) and not overwrite:
        if os.listdir(paths["project_dir"]):
            raise FileExistsError(
                "workspace '%s' already exists and is not empty; "
                "refusing to overwrite" % paths["project_dir"])
    for key in ("views_A", "views_B", "views_C", "reports"):
        os.makedirs(paths[key], exist_ok=True)

    intake = intake_skeleton(project_id, project_name)
    intake["meta.track"] = track
    intake["meta.is_test_project"] = bool(is_test)
    save_json(intake, paths["intake"])
    save_json(default_field_specs(), paths["field_specs"])

    readme = {
        "_README": "IDA project workspace. intake.json is filled by the user, "
                   "then `ida build` produces project_master.json (the SSOT). "
                   "Never edit project_master.json by hand for a confirmed "
                   "fact — confirmed changes go through a Change Request.",
        "project_id": project_id,
        "created_on": utc_today(),
    }
    save_json(readme, os.path.join(paths["project_dir"], "workspace.json"))
    return paths


# ---------------------------------------------------------------------------
# Output file naming — Spec R01 section 10
# ---------------------------------------------------------------------------

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9][^A-Za-z0-9]*")


def output_filename(project_id, revision, cls, view, ext):
    """<PRJ>_<REV>_<CLASS>_<View>.<ext>, sanitised for file systems."""
    def clean(text):
        text = str(text or "").strip().replace(" ", "")
        text = _SAFE_CHARS.sub("-", text)
        return text or "X"
    return "%s_%s_%s_%s.%s" % (
        clean(project_id), clean(revision), clean(cls), clean(view),
        str(ext or "dat").lstrip(".").lower() or "dat")


def identity_of(master):
    """Identity dict consumed by C3/C5/C6/D as `identity`.

    The template carries meta.revision; several engines also read
    meta.master_revision. Both are carried; nothing is invented.
    """
    meta = (master or {}).get("meta") or {}
    revision = meta.get("master_revision") or meta.get("revision")
    return {
        "project_id": meta.get("project_id", "NOT_SET"),
        "master_revision": revision or "NOT_SET",
        "revision": revision or "NOT_SET",
        "geometry_version": meta.get("geometry_version", "NOT_SET"),
    }


# ---------------------------------------------------------------------------
# Packaging rules (interface layer — declared, never silent)
# ---------------------------------------------------------------------------

TEST_BANNER = "TEST PROJECT — NOT A REAL CLIENT PROJECT"


def ensure_test_banner(master):
    """Attach the mandatory test banner when is_test_project is true.

    RULES.md rule 19: a test project carries its banner IN THE DATA.
    The banner text is a fixed literal, not an invented value. The interface
    applies it at persist time (it is the caller that writes the file) and
    reports it. Real projects are untouched.
    Returns (master, banner_applied: bool).
    """
    master = master or {}
    meta = master.get("meta") or {}
    if meta.get("is_test_project") is True:
        if meta.get("test_banner") != TEST_BANNER:
            meta["test_banner"] = TEST_BANNER
            master["meta"] = meta
            return master, True
    return master, False


def master_copy(master):
    return copy.deepcopy(master)
