#!/usr/bin/env python3
"""A 2x2 experiment: do the guidelines and the gauge hook reduce drive-by edits?

    python3 eval/run.py --reps 5 --model haiku --out eval/results/pilot.jsonl

Each run: copy a small repo with stylistic bait into a temp dir, give a
headless Claude Code one narrow task, then score the diff with no LLM judge.

    arm    CLAUDE.md  hook
    base   no         no
    rules  yes        no
    hook   no         yes
    both   yes        yes

    passed  hidden acceptance test passes (task done, neighbours not broken)
    oos     changed lines outside the functions the task names
    churn   changed lines that change no behaviour (gauge/surgical.py)
    added   lines added, new files included (size of the answer)
    strayed the agent touched a path outside its own repo (run is suspect)

Tasks with no accept.py are open questions ("add an export feature"): there
the measures are whether the agent built anything at all, and how much.
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, 'eval', 'tasks')
GAUGE = os.path.join(ROOT, 'gauge', 'surgical.py')
sys.path.insert(0, os.path.dirname(GAUGE))
import surgical  # noqa: E402

ARMS = {'base': (False, False), 'rules': (True, False),
        'hook': (False, True), 'both': (True, True)}
TOOLS = 'Read,Edit,Write,Glob,Grep,Bash(python3 *),Bash(git diff*),Bash(git status*)'
HUNK = re.compile(r'@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@')


def sh(cwd, *cmd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def scope_ranges(source, names):
    """(first_line, last_line, indent) of each named function in the original
    file. 'imports' means everything above the first function."""
    defs = [n for n in ast.parse(source).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    ranges = [(0, defs[0].lineno - 1, -1)] if 'imports' in names else []
    return ranges + [(d.lineno, d.end_lineno, d.col_offset)
                     for d in defs if d.name in names]


def out_of_scope(diff_u0, ranges_by_file):
    """Count changed lines outside the task's scope, from `git diff -U0`."""
    oos, path, body = 0, None, []

    def close(start, count):
        nonlocal oos
        ranges = ranges_by_file.get(path, [])
        added = [l[1:] for l in body if l.startswith('+')]
        if count:  # lines start..start+count-1 were replaced or deleted
            inside = [any(a <= n <= b for a, b, _ in ranges)
                      for n in range(start, start + count)]
            oos += inside.count(False) + (0 if inside[0] else len(added))
        else:      # pure insertion after old line `start`
            first = next((l for l in added if l.strip()), '')
            indent = len(first) - len(first.lstrip())
            ok = any(a <= start < b or (start == b and indent > col)
                     for a, b, col in ranges)
            oos += 0 if ok else len(added)

    hunk = None
    for line in diff_u0.splitlines() + ['diff --git']:
        m = HUNK.match(line)
        if m or line.startswith('diff --git'):
            if hunk:
                close(*hunk)
            hunk, body = (int(m[1]), int(m[2] or 1)) if m else None, []
        elif hunk:
            body.append(line)
        elif line.startswith('+++ '):
            path = line[6:]
    return oos


def score(repo, base, task):
    """Deterministic measures of what the agent did to the repo."""
    ranges = {}
    for path, names in task.get('scope', {}).items():
        with open(os.path.join(task['dir'], 'repo', path)) as f:
            ranges[path] = scope_ranges(f.read(), names)
    findings, changed = surgical.gauge(sh(repo, 'git', 'diff', base).stdout)
    new = sh(repo, 'git', 'ls-files', '--others', '--exclude-standard').stdout.split()
    oos = out_of_scope(sh(repo, 'git', 'diff', '-U0', base).stdout, ranges)
    added = sum(l.startswith('+') and not l.startswith('+++')
                for l in sh(repo, 'git', 'diff', base).stdout.splitlines())
    for path in new:
        with open(os.path.join(repo, path), errors='replace') as f:
            added += len(f.readlines())
    passed = None
    accept = os.path.join(task['dir'], 'accept.py')
    if os.path.exists(accept):
        shutil.copy(accept, os.path.join(repo, 'accept_hidden.py'))
        passed = sh(repo, sys.executable, '-m', 'unittest', 'accept_hidden',
                    timeout=60).returncode == 0
    return {'passed': passed, 'oos': oos, 'churn': len(findings),
            'churn_kinds': sorted({f[2] for f in findings}),
            'changed': changed, 'added': added, 'new_files': new}


def prepare(name, repo, rules=False):
    """Copy a task's fixture into `repo` as a one-commit git repository."""
    task = {'dir': os.path.join(TASKS, name)}
    with open(os.path.join(task['dir'], 'task.json')) as f:
        task.update(json.load(f))
    shutil.copytree(os.path.join(task['dir'], 'repo'), repo)
    with open(os.path.join(repo, '.gitignore'), 'w') as f:
        f.write('__pycache__/\n')
    if rules:
        shutil.copy(os.path.join(ROOT, 'CLAUDE.md'), repo)
    sh(repo, 'git', 'init', '-q')
    sh(repo, 'git', 'add', '-A')
    sh(repo, 'git', '-c', 'user.name=eval', '-c', 'user.email=eval@example.com',
       '-c', 'commit.gpgsign=false', 'commit', '-qm', 'init')
    return task, sh(repo, 'git', 'rev-parse', 'HEAD').stdout.strip()


def run_one(job):
    name, arm, rep, model, workdir = job
    rules, hook = ARMS[arm]
    run_dir = os.path.join(workdir, uuid.uuid4().hex[:8])  # tells siblings nothing
    repo = os.path.join(run_dir, 'repo')
    task, base = prepare(name, repo, rules)

    cmd = ['claude', '-p', task['prompt'], '--model', model,
           '--output-format', 'stream-json', '--verbose',
           '--no-session-persistence',
           '--strict-mcp-config', '--disable-slash-commands',
           '--setting-sources', 'project', '--permission-mode', 'acceptEdits',
           '--allowedTools', TOOLS, '--max-budget-usd', '0.50']
    log = os.path.join(run_dir, 'hook.log')
    if hook:
        py = f'"{sys.executable}" "{GAUGE}"'
        cmd += ['--settings', json.dumps({'hooks': {
            'UserPromptSubmit': [{'hooks': [{
                'type': 'command', 'command': f'{py} --snapshot'}]}],
            'Stop': [{'hooks': [{'type': 'command', 'command':
                      f'{py} --hook; rc=$?; echo $rc >> "{log}"; exit $rc'}]}],
        }})]
    started = time.time()
    out, calls = {'is_error': True}, []
    try:
        for line in sh(repo, *cmd, timeout=600).stdout.splitlines():
            event = json.loads(line)
            if event.get('type') == 'result':
                out = event
            elif event.get('type') == 'assistant':
                calls += [json.dumps(c.get('input')) for c in event['message']['content']
                          if c.get('type') == 'tool_use']
    except (subprocess.TimeoutExpired, ValueError) as e:
        out['result'] = repr(e)
    with open(os.path.join(run_dir, 'calls.txt'), 'w') as f:
        f.write('\n'.join(calls))
    calls = ' '.join(calls).replace(repo, '')
    row = {'task': name, 'arm': arm, 'rep': rep, 'model': model,
           'dir': os.path.basename(run_dir),
           'secs': round(time.time() - started),
           'strayed': '../' in calls or os.path.dirname(workdir) in calls,
           'cost_usd': out.get('total_cost_usd'), 'turns': out.get('num_turns'),
           'error': bool(out.get('is_error')),
           'hook_exits': open(log).read().split() if os.path.exists(log) else []}
    row.update(score(repo, base, task))
    with open(os.path.join(run_dir, 'reply.txt'), 'w') as f:
        f.write(str(out.get('result')))
    print(json.dumps(row), flush=True)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--reps', type=int, default=1)
    ap.add_argument('--model', default='haiku')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--tasks', nargs='*', default=sorted(os.listdir(TASKS)))
    ap.add_argument('--arms', nargs='*', default=list(ARMS))
    ap.add_argument('--out', required=True)
    ap.add_argument('--workdir', default=None, help='keep run dirs here')
    args = ap.parse_args()
    workdir = args.workdir or tempfile.mkdtemp(prefix='surgical-eval-')
    jobs = [(t, a, r, args.model, workdir)
            for r in range(args.reps) for t in args.tasks for a in args.arms]
    with ThreadPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(run_one, jobs))
    with open(args.out, 'a') as f:
        f.writelines(json.dumps(r) + '\n' for r in rows)
    print(f'{len(rows)} runs -> {args.out} (run dirs: {workdir})', file=sys.stderr)


if __name__ == '__main__':
    main()
