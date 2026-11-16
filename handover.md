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
- Spend: about $6.70 at list prices including the discarded pilot and the agreement test. The runs used up the account's 5-hour usage window; the last 3 Sonnet runs failed on it and are excluded.

## Your own working agreement, tested (16/11/2026, Sonnet 5.5, export task, 8 runs per row)

| Instruction file given to the agent | Asked instead of building | Median lines added |
|---|---|---|
| none (from the main experiment, 7 runs) | 0 of 7 | 22 |
| this repo's `CLAUDE.md` (from the main experiment) | 6 of 8 | 0 |
| your working agreement, rules sections only | 0 of 8 | 36.5 |
| your working agreement followed by this repo's `CLAUDE.md` | 0 of 8 | 15 |

- "Act, don't ask" overrides this repo's "if uncertain, ask": asking fell from 6 of 8 to 0 of 8 (Fisher exact p = 0.007).
- The repo's simplicity rule still works beside it: 36.5 to 15 lines (exact p = 0.037).
- Your agreement alone gave the largest answers. 36.5 vs 22 lines with no file is not significant (p = 0.12).
- All 16 answers stated their assumptions or excluded the password hash; none of the 16 export functions leaked the hash.
- The agreement file and these runs are not in the repo. Each row of new results records which `--rules` file it used.
- The first two rows were run a day earlier than the last two.

## Decisions and why

- Indentation changes are never called churn. Re-indenting changes behaviour in Python.
- A comment edit counts only when the code beside it is untouched. A comment updated with its code is legitimate.
- The hook compares against a snapshot taken when the prompt is submitted, so commits and the user's own uncommitted edits do not confuse it.
- The first pilot (60 runs) was discarded. Runs could read sibling run folders. Fixed with opaque folder names and a `strayed` flag, then re-run.
- `--restricted` isolates runs fully but stops `CLAUDE.md` loading (canary test), so it cannot be used for the rules arm.

## Open

1. Done 16/11/2026: the Stop hook is opt-in (`SURGICAL_GAUGE=1`). Plugin users who only want the rules see no change. Version in `plugin.json` is not bumped.
2. Windows: the hook calls `python3`. On Windows 11 that is usually `python` or `py`. Untested.
3. This repo's rule "if uncertain, ask" conflicts with a working agreement of "act, don't ask". Measured: on Sonnet it does make the agent stop and ask.
4. The floor effect held on a nine-file repo. Untested: a large real codebase and long multi-turn sessions.
5. The agreement test used one task and one model. Repeat on the `orders` task before relying on it.

## Next action

Review the draft PR.
