# Task 3: one original idea, with a working prototype

Short version: **build a verifier audit kit that every new task must pass before it ships.** It
combines a static linter that finds suspects in seconds with "probe agents" that prove a false pass
on the real environment. Prototype: `notes/prototype/` (README there has the 2-minute demo).

---

## Candidate ideas

Effort assumes one engineer who knows Python and Docker.

### Idea 1: Probe agents ("mutation testing for verifiers")
- **Problem, with evidence.** Verifiers in this repo pass end states that the task's own documents
  call wrong. I proved 7 cases on 5 tasks by running the real emulator and verifier:
  - `task-a-1`: 2 of 13 OAuth tokens left live. The runbook says "Revoke all".
  - `task-n-1`: a live host torn down, and the change left open.
  - `task-iam-12`: all 77 permission assignments deleted.
  - `task-c2`: the payload exclusion kept.
  - `task-b1`: a message saying "no need to escalate" counts as an escalation.

  (`notes/prototype/results/demo_output.txt`, `extra_mutants_output.txt`.)
- **Why it matters for vertical AI companies.** A company building its own benchmark writes verifiers
  quickly and checks them by running one good solution. That only shows the verifier *can* pass. It
  never shows the verifier *fails* when it should. Probe agents test the second property. A false
  pass inflates scores quietly, and in IT, finance or healthcare the missed step is often the one
  that matters (a live token, a deleted record).
- **Effort.** Small to medium. The harness exists (~400 lines). Each mutant is 1-3 line edits of the
  oracle. Auto-generating mutants (drop one write call at a time, or flip the oracle's guard
  conditions) is about 1-2 weeks.
- **What would make it fail.** Hand-written mutants do not scale to hundreds of tasks. If authors
  must write them, they will write easy ones. Some leniency is intended ("over-remediation is free",
  `tasks/task-c2/task_construction.json:21`), so a probe can flag behaviour the designer accepts.
  Then you need a policy decision, not a fix.

### Idea 2: Spec-to-verifier consistency linter
- **Problem, with evidence.**
  - `tasks/task-n-1/fairness.md:52` lists a scored `test_change_closed`, and L53 protects the live
    host only with an "unscored guard" in `test_controls`. The shipped `tests/test_outputs.py` has
    neither, though it still defines `_change_state()` (L76) and `CHG_SYS` (L14), which are never
    used. Even as designed, breaking the live host would not have cost reward.
  - `tasks/task-iam-12/tests/test_outputs.py:112-114` takes `keep` and never asserts it.
  - In 7 tasks the oracle's own read-back checks restraint the verifier does not. One example:
    `task-iam-12/solution/solution.py:215-225` checks "primary preserved", "still active", and that
    a compensating-control exception "keeps both halves".
- **Why it matters.** Task docs, oracle and verifier drift apart as authors iterate. A vertical
  company's domain expert usually writes the docs and an engineer writes the tests, so drift is
  normal. A linter in CI catches it for free.
- **Effort.** Small. `static_audit.py` already has the exact checks. Improving the heuristics (e.g.
  an LLM pass that maps each README requirement to a test) is ~1 week.
- **What would make it fail.** Heuristic noise. My sibling check gave 35 candidates before tuning
  and 8 after, and some of the 8 are deliberate decoys. If the linter cries wolf, authors ignore it.

### Idea 3: Environment-drift CI (task health on every image change)
- **Problem, with evidence.** On the emulator digest the repo pins, `task-ep-14`'s oracle crashes
  ("Invalid value for choice field discovery_source: Device42") and `task-ep-9`'s oracle aborts.
  Both pass 100% on the older `cat-1ab2a6b42823` emulator, which
  `scripts/build_dind_snapshot.py:55-56` also pulls (`notes/prototype/results/`). There are 16
  divergent copies of `grade.js`. The published claim is "if it doesn't pass every check, we don't
  ship the task" (https://www.atomicwork.com/itsm-bench).
- **Why it matters.** Mock environments are software, and they change. A vertical benchmark is only
  comparable over time if every result records the exact environment build and every build is
  re-validated.
- **Effort.** Small. The sweep (`live_probe.py --sweep`) already does null + oracle ×2 for 89 tasks
  in about 6 minutes. Wiring it into CI is a day.
- **What would make it fail.** It only catches tasks with an oracle. It says nothing about agent
  paths the oracle never takes.

### Idea 4: Contamination-resistant task regeneration
- **Problem, with evidence.** Everything is public: tasks, verifiers and solutions ("we're
  open-sourcing all of it", https://www.atomicwork.com/itsm-bench). Agents run with
  `network_mode = "public"` on all 89 tasks (`tasks/*/task.toml`). So a run can in principle fetch
  `github.com/new-measure/ITSMBench/.../solution.py`. It already has the ticket number and names to
  search for (e.g. `INC0012345`, `dana.whitfield@northwind.example`). Future training data will also
  contain the tasks. On the other hand, `tasks/task-net-1/tests/cast.py` already generates IDs from
  a hash of a key (`hid()`, L15-16), so the seeds are partly parametric.
- **Why it matters.** A vertical company wants a benchmark that stays meaningful for years.
  Comparison: FrontierCode keeps tasks private "to avoid contamination"
  (https://cognition.com/blog/frontier-code), and AutomationBench posts scores "based on the private
  dataset" (https://arxiv.org/html/2604.18934v1).
- **Effort.** Medium to large. Re-skinning names, IDs and dates per run is easy where seeds are
  generated, but many seeds are hand-written JSON. Also turn on `no-network` or an allowlist for the
  agent phase (Harbor supports `allowlist`).
- **What would make it fail.** Re-skinning changes surface strings, not the reasoning pattern, so it
  does not stop training-time memorisation of "the trick". Some tasks may legitimately need the
  internet.

### Idea 5: Failure taxonomy + multi-model difficulty calibration
- **Problem, with evidence.** Failure analysis is prose written from single runs. Examples:
  `tasks/task-n-1/README.md:22` says "Current runs usually complete this task correctly", and 16
  READMEs each report one gpt-5.6-sol run. Taskgen tasks were tuned until one target model failed
  (`task-c2/task_construction.json:22`: "<=50% target"). Tuning against the model you evaluate
  biases the benchmark against that model.
- **Why it matters.** Customers want to know *why* an agent fails (investigation, restraint,
  bookkeeping) and want difficulty that is not tied to one vendor.
- **Effort.** Medium. Per-check results already exist (`judge_result.json`, `ctrf.json`). Tag each
  check by type (action / guard / escalation), aggregate across models, then fit a simple IRT model
  (item response theory: estimate each task's difficulty and each model's ability together).
- **What would make it fail.** It needs many trajectories from several models, which are not in this
  repo. Without them it is speculation.

---

## Recommendation: Ideas 1 + 2 as one tool, the "verifier audit kit"

Why this one:
1. **The strongest evidence.** I could not just *argue* it. I *ran* it and got 7 reproducible false
   passes, 2 broken oracles, and 1 vacuous check family, all on the real tasks.
2. **It needs no model calls.** It runs in seconds, costs nothing per run, and is deterministic, so it
   can block a merge in CI.
3. **It generalises.** Any Harbor-style task with an oracle can use it, and that includes every
   benchmark Ressl or New Measure would build for a customer. The static half finds suspects. The
   live half turns a suspect into a demo the author cannot argue with.
4. **It changes the conversation with the task author.** Instead of "this verifier might be weak"
   you hand them a 2-line diff and the reward it earned.

Idea 3 comes almost free with it (`--sweep`).

## Prototype status
- `notes/prototype/static_audit.py`: 9 checks over all 89 tasks, ~3 s, stdlib only.
- `notes/prototype/live_probe.py`: null / oracle / 7 mutants, plus a full sweep with an emulator
  override.
- `notes/prototype/summarize_sweep.py`: health table.
- Results in `notes/prototype/results/`.

## Honest limits (what the prototype proves and doesn't)
See `notes/prototype/README.md`, "What this proves and what it does not". The short version:
- It proves these verifiers accept specific wrong end states. It does not prove any model exploited
  them, or by how much scores move.
- The mutants were hand-written after the static audit pointed at suspects. Generating them
  automatically is the next step.
- My runner reproduces Harbor's layout but is not Harbor (**UNVERIFIED** equivalence).
- Some flagged leniency is intentional design. Those cases need a decision, not a patch.

## What I'd build next (if asked "what would you do in week 1?")
1. Auto-mutants: for each oracle, drop one state-changing HTTP call at a time and re-run the
   verifier. Any variant that still gets reward 1 marks a write the verifier never checks. This
   directly measures verifier coverage.
2. "Blunt policy" library: generic over-remediators (delete all tokens, deprovision all listed users,
   post one keyword-stuffed message), run against every task.
3. A CI gate: oracle reward 1 on the pinned emulator, null reward 0, no auto-mutant gets reward 1
   unless it is allow-listed with a written reason.
