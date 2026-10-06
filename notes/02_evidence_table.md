# Evidence table for `02_writeup_draft.md`

Every factual claim in the draft, in order. Check each one before you send.

How each source was checked:
- **Repo**: a path in this clone, which I read myself.
- **Run**: produced by `notes/prototype/` on this machine. Re-run it to reproduce.
- **Web (re-checked)**: I fetched the page myself on 2026-10-06 and saw the quote.
- **Web (research agent)**: found by a research sub-agent with a quote. I did not re-fetch it.

Abbreviations: ITSM = ITSMBench, FC = FrontierCode, AB = AutomationBench.
Web URLs used below:
- [AW] https://www.atomicwork.com/itsm-bench
- [NM] https://newmeasure.ai/about and https://newmeasure.ai/benchmarks
- [FC1] https://cognition.com/blog/frontier-code
- [FC11] https://cognition.com/blog/frontier-code-1.1
- [AB] https://arxiv.org/html/2604.18934v1 (abstract: https://arxiv.org/abs/2604.18934)

| # | Claim in the draft | Bench | Source | How checked |
|---|---|---|---|---|
| 1 | ITSMBench is from New Measure and Atomicwork | ITSM | [NM] /benchmarks: "We worked with the Atomicwork team to build a public benchmark ... 89 tasks"; git remote `new-measure/ITSMBench` | Web (research agent) + Repo |
| 2 | It puts an agent in mock IT systems and grades the final state | ITSM | `README.md:7-12`, `README.md:137` | Repo |
| 3 | FrontierCode is published by Cognition and asks whether a maintainer would merge the PR | FC | [FC1] "Would the maintainer actually merge this PR?" | Web (re-checked) |
| 4 | AutomationBench is published by Zapier and tests cross-app workflows via REST APIs | AB | arXiv abstract: "cross-application workflow orchestration via REST APIs"; [AB] mentions "Zapier's Agents service" | Web (research agent for the abstract; re-checked [AB]) |
| 5 | In task-a-1 the employee wants access back, Legal froze the account, and the right move is to refuse and finish the freeze | ITSM | `tasks/task-a-1/instruction.md:7-11`; `tasks/task-a-1/README.md:9-12`; seed record SEC0001042 in `tasks/task-a-1/environment/seed.json` | Repo |
| 6 | The seed includes a help article about resetting a phone factor (the tempting wrong path) | ITSM | `tasks/task-a-1/environment/seed.json`, `servicenow.kb_knowledge` KB0000101 "How to reset your SMS MFA factor after changing your phone number" | Repo |
| 7 | The README admits the APIs are mocks | ITSM | `README.md:137` "Tasks use synthetic mock APIs" | Repo |
| 8 | FC tasks were built by maintainers from their own repos, at over 40 hours per task | FC | [FC1] "20+ world-class open-source developers built ... coding tasks from the repos they maintain, spending more than 40 hours per task." | Web (re-checked) |
| 9 | AB tasks were generated from the shape of real customer workflows | AB | [AB] "Tasks were synthetically generated based on use cases from real customers ... only the shape of workflows" | Web (re-checked) |
| 10 | AB paper says synthetic data risks "lack of realism and impossibility" | AB | [AB] "there is a risk of lack of realism and impossibility" | Web (re-checked) |
| 11 | ITSM grades final state, not the agent's explanation | ITSM | `README.md:11-12`; every `tests/test_outputs.py` reads state over HTTP; [AW] "We don't use an LLM as a judge." Note: escalation checks read Slack message text by regex (`tasks/task-b1/tests/assertions.json:100-107`) | Repo + Web (re-checked) |
| 12 | In 54 of 89 tasks no check passes on the untouched world | ITSM | `notes/prototype/results/sweep.jsonl` (null-agent rows with `n_pass == 0`) | Run |
| 13 | I changed one or two lines of a task's own solution (one variant is a short standalone script, `iam12-blunt`); 7 variants on 5 tasks got full reward | ITSM | `notes/prototype/live_probe.py` (`MUTANTS`); `results/demo_output.txt`; `results/extra_mutants_output.txt` | Run |
| 14 | In task-iam-12, deleting every permission assignment scores 25/25 | ITSM | `results/demo_output.txt` ("deleted 77 of 77 assignments, held by 71 different users"); verifier `tasks/task-iam-12/tests/test_outputs.py:112-123`; README requires least disruption, `tasks/task-iam-12/README.md:21-25` | Run + Repo |
| 15 | In task-c2 the attacker's exclusion can stay because a list is compared as a string | ITSM | `tasks/task-c2/tests/assertions.json:44-54`; `tasks/task-c2/tests/grade.js:119-126, 149`; `results/demo_output.txt` | Run + Repo |
| 16 | AB adds negative assertions to stop "shotgun" behaviour | AB | [AB] "We include negative assertions to prevent shotgun approach reward hacking" | Web (re-checked) |
| 17 | FC audited its blocking criteria and demoted 75 that were too strict | FC | [FC11] "We found 75 blockers that were overly strict, and we have since demoted them"; "We audited all 1000+ blocker criteria" | Web (re-checked) |
| 18 | ITSM top Pass@1 is 46.07% | ITSM | [AW] "claude-opus-5 [high] claude-code 46.07% ±1.99" | Web (re-checked) |
| 19 | 73 of 89 ITSM tasks were solved at least once | ITSM | [AW] "73 of 89 tasks were solved at least once by at least one model in at least one trial." | Web (re-checked) |
| 20 | FC's best score on its hardest subset is 13.4% | FC | [FC1] "Claude Opus 4.8, achieves a score of only 13.4%" (Diamond) | Web (re-checked) |
| 21 | AB's best model scores 9.9% | AB | [AB] "Opus 4.7 tops the leaderboard at 9.9%." | Web (re-checked) |
| 22 | Some ITSM tasks were tuned until one target model failed; task-c2 mentions a "<=50% target" for gpt-5.6-sol | ITSM | `tasks/task-c2/task_construction.json:22` ("CALIBRATION ... <=50% target"); the 16 taskgen READMEs each report one gpt-5.6-sol run (e.g. `tasks/task-b1/README.md:3-5`) | Repo |
| 23 | ITSM publishes every task, test and reference solution | ITSM | `tasks/*/tests/`, `tasks/*/solution/` in the public repo; [AW] "we're open-sourcing all of it, every task and its corresponding environment!" | Repo + Web (re-checked) |
| 24 | Agents have full internet access in all 89 tasks | ITSM | `network_mode = "public"` in all 89 `tasks/*/task.toml` (e.g. `tasks/task-a-1/task.toml:22`); Harbor docs `/tasks/network-policies`: "`public` / Full network access" | Repo + Web (research agent) |
| 25 | A run could search the ticket number and find the answer on GitHub; not observed | ITSM | Ticket number in `tasks/task-a-1/instruction.md:3`; solution in `tasks/task-a-1/solution/solution.py`. **UNVERIFIED** whether any run did this. Check by grepping agent trajectories for `github.com` | Inference |
| 26 | FC keeps its tasks private to avoid contamination | FC | [FC1] "we don't currently plan to release the tasks publicly to avoid contamination" | Web (re-checked) |
| 27 | AB posts leaderboard scores from a private set | AB | [AB] "Scores will be posted to the leaderboard based on the private dataset." | Web (re-checked) |
| 28 | The ITSM emulator image is pinned by digest | ITSM | `README.md:76`; `scripts/build_dind_snapshot.py:53-54` | Repo |
| 29 | The clock is frozen | ITSM | top-level `_now` in 86 of 89 `seed.json` files (not in a-1, a-2, a-5); the emulator sets the `Date` header from `_now` (`/opt/emulator/server.js` inside the pinned image) | Repo + Run |
| 30 | Every task's solution, run twice on fresh worlds, gave identical check results on all 89 | ITSM | `notes/prototype/results/sweep_summary.md` ("flaky: 0") | Run |
| 31 | On the pinned emulator two reference solutions fail their own tests | ITSM | `results/sweep_summary.md` (task-ep-14 11/24, task-ep-9 16/26); ep-14 error: emulator rejects `discovery_source: Device42` (`tasks/task-ep-14/solution/solution.py:237`) | Run |
| 32 | Both pass on an older emulator build the snapshot script also pulls | ITSM | `results/sweep_cat_emulator.jsonl` (24/24 and 26/26, twice); `scripts/build_dind_snapshot.py:55-56` | Run + Repo |
| 33 | The published GPT config is 8,900 trials | ITSM | `configs/gpt.yaml:6` (5 attempts) × 20 agent entries (L15-117) × 89 tasks (`README.md:115`) | Repo |
| 34 | Leaderboard lists an average cost of $1.75 for its top row, unit not stated | ITSM | [AW] columns "Model, Pass@1, Avg cost, Out tok"; row "... 46.07% ±1.99 $1.75 21.4K" | Web (re-checked) |
| 35 | FC runs each model five times at every reasoning effort | FC | [FC1] "Each model is run 5 times at every available reasoning effort." | Web (re-checked) |
| 36 | I did not find run costs for FC or AB | FC, AB | Absence. The research was not exhaustive. **UNVERIFIED**; check the AB leaderboard at https://zapier.com/benchmarks | Inference |
| 37 | 72 of 89 ITSM tasks have a "What agents often miss" section | ITSM | `grep -l "What agents often miss" tasks/*/README.md` → 72 | Repo |
| 38 | The assertion grader saves results per check | ITSM | `tasks/task-b1/tests/grade.js:204-208` (`judge_result.json` with an `assertions` array) | Repo |
| 39 | The notes are prose, often from a single run | ITSM | e.g. `tasks/task-n-1/README.md:22`; taskgen tables show one run (`tasks/task-b1/README.md:3-5`) | Repo |
| 40 | Nothing in the repo groups failures across models | ITSM | Repo contents: only `configs/`, `environments/`, `scripts/build_dind_snapshot.py`, `tasks/` (no analysis code) | Repo |
| 41 | FC grades against named blocker criteria | FC | [FC1] "Blockers represent mergeability requirements, i.e., criteria that a maintainer would consider hard stops during code review." | Web (re-checked) |
| 42 | AB gives no partial credit but tracks how close a model got | AB | [AB] "We give no partial credit but we can see how close models get to completion for non-scoring purposes." | Web (re-checked) |

## Things in the draft that rest on my own runs, not on Harbor
Claims 12-15 and 30-32 come from my runner (`notes/prototype/live_probe.py`). It uses the same emulator
image, aliases and test files as Harbor, but it is not Harbor. To confirm one case with the official
tool: `harbor run -p tasks/task-ep-14 -a oracle -e docker`.

## Attribution note (UNVERIFIED)
The draft says FrontierCode and AutomationBench are *published by* Cognition and Zapier. That is what
the sources show. Neither page names who built them. Your briefing says Ressl builds benchmarks like
these for vertical AI companies. New Measure (same founders as Ressl) sells "custom evals and
benchmarks as a service" (https://newmeasure.ai/about), and ITSMBench is shown on its client's site.
So Ressl may well have built them. Don't claim either way. Ask on the call which ones their team
built.
