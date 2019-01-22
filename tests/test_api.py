#!/usr/bin/env python
# coding: utf-8

"""
Functional Test of the API
"""
import os
import sys
import unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import drs


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = drs.create_app()
        cls.app.run(host="127.0.0.1", port="8080", debug=True)
        client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_nothing(self):
        r = self.client.post(
            '/echo',
            data='{"message": "Hello"}',
            headers={
                'Content-Type': 'application/json'
            })

        pass

if __name__ == '__main__':
    unittest.main()
