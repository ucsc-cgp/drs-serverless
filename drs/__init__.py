import os
import base64
import json
import logging

from flask import Flask, jsonify, request
from flask_cors import cross_origin
from six.moves import http_client

import connexion.apis.abstract
import connexion
from connexion.resolver import RestyResolver

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
    app.add_api("../drs-api.yml", base_path=os.environ['DRS_API_VERSION'], resolver=RestyResolver("drs.api"))
    app.add_error_handler(Exception, unexpected_error)
    return app
