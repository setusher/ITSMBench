#!/usr/bin/env python3
"""Summarise results/sweep.jsonl (written by `live_probe.py --sweep`) into a markdown table.

Three sanity checks every benchmark task should pass:
  1. oracle solves it      -> the reference solution gets reward 1
  2. oracle is repeatable  -> two oracle runs on fresh worlds give identical per-check results
  3. doing nothing fails   -> the null agent gets reward 0; and no ACTION check passes on the
                              untouched world (guard checks like "X untouched" are expected to pass)

Usage: python3 summarize_sweep.py [results/sweep.jsonl] > results/sweep_summary.md
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Same heuristic as static_audit.py: a check whose name sounds like "don't break X".
GUARD_NAME = re.compile(r"guard|preserv|remain|untouched|unchanged|intact|spare|kept|keep|control|still|"
                        r"bystander|not_|no_|exact|stable|present|only_|left", re.I)


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "sweep.jsonl"
    runs = defaultdict(lambda: defaultdict(list))
    errors = []
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if r.get("error"):
            errors.append(r)
            continue
        runs[r["task"]][r["agent"]].append(r)

    rows, oracle_fail, flaky, null_reward1, vacuous = [], [], [], [], []
    for task in sorted(runs):
        nul = runs[task]["null"][0] if runs[task]["null"] else None
        ors = runs[task]["oracle"]
        o_rewards = [o["reward"] for o in ors]
        same = len(ors) == 2 and ors[0]["checks"] == ors[1]["checks"]
        if any(x != 1 for x in o_rewards):
            oracle_fail.append(task)
        if len(ors) == 2 and not same:
            diff = [k for k in ors[0]["checks"] if ors[0]["checks"][k] != ors[1]["checks"].get(k)]
            flaky.append((task, diff))
        null_pass = [k for k, v in (nul or {}).get("checks", {}).items() if v]
        action_pass = [k for k in null_pass if not GUARD_NAME.search(k)]
        if nul and nul["reward"] == 1:
            null_reward1.append(task)
        if action_pass:
            vacuous.append((task, action_pass))
        rows.append(f"| {task} | {nul['family'] if nul else '?'} | "
                    f"{nul['n_pass'] if nul else '?'}/{nul['n_checks'] if nul else '?'} | "
                    + " , ".join(f"{o['n_pass']}/{o['n_checks']}" for o in ors)
                    + f" | {'yes' if same else 'NO'} | {', '.join(action_pass[:3]) or '-'} |")

    n = len(runs)
    out = ["# Live sweep: null agent + oracle x2 on every task", "",
           f"Source: `{path.name}`. Emulator: the digest pinned in the repo README. "
           "Verifier: each task's own tests (pytest 8.4.1 / grade.js).", "",
           "## Headline numbers", "",
           f"- tasks swept: {n} (infra errors: {len(errors)})",
           f"- oracle gets reward 1 on both runs: {n - len(oracle_fail)}/{n}",
           f"- oracle fails: {len(oracle_fail)} -> {', '.join(oracle_fail) or 'none'}",
           f"- two oracle runs disagree on some check (flaky): {len(flaky)} -> "
           + ("; ".join(f"{t}: {d[:3]}" for t, d in flaky) or "none"),
           f"- null agent gets reward 1: {len(null_reward1)} -> {', '.join(null_reward1) or 'none'}",
           f"- tasks where a non-guard-looking check passes with NO agent action: {len(vacuous)} "
           "(name heuristic; review each)", ""]
    if vacuous:
        out += ["| task | checks passing on the untouched world (non-guard names) |", "|---|---|"]
        out += [f"| {t} | {', '.join(c)} |" for t, c in vacuous]
        out.append("")
    out += ["## Per task", "",
            "| task | family | null agent | oracle runs | oracle repeatable | non-guard checks passing for null |",
            "|---|---|---|---|---|---|"] + rows
    if errors:
        out += ["", "## Infra errors", ""] + [f"- {e['task']} {e['agent']}: {e['error'][-200:]}" for e in errors]
    print("\n".join(out))


if __name__ == "__main__":
    main()
