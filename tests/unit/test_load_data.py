import pytest

from scripts import load_data

COLUMNS = ["row_number", "GEOID", "county"]


def item(row_number, geoid, county):
    return {
        "row_number": {"N": str(row_number)},
        "GEOID": {"S": geoid},
        "county": {"S": county},
    }


class MockClient:
    """Stands in for a boto3 DynamoDB client: scan returns pages of items,
    batch_write_item records requests and can report some as unprocessed"""

    def __init__(self, pages=None, unprocessed=None):
        self.pages = pages or [[]]
        self.unprocessed = list(unprocessed or [])
        self.batches = []

    def scan(self, TableName, ExclusiveStartKey=None):
        page = 0 if ExclusiveStartKey is None else ExclusiveStartKey["page"]
        response = {"Items": self.pages[page]}
        if page + 1 < len(self.pages):
            response["LastEvaluatedKey"] = {"page": page + 1}
        return response

    def batch_write_item(self, RequestItems):
        self.batches.append(RequestItems)
        if self.unprocessed:
            return {"UnprocessedItems": self.unprocessed.pop(0)}
        return {"UnprocessedItems": {}}


@pytest.fixture
def write_csv(tmp_path):
    def _write_csv(text):
        path = tmp_path / "counties.csv"
        path.write_text(text)
        return str(path)

    return _write_csv


def test_row_to_item_types():
    """row_to_item key is N and every other attribute is S, including numbers"""
    row = {"row_number": "3", "GEOID": "34001", "first_year": "2000"}
    assert load_data.row_to_item(row) == {
        "row_number": {"N": "3"},
        "GEOID": {"S": "34001"},
        "first_year": {"S": "2000"},
    }


def test_read_csv_items(write_csv):
    """read_csv_items keys items by integer row_number"""
    path = write_csv(
        "row_number,GEOID,county\n1,34001,Atlantic County\n2,34003,Bergen County\n"
    )
    assert load_data.read_csv_items(path, COLUMNS) == {
        1: item(1, "34001", "Atlantic County"),
        2: item(2, "34003", "Bergen County"),
    }


def test_read_csv_items_wrong_columns(write_csv):
    """read_csv_items refuses a CSV whose columns don't match the table"""
    path = write_csv("row_number,GEOID,municipality\n1,34001,Absecon city\n")
    with pytest.raises(ValueError, match="expected columns"):
        load_data.read_csv_items(path, COLUMNS)


def test_read_csv_items_duplicate_key(write_csv):
    """read_csv_items refuses duplicate row_numbers"""
    path = write_csv(
        "row_number,GEOID,county\n1,34001,Atlantic County\n1,34003,Bergen County\n"
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_data.read_csv_items(path, COLUMNS)


def test_read_csv_items_empty(write_csv):
    """read_csv_items refuses an empty CSV, which would delete every row"""
    path = write_csv("row_number,GEOID,county\n")
    with pytest.raises(ValueError, match="no rows"):
        load_data.read_csv_items(path, COLUMNS)


def test_scan_items_paginates():
    """scan_items follows LastEvaluatedKey across pages"""
    client = MockClient(pages=[[item(1, "34001", "A")], [item(2, "34003", "B")]])
    assert load_data.scan_items(client, "counties") == {
        1: item(1, "34001", "A"),
        2: item(2, "34003", "B"),
    }


def test_plan_changes_no_op():
    """plan_changes with identical data plans nothing"""
    data = {1: item(1, "34001", "A"), 2: item(2, "34003", "B")}
    assert load_data.plan_changes(data, dict(data)) == ([], [])


def test_plan_changes_put_and_delete():
    """plan_changes puts new and changed rows and deletes missing ones"""
    live = {
        1: item(1, "34001", "A"),
        2: item(2, "34003", "B"),
        3: item(3, "34005", "C"),
    }
    desired = {
        1: item(1, "34001", "A"),
        2: item(2, "34003", "B2"),
        4: item(4, "34007", "D"),
    }
    puts, deletes = load_data.plan_changes(desired, live)
    assert puts == [item(2, "34003", "B2"), item(4, "34007", "D")]
    assert deletes == [{"row_number": {"N": "3"}}]


def test_plan_changes_type_mismatch():
    """plan_changes rewrites an item whose attribute has the wrong type"""
    live = {
        1: {"row_number": {"N": "1"}, "GEOID": {"N": "34001"}, "county": {"S": "A"}}
    }
    desired = {1: item(1, "34001", "A")}
    assert load_data.plan_changes(desired, live) == ([item(1, "34001", "A")], [])


def test_batch_write_chunks():
    """batch_write sends at most 25 requests per batch"""
    client = MockClient()
    requests = [{"PutRequest": {"Item": item(i, "x", "y")}} for i in range(60)]
    load_data.batch_write(client, "counties", requests)
    assert [len(batch["counties"]) for batch in client.batches] == [25, 25, 10]


def test_batch_write_retries_unprocessed(monkeypatch):
    """batch_write resends unprocessed items"""
    monkeypatch.setattr(load_data.time, "sleep", lambda seconds: None)
    retry = {"counties": [{"PutRequest": {"Item": item(1, "x", "y")}}]}
    client = MockClient(unprocessed=[retry])
    load_data.batch_write(
        client, "counties", [{"PutRequest": {"Item": item(1, "x", "y")}}]
    )
    assert client.batches[1] == retry
    assert len(client.batches) == 2


def test_batch_write_gives_up(monkeypatch):
    """batch_write raises if items stay unprocessed"""
    monkeypatch.setattr(load_data.time, "sleep", lambda seconds: None)
    retry = {"counties": [{"PutRequest": {"Item": item(1, "x", "y")}}]}
    client = MockClient(unprocessed=[retry] * load_data.MAX_RETRIES)
    with pytest.raises(RuntimeError, match="unprocessed"):
        load_data.batch_write(
            client, "counties", [{"PutRequest": {"Item": item(1, "x", "y")}}]
        )


def test_load_table_dry_run_writes_nothing(write_csv):
    """load_table with dry_run reports changes but doesn't write"""
    path = write_csv("row_number,GEOID,county\n1,34001,A\n")
    client = MockClient(pages=[[item(2, "34003", "B")]])
    puts, deletes = load_data.load_table(
        client, "counties", path, COLUMNS, dry_run=True
    )
    assert (len(puts), len(deletes)) == (1, 1)
    assert client.batches == []


def test_load_table_writes(write_csv):
    """load_table sends puts and deletes in one request list"""
    path = write_csv("row_number,GEOID,county\n1,34001,A\n")
    client = MockClient(pages=[[item(2, "34003", "B")]])
    load_data.load_table(client, "counties", path, COLUMNS, dry_run=False)
    assert client.batches == [
        {
            "counties": [
                {"PutRequest": {"Item": item(1, "34001", "A")}},
                {"DeleteRequest": {"Key": {"row_number": {"N": "2"}}}},
            ]
        }
    ]
