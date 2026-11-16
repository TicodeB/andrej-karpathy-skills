# Handover

Working state for the branch `claude/dazzling-clarke-j8rkvi`. Drop this file before sending anything upstream.

## Goal

Turn this repo's four rules from an opinion into a measured process: a gauge for drive-by edits, a hook that enforces it, and an A/B experiment with real numbers.

## Done (15/11/2026)

| Unit | File | Verified by |
|---|---|---|
| Diff gauge, 4 defect classes, stdlib only | `gauge/surgical.py` | `python3 -m unittest discover gauge` (16 tests, includes the diffs in `EXAMPLES.md`) |
| Plugin Stop hook, sends the agent back once | `hooks/hooks.json` | Live headless session with `--plugin-dir`: hook fired, agent kept the requested change, no loop |
| Experiment runner, 6 tasks, 2x2 arms | `eval/run.py`, `eval/tasks/` | `python3 -m unittest discover eval` (5 scorer tests on hand-made edits) |
| Results and write-up | `eval/results/`, `eval/README.md` | `python3 eval/report.py eval/results/*.jsonl` reproduces every table |

## Findings (177 scored runs, Haiku 5.5 and Sonnet 5.5)

- Narrow tasks: 0 of 116 runs had an out-of-scope or cosmetic line, in every arm. Floor effect. Holds on the multi-file `orders` task (26 runs, added 16/11/2026).
- Open "export" task: rules cut Haiku's median answer from 43.5 to 15.5 lines. Rules made Sonnet ask first in 6 of 8 runs (0 of 7 without).
- Hook armed in 30 runs: 0 bounces.
- Spend: about $5.45 at list prices including the discarded pilot. The runs used up the account's 5-hour usage window; the last 3 Sonnet runs failed on it and are excluded.

## Decisions and why

- Indentation changes are never called churn. Re-indenting changes behaviour in Python.
- A comment edit counts only when the code beside it is untouched. A comment updated with its code is legitimate.
- The hook compares against a snapshot taken when the prompt is submitted, so commits and the user's own uncommitted edits do not confuse it.
- The first pilot (60 runs) was discarded. Runs could read sibling run folders. Fixed with opaque folder names and a `strayed` flag, then re-run.
- `--restricted` isolates runs fully but stops `CLAUDE.md` loading (canary test), so it cannot be used for the rules arm.

## Open

1. Decide: should the Stop hook ship on by default for every plugin user? It changes behaviour for people who only wanted the rules. Version in `plugin.json` is not bumped.
2. Windows: the hook calls `python3`. On Windows 11 that is usually `python` or `py`. Untested.
3. This repo's rule "if uncertain, ask" conflicts with a working agreement of "act, don't ask". Measured: on Sonnet it does make the agent stop and ask.
4. The floor effect held on a nine-file repo. Untested: a large real codebase and long multi-turn sessions.
5. `eval/run.py --rules FILE` tests any instruction file. Not yet run on any file other than this repo's `CLAUDE.md`.

## Next action

Review the draft PR. Answer open item 1.
