import json
from http import HTTPStatus

import pandas as pd
import pytest

from counties.app import counties_api


# This is an API gateway event for the counties API. We will use variations
# on it to generate several fixtures
@pytest.fixture
def apigw_event_get_counties_base():
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
        "queryStringParameters": None,
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


@pytest.fixture
def apigw_event_get_counties(apigw_event_get_counties_base):
    """Generates API GW Event with no pathParameters"""

    return apigw_event_get_counties_base


@pytest.fixture
def apigw_event_get_county(apigw_event_get_counties_base):
    """Generates API GW Event with GEOID=34009"""
    event = apigw_event_get_counties_base
    event["pathParameters"] = {"GEOID": "34005"}
    return event


@pytest.fixture
def apigw_event_get_non_county(apigw_event_get_counties_base):
    """Generates API GW Event with GEOID=34999"""
    event = apigw_event_get_counties_base
    event["pathParameters"] = {"GEOID": "34999"}
    return event


@pytest.fixture
def apigw_event_get_page_2(apigw_event_get_counties_base):
    """Generates API GW Event with page parameters"""
    event = apigw_event_get_counties_base
    event["queryStringParameters"] = {"page_size": "20", "page_number": "2"}
    return event


@pytest.fixture
def apigw_event_bad_pagination(apigw_event_get_counties_base):
    """Generates API GW Event with page parameters"""
    event = apigw_event_get_counties_base
    event["queryStringParameters"] = {"page_size": "q", "page_number": "z"}
    return event


@pytest.fixture
def counties_table():
    """ "A counties table as a dataframe"""
    df_len = 4
    return pd.DataFrame(
        {
            "row_number": list(range(1, df_len + 1)),
            "GEOID": ["34001", "34003", "34005", "34007"],
            "county": [
                "Atlantic County",
                "Bergen County",
                "Burlington County",
                "Camden County",
            ],
        }
    )


@pytest.fixture
def counties_table_backend(monkeypatch, counties_table):
    """ "A counties table as a dataframe"""

    def mock_build_counties_table(table_name):
        return counties_table

    monkeypatch.setattr(
        "counties.app.counties_data.build_counties_table", mock_build_counties_table
    )


def test_counties_handler_1(
    apigw_event_get_counties, counties_table, counties_table_backend
):
    """counties_handler retrieves all counties"""

    ret = counties_api.counties_handler(apigw_event_get_counties, "")
    body = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "links" in body
    assert "data" in body
    assert "meta" in body
    data = body["data"]
    meta = body["meta"]
    assert {"GEOID": "34001", "county": "Atlantic County"} in data
    assert "record_count" in meta
    assert meta["record_count"] == len(counties_table)


def test_counties_handler_2(apigw_event_get_county, counties_table_backend):
    """counties_handler retrieving a single county"""

    ret = counties_api.counties_handler(apigw_event_get_county, "")
    body = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "links" in body
    assert "data" in body
    data = body["data"]
    assert {"GEOID": "34005", "county": "Burlington County"} in data


def test_counties_handler_3(apigw_event_get_non_county, counties_table_backend):
    """counties_handler retrieving a county that does not exist"""

    ret = counties_api.counties_handler(apigw_event_get_non_county, "")
    json.loads(ret["body"])

    assert ret["statusCode"] == 404


def test_return_counties_table_1(counties_table):
    """return_counties_table basic test"""
    aux = {}
    result = counties_api.return_counties_table(counties_table, aux)
    assert "headers" in result
    assert "statusCode" in result
    assert "body" in result
    body = json.loads(result["body"])
    assert "data" in body
    data = pd.DataFrame(body["data"])
    pd.testing.assert_frame_equal(counties_table, data)


def test_return_counties_table_2():
    """return_counties_table empty result"""
    aux = {}
    result = counties_api.return_counties_table(pd.DataFrame(), aux)
    assert "headers" in result
    assert "statusCode" in result
    assert "body" in result
    assert result["statusCode"] == HTTPStatus.NOT_FOUND


def test_make_counties_path_1():
    """make_counties_path no GEOID"""
    expected = "nj/counties"
    assert expected == counties_api.make_counties_path({})


def test_make_counties_path_2():
    """make_counties_path with GEOID"""
    expected = "nj/counties/12345"
    assert expected == counties_api.make_counties_path({"GEOID": "12345"})


def test_process_counties_params_1(apigw_event_get_counties_base):
    """process_counties_params with no params"""
    status, message, params = counties_api.process_counties_params(
        apigw_event_get_counties_base
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 100} == params  # default value


def test_process_counties_params_2(apigw_event_get_page_2):
    """process_counties_params with page params"""
    status, message, params = counties_api.process_counties_params(
        apigw_event_get_page_2
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_number": 2, "page_size": 20} == params


def test_process_counties_params_3(apigw_event_get_county):
    """process_counties_params with GEOID"""
    status, message, params = counties_api.process_counties_params(
        apigw_event_get_county
    )
    assert HTTPStatus.OK == status
    assert message is None
    assert {"page_size": 100, "GEOID": "34005"} == params  # default value


def test_process_counties_params_4(apigw_event_bad_pagination):
    """process_counties_params with bad pagination params"""
    status, message, params = counties_api.process_counties_params(
        apigw_event_bad_pagination
    )
    assert HTTPStatus.BAD_REQUEST == status
    assert message is not None
