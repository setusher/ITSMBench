# Interview prep: 20 tough questions

Format: **Q**, then an answer outline grounded in the repo or your runs, then the likely
**follow-up**. 📚 marks questions you can't answer well without studying something specific. The
reading list is at the bottom. I have not fetched those references myself, so search the exact title.

---

## (a) About the ITSMBench repo

### 1. Walk me through how one task becomes a score.
- `harbor run` reads `configs/gpt.yaml`. Each trial is one task × agent config × attempt.
- Harbor brings up `environment/docker-compose.yaml`: `main` (the agent) and `mock-api` (the
  emulator, loaded from `seed.json`).
- It installs the agent CLI (pi or codex) and gives it `instruction.md`. The agent uses curl against
  `*.local.mock:8080`.
- When the agent finishes or times out, Harbor uploads `tests/` and runs `test.sh`. That runs pytest,
  or `grade.js` over `assertions.json`, reading the final state over the same APIs.
- `reward.txt` gets 1 only if every check passed (`tasks/task-a-1/tests/test.sh:10-14`). Harbor
  averages rewards over all trials.
- **Follow-up:** "Where is the agent prevented from seeing the tests?" Harbor copies `tests/` in only
  after the agent phase (Harbor docs `/tasks/verifier`). The test files are not in the agent image:
  Docker builds only `environment/`.

### 2. Why two verifier styles, and which is better?
- pytest (73 tasks, abhishek203) is flexible. It can compute things like effective permissions, as in
  `tasks/task-iam-12/tests/test_outputs.py:55-106`.
- Declarative `assertions.json` (16 tasks, taskgen) is auditable and diff-able. But `grade.js` is
  copied 16 times with differences, and its loose `String()` comparison caused the task-c2 false
  pass (`grade.js:119-126`).
- My view: declarative for most checks, plus a small typed library of shared check functions. Never
  copy-paste the grader.
- **Follow-up:** "What would you add to the assertion language?" List-aware operators
  (`list_contains`, `list_not_contains`), negated free-text checks, and an `unchanged_since_seed`
  guard type.

### 3. How does ITSMBench handle nondeterminism?
- Environment side: emulator pinned by digest (`README.md:76`), frozen clock `_now` in 86/89 seeds,
  fixed seeds. My sweep: two oracle runs per task disagreed on 0 of 89 tasks
  (`notes/prototype/results/sweep_summary.md`).
- Model side: `n_attempts: 5` (`configs/gpt.yaml:6`). Harbor retries only on exceptions, never on
  reward 0 (Harbor `trial/queue.py`).
- Infra side: `environments/reliable_daytona.py` restarts dockerd once. The snapshot avoids registry
  rate limits.
- **Follow-up:** "Any flakiness left?" Yes, possibly. 72 `test.sh` files download uv from the internet
  during grading. If that fails, the reward is 0 and looks like a model failure (UNVERIFIED in
  practice).

### 4. Agents have internet access. Is that a problem?
- All 89 tasks use `network_mode = "public"`. Tasks, tests and solutions are public. Ticket numbers and
  names are unique strings (e.g. `INC0012345` in `tasks/task-a-1/instruction.md:3`). So a test-time
  leak path exists, and future training data will include the repo.
- I have no evidence any run used it. Say that clearly.
- Fix: Harbor supports `no-network` and `allowlist`. Set it for the agent phase, add a canary string,
  and keep a private split, as FrontierCode and AutomationBench do.
- **Follow-up:** "Doesn't the agent need internet to install itself?" Harbor installs the agent CLI.
  The b/c images even bake in `pi` (`tasks/task-b1/environment/Dockerfile:5`). Network policy can
  differ per phase (Harbor docs `/tasks/network-policies`), but check how installation interacts
  with it.

### 5. The README says you measure "agent-plus-harness". Why does that matter?
- `README.md:141`. The config runs the same model under `pi` and `codex` (`configs/gpt.yaml:15-117`).
  Atomicwork reports that switching harnesses moved Opus by seven points.
- So a leaderboard row is a system, not a model. To compare models, fix the harness. To compare
  harnesses, fix the model.
- **Follow-up:** "The b-series images bake in pi 0.80.2 vs 0.80.6. Does that matter?" Possibly. The
  harness version becomes a hidden variable. Which pi Harbor actually runs is UNVERIFIED.

---

## (b) About your writeup

### 6. Maybe lenient grading was intended. Why call it a flaw?
- Separate design choice from bug. task-c2 says "over-remediation is free"
  (`task_construction.json:21`). That is a choice. I would debate it, but it isn't a bug.
- task-a-1, task-n-1 and task-iam-12 are different. Their own README, runbook or oracle says the
  behaviour is wrong:
  - the runbook says "Revoke all third-party OAuth tokens";
  - `tasks/task-n-1/README.md:7` says "It must not be changed";
  - the iam-12 oracle checks "still active" and "primary preserved" itself
    (`solution/solution.py:215-225`).

  There the verifier disagrees with the task.
- **Follow-up:** "Where's the line?" If the task text gives a requirement, it needs a check, or the
  requirement should be deleted from the text.

### 7. You criticise calibrating against GPT. How would you set difficulty?
- Calibrate against a pool of models from several vendors, or against models you will not rank.
- Report difficulty per task using IRT (item response theory: fit each task's difficulty and each
  model's ability together).
- Keep calibration runs separate from leaderboard runs. Evidence of the current practice:
  `task-c2/task_construction.json:22` ("<=50% target", one gpt-5.6-sol trial). 14 of 16 taskgen
  READMEs report a single FAIL for that model.
- **Follow-up:** "Doesn't every benchmark filter for hard tasks?" Yes. The issue is *which* model you
  filter against. Filtering against the model you evaluate pushes its score down relative to others.
  📚

### 8. Why compare ITSMBench with FrontierCode and AutomationBench? Different domains.
- They answer the same design questions differently:
  - How to verify: state assertions (ITSM, AB) vs tests plus rubrics plus blockers (FC).
  - Public or private: public (ITSM) vs private (FC; AB's leaderboard).
  - Partial credit: binary (all three, at the reward level).
  - Over-remediation: negative assertions (AB) vs often none (ITSM).
- AB is the closest cousin: REST APIs, a world state, deterministic assertions.
- **Follow-up:** "Who made FrontierCode?" Cognition published it, and Zapier published AutomationBench.
  Neither page names an outside builder. If your team built them, I'd love to hear how the verifiers
  were validated. (UNVERIFIED either way: ask rather than assert.)

### 9. You raise contamination with no evidence it happened. Isn't that speculation?
- It is a risk, stated as a risk. The cost to close it is small (network allowlist, canaries, a private
  split) and the cost of ignoring it grows every time a model is trained.
- Offer a test: grep trajectories for `github.com/new-measure`, or re-skin seed names and IDs (task-net-1
  already derives IDs from hashes, `tests/cast.py:15-16`) and see whether scores drop.
- **Follow-up:** "How would re-skinning detect memorisation?" If scores fall on renamed but logically
  identical tasks, the model was relying on surface memory. 📚 (contamination detection methods)

---

## (c) About your prototype

### 10. Your mutants were written by someone who already knew the bug. Isn't that circular?
- Partly, yes. Admit it. The static audit found the suspects first (doc/test mismatch, unused `keep`,
  sibling gap, list-vs-string). Then I wrote mutants to *prove* them.
- The finding itself is not circular. The shipped verifier gives reward 1 to an end state the task
  calls wrong.
- Next step: auto-mutants that drop one state-changing API call from the oracle at a time. Any variant
  that still gets reward 1 marks a write the verifier never checks. That measures verifier coverage
  without my judgment.
- **Follow-up:** "What about mutants that do *extra* harm?" A library of blunt policies, like
  `iam12-blunt`: delete all, deprovision all, keyword-stuffed messages.

### 11. How do you know your runner matches Harbor?
- Same emulator digest, same `seed.json`, same network aliases from each compose file, same test
  files, tests run after the agent, pytest 8.4.1 as `test.sh` pins.
- Differences: my Python client is 3.12-slim, not Ubuntu's python3. I skip `test.sh`'s uv download.
  I don't use Daytona.
- I didn't run Harbor itself. Confirm with `harbor run -p tasks/task-ep-14 -a oracle -e docker`.
- **Follow-up:** "Why not just use Harbor?" I should for the final check. My runner was faster to
  make probes with, since mutants are temp-dir copies of `solution/`.

### 12. Two oracles fail on the pinned emulator. Is the leaderboard wrong?
- Not necessarily. It depends which emulator the published runs used, which is UNVERIFIED. Both pass
  on the older `cat-1ab2a6b42823` build that `scripts/build_dind_snapshot.py:55-56` also pulls.
- For ep-14 the failure looks like an oracle bug, not a broken task. The emulator rejects
  `discovery_source: Device42`, but the test never requires that field, so an agent could likely
  still pass. (UNVERIFIED: I did not test creating the CI without that field.)
  For ep-9, the oracle aborts on a precondition check. Whether agents can pass is unknown.
- The real lesson: re-validate oracles on every environment change, and record the emulator digest
  with every result.
- **Follow-up:** "How would you prevent this?" A CI gate. The sweep runs in about 6 minutes.

### 13. A customer has 500 tasks and no oracles. Does your tool still work?
- The null agent and blunt policies need no oracle. They already catch vacuous checks (grc-3) and
  missing guards (54/89 tasks have no check that passes at baseline).
- Mutants need an oracle. Many vertical teams can write one quickly with an LLM's help, and the null
  and oracle checks then validate that oracle too.
- **Follow-up:** "What if the oracle is wrong?" Then it fails, or a guard catches it. That is why
  you need both directions (null → 0, oracle → 1).

### 14. What's the false-positive rate of your static audit?
- Exact checks: zero false positives in what I saw. The doc/test mismatch and unused argument are
  facts.
- Heuristics are noisy. The sibling check flagged 35 before tuning and 8 after. 1 is confirmed by a
  live run (task-a-1), and several look like deliberate decoys (e.g. ep-5). The restraint-words check
  flags 45 tasks.
- So I lead with the exact measure: 54/89 tasks have no check passing on the untouched world
  (`results/sweep.jsonl`).
- **Follow-up:** "How would you lower it?" Let each flag be confirmed or dismissed with a reason, and
  run a live probe automatically for every flag.

---

## (d) Benchmark design in general

### 15. Is model A (46.07%) really better than model B (45.39%)? 📚
- Probably can't tell. Treat tasks as a sample. With 89 tasks and per-task success rates that vary a
  lot, the task-level standard error is roughly 3-4 points, so a 95% interval of about ±6-8 points.
  This is my rough estimate, assuming a per-task standard deviation of 0.3-0.4.
- The page shows ±1.99. If that were a 95% binomial interval it would imply about 2,400 independent
  trials. If one standard error, about 630. Both treat repeated trials of the same task as
  independent, which understates uncertainty. What the ± really is: UNVERIFIED, so ask.
- The better method is a paired comparison on the same tasks: per-task difference, then bootstrap over
  tasks, or clustered standard errors.
- **Follow-up:** "What is a clustered standard error?" It accounts for attempts on the same task being
  correlated. Cluster by task.

### 16. Binary or partial credit?
- Binary matches the business ("Businesses do not want partially completed workflows",
  AutomationBench). ITSM uses binary for `reward.txt` but saves `partial_credit` in
  `judge_result.json` (`grade.js:206`).
- Partial credit gives more signal per trial and helps compare weak models. It can be gamed by doing
  the easy checks.
- Answer: report both. Rank on binary and diagnose with partial.
- **Follow-up:** "Should checks be weighted?" Yes, if some are critical. A live leaked token matters
  more than a missing ticket note.

### 17. pass@k vs pass^k: which matters for an IT agent? 📚
- pass@k is the chance that at least one of k tries works. It suits "a human picks the best attempt".
  Harbor computes it from n attempts with c successes (`utils/pass_at_k.py`).
- pass^k (from tau-bench) is the chance that *all* k tries work. It measures reliability, which is
  what an enterprise running the agent unattended needs.
- With `n_attempts: 5` you can estimate both.
- **Follow-up:** "Compute pass^k from data?" Per task, C(c,k)/C(n,k), then average.

### 18. How do you validate a verifier?
- Oracle → 1. Null → 0. Wrong-behaviour mutants → 0. Blunt policies → 0.
- Then sample real agent trajectories and have a human label them, which measures false pass and false
  fail rates.
- FrontierCode v1.1 did a manual audit and demoted 75 over-strict blockers, i.e. fixed false fails.
  task-c2's notes describe fixing one too (`intent:uninstall` "unfairly failed").
- **Follow-up:** "Which error is worse?" For ranking, false passes inflate weaker agents. For a buyer,
  a false pass hides a dangerous miss. False fails mostly hurt the best agents.

### 19. How much does it cost to run, and how would you cut it? 📚
- `configs/gpt.yaml` = 89 × 20 × 5 = 8,900 trials. The leaderboard's "Avg cost" column shows $1.75 for
  the top row, unit unstated. Agent timeouts go up to 5,400 s per task.
- Cuts:
  - Fewer reasoning levels per sweep.
  - Adaptive sampling: stop adding attempts when the CI is tight.
  - Drop tasks that every model passes or every model fails (they add cost, not ranking signal).
  - Use an IRT-selected subset for quick checks.
- **Follow-up:** "What do you lose with a subset?" Coverage of rare failure types. Keep the full set
  for releases.

### 20. How would you help a vertical company build its benchmark quickly?
- Template per task: seed, instruction, oracle, verifier, README. Turn every requirement sentence in
  the README into a check, including guards for every "do not".
- Gate every task with the audit kit: oracle 1, null 0, auto-mutants 0, run on the pinned
  environment.
- Calibrate on several models, keep a private split, and record environment digests with results.
- **Follow-up:** "What's the slowest part?" Domain experts writing realistic seeds and decoys.
  Generators like task-net-1's `cast.py` help.

---

## Reading list (for the 📚 questions)
I have not fetched these. Search the exact titles.
1. Evan Miller, *"Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations"*
   (arXiv 2024). Clustered SEs and paired comparisons (Q15, Q19).
2. Yao et al., *"τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains"* (arXiv
   2024). The pass^k metric and state-based grading (Q17).
3. Chen et al., *"Evaluating Large Language Models Trained on Code"* (Codex paper, 2021). The unbiased
   pass@k estimator (Q17).
4. Zhu et al., *"Establishing Best Practices for Building Rigorous Agentic Benchmarks"* (2025). Task
   validity and outcome validity checklist (Q18).
5. OpenAI, *"Introducing SWE-bench Verified"* (2024 blog). Humans re-validating tasks and tests
   (Q18).
6. Polo et al., *"tinyBenchmarks: evaluating LLMs with fewer examples"* (2024). IRT for picking subsets
   (Q7, Q19).
7. Krakovna et al., *"Specification gaming: the flip side of AI ingenuity"* (DeepMind blog, 2020).
   Reward hacking examples (Q6, Q10).
8. Mutation testing, any intro (e.g. the Wikipedia article). The idea behind your prototype (Q10).
9. Harbor docs: `/tasks/verifier`, `/jobs/configs`, `/datasets/metrics`, `/tasks/network-policies` at
   https://docs.harborframework.com (Q1, Q3, Q4).
