#!/usr/bin/env python3
"""Surgical gauge: count changed lines in a diff that change no behaviour.

    git diff | python3 surgical.py     exit 1 if any churn is found
    python3 surgical.py --snapshot     UserPromptSubmit hook: remember the tree
    python3 surgical.py --hook         Stop hook: gauge the diff since snapshot

The two hook modes do nothing unless the environment has SURGICAL_GAUGE=1.

Four defect classes, all detectable with no knowledge of the task:
    whitespace  line re-spaced, nothing else changed
    quotes      quote style swapped, nothing else changed
    comment     comment edited, added or deleted beside untouched code
    blank       blank lines added or deleted beside untouched code

It cannot see scope creep (extra features, unrequested refactors). That needs
a stated scope; see eval/ for a gauge that has one.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

PROSE = ('.md', '.rst', '.txt')  # whitespace is content in these
STRING = re.compile(r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''')
COMMENT = re.compile(r'\s*(#|//)')
HUNK = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def key(line, unify_quotes):
    """The line with cosmetic differences removed. Indentation is kept:
    re-indenting can change behaviour (Python), so it is never called churn."""
    body = line.strip()
    parts = STRING.split(body)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            parts[i] = re.sub(r'\s+', '', part)
        elif unify_quotes:
            parts[i] = '"' + part[1:-1] + '"'
    return len(line) - len(line.lstrip()), ''.join(parts)


def classify(removed, added):
    """Findings for one block of adjacent changed lines.
    removed and added are lists of (line_number, text)."""
    found = []
    for unify_quotes, kind in ((False, 'whitespace'), (True, 'quotes')):
        by_key = {}
        for new in added:
            if new[1].strip():
                by_key.setdefault(key(new[1], unify_quotes), []).append(new)
        unmatched, matched = [], set()
        for old in removed:
            same = by_key.get(key(old[1], unify_quotes), [])
            # identical text is a moved line: order can matter, so not churn
            new = next((n for n in same if n[1] != old[1]), None)
            if new:
                same.remove(new)
                matched.add(new)
                found.append((new[0], kind, new[1]))
            else:
                unmatched.append(old)
        removed = unmatched
        added = [n for n in added if n not in matched]
    rest = removed + added
    if rest and all(not t.strip() or COMMENT.match(t) for _, t in rest):
        kind = 'comment' if any(t.strip() for _, t in rest) else 'blank'
        found += [(n, kind, t) for n, t in (added or removed)]
    return found


def gauge(diff):
    """Return (findings, changed_line_count) for a unified diff.
    Each finding is (file, line_number, defect_class, text)."""
    findings, changed = [], 0
    path, old_no, new_no = None, 0, 0
    old_left = new_left = 0
    removed, added = [], []

    def flush():
        if path and not path.endswith(PROSE):
            findings.extend((path, *f) for f in classify(removed, added))
        removed.clear()
        added.clear()

    for line in diff.splitlines():
        if old_left <= 0 and new_left <= 0:  # between hunks: headers only
            flush()
            if line.startswith('+++ '):
                path = line[4:].split('\t')[0]
                path = None if path == '/dev/null' else re.sub(r'^b/', '', path)
            m = HUNK.match(line)
            if m:
                old_no, new_no = int(m[1]), int(m[3])
                old_left = int(m[2] or 1)
                new_left = int(m[4] or 1)
        elif line.startswith('-'):
            removed.append((old_no, line[1:]))
            old_no, old_left, changed = old_no + 1, old_left - 1, changed + 1
        elif line.startswith('+'):
            added.append((new_no, line[1:]))
            new_no, new_left, changed = new_no + 1, new_left - 1, changed + 1
        elif line.startswith('\\'):
            pass  # "\ No newline at end of file"
        else:
            flush()
            old_no, new_no = old_no + 1, new_no + 1
            old_left, new_left = old_left - 1, new_left - 1
    flush()
    return findings, changed


def report(findings, changed):
    lines = [f'Surgical gauge: {len(findings)} of {changed} changed lines '
             'change no behaviour.']
    lines += [f'  {p}:{n}  {kind:<10}  {text.strip()}'
              for p, n, kind, text in findings]
    return '\n'.join(lines)


def git(cwd, *args):
    out = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ''


def base_file(event):
    return os.path.join(tempfile.gettempdir(),
                        f"surgical-{event.get('session_id', 'x')}")


def snapshot(event):
    """Record the working tree as it is before the agent touches it."""
    cwd = event.get('cwd') or os.getcwd()
    base = git(cwd, 'stash', 'create').strip() or git(cwd, 'rev-parse', 'HEAD').strip()
    if base:
        with open(base_file(event), 'w') as f:
            f.write(base)


def hook(event):
    """Send the agent back once if its changes contain churn."""
    if event.get('stop_hook_active'):
        return 0  # already sent back once: never loop
    cwd = event.get('cwd') or os.getcwd()
    try:
        with open(base_file(event)) as f:
            base = f.read()
    except OSError:
        base = 'HEAD'
    findings, changed = gauge(git(cwd, 'diff', base))
    if not findings:
        return 0
    print(report(findings, changed), file=sys.stderr)
    print('Revert these lines unless the user asked for them, then finish.',
          file=sys.stderr)
    return 2


def main(argv):
    if argv[1:] in (['--snapshot'], ['--hook']) and os.environ.get('SURGICAL_GAUGE') != '1':
        return 0  # the hook is opt-in
    if argv[1:] == ['--snapshot']:
        snapshot(json.load(sys.stdin))
        return 0
    if argv[1:] == ['--hook']:
        return hook(json.load(sys.stdin))
    findings, changed = gauge(sys.stdin.read())
    if findings:
        print(report(findings, changed))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
