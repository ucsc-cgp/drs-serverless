import os
import base64
import json
import requests
import logging
import functools
import traceback

from flask import jsonify
from six.moves import http_client

import werkzeug.exceptions
import connexion.apis.abstract
from connexion.apis.flask_api import FlaskApi
from connexion.decorators.validation import ParameterValidator, RequestBodyValidator
from connexion.lifecycle import ConnexionResponse
import connexion
from connexion.resolver import RestyResolver
from connexion.exceptions import OAuthProblem, OAuthResponseProblem, OAuthScopeProblem
from jsonschema import draft4_format_checker
from flask import Response as FlaskResponse
from werkzeug.exceptions import Forbidden

from drs.util.version import datetime_to_version_format


logger = logging.getLogger(__name__)


class DRSApp(connexion.App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def common_error_handler(exception):
        """
        Generally, each route handler should be decorated with @dss_handler, which manages exceptions. The two cases
        that fail are:

        1. handlers that are not decorated.
        2. handlers that return a code that is not in the swagger spec.

        In both cases, the exception would be punted here, and we return this very generic error that also happens to
        bypass all validation.
        """
        problem = {
            'status': requests.codes.server_error,
            'code': "unhandled_exception",
            'title': str(exception),
            'stacktrace': traceback.format_exc(),
        }
        if isinstance(exception, (OAuthProblem, OAuthResponseProblem, OAuthScopeProblem, Forbidden)):
            problem['status'] = exception.code
            problem['code'] = exception.__class__.__name__
            problem['title'] = exception.description
        return FlaskApi.get_response(ConnexionResponse(
            status_code=problem['status'],
            mimetype="application/problem+json",
            content_type="application/problem+json",
            body=problem,
        ))


class DRSException(Exception):
    def __init__(self, status: int, code: str, title: str, *args, **kwargs) -> None:
        super().__init__(*args)  # , **kwargs)
        self.status = status
        self.code = code
        self.message = title


class DSSBindingException(DRSException):
    def __init__(self, title, *args, **kwargs) -> None:
        super().__init__(requests.codes.bad_request, "illegal_arguments", title, *args, **kwargs)


def drs_exception_handler(e: DRSException) -> FlaskResponse:
    return FlaskResponse(
        status=e.status,
        mimetype="application/problem+json",
        content_type="application/problem+json",
        response=json.dumps({
            'status': e.status,
            'code': e.code,
            'title': e.message,
            'stacktrace': traceback.format_exc(),
        }))


def unexpected_error(e):
    """Handle exceptions by returning swagger-compliant json."""
    logging.exception('An error occured while processing the request.')
    response = jsonify({
        'code': http_client.INTERNAL_SERVER_ERROR,
        'message': 'Exception: {}'.format(e)})
    response.status_code = http_client.INTERNAL_SERVER_ERROR
    return response


def drs_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except werkzeug.exceptions.HTTPException as ex:
            status = ex.code
            code = ex.name
            title = str(ex)
            stacktrace = traceback.format_exc()
            headers = None
        except DRSException as ex:
            status = ex.status
            code = ex.code
            title = ex.message
            stacktrace = traceback.format_exc()
            headers = None
        except Exception as ex:
            status = requests.codes.server_error
            code = "unhandled_exception"
            title = str(ex)
            stacktrace = traceback.format_exc()
            headers = None
        logger.error(stacktrace)

        return ConnexionResponse(
            status_code=status,
            mimetype="application/problem+json",
            content_type="application/problem+json",
            headers=headers,
            body={
                'status': status,
                'code': code,
                'title': title,
                'stacktrace': stacktrace,
            })

    return wrapper


@draft4_format_checker.checks('DSS_VERSION')
def is_DSS_VERSION(val):
    """
    Verifies `val` is compliant with expected format. See for more info on connexion custom type formats
    https://connexion.readthedocs.io/en/latest/cookbook.html#custom-type-format.
    :param val: the value to verify
    :return: the verified value
    """
    from iso8601 import iso8601
    # convert it to date-time so we can format exactly as the system requires (with microsecond precision)
    try:
        timestamp = iso8601.parse_date(val)
    except iso8601.ParseError:
        raise DRSException(
            requests.codes.bad_request,
            "illegal_version",
            f"version should be an RFC3339 compliant timestamp")
    timestamp = datetime_to_version_format(timestamp)
    if timestamp != val:
        raise DRSException(
            requests.codes.bad_request,
            "illegal_version",
            f"version should be a DSS_VERSION with the format 'YYYY-MM-DDTHHmmSS.zzzzzzZ'")
    return val


class DSSParameterValidator(ParameterValidator):
    """
    The ParameterValidator provided by Connexion immediately returns a value if the validation fails.  Therefore, our
    code is never invoked, and the common_error_handler in the connexion.App object is never called.  This means error
    messsages are not returned using our standard error formats.

    The solution is to trap the validation results, and if it fails, exit the validation flow.  We catch the exception
    at the top level where the various validators are called, and return a value according to our specs.
    """

    @staticmethod
    def validate_parameter(*args, **kwargs):
        result = ParameterValidator.validate_parameter(*args, **kwargs)
        if result is not None:
            raise DSSBindingException(result)
        return result

    def __call__(self, function):
        origwrapper = super().__call__(function)

        @functools.wraps(origwrapper)
        def wrapper(request):
            try:
                return origwrapper(request)
            except DSSBindingException as ex:
                status = ex.status
                code = ex.code
                title = ex.message
                stacktrace = traceback.format_exc()

                return FlaskApi.get_response(ConnexionResponse(
                    status_code=status,
                    mimetype="application/problem+json",
                    content_type="application/problem+json",
                    body={
                        'status': status,
                        'code': code,
                        'title': title,
                        'stacktrace': stacktrace,
                    },
                ))

        return wrapper


class DSSRequestBodyValidator(RequestBodyValidator):
    """
    The RequestBodyValidator provided by Connexion immediately returns a value if the validation fails.  Therefore, our
    code is never invoked, and the common_error_handler in the connexion.App object is never called.  This means error
    messsages are not returned using our standard error formats.

    The solution is to trap the validation results, and if it fails, exit the validation flow.  We catch the exception
    at the top level where the various validators are called, and return a value according to our specs.
    """

    def validate_schema(self, *args, **kwargs):
        result = super().validate_schema(*args, **kwargs)
        if result is not None:
            raise DSSBindingException(result.body['detail'])
        return result

    def __call__(self, function):
        origwrapper = super().__call__(function)

        @functools.wraps(origwrapper)
        def wrapper(request):
            try:
                return origwrapper(request)
            except DSSBindingException as ex:
                status = ex.status
                code = ex.code
                title = ex.message
                stacktrace = traceback.format_exc()

                return FlaskApi.get_response(ConnexionResponse(
                    status_code=status,
                    mimetype="application/problem+json",
                    content_type="application/problem+json",
                    body={
                        'status': status,
                        'code': code,
                        'title': title,
                        'stacktrace': stacktrace,
                    },
                ))

        return wrapper


def create_app():
    app = DRSApp(
        __name__,
        validator_map={
            'body': DSSRequestBodyValidator,
            'parameter': DSSParameterValidator,
        },
    )
    base_path = "/" + os.environ['DRS_API_VERSION']
    app.add_api("../drs-api.yml", base_path=base_path, resolver=RestyResolver("drs.api"))
    app.add_error_handler(DRSException, drs_exception_handler)
    return app
