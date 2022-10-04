from decimal import Decimal

import pandas as pd
import pytest

from common_layer import ddblib


@pytest.fixture()
def ddb_itemlist():
    return [
        {
            "str": {"S": "value_1"},
            "float": {"N": "1.5"},
            "int_1": {"N": "1"},
            "int_2": {"N": "1"},
        },
        {
            "str": {"S": "value_2"},
            "float": {"N": "2.5"},
            "int_1": {"N": "2"},
            "int_2": {"N": "2"},
        },
    ]


def test_ddb_decimal_to_numeric_1():
    """ddb_decimal_to_numeric integral decimals converted to float"""
    val = 3
    decimal_val = Decimal(val)
    result = ddblib.ddb_decimal_to_numeric("", decimal_val, set())
    assert type(result) is float
    assert result == val


def test_ddb_decimal_to_numeric_2():
    """ddb_decimal_to_numeric non-integral decimals converted to float"""
    val = 3.5
    decimal_val = Decimal(val)
    result = ddblib.ddb_decimal_to_numeric("", decimal_val, set())
    assert type(result) is float
    assert result == val


def test_ddb_decimal_to_numeric_3():
    """ddb_decimal_to_numeric integral decimals converted to if indicated by optional param"""
    val = 3
    decimal_val = Decimal(val)
    result = ddblib.ddb_decimal_to_numeric("key", decimal_val, ["key"])
    assert type(result) is int
    assert result == val


def test_ddb_decimal_to_numeric_4():
    """ddb_decimal_to_numeric non-decimals pass through gracefully"""
    val = "str"
    result = ddblib.ddb_decimal_to_numeric("key", val, ["key"])
    assert type(result) is type(val)
    assert result == val


def test_ddb_item_to_py_1():
    """ddb_item_to_py handles strings"""
    ddb_item = {"key": {"S": "value"}}
    py_item = ddblib.ddb_item_to_py(ddb_item, set())
    assert py_item == {"key": "value"}


def test_ddb_item_to_py_2():
    """ddb_item_to_py handles numerics"""
    ddb_item = {"key": {"N": "5"}}
    py_item = ddblib.ddb_item_to_py(ddb_item, set())
    assert py_item == {"key": 5}
    assert type(py_item["key"]) is float


def test_ddb_item_to_py_3():
    """ddb_item_to_py handles numerics specified as integers"""
    ddb_item = {"key": {"N": "5"}}
    py_item = ddblib.ddb_item_to_py(ddb_item, ["key"])
    assert type(py_item["key"]) is int


def test_itemlist_to_py_1(ddb_itemlist):
    """ "ddb_itemlist_to_py basic test"""
    pylist = ddblib.ddb_itemlist_to_py(ddb_itemlist, ["int_1"])
    expected = [
        {"str": "value_1", "float": 1.5, "int_1": 1.0, "int_2": 1},
        {"str": "value_2", "float": 2.5, "int_1": 2.0, "int_2": 2},
    ]
    assert expected == pylist


def test_itemlist_to_pd_1(ddb_itemlist):
    """ "ddb_itemlist_to_pd basic test"""
    tbl = ddblib.ddb_itemlist_to_pd(ddb_itemlist, ["int_1"])
    expected = pd.DataFrame(
        {
            "str": ["value_1", "value_2"],
            "float": [1.5, 2.5],
            "int_1": [1, 2],
            "int_2": [1.0, 2.0],
        }
    )
    pd.testing.assert_frame_equal(expected, tbl)
