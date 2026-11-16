import unittest
from validator import validate_user, validate_age


class Accept(unittest.TestCase):
    def test_missing_or_empty_email(self):
        for data in ({'username': 'bob'}, {'email': None, 'username': 'bob'},
                     {'email': '', 'username': 'bob'}, {'email': '  ', 'username': 'bob'}):
            with self.assertRaisesRegex(ValueError, 'Email required'):
                validate_user(data)

    def test_existing_behaviour_kept(self):
        self.assertTrue(validate_user({'email': 'a@b.ie', 'username': 'bob'}))
        with self.assertRaisesRegex(ValueError, 'Invalid email'):
            validate_user({'email': 'nope', 'username': 'bob'})
        with self.assertRaisesRegex(ValueError, 'Username required'):
            validate_user({'email': 'a@b.ie'})
        self.assertTrue(validate_age(30))
        with self.assertRaises(ValueError):
            validate_age(None)
