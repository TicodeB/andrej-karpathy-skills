import logging
import os
import tempfile
import unittest
from upload import upload_file, download_file


class Reply:
    def __init__(self, status, body=b''):
        self.status, self.body = status, body

    def read(self):
        return self.body


class Accept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.write(b'bread')
        self.tmp.close()

    def tearDown(self):
        os.remove(self.tmp.name)

    def test_success_is_logged(self):
        with self.assertLogs(level=logging.DEBUG) as logs:
            self.assertTrue(upload_file(self.tmp.name, 'http://x/y', opener=lambda r: Reply(200)))
        self.assertTrue(logs.records)

    def test_failure_is_logged(self):
        with self.assertLogs(level=logging.WARNING):
            self.assertFalse(upload_file('/no/such/file', 'http://x/y', opener=lambda r: Reply(200)))

    def test_existing_behaviour_kept(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.assertFalse(upload_file(self.tmp.name, 'http://x/y', opener=lambda r: Reply(500)))
        target = self.tmp.name + '.out'
        self.addCleanup(lambda: os.path.exists(target) and os.remove(target))
        self.assertTrue(download_file('http://x/y', target, opener=lambda u: Reply(200, b'ok')))
        self.assertFalse(download_file('http://x/y', target, opener=lambda u: Reply(404)))
