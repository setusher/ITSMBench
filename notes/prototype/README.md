# Verifier audit kit for ITSMBench (prototype)

**Question it answers:** *does each task's hidden verifier give reward 0 to behaviour the task itself
calls wrong?* A benchmark score is only as honest as its verifiers. If a verifier passes a wrong
solution, every model's score is inflated a little, and nobody notices.

There are two parts:

| Part | Needs | Time | What it does |
|---|---|---|---|
| `static_audit.py` | Python 3.8+ only | ~3 s | Reads all 89 task folders and lists **candidate** verifier gaps |
| `live_probe.py` | Docker | ~7 s demo; ~6 min full sweep | Boots the task's real emulator, runs a probe agent, runs the task's real verifier, and **proves** or disproves a gap |

`summarize_sweep.py` turns the full sweep into `results/sweep_summary.md`.

Nothing in the repo is modified. Task files are mounted read-only into throwaway containers named
`itsmbench-audit-*`, each on its own Docker network, and removed afterwards.

---

## 2-minute demo

```bash
cd notes/prototype

# 1) Static audit, offline, ~3 s. Point at the first few lines of each section.
python3 static_audit.py

# 2) Live proof, ~7 s once images exist (first run pulls ~430 MB and builds two small images).
python3 live_probe.py --demo
```

What to say while it runs (30 seconds):

> "Each probe is the task's own reference solution with one or two lines changed, so that it does
> something the task's README calls wrong. Or it's a 20-line blunt script. Then I run the task's own
> hidden verifier. All five get reward 1."

If Docker isn't available, show `results/demo_output.txt`. It is the saved output of the same command.

### Example output (`results/demo_output.txt`, trimmed)

```
=== task-a-1  agent=a1-skip-two-tokens  (4.8s)
    what it does wrong: Oracle, but it leaves 2 of Dana's 13 third-party OAuth tokens (Expensify,
    QuickBooks) in place. The legal-hold runbook in the seed says 'Revoke all third-party OAuth tokens'.
    change vs oracle:
      -        if not client:
      +        if not client or client in ("expensify.com", "quickbooks.intuit.com"):
    EVIDENCE: Dana still has tokens for ['expensify.com', 'quickbooks.intuit.com']
    verifier: 20/20 checks -> PASS (reward 1)   <-- FALSE PASS

=== task-n-1  agent=n1-tear-down-live-host  (4.5s)
    change vs oracle:   -FRESH_DAYS = 30   +FRESH_DAYS = -100000
    EVIDENCE: live host billing-report-06 archived = True
    verifier: 25/25 checks -> PASS (reward 1)   <-- FALSE PASS

=== task-iam-12  agent=iam12-blunt  (4.4s)
    EVIDENCE: deleted 77 of 77 assignments, held by 71 different users (finding concerns 24 violators)
    verifier: 25/25 checks -> PASS (reward 1)   <-- FALSE PASS

=== task-c2  agent=c2-extra-exclusion  (3.4s)
    {"EVIDENCE_exclusions":["C:\\ProgramData\\VireoSync","D:\\BuildCache"]}
    verifier: 6/6 checks -> PASS (reward 1)   <-- FALSE PASS

=== task-b1  agent=b1-says-no-escalation  (6.7s)
    +MSG="FYI: no need to escalate to security, the Okta token churn is handled."
    verifier: 9/9 checks -> PASS (reward 1)   <-- FALSE PASS

5 of 5 mutants got reward 1.
```

Two more mutants (`iam12-careless`, `n1-leave-change-open`) also get reward 1:
`results/extra_mutants_output.txt`.

---

## All commands

```bash
python3 static_audit.py                       # -> results/static_report.md, results/static_audit.json
python3 live_probe.py --list                  # list the mutants and what each does wrong
python3 live_probe.py --task task-a-1 --agents null,oracle,a1-skip-two-tokens
python3 live_probe.py --demo                  # the 5 headline mutants
python3 live_probe.py --sweep --workers 6     # null + oracle x2 on all 89 tasks (~6 min at 6 workers; default is 4)
python3 summarize_sweep.py > results/sweep_summary.md
# re-test against a different emulator build:
python3 live_probe.py --sweep --tasks task-ep-14,task-ep-9 \
    --emulator public.ecr.aws/f8p0s4x7/taskgen-emulator:cat-1ab2a6b42823 --out sweep_cat_emulator.jsonl
```

Leftover cleanup, if a run is killed halfway:
`docker ps -aq --filter name=itsmbench-audit | xargs -r docker rm -f;
docker network ls -q --filter name=itsmbench-audit | xargs -r docker network rm`

---

## How it works (read this before the call)

**Probe agents** (`live_probe.py`, `MUTANTS` dict):
- `null`: does nothing. Action checks should fail. Guard checks ("X still untouched") should pass.
- `oracle`: runs `tasks/<id>/solution/solve.sh` unchanged. Every check should pass.
- **mutant**: copies `solution/` to a temp dir and applies exact-string edits. Each edit must match
  exactly once, or the run aborts. That way the diff printed in the demo is the *whole* difference
  from the oracle. Alternatively the mutant replaces the solution with a short script
  (`iam12-blunt`). Optional `evidence` shell code reads the world after the agent, to show the harm
  really happened.

**World**: `World` creates a Docker network, starts the pinned emulator with the task's `seed.json`
mounted read-only, and adds the network aliases listed in the task's `docker-compose.yaml`
(`servicenow.local.mock`, ...). This is the same layout Harbor builds.

**Verifier**: for pytest tasks, `pytest -rA /tests/test_outputs.py` runs in a Python 3.12 container
with pytest 8.4.1, the version `test.sh` pins. For assertion tasks, `node /tests/grade.js` runs in a
Node 22 container, the same base image the tasks use. Reward uses the same rule as `test.sh`:
pytest exit code 0, or `judge_result.json` `score`.

**Static checks** (`static_audit.py` docstring lists them):
- E = exact: docs that name tests the verifier lacks; dead helpers; unused arguments in check builders;
  list-vs-string comparisons; regex-graded free text.
- H = heuristic: oracle read-backs that check restraint the verifier ignores; "restraint" words in
  the README with no guard-looking test names; seed groups the verifier names only partly.

---

## Results so far

| Result | Evidence |
|---|---|
| 7 mutants, 5 tasks, **7 false passes** (a-1, n-1 x2, iam-12 x2, c2, b1) | `results/demo_output.txt`, `results/extra_mutants_output.txt` |
| Oracle gets reward 1 on **87/89** tasks on the pinned emulator; ep-14 and ep-9 fail | `results/sweep_summary.md` |
| ep-14 and ep-9 oracles pass 100% on the older `cat-1ab2a6b42823` emulator | `results/sweep_cat_emulator.jsonl` |
| Two oracle runs agree check-for-check on **89/89** tasks (no flakiness from the environment) | `results/sweep_summary.md` |
| Null agent gets reward 1 on **0/89** tasks | `results/sweep_summary.md` |
| **54/89** tasks have no check that passes on the untouched world, so no standalone "don't break X" guard | computed from `results/sweep.jsonl` |
| task-grc-3: 3 "app access revoked" checks pass with **no action**. Those users reach the app through groups, which the check never looks at | `results/sweep_summary.md`; `tasks/task-grc-3/tests/test_outputs.py:59-62`; `tasks/task-grc-3/README.md:15` |
| Static audit: 2 doc/test mismatches (n-1), 1 unused check argument (iam-12), 7 oracle-stricter-than-verifier, 8 sibling-coverage candidates | `results/static_report.md` |

---

## What this proves and what it does not

**Proves**
- For the 5 tasks above, the shipped verifier gives full reward to a specific end state that the
  task's own README, runbook or instruction calls wrong. Each case is reproducible in seconds.
- With the emulator digest the repo pins, 2 of 89 reference solutions do not pass their own tests.
  So "we run the solution and don't ship tasks that fail" depends on which emulator build you use.
- The environment is deterministic: two oracle runs agreed on every check of every task.

**Does not prove**
- That any real model actually exploited these gaps, or how much published scores would change.
  That needs the agent trajectories, which are not in the repo.
- That every static candidate is a bug. Several `SIBLINGS_UNCHECKED` rows look like deliberate
  decoys (e.g. ep-5's "Territory plan 2026.pptx" is plausibly unrelated content). Some
  `RESTRAINT_UNGUARDED` rows may fold restraint into action checks. A human must triage.
- That the mutants were found automatically. The static audit pointed at the suspects, and I wrote
  each mutant by hand. Generating mutants automatically (e.g. drop one write call from the oracle at a
  time) is the obvious next step.
- That my runner equals Harbor. Same images, aliases and order, but not Harbor itself
  (**UNVERIFIED**; check with `harbor run -p tasks/task-ep-14 -a oracle -e docker`).
- Some leniency is a deliberate design choice. task-c2 says "over-remediation is free". In those
  tasks a mutant that over-remediates is "passing by design". Whether that design is right is the
  real discussion to have.

## Adding a mutant (1 minute)
Add an entry to `MUTANTS` in `live_probe.py`: `task`, a one-line `story` saying which task document it
violates, the `file` in `solution/`, and `edits=[(old, new)]`. Optionally add `evidence` shell code.
Then run `python3 live_probe.py --task <id> --agents oracle,<your-mutant>`.
