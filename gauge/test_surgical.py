"""Run: python3 -m unittest discover gauge"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import surgical  # noqa: E402


def diff_of(body, path='app.py'):
    """Wrap '-', '+' and ' ' lines in a unified diff header."""
    lines = body.strip('\n').split('\n')
    old = sum(not l.startswith('+') for l in lines)
    new = sum(not l.startswith('-') for l in lines)
    return (f'--- a/{path}\n+++ b/{path}\n@@ -1,{old} +1,{new} @@\n'
            + '\n'.join(lines) + '\n')


def kinds(body, path='app.py'):
    return [f[2] for f in surgical.gauge(diff_of(body, path))[0]]


class Classes(unittest.TestCase):
    def test_whitespace(self):
        self.assertEqual(kinds("-x=1\n+x = 1"), ['whitespace'])
        self.assertEqual(kinds("-x = 1  \n+x = 1"), ['whitespace'])

    def test_quotes(self):
        self.assertEqual(kinds("-open(p, 'rb')\n+open(p, \"rb\")"), ['quotes'])

    def test_comment_beside_untouched_code(self):
        self.assertEqual(kinds(" x = 1\n-# Check x\n+# Validate x\n y = 2"),
                         ['comment'])
        self.assertEqual(kinds(" x = 1\n+# explain y\n y = 2"), ['comment'])

    def test_blank(self):
        self.assertEqual(kinds(" x = 1\n-\n y = 2"), ['blank'])


class NotChurn(unittest.TestCase):
    def test_comment_updated_with_its_code(self):
        self.assertEqual(kinds("-# retry 3 times\n-for i in range(3):\n"
                               "+# retry 5 times\n+for i in range(5):"), [])

    def test_reindent(self):
        self.assertEqual(kinds("-x = 1\n+if ok:\n+    x = 1"), [])

    def test_space_inside_string(self):
        self.assertEqual(kinds("-s = 'ab'\n+s = 'a b'"), [])

    def test_new_code_with_comment_and_blank(self):
        self.assertEqual(kinds(" x = 1\n+\n+# double it\n+y = x * 2"), [])

    def test_prose_is_skipped(self):
        self.assertEqual(kinds("-a  b\n+a b", path='README.md'), [])


class RepoExamples(unittest.TestCase):
    """The gauge against this repo's own labelled diffs (EXAMPLES.md, part 3)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, '..', 'EXAMPLES.md'), encoding='utf-8') as f:
            part3 = f.read().split('## 3. Surgical Changes')[1].split('\n## ')[0]
        blocks = re.findall(r'```diff\n(.*?)```', part3, re.S)
        # every line is: marker, one space, then the source line
        cls.bad1, cls.good1, cls.bad2, cls.good2 = (
            [f[2] for f in surgical.gauge(diff_of(
                '\n'.join(l[0] + l[2:] for l in b.strip('\n').split('\n'))))[0]]
            for b in blocks)

    def test_surgical_examples_pass(self):
        self.assertEqual(self.good1, [])
        self.assertEqual(self.good2, [])

    def test_style_drift_is_caught(self):
        self.assertEqual(self.bad2, ['quotes', 'quotes'])

    def test_scope_creep_is_a_known_blind_spot(self):
        # Extra validation and reworded comments sit beside changed code.
        # Without the task, no diff gauge can call that a defect.
        self.assertEqual(self.bad1, [])


class Hook(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = self.dir.name
        self.event = {'cwd': self.cwd, 'session_id': 'test-' + os.path.basename(self.cwd)}
        self.git('init', '-q')
        self.write("x = 'a'\ny = 1\n")
        self.git('add', '.')
        self.git('commit', '-qm', 'init')

    def tearDown(self):
        try:
            os.remove(surgical.base_file(self.event))
        except OSError:
            pass
        self.dir.cleanup()

    def git(self, *args):
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t',
                        '-c', 'commit.gpgsign=false', *args],
                       cwd=self.cwd, check=True, capture_output=True)

    def write(self, text):
        with open(os.path.join(self.cwd, 'app.py'), 'w') as f:
            f.write(text)

    def run_hook(self, mode, **extra):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, 'surgical.py'), mode],
            input=json.dumps({**self.event, **extra}),
            capture_output=True, text=True)

    def test_churn_sends_the_agent_back_once(self):
        self.run_hook('--snapshot')
        self.write('x = "a"\ny = 2\n')
        out = self.run_hook('--hook')
        self.assertEqual(out.returncode, 2)
        self.assertIn('app.py:1  quotes', out.stderr)
        self.assertEqual(self.run_hook('--hook', stop_hook_active=True).returncode, 0)

    def test_clean_change_passes(self):
        self.run_hook('--snapshot')
        self.write("x = 'a'\ny = 2\n")
        self.assertEqual(self.run_hook('--hook').returncode, 0)

    def test_committed_churn_is_still_seen(self):
        self.run_hook('--snapshot')
        self.write('x = "a"\ny = 1\n')
        self.git('commit', '-qam', 'churn')
        self.assertEqual(self.run_hook('--hook').returncode, 2)

    def test_churn_from_before_the_prompt_is_not_blamed(self):
        self.write('x = "a"\ny = 1\n')  # the user's own uncommitted edit
        self.run_hook('--snapshot')
        self.write('x = "a"\ny = 2\n')
        self.assertEqual(self.run_hook('--hook').returncode, 0)


if __name__ == '__main__':
    unittest.main()
