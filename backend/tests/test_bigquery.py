from datetime import date
from decimal import Decimal

import pytest

from app.bigquery.client import _to_json_value
from app.bigquery.guard import QueryRejected, check_dry_run

GB = 1_000_000_000


def test_select_within_budget_is_allowed():
    check_dry_run("SELECT", 1 * GB, max_bytes=3 * GB)


@pytest.mark.parametrize("statement_type", ["SCRIPT", "INSERT", "DELETE", "DROP_TABLE", "MERGE"])
def test_non_select_statements_are_rejected(statement_type):
    with pytest.raises(QueryRejected, match="Only single SELECT"):
        check_dry_run(statement_type, 0, max_bytes=3 * GB)


def test_query_over_byte_budget_is_rejected():
    with pytest.raises(QueryRejected, match="3.6 GB"):
        check_dry_run("SELECT", int(3.6 * GB), max_bytes=3 * GB)


def test_values_are_converted_to_json_safe_types():
    row = [Decimal("12.5"), date(2020, 12, 1), float("nan"), [Decimal("1")], {"n": Decimal("2")}]
    assert [_to_json_value(value) for value in row] == [12.5, "2020-12-01", None, [1.0], {"n": 2.0}]
