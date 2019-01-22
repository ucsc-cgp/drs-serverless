# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Endpoints sample application.

Demonstrates how to create a simple echo API as well as how to deal with
various authentication methods.
"""

import base64
import json
import logging

from flask import Flask, jsonify, request
from flask_cors import cross_origin
from six.moves import http_client

import connexion.apis.abstract
import connexion
from connexion.resolver import RestyResolver


#@app.errorhandler(http_client.INTERNAL_SERVER_ERROR)
def unexpected_error(e):
    """Handle exceptions by returning swagger-compliant json."""
    logging.exception('An error occured while processing the request.')
    response = jsonify({
        'code': http_client.INTERNAL_SERVER_ERROR,
        'message': 'Exception: {}'.format(e)})
    response.status_code = http_client.INTERNAL_SERVER_ERROR
    return response


def create_app():
    app = connexion.FlaskApp(__name__)
    app.add_api("../drs-api.yml", resolver=RestyResolver("drs.api"))
    app.add_error_handler(Exception, unexpected_error)
    return app
