import json
from http import HTTPStatus

import pandas as pd
import pytest

from municipalities.app import municipalities_api


@pytest.fixture()
def apigw_event_get_base():
    """Generates API GW Event"""

    return {
        "body": "",
        "resource": "/{proxy+}",
        "requestContext": {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": "/{proxy+}",
            "httpMethod": "GET",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "identity": {
                "apiKey": "",
                "userArn": "",
                "cognitoAuthenticationType": "",
                "caller": "",
                "userAgent": "Custom User Agent String",
                "user": "",
                "cognitoIdentityPoolId": "",
                "cognitoIdentityId": "",
                "cognitoAuthenticationProvider": "",
                "sourceIp": "127.0.0.1",
                "accountId": "",
            },
            "stage": "prod",
        },
        "queryStringParameters": {"foo": "bar"},
        "headers": {
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Mobile-Viewer": "false",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "CloudFront-Viewer-Country": "US",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-Port": "443",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "X-Forwarded-Proto": "https",
            "X-Amz-Cf-Id": "aaaaaaaaaae3VYQb9jd-nvCd-de396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "CloudFront-Is-Tablet-Viewer": "false",
            "Cache-Control": "max-age=0",
            "User-Agent": "Custom User Agent String",
            "CloudFront-Forwarded-Proto": "https",
            "Accept-Encoding": "gzip, deflate, sdch",
        },
        "pathParameters": None,
        "httpMethod": "GET",
        "stageVariables": {"baz": "qux"},
        "path": "/examplepath",
    }


@pytest.fixture()
def apigw_event_get_municipalities(apigw_event_get_base):
    """Generates API GW Event for municipalities"""

    return apigw_event_get_base


@pytest.fixture()
def apigw_event_get_xrefs(apigw_event_get_base):
    """Generates API GW Event"""

    event = apigw_event_get_base
    event["pathParameters"] = {"year_ref": "2000", "year": "2010"}
    return event


@pytest.fixture()
def municipalities_table():
    df_len = 5
    rows = list(range(1, df_len + 1))
    return pd.DataFrame(
        {
            "row_number": rows,
            "GEOID_Y2K": [
                "0000000000",
                "0000000001",
                "0000000001",
                "0000000001",
                "0000000002",
            ],
            "GEOID": [
                "0000000000",
                "0000000001",
                "0000000011",
                "0000000021",
                "0000000002",
            ],
            "first_year": [2000, 2000, 2005, 2010, 2000],
            "final_year": [2025, 2004, 2009, 2025, 2025],
            "county": ["County A", "County B", "County B", "County B", "County C"],
            "municipality": ["Town A", "Town B1", "Town B2", "Town B2", "Town C"],
        }
    )


@pytest.fixture
def municipalities_table_backend(monkeypatch, municipalities_table):
    """ "A municipalities table as a dataframe"""

    def mock_build_municipalities_table(table_name):
        return municipalities_table

    monkeypatch.setattr(
        "municipalities.app.municipalities_data.build_municipalities_table",
        mock_build_municipalities_table,
    )


def test_municipality_handler_1(
    apigw_event_get_municipalities, municipalities_table_backend
):
    """ "municipalities_handler basic test"""
    ret = municipalities_api.municipalities_handler(apigw_event_get_municipalities, "")
    body = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "data" in body
    assert "links" in body
    assert "meta" in body
    data = body["data"]
    meta = body["meta"]
    expected_data = [
        {
            "year": 2025,
            "GEOID": "0000000000",
            "county": "County A",
            "municipality": "Town A",
        },
        {
            "year": 2025,
            "GEOID": "0000000021",
            "county": "County B",
            "municipality": "Town B2",
        },
        {
            "year": 2025,
            "GEOID": "0000000002",
            "county": "County C",
            "municipality": "Town C",
        },
    ]
    assert expected_data == data
    assert "record_count" in meta
    assert meta["record_count"] == 3


def test_municipality_handler_2(
    apigw_event_get_municipalities, municipalities_table_backend
):
    """ "municipalities_handler non-default year"""
    apigw_event_get_municipalities["pathParameters"] = {"year": "2009"}
    ret = municipalities_api.municipalities_handler(apigw_event_get_municipalities, "")
    body = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "data" in body
    assert "links" in body
    assert "meta" in body
    data = body["data"]
    meta = body["meta"]
    expected_data = [
        {
            "year": 2009,
            "GEOID": "0000000000",
            "county": "County A",
            "municipality": "Town A",
        },
        {
            "year": 2009,
            "GEOID": "0000000011",
            "county": "County B",
            "municipality": "Town B2",
        },
        {
            "year": 2009,
            "GEOID": "0000000002",
            "county": "County C",
            "municipality": "Town C",
        },
    ]
    assert expected_data == data
    assert "record_count" in meta
    assert meta["record_count"] == 3


def test_municipality_handler_3(
    apigw_event_get_municipalities, municipalities_table_backend
):
    """ "municipalities_handler year out of range"""
    apigw_event_get_municipalities["pathParameters"] = {"year": "1999"}
    ret = municipalities_api.municipalities_handler(apigw_event_get_municipalities, "")
    body = json.loads(ret["body"])

    assert ret["statusCode"] == HTTPStatus.NOT_FOUND
    assert "errors" in body


def test_xref_handler_1(apigw_event_get_xrefs, municipalities_table_backend):
    """xref_handler basic test"""
    ret = municipalities_api.xref_handler(apigw_event_get_xrefs, "")
    body = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "data" in body
    assert "links" in body
    assert "meta" in body
    data = body["data"]
    meta = body["meta"]
    expected_data = [
        {
            "GEOID": "0000000000",
            "GEOID_ref": "0000000000",
            "year": 2010,
            "year_ref": 2000,
        },
        {
            "GEOID": "0000000021",
            "GEOID_ref": "0000000001",
            "year": 2010,
            "year_ref": 2000,
        },
        {
            "GEOID": "0000000002",
            "GEOID_ref": "0000000002",
            "year": 2010,
            "year_ref": 2000,
        },
    ]
    assert expected_data == data
    assert meta["record_count"] == 3


def test_return_xref_table_1():
    """return_xref_table basic test"""
    aux = {"year": 2005, "year_ref": 2006}
    xref_result_set = pd.DataFrame(
        {
            "GEOID": ["000000000"],
            "GEOID_ref": ["000000000"],
            "year": [2005],
            "year_ref": [2006],
        }
    )
    result = municipalities_api.return_xref_table(xref_result_set, aux)
    assert "headers" in result
    assert "statusCode" in result
    assert "body" in result
    body = json.loads(result["body"])
    assert "data" in body
    data = pd.DataFrame(body["data"])
    pd.testing.assert_frame_equal(xref_result_set, data)


def test_return_xref_table_2():
    """return_xref_table empty result"""
    aux = {"year": 2005, "year_ref": 2006}
    xref_result_set = pd.DataFrame(
        {"GEOID": [], "GEOID_ref": [], "year": [], "year_ref": []}
    )
    result = municipalities_api.return_xref_table(xref_result_set, aux)
    assert "headers" in result
    assert "statusCode" in result
    assert "body" in result
    assert result["statusCode"] == HTTPStatus.NOT_FOUND


def test_return_return_municipalities_table_1():
    """return_municipalities_table basic test"""
    aux = {"year": 2005}
    municipality_result_set = pd.DataFrame(
        {
            "year": [2005],
            "GEOID": ["000000000"],
            "county": ["County X"],
            "municipality": ["Town Y"],
        }
    )
    result = municipalities_api.return_municipalities_table(
        municipality_result_set, aux
    )
    assert "headers" in result
    assert "statusCode" in result
    assert "body" in result
    body = json.loads(result["body"])
    assert "data" in body
    data = pd.DataFrame(body["data"])
    pd.testing.assert_frame_equal(municipality_result_set, data)


def test_return_return_municipalities_table_2():
    """return_municipalities_table empty result"""
    aux = {"year": 2005}
    municipality_result_set = pd.DataFrame(
        {"year": [], "GEOID": [], "county": [], "municipality": []}
    )
    result = municipalities_api.return_municipalities_table(
        municipality_result_set, aux
    )
    assert "headers" in result
    assert "statusCode" in result
    assert "body" in result
    assert "body" in result
    assert result["statusCode"] == HTTPStatus.NOT_FOUND


def test_make_municipalities_path_1():
    """make_municipalities_path year and GEOID not specified"""
    aux = {}
    path = municipalities_api.make_municipalities_path(aux)
    assert "nj/municipalities/2025" == path


def test_make_municipalities_path_2():
    """make_municipalities_path year and GEOID specified"""
    aux = {"year": 2010, "GEOID": "9999999999"}
    path = municipalities_api.make_municipalities_path(aux)
    assert "nj/municipalities/2010/9999999999" == path


def test_make_xref_path_1():
    """make_xref_path basic test"""
    aux = {"year": 2010, "year_ref": 2011}
    path = municipalities_api.make_xref_path(aux)
    assert "nj/municipality_xrefs/2011/2010" == path


def test_process_xref_params_1(apigw_event_get_xrefs):
    """process_xref_params without page params"""
    status, message, params = municipalities_api.process_xref_params(
        apigw_event_get_xrefs
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 100, "year": 2010, "year_ref": 2000} == params


def test_process_xref_params_2(apigw_event_get_xrefs):
    """process_xref_params with page params"""
    apigw_event_get_xrefs["queryStringParameters"] = {
        "page_size": "10",
        "page_number": "2",
    }
    status, message, params = municipalities_api.process_xref_params(
        apigw_event_get_xrefs
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 10, "page_number": 2, "year": 2010, "year_ref": 2000} == params


def test_process_xref_params_3(apigw_event_get_xrefs):
    """process_xref_params with bad pagination params"""
    apigw_event_get_xrefs["queryStringParameters"] = {
        "page_size": "x",
        "page_number": "2",
    }
    status, message, params = municipalities_api.process_xref_params(
        apigw_event_get_xrefs
    )
    assert HTTPStatus.BAD_REQUEST == status
    assert message is not None


def test_process_municipality_params_1(apigw_event_get_municipalities):
    """process_municipality_params with no params"""
    status, message, params = municipalities_api.process_municipality_params(
        apigw_event_get_municipalities
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 100} == params


def test_process_municipality_params_2(apigw_event_get_municipalities):
    """process_municipality_params year and GEOID"""
    apigw_event_get_municipalities["pathParameters"] = {
        "year": "2010",
        "GEOID": "0000000000",
    }
    status, message, params = municipalities_api.process_municipality_params(
        apigw_event_get_municipalities
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 100, "year": 2010, "GEOID": "0000000000"} == params


def test_process_municipality_params_3(apigw_event_get_municipalities):
    """process_municipality_params invalid year"""
    apigw_event_get_municipalities["pathParameters"] = {
        "year": "bad",
        "GEOID": "0000000000",
    }
    status, message, params = municipalities_api.process_municipality_params(
        apigw_event_get_municipalities
    )
    assert HTTPStatus.BAD_REQUEST == status
    assert message is not None


def test_process_municipality_params_4(apigw_event_get_municipalities):
    """process_municipality_params with pagination"""
    apigw_event_get_municipalities["pathParameters"] = {"year": "2011"}
    apigw_event_get_municipalities["queryStringParameters"] = {
        "page_size": "10",
        "page_number": "2",
    }
    status, message, params = municipalities_api.process_municipality_params(
        apigw_event_get_municipalities
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 10, "page_number": 2, "year": 2011} == params


def test_process_municipality_params_5(apigw_event_get_municipalities):
    """process_municipality_params with bad pagination params"""
    apigw_event_get_municipalities["pathParameters"] = {"year": "2011"}
    apigw_event_get_municipalities["queryStringParameters"] = {
        "page_size": "10",
        "page_number": "foo",
    }
    status, message, params = municipalities_api.process_municipality_params(
        apigw_event_get_municipalities
    )
    assert HTTPStatus.BAD_REQUEST == status
    assert message is not None
