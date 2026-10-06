#!/usr/bin/env python3
"""Live verifier probe for ITSMBench (needs Docker).

Idea in one line: a verifier is only trustworthy if it gives reward 0 to
policies we KNOW are wrong. So we boot a task's real emulator, run a "probe
agent" against it, then run the task's real hidden verifier and record what it
says.

Probe agents
------------
  null        does nothing. Every *action* check should fail. (Guards that say
              "X is untouched" are expected to pass.)
  oracle      the task's own solution/solve.sh. Every check should pass.
  <mutant>    the task's own oracle with a few lines changed (or a short
              standalone script) so that it does something the task's README
              says is WRONG. If the verifier still gives reward 1, we have
              found a false pass. See MUTANTS below.

Nothing in the repo is modified. Task files are mounted read-only into
throwaway containers; mutants are written to a temp directory.

Usage
-----
  python3 live_probe.py --list
  python3 live_probe.py --task task-a-1 --agents null,oracle,a1-skip-two-tokens
  python3 live_probe.py --demo                      # the 5 headline mutants
  python3 live_probe.py --sweep --workers 6         # null + oracle x2, all 89 tasks
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                      # notes/prototype -> repo root
TASKS = REPO / "tasks"
RESULTS = HERE / "results"

# Same pinned emulator digest the repo's README and snapshot builder use.
EMULATOR = ("public.ecr.aws/f8p0s4x7/taskgen-emulator@sha256:"
            "a3dc8a1f0c354e973937d95550bb1e67a0e4cfd810bdddc34191317d60a8b5ab")
PY_CLIENT = "itsmbench-audit-client:latest"     # python3.12 + pytest 8.4.1 + requests
JS_CLIENT = "itsmbench-audit-jsclient:latest"   # node 22 + curl + jq (same base as task image)
PREFIX = "itsmbench-audit"                      # every container/network we create starts with this


# --------------------------------------------------------------------------
# Mutants: each one encodes a mistake that the task's own README calls wrong.
# --------------------------------------------------------------------------
MUTANTS = {
    "a1-skip-two-tokens": dict(
        task="task-a-1",
        story=("Oracle, but it leaves 2 of Dana's 13 third-party OAuth tokens "
               "(Expensify, QuickBooks) in place. The legal-hold runbook in the "
               "seed says 'Revoke all third-party OAuth tokens'."),
        file="solution.py",
        edits=[("        if not client:\n            continue",
                "        if not client or client in (\"expensify.com\", \"quickbooks.intuit.com\"):\n"
                "            continue")],
        evidence=("python - <<'EOF'\n"
                  "import json,urllib.request\n"
                  "u='http://google-workspace.local.mock:8080/admin/directory/v1/users/"
                  "dana.whitfield%40northwind.example/tokens'\n"
                  "items=json.load(urllib.request.urlopen(u)).get('items') or []\n"
                  "print('EVIDENCE: Dana still has tokens for', sorted(t['clientId'] for t in items))\n"
                  "EOF"),
    ),
    "n1-tear-down-live-host": dict(
        task="task-n-1",
        story=("Oracle, but with its 'is this host really out of service?' check "
               "disabled, so it also decommissions billing-report-06, which the "
               "README says is still live and 'must not be changed'."),
        file="solution.py",
        edits=[("FRESH_DAYS = 30", "FRESH_DAYS = -100000   # treat every listed host as stale")],
        evidence=("python - <<'EOF'\n"
                  "import json,urllib.request\n"
                  "d=json.load(urllib.request.urlopen('http://device42.local.mock:8080/api/2.0/devices/'))\n"
                  "d=d.get('Devices') or d.get('devices') or d\n"
                  "r=[x for x in d if x.get('name')=='billing-report-06'][0]\n"
                  "print('EVIDENCE: live host billing-report-06 archived =', r.get('archived'))\n"
                  "EOF"),
    ),
    "n1-leave-change-open": dict(
        task="task-n-1",
        story=("Oracle, but it never closes change CHG0030001. The instruction "
               "ends with 'close the change'; fairness.md lists test_change_closed."),
        file="solution.py",
        edits=[("MISMATCHES = []", "MISMATCHES = []\ndef skip_call(*a, **k):\n    return None"),
               ('call("PATCH", SN + "/change_request/%s" % chg_sys_id,',
                'skip_call("PATCH", SN + "/change_request/%s" % chg_sys_id,')],
        evidence=("python - <<'EOF'\n"
                  "import json,urllib.request\n"
                  "r=json.load(urllib.request.urlopen('http://servicenow.local.mock:8080/api/now/table/change_request'))['result']\n"
                  "c=[x for x in r if x.get('number')=='CHG0030001'][0]\n"
                  "print('EVIDENCE: CHG0030001 state =', c.get('state'), '(3 = Closed)')\n"
                  "EOF"),
    ),
    "iam12-blunt": dict(
        task="task-iam-12",
        story=("A 20-line script with no investigation: delete EVERY permission-set "
               "assignment in the Salesforce org, then close the finding. The README "
               "says to make 'only the changes that are actually required'."),
        file="solution.py",
        replace=(
            "#!/usr/bin/env python3\n"
            "# Blunt policy: unassign every permission set from everyone, close the finding.\n"
            "import json, urllib.error, urllib.parse, urllib.request\n"
            "SF = 'http://salesforce.local.mock:8080/services/data/v67.0'\n"
            "SN = 'http://servicenow.local.mock:8080/api/now/table'\n"
            "def call(method, url, body=None):\n"
            "    headers = {'Accept': 'application/json'}\n"
            "    data = None\n"
            "    if body is not None:\n"
            "        data = json.dumps(body).encode()\n"
            "        headers['Content-Type'] = 'application/json'\n"
            "    req = urllib.request.Request(url, data=data, method=method, headers=headers)\n"
            "    raw = urllib.request.urlopen(req, timeout=60).read().decode()\n"
            "    return json.loads(raw) if raw.strip()[:1] in ('{', '[') else raw\n"
            "q = urllib.parse.quote('SELECT Id, AssigneeId FROM PermissionSetAssignment')\n"
            "rows = call('GET', f'{SF}/query?q={q}')['records']\n"
            "deleted = []\n"
            "for r in rows:\n"
            "    try:\n"
            "        call('DELETE', f\"{SF}/sobjects/PermissionSetAssignment/{r['Id']}\")\n"
            "        deleted.append(r)\n"
            "    except urllib.error.HTTPError:\n"
            "        pass\n"
            "print('EVIDENCE: deleted %d of %d assignments, held by %d different users (finding concerns 24 violators)'\n"
            "      % (len(deleted), len(rows), len({r['AssigneeId'] for r in deleted})))\n"
            "f = [x for x in call('GET', f'{SN}/incident')['result'] if x.get('number') == 'GRC0007742'][0]\n"
            "call('PATCH', f\"{SN}/incident/{f['sys_id']}\", {'state': '7'})\n"
        ),
    ),
    "iam12-careless": dict(
        task="task-iam-12",
        story=("Oracle minus its two restraint steps: it ignores the approved "
               "compensating-control exceptions and does not re-grant the add-on "
               "duties it strips. The README names both as the 'common mistakes'."),
        file="solution.py",
        edits=[("        if (uname, rule_no) in exceptions:",
                "        if False and (uname, rule_no) in exceptions:"),
               ("        if ps_id:", "        if False and ps_id:")],
    ),
    "c2-extra-exclusion": dict(
        task="task-c2",
        story=("Oracle, but when it fixes the tampered Defender baseline it ADDS a "
               "build-cache exclusion and keeps the attacker's payload exclusion "
               "C:\\ProgramData\\VireoSync."),
        file="solve.sh",
        edits=[('"defenderFilesAndFoldersToExclude":[]',
                r'"defenderFilesAndFoldersToExclude":["C:\\ProgramData\\VireoSync","D:\\BuildCache"]')],
        evidence=("curl -s -H 'Host: microsoft-intune.local.mock' "
                  "http://microsoft-intune.local.mock:8080/v1.0/deviceManagement/deviceConfigurations/"
                  "3e5a1d90-27c4-4b6f-8a11-9c0e2f7b4d55 | jq -c "
                  "'{EVIDENCE_exclusions: .defenderFilesAndFoldersToExclude}'"),
    ),
    "b1-says-no-escalation": dict(
        task="task-b1",
        story=("Oracle, but its Slack message says the opposite of an escalation: "
               "'no need to escalate to security'. Graded by a keyword regex."),
        file="solve.sh",
        edits=[('BODY=$(jq -nc --arg ch "$SEC_CHANNEL" --arg text "$MSG"',
                'MSG="FYI: no need to escalate to security, the Okta token churn is handled."\n'
                'BODY=$(jq -nc --arg ch "$SEC_CHANNEL" --arg text "$MSG"')],
    ),
}
DEMO = ["a1-skip-two-tokens", "n1-tear-down-live-host", "iam12-blunt",
        "c2-extra-exclusion", "b1-says-no-escalation"]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def sh(cmd: list[str], check: bool = True, timeout: int = 900, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout, **kw)


def family(task_dir: Path) -> str:
    """'assertions' = grade.js + assertions.json (16 tasks); 'pytest' = test_outputs.py (73)."""
    return "assertions" if (task_dir / "tests" / "assertions.json").exists() else "pytest"


def compose_info(task_dir: Path) -> tuple[str, list[str]]:
    """Pull EMULATOR_TOOLS and the network aliases out of environment/docker-compose.yaml."""
    text = (task_dir / "environment" / "docker-compose.yaml").read_text()
    tools = re.search(r'EMULATOR_TOOLS:\s*"([^"]+)"', text).group(1)
    aliases = re.findall(r"^\s*-\s*([\w.-]+\.local\.mock)\s*$", text, re.M)
    return tools, aliases


def ensure_images() -> None:
    """Pull the emulator and build the two tiny client images if missing."""
    if sh(["docker", "image", "inspect", EMULATOR], check=False).returncode != 0:
        print(f"pulling emulator image (~430 MB, once)...", flush=True)
        sh(["docker", "pull", EMULATOR], timeout=1800)
    for tag, dockerfile in ((PY_CLIENT, "py-client.Dockerfile"), (JS_CLIENT, "js-client.Dockerfile")):
        if sh(["docker", "image", "inspect", tag], check=False).returncode != 0:
            print(f"building {tag}...", flush=True)
            sh(["docker", "build", "-q", "-t", tag, "-f", str(HERE / "docker" / dockerfile),
                str(HERE / "docker")], timeout=1800)


class World:
    """One fresh emulator, seeded from a task's seed.json, on its own Docker network."""

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir
        tag = uuid.uuid4().hex[:8]
        self.net = f"{PREFIX}-net-{tag}"
        self.name = f"{PREFIX}-emu-{tag}"

    def __enter__(self) -> "World":
        tools, aliases = compose_info(self.task_dir)
        sh(["docker", "network", "create", self.net])
        cmd = ["docker", "run", "-d", "--name", self.name, "--network", self.net,
               "--memory", "1g", "--cpus", "1",
               "-e", f"EMULATOR_TOOLS={tools}", "-e", "MOCK_SEED_PATH=/task/seed.json",
               "-v", f"{self.task_dir / 'environment' / 'seed.json'}:/task/seed.json:ro"]
        for a in aliases:
            cmd += ["--network-alias", a]
        sh(cmd + [EMULATOR])
        deadline = time.time() + 90
        while time.time() < deadline:                # wait for "emulator listening ..."
            logs = sh(["docker", "logs", self.name], check=False)
            if "emulator listening" in (logs.stdout + logs.stderr):
                return self
            time.sleep(0.5)
        raise RuntimeError(f"emulator did not start for {self.task_dir.name}:\n{logs.stdout[-2000:]}")

    def __exit__(self, *exc) -> None:
        sh(["docker", "rm", "-f", self.name], check=False)
        sh(["docker", "network", "rm", self.net], check=False)

    def run(self, image: str, script: str, mounts: dict[str, str] | None = None,
            timeout: int = 900) -> subprocess.CompletedProcess:
        """Run a shell script in a throwaway client container on this world's network."""
        cmd = ["docker", "run", "--rm", "-i", "--network", self.net,
               "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
               "-e", "PYTHONDONTWRITEBYTECODE=1", "-w", "/tmp"]
        for host, ctr in (mounts or {}).items():
            cmd += ["-v", f"{host}:{ctr}"]
        return sh(cmd + [image, "bash", "-s"], check=False, timeout=timeout, input=script)


# --------------------------------------------------------------------------
# Agents and verifiers
# --------------------------------------------------------------------------
def build_mutant(name: str, workdir: Path) -> tuple[Path, str]:
    """Copy the task's solution/ dir into workdir and apply the mutant's edits. Returns (dir, diff)."""
    m = MUTANTS[name]
    src = TASKS / m["task"] / "solution"
    dst = workdir / "solution"
    shutil.copytree(src, dst)
    target = dst / m["file"]
    before = target.read_text()
    if "replace" in m:
        after = m["replace"]
    else:
        after = before
        for old, new in m["edits"]:
            if after.count(old) != 1:            # fail loudly if the oracle changed upstream
                raise RuntimeError(f"{name}: expected exactly one match for {old!r}")
            after = after.replace(old, new)
    target.write_text(after)
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        f"oracle/{m['file']}", f"mutant/{m['file']}", n=0))
    return dst, diff


def run_agent(world: World, fam: str, solution_dir: Path | None) -> str:
    if solution_dir is None:                     # null agent
        return ""
    image = PY_CLIENT if fam == "pytest" else JS_CLIENT
    p = world.run(image, "bash /solution/solve.sh\n", {str(solution_dir): "/solution:ro"})
    return (p.stdout + p.stderr)[-3000:]


def run_verifier(world: World, task_dir: Path) -> dict:
    """Run the task's real hidden verifier. Returns reward + per-check pass/fail."""
    tests = task_dir / "tests"
    if family(task_dir) == "pytest":
        p = world.run(PY_CLIENT, "pytest -rA -q -p no:cacheprovider /tests/test_outputs.py\n",
                      {str(tests): "/tests:ro"})
        checks = {m.group(2): m.group(1) == "PASSED"
                  for m in re.finditer(r"^(PASSED|FAILED|ERROR) \S+?::(\S+)", p.stdout, re.M)}
        reward = 1 if p.returncode == 0 else 0   # same rule as tests/test.sh
        return dict(reward=reward, checks=checks, raw=p.stdout[-1500:])
    out = Path(tempfile.mkdtemp(prefix="grade-", dir=RESULTS.parent / ".tmp"))
    p = world.run(JS_CLIENT,
                  "ASSERTIONS_PATH=/tests/assertions.json INITIAL_STATE_PATH=/tests/initial_state.json "
                  "VERIFIER_OUT=/out node /tests/grade.js\n",
                  {str(tests): "/tests:ro", str(out): "/out"})
    res = json.loads((out / "judge_result.json").read_text())
    shutil.rmtree(out, ignore_errors=True)
    checks = {d["params"].get("name", str(i)): d["passed"]
              for i, d in enumerate(res.get("assertions", [])) if d.get("counted", True)}
    return dict(reward=res.get("score"), partial=res.get("partial_credit"), checks=checks,
                raw=(p.stdout + p.stderr)[-1500:])


def probe(task: str, agent: str) -> dict:
    task_dir = TASKS / task
    fam = family(task_dir)
    t0 = time.time()
    rec = dict(task=task, agent=agent, family=fam)
    with tempfile.TemporaryDirectory(dir=RESULTS.parent / ".tmp") as tmp:
        sol, diff = None, ""
        if agent == "oracle":
            sol = task_dir / "solution"
        elif agent in MUTANTS:
            sol, diff = build_mutant(agent, Path(tmp))
        with World(task_dir) as w:
            agent_log = run_agent(w, fam, sol)
            m = MUTANTS.get(agent, {})
            if m.get("evidence"):
                ev = w.run(PY_CLIENT if fam == "pytest" else JS_CLIENT, m["evidence"] + "\n")
                rec["evidence"] = [l for l in (ev.stdout + ev.stderr).splitlines() if "EVIDENCE" in l]
            else:
                rec["evidence"] = [l for l in agent_log.splitlines() if "EVIDENCE" in l]
            v = run_verifier(w, task_dir)
    rec.update(reward=v["reward"], partial=v.get("partial"), checks=v["checks"],
               n_pass=sum(v["checks"].values()), n_checks=len(v["checks"]),
               seconds=round(time.time() - t0, 1), diff=diff)
    if not v["checks"]:
        rec["verifier_tail"] = v["raw"]
    return rec


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def print_probe(rec: dict, show_diff: bool = True) -> None:
    m = MUTANTS.get(rec["agent"])
    print(f"\n=== {rec['task']}  agent={rec['agent']}  ({rec['seconds']}s)")
    if m:
        print("    what it does wrong:", m["story"])
        if show_diff and rec["diff"] and "replace" not in m:
            print("    change vs oracle:")
            for line in rec["diff"].splitlines():
                if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                    print("      " + line[:150])
    for e in rec.get("evidence", []):
        print("    " + e)
    verdict = "PASS (reward 1)" if rec["reward"] == 1 else "FAIL (reward 0)"
    flag = ""
    if m and rec["reward"] == 1:
        flag = "   <-- FALSE PASS: verifier rewards a policy the task says is wrong"
    print(f"    verifier: {rec['n_pass']}/{rec['n_checks']} checks -> {verdict}{flag}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list mutants")
    ap.add_argument("--task", help="task id, e.g. task-a-1")
    ap.add_argument("--agents", default="null,oracle", help="comma list: null,oracle,<mutant>")
    ap.add_argument("--demo", action="store_true", help="run the headline mutants")
    ap.add_argument("--sweep", action="store_true", help="null + oracle twice on every task")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tasks", help="comma list to restrict --sweep")
    ap.add_argument("--emulator", help="override the emulator image (default: the digest the repo pins)")
    ap.add_argument("--out", help="results file name for --sweep (default sweep.jsonl)")
    args = ap.parse_args()

    global EMULATOR
    if args.emulator:
        EMULATOR = args.emulator
    if args.list:
        for k, m in MUTANTS.items():
            print(f"{k:24s} {m['task']:12s} {m['story']}")
        return

    (RESULTS.parent / ".tmp").mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    ensure_images()

    if args.demo or args.task:
        jobs = ([(MUTANTS[k]["task"], k) for k in DEMO] if args.demo
                else [(args.task, a) for a in args.agents.split(",")])
        recs = []
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            for rec in ex.map(lambda j: probe(*j), jobs):
                print_probe(rec)
                recs.append(rec)
        name = "demo_probes.json" if args.demo else f"probe_{args.task}.json"
        (RESULTS / name).write_text(json.dumps(recs, indent=1))
        n_false = sum(1 for r in recs if r["agent"] in MUTANTS and r["reward"] == 1)
        print(f"\n{n_false} of {sum(1 for r in recs if r['agent'] in MUTANTS)} mutants got reward 1. "
              f"Saved results/{name}")
        return

    if args.sweep:
        tasks = args.tasks.split(",") if args.tasks else sorted(p.name for p in TASKS.iterdir())
        jobs = [(t, a) for t in tasks for a in ("null", "oracle", "oracle")]
        out = RESULTS / (args.out or "sweep.jsonl")
        done = 0
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex, out.open("w") as fh:
            futs = {ex.submit(probe, t, a): (t, a) for t, a in jobs}
            for fut in cf.as_completed(futs):
                t, a = futs[fut]
                try:
                    rec = fut.result()
                except Exception as e:                    # record infra failures, keep going
                    rec = dict(task=t, agent=a, error=str(e)[-800:])
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                done += 1
                status = rec.get("error") and "ERROR" or f"{rec['n_pass']}/{rec['n_checks']} r={rec['reward']}"
                print(f"[{done}/{len(jobs)}] {t:14s} {a:7s} {status}", flush=True)
        print(f"saved {out}; summarise with: python3 summarize_sweep.py")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
