import boto3
import pandas as pd
import pytest

from municipalities.app import municipalities_data


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
        if TableName == "municipalities_table":
            return {
                "Items": [
                    {
                        "row_number": {"N": "1"},
                        "GEOID": {"S": "12345647890"},
                        "GEOID_Y2K": {"S": "12345647890"},
                        "first_year": {"S": "2000"},
                        "final_year": {"S": "2022"},
                        "county": {"S": "Foo County"},
                        "municipality": {"S": "Foo town"},
                    },
                ]
            }
        else:
            raise Exception("table not found")

    boto_client_scan_mock(scanner)


def test_build_municipalities_table_1(boto_client_scan_mock):
    """build_municipalities_table basic test. We include spurious columns to test
    additional types"""
    boto_client_scan_mock(
        {
            "Items": [
                {
                    "row_number": {"N": "1"},
                    "GEOID": {"S": "1111111110"},
                    "GEOID_Y2K": {"S": "1111111111"},
                    "first_year": {"S": "2000"},
                    "final_year": {"S": "2022"},
                    "county": {"S": "Foo County"},
                    "municipality": {"S": "Foo town"},
                    "flag": {"BOOL": True},
                    "string_list": {"SS": ["a", "b", "c"]},
                },
                {
                    "row_number": {"N": "2"},
                    "GEOID": {"S": "2222222220"},
                    "GEOID_Y2K": {"S": "2222222222"},
                    "first_year": {"S": "2001"},
                    "final_year": {"S": "2021"},
                    "county": {"S": "Bar County"},
                    "municipality": {"S": "Bar town"},
                    "flag": {"BOOL": False},
                    "string_list": {"SS": ["1", "2"]},
                },
            ]
        }
    )
    expected = pd.DataFrame(
        {
            "row_number": [1, 2],
            "GEOID": ["1111111110", "2222222220"],
            "GEOID_Y2K": ["1111111111", "2222222222"],
            "first_year": [2000, 2001],
            "final_year": [2022, 2021],
            "county": ["Foo County", "Bar County"],
            "municipality": ["Foo town", "Bar town"],
            "flag": [True, False],
            "string_list": [{"a", "b", "c"}, {"1", "2"}],
        }
    )
    result = municipalities_data.build_municipalities_table("foo")
    pd.testing.assert_frame_equal(expected, result)


def test_build_municipalities_table_2(boto_client_scan_mock):
    """build_municipalities_table inconsistent structure"""
    boto_client_scan_mock(
        {
            "Items": [
                {
                    "row_number": {"N": "1"},
                    "GEOID": {"S": "1111111110"},
                    "GEOID_Y2K": {"S": "1111111111"},
                    "first_year": {"S": "2000"},
                    "final_year": {"S": "2022"},
                    "county": {"S": "Foo County"},
                    "municipality": {"S": "Foo town"},
                },
                {
                    "row_number": {"N": "2"},
                    "GEOID": {"S": "2222222220"},
                    "GEOID_Y2K": {"S": "2222222222"},
                    "first_year": {"S": "2001"},
                    "final_year": {"S": "2021"},
                    "county": {"S": "Bar County"},
                    "municipality_2": {"S": "Bar town"},
                },
            ]
        }
    )
    expected = pd.DataFrame(
        {
            "row_number": [1, 2],
            "GEOID": ["1111111110", "2222222220"],
            "GEOID_Y2K": ["1111111111", "2222222222"],
            "first_year": [2000, 2001],
            "final_year": [2022, 2021],
            "county": ["Foo County", "Bar County"],
            "municipality": ["Foo town", None],
            "municipality_2": [None, "Bar town"],
        }
    )
    result = municipalities_data.build_municipalities_table("foo")
    pd.testing.assert_frame_equal(expected, result)


def test_build_municipalities_table_3(boto_client_scan_mock):
    """build_municipalities_table missing GEOID_Y2K"""
    boto_client_scan_mock(
        {
            "Items": [
                {
                    "row_number": {"N": "1"},
                    "GEOID": {"S": "1111111110"},
                    "first_year": {"S": "2000"},
                    "final_year": {"S": "2022"},
                    "county": {"S": "Foo County"},
                    "municipality": {"S": "Foo town"},
                    "flag": {"BOOL": True},
                    "string_list": {"SS": ["a", "b", "c"]},
                },
                {
                    "row_number": {"N": "2"},
                    "GEOID": {"S": "2222222220"},
                    "first_year": {"S": "2001"},
                    "final_year": {"S": "2021"},
                    "county": {"S": "Bar County"},
                    "municipality": {"S": "Bar town"},
                    "flag": {"BOOL": False},
                    "string_list": {"SS": ["1", "2"]},
                },
            ]
        }
    )
    with pytest.raises(KeyError):
        municipalities_data.build_municipalities_table("foo")


def test_get_municipalities_table_1():
    """get_municipalities_table returns table that already exists"""
    tbl = pd.DataFrame(
        {
            "x": [
                1,
            ]
        }
    )
    municipalities_data.municipalities_table = tbl
    result = municipalities_data.get_municipalities_table()
    pd.testing.assert_frame_equal(tbl, result)


def test_get_municipalities_table_2(monkeypatch, table_name_mock):
    """get_municipalities_table fetches table by name"""
    municipalities_data.municipalities_table = None
    monkeypatch.setenv("TABLE_MUNICIPALITIES", "municipalities_table")
    result = municipalities_data.get_municipalities_table()
    expected = pd.DataFrame(
        {
            "row_number": [1],
            "GEOID": ["12345647890"],
            "GEOID_Y2K": ["12345647890"],
            "first_year": [2000],
            "final_year": [2022],
            "county": ["Foo County"],
            "municipality": ["Foo town"],
        }
    )
    pd.testing.assert_frame_equal(expected, result)


def test_get_municipalities_table_3(monkeypatch, table_name_mock):
    """get_municipalities_table throws exception on name mismatch"""
    municipalities_data.municipalities_table = None
    monkeypatch.setenv("TABLE_COUNTIES", "municipalities_table_wrong")
    with pytest.raises(Exception):
        municipalities_data.get_municipalities_table()
