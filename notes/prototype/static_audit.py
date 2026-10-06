#!/usr/bin/env python3
"""Static verifier audit for ITSMBench (no Docker, stdlib only, ~2 seconds).

It reads every task folder and looks for signs that the hidden verifier checks
less than the task asks for. Each finding is a CANDIDATE for a human to look
at, not a proven bug. The live probe (live_probe.py) is how you prove one.

Checks (H = heuristic, may have false positives; E = exact):
  DOC_NAMES_MISSING_TEST  (E) task docs name a test_* function that the verifier does not define
  DEAD_VERIFIER_CODE      (E) helper / constant defined in the verifier but never used
  UNUSED_ARG_IN_CHECK     (E) a check-building function takes an argument it never reads
  ORACLE_CHECKS_MORE      (H) the oracle's own read-back checks restraint (preserved/still
                              active/kept/spared...) but the verifier has no guard checks
  RESTRAINT_UNGUARDED     (H) README/instruction says "do not / preserve / leave unchanged..."
                              but no verifier check looks like a guard
  SIBLINGS_UNCHECKED      (H) the verifier names most records of a group in seed.json
                              (e.g. 11 of one user's 13 OAuth tokens) but not all of them
  REGEX_GRADED_TEXT       (E) an assertion passes on a keyword regex over free text
  SCALAR_COMPARE_ON_LIST  (E) field_equals / field_not_equals against a field that is a
                              list in the seed or initial state (grade.js compares String(list))
  NO_GUARDS_DECLARED      (E) assertions.json says itself that it has no untouched-data guards

Usage:  python3 static_audit.py [--json results/static_audit.json] [--md results/static_report.md]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE.parents[1] / "tasks"

# Words that suggest a check (or an oracle read-back) is about NOT breaking things.
GUARD_NAME = re.compile(r"guard|preserv|remain|untouched|unchanged|intact|spare|kept|keep|"
                        r"control|still|bystander|not_(?:touched|changed|modified|deleted|removed|"
                        r"reopened|deactivated|revoked)|no_(?:collateral|bystander|other)", re.I)
RESTRAINT_TEXT = re.compile(r"\b(do not|don't|must not|never|should not|without (?:breaking|removing|"
                            r"touching|changing|killing)|leave [^.]{0,60}(?:unchanged|untouched|intact|"
                            r"alone)|preserv\w*|only the changes)\b", re.I)
OWNER_FIELD = re.compile(r"user|owner|assignee|member|parent|account|principal|email|login|device|"
                         r"host|employee|author|drive|group|vpc|subnet|custodian|manager", re.I)
NOT_OWNER = re.compile(r"date|time|updated|created|_on$|status|type|last|count", re.I)
RESTRAINT_WORDS = re.compile(r"preserv|still active|keeps?\b|kept|spar|untouched|unchanged|intact|"
                             r"restraint|not (?:touched|changed)|left alone", re.I)


def finding(kind: str, task: str, where: str, msg: str) -> dict:
    return dict(kind=kind, task=task, where=where, msg=msg)


# ---------------------------------------------------------------- pytest family
def pytest_checks(src: str) -> tuple[list[str], bool]:
    """Names of test functions, and whether tests are generated dynamically (globals()[...] = f)."""
    tree = ast.parse(src)
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    dynamic = "globals()[" in src
    return names, dynamic


def dead_code(task: str, path: Path, src: str) -> list[dict]:
    """Top-level helpers/constants in the verifier that nothing references."""
    out = []
    tree = ast.parse(src)
    used = Counter(n.id for n in ast.walk(tree) if isinstance(n, ast.Name))
    used.update(n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            if used[node.name] == 0:
                out.append(finding("DEAD_VERIFIER_CODE", task, f"{path}:{node.lineno}",
                                   f"helper `{node.name}()` is defined but never called"))
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name.isupper() and used[name] == 1:   # 1 = the assignment itself
                out.append(finding("DEAD_VERIFIER_CODE", task, f"{path}:{node.lineno}",
                                   f"constant `{name}` is defined but never used"))
    # A function that builds checks (contains an `assert` in a nested def) but ignores one of its args.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            inner = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n is not node]
            if not any(isinstance(x, ast.Assert) for f in inner for x in ast.walk(f)):
                continue
            body_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            for arg in node.args.args:
                if arg.arg not in body_names and not arg.arg.startswith("_"):
                    out.append(finding("UNUSED_ARG_IN_CHECK", task, f"{path}:{node.lineno}",
                                       f"`{node.name}({', '.join(a.arg for a in node.args.args)})` never "
                                       f"reads `{arg.arg}`, so nothing about `{arg.arg}` is asserted"))
    return out


def oracle_restraint_checks(sol: Path) -> list[tuple[int, str]]:
    """Lines where the oracle's own read-back verifies restraint, e.g. check('primary preserved', ...)."""
    if not sol.exists():
        return []
    hits = []
    for i, line in enumerate(sol.read_text().splitlines(), 1):
        m = re.search(r"\bcheck\(\s*([\"'])(.*?)\1", line)
        if m and RESTRAINT_WORDS.search(m.group(2)):
            hits.append((i, m.group(2)))
    return hits


def string_literals(src: str) -> set[str]:
    """Every string (and id-like integer, e.g. Device42 ip id 3007) written in the verifier."""
    out = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Constant):
            if isinstance(n.value, str) and 4 <= len(n.value) <= 120:
                out.add(n.value)
            elif isinstance(n.value, int) and not isinstance(n.value, bool) and n.value >= 100:
                out.add(str(n.value))
    return out


def sibling_gaps(task: str, seed: dict, literals: set[str]) -> list[dict]:
    """Groups of seed records where the verifier names most, but not all, members.

    Example: task-a-1's verifier names 11 clientIds; seed.json gives Dana 13 tokens.
    We group records in each collection by every scalar field (e.g. userKey) and flag a
    group if the verifier references >= 3 members and misses 1-3 of them.
    """
    out = []
    for app, cols in seed.items():
        if not isinstance(cols, dict):
            continue
        for col, recs in cols.items():
            if not isinstance(recs, list) or len(recs) < 4 or not all(isinstance(r, dict) for r in recs):
                continue
            best = None
            # Only group by "who/what owns this record" fields (userKey, device, AssigneeId...).
            # Grouping by dates or statuses produced mostly noise when we tried it.
            fields = {k for r in recs for k, v in r.items()
                      if isinstance(v, (str, int)) and OWNER_FIELD.search(k) and not NOT_OWNER.search(k)}
            for f in fields:
                values = Counter(str(r.get(f)) for r in recs)
                if len(values) < 2:                        # field is the same everywhere: no info
                    continue
                # A record counts as "named by the verifier" only through a field OTHER than the
                # grouping field (task-a-1's verifier names Dana's email, which every one of her
                # tokens carries; that must not count as naming each token).
                refd = [any(isinstance(v, (str, int)) and str(v) in literals for k, v in r.items() if k != f)
                        for r in recs]
                for val in values:
                    idx = [i for i, r in enumerate(recs) if str(r.get(f)) == val]
                    hit = sum(refd[i] for i in idx)
                    miss = len(idx) - hit
                    if hit >= 3 and 1 <= miss <= 3 and hit / len(idx) >= 0.75:
                        if best is None or len(idx) < best[0]:
                            missing = [recs[i] for i in idx if not refd[i]]
                            best = (len(idx), f, val, hit, missing)
            if best:
                n, f, val, hit, missing = best
                def label(r: dict) -> str:
                    for k in ("clientId", "name", "displayName", "number", "email", "id", "sys_id"):
                        if k in r:
                            return str(r[k])
                    return next((str(v) for k, v in r.items() if re.search(r"(id|name)$", k, re.I)), "?")
                out.append(finding("SIBLINGS_UNCHECKED", task, f"tasks/{task}/environment/seed.json",
                                   f"{app}.{col} where {f}={val!r}: verifier names {hit} of {n} records; "
                                   f"never mentions {[label(r) for r in missing]}"))
    return out


# ------------------------------------------------------------ assertions family
def lookup_seed_record(seed: dict, initial: dict | None, a: dict) -> dict | None:
    """Find the record an assertion points at, in initial_state.json if present, else seed.json."""
    match = a.get("match") or {}
    cands = []
    if initial:
        cands += initial.get(f"{a['app']}::{a['collection']}::{json.dumps(a.get('path_params') or {})}", [])
    cands += (seed.get(a["app"]) or {}).get(a["collection"], []) if isinstance(seed.get(a["app"]), dict) else []
    for r in cands:
        if isinstance(r, dict) and all(str(_get(r, k)).lower() == str(v).lower() for k, v in match.items()):
            return r
    return None


def _get(obj, dotted):
    for k in str(dotted).split("."):
        obj = obj.get(k) if isinstance(obj, dict) else None
    return obj


def audit_assertions(task: str, tdir: Path, seed: dict) -> tuple[list[dict], int, int]:
    doc = json.loads((tdir / "tests" / "assertions.json").read_text())
    al = doc["assertions"] if isinstance(doc, dict) else doc
    ini_p = tdir / "tests" / "initial_state.json"
    initial = json.loads(ini_p.read_text()) if ini_p.exists() else None
    out = []
    rel = f"tasks/{task}/tests/assertions.json"
    desc = doc.get("description", "") if isinstance(doc, dict) else ""
    m = re.search(r"no untouched-data guards|over-remediation (?:stays|is) free", desc, re.I)
    if m:
        out.append(finding("NO_GUARDS_DECLARED", task, rel,
                           f"assertions.json description says: \"...{m.group(0)}...\""))
    guards = sum(1 for a in al if a.get("scored") is False)
    for a in al:
        name = a.get("name", a["type"])
        if a.get("match_pattern") or a["type"] == "field_matches":
            pat = json.dumps(a.get("match_pattern") or a.get("pattern"))
            if len(pat) > 60:                              # long keyword regex over free text
                out.append(finding("REGEX_GRADED_TEXT", task, rel,
                                   f"`{name}` passes if any {a['app']}.{a['collection']} record matches a "
                                   f"{len(pat)}-char keyword regex (negation, e.g. 'no need to escalate', "
                                   f"also matches)"))
        if a["type"] in ("field_equals", "field_not_equals") and "field" in a:
            rec = lookup_seed_record(seed, initial, a)
            val = _get(rec, a["field"]) if rec else None
            if isinstance(val, (list, dict)):
                out.append(finding("SCALAR_COMPARE_ON_LIST", task, rel,
                                   f"`{name}` does {a['type']}({a['field']}, {a['value']!r}) but the field "
                                   f"is a {type(val).__name__} ({json.dumps(val)[:80]}). grade.js compares "
                                   f"String(list), so adding a 2nd element flips the result"))
    return out, len(al), guards


# ----------------------------------------------------------------------- main
def audit_task(tdir: Path) -> tuple[dict, list[dict]]:
    task = tdir.name
    seed = json.loads((tdir / "environment" / "seed.json").read_text())
    readme = (tdir / "README.md").read_text() if (tdir / "README.md").exists() else ""
    instr = (tdir / "instruction.md").read_text()
    docs_text = readme + instr + "".join(
        (tdir / f).read_text() for f in ("fairness.md", "task_construction.json") if (tdir / f).exists())
    n_restraint = len(RESTRAINT_TEXT.findall(readme + "\n" + instr))
    fnd: list[dict] = []
    info = dict(task=task, restraint_phrases=n_restraint, has_readme=bool(readme))

    if (tdir / "tests" / "assertions.json").exists():
        info["family"] = "assertions"
        f2, n, guards = audit_assertions(task, tdir, seed)
        fnd += f2
        info.update(n_checks=n, n_guard_like=guards)
    else:
        info["family"] = "pytest"
        vpath = tdir / "tests" / "test_outputs.py"
        rel = f"tasks/{task}/tests/test_outputs.py"
        src = vpath.read_text()
        names, dynamic = pytest_checks(src)
        guards = [n for n in names if GUARD_NAME.search(n)]
        info.update(n_checks=len(names), dynamic_tests=dynamic, n_guard_like=len(guards))
        # 1. docs that name tests the verifier does not define
        defined = set(names) | set(re.findall(r"def (test_\w+)", src))
        named = set(re.findall(r"\b(test_[a-z0-9_]+)\b", docs_text)) - {"test_outputs"}
        for t in sorted(named - defined):
            if not any(d.startswith(t) for d in defined):   # allow parametrised families
                src_doc = next(f for f in ("fairness.md", "task_construction.json", "README.md", "instruction.md")
                               if (tdir / f).exists() and t in (tdir / f).read_text())
                fnd.append(finding("DOC_NAMES_MISSING_TEST", task, f"tasks/{task}/{src_doc}",
                                   f"docs mention `{t}` but {rel} defines no such test"))
        # 2. dead helpers / unused args
        fnd += dead_code(task, Path(rel), src)
        # 3. the oracle checks restraint that the verifier does not
        hits = oracle_restraint_checks(tdir / "solution" / "solution.py")
        if hits and not guards:
            lines = ", ".join(f"L{i} '{s}'" for i, s in hits[:4])
            fnd.append(finding("ORACLE_CHECKS_MORE", task, f"tasks/{task}/solution/solution.py",
                               f"oracle read-back checks restraint ({lines}) but no verifier check "
                               f"looks like a guard"))
        # 4. seed groups the verifier only partly enumerates
        fnd += sibling_gaps(task, seed, string_literals(src))

    if n_restraint >= 2 and info["n_guard_like"] == 0:
        fnd.append(finding("RESTRAINT_UNGUARDED", task, f"tasks/{task}/README.md",
                           f"README/instruction contain {n_restraint} restraint phrases "
                           f"(do not / preserve / leave unchanged...) but 0 guard-like checks"))
    return info, fnd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "results" / "static_audit.json"))
    ap.add_argument("--md", default=str(HERE / "results" / "static_report.md"))
    args = ap.parse_args()

    infos, findings = [], []
    for tdir in sorted(p for p in TASKS.iterdir() if p.is_dir()):
        info, f = audit_task(tdir)
        infos.append(info)
        findings += f

    # Repo-wide facts (exact, counted from the files)
    tomls = {p.parent.name: p.read_text() for p in TASKS.glob("*/task.toml")}
    public = sum('network_mode = "public"' in t for t in tomls.values())
    uv_net = sum("astral.sh/uv" in p.read_text() for p in TASKS.glob("*/tests/test.sh"))
    pi_versions = Counter(m for p in TASKS.glob("*/environment/Dockerfile")
                          for m in re.findall(r"pi-coding-agent@([\d.]+)", p.read_text()))
    repo = dict(tasks=len(infos), network_public=public, verifier_downloads_uv=uv_net,
                pi_versions_baked_into_images=dict(pi_versions),
                families=dict(Counter(i["family"] for i in infos)),
                tasks_without_readme=[i["task"] for i in infos if not i["has_readme"]])

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(dict(repo=repo, tasks=infos, findings=findings), indent=1))

    by_kind = defaultdict(list)
    for f in findings:
        by_kind[f["kind"]].append(f)
    order = ["DOC_NAMES_MISSING_TEST", "UNUSED_ARG_IN_CHECK", "ORACLE_CHECKS_MORE", "SIBLINGS_UNCHECKED",
             "SCALAR_COMPARE_ON_LIST", "REGEX_GRADED_TEXT", "NO_GUARDS_DECLARED", "RESTRAINT_UNGUARDED",
             "DEAD_VERIFIER_CODE"]
    lines = ["# Static verifier audit (generated by static_audit.py)", "",
             "Every row is a candidate for human review. (H) = heuristic. Prove with live_probe.py.", "",
             "## Repo-wide facts", ""]
    lines += [f"- {k}: {v}" for k, v in repo.items()]
    lines += ["", "## Findings by type", ""]
    lines += [f"- {k}: {len(by_kind[k])} finding(s) in {len({f['task'] for f in by_kind[k]})} task(s)"
              for k in order if by_kind[k]]
    for k in order:
        if not by_kind[k]:
            continue
        lines += ["", f"## {k}", "", "| task | where | detail |", "|---|---|---|"]
        lines += [f"| {f['task']} | `{f['where']}` | {f['msg'].replace('|', '/')} |" for f in by_kind[k]]
    Path(args.md).write_text("\n".join(lines) + "\n")

    # Console summary (this is what you show in the demo)
    print(f"Audited {len(infos)} tasks ({repo['families']}).")
    print(f"network_mode=public: {public}/{len(infos)}  |  verifier downloads uv at grading time: "
          f"{uv_net}/{len(infos)}  |  pi versions baked into images: {dict(pi_versions)}")
    for k in order:
        if by_kind[k]:
            print(f"\n{k}: {len(by_kind[k])}")
            for f in by_kind[k][:6]:
                print(f"  {f['task']:12s} {f['msg'][:150]}")
            if len(by_kind[k]) > 6:
                print(f"  ... {len(by_kind[k]) - 6} more in {Path(args.md).name}")
    print(f"\nWrote {args.md} and {args.json}")


if __name__ == "__main__":
    main()
