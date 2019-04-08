#!/usr/bin/env python
# coding: utf-8

"""
Functional Test of the API
"""
import os
import sys
import json
import unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import drs


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = drs.create_app()
        cls.app.app.config['TESTING'] = True
        cls.client = cls.app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_nothing(self):
        message = {"message": "Hello"}
        resp = self.client.post(
            '/v1/echo',
            data=json.dumps(message),
            headers={
                'Content-Type': 'application/json'
            }
        )
        self.assertEqual(message, resp.json['the message'])

if __name__ == '__main__':
    unittest.main()
