from decimal import Decimal

import pandas as pd
from boto3.dynamodb.types import TypeDeserializer


def ddb_decimal_to_numeric(key, value, integral_keys):
    """Handle Decmimal type, converting to fload or int, as required"""
    if isinstance(value, Decimal):
        if key in integral_keys:
            return int(value)
        return float(value)
    return value


def ddb_item_to_py(ddb_item, integral_keys):
    """Converts DynamoDB single 'Item' to pythonic dict"""
    type_deserializer = TypeDeserializer()
    ds = {key: type_deserializer.deserialize(value) for key, value in ddb_item.items()}
    return {
        key: ddb_decimal_to_numeric(key, value, integral_keys)
        for key, value in ds.items()
    }


def ddb_itemlist_to_py(ddb_itemlist, integral_keys):
    """Converts DynamoDB 'Items' list to list of pythonic dicts"""
    return [ddb_item_to_py(ddb_item, integral_keys) for ddb_item in ddb_itemlist]


def ddb_itemlist_to_pd(ddb_itemlist, integral_keys=set()):
    """
    Converts a DynamoDB 'Items' list to a pd.DataFrame

    By default, numeric columns will be converted to float.  To convert to
    int instead, specify the column name in the integral_keys param.  For example,
    ddb_itemlist_to_pd(ddb_itemlist, ["int_column_1", "int_column_2"])

    Args:
        ddb_itemlist: 'Item' list from DynamoDB
        integral_keys: Optional list of column names to treat as int instead of float

    Returns:
        A pandas DataFram representing the itemlist
    """
    return pd.DataFrame(ddb_itemlist_to_py(ddb_itemlist, integral_keys))
