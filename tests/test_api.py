#!/usr/bin/env python
# coding: utf-8

"""
Functional Test of the API
"""
import io
import os
import sys
import json
import unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import drs
from drs import storage


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = drs.create_app()
        cls.app.app.config['TESTING'] = True
        cls.client = cls.app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_echo(self):
        message = {"message": "Hello"}
        resp = self.client.post(
            '/v1/echo',
            data=json.dumps(message),
            headers={
                'Content-Type': 'application/json'
            }
        )
        self.assertEqual(message, resp.json['the message'])

    def test_blobstore_handle(self):
        data = os.urandom(100)
        handle = storage.get_blobstore_handle()
        bucket = os.environ['DRS_BUCKET']
        with io.BytesIO(data) as fh:
            handle.upload_file_handle(bucket, "test_key", fh)
            handle.delete(bucket, "test_key")

if __name__ == '__main__':
    unittest.main()
