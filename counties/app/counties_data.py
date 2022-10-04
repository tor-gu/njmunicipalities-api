import os

import boto3
from ddblib import ddb_itemlist_to_pd

# Cached result of build
counties_table = None


def get_counties_table():
    """Return cached result, or build from DynamoDB"""
    global counties_table
    if counties_table is None:
        table_name = os.environ.get("TABLE_COUNTIES")
        counties_table = build_counties_table(table_name)
    return counties_table


def build_counties_table(table_name):
    """Scan counties table and convert to dataframe"""
    client = boto3.client("dynamodb")
    data = client.scan(TableName=table_name)
    counties = ddb_itemlist_to_pd(data["Items"], ["row_number"]).sort_values("GEOID")
    return counties
