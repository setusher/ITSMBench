# What's good and bad about ITSMBench, FrontierCode and AutomationBench

*Draft. Every factual claim is listed with its source in `02_evidence_table.md`. Each [YOUR TAKE] is
a question to answer in your own words before you send this.*

I read three agent benchmarks. ITSMBench, built by New Measure with Atomicwork, puts an agent inside
mock IT systems and grades the final state. FrontierCode, published by Cognition, asks whether a
maintainer would merge a model's pull request. AutomationBench, published by Zapier, tests workflows
across business apps through REST APIs. I had the full ITSMBench repo and could run it. For the
other two I only had public write-ups.

## Task realism

ITSMBench tasks read like real tickets. In task-a-1 an employee asks for her access back. The right
answer is to refuse, because Legal froze the account, and then finish the freeze in every system.
The seed even includes a help article about resetting a phone factor, which is the tempting wrong
path. The README admits the APIs are mocks. FrontierCode tasks were built by maintainers from their
own repos, at over 40 hours per task. AutomationBench tasks were generated from the shape of real
customer workflows. Its paper says synthetic data risks "lack of realism and impossibility".

[YOUR TAKE: For a company buying an agent, which matters more: real systems, or real judgment calls?]

## Verifier quality and reward hacking

ITSMBench grades the final state of the systems, not the agent's explanation, which I like. But many
tasks only check that the agent did the right thing. They do not check that it avoided the wrong
thing. In 54 of the 89 tasks, no check passes on the untouched world. So none of those tasks has a
pure "do not break this" check. To test what that means, I took a task's own solution. I changed one
or two lines so it does something the README calls wrong. For one task I wrote a short blunt script
instead. Seven of these variants, on five tasks, still got full reward. In task-iam-12, deleting
every permission assignment in the org scores 25 out of 25. In task-c2, the attacker's antivirus
exclusion can stay, because the grader compares a list as a string. AutomationBench says it adds negative assertions to stop this kind of "shotgun"
behaviour. FrontierCode had the opposite problem. It audited its blocking criteria and demoted 75
that were too strict.

[YOUR TAKE: For a customer choosing an agent, is a false pass worse than a false fail? Why?]

## Difficulty and saturation

None of the three is close to saturated. ITSMBench's top Pass@1 on Atomicwork's page is 46.07%, and
73 of 89 tasks were solved at least once. FrontierCode's best score on its hardest subset is 13.4%.
AutomationBench says the best model scores 9.9%. One thing worries me in ITSMBench. Some tasks were
tuned until one target model failed. The notes for task-c2 mention a "<=50% target" for gpt-5.6-sol.

[YOUR TAKE: Is it fair to tune task difficulty against a model you later rank? What would you do instead?]

## Contamination

ITSMBench publishes every task, test and reference solution. Agents also run with full internet
access in all 89 tasks. So a run could search the ticket number and find the answer on GitHub. I did
not see this happen. I only see that the path exists. FrontierCode keeps its tasks private to avoid
contamination. AutomationBench posts leaderboard scores from a private set.

[YOUR TAKE: Is openness worth this risk for a benchmark that enterprises will use to buy agents?]

## Reproducibility and cost

ITSMBench does a lot right here. The emulator image is pinned by digest and the clock is frozen. When
I ran every task's solution twice on fresh worlds, all 89 gave identical check results. But with the
pinned emulator, two reference solutions fail their own tests. Both pass on an older emulator build
that the repo's snapshot script also pulls. The published GPT config alone is 8,900 trials. The
leaderboard lists an average cost of $1.75 for its top row, but does not say per what. FrontierCode
runs each model five times at every reasoning effort. I did not find run costs for FrontierCode or
AutomationBench.

[YOUR TAKE: Who should own re-validating tasks when the environment changes: the benchmark team or the customer?]

## Failure analysis

72 of the 89 ITSMBench tasks have a "What agents often miss" section, and the assertion grader saves
results per check. But the notes are prose, often from a single run, and nothing groups failures
across models. FrontierCode grades against named blocker criteria, so a failure points at a specific
requirement. AutomationBench gives no partial credit but still tracks how close a model got.

[YOUR TAKE: What one failure category would you want reported for every task, and why?]

## Ideas

1. [IDEA 1 (03_idea.md): verifier audit kit. Problem, what you built, one result.]
2. [IDEA 2 (03_idea.md): re-run solutions on every environment change.]
3. [IDEA 3 (03_idea.md): task regeneration or failure taxonomy, your pick.]
