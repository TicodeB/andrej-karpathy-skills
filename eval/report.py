#!/usr/bin/env python3
"""Summarise eval/run.py results as markdown.

    python3 eval/report.py eval/results/*.jsonl
"""
import json
import sys
from collections import defaultdict
from itertools import combinations
from statistics import median

ARMS = ['base', 'rules', 'hook', 'both']


def exact_p(a, b):
    """Two-sided exact permutation test on the rank sum (Mann-Whitney)."""
    pooled = sorted(a + b)
    rank = {v: (2 * pooled.index(v) + pooled.count(v) + 1) / 2 for v in pooled}
    ranks = [rank[v] for v in a + b]
    mean = sum(ranks) * len(a) / len(ranks)
    seen = abs(sum(ranks[:len(a)]) - mean)
    sums = [abs(sum(c) - mean) for c in combinations(ranks, len(a))]
    return sum(s >= seen - 1e-9 for s in sums) / len(sums)


def main(paths):
    every = [json.loads(line) for p in paths for line in open(p)]
    rows = [r for r in every if not r['error']]  # a failed run measures nothing
    closed = defaultdict(list)  # tasks with an acceptance test
    opened = defaultdict(list)  # open questions
    for r in rows:
        if r['passed'] is None:
            opened[r['model'], r['task']].append(r)
        else:
            closed[r['model'], r['arm']].append(r)

    print('### Narrow tasks: does the agent stay inside the request?\n')
    print('| model | arm | runs | task done | runs with out-of-scope lines '
          '| runs with churn | hook sent agent back | mean lines changed |')
    print('|---|---|---|---|---|---|---|---|')
    for (model, arm), rs in sorted(closed.items(),
                                   key=lambda kv: (kv[0][0], ARMS.index(kv[0][1]))):
        n = len(rs)
        hook = sum('2' in r['hook_exits'] for r in rs) if arm in ('hook', 'both') else '-'
        print(f"| {model} | {arm} | {n} | {sum(r['passed'] for r in rs)} "
              f"| {sum(r['oos'] > 0 for r in rs)} | {sum(r['churn'] > 0 for r in rs)} "
              f"| {hook} | {sum(r['changed'] for r in rs) / n:.1f} |")

    print('\n### Open tasks: how much does the agent build?\n')
    print('| model | task | arm | runs | built something | lines added: '
          'median (min-max) | exact p, base vs rules |')
    print('|---|---|---|---|---|---|---|')
    for (model, task), rs in sorted(opened.items()):
        by_arm = {a: [r for r in rs if r['arm'] == a] for a in ('base', 'rules')}
        p = exact_p(*([r['added'] for r in by_arm[a]] for a in ('base', 'rules')))
        for arm, ars in by_arm.items():
            added = [r['added'] for r in ars]
            built = sum(r['changed'] > 0 or bool(r['new_files']) for r in ars)
            print(f"| {model} | {task} | {arm} | {len(ars)} | {built} "
                  f"| {median(added):g} ({min(added)}-{max(added)}) "
                  f"| {f'{p:.4f}' if arm == 'rules' else ''} |")

    cost = sum(r['cost_usd'] or 0 for r in every)
    print(f"\n{len(rows)} runs scored, {len(every) - len(rows)} failed and excluded, "
          f"{sum(r.get('strayed', False) for r in rows)} looked outside their repo, "
          f"total cost ${cost:.2f}.")


if __name__ == '__main__':
    main(sys.argv[1:])
