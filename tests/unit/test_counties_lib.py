import pandas as pd
import pytest

from counties.app import counties_lib


@pytest.fixture
def counties_table():
    df_size = 15
    rows = list(range(1, df_size + 1))

    return pd.DataFrame(
        {
            "row_number": rows,
            "GEOID": [str(10000 + row) for row in rows],
            "county": [f"County {row}" for row in rows],
        }
    )


def test_get_counties_1(counties_table):
    """get_counties basic test"""
    result_set, aux = counties_lib.handle_get_counties(counties_table, {})
    expected_result = counties_table[["GEOID", "county"]]
    pd.testing.assert_frame_equal(expected_result, result_set)
    expected_aux = {
        "page_size": 100,
        "page_number": 1,
        "record_count": len(counties_table),
    }
    assert expected_aux == aux


def test_get_counties_2(counties_table):
    """get_counties basic pagination test"""
    params = {"page_size": 5, "page_number": 2, "extra_param": "foo"}
    result_set, aux = counties_lib.handle_get_counties(counties_table, params)
    expected_result = counties_table[
        (counties_table["row_number"] > 5) & (counties_table["row_number"] < 11)
    ][["GEOID", "county"]]
    pd.testing.assert_frame_equal(expected_result, result_set)
    expected_aux = {
        "page_size": 5,
        "page_number": 2,
        "record_count": len(counties_table),
    }
    assert expected_aux == aux


def test_get_counties_3(counties_table):
    """get_counties out-of-range pagination (high)"""
    params = {"page_size": 5, "page_number": 4}
    with pytest.raises(counties_lib.CountiesNotFoundError):
        counties_lib.handle_get_counties(counties_table, params)


def test_get_counties_4(counties_table):
    """get_counties out-of-range pagination (low)"""
    params = {"page_size": 5, "page_number": 0}
    with pytest.raises(counties_lib.CountiesNotFoundError):
        counties_lib.handle_get_counties(counties_table, params)


def test_get_county_1(counties_table):
    """ "get_county basic test"""
    params = {"GEOID": "10005"}
    result, aux = counties_lib.handle_get_county(counties_table, params)
    assert len(result) == 1
    assert result.iloc[0]["GEOID"] == "10005"
    assert "GEOID" in aux
    assert aux["GEOID"] == "10005"


def test_get_county_2(counties_table):
    """get_county not found"""
    params = {"GEOID": "10099"}
    with pytest.raises(counties_lib.CountiesNotFoundError):
        counties_lib.handle_get_county(counties_table, params)
