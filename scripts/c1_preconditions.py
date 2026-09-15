#!/usr/bin/env python3
"""
00.5-C1 — GENERATION PRECONDITIONS ENGINE
Reference architecture: 00.5-C1-GENERATION-PRECONDITIONS.md R05 (APPROVED).

WHAT C1 IS
  A GATE OF ABSTENTION. For each *requested* output it answers only:
      1. may it be generated?      2. must we abstain?
      3. why?                      4. what scope is affected?
      5. what must be lifted to allow generation?

WHAT C1 IS NOT — enforced by construction, proven by the isolation tests:
  * It generates NO file (no DXF/SVG/PDF/GLB/OBJ).
  * It NEVER writes to project_master.json, the schema, or any model data.
  * It does NOT re-implement A / B1..B11 rules. It CONSUMES their published
    verdicts and interfaces.
  * It does NOT re-interpret validator `severity`, and never lowers it.
  * It does NOT own outputs[]  (GAP-C-06 -> 00.5-E). Requests come from the
    caller; C1 returns an external decision record.
  * It makes NO design decision and invents NO value.

SCOPE DISCIPLINE (R05 sections 3.3 / 3.4 / 3.5 / 3.6)
  A blocking verdict is only comprehensive when the OWNER says so. C1 never
  promotes a finding to model-wide on its own:
      OWNER_DECLARED  - the owner's verdict carries an explicit scope.
      PATH_DERIVED    - the scope is structurally attached (e.g. a fact's own
                        path / a per-fact source_type), not guessed.
      UNPROVEN_SCOPE  - scope cannot be established -> FAIL-CLOSED (block),
                        declared honestly as "scope unproven", never as
                        "the model is invalid".

  Per instruction: the free-text `Finding.location` of the existing engines is
  NOT accepted as a formal scope contract. A verdict without a structured
  `scope` is treated as UNPROVEN_SCOPE. This is exactly why GAP-C-12 and
  GAP-C-13 stay OPEN; C1 does not close them by guessing.
"""

# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------
ALLOWED = "GENERATION_ALLOWED"
ABSTAIN = "ABSTAIN"

# Scope basis
OWNER_DECLARED = "OWNER_DECLARED"
PATH_DERIVED = "PATH_DERIVED"
UNPROVEN_SCOPE = "UNPROVEN_SCOPE"

# Scope kinds an owner may declare
SCOPE_MODEL_WIDE = "MODEL_WIDE"
SCOPE_PATH = "PATH"
SCOPE_OUTPUT = "OUTPUT"

# Output classes
CLASS_A = "A"
CLASS_B = "B"
CLASS_C = "C"

# R02 rule: class A consumes [C]/[D] ONLY. An APPROVED [A] is NOT eligible
# (C1-FIX-01). This is C1's own input-eligibility rule, not a re-run of any
# B-series rule: C1 judges admissibility of an input for a binding output,
# it does not judge the legality of the fact itself (that is A/B6/B8).
ELIGIBLE_STATUSES = frozenset({"C", "D"})

# source_type values that are not authoritative geometry sources.
UNTRUSTED_SOURCES = frozenset({
    "AI_IMAGE", "EXTERNAL_STANDARD", "EXTERNAL_LIBRARY",
    "AGENT_PROPOSAL", "AGENT_ASSUMPTION", "NOT_PROVIDED",
})

# Reason codes — mirror A-BLK-xx of the approved map.
BLK_LAYER_ERROR = "A-BLK-01"
BLK_PROJECT_BLOCKER = "A-BLK-02"
BLK_BLOCKING_UNKNOWN = "A-BLK-03"
BLK_PRESENCE_UNKNOWN = "A-BLK-04"
BLK_UNKNOWN_FIELD = "A-BLK-05"
BLK_UNAPPROVED = "A-BLK-06"
BLK_UNCOMPUTABLE = "A-BLK-07"
BLK_DEPENDENCY = "A-BLK-08"
BLK_MISSING_GEOMETRY = "A-BLK-09"
BLK_NO_CAMERA = "A-BLK-10"
BLK_NO_CAPABILITY = "A-BLK-11"
BLK_VERSION_MISMATCH = "A-BLK-12"
BLK_UNTRUSTED_SOURCE = "A-BLK-13"


class Reason:
    """One abstention reason. Carries WHY, WHO judged it, and WHAT scope."""

    __slots__ = ("code", "message", "source_layer", "scope_basis",
                 "affected", "lift")

    def __init__(self, code, message, source_layer, scope_basis,
                 affected=None, lift=""):
        self.code = code
        self.message = message
        self.source_layer = source_layer      # owner of the judgement
        self.scope_basis = scope_basis
        self.affected = affected              # path / element / output
        self.lift = lift                      # what must happen to allow it

    def __repr__(self):
        return f"<{self.code} {self.scope_basis} @ {self.affected}>"


class Decision:
    __slots__ = ("output_id", "cls", "decision", "reasons")

    def __init__(self, output_id, cls, decision, reasons):
        self.output_id = output_id
        self.cls = cls
        self.decision = decision
        self.reasons = reasons

    @property
    def allowed(self):
        return self.decision == ALLOWED

    def codes(self):
        return sorted({r.code for r in self.reasons})

    def bases(self):
        return sorted({r.scope_basis for r in self.reasons})

    def __repr__(self):
        return f"<{self.output_id} {self.decision} {self.codes()}>"


class OutputRequest:
    """A requested output. The caller owns this list — C1 does not read or
    write master['outputs'] (GAP-C-06 keeps that ownership with 00.5-E).

    requires_paths   : model paths the output consumes ("space/ceiling_height")
    shared_geometry  : subset of requires_paths that is the COMMON geometry;
                       failing it blocks A and B alike (R05 section 4 layer 1)
    requires_camera  : output cannot exist without a defined camera
    requires_capability : toolchain key, e.g. "dxf"
    """

    __slots__ = ("output_id", "cls", "view_type", "requires_paths",
                 "shared_geometry", "requires_camera", "requires_capability")

    def __init__(self, output_id, cls, view_type="", requires_paths=(),
                 shared_geometry=(), requires_camera=False,
                 requires_capability=None):
        self.output_id = output_id
        self.cls = cls
        self.view_type = view_type
        self.requires_paths = tuple(requires_paths)
        self.shared_geometry = tuple(shared_geometry)
        self.requires_camera = requires_camera
        self.requires_capability = requires_capability


# --------------------------------------------------------------------------
# Owner verdict adapter
# --------------------------------------------------------------------------
class OwnerVerdict:
    """A judgement produced by an OWNING layer and handed to C1.

    `scope` is either None (no formal scope -> UNPROVEN_SCOPE, fail-closed) or
    a dict:  {"kind": MODEL_WIDE|PATH|OUTPUT, "paths": [...], "outputs": [...]}

    C1 NEVER fabricates this dict and never derives it from free text.
    """

    __slots__ = ("rule", "severity", "layer", "message", "scope", "code")

    def __init__(self, rule, severity, layer, message="", scope=None,
                 code=BLK_LAYER_ERROR):
        self.rule = rule
        self.severity = severity          # consumed verbatim, never re-graded
        self.layer = layer
        self.message = message
        self.scope = scope
        self.code = code


def _scope_hits(verdict, req):
    """Does an owner verdict apply to this request? Returns (applies, basis).

    The three R05 categories, and nothing else.
    """
    scope = verdict.scope
    if not scope:
        # (3) no trustworthy scope -> fail closed, honestly labelled.
        return True, UNPROVEN_SCOPE

    kind = scope.get("kind")
    if kind == SCOPE_MODEL_WIDE:
        # (1) comprehensive ONLY because the owner declared it.
        return True, OWNER_DECLARED
    if kind == SCOPE_OUTPUT:
        return (req.output_id in set(scope.get("outputs") or ())), OWNER_DECLARED
    if kind == SCOPE_PATH:
        paths = set(scope.get("paths") or ())
        return bool(paths & set(req.requires_paths)), OWNER_DECLARED
    # Unrecognised scope kind is not a licence to guess.
    return True, UNPROVEN_SCOPE


# --------------------------------------------------------------------------
# Read-only model helpers (no mutation anywhere in this module)
# --------------------------------------------------------------------------
def _get_path(data, path):
    node = data
    for part in path.split("/"):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _is_fact(node):
    return isinstance(node, dict) and "status" in node and "source_type" in node


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------
def evaluate_request(data, req, verdicts=(), capabilities=None,
                     uncertainty=None):
    """Decide ONE requested output. Returns a Decision. Never mutates `data`."""
    reasons = []
    capabilities = capabilities or {}

    # ---- consumed from B7 (not recomputed) -------------------------------
    if uncertainty is None:
        uncertainty = {}

    # ---- owner verdicts (A-BLK-01 / 12 / 13 and any layer ERROR) ---------
    for v in verdicts:
        if v.severity != "ERROR":
            continue                      # severity consumed as-is, not re-graded
        applies, basis = _scope_hits(v, req)
        if not applies:
            continue
        lift = ("owner must resolve the finding, or declare its scope"
                if basis == UNPROVEN_SCOPE
                else "owner must resolve the finding")
        note = v.message
        if basis == UNPROVEN_SCOPE:
            note = (f"{v.message} [scope not proven — blocked conservatively; "
                    f"this is NOT a claim that the model is invalid]")
        reasons.append(Reason(v.code, f"{v.rule}: {note}", v.layer, basis,
                              affected=req.output_id, lift=lift))

    # ---- required model paths -------------------------------------------
    for path in req.requires_paths:
        shared = path in req.shared_geometry
        node = _get_path(data, path)

        if node is None:
            reasons.append(Reason(
                BLK_MISSING_GEOMETRY,
                f"required geometry '{path}' is absent from the master",
                "C1/input-eligibility", PATH_DERIVED, affected=path,
                lift=f"supply '{path}' as a [C] or [D] fact"))
            continue

        # B7 already judged uncertainty; consume its verdict verbatim.
        if path in uncertainty:
            code_map = {
                "UNKNOWN": BLK_UNKNOWN_FIELD,
                "PROPOSED": BLK_UNAPPROVED,
                "UNAPPROVED_ASSUMPTION": BLK_UNAPPROVED,
                "UNCOMPUTABLE": BLK_UNCOMPUTABLE,
            }
            reason_kind, msg = uncertainty[path]
            reasons.append(Reason(
                code_map.get(reason_kind, BLK_DEPENDENCY),
                f"{reason_kind}: {msg}", "B7", PATH_DERIVED, affected=path,
                lift=f"resolve '{path}' to [C] or a VERIFIED [D]"))
            continue

        if not _is_fact(node):
            continue

        status = node.get("status")
        presence = node.get("presence")

        # Triple distinction: NOT_PRESENT is a usable fact; UNKNOWN is not.
        if presence == "UNKNOWN":
            # NOTE: layer A owns whether presence semantics are LEGAL. C1 only
            # judges whether an unknown presence is USABLE for this output.
            reasons.append(Reason(
                BLK_PRESENCE_UNKNOWN,
                f"presence of '{path}' was never confirmed or denied",
                "C1/input-eligibility", PATH_DERIVED, affected=path,
                lift=f"confirm or deny the existence of '{path}'"))
            continue

        # Input eligibility by class (C-STEP-01 R02).
        if req.cls in (CLASS_A, CLASS_B) and status not in ELIGIBLE_STATUSES:
            if status == "A":
                approved = node.get("approval_state") == "APPROVED"
                detail = ("approved assumption is still an assumption; user "
                          "approval does not turn it into geometric fact"
                          if approved else "unapproved assumption")
                reasons.append(Reason(
                    BLK_UNAPPROVED, f"[A] {detail} at '{path}'",
                    "C1/input-eligibility", PATH_DERIVED, affected=path,
                    lift=("convert to a measured [C] fact, or obtain an "
                          "architectural decision (GAP-C-11)")))
            elif status == "P":
                reasons.append(Reason(
                    BLK_UNAPPROVED, f"[P] proposal at '{path}' is not a decision",
                    "C1/input-eligibility", PATH_DERIVED, affected=path,
                    lift="a decision must approve the proposal first"))
            elif status == "U":
                reasons.append(Reason(
                    BLK_UNKNOWN_FIELD, f"[U] unknown at '{path}'",
                    "C1/input-eligibility", PATH_DERIVED, affected=path,
                    lift=f"supply a value for '{path}'"))
            continue

        # Untrusted source, structurally attached to THIS path (R05 3.4).
        if node.get("source_type") in UNTRUSTED_SOURCES:
            reasons.append(Reason(
                BLK_UNTRUSTED_SOURCE,
                f"'{path}' rests on untrusted source "
                f"{node.get('source_type')}",
                "C1/input-eligibility", PATH_DERIVED, affected=path,
                lift=f"re-source '{path}' from a trusted input"))

        _ = shared  # shared-geometry handling is caller-declared, see below

    # ---- camera (output-scoped, never comprehensive) ---------------------
    if req.requires_camera:
        cams = [c for c in (data.get("cameras") or [])
                if isinstance(c, dict) and c.get("status") in ELIGIBLE_STATUSES]
        if not cams:
            reasons.append(Reason(
                BLK_NO_CAMERA,
                "no confirmed camera is defined; this view cannot be framed",
                "C1/input-eligibility", PATH_DERIVED, affected=req.output_id,
                lift="define a camera with a confirmed status"))

    # ---- capability -------------------------------------------------------
    cap = req.requires_capability
    if cap and not capabilities.get(cap, False):
        reasons.append(Reason(
            BLK_NO_CAPABILITY,
            f"toolchain capability '{cap}' is unavailable in this environment",
            "C1/environment", PATH_DERIVED, affected=req.output_id,
            lift=f"install/pin the '{cap}' capability (GAP-C-02)"))

    decision = ABSTAIN if reasons else ALLOWED
    return Decision(req.output_id, req.cls, decision, reasons)


def evaluate(data, requests, verdicts=(), capabilities=None,
             uncertainty=None, project_blockers=()):
    """Decide a batch of requests.

    `project_blockers` are project-level blockers (from A). Per C1-FIX-03 they
    are NOT automatically universal: each carries its own scope, resolved with
    the same three-category discipline.
    """
    out = []
    all_verdicts = list(verdicts) + list(project_blockers)
    for req in requests:
        out.append(evaluate_request(data, req, all_verdicts, capabilities,
                                    uncertainty))
    return out


def abstention_report(decisions):
    """Human-readable abstention declarations. Declares inability explicitly;
    never proposes a value, never hides a capability gap."""
    lines = []
    for d in decisions:
        if d.allowed:
            lines.append(f"[{d.output_id}] GENERATION_ALLOWED (class {d.cls})")
            continue
        lines.append(f"[{d.output_id}] ABSTAINED (class {d.cls})")
        for r in d.reasons:
            lines.append(f"    - {r.code} ({r.scope_basis}) via {r.source_layer}"
                         f" @ {r.affected}: {r.message}")
            lines.append(f"      to lift: {r.lift}")
    return "\n".join(lines)
