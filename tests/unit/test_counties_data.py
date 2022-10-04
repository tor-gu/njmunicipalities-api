import boto3
import pandas as pd
import pytest

from counties.app import counties_data


@pytest.fixture
def boto_client_scan_mock(monkeypatch):
    """This is a mock that takes a an argument, 'scan', which can either be the
    a function that replaces client.scan(TableName), or else the return value of
    such a function.
    """

    def _boto_backend(scan):
        class MockClient:
            @staticmethod
            def scan(TableName):
                if callable(scan):
                    return scan(TableName)
                else:
                    return scan

        def mock_client(*args, **kwargs):
            return MockClient()

        monkeypatch.setattr(boto3, "client", mock_client)

    return _boto_backend


@pytest.fixture
def table_name_mock(boto_client_scan_mock):
    """Return a table only if table name matches 'counties_table'"""

    def scanner(TableName=None):
        if TableName == "counties_table":
            return {
                "Items": [
                    {
                        "row_number": {"N": "1"},
                        "GEOID": {"S": "12345"},
                    },
                ]
            }
        else:
            raise Exception("table not found")

    boto_client_scan_mock(scanner)


def test_build_counties_table_1(boto_client_scan_mock):
    """build_counties_table basic test. We include spurious columns to test
    additional types"""
    boto_client_scan_mock(
        {
            "Items": [
                {
                    "row_number": {"N": "1"},
                    "GEOID": {"S": "12345"},
                    "county": {"S": "Foo County"},
                    "flag": {"BOOL": True},
                    "string_list": {"SS": ["a", "b", "c"]},
                },
                {
                    "row_number": {"N": "2"},
                    "GEOID": {"S": "54321"},
                    "county": {"S": "Bar County"},
                    "flag": {"BOOL": False},
                    "string_list": {"SS": ["1", "2"]},
                },
            ]
        }
    )
    expected = pd.DataFrame(
        {
            "row_number": [1, 2],
            "GEOID": ["12345", "54321"],
            "county": ["Foo County", "Bar County"],
            "flag": [True, False],
            "string_list": [{"a", "b", "c"}, {"1", "2"}],
        }
    )
    result = counties_data.build_counties_table("foo")
    pd.testing.assert_frame_equal(expected, result)


def test_build_counties_table_2(boto_client_scan_mock):
    """build_counties_table inconsistent structure"""
    boto_client_scan_mock(
        {
            "Items": [
                {
                    "row_number": {"N": "1"},
                    "GEOID": {"S": "12345"},
                    "county": {"S": "Foo County"},
                },
                {
                    "row_number": {"N": "2"},
                    "GEOID": {"S": "54321"},
                    "county_2": {"S": "Bar County"},
                },
            ]
        }
    )
    expected = pd.DataFrame(
        {
            "row_number": [1, 2],
            "GEOID": ["12345", "54321"],
            "county": ["Foo County", None],
            "county_2": [None, "Bar County"],
        }
    )
    result = counties_data.build_counties_table("foo")
    pd.testing.assert_frame_equal(expected, result)


def test_build_counties_table_3(boto_client_scan_mock):
    """build_counties_table missing GEOID"""
    boto_client_scan_mock(
        {
            "Items": [
                {
                    "row_number": {"N": "1"},
                    "county": {"S": "Foo County"},
                },
                {
                    "row_number": {"N": "2"},
                    "county": {"S": "Bar County"},
                },
            ]
        }
    )
    with pytest.raises(KeyError):
        counties_data.build_counties_table("foo")


def test_get_counties_table_1():
    """get_counties_table returns table that already exists"""
    tbl = pd.DataFrame(
        {
            "x": [
                1,
            ]
        }
    )
    counties_data.counties_table = tbl
    result = counties_data.get_counties_table()
    pd.testing.assert_frame_equal(tbl, result)


def test_get_counties_table_2(monkeypatch, table_name_mock):
    """get_counties_table fetches table by name"""
    counties_data.counties_table = None
    monkeypatch.setenv("TABLE_COUNTIES", "counties_table")
    result = counties_data.get_counties_table()
    expected = pd.DataFrame({"row_number": [1], "GEOID": ["12345"]})
    pd.testing.assert_frame_equal(expected, result)


def test_get_counties_table_3(monkeypatch, table_name_mock):
    """get_counties_table throws exception on name mismatch"""
    counties_data.counties_table = None
    monkeypatch.setenv("TABLE_COUNTIES", "counties_table_wrong")
    with pytest.raises(Exception):
        counties_data.get_counties_table()
