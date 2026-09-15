#!/usr/bin/env python3
"""Phase 00.5-B6 — Formula / Derived-Value Integrity.

WHAT B6 OWNS:
  Every [D] value must be arithmetically CORRECT and REPRODUCIBLE from its
  declared inputs. Layer A enforces the SHAPE of a [D] (rule F4: derived_from,
  formula, derivation_type must exist). B1/XR-008 enforces that those refs
  RESOLVE. Nobody checked the sum itself — a fact claiming "2800 - 100 = 9999"
  passes both A and B1 today. That proven gap is this layer's territory.

WHAT B6 DOES NOT OWN (consumed, never re-implemented):
  - presence of derived_from / formula / derivation_type -> A  (rule F4)
  - resolvability of derived_from refs                   -> B1 (XR-008)
  - wall topology -> B2 · furniture -> B3 · circulation -> B4 · doors -> B5
  - blocking-unknown gate -> B7 · source impersonation -> 00.5-E

R02 ADDITIONS:
  * FM-005 upgraded from an additive-only check to full DIMENSIONAL ALGEBRA:
    + / -  require the same dimension AND the same unit
    *      composes dimensions   (mm x mm -> mm2)
    /      divides them          (mm2 / mm -> mm,  mm / s -> mm/s)
    A numerically correct figure carrying the WRONG dimension is never
    VERIFIED. Scale factors serve detection only — nothing is ever converted.
  * FM-004 tightened: numeric + declared is not sufficient (see below).
  * tolerance policy and FM-009's limits are documented, not assumed.

HARD RULES:
  * no arbitrary code execution: formulas are parsed, whitelisted and walked
  * no implicit unit conversion, ever — detect and report, never rescale
  * an input that is [U]/[P]/[A] makes the result UNCOMPUTABLE, never guessed
  * a [D] is a computation, never a preference or a design decision
  * detect / classify / report only — no auto-fix, no suggested formulas
  * B6 never derives a value nobody asked for; it checks what is declared
"""

import ast
import math
import re

# --------------------------------------------------------------------------
# Constants — tolerances only. No design value of any kind.
# --------------------------------------------------------------------------
# ---- NUMERICAL COMPARISON POLICY (documented in R02) ---------------------
# WHY A TOLERANCE EXISTS AT ALL
#   Binary floating point cannot represent most decimals exactly: recomputing
#   a value can land an ulp away from the stored one (0.1+0.2 = 0.30000000000
#   000004). Without a tolerance, B6 would raise MISMATCH on arithmetic that
#   is in fact identical. The tolerance exists ONLY to absorb that
#   representation error.
#
# WHAT IT IS NOT
#   It is NOT an engineering, construction or manufacturing tolerance. It is
#   NOT a design rule. It encodes no opinion about what deviation is
#   acceptable on site. "0.01 mm" is NOT a general design tolerance in this
#   system: FB-02 uses a 0.01 mm discrepancy merely as a test probe that is
#   astronomically larger than float noise, and it is correctly reported as a
#   MISMATCH. Any real-world tolerance is a human decision recorded as [C]/[P]
#   — never something B6 invents.
#
# ABSOLUTE, RELATIVE, OR BOTH -> BOTH, whichever is larger:
#       |stored - computed| <= max(ABS_TOLERANCE, REL_TOLERANCE * |computed|)
#   Relative alone fails near zero (a computed 0.0 would demand exactness);
#   absolute alone fails at large magnitudes (at 1e9 mm, one ulp exceeds any
#   fixed epsilon). Taking the larger of the two is correct at both extremes.
#
# VERIFIED  -> the difference is within that bound: the stored value IS what
#              the formula produces, AND the dimension/unit also match.
# MISMATCH  -> the difference exceeds it, or the unit/dimension is wrong. The
#              stored value is reported and deliberately NOT corrected.
#
# 1e-9 is chosen as a floating-point epsilon many orders of magnitude below
# any physical quantity this system records, and far above double-precision
# noise (~1e-16 relative). It is a numerical constant, not a design constant.
REL_TOLERANCE = 1e-9
ABS_TOLERANCE = 1e-9

# ---- What may enter a derivation (FM-004, tightened in R02) --------------
# Being numeric and listed in derived_from is NOT sufficient. An admissible
# input must be: (a) resolvable, (b) of a status valid for derivation,
# (c) a recorded quantity rather than a decision/preference/unapproved
# standard wearing a number, (d) if itself derived, properly documented.
# Anything else -> UNCOMPUTABLE. Never a guessed value.
DERIVABLE_INPUT_STATUSES = {"C", "D"}

# source_type values that are NOT measured/confirmed quantities. A number
# carrying one of these is a proposal, an assumption or an external standard
# — admissible only once it has been approved and recorded as [C].
NON_FACTUAL_SOURCE_TYPES = {
    "AGENT_PROPOSAL": "an agent proposal",
    "AGENT_ASSUMPTION": "an agent assumption",
    "EXTERNAL_STANDARD": "an external standard",
    "EXTERNAL_LIBRARY": "an external library entry",
    "AI_IMAGE": "an AI image",
    "NOT_PROVIDED": "not provided",
}

VERIFIED = "VERIFIED"
MISMATCH = "MISMATCH"
UNCOMPUTABLE = "UNCOMPUTABLE"

# Whitelisted deterministic helpers. Nothing stateful, random or time-based.
SAFE_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "floor": math.floor,
    "ceil": math.ceil,
}

# Anything matching these is non-deterministic or environment-dependent.
NONDETERMINISTIC_TOKENS = (
    "random", "rand", "now", "today", "time", "date", "uuid", "shuffle",
    "choice", "input", "open", "import", "eval", "exec", "getattr", "globals",
)

# ---- FM-009 SCOPE AND ITS HONEST LIMITS (documented in R02) --------------
# B6 uses BOUNDED LITERAL TEXT MATCHING. It is deliberately not a semantic or
# intent-understanding engine, and no AI judgement runs inside this layer.
#
# WHAT IT CAN DETECT
#   Explicit judgement vocabulary in the formula / note / source_ref of a [D]
#   — "preferred", "recommended", "optimal", "ideal", "looks better", etc.
#
# WHAT IT CANNOT DETECT
#   * a design decision expressed in neutral wording ("x = 2400")
#   * a chosen constant with no justifying text at all
#   * an unapproved standard silently hardcoded into a formula
#   * intent, motive, or whether a number was argued over in a meeting
#
# CRITICAL: NOT FLAGGING IS NOT A CLEARANCE.
#   Silence from FM-009 does NOT mean the value is a genuine computation, and
#   does NOT convert a decision into an arithmetic fact. A [D] that escapes
#   FM-009 has only escaped a text filter. Distinguishing a real derivation
#   from a decision dressed as one is a GOVERNANCE duty (00.5-E), enforced by
#   human approval — never by this layer. Tracked as GAP-03.
JUDGEMENT_TOKENS = (
    "prefer", "recommend", "suggest", "nicer", "better", "best", "optimal",
    "optimis", "optimiz", "aesthetic", "beautiful", "should be", "ideal",
    "comfortable", "cosy", "cozy", "looks", "taste", "style_choice",
)

# --------------------------------------------------------------------------
# B6 R02 — DIMENSIONAL UNIT ALGEBRA
# --------------------------------------------------------------------------
# This is NOT a unit-conversion library and must never become one. Scale
# factors exist for ONE purpose: to DETECT that two quantities are expressed
# in different units of the same dimension. A value is never rescaled,
# converted or rewritten by B6. Detect / classify / report only.
#
# Base dimensions kept deliberately small — only what this system's own unit
# vocabulary needs. No external standard, no design semantics.
#   L=length  T=time  ANG=angle  TEMP=temperature  LUM=illuminance
#   PWR=power  CUR=currency  CNT=countable items
_BASE_UNITS = {
    "mm":       (1e-3, {"L": 1}),
    "cm":       (1e-2, {"L": 1}),
    "m":        (1.0,  {"L": 1}),
    "s":        (1.0,  {"T": 1}),
    "deg":      (1.0,  {"ANG": 1}),
    "kelvin":   (1.0,  {"TEMP": 1}),
    "lux":      (1.0,  {"LUM": 1}),
    "watt":     (1.0,  {"PWR": 1}),
    "currency": (1.0,  {"CUR": 1}),
    "count":    (1.0,  {"CNT": 1}),
    "none":     (1.0,  {}),
}

# Outcome tags of a dimensional inference.
DIM_OK = "OK"              # dimension and scale both determined
DIM_LITERAL = "LITERAL"    # a bare number: adopts its sibling's dimension
DIM_UNKNOWN = "UNKNOWN"    # cannot be determined -> never claimed as correct
DIM_VIOLATION = "VIOLATION"


def _dim_mul(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return {k: v for k, v in out.items() if v != 0}


def _dim_pow(a, n):
    return {k: v * n for k, v in a.items() if v * n != 0}


def _dim_str(dims):
    if not dims:
        return "dimensionless"
    return "·".join(f"{k}^{v}" if v != 1 else k for k, v in sorted(dims.items()))


def parse_unit(text):
    """Parse a unit expression into (scale, dims), or (None, None).

    Understands the forms this system actually uses: a base token, an integer
    power written as a suffix or with '^' (mm2, mm^2), products ('*' or '.')
    and quotients ('/'). Anything else is UNKNOWN — never guessed.
    """
    if text is None:
        return None, None
    t = str(text).strip().lower().replace(" ", "")
    if not t:
        return None, None
    scale, dims = 1.0, {}
    # split into numerator / denominator around a single '/'
    parts = t.split("/")
    if len(parts) > 2:
        return None, None
    for side, chunk in enumerate(parts):
        if not chunk:
            return None, None
        for token in re.split(r"[*.·]", chunk):
            if not token:
                return None, None
            m = re.fullmatch(r"([a-z_]+)(?:\^?(-?\d+))?", token)
            if not m:
                return None, None
            base, exp = m.group(1), m.group(2)
            if base not in _BASE_UNITS:
                return None, None
            e = int(exp) if exp is not None else 1
            if side == 1:
                e = -e
            bscale, bdims = _BASE_UNITS[base]
            scale *= bscale ** e
            dims = _dim_mul(dims, _dim_pow(bdims, e))
    return scale, dims


def _unify_additive(left, right):
    """Addition/subtraction: same dimension AND same unit, or it is invalid."""
    if left[0] == DIM_VIOLATION:
        return left
    if right[0] == DIM_VIOLATION:
        return right
    if left[0] == DIM_LITERAL:
        return right
    if right[0] == DIM_LITERAL:
        return left
    if left[0] == DIM_UNKNOWN or right[0] == DIM_UNKNOWN:
        return (DIM_UNKNOWN, None, None)
    if left[2] != right[2]:
        return (DIM_VIOLATION, None,
                f"cannot add/subtract {_dim_str(left[2])} and "
                f"{_dim_str(right[2])}: different physical dimensions")
    if abs(left[1] - right[1]) > 1e-15 * max(abs(left[1]), abs(right[1]), 1.0):
        return (DIM_VIOLATION, None,
                f"both operands are {_dim_str(left[2])} but are expressed in "
                f"different units (scale {left[1]} vs {right[1]}). B6 performs "
                f"no implicit conversion; convert explicitly and declare it")
    return left


def infer_dimension(node, unit_env):
    """Infer (tag, scale, dims_or_reason) for an expression node.

    A bare numeric literal is DIM_LITERAL: it carries no unit of its own and
    adopts the dimension of whatever it is added to. This is a DECLARED
    convention, documented as a limitation — B6 cannot tell '100 mm' from a
    unitless 100, and it does not pretend otherwise.
    """
    if isinstance(node, ast.Expression):
        return infer_dimension(node.body, unit_env)
    if isinstance(node, ast.Constant):
        return (DIM_LITERAL, 1.0, {})
    if isinstance(node, ast.Name):
        raw = unit_env.get(node.id, "__missing__")
        if raw == "__missing__" or raw is None:
            return (DIM_UNKNOWN, None, None)
        scale, dims = parse_unit(raw)
        if scale is None:
            return (DIM_UNKNOWN, None, None)
        return (DIM_OK, scale, dims)
    if isinstance(node, ast.UnaryOp):
        return infer_dimension(node.operand, unit_env)
    if isinstance(node, ast.BinOp):
        left = infer_dimension(node.left, unit_env)
        right = infer_dimension(node.right, unit_env)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return _unify_additive(left, right)
        if isinstance(node.op, (ast.Mult, ast.Div)):
            for side in (left, right):
                if side[0] == DIM_VIOLATION:
                    return side
            if left[0] == DIM_UNKNOWN or right[0] == DIM_UNKNOWN:
                return (DIM_UNKNOWN, None, None)
            ls = 1.0 if left[0] == DIM_LITERAL else left[1]
            rs = 1.0 if right[0] == DIM_LITERAL else right[1]
            ld = {} if left[0] == DIM_LITERAL else left[2]
            rd = {} if right[0] == DIM_LITERAL else right[2]
            if left[0] == DIM_LITERAL and right[0] == DIM_LITERAL:
                return (DIM_LITERAL, 1.0, {})
            if isinstance(node.op, ast.Mult):
                return (DIM_OK, ls * rs, _dim_mul(ld, rd))
            if rs == 0:
                return (DIM_UNKNOWN, None, None)
            return (DIM_OK, ls / rs, _dim_mul(ld, _dim_pow(rd, -1)))
        if isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or \
                    not isinstance(node.right.value, int):
                return (DIM_UNKNOWN, None, None)
            n = node.right.value
            if left[0] == DIM_LITERAL:
                return (DIM_LITERAL, 1.0, {})
            if left[0] != DIM_OK:
                return left if left[0] == DIM_VIOLATION else (DIM_UNKNOWN, None, None)
            return (DIM_OK, left[1] ** n, _dim_pow(left[2], n))
        # FloorDiv / Mod: dimension of the left operand, scale preserved
        return left if left[0] != DIM_LITERAL else right
    if isinstance(node, ast.Call):
        fname = node.func.id if isinstance(node.func, ast.Name) else ""
        args = [infer_dimension(a, unit_env) for a in node.args]
        if not args:
            return (DIM_UNKNOWN, None, None)
        if fname in ("min", "max"):
            acc = args[0]
            for nxt in args[1:]:
                acc = _unify_additive(acc, nxt)
            return acc
        if fname in ("abs", "round", "floor", "ceil"):
            return args[0]
        if fname == "sqrt":
            a = args[0]
            if a[0] != DIM_OK:
                return a if a[0] == DIM_VIOLATION else (DIM_UNKNOWN, None, None)
            if any(v % 2 for v in a[2].values()):
                return (DIM_VIOLATION, None,
                        f"sqrt of {_dim_str(a[2])} has no whole-number "
                        f"dimension; the result is not expressible")
            return (DIM_OK, math.sqrt(a[1]), _dim_pow(a[2], 1) and
                    {k: v // 2 for k, v in a[2].items()})
        return (DIM_UNKNOWN, None, None)
    return (DIM_UNKNOWN, None, None)


_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Call,
    ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Pow, ast.USub, ast.UAdd, ast.Tuple,
)


class Finding:
    __slots__ = ("rule", "location", "message", "severity")

    def __init__(self, rule, location, message, severity="ERROR"):
        self.rule = rule
        self.location = location
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"[{self.severity}] {self.rule} {self.location}: {self.message}"


# --------------------------------------------------------------------------
# Formula parsing — no eval(), ever
# --------------------------------------------------------------------------
def _normalise(expr):
    """Strip a leading 'name =' so both 'x = a + b' and 'a + b' are accepted."""
    if "=" in expr:
        head, _, tail = expr.partition("=")
        # only treat it as an assignment when the head is a bare identifier
        if re.fullmatch(r"\s*[A-Za-z_][\w.]*\s*", head):
            return tail.strip()
    return expr.strip()


def parse_formula(expr):
    """Parse a formula into an AST. Returns (tree, error_message)."""
    if not isinstance(expr, str) or not expr.strip():
        return None, "formula is empty or not a string"
    body = _normalise(expr)
    low = body.lower()
    for tok in NONDETERMINISTIC_TOKENS:
        if re.search(r"\b" + re.escape(tok), low):
            return None, (f"formula references '{tok}', which is not "
                          f"deterministic or not permitted")
    try:
        tree = ast.parse(body, mode="eval")
    except SyntaxError as exc:
        return None, f"formula cannot be parsed: {exc.msg}"
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return None, (f"formula uses an unsupported construct "
                          f"({type(node).__name__}); only plain arithmetic and "
                          f"whitelisted functions are allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                return None, "only direct calls to whitelisted functions allowed"
            if node.func.id not in SAFE_FUNCS:
                return None, (f"function '{node.func.id}' is not a whitelisted "
                              f"deterministic function {sorted(SAFE_FUNCS)}")
    return tree, None


def formula_variables(tree):
    """Every free variable the formula actually reads."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in SAFE_FUNCS:
            names.add(node.id)
    return names


def evaluate(tree, env):
    """Evaluate a whitelisted AST against a variable environment.

    Returns (value, error). Never executes arbitrary code.
    """
    def _ev(node):
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(
                    node.value, (int, float)):
                raise ValueError("only numeric literals are allowed")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise KeyError(node.id)
            return env[node.id]
        if isinstance(node, ast.UnaryOp):
            v = _ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else +v
        if isinstance(node, ast.BinOp):
            a, b = _ev(node.left), _ev(node.right)
            op = node.op
            if isinstance(op, ast.Add):
                return a + b
            if isinstance(op, ast.Sub):
                return a - b
            if isinstance(op, ast.Mult):
                return a * b
            if isinstance(op, ast.Div):
                if b == 0:
                    raise ZeroDivisionError("division by zero")
                return a / b
            if isinstance(op, ast.FloorDiv):
                if b == 0:
                    raise ZeroDivisionError("division by zero")
                return a // b
            if isinstance(op, ast.Mod):
                if b == 0:
                    raise ZeroDivisionError("modulo by zero")
                return a % b
            if isinstance(op, ast.Pow):
                return a ** b
            raise ValueError(f"unsupported operator {type(op).__name__}")
        if isinstance(node, ast.Call):
            args = [_ev(a) for a in node.args]
            return float(SAFE_FUNCS[node.func.id](*args))
        raise ValueError(f"unsupported node {type(node).__name__}")

    try:
        return _ev(tree), None
    except KeyError as exc:
        return None, f"formula reads undeclared variable {exc}"
    except ZeroDivisionError as exc:
        return None, str(exc)
    except (ValueError, TypeError, OverflowError) as exc:
        return None, str(exc)


# --------------------------------------------------------------------------
# Reference / variable naming
# --------------------------------------------------------------------------
def var_name_for(ref):
    """The variable name a derived_from ref is addressed by inside a formula.

    'space.ceiling_height' -> 'ceiling_height'. The full dotted path is also
    accepted so both spellings resolve to the same declared input.
    """
    return ref.split(".")[-1].split("/")[-1]


# --------------------------------------------------------------------------
# Master traversal — reuses B1's resolver so path semantics stay identical
# --------------------------------------------------------------------------
def _iter_derived(data):
    """Yield (path, fact) for every [D] fact in the master."""
    from validate_refs import iter_facts
    for path, fact in iter_facts(data):
        if isinstance(fact, dict) and fact.get("status") == "D":
            yield path, fact


def _resolve(data, ref):
    from validate_refs import resolve_fact_path
    return resolve_fact_path(data, ref)


def _numeric(value):
    """Scalar number, or None. bool is explicitly NOT a number here."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


# --------------------------------------------------------------------------
# FM-006 dependency graph / cycle detection
# --------------------------------------------------------------------------
def derivation_cycles(data):
    """Every dependency cycle among [D] facts, as ordered node lists."""
    from validate_refs import iter_facts
    node_of = {}
    for path, fact in iter_facts(data):
        node_of[path] = fact

    edges = {}
    for path, fact in _iter_derived(data):
        deps = []
        for ref in fact.get("derived_from") or []:
            target = _resolve(data, ref)
            if target is None:
                continue
            for p2, f2 in node_of.items():
                if f2 is target:
                    deps.append(p2)
                    break
        edges[path] = deps

    cycles, state, stack = [], {}, []

    def visit(n):
        state[n] = 1
        stack.append(n)
        for m in edges.get(n, []):
            if state.get(m) == 1:
                cycles.append(stack[stack.index(m):] + [m])
            elif state.get(m, 0) == 0 and m in edges:
                visit(m)
        stack.pop()
        state[n] = 2

    for n in edges:
        if state.get(n, 0) == 0:
            visit(n)
    return cycles


# --------------------------------------------------------------------------
# Main check
# --------------------------------------------------------------------------
def check_formulas(data):
    findings = []
    verdicts = {}

    # ---- FM-006 cycles first: a cycle makes every member uncomputable ----
    cyclic = set()
    for cyc in derivation_cycles(data):
        for n in cyc:
            cyclic.add(n)
        findings.append(Finding(
            "FM-006", " -> ".join(cyc),
            f"circular derivation: {' -> '.join(cyc)}. No value in this cycle "
            f"can be computed, and none is assumed."))
    for n in cyclic:
        verdicts[n] = UNCOMPUTABLE

    for path, fact in _iter_derived(data):
        if path in cyclic:
            continue

        # A / B1 own the presence and resolvability of these fields. B6 only
        # needs them to do its own job, so their absence is skipped quietly
        # rather than re-reported as a B6 error.
        formula = fact.get("formula")
        refs = fact.get("derived_from") or []
        if not formula or not refs:
            continue

        # ---- FM-009 a [D] must be a computation, not a preference --------
        blob = f"{formula} {fact.get('note', '')} {fact.get('source_ref', '')}".lower()
        hits = [t for t in JUDGEMENT_TOKENS if t in blob]
        if hits:
            findings.append(Finding(
                "FM-009", path,
                f"this [D] carries design-judgement language {sorted(set(hits))}. "
                f"A derived value is a deterministic computation; a preference "
                f"or selection must be recorded as [P], never as [D]."))
            verdicts[path] = MISMATCH
            continue

        # ---- FM-001 the formula must parse and be deterministic ----------
        tree, err = parse_formula(formula)
        if tree is None:
            findings.append(Finding(
                "FM-001", path,
                f"{err}. The value is not computable and is NOT taken on trust."))
            verdicts[path] = UNCOMPUTABLE
            continue
        if fact.get("derivation_type") == "LOGICAL_DEDUCTION":
            # Not arithmetic: B6 records it and refuses to fake a computation.
            findings.append(Finding(
                "FM-001", path,
                "derivation_type is LOGICAL_DEDUCTION, which this layer does "
                "not evaluate arithmetically. Recorded as not arithmetically "
                "verifiable; no value is assumed.", severity="INFO"))
            verdicts[path] = UNCOMPUTABLE
            continue

        used = formula_variables(tree)

        # ---- build the environment from DECLARED inputs only -------------
        env, units, unresolved, bad_status = {}, {}, [], []
        declared = {}
        for ref in refs:
            target = _resolve(data, ref)
            if target is None:
                # resolvability is XR-008's rule; here it simply blocks compute
                unresolved.append(ref)
                continue
            name = var_name_for(ref)
            declared[name] = ref
            declared[ref] = ref
            st = target.get("status")
            if st not in DERIVABLE_INPUT_STATUSES:
                bad_status.append((ref, f"status {st}"))
                continue
            num = _numeric(target.get("value"))
            if num is None:
                bad_status.append((ref, "non-numeric value"))
                continue
            # R02: a number is not automatically a fact. A [C] whose origin is
            # a proposal/assumption/standard is a decision in numeric clothing.
            src_type = target.get("source_type")
            if src_type in NON_FACTUAL_SOURCE_TYPES and st != "D":
                bad_status.append((
                    ref, f"source_type {src_type} — "
                         f"{NON_FACTUAL_SOURCE_TYPES[src_type]}, not a "
                         f"confirmed quantity"))
                continue
            # R02: a [D] input must itself be documented, or its lineage is
            # broken and nothing downstream can be trusted.
            if st == "D" and not (target.get("formula")
                                  and target.get("derived_from")):
                bad_status.append((
                    ref, "a [D] input with no formula/derived_from — "
                         "undocumented derived value, lineage unverifiable"))
                continue
            env[name] = num
            env[ref] = num
            units[name] = target.get("unit")

        # ---- FM-004 inputs not usable for derivation ---------------------
        if bad_status:
            detail = ", ".join(f"'{r}' [{s}]" for r, s in bad_status)
            findings.append(Finding(
                "FM-004", path,
                f"input(s) not admissible for derivation: {detail}. An input "
                f"must be resolvable, of a derivable status, a recorded "
                f"quantity rather than a decision/preference/unapproved "
                f"standard, and — if derived — documented. The result is "
                f"UNCOMPUTABLE; it is never replaced by a guess."))
            verdicts[path] = UNCOMPUTABLE
            continue
        if unresolved:
            findings.append(Finding(
                "FM-004", path,
                f"input(s) {sorted(unresolved)} do not resolve, so the value "
                f"cannot be recomputed (reference resolution itself is owned "
                f"by B1/XR-008).", severity="INFO"))
            verdicts[path] = UNCOMPUTABLE
            continue

        # ---- FM-002 formula reads something not declared -----------------
        undeclared = sorted(v for v in used if v not in env)
        if undeclared:
            findings.append(Finding(
                "FM-002", path,
                f"formula reads {undeclared}, which is not listed in "
                f"derived_from. Hidden inputs are not permitted: every value "
                f"entering a derivation must be declared and traceable."))
            verdicts[path] = MISMATCH
            continue

        # ---- FM-003 declared input never used ----------------------------
        canonical_used = {var_name_for(v) for v in used}
        unused = sorted({var_name_for(r) for r in refs} - canonical_used)
        if unused:
            findings.append(Finding(
                "FM-003", path,
                f"derived_from declares {unused}, which the formula never "
                f"uses. The declared lineage does not match the actual "
                f"computation.", severity="INFO"))

        # ---- FM-008 determinism: same inputs, same answer ----------------
        first, err1 = evaluate(tree, env)
        second, err2 = evaluate(tree, dict(env))
        if err1 or err2:
            findings.append(Finding(
                "FM-001", path,
                f"formula could not be evaluated: {err1 or err2}. No value is "
                f"assumed."))
            verdicts[path] = UNCOMPUTABLE
            continue
        if first != second:
            findings.append(Finding(
                "FM-008", path,
                "formula is not deterministic: two evaluations with identical "
                "inputs disagreed."))
            verdicts[path] = MISMATCH
            continue

        # ---- FM-005 dimensional unit algebra (R02) -----------------------
        # Full dimensional check: addition/subtraction require the SAME
        # dimension AND the same unit; multiplication and division compose
        # dimensions (mm x mm -> mm2, mm2 / mm -> mm, mm / s -> mm/s).
        # B6 never converts: it only proves the declared output unit is the
        # one the formula actually produces.
        out_unit = fact.get("unit")
        unit_env = {n: u for n, u in units.items()}
        dim_tag, dim_scale, dim_info = infer_dimension(tree, unit_env)

        if dim_tag == DIM_VIOLATION:
            findings.append(Finding(
                "FM-005", path,
                f"dimensional error in the formula: {dim_info}. No implicit "
                f"conversion is performed and no result is accepted."))
            verdicts[path] = UNCOMPUTABLE
            continue

        unit_checked = False
        if dim_tag == DIM_OK and out_unit is not None:
            out_scale, out_dims = parse_unit(out_unit)
            if out_scale is None:
                findings.append(Finding(
                    "FM-005", path,
                    f"output unit '{out_unit}' is not parseable by B6, so the "
                    f"dimension of the result cannot be confirmed. Reported as "
                    f"unverified, not as correct.", severity="INFO"))
            elif out_dims != dim_info:
                findings.append(Finding(
                    "FM-005", path,
                    f"the formula produces {_dim_str(dim_info)} but the value "
                    f"is declared in '{out_unit}' ({_dim_str(out_dims)}). A "
                    f"numerically correct figure with the wrong dimension is "
                    f"NOT verified."))
                verdicts[path] = MISMATCH
                continue
            elif abs(out_scale - dim_scale) > 1e-15 * max(
                    abs(out_scale), abs(dim_scale), 1.0):
                findings.append(Finding(
                    "FM-005", path,
                    f"the formula produces {_dim_str(dim_info)} at scale "
                    f"{dim_scale} but the value is declared in '{out_unit}' "
                    f"(scale {out_scale}). Same dimension, different unit: B6 "
                    f"never rescales a value by guess."))
                verdicts[path] = MISMATCH
                continue
            else:
                unit_checked = True
        elif dim_tag == DIM_UNKNOWN or out_unit is None:
            findings.append(Finding(
                "FM-005", path,
                "the dimension of this derivation cannot be determined "
                "(an input or the output carries no parseable unit). The "
                "arithmetic is still checked, but the unit is NOT confirmed.",
                severity="INFO"))

        # ---- FM-007 stored value must equal the computed value -----------
        stored = _numeric(fact.get("value"))
        if stored is None:
            findings.append(Finding(
                "FM-007", path,
                "a [D] fact carries no numeric value to verify against its "
                "own formula.", severity="INFO"))
            verdicts[path] = UNCOMPUTABLE
            continue
        if not (abs(stored - first) <= max(ABS_TOLERANCE,
                                           REL_TOLERANCE * abs(first))):
            findings.append(Finding(
                "FM-007", path,
                f"stored value {stored:g} does not equal the result of its own "
                f"declared formula '{formula}' = {first:g}. The stored value is "
                f"NOT corrected automatically."))
            verdicts[path] = MISMATCH
            continue

        verdicts[path] = VERIFIED

    # ---- FM-010 explicit verdict per derived value -----------------------
    for path in sorted(verdicts):
        findings.append(Finding(
            "FM-010", path, f"derived value verdict: {verdicts[path]}.",
            severity="INFO"))

    return findings, verdicts


def validate_formulas(data):
    findings, verdicts = check_formulas(data)
    ok = len([f for f in findings if f.severity == "ERROR"]) == 0
    return ok, findings, verdicts


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: validate_formulas.py <master.json>")
        sys.exit(2)
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    ok, fs, verdicts = validate_formulas(payload)
    print("FORMULA INTEGRITY:", "PASS" if ok else f"FAIL ({len(fs)} finding(s))")
    for f in fs:
        print(" ", f)
    sys.exit(0 if ok else 1)
