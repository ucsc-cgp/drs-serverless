import datetime
import json
import logging
import os
import re
import time
import typing
from enum import Enum, auto
from uuid import uuid4

import requests
from cloud_blobstore import BlobAlreadyExistsError, BlobNotFoundError
from dcplib.s3_multipart import AWS_MIN_CHUNK_SIZE
from flask import jsonify, make_response, redirect, request

from drs import DRSException, drs_handler
from drs import storage
from drs.storage.files import write_file_metadata
from drs.storage import FileMetadata, HCABlobStore, compose_blob_key
from drs.util.version import datetime_to_version_format


logger = logging.getLogger(__name__)


@drs_handler
def head(uuid: str, version: str = None, token: str = None):
    return get_helper(uuid, version, token)


@drs_handler
def get(uuid: str, version: str = None, token: str = None):
    return get_helper(uuid, version, token)


def get_helper(uuid: str, version: str = None, token: str = None):
    handle = storage.get_blobstore_handle()
    bucket = os.environ['DRS_BUCKET']

    if version is None:
        # list the files and find the one that is the most recent.
        prefix = "files/{}.".format(uuid)
        for matching_file in handle.list(bucket, prefix):
            matching_file = matching_file[len(prefix):]
            if version is None or matching_file > version:
                version = matching_file

    if version is None:
        # no matches!
        raise DRSException(404, "not_found", "Cannot find file!")

    # retrieve the file metadata.
    key = f"files/{uuid}.{version}"
    try:
        file_metadata = json.loads(handle.get(bucket, key).decode("utf-8"))
    except BlobNotFoundError:
        raise DRSException(404, "not_found", "Cannot find file!")

    blob_path = compose_blob_key(file_metadata)

    if request.method == "GET":
        url = f"https://storage.googleapis.com/{bucket}/{blob_path}"
        response = redirect(url)
    else:
        response = make_response('', 200)

    headers = response.headers
    headers['X-DSS-CREATOR-UID'] = file_metadata[FileMetadata.CREATOR_UID]
    headers['X-DSS-VERSION'] = version
    headers['X-DSS-CONTENT-TYPE'] = file_metadata[FileMetadata.CONTENT_TYPE]
    headers['X-DSS-SIZE'] = file_metadata[FileMetadata.SIZE]
    headers['X-DSS-CRC32C'] = file_metadata[FileMetadata.CRC32C]
    headers['X-DSS-S3-ETAG'] = file_metadata[FileMetadata.S3_ETAG]
    headers['X-DSS-SHA1'] = file_metadata[FileMetadata.SHA1]
    headers['X-DSS-SHA256'] = file_metadata[FileMetadata.SHA256]

    return response


@drs_handler
def put(uuid: str, json_request_body: dict, version: str):
    class CopyMode(Enum):
        NO_COPY = auto()
        COPY_INLINE = auto()
        COPY_ASYNC = auto()

    uuid = uuid.lower()
    source_url = json_request_body['source_url']
    cre = re.compile(
        "^"
        "(?P<schema>(?:s3|gs|wasb))"
        "://"
        "(?P<bucket>[^/]+)"
        "/"
        "(?P<key>.+)"
        "$")
    mobj = cre.match(source_url)
    if mobj and mobj.group('schema') == "gs":
        pass
    else:
        schema = mobj.group('schema')
        raise DRSException(
            requests.codes.bad_request,
            "unknown_source_schema",
            f"source_url schema {schema} not supported")

    handle = storage.get_blobstore_handle()
    hca_handle = storage.DRSHCABlobstore(handle)
    dst_bucket = os.environ['DRS_BUCKET']

    src_bucket = mobj.group('bucket')
    src_key = mobj.group('key')

    metadata = handle.get_user_metadata(src_bucket, src_key)
    size = handle.get_size(src_bucket, src_key)
    content_type = handle.get_content_type(src_bucket, src_key)

    try:
        # format all the checksums so they're lower-case.
        for metadata_spec in HCABlobStore.MANDATORY_STAGING_METADATA.values():
            if metadata_spec['downcase']:
                keyname = typing.cast(str, metadata_spec['keyname'])
                metadata[keyname] = metadata[keyname].lower()
    except KeyError:
        raise DRSException(
            requests.codes.unprocessable,
            "missing_checksum",
            f"mssing {keyname}")

    # what's the target object name for the actual data?
    dst_key = ("blobs/" + ".".join(
        (
            metadata['hca-dss-sha256'],
            metadata['hca-dss-sha1'],
            metadata['hca-dss-s3_etag'],
            metadata['hca-dss-crc32c'],
        )
    )).lower()

    # does it exist? if so, we can skip the copy part.
    copy_mode = CopyMode.COPY_INLINE
    try:
        if hca_handle.verify_blob_checksum_from_staging_metadata(dst_bucket, dst_key, metadata):
            copy_mode = CopyMode.NO_COPY
    except BlobNotFoundError:
        pass

    # build the json document for the file metadata.
    file_metadata = {
        FileMetadata.FORMAT: FileMetadata.FILE_FORMAT_VERSION,
        FileMetadata.CREATOR_UID: json_request_body['creator_uid'],
        FileMetadata.VERSION: version,
        FileMetadata.CONTENT_TYPE: content_type,
        FileMetadata.SIZE: size,
        FileMetadata.CRC32C: metadata['hca-dss-crc32c'],
        FileMetadata.S3_ETAG: metadata['hca-dss-s3_etag'],
        FileMetadata.SHA1: metadata['hca-dss-sha1'],
        FileMetadata.SHA256: metadata['hca-dss-sha256'],
    }
    file_metadata_json = json.dumps(file_metadata)

    if copy_mode != CopyMode.NO_COPY:
        handle.copy(src_bucket, src_key, dst_bucket, dst_key)
        # verify the copy was done correctly.
        assert hca_handle.verify_blob_checksum_from_staging_metadata(dst_bucket, dst_key, metadata)

    try:
        write_file_metadata(handle, dst_bucket, uuid, version, file_metadata_json)
        status_code = requests.codes.created
    except BlobAlreadyExistsError:
        # fetch the file metadata, compare it to what we have.
        key = f"files/{uuid}.{version}"
        existing_file_metadata = json.loads(
            handle.get(dst_bucket, key).decode("utf-8"))
        if existing_file_metadata != file_metadata:
            raise DRSException(
                requests.codes.conflict,
                "file_already_exists",
                f"file with UUID {uuid} and version {version} already exists")
        status_code = requests.codes.ok

    return jsonify(
        dict(version=version)), status_code
