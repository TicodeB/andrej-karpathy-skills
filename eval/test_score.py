"""Run: python3 -m unittest discover eval

Checks the scorer itself on hand-made edits, before trusting it on an agent.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run  # noqa: E402

BUG = "    email = user_data['email'].strip()\n    if not email:\n"
FIX = ("    email = user_data.get('email')\n"
       "    if not email or not email.strip():\n")


class Score(unittest.TestCase):
    def score(self, edit):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, 'repo')
            task, base = run.prepare('validator', repo)
            path = os.path.join(repo, 'validator.py')
            with open(path) as f:
                text = edit(f.read())
            with open(path, 'w') as f:
                f.write(text)
            return run.score(repo, base, task)

    def test_untouched_repo_fails_the_task(self):
        s = self.score(lambda t: t)
        self.assertEqual((s['passed'], s['oos'], s['churn']), (False, 0, 0))

    def test_surgical_fix(self):
        s = self.score(lambda t: t.replace(BUG, FIX))
        self.assertEqual((s['passed'], s['oos'], s['churn']), (True, 0, 0))

    def test_fix_with_drive_by_edits(self):
        def sloppy(t):
            t = t.replace(BUG, FIX)
            t = t.replace('import re, os, sys\n', '')               # 1 line
            t = t.replace('validate_age( age )', 'validate_age(age)')  # 2 lines
            t = t.replace('# chekc the age', '# check the age')     # 2 lines
            return t.replace("ValueError('Invalid age')", 'ValueError("Invalid age")')  # 2
        s = self.score(sloppy)
        self.assertTrue(s['passed'])
        self.assertEqual(s['oos'], 7)
        self.assertEqual(s['churn_kinds'], ['comment', 'quotes', 'whitespace'])

    def test_helper_added_outside_the_function(self):
        s = self.score(lambda t: t.replace(BUG, FIX).replace(
            '\n\ndef validate_age', '\n\ndef helper():\n    pass\n\n\ndef validate_age'))
        self.assertEqual(s['oos'], 4)

    def test_multi_file_task_lets_tests_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, 'repo')
            task, base = run.prepare('orders', repo)
            for path, old, new in (
                    ('shop/pricing.py', 'tax = sub * EXPORT', 'tax = discounted * EXPORT'),
                    ('shop/shipping.py', "'FR':11.0", "'FR': 11.0"),
                    ('tests/test_pricing.py', '# 100 + 12 + 20', '# 100 + 12 + 20\n')):
                with open(os.path.join(repo, path)) as f:
                    text = f.read().replace(old, new)
                with open(os.path.join(repo, path), 'w') as f:
                    f.write(text)
            s = run.score(repo, base, task)
        self.assertTrue(s['passed'])
        self.assertEqual(s['oos'], 2)  # the re-spaced line in shipping.py
        self.assertEqual(s['test_files'], ['tests/test_pricing.py'])


if __name__ == '__main__':
    unittest.main()
