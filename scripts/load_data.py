"""Load the CSVs in data/ into the njmunicipalities DynamoDB tables.

Usage: python scripts/load_data.py [--env-prefix dev-] [--data-dir data] [--dry-run]

Idempotent: rows that are new or changed are put, rows no longer in the CSV are
deleted, and an unchanged table is left alone. Items keep the shape DynamoDB's
CSV import gave them: row_number is N, every other attribute is S.

The load is not atomic. A lambda that cold-starts mid-load can cache a mix of
old and new rows, so the deploy must recycle the lambdas after loading. The
pipeline does this by passing data/SOURCE's version to template.yaml's
DataVersion (see pipeline/buildspec_deploy.yaml).
"""

import argparse
import csv
import os
import sys
import time

import boto3

KEY = "row_number"

# CSV columns expected for each table, checked so a mismatched file can't
# overwrite the wrong table
TABLES = {
    "counties": [KEY, "GEOID", "county"],
    "municipalities": [
        KEY,
        "GEOID_Y2K",
        "GEOID",
        "county",
        "municipality",
        "first_year",
        "final_year",
    ],
}

BATCH_SIZE = 25  # BatchWriteItem limit
MAX_RETRIES = 8


def row_to_item(row):
    """Convert a CSV row (all str) to a DynamoDB item"""
    return {
        name: {"N": value} if name == KEY else {"S": value}
        for name, value in row.items()
    }


def read_csv_items(path, columns):
    """Read a CSV and return {row_number: item}"""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != columns:
            raise ValueError(
                f"{path}: expected columns {columns}, got {reader.fieldnames}"
            )
        items = {}
        for row in reader:
            key = int(row[KEY])
            if key in items:
                raise ValueError(f"{path}: duplicate {KEY} {key}")
            items[key] = row_to_item(row)
    if not items:
        raise ValueError(f"{path}: no rows")
    return items


def scan_items(client, table_name):
    """Scan a table and return {row_number: item}"""
    items = {}
    kwargs = {"TableName": table_name}
    while True:
        response = client.scan(**kwargs)
        for item in response["Items"]:
            items[int(item[KEY]["N"])] = item
        if "LastEvaluatedKey" not in response:
            return items
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def plan_changes(desired, live):
    """Return (puts, deletes): items to write and keys to remove"""
    puts = [item for key, item in sorted(desired.items()) if live.get(key) != item]
    deletes = [{KEY: {"N": str(key)}} for key in sorted(live.keys() - desired.keys())]
    return puts, deletes


def batch_write(client, table_name, requests):
    """Send write requests in batches, retrying unprocessed items"""
    for start in range(0, len(requests), BATCH_SIZE):
        pending = {table_name: requests[start : start + BATCH_SIZE]}
        for attempt in range(MAX_RETRIES):
            response = client.batch_write_item(RequestItems=pending)
            pending = response.get("UnprocessedItems", {})
            if not pending:
                break
            time.sleep(0.1 * 2**attempt)
        else:
            raise RuntimeError(
                f"{table_name}: unprocessed items after {MAX_RETRIES} retries"
            )


def load_table(client, table_name, csv_path, columns, dry_run):
    """Bring one table in line with its CSV and return (puts, deletes)"""
    desired = read_csv_items(csv_path, columns)
    live = scan_items(client, table_name)
    puts, deletes = plan_changes(desired, live)
    action = "would apply" if dry_run else "applying"
    print(
        f"{table_name}: {len(desired)} rows in {csv_path}, {len(live)} in table; "
        f"{action} {len(puts)} puts, {len(deletes)} deletes"
    )
    if not dry_run:
        requests = [{"PutRequest": {"Item": item}} for item in puts]
        requests += [{"DeleteRequest": {"Key": key}} for key in deletes]
        batch_write(client, table_name, requests)
    return puts, deletes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load data/ CSVs into DynamoDB")
    parser.add_argument(
        "--env-prefix", default="", help='table name prefix, e.g. "dev-"'
    )
    parser.add_argument(
        "--data-dir", default="data", help="directory containing the CSVs"
    )
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument(
        "--dry-run", action="store_true", help="report changes without writing"
    )
    args = parser.parse_args(argv)

    client = boto3.client("dynamodb", region_name=args.region)
    for name, columns in TABLES.items():
        load_table(
            client,
            f"{args.env_prefix}{name}",
            os.path.join(args.data_dir, f"{name}.csv"),
            columns,
            args.dry_run,
        )


if __name__ == "__main__":
    sys.exit(main())
