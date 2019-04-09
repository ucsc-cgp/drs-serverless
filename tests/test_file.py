#!/usr/bin/env python
# coding: utf-8

"""
Functional Test of the API
"""
import io
import os
import sys
import datetime
import requests
import json
import typing
import dcplib
import unittest
from uuid import uuid4

from dcplib.s3_multipart import get_s3_multipart_chunk_size
from dcplib.checksumming_io import ChecksummingSink

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import drs
from drs import storage
from drs.util.version import datetime_to_version_format


class TestFileApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = drs.create_app()
        cls.app.app.config['TESTING'] = True
        cls.client = cls.app.app.test_client()

    def setUp(self):
        self.handle = storage.get_blobstore_handle()
        self.staging_bucket = os.environ['DRS_BUCKET_TEST']

    def test_file_put(self):
        src_data = os.urandom(1024)
        source_url = self._checksum_and_stage_file(io.BytesIO(src_data), 1024)
        file_uuid = str(uuid4())
        version = datetime_to_version_format(datetime.datetime.utcnow())

        with self.subTest(f"Created returned when uploading a file with a unique payload, and FQID"):
            resp = self._put_file(source_url, file_uuid, version)
            self.assertEqual(resp.status_code, requests.codes.created)

        with self.subTest("Created returned when uploading a file with same payload, and different FQID"):
            resp = self._put_file(source_url, str(uuid4()), version)
            self.assertEqual(resp.status_code, requests.codes.created)

        with self.subTest(f"OK returned when uploading a file with the same payload, UUID, version"):
            resp = self._put_file(source_url, file_uuid, version)
            self.assertEqual(resp.status_code, requests.codes.ok)

        with self.subTest(f"Conflict returned when uploading a file with a different payload and same FQID"):
            source_url_temp = self._checksum_and_stage_file(io.BytesIO(os.urandom(128)), 128)
            resp = self._put_file(source_url_temp, file_uuid, version)
            self.assertEqual(resp.status_code, requests.codes.conflict)

        with self.subTest(f"Bad request returned when uploading a file with an invalid version"):
            resp = self._put_file(source_url_temp, str(uuid4()), "")
            self.assertEqual(resp.status_code, requests.codes.bad_request)

        invalid_version = 'ABCD'
        with self.subTest(f"Bad request returned when uploading a file with invalid version {invalid_version}"):
            resp = self._put_file(source_url_temp, str(uuid4()), invalid_version)
            self.assertEqual(resp.status_code, requests.codes.bad_request)

        invalid_uuids = ['ABCD', '1234']
        for invalid_uuid in invalid_uuids:
            with self.subTest(f"Bad request returned when uploading a file with invalid UUID {invalid_uuid}"):
                resp = self._put_file(source_url, invalid_uuid, version)
                self.assertEqual(resp.status_code, requests.codes.bad_request)

        # TODO: Figure out why UUID validation throws 500
        # with self.subTest(f"Forbidden returned when uploading a file with without UUID {invalid_uuid}"):
        #     resp = self._put_file(source_url, "", version)
        #     self.assertEqual(resp.status_code, requests.codes.forbidden)

    def test_file_head(self):
        source_url = self._checksum_and_stage_file(io.BytesIO(os.urandom(1024)), 1024)
        uuid = str(uuid4())
        version = datetime_to_version_format(datetime.datetime.utcnow())
        self._put_file(source_url, uuid, version)
        # TODO: check header values in response
        # headers = {'X-DSS-CREATOR-UID': ,
        #            'X-DSS-VERSION':,
        #            'X-DSS-CONTENT-TYPE': ,
        #            'X-DSS-SIZE': ,
        #            'X-DSS-CRC32C': ,
        #            'X-DSS-S3-ETAG': ,
        #            'X-DSS-SHA1': ,
        #            'X-DSS-SHA256': ,
        #            }
        resp = self.client.head(
            f"/v1/files/{uuid}?version={version}",
            headers={
                'Content-Type': "application/json"
            }
        )
        self.assertEqual(resp.status_code, requests.codes.ok)
        # TODO: check header values in response
        # for h in headers:
        #     print(resp.headers[h])

    def test_file_get(self):
        size = 1024
        source_url = self._checksum_and_stage_file(io.BytesIO(os.urandom(size)), size)
        uuid = str(uuid4())
        version = datetime_to_version_format(datetime.datetime.utcnow())
        latest_version = datetime_to_version_format(datetime.datetime.utcnow())
        self._put_file(source_url, uuid, version)
        self._put_file(source_url, uuid, latest_version)

        with self.subTest("Get specific file"):
            resp = self.client.get(
                f"/v1/files/{uuid}?version={version}",
                headers={
                    'Content-Type': "application/json"
                }
            )
            self.assertEqual(resp.status_code, requests.codes.found)
            url = resp.headers['Location']
            data = requests.get(url)
            self.assertEqual(len(data.content), size)
            self.assertEqual(resp.headers['X-DSS-SIZE'], str(size))

        with self.subTest("Get latest file"):
            resp = self.client.get(
                f"/v1/files/{uuid}",
                headers={
                    'Content-Type': "application/json"
                }
            )

        with self.subTest("Get file that doesn't exist"):
            resp = self.client.get(
                f"/v1/files/{uuid4()}",
                headers={
                    'Content-Type': "application/json"
                }
            )
            self.assertEqual(resp.status_code, requests.codes.not_found)

    def _put_file(self, source_url, uuid, version):
        resp = self.client.put(
            f"/v1/files/{uuid}?version={version}",
            data=json.dumps(dict(creator_uid=123, source_url=source_url)),
            headers={
                'Content-Type': "application/json"
            }
        )
        return resp

    def _checksum_and_stage_file(self,
                                 file_handle: typing.BinaryIO,
                                 size: int,
                                 content_type: str = "application/octet-stream"):
        key = f"staging/{uuid4()}"
        chunk_size = get_s3_multipart_chunk_size(size)
        with ChecksummingSink(write_chunk_size=chunk_size) as sink:
            data = file_handle.read()
            sink.write(data)
            sums = sink.get_checksums()

        metadata = dict()
        metadata['hca-dss-crc32c'] = sums['crc32c'].lower()
        metadata['hca-dss-s3_etag'] = sums['s3_etag'].lower()
        metadata['hca-dss-sha1'] = sums['sha1'].lower()
        metadata['hca-dss-sha256'] = sums['sha256'].lower()

        with io.BytesIO(data) as fh:
            self.handle.upload_file_handle(self.staging_bucket, key, fh, content_type, metadata)

        return f"gs://{self.staging_bucket}/{key}"

if __name__ == '__main__':
    unittest.main()
