import traceback
from http import HTTPStatus

from util import un_none

from torguapi import (
    TorguapiInvalidRequest,
    torguapi_get_page_parameters,
    torguapi_http_error,
    torguapi_make_links_and_meta,
    torguapi_result,
)

from .counties_data import get_counties_table
from .counties_lib import CountiesNotFoundError, handle_get_counties, handle_get_county


def process_counties_params(event):
    """
    Gets path and query params from API Gateway event and does initial processing

    Args:
        event: API Gateway event

    Returns:
        HTTPStatus
        Error message (or None, if HTTPStatus.OK)
        dict of processed parameters
    """
    path_parameters = un_none(event["pathParameters"], {})
    query_parameters = un_none(event["queryStringParameters"], {})
    try:
        params = torguapi_get_page_parameters(query_parameters)
    except TorguapiInvalidRequest as e:
        return HTTPStatus.BAD_REQUEST, str(e), {}
    GEOID = path_parameters.get("GEOID", None)
    if GEOID is not None:
        params["GEOID"] = GEOID
    return HTTPStatus.OK, None, params


def make_counties_path(aux):
    """Returns path to be passed to torguapi_result"""
    if "GEOID" in aux:
        return f"nj/counties/{aux['GEOID']}"
    return "nj/counties"


def return_counties_table(result_set, aux):
    """Assemble, path and meta, and pass to torguapi_result"""
    path = make_counties_path(aux)
    links, meta = torguapi_make_links_and_meta(aux, path)
    return torguapi_result(result_set, links, meta)


def counties_handler(event, context):
    """
    Handles counties API events

    Always returns a torguapi HTTP result

    Args:
        event: API Gateway event
        context: API Gateway context

    Returns:
        A torguapi HTTP resultset response or error response
    """
    try:
        counties = get_counties_table()
    except Exception:
        traceback.print_exc()
        return torguapi_http_error(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
        )

    status_code, status_message, params = process_counties_params(event)
    if status_code != HTTPStatus.OK:
        return torguapi_http_error(status_code, status_message)
    try:
        if "GEOID" not in params:
            result_set, aux = handle_get_counties(counties, params)
        else:
            result_set, aux = handle_get_county(counties, params)
        return return_counties_table(result_set, aux)

    except CountiesNotFoundError as e:
        return torguapi_http_error(HTTPStatus.NOT_FOUND, str(e))
    except Exception:
        traceback.print_exc()
        return torguapi_http_error(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
        )
