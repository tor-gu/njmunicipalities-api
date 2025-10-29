import numpy
import pandas as pd
import pytest

from municipalities.app import municipalities_lib


@pytest.fixture()
def municipality_table():
    """ "Table of municipalities"""

    df_len = 4
    return pd.DataFrame(
        {
            "row_number": list(range(1, df_len + 1)),
            "county": ["county name"] * df_len,
            "GEOID_Y2K": ["0001", "0001", "0002", "0003"],
            "GEOID": ["0001", "9001", "0002", "0003"],
            "first_year": [2000, 2010, 2000, 2000],
            "final_year": [2009, 2021, 2021, 2015],
            "municipality": ["a", "b", "c", "d"],
        }
    ).set_index("row_number")


def test_handle_get_municipalities_page_1(municipality_table):
    """ "Test filtering out later years"""

    result_set, aux = municipalities_lib.handle_get_municipalities(
        municipality_table, {"year": 2000}
    )
    assert list(result_set.GEOID) == ["0001", "0002", "0003"]


def test_handle_get_municipalities_page_2(municipality_table):
    """ "Test filtering out earlier years"""

    result_set, aux = municipalities_lib.handle_get_municipalities(
        municipality_table, {"year": 2021}
    )
    assert list(result_set.GEOID) == ["9001", "0002"]


def test_handle_get_municipalities_page_3(municipality_table):
    """ "Out of range years"""

    with pytest.raises(municipalities_lib.MunicipalitiesNotFoundError):
        municipalities_lib.handle_get_municipalities(municipality_table, {"year": 1999})

    with pytest.raises(municipalities_lib.MunicipalitiesNotFoundError):
        municipalities_lib.handle_get_municipalities(municipality_table, {"year": 2025})


def test_handle_get_municipalities_page_4(municipality_table):
    """ "Non-numeric year"""

    with pytest.raises(TypeError):
        municipalities_lib.handle_get_municipalities(
            municipality_table, {"year": "foo"}
        )


def test_handle_get_municipality_1(municipality_table):
    """ "Municipality that exists at late edge of specified range"""

    result_set, aux = municipalities_lib.handle_get_municipality(
        municipality_table, {"year": 2009, "GEOID": "0001"}
    )
    assert list(result_set.GEOID) == ["0001"]


def test_handle_get_municipality_2(municipality_table):
    """ "Municipality that exists at early edge of specified range"""

    result_set, aux = municipalities_lib.handle_get_municipality(
        municipality_table, {"year": 2010, "GEOID": "9001"}
    )
    assert list(result_set.GEOID) == ["9001"]


def test_handle_get_municipality_3(municipality_table):
    """ "Municipality that does not exist at specified year"""

    with pytest.raises(municipalities_lib.MunicipalitiesNotFoundError):
        municipalities_lib.handle_get_municipality(
            municipality_table, {"year": 2009, "GEOID": "9001"}
        )


def test_handle_get_xrefs_1(municipality_table):
    """ "Early ref year"""

    result_set, aux = municipalities_lib.handle_get_xrefs(
        municipality_table, {"year": 2021, "year_ref": 2000}
    )
    assert list(result_set.GEOID) == ["9001", "0002"]
    assert list(result_set.GEOID_ref) == ["0001", "0002"]


def test_handle_get_xrefs_2(municipality_table):
    """ "Late ref year"""

    result_set, aux = municipalities_lib.handle_get_xrefs(
        municipality_table, {"year": 2000, "year_ref": 2021}
    )
    assert list(result_set.GEOID) == ["0001", "0002", "0003"]
    assert list(result_set.GEOID_ref) == ["9001", "0002", numpy.nan]


def test_handle_get_xrefs_3(municipality_table):
    """ "No data for year"""

    with pytest.raises(municipalities_lib.MunicipalitiesNotFoundError):
        municipalities_lib.handle_get_xrefs(
            municipality_table, {"year": 1999, "year_ref": 2021}
        )


def test_handle_get_xrefs_4(municipality_table):
    """ "No data for ref year"""

    with pytest.raises(municipalities_lib.MunicipalitiesNotFoundError):
        municipalities_lib.handle_get_xrefs(
            municipality_table, {"year": 2000, "year_ref": 1999}
        )
