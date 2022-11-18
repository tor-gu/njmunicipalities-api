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

from .municipalities_data import get_municipalities_table
from .municipalities_lib import (
    DEFAULT_YEAR,
    MunicipalitiesNotFoundError,
    handle_get_municipalities,
    handle_get_municipality,
    handle_get_xrefs,
)


def process_municipality_params(event):
    """
    Gets path and query params from API Gateway municipalities event and does
    initial processing

    Args:
        event: Municipalities API Gateway event

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
    year = path_parameters.get("year", None)
    GEOID = path_parameters.get("GEOID", None)
    if year is not None:
        if not year.isnumeric():
            return HTTPStatus.BAD_REQUEST, "Invalid year " + year, params
        else:
            params["year"] = int(year)
    if GEOID is not None:
        params["GEOID"] = GEOID
    return HTTPStatus.OK, None, params


def process_xref_params(event):
    """
    Gets path and query params from API Gateway XREFs event and does initial processing

    Args:
        event: Municipality XREFs API Gateway event

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

    year = path_parameters.get("year", None)
    year_ref = path_parameters.get("year_ref", None)
    if year is not None:
        if not year.isnumeric():
            return HTTPStatus.BAD_REQUEST, "Invalid year " + year, params
        else:
            params["year"] = int(year)
    if year_ref is not None:
        if not year_ref.isnumeric():
            return HTTPStatus.BAD_REQUEST, "Invalid reference year " + year_ref, params
        else:
            params["year_ref"] = int(year_ref)
    return HTTPStatus.OK, None, params


def make_municipalities_path(aux):
    """Returns path to be passed to torguapi_result"""
    year = aux.get("year", DEFAULT_YEAR)
    path = f"nj/municipalities/{year}"
    if "GEOID" in aux:
        path = f"{path}/{aux['GEOID']}"
    return path


def make_xref_path(aux):
    """Returns path to be passed to torguapi_result"""
    year = aux["year"]
    year_ref = aux["year_ref"]
    return f"nj/municipality_xrefs/{year_ref}/{year}"


def return_municipalities_table(result_set, aux):
    """Assemble, path and meta, and pass to torguapi_result"""
    path = make_municipalities_path(aux)
    links, meta = torguapi_make_links_and_meta(aux, path)
    return torguapi_result(result_set, links, meta)


def return_xref_table(result_set, aux):
    """Assemble, path and meta, and pass to torguapi_result"""
    path = make_xref_path(aux)
    links, meta = torguapi_make_links_and_meta(aux, path)
    return torguapi_result(result_set, links, meta)


def municipalities_handler(event, context):
    """
    Handles municipalities API events

    Always returns a torguapi HTTP result

    Args:
        event: API Gateway event
        context: API Gateway context

    Returns:
        A torguapi HTTP resultset response or error response
    """
    try:
        municipalities = get_municipalities_table()
    except Exception:
        traceback.print_exc()
        return torguapi_http_error(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
        )

    status_code, status_message, params = process_municipality_params(event)
    if status_code != HTTPStatus.OK:
        return torguapi_http_error(status_code, status_message)

    try:
        if "GEOID" not in params:
            result_set, aux = handle_get_municipalities(municipalities, params)
        else:
            result_set, aux = handle_get_municipality(municipalities, params)
        return return_municipalities_table(result_set, aux)
    except MunicipalitiesNotFoundError as e:
        return torguapi_http_error(HTTPStatus.NOT_FOUND, str(e))
    except Exception:
        traceback.print_exc()
        return torguapi_http_error(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
        )


def xref_handler(event, context):
    """
    Handles municipality XREFs API events

    Always returns a torguapi HTTP result

    Args:
        event: API Gateway event
        context: API Gateway context

    Returns:
        A torguapi HTTP resultset response or error response
    """
    try:
        municipalities = get_municipalities_table()
    except Exception:
        traceback.print_exc()
        return torguapi_http_error(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
        )

    status_code, status_message, params = process_xref_params(event)
    if status_code != HTTPStatus.OK:
        return torguapi_http_error(status_code, status_message)
    try:
        result_set, aux = handle_get_xrefs(municipalities, params)
        return return_xref_table(result_set, aux)
    except MunicipalitiesNotFoundError as e:
        return torguapi_http_error(HTTPStatus.NOT_FOUND, str(e))
    except Exception:
        traceback.print_exc()
        return torguapi_http_error(
            HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"
        )
