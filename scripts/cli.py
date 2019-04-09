#!/usr/bin/env python

import io
import os
import sys
import argparse
import mimetypes
import json
import requests
import datetime
from uuid import uuid4

from urllib.parse import urlencode
from dcplib.s3_multipart import get_s3_multipart_chunk_size
from dcplib.checksumming_io import ChecksummingSink

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from drs.util.version import datetime_to_version_format
from drs.storage import get_blobstore_handle

blobstore_handle = get_blobstore_handle()
staging_bucket = os.environ['DRS_BUCKET_TEST']

def put_file(source_url, uuid, version=None):
    if version is None:
        version = datetime_to_version_format(datetime.datetime.utcnow())
    resp = requests.put(
        f"https://{os.environ['API_DOMAIN_NAME']}/v1/files/{uuid}?version={version}",
        data=json.dumps(dict(creator_uid=123, source_url=source_url)),
        headers={
            'Content-Type': "application/json"
        }
    )
    return resp

def checksum_and_stage_file(file_handle, size, content_type="application/octet-stream"):
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
        blobstore_handle.upload_file_handle(staging_bucket, key, fh, content_type, metadata)

    return f"gs://{staging_bucket}/{key}"

def upload_file(path, uuid, version=None):
    mt = mimetypes.MimeTypes()
    content_type = mt.guess_type(path)[0]
    size = os.path.getsize(args.path)
    with open(args.path, "rb") as f:
        source_url = checksum_and_stage_file(f, size, content_type)
    resp = put_file(source_url, uuid, version)
    print(uuid, resp.json()['version'])

def download_file(local_path, uuid, version=None):
    url = f"https://{os.environ['API_DOMAIN_NAME']}/v1/files/{uuid}"
    if version is not None:
        url += f"?version={version}"
    resp = requests.get(url)
    with open(local_path, "wb") as fh:
        fh.write(resp.content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="command", dest="command")

    upload_parser = subparsers.add_parser("upload")
    upload_parser.add_argument("path", default=None)
    upload_parser.add_argument("--uuid", default=str(uuid4()))
    upload_parser.add_argument("--version", default=None)

    download_parser = subparsers.add_parser("download")
    download_parser.add_argument("path", default=None)
    download_parser.add_argument("--uuid", required=True)
    download_parser.add_argument("--version", default=None)

    args = parser.parse_args()
    if "upload" == args.command:
        upload_file(args.path, args.uuid, args.version)
    elif "download" == args.command:
        download_file(args.path, args.uuid, args.version)
