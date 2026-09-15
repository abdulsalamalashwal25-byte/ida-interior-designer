#!/usr/bin/env python3
"""
ida — the Interior Designer Agent command line.
وكيل التصميم الداخلي — واجهة سطر الأوامر الموحدة.

USAGE
  python3 ida.py <command> [options]
  python3 ida.py <command> --help        (Arabic help per command)

COMMANDS
  init            create a new project workspace
  intake          run the G1 intake gate (may population begin?)
  build           run Phase 01: intake -> validated project_master.json
  validate        run A + B1..B11 and report (carried verdicts)
  readiness       final-approval readiness (blockers, never bypassed)
  status          read-only project dashboard
  plan            generate the Class A floor plan (C1 gate + C3 + D)
  quantities      build the C4 quantity schedule (Q-01..Q-04)
  present         build a Class B presentation SVG from the A assembly
  manifest        assemble the C6 evidence manifest
  fidelity        judge one SVG against its GA assembly (D)
  existing-state  Phase 01 SA Unit 1 (O-1) analytical evidence
  propose         register a [P] proposal (never a decision)
  decide          record a USER decision with its full record
  object          raise a professional objection (OBJ-xxx)
  cr              open a change request for a confirmed element
  approve-cr      approve an OPEN change request (USER only)
  apply-change    apply an APPROVED CR to one master path
  caption         build / lint the guarantee caption (A/B/C language policy)
  test            run the regression suite
  serve           preview a project workspace over HTTP (binds 0.0.0.0)

EXIT CODES
  0  success · 1  error · 2  usage error · 3  abstained / blocked (domain
  refusal — a legitimate outcome, not a crash)

Every command accepts --json for machine-readable output.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "scripts"))

import ida_api as API                                          # noqa: E402
import ida_workspace as WS                                     # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ABSTAIN = 3


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def emit(obj, as_json, pretty_fn=None):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    elif pretty_fn:
        pretty_fn(obj)
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _rule(char="-", width=64):
    print(char * width)


def _kv(label, value):
    print("  %-24s %s" % (label, value))


def _findings_table(refs, limit=40):
    shown = 0
    for ref in refs or []:
        if shown >= limit:
            print("  ... and %d more (use --json for the full list)"
                  % (len(refs) - shown))
            break
        sev = ref.get("severity") or "?"
        print("  [%s] %s %s @ %s" % (
            sev, ref.get("layer"), ref.get("rule"), ref.get("location")))
        msg = str(ref.get("message") or "")[:160]
        if msg:
            print("        %s" % msg)
        shown += 1
    if not shown:
        print("  (no findings)")


def _master_arg(parser, required=True):
    parser.add_argument("--master", required=required,
                        help="path to project_master.json")


def _json_arg(parser):
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

def cmd_init(args):
    target = args.dir or os.path.join(WS.DEFAULT_PROJECTS_DIR, args.project_id)
    try:
        paths = WS.init_project(target, args.project_id,
                                project_name=args.name or args.project_id,
                                track=args.track, is_test=args.test,
                                overwrite=args.overwrite)
    except (FileExistsError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(paths, ensure_ascii=False, indent=2))
    else:
        print("workspace created: %s" % paths["project_dir"])
        print("  intake.json       — fill the answers, then run `ida build`")
        print("  field_specs.json  — BLOCKING / NON_BLOCKING classification")
        print("  05_VIEWS/A|B|C    — output folders per class")
        print("  reports/          — validation / readiness / fidelity JSON")
    return EXIT_OK


# ---------------------------------------------------------------------------
# intake (G1)
# ---------------------------------------------------------------------------

def cmd_intake(args):
    try:
        answers = WS.strip_private(WS.load_json(args.intake))
        specs = WS.load_json(args.specs)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    record = API.run_intake(answers, specs)

    def pretty(rec):
        print("G1 verdict: %s" % rec["verdict"])
        _kv("supplied", len(rec["supplied_fields"]))
        _kv("missing BLOCKING", len(rec["missing_blocking"]))
        for miss in rec["missing_blocking"]:
            print("    ! %s" % miss["field"])
        _kv("missing NON_BLOCKING", len(rec["missing_non_blocking"]))
        for miss in rec["missing_non_blocking"]:
            print("    ? %s (enters master as [U])" % miss["field"])
        _kv("unresolved classification",
            len(rec["unresolved_classification"]))
        for gap in rec["unresolved_classification"]:
            print("    ~ %s (neither BLOCKING nor NON_BLOCKING)"
                  % gap["field"])
        if rec.get("abstention_reason"):
            print("abstention: %s" % rec["abstention_reason"])

    emit(record, args.json, pretty)
    if args.out:
        WS.save_json(record, args.out)
        if not args.json:
            print("record written: %s" % args.out)
    return EXIT_ABSTAIN if record["verdict"] == "ABSTAIN" else EXIT_OK


# ---------------------------------------------------------------------------
# build (Phase 01 pipeline)
# ---------------------------------------------------------------------------

def cmd_build(args):
    project_dir = args.project
    if project_dir:
        paths = WS.project_paths(project_dir)
        intake_path, specs_path = paths["intake"], paths["field_specs"]
        master_out = args.out or paths["master"]
    else:
        if not args.intake or not args.specs or not args.out:
            print("error: give --project, or --intake + --specs + --out",
                  file=sys.stderr)
            return 2
        intake_path, specs_path, master_out = \
            args.intake, args.specs, args.out
    try:
        master, record = API.run_phase01_from_files(
            intake_path, specs_path, args.recorded_on)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR

    def pretty(rec):
        print("Phase 01 state: %s" % rec.get("state"))
        print("lifecycle: %s" % " -> ".join(rec.get("lifecycle_trace", [])))
        for gate in ("G1", "G2", "G3", "G4", "G5"):
            g = (rec.get("gates") or {}).get(gate)
            if g is None:
                continue
            if gate == "G1":
                print("  G1 intake: %s" % g.get("verdict"))
            elif gate == "G2":
                print("  G2 populate: %d tagged, %d unknowns, %d "
                      "contradictions" % (
                          len(g.get("tagged_fields", [])),
                          len(g.get("unknowns_registered", [])),
                          len(g.get("contradictions", []))))
                for c in g.get("contradictions", []):
                    print("    CONTRADICTION @ %s: %s" % (
                        c.get("field"), c.get("detail")))
            elif gate in ("G3", "G4"):
                print("  %s %s: %s (%d errors)" % (
                    gate, g.get("layer") or "B1..B11",
                    g.get("result"), g.get("error_count", 0)))
            elif gate == "G5":
                print("  G5 readiness: ready=%s (%d blockers)" % (
                    g.get("ready"), g.get("blocker_count", 0)))
                for b in g.get("blockers", [])[:10]:
                    print("    ! %s" % b)
        if rec.get("abstention_reason"):
            print("abstention: %s" % rec["abstention_reason"])
        if rec.get("note"):
            print("note: %s" % rec["note"])

    emit(record, args.json, pretty)
    state = record.get("state")
    if master is not None:
        # Underscore-prefixed keys are documentation, never data: they are
        # stripped before the SSOT is persisted (the schema forbids them).
        master = WS.strip_private(master)
        master, bannered = WS.ensure_test_banner(master)
        WS.save_json(master, master_out)
        if not args.json:
            print("master written: %s" % master_out)
            if bannered:
                print("test banner applied (RULES.md 19: test projects "
                      "carry the banner in the data)")
    if args.record_out:
        WS.save_json(record, args.record_out)
    if state in ("ABSTAINED", "BLOCKED_DECLARED"):
        return EXIT_ABSTAIN
    if state == "VALIDATION_FAILED":
        return EXIT_ERROR
    return EXIT_OK


# ---------------------------------------------------------------------------
# validate / readiness / status
# ---------------------------------------------------------------------------

def cmd_validate(args):
    try:
        master = API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    try:
        report = API.validate_all(master)
    except ImportError as exc:
        print("error: missing dependency (%s). Install requirements: "
              "pip install -r requirements.txt" % exc, file=sys.stderr)
        return EXIT_ERROR

    def pretty(rep):
        summary = rep["summary"]
        print("validation: %s (%d errors)" % (
            summary["result"], summary["total_errors"]))
        direct = rep.get("schema_gate_direct") or {}
        print("  A  schema_gate: %s (%d errors)" % (
            "PASS" if direct.get("ok") else "FAIL",
            direct.get("error_count", 0)))
        layers = (rep["rules"].get("layers") or {})
        for layer in sorted(layers):
            info = layers[layer]
            print("  %s %-16s %s (%d findings, %d errors)" % (
                layer, info.get("module"), info.get("result"),
                info.get("findings", 0), info.get("errors", 0)))
        if summary["total_errors"]:
            _rule()
            if direct.get("errors"):
                print("ERROR findings (schema):")
                for err in direct["errors"][:40]:
                    print("  [ERROR] A %s" % str(err)[:200])
                if len(direct["errors"]) > 40:
                    print("  ... and %d more (use --json)" % (
                        len(direct["errors"]) - 40))
            print("ERROR findings (rules):")
            _findings_table([r for r in rep["rules"].get(
                "finding_references", [])
                if r.get("severity") == "ERROR"])

    emit(report, args.json, pretty)
    if args.out:
        WS.save_json(report, args.out)
    return EXIT_ERROR if report["summary"]["total_errors"] else EXIT_OK


def cmd_readiness(args):
    try:
        master = API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    try:
        report = API.readiness(master)
    except ImportError as exc:
        print("error: missing dependency (%s). Install requirements: "
              "pip install -r requirements.txt" % exc, file=sys.stderr)
        return EXIT_ERROR

    def pretty(rep):
        gate = rep["final_approval_gate"]
        print("ready for final approval: %s"
              % rep["ready_for_final_approval"])
        print("blockers (%d):" % gate["blocker_count"])
        for blocker in gate["blockers"]:
            print("  ! %s" % blocker)
        b7 = rep.get("blocking_integrity") or {}
        if b7.get("b7_integrity_errors"):
            print("B7 integrity errors:")
            for err in b7["b7_integrity_errors"]:
                print("  ! %s" % err)

    emit(report, args.json, pretty)
    if args.out:
        WS.save_json(report, args.out)
    return EXIT_OK if report["ready_for_final_approval"] else EXIT_ABSTAIN


def cmd_status(args):
    try:
        master = API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    report = API.project_status(master)

    def pretty(rep):
        meta = rep["meta"]
        print("%s — %s  (rev %s, %s)" % (
            meta.get("project_id"), meta.get("project_name"),
            meta.get("revision"), meta.get("status")))
        counts = rep["counts"]
        print("elements: %d walls, %d openings, %d columns, %d zones, "
              "%d furniture, %d materials, %d cameras, %d outputs" % (
                  counts["walls"], counts["openings"], counts["columns"],
                  counts["zones"], counts["furniture"], counts["materials"],
                  counts["cameras"], counts["outputs"]))
        regs = rep["registers"]
        print("unknowns: %d (%d blocking)" % (
            regs["unknowns_total"], regs["unknowns_blocking"]))
        for unk in regs["unknowns"]:
            flag = "BLOCKING" if unk.get("blocking") else "non-blocking"
            print("  [%s] %s — %s" % (flag, unk.get("id"),
                                      unk.get("question")))
        print("assumptions: %d (%d pending)" % (
            regs["assumptions_total"], regs["assumptions_pending"]))
        print("proposals: %d · decisions: %d · open CRs: %d · "
              "open objections: %d" % (
                  regs["proposals_total"], regs["decisions_total"],
                  regs["change_requests_open"], regs["objections_open"]))
        ready = rep["readiness"]
        print("ready for final approval: %s" %
              ready.get("ready_for_final_approval"))
        for blocker in (ready.get("blockers") or [])[:10]:
            print("  ! %s" % blocker)

    emit(report, args.json, pretty)
    if args.out:
        WS.save_json(report, args.out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# plan (Class A)
# ---------------------------------------------------------------------------

def cmd_plan(args):
    try:
        master = API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    try:
        bundle = API.generate_plan(
            master, output_id=args.output_id, output_view=args.view,
            run_fidelity=not args.no_fidelity, skip_gate=args.skip_gate)
    except API.Abstained as exc:
        print("ABSTAINED: %s" % exc, file=sys.stderr)
        if args.json:
            print(json.dumps(exc.record, ensure_ascii=False, indent=2,
                             default=str))
        elif (exc.record.get("gate") or {}).get("abstention_text"):
            print(exc.record["gate"]["abstention_text"])
        if args.record_out:
            WS.save_json(exc.record, args.record_out)
        return EXIT_ABSTAIN
    except ImportError as exc:
        print("error: missing dependency (%s)" % exc, file=sys.stderr)
        return EXIT_ERROR

    ident = bundle["identity"]
    filename = WS.output_filename(ident["project_id"],
                                  ident["master_revision"], "A",
                                  args.view, "svg")
    if args.project:
        svg_path = os.path.join(WS.project_paths(args.project)["views_A"],
                                filename)
        reports = WS.project_paths(args.project)["reports"]
        base = os.path.splitext(filename)[0]
        record_path = args.record_out or os.path.join(
            reports, base + ".bundle.json")
    else:
        svg_path = args.svg_out or filename
        record_path = args.record_out
    os.makedirs(os.path.dirname(os.path.abspath(svg_path)), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as handle:
        handle.write(bundle["svg"])
    # The sidecar carries everything D and C6 need; the SVG stays pristine.
    sidecar = {k: v for k, v in bundle.items() if k != "svg"}
    sidecar["svg_file"] = os.path.basename(svg_path)
    if record_path:
        WS.save_json(sidecar, record_path)

    if args.json:
        out = dict(sidecar)
        out["svg_path"] = svg_path
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    else:
        print("Class A plan emitted: %s" % svg_path)
        asm = bundle.get("assembly") or {}
        print("  walls: %d · openings: %d · not represented: %d" % (
            len(asm.get("walls", [])), len(asm.get("openings", [])),
            len(asm.get("not_represented", []))))
        fidelity = bundle.get("fidelity") or {}
        print("  fidelity (D): %s" % fidelity.get("verdict"))
        if record_path:
            print("  bundle record: %s" % record_path)
        print("  DESIGN INTENT — NOT FOR CONSTRUCTION")
    return EXIT_OK


# ---------------------------------------------------------------------------
# quantities / present / manifest / fidelity / existing-state
# ---------------------------------------------------------------------------

def cmd_quantities(args):
    try:
        master = API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    schedule = API.build_quantities(master)

    def pretty(sched):
        print("quantity schedule: %d items, %d exclusions" % (
            len(sched.get("items", [])), len(sched.get("exclusions", []))))
        for item in sched.get("items", []):
            print("  %s %-8s = %s %s  (%s)" % (
                item.get("quantity_id"), item.get("element_id"),
                item.get("value"), item.get("unit"),
                item.get("operation")))
        for exc_item in sched.get("exclusions", []):
            print("  EXCLUDED %s %s: %s" % (
                exc_item.get("code"), exc_item.get("element_id"),
                exc_item.get("reason")))
        print("completeness: %s" % sched.get("completeness"))

    emit(schedule, args.json, pretty)
    if args.out:
        WS.save_json(schedule, args.out)
        if not args.json:
            print("schedule written: %s" % args.out)
    return EXIT_OK


def cmd_present(args):
    try:
        bundle = WS.load_json(args.assembly)
    except (OSError, ValueError) as exc:
        print("error: cannot read A bundle (%s)" % exc, file=sys.stderr)
        return EXIT_ERROR
    ga = bundle.get("assembly")
    if not isinstance(ga, dict):
        print("error: bundle has no GA assembly (run `ida plan` first)",
              file=sys.stderr)
        return EXIT_ERROR
    params = {}
    if args.params:
        try:
            params = WS.load_json(args.params)
        except (OSError, ValueError) as exc:
            print("error: cannot read params (%s)" % exc, file=sys.stderr)
            return EXIT_ERROR
    identity = bundle.get("identity")
    record = API.present_class_b(ga, parameters=params, identity=identity,
                                 declared_by=args.declared_by)
    if record.get("status") != "EMITTED" or not record.get("svg"):
        abs_info = record.get("abstention") or {}
        print("ABSTAINED: %s" % (
            abs_info.get("message") or abs_info.get("code")
            or "presentation refused"), file=sys.stderr)
        return EXIT_ABSTAIN
    parent = bundle.get("svg_file") or args.assembly
    record["derived_from_output"] = parent
    record["supersedes_A"] = False
    ident = identity or {}
    filename = WS.output_filename(ident.get("project_id", "PRJ"),
                                  ident.get("master_revision", "R"),
                                  "B", args.view, "svg")
    if args.project:
        svg_path = os.path.join(WS.project_paths(args.project)["views_B"],
                                filename)
    else:
        svg_path = args.svg_out or filename
    os.makedirs(os.path.dirname(os.path.abspath(svg_path)), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as handle:
        handle.write(record["svg"])
    if args.json:
        out = dict(record)
        out.pop("svg", None)
        out["svg_path"] = svg_path
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    else:
        print("Class B presentation emitted: %s" % svg_path)
        print("  derived from A: %s (B never supersedes A)" % parent)
        print("  admitted: %s" % [v.get("name") if isinstance(v, dict)
                                  else v
                                  for v in record.get(
                                      "parameters_admitted", [])])
        print("  rejected: %d" % len(record.get("parameters_rejected", [])))
    if args.record_out:
        sidecar = dict(record)
        sidecar.pop("svg", None)
        WS.save_json(sidecar, args.record_out)
    return EXIT_OK


def cmd_manifest(args):
    pairs = []
    for spec in args.record or []:
        if "=" not in spec:
            print("error: --record must look like OWNER=path "
                  "(e.g. C3=reports/plan.bundle.json)", file=sys.stderr)
            return 2
        owner, path = spec.split("=", 1)
        try:
            pairs.append((owner.strip(), WS.load_json(path.strip())))
        except (OSError, ValueError) as exc:
            print("error: cannot read %s (%s)" % (path, exc), file=sys.stderr)
            return EXIT_ERROR
    identity = None
    if args.master:
        try:
            identity = WS.identity_of(API.load_master(args.master))
        except API.IDAError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return EXIT_ERROR
    manifest = API.assemble_manifest(pairs, identity=identity,
                                     environment=args.env and WS.load_json(
                                         args.env) or None)

    def pretty(mani):
        print("manifest: %d members (assembly only — no verdicts)" % len(
            mani.get("members", [])))
        for member in mani.get("members", []):
            print("  %s · %s · %s" % (
                member.get("source_owner"), member.get("output_id"),
                member.get("source_status")))

    emit(manifest, args.json, pretty)
    if args.out:
        WS.save_json(manifest, args.out)
        if not args.json:
            print("manifest written: %s" % args.out)
    return EXIT_OK


def cmd_fidelity(args):
    try:
        bundle = WS.load_json(args.assembly)
    except (OSError, ValueError) as exc:
        print("error: cannot read bundle (%s)" % exc, file=sys.stderr)
        return EXIT_ERROR
    ga = bundle.get("assembly")
    if not isinstance(ga, dict):
        print("error: bundle has no GA assembly", file=sys.stderr)
        return EXIT_ERROR
    try:
        with open(args.svg, encoding="utf-8") as handle:
            svg_text = handle.read()
    except OSError as exc:
        print("error: cannot read SVG (%s)" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.pair:
        try:
            with open(args.pair, encoding="utf-8") as handle:
                b_svg = handle.read()
        except OSError as exc:
            print("error: cannot read pair SVG (%s)" % exc, file=sys.stderr)
            return EXIT_ERROR
        report = API.assess_pair(ga, svg_text, b_svg)
    else:
        report = API.assess_fidelity(ga, svg_text, output_class=args.cls)

    def pretty(rep):
        if "A" in rep:
            print("A fidelity: %s" % rep["A"].get("verdict"))
            print("B fidelity: %s" % rep["B"].get("verdict"))
            print("note: each judged directly against GA; A-to-B "
                  "agreement is not a reference")
        else:
            print("fidelity verdict: %s (scope: %s)" % (
                rep.get("verdict"), rep.get("scope")))
            for diff in rep.get("differences", [])[:10]:
                print("  - %s" % diff)
            if rep.get("reason"):
                print("reason: %s" % rep["reason"])

    emit(report, args.json, pretty)
    if args.out:
        WS.save_json(report, args.out)
    return EXIT_OK


def cmd_existing_state(args):
    try:
        master = API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    record = API.existing_state(master)

    def pretty(rec):
        print("O-1 %s [%s]: %s" % (
            rec.get("output_name"), rec.get("output_class"),
            rec.get("status")))
        for key in ("space", "fixed_elements", "openings", "presence"):
            if rec.get(key) is not None:
                print("  %s: present" % key)
        for unk in (rec.get("unknowns") or [])[:15]:
            print("  UNKNOWN @ %s" % unk.get("path", unk))

    emit(record, args.json, pretty)
    if args.out:
        WS.save_json(record, args.out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# Governance commands
# ---------------------------------------------------------------------------

def _load_master_for_gov(args):
    try:
        return API.load_master(args.master)
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return None


def _save_gov_master(master, args, entry):
    if args.in_place:
        API.save_master(master, args.master)
        print("master updated: %s" % args.master)
    if args.out:
        API.save_master(master, args.out)
        print("master written: %s" % args.out)
    if not args.in_place and not args.out:
        print(json.dumps(entry, ensure_ascii=False, indent=2, default=str))
        print("(dry run — nothing saved; use --in-place or --out)")
    return EXIT_OK


def cmd_propose(args):
    master = _load_master_for_gov(args)
    if master is None:
        return EXIT_ERROR
    try:
        master, entry = API.record_proposal(
            master, args.text, raised_on=args.date)
    except API.GovernanceError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        print("proposal %s registered (OPEN — a proposal, never a decision)"
              % entry["id"])
    return _save_gov_master(master, args, entry)


def cmd_decide(args):
    master = _load_master_for_gov(args)
    if master is None:
        return EXIT_ERROR
    try:
        master, entry = API.record_decision(
            master, args.title, linked_proposal=args.proposal,
            linked_elements=args.link or [], rationale=args.rationale,
            alternatives_considered=args.alternative or [],
            actor="USER", approved_on=args.date,
            approved_in_revision=args.revision)
    except API.GovernanceError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        print("decision %s recorded (approved_by USER; proposal %s now "
              "APPROVED)" % (entry["decision_id"], entry["linked_proposal"]))
    return _save_gov_master(master, args, entry)


def cmd_object(args):
    master = _load_master_for_gov(args)
    if master is None:
        return EXIT_ERROR
    try:
        master, entry = API.record_objection(
            master, args.against, args.problem, args.impact,
            args.alternative, raised_on=args.date)
    except API.GovernanceError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        print("objection %s raised (OPEN — blocks final approval)"
              % entry["id"])
        print("note: an OPEN objection against a standing decision is a "
              "B10 lifecycle error until resolved, withdrawn, accepted or "
              "explicitly overridden (RL-003)")
    return _save_gov_master(master, args, entry)


def _parse_json_value(text, name):
    try:
        return json.loads(text)
    except ValueError as exc:
        print("error: %s must be valid JSON (%s)" % (name, exc),
              file=sys.stderr)
        return None


def cmd_cr(args):
    master = _load_master_for_gov(args)
    if master is None:
        return EXIT_ERROR
    current = _parse_json_value(args.current, "--current")
    proposed = _parse_json_value(args.proposed, "--proposed")
    if current is None and args.current.strip() != "null":
        return 2
    if proposed is None and args.proposed.strip() != "null":
        return 2
    try:
        master, entry = API.record_change_request(
            master, args.target_element, current, proposed,
            args.reason, args.impact, classification=args.cls,
            alternatives=args.alternative or [], raised_on=args.date)
    except API.GovernanceError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        print("change request %s opened (%s, PENDING_APPROVAL — awaiting "
              "USER approval)" % (entry["id"], entry["classification"]))
    return _save_gov_master(master, args, entry)


def cmd_approve_cr(args):
    master = _load_master_for_gov(args)
    if master is None:
        return EXIT_ERROR
    try:
        master, entry = API.approve_change_request(
            master, args.cr_id, actor="USER", approved_on=args.date)
    except API.GovernanceError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        print("CR %s APPROVED by USER" % entry["id"])
    return _save_gov_master(master, args, entry)


def cmd_apply_change(args):
    master = _load_master_for_gov(args)
    if master is None:
        return EXIT_ERROR
    try:
        new_fact = json.loads(args.fact)
    except ValueError as exc:
        print("error: --fact must be a JSON object (%s)" % exc,
              file=sys.stderr)
        return 2
    try:
        master, applied = API.apply_approved_change(
            master, args.cr_id, args.path, new_fact)
    except API.GovernanceError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(applied, ensure_ascii=False, indent=2, default=str))
    else:
        print("CR %s applied to %s (CR now APPLIED, changelog appended)"
              % (applied["cr_id"], applied["path"]))
    return _save_gov_master(master, args, applied)


# ---------------------------------------------------------------------------
# caption / test / serve
# ---------------------------------------------------------------------------

def cmd_caption(args):
    try:
        result = API.caption_for(args.cls, args.view or "", args.rev,
                                 extra=args.extra or "")
    except ImportError as exc:
        print("error: missing dependency (%s)" % exc, file=sys.stderr)
        return EXIT_ERROR
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["caption"])
        for problem in result["problems"]:
            print("  LINT: %s" % problem)
    return EXIT_ERROR if result["problems"] else EXIT_OK


def cmd_test(args):
    import subprocess
    root = os.path.dirname(os.path.abspath(__file__))
    if args.suite:
        target = os.path.join(root, "tests", args.suite)
        if not os.path.exists(target):
            print("error: no such suite: %s" % args.suite, file=sys.stderr)
            return EXIT_ERROR
        proc = subprocess.run([sys.executable, target])
        return proc.returncode
    proc = subprocess.run([sys.executable,
                           os.path.join(root, "tests", "run_all.py")])
    return proc.returncode


def cmd_serve(args):
    import functools
    import http.server
    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print("error: no such directory: %s" % directory, file=sys.stderr)
        return EXIT_ERROR
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=directory)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print("serving %s at http://0.0.0.0:%d/ (Ctrl+C to stop)"
          % (directory, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="ida", description="Interior Designer Agent — unified CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a new project workspace")
    p.add_argument("project_id", help="e.g. PRJ-01")
    p.add_argument("--name", default="", help="project name")
    p.add_argument("--dir", default="",
                   help="workspace dir (default: projects/<id>)")
    p.add_argument("--track", default="FULL", choices=("FULL", "LITE"))
    p.add_argument("--test", action="store_true",
                   help="mark as a TEST project (banner required)")
    p.add_argument("--overwrite", action="store_true")
    _json_arg(p)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("intake", help="run the G1 intake gate")
    p.add_argument("--intake", required=True, help="intake.json answers")
    p.add_argument("--specs", required=True, help="field_specs.json")
    p.add_argument("--out", default="", help="write the G1 record here")
    p.add_argument("--record-out", default="",
                   help="alias of --out")
    _json_arg(p)
    p.set_defaults(func=cmd_intake)

    p = sub.add_parser("build", help="Phase 01: intake -> validated master")
    p.add_argument("--project", default="",
                   help="project workspace dir (uses its intake/specs)")
    p.add_argument("--intake", default="")
    p.add_argument("--specs", default="")
    p.add_argument("--out", default="", help="master output path")
    p.add_argument("--record-out", default="")
    p.add_argument("--recorded-on", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("validate", help="run A + B1..B11")
    _master_arg(p)
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("readiness", help="final-approval readiness")
    _master_arg(p)
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_readiness)

    p = sub.add_parser("status", help="read-only project dashboard")
    _master_arg(p)
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("plan", help="generate the Class A floor plan")
    _master_arg(p)
    p.add_argument("--project", default="",
                   help="workspace (outputs go to 05_VIEWS/A_accurate/)")
    p.add_argument("--view", default="FloorPlan")
    p.add_argument("--output-id", default="PLAN-01")
    p.add_argument("--svg-out", default="")
    p.add_argument("--record-out", default="")
    p.add_argument("--skip-gate", action="store_true",
                   help="skip the C1 gate (recorded honestly in the bundle)")
    p.add_argument("--no-fidelity", action="store_true",
                   help="skip the D fidelity assessment")
    _json_arg(p)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("quantities", help="C4 quantity schedule")
    _master_arg(p)
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_quantities)

    p = sub.add_parser("present", help="Class B SVG from the A assembly")
    p.add_argument("--assembly", required=True,
                   help="the A bundle record from `ida plan`")
    p.add_argument("--params", default="",
                   help="JSON file of presentation parameters")
    p.add_argument("--declared-by", default="caller")
    p.add_argument("--view", default="Board01")
    p.add_argument("--project", default="")
    p.add_argument("--svg-out", default="")
    p.add_argument("--record-out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_present)

    p = sub.add_parser("manifest", help="C6 evidence manifest")
    p.add_argument("--record", action="append", default=[],
                   help="OWNER=path, repeatable (e.g. C3=reports/x.json)")
    p.add_argument("--master", default="")
    p.add_argument("--env", default="")
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("fidelity", help="D: judge SVG vs GA assembly")
    p.add_argument("--assembly", required=True, help="bundle record JSON")
    p.add_argument("--svg", required=True, help="SVG artefact to judge")
    p.add_argument("--cls", default="A", choices=("A", "B"))
    p.add_argument("--pair", default="",
                   help="second SVG: assess A and B each against GA")
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_fidelity)

    p = sub.add_parser("existing-state", help="SA Unit 1 (O-1) evidence")
    _master_arg(p)
    p.add_argument("--out", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_existing_state)

    def gov_common(sp, help_text):
        sp.add_argument("title", help=help_text)
        _master_arg(sp)
        sp.add_argument("--date", default="",
                        help="recorded_on (default: today UTC)")
        sp.add_argument("--out", default="")
        sp.add_argument("--in-place", action="store_true")
        _json_arg(sp)

    p = sub.add_parser("propose", help="register a [P] proposal")
    p.add_argument("text", help="proposal text (min 5 chars)")
    _master_arg(p)
    p.add_argument("--date", default="")
    p.add_argument("--out", default="")
    p.add_argument("--in-place", action="store_true")
    _json_arg(p)
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("decide", help="record a USER decision")
    gov_common(p, "decision title")
    p.add_argument("--rationale", required=True,
                   help="WHY — mandatory, min 10 chars")
    p.add_argument("--proposal", required=True,
                   help="the OPEN proposal this decision rests on")
    p.add_argument("--link", action="append", default=[],
                   help="linked element id (repeatable)")
    p.add_argument("--alternative", action="append", default=[])
    p.add_argument("--revision", required=True,
                   help="approved_in_revision, e.g. R01")
    p.add_argument("--override", default="",
                   help="user_override_of OBJ id, when overriding")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("object", help="raise an objection")
    p.add_argument("--against", required=True,
                   help="decision id under objection (or free text)")
    p.add_argument("--problem", required=True,
                   help="the problem — min 10 chars")
    p.add_argument("--impact", required=True, help="min 5 chars")
    p.add_argument("--alternative", required=True, help="min 5 chars")
    _master_arg(p)
    p.add_argument("--date", default="")
    p.add_argument("--out", default="")
    p.add_argument("--in-place", action="store_true")
    _json_arg(p)
    p.set_defaults(func=cmd_object)

    p = sub.add_parser("cr", help="open a change request")
    p.add_argument("--target-element", required=True,
                   help="e.g. space/ceiling_height")
    p.add_argument("--current", required=True,
                   help="current value as JSON")
    p.add_argument("--proposed", required=True,
                   help="proposed value as JSON")
    p.add_argument("--reason", required=True, help="min 5 chars")
    p.add_argument("--impact", required=True, help="min 5 chars")
    p.add_argument("--cls", default="MINOR", choices=("MINOR", "MAJOR"))
    p.add_argument("--alternative", action="append", default=[])
    _master_arg(p)
    p.add_argument("--date", default="")
    p.add_argument("--out", default="")
    p.add_argument("--in-place", action="store_true")
    _json_arg(p)
    p.set_defaults(func=cmd_cr)

    p = sub.add_parser("approve-cr", help="approve an OPEN CR (USER only)")
    p.add_argument("cr_id", help="e.g. CR-001")
    _master_arg(p)
    p.add_argument("--date", default="", required=False)
    p.add_argument("--out", default="")
    p.add_argument("--in-place", action="store_true")
    _json_arg(p)
    p.set_defaults(func=cmd_approve_cr)

    p = sub.add_parser("apply-change",
                       help="apply an APPROVED CR to one master path")
    p.add_argument("cr_id", help="e.g. CR-001")
    _master_arg(p)
    p.add_argument("--path", required=True,
                   help="master path, e.g. space/ceiling_height")
    p.add_argument("--fact", required=True,
                   help="new tagged fact as a JSON object")
    p.add_argument("--applied-in-revision", default="",
                   help="defaults to the master's current revision")
    p.add_argument("--out", default="")
    p.add_argument("--in-place", action="store_true")
    _json_arg(p)
    p.set_defaults(func=cmd_apply_change)

    p = sub.add_parser("caption", help="guarantee caption (A/B/C policy)")
    p.add_argument("--cls", required=True, choices=("A", "B", "C"))
    p.add_argument("--view", default="")
    p.add_argument("--rev", default="R01")
    p.add_argument("--extra", default="")
    _json_arg(p)
    p.set_defaults(func=cmd_caption)

    p = sub.add_parser("test", help="run the regression suite")
    p.add_argument("--suite", default="",
                   help="single suite file, e.g. test_00_5_A.py")
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("serve", help="preview a workspace over HTTP")
    p.add_argument("--dir", default=".", help="directory to serve")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    # --out is the canonical writer; --record-out is its alias on intake.
    if getattr(args, "command", "") == "intake" and args.record_out:
        args.out = args.record_out
    if hasattr(args, "date") and not getattr(args, "date", None):
        args.date = WS.utc_today()
    try:
        return args.func(args)
    except BrokenPipeError:
        return EXIT_OK
    except API.IDAError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return EXIT_ERROR
    except ImportError as exc:
        print("error: missing dependency (%s). Run: "
              "pip install -r requirements.txt" % exc, file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
