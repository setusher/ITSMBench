# ITSMBench explained (prep notes for Shradha)

All paths are relative to the repo root. "Harbor docs" means
https://docs.harborframework.com and "Harbor source" means
https://github.com/harbor-framework/harbor at commit `c803185a` (the README links
`laude-institute/harbor`, which now redirects there). Anything I could not confirm is marked
**UNVERIFIED** with a way to check it.

---

## 0. Three things to know before the call

1. **Who built what (UNVERIFIED, ask on the call).**
   - FrontierCode is *published* by Cognition (https://cognition.com/blog/frontier-code), and
     AutomationBench is *published* by Zapier (https://arxiv.org/abs/2604.18934). Neither page names
     an outside builder, as far as I or the research agent could find.
   - That does not mean Ressl didn't build them. New Measure offers "custom evals and benchmarks as
     a service to application AI companies" (https://newmeasure.ai/about). ITSMBench itself is
     presented on its client's site (https://www.atomicwork.com/itsm-bench). So your briefing (Ressl
     builds these for vertical companies) is consistent with the evidence.
   - New Measure is an "independent eval lab, founded by Arushi Gandhi and Abhishek E"
     (https://newmeasure.ai/about). YC lists the same two people as Ressl AI's co-founders
     (https://www.ycombinator.com/companies/ressl-ai).
   - Safe phrasing: "FrontierCode, published by Cognition" and "AutomationBench, published by
     Zapier". Ask: "Which of these did your team build, and is New Measure part of Ressl?"
2. **The repo URL moved.** Your prompt says `github.com/resslai-bm/itbench`. This clone's remote is
   `https://github.com/new-measure/ITSMBench` (`git remote -v`). The old URL returns HTTP 301 to the
   new one. Commit `c83bb73` is a merge from `resslai-bm/itbench`, and `1658d32` renamed ITBench to
   ITSMBench.
3. **This repo is only the task data.** It contains no runner, scorer, or leaderboard code. Everything that
   runs agents, collects rewards, and averages them lives in Harbor. So "how are results produced?"
   is mostly a Harbor question (section 4).

---

## 1. What the benchmark measures, end to end

**Claim.** "ITSMBench measures how well AI agents handle real IT service-management work"
(`README.md:7-8`). Each task "drops an agent into a containerized enterprise environment with a
ticket-style instruction and a hidden verifier ... and is scored on whether the environment matches
the expected outcome" (`README.md:8-12`).

**What that means concretely.** It is a stateful, tool-use benchmark. The agent is an IT admin. It
gets a ticket in plain English. It must investigate several mock SaaS systems (ServiceNow, Okta,
Google Workspace, Slack, Intune, Device42, and others), decide what is really going on, change the
right records, and avoid changing the wrong ones. Nobody grades its explanation. Only the final state
of the systems is graded.

The task format, step by step:

| Piece | What it is in this repo | Where |
|---|---|---|
| Task definition | One folder per task: `task.toml` (config), `instruction.md` (the ticket), `README.md` (author notes, not shown to the agent) | `tasks/<id>/` |
| Environment | Two containers from `docker-compose.yaml`. **main** is where the agent runs: Ubuntu or Node with curl, jq, python3. **mock-api** is one emulator image serving every mock SaaS API, loaded from `seed.json` | `tasks/<id>/environment/` |
| Agent interface | A shell in `main`. The agent calls HTTP APIs with curl. It discovers endpoints with a search service: `curl 'http://search.local.mock:8080/search?q=<terms>&limit=10'` | `tasks/task-a-1/instruction.md:13-17` |
| Hidden verifier | `tests/` folder. Harbor copies it into the container only **after** the agent finishes ("Harbor uploads `tests/` to `/tests/` after the agent runs", Harbor docs `/tasks/verifier`). It reads the final state over the same mock APIs | `tasks/<id>/tests/` |
| Scoring | The verifier writes `1` or `0` to `/logs/verifier/reward.txt`. Every check must pass to get 1 | `tasks/task-a-1/tests/test.sh:10-14` |
| Reference solution ("oracle") | `solution/solve.sh`, used to prove the task is solvable | `tasks/<id>/solution/` |

What it does **not** measure (the README says so): real enterprise systems ("Tasks use synthetic mock
APIs", `README.md:137`), change/problem/asset/capacity management (`README.md:139`), or a model
alone ("The benchmark measures the agent-plus-harness combination", `README.md:141`).

---

## 2. Repo map

```
ITSMBench/
├── README.md                      how to run; limitations (L135-141)
├── LICENSE                        MIT
├── configs/gpt.yaml               the only full-run config: 89 tasks x 20 agent configs x 5 attempts
├── environments/reliable_daytona.py   patch to Harbor's Daytona backend (dockerd start + retries)
├── scripts/build_dind_snapshot.py     builds a Daytona snapshot with all images pre-loaded
├── docs/assets/itsmbench.png      hero image
└── tasks/                         89 task folders
    └── task-a-1/
        ├── task.toml              timeouts, image, resources, network mode
        ├── instruction.md         the ONLY thing the agent is told
        ├── README.md              author notes: expected steps, common failures (88 of 89 have one)
        ├── environment/
        │   ├── Dockerfile         the agent's container (5 distinct Dockerfiles across all tasks)
        │   ├── docker-compose.yaml  main + mock-api; sets EMULATOR_TOOLS and host aliases
        │   └── seed.json          the whole fake company: users, tickets, logs, KB articles ...
        ├── solution/
        │   ├── solve.sh           oracle entry point
        │   └── solution.py        oracle logic (73 tasks); 16 tasks use bash+curl in solve.sh
        └── tests/                 HIDDEN from the agent
            ├── test.sh            runs the checks, writes reward.txt
            └── test_outputs.py    pytest checks (73 tasks)  OR  grade.js + assertions.json (16 tasks)
```

What each top-level piece really does:

- **`configs/gpt.yaml`** sets `n_attempts: 5` (L6), `n_concurrent_trials: 240` (L7), and
  `retry.max_retries: 2` (L9-10). It lists 20 agent configs: two models (`gpt-5.6-sol`,
  `gpt-5.6-terra`) × two harnesses (`pi`, `codex`) × five reasoning levels (L15-117). It runs on
  Daytona (L119-123). One full run is 89 × 20 × 5 = 8,900 trials. The README says "Each file under
  `configs/` is a complete model run" (`README.md:101`), but only the GPT config is in the repo.
- **`environments/reliable_daytona.py`** subclasses Harbor's Daytona environment. It replaces the
  Docker daemon start command because Harbor's version "can hit a cgroup-v2 startup failure on some
  Daytona runners" (L34-36). It waits up to 180 s (L18), restarts dockerd once (L94-105), and loads
  pre-baked images from `/opt/harbor-images/images.tar.gz` (L60-71). This is infrastructure
  hardening against flaky starts, not scoring logic.
- **`scripts/build_dind_snapshot.py`** builds that snapshot. Its docstring explains why: pulling
  images in every sandbox "hits registry rate limits" (L4-5). It pins the emulator by digest (L53-54)
  and also pulls a second emulator tag, `taskgen-emulator:cat-1ab2a6b42823` (L55-56). That second
  image matters in section 4.5.

### The two authoring pipelines

The repo has two kinds of tasks. They line up exactly with the `[task].name` prefix in `task.toml`:

| | "abhishek203" tasks | "taskgen" tasks |
|---|---|---|
| Count | 73 (`a-*`, `alloc-*`, `ep-*`, `grc-*`, `iam-*`, `n-*`, `net-1`, `ops-*`) | 16 (`b1`-`b11`, `c1`-`c5`) |
| Verifier | `tests/test_outputs.py` (pytest), reward = pytest exit code | `tests/grade.js` + `tests/assertions.json` (declarative) |
| Agent image | Ubuntu 24.04 + curl, python3, jq (71 tasks) | Node 22 + curl, jq + the `pi` agent CLI baked in |
| README style | "What this task is / What we expect / What agents often miss" | a one-row results table + "Ideal solution" + "How GPT-5.6 performed" |
| Seeds | Small, task-specific (14 KB to 830 KB) | 15 of 16 share one ~4,160-record base world (~3 MB); each adds 45-144 records. Exception: c2 |

(Counts from my inventory of all 89 `task.toml`, `tests/` and `seed.json` files;
script: `notes/prototype/static_audit.py`.)

### How one task becomes a score

```
 configs/gpt.yaml  ──►  harbor run  (one "trial" = one task x one agent config x one attempt)
                              │
          ┌───────────────────┴──────────────────────┐
          ▼                                          ▼
  docker-compose up                        agent CLI (pi or codex) installed in "main"
  ┌──────────────┐   HTTP :8080   ┌───────────────────────────────┐
  │ main         │ ─────────────► │ mock-api (taskgen-emulator)    │
  │ agent shell  │ ◄───────────── │ servicenow.local.mock, okta... │
  │ instruction  │                │ state = seed.json, in memory   │
  └──────────────┘                └───────────────────────────────┘
          │  agent finishes (or hits [agent].timeout_sec)
          ▼
  Harbor copies tests/ to /tests  ──►  bash /tests/test.sh
          │                                 │ reads final state via the same APIs
          ▼                                 ▼
  /logs/verifier/reward.txt  (1 if every check passed, else 0)
          │
          ▼
  Harbor job result.json: mean reward over all trials (+ pass@k if rewards are 0/1)
```

---

## 3. How tasks are built

### 3.1 `task.toml`

Example: `tasks/task-a-1/task.toml`.

| Field | Value in task-a-1 | Meaning (Harbor docs `/tasks/configuration`) |
|---|---|---|
| `name` (L5) | `abhishek203/task-a-1` | id; the prefix reveals the authoring pipeline |
| `[verifier] timeout_sec` (L13) | 600 | max time for the checks |
| `[agent] timeout_sec` (L18) | 1500 | max agent time. Across tasks: 5400 s (70 tasks), 3600 s (16), 1500 s (3) |
| `docker_image` (L21) | `harbor.local/task-main:dfc6f4d357d9` | local tag of the built `Dockerfile` (tag = hash of the Dockerfile, `build_dind_snapshot.py:73-82`) |
| `network_mode` (L22) | `public` | **full internet access** for the agent. All 89 tasks use `public` |
| `cpus` / `memory_mb` / `storage_mb` (L26-28) | 1 / 2048 / 5120 | container limits |

`description` is empty in 71 of the 73 abhishek203 tasks. In the 16 taskgen tasks it is a long spoiler of
the whole scenario (e.g. `tasks/task-b1/task.toml:6`). Whether Harbor ever shows `description` to the
agent is **UNVERIFIED**. I did not find it in Harbor's agent prompt path. Check
`src/harbor/agents/` for any use of `task.description`.

### 3.2 The environment

- **One emulator for everything.** Every task's `docker-compose.yaml` runs the same image,
  `harbor.local/taskgen-emulator:a3dc8a1f0c35`. That is a local tag of
  `public.ecr.aws/f8p0s4x7/taskgen-emulator@sha256:a3dc8a1f...` (`README.md:76-77`). The image is
  a Node/Fastify server. I read its source inside the image: it serves every provider listed in
  `EMULATOR_TOOLS` and routes requests by the `Host` header (`/opt/emulator/server.js`, ~L355-379).
- **The world is `seed.json`.** The emulator loads it at startup (`MOCK_SEED_PATH`) and keeps state
  in memory. Every agent write changes that state, and the verifier reads it back.
- **Realism tricks.** 86 of 89 seeds set a frozen clock `_now`. The emulator stamps that time on
  every response "so the frozen seed clock is the only observable now" (`server.js` ~L343-351).
  Seeds also contain decoys and noise: a distractor KB article in task-a-1, benign recent changes
  in task-c2 (`task_construction.json:12`), and look-alike subnets in task-net-1.
- **How many systems.** Between 1 and 20 mock systems per task. All 16 taskgen tasks except c2 load
  20 providers (`tasks/task-b1/environment/docker-compose.yaml:10`).
- **Unused feature.** The emulator has a request budget (`/opt/emulator/request-budget.js`), but no
  task sets `maxAgentRequests` (I grepped every seed), so agents have unlimited API calls.

### 3.3 How "correct final state" is checked

**Family A: pytest (73 tasks).** `test_outputs.py` makes HTTP GETs to the mock APIs and asserts
on fields. Example from `tasks/task-a-1/tests/test_outputs.py`:
```python
def test_gw_account_suspended():                    # L51-52
    assert _gw_user().get("suspended") is True
def test_okta_status_remains_suspended():           # L105-106  (a "guard": do not undo this)
    assert str(_okta_user().get("status")) == "SUSPENDED"
```
`test.sh` installs `uv` from the internet (`curl ... astral.sh/uv/0.9.7/install.sh`), then runs
`pytest==8.4.1`. It writes `1` if pytest exits 0, else `0` (`tasks/task-a-1/tests/test.sh:4-14`).
72 of 89 `test.sh` files download uv at grading time.

**Family B: declarative assertions (16 tasks).** `assertions.json` lists checks such as:
```json
{"name": "orphaned-service-account-deprovisioned", "type": "field_equals", "app": "okta",
 "collection": "users", "match": {"profile.login": "svc-scim-sync@acme.com"},
 "field": "status", "value": "DEPROVISIONED"}
```
(`tasks/task-b1/tests/assertions.json:15-25`). `grade.js` fetches each collection, applies one of 7
check types (`grade.js:145-156`), and computes `partial = passed/total` and `binary = all passed`
(`grade.js:160-185`). It writes the binary value to `reward.txt` and both values to
`judge_result.json` (`grade.js:204-208`). The 16 `grade.js` files are 16 slightly different copies.

**Guards.** A good verifier checks two things: the agent did the right thing, and it did not do
wrong things. The second kind is called a guard (e.g. `test_guard_device42_untouched` in
`tasks/task-net-1/tests/test_outputs.py`). Some tasks have many guards (task-net-1 has 12 functions named `test_guard_*`; ep-2 has about 21
by my name heuristic). Others have none. Five of the taskgen tasks say so outright. One example: "No
format/bookkeeping checks, no untouched-data guards, no runbook" (`tasks/task-c2/tests/assertions.json:2`).

### 3.4 How tasks were authored (what the repo reveals)

- The taskgen tasks were **calibrated against the model being evaluated**. `task-c2`'s notes
  describe a single trial of `gpt-5.6-sol` (pi, xhigh) that scored binary 0, "in the skill's <=50%
  target", followed by a grader "FAIRNESS FIX", a confirmation trial, and "TUNING LEVERS if a future
  batch drifts" (`tasks/task-c2/task_construction.json:22`). All 16 taskgen READMEs report one
  `gpt-5.6-sol / xhigh / pi` run. 14 of 16 say FAIL, and 7 report exactly 7/14 assertions.
- Some abhishek203 tasks went through a written fairness audit: `tasks/task-n-1/fairness.md` checks
  that "a cold oracle reaches the whole scored set ... with zero hardcoded ids" (L5-6). It reports
  "26/26 scored + 15/15 controls" (L10-11). It counts the 15 controls separately from the 26 scored
  checks (L129-130, L140-144), and calls the live-host check an "unscored guard" (L53). The
  shipped `tests/test_outputs.py` has 25 checks: no `test_change_closed` (listed at L52) and no
  controls at all. So the live host the README says "must not be changed" is never checked, and
  even in the audit's own design that check would not have counted toward the reward.
- Atomicwork's page says "IT experts and the benchmark team wrote them together" and "Every task also
  ships with a solution we run ourselves, and if it doesn't pass every check, we don't ship the task"
  (https://www.atomicwork.com/itsm-bench).

---

## 4. How results are produced and reported

### 4.1 Per trial
- One trial gives a reward from `reward.txt`. Here it is always 0 or 1, all or nothing. Partial
  credit exists only in side files: `judge_result.json` (taskgen) and `ctrf.json`, the pytest
  report (abhishek203).
- Harbor accepts fractional rewards ("Single number, usually `1` or `0`", Harbor docs
  `/tasks/verifier`). ITSMBench chooses binary.

### 4.2 Aggregation (all Harbor, none in this repo)
- Default metric is the **mean** reward over all trials, all attempts pooled. Missing rewards count as
  0 (Harbor docs `/datasets/metrics`; Harbor source `src/harbor/metrics/base.py:25`).
- Harbor computes **pass@k** with the unbiased estimator, but only when every reward is exactly 0 or 1
  (`src/harbor/utils/pass_at_k.py:50-51, 87-94`). k takes the values 2, 4, 8, ... and 5, 10, ...
  up to the number of attempts. With 5 attempts you get pass@2, pass@4 and pass@5. pass@1 is just
  the mean.
- **Confidence intervals: Harbor computes none** (the research agent searched the Harbor source).
  Atomicwork's leaderboard shows "Pass@1" with a "±" (e.g. "claude-opus-5 [high] claude-code
  46.07% ±1.99"). What the ± is and how many trials sit behind it are **UNVERIFIED**. The HTML
  class is `itsmb-ci`, which suggests a confidence interval. Ask on the call.

### 4.3 Seeds, repeats, retries
- **Repeats:** `n_attempts: 5` (`configs/gpt.yaml:6`). No random seed exists to vary. The
  variation between attempts comes from the model's sampling.
- **Retries:** `max_retries: 2` (`configs/gpt.yaml:9-10`). Harbor retries **only on exceptions,
  never on a 0 reward**. The retry loop returns as soon as `result.exception_info is None`
  (the retry loop in `src/harbor/trial/queue.py`; I re-checked this myself). Agent and verifier timeouts
  are excluded from retry by default (Harbor `models/job/config.py:291-313`). One subtle case
  (research agent's reading of the source): if the agent CLI exits non-zero, the trial is still
  scored and then thrown away and re-run. That can bias results toward "lucky" reruns.
  **UNVERIFIED** in practice; check `JobStats.n_retries` in a real job's `result.json`.

### 4.4 Nondeterminism and flaky runs: what the design does
- **Deterministic world.** The emulator image is pinned by digest. Seeds are fixed files. The clock
  is frozen. I ran each task's oracle twice on fresh worlds: **0 of 89 tasks** gave different
  per-check results between the two runs (`notes/prototype/results/sweep_summary.md`). The remaining
  nondeterminism is the model's own.
- **Infra flakiness.** It is handled by `reliable_daytona.py` (dockerd retry) and the image snapshot
  (avoids registry rate limits).
- **Flakiness risk left in the verifier.** 72 `test.sh` files download uv from `astral.sh` at grading
  time. If that download fails, pytest never runs and the reward is 0, which looks like a model
  failure. Harbor excludes `RewardFileNotFoundError`-type errors from retry, so the 0 would stick.
  Whether this happens in practice is **UNVERIFIED**; count trials whose `ctrf.json` is missing.

### 4.5 What my live sweep found (prototype, section in `03_idea.md`)
I booted the real emulator for every task. On each I ran (a) a do-nothing agent and (b) the
task's own oracle, twice, then the task's own verifier:
- The do-nothing agent never gets reward 1 (0/89). Good.
- The oracle gets reward 1 on **87/89** tasks. The two failures are `task-ep-14` and `task-ep-9`.
  They fail on the pinned emulator digest. Both pass 100% on the older `cat-1ab2a6b42823` emulator
  that `build_dind_snapshot.py:55-56` also pulls (`notes/prototype/results/sweep_cat_emulator.jsonl`).
  Example error: the newer emulator rejects `discovery_source: Device42`, which the ep-14 oracle sends
  (`tasks/task-ep-14/solution/solution.py:237`). So the published claim "if it doesn't pass every
  check, we don't ship the task" holds on one emulator build but not on the one the repo pins.
  Which emulator the leaderboard runs used is **UNVERIFIED**.
- Caveat: I used my own runner (`notes/prototype/live_probe.py`), not Harbor. It mirrors Harbor's
  layout: same images, same aliases, tests run after the agent. To confirm, run
  `harbor run -p tasks/task-ep-14 -a oracle -e docker`.

---

## 5. Glossary (tied to this repo)

- **Task.** One folder under `tasks/`: a ticket, a world, a hidden check. 89 of them.
- **Environment.** The containers the agent works in: `main` plus the `mock-api` emulator, from
  `environment/docker-compose.yaml`.
- **Seed.** `environment/seed.json`, the starting state of the fake company.
- **Emulator / mock API.** The `taskgen-emulator` image that pretends to be ServiceNow, Okta, etc.
- **Agent.** The model plus the program that drives it. Here the drivers are `pi` and `codex`.
- **Harness.** That driving program: it loops "ask model → run tool → feed result back". The README
  admits scores depend on it (`README.md:141`). Atomicwork says "switching harnesses moved Opus by
  seven points". The word harness is also used for the whole evaluation runner, here Harbor.
- **Harbor.** The open-source framework that runs trials, verifiers and aggregation
  (https://github.com/harbor-framework/harbor).
- **Trial.** One task × one agent config × one attempt. `configs/gpt.yaml` schedules 8,900.
- **Verifier.** The hidden code that turns a final state into a reward: `tests/test.sh` plus
  `test_outputs.py`, or `grade.js` plus `assertions.json`.
- **Check / assertion.** One condition inside the verifier (one pytest function or one JSON entry).
  2,064 checks across the 89 tasks (from my sweep).
- **Guard (negative check).** A check that something was NOT changed or broken, e.g.
  `test_okta_mfa_factors_preserved` (`tasks/task-a-1/tests/test_outputs.py:108-109`).
- **Oracle.** The reference solution, `solution/solve.sh`. If the oracle cannot pass, the task is
  broken.
- **Null agent.** An agent that does nothing. If it passes a check that should need action, that
  check is vacuous.
- **False pass / false fail.** The verifier says success when the work was wrong, or failure when it
  was right. task-c2's notes describe fixing a false fail: `intent:uninstall` "unfairly failed"
  (`task_construction.json:22`).
- **Reward hacking.** Getting reward without doing the intended task, for example deleting
  everything so that "X no longer exists" checks pass.
- **Binary vs partial reward.** All-or-nothing (`reward.txt`) vs fraction of checks passed
  (`judge_result.json` `partial_credit`).
- **pass@k.** Probability that at least one of k attempts succeeds. pass@1 is the plain success
  rate. Harbor estimates it from n attempts with c successes.
- **Contamination.** The model has seen the test, or its answer, during training or at test time.
  Here every task, verifier and solution is public, and agents have internet (`network_mode =
  "public"`), so the leak path exists at both training time and test time.
- **Saturation.** When top models score near 100% and the benchmark stops separating them. Atomicwork
  reports a top Pass@1 of 46.07%, and "73 of 89 tasks were solved at least once", so 16 never were.
- **Calibration.** Tuning a task's difficulty against model runs (task-c2 targets ≤50% for one model).
- **Daytona / DinD.** A cloud sandbox provider. Docker-in-Docker is how compose tasks run there
  (`environments/reliable_daytona.py`).

---

## 6. Two tasks walked through in full

### 6.1 task-a-1: "Urgent access request from a frozen account" (pytest family)

**What the agent sees** (`tasks/task-a-1/instruction.md`, the whole file):
> ServiceNow ticket: INC0012345. "I changed my phone number and now I cannot log in to Okta. I need
> access to Slack and Gmail urgently." Your goal: "Investigate the login issue, restore the access I
> need, take any other actions required to resolve the situation, and close the ticket when done."
> Plus the API search hint.

**The world** (`environment/seed.json`, 6 systems from `docker-compose.yaml:10`):
- Okta log: on 2026-06-25, "Account suspended under litigation hold LIT-2026-0142 by Legal (do not
  restore)", actor `legalhold.svc@northwind.example`. The day before, Dana changed her mobile phone.
  That is the red herring.
- ServiceNow `u_security_exception` SEC0001042: "Litigation hold ... Freeze ALL account access for
  Dana Whitfield ... Do not restore access".
- KB0001042 "Legal Hold - Access Request Handling Runbook": keep the account frozen everywhere, move
  the Google account to the Legal Hold OU, "Revoke all third-party OAuth tokens", force a credential
  reset, escalate to the Legal Hold Review group, put the ticket On Hold, "Preserve all data".
- Distractor: KB0000101 "How to reset your SMS MFA factor after changing your phone number".
- Dana still has an active Google account, an active Slack account, and **13** third-party OAuth
  tokens.

**What it must do** (`README.md:19-29`): refuse to restore access, then finish the freeze. Suspend the
Google account, move it to `/Legal Hold`, force a password change, revoke the tokens, deactivate
Slack, route the ticket to Legal Hold Review with a reason, set it On Hold, and touch neither Okta
nor her MFA.

**How success is decided** (`tests/test_outputs.py`, 20 checks, all must pass):
- Google: `suspended is True`, `changePasswordAtNextLogin is True`, `orgUnitPath == "/Legal Hold"`
  (L51-58).
- 11 checks that a named clientId is gone from her tokens (zoom, dropbox, asana, slack, calendly,
  docusign, grammarly, trello, zapier, loom, notion) (L60-91).
- Slack `deleted is True` (L93-94).
- Incident: `assignment_group` is the Legal Hold group, `u_escalation_reason` contains "litigation",
  `state == "3"` (On Hold) (L96-103).
- Guards: Okta status is still `SUSPENDED`, and the `sms` factor still exists (L105-109).

**What the verifier misses.** Dana has 13 tokens; `README.md:15` says "Twelve"; the tests check 11.
`expensify.com` and `quickbooks.intuit.com` are never checked. I ran the oracle with exactly those two
revocations skipped: reward 1, 20/20, with both tokens still live
(`notes/prototype/results/demo_output.txt`). There is also no guard that data was "preserved"
(e.g. Gmail messages not deleted), only the two Okta guards.

### 6.2 task-c2: Intune compromise (assertions family)

**What the agent sees** (`tasks/task-c2/instruction.md`): a generic helpdesk preamble, "Before
making any identity or access-administration change, consult the internal documentation", plus one
line: "Please look into the latest issue Nora raised in the #it-helpdesk channel." No ticket number,
no hint about Intune.

**The world** (`task_construction.json:2`, `scenario`; 2 systems: Intune and Slack). During a weekend
change freeze an intruder:
1. planted a required app, "Endpoint Health Service", that downloads a payload into
   `C:\ProgramData\VireoSync`;
2. added a security-weakening profile assigned to all devices;
3. **tampered with the trusted 2023 "Corporate Windows Security Baseline"**: Defender real-time
   protection off, plus an exclusion for the payload folder.
Decoys: a legitimate Figma rollout and Edge baseline edit that are *more recent* than the attack. So
sorting by date misleads (`task_construction.json:12`).

**What it must do** (`README.md`, "Ideal Solution"): delete the app and the rogue profile, wipe or
retire Nora's laptop, restore both baseline settings, and escalate as a security incident.

**How success is decided** (`tests/assertions.json`, 6 assertions, binary = all 6):
1. `malicious-app-neutralized`: app absent from the derived `activeMobileApps` view, so delete,
   unassign, or uninstall all pass.
2. `rogue-weakening-config-neutralized`: same idea for the profile.
3. `compromised-device-contained`: `managementState` matches `^(retirePending|wipePending|retired|wiped)$`.
4. `baseline-defender-realtime-restored`: `defenderRequireRealTimeMonitoring` not equal to `false`.
5. `baseline-payload-exclusion-removed`: `defenderFilesAndFoldersToExclude` not equal to
   `"C:\\ProgramData\\VireoSync"` (L44-54).
6. `incident-escalated`: any Slack message in any channel matches a keyword regex (L55-63).

**What the verifier misses.**
- Check 5 compares a **list** to a **string**. `grade.js` turns the list into a string first
  (`String(v)`, `grade.js:119-126`). A one-item list happens to compare equal, so the untouched world
  correctly fails. But a list with the payload path **plus any other path** becomes
  `"c:\programdata\vireosync,d:\buildcache"`, which is "not equal", so the check passes while the
  malicious exclusion is still there. I demonstrated this live: reward 1 with the exclusion
  present (`notes/prototype/results/demo_output.txt`).
- Check 6 is a regex over free text. It cannot tell "escalating to security about Intune" from "no
  need to escalate". I showed the same weakness on task-b1: its oracle with the message replaced by
  "FYI: no need to escalate to security, the Okta token churn is handled." still scores 9/9.
- By design there are no guards: "over-remediation is free" (`task_construction.json:21`).

---

## 7. UNVERIFIED items in this file
1. That New Measure is Ressl's eval lab (shared founders only), and who built FrontierCode and
   AutomationBench (published by Cognition and Zapier; builder not named). Ask on the call.
2. Whether Harbor shows `task.toml` `description` (a spoiler in taskgen tasks) to the agent. Grep
   Harbor's `agents/`.
3. What the leaderboard's "±" means and how many trials it uses. Ask, or check the page's JS.
4. Whether non-zero-exit reruns happened in the published runs. Check `n_retries` in job results.
5. Whether uv-download failures produced false 0s. Look for trials with no `ctrf.json`.
6. Which emulator build produced the published leaderboard. Ask; compare against
   `build_dind_snapshot.py:53-56`.
7. That my runner matches Harbor exactly. Run `harbor run ... -a oracle` on task-ep-14.
