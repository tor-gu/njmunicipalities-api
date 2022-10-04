import os

import boto3
from ddblib import ddb_itemlist_to_pd

# Cached result of build
municipalities_table = None


def get_municipalities_table():
    """Return cached result, or build from DynamoDB"""
    global municipalities_table
    if municipalities_table is None:
        table_name = os.environ.get("TABLE_MUNICIPALITIES")
        municipalities_table = build_municipalities_table(table_name)
    return municipalities_table


def build_municipalities_table(table_name):
    """Scan municipalities table and convert to dataframe"""
    client = boto3.client("dynamodb")
    data = client.scan(TableName=table_name)
    municipalities = (
        ddb_itemlist_to_pd(data["Items"], ["row_number"])
        .assign(first_year=lambda df: df["first_year"].map(lambda year: int(year)))
        .assign(final_year=lambda df: df["final_year"].map(lambda year: int(year)))
        .sort_values("GEOID_Y2K")
    )
    return municipalities
