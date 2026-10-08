from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import date
from decimal import Decimal

import pytest
from google.api_core.exceptions import BadRequest
from google.cloud.bigquery import SchemaField

from app.bigquery.client import MAX_BYTES_BILLED, MAX_ROWS, TIMEOUT_SECONDS, BigQueryRunner, QueryError

GB = 1_000_000_000


class FakeRow:
    def __init__(self, *values):
        self._values = values

    def values(self):
        return self._values


class FakeRows(list):
    schema = [SchemaField("category", "STRING"), SchemaField("revenue", "NUMERIC")]
    total_rows = 3


class FakeJob:
    def __init__(self, statement_type="SELECT", total_bytes_processed=GB, error=None):
        self.statement_type = statement_type
        self.total_bytes_processed = total_bytes_processed
        self.error = error
        self.result_kwargs = None

    def result(self, **kwargs):
        self.result_kwargs = kwargs
        if self.error:
            raise self.error
        return FakeRows([FakeRow("desktop", Decimal("208815.5")), FakeRow("mobile", None)])


class FakeClient:
    """Plays the dry run first, then the real job, and records each job config it was given."""

    def __init__(self, dry_run: FakeJob, job: FakeJob | None = None):
        self._jobs = [dry_run, job or FakeJob()]
        self.configs = []

    def query(self, sql, job_config):
        self.configs.append(job_config)
        job = self._jobs[len(self.configs) - 1]
        if isinstance(job, Exception):
            raise job
        return job


def test_select_runs_after_a_dry_run_with_cost_and_time_limits():
    real_job = FakeJob()
    client = FakeClient(dry_run=FakeJob(), job=real_job)

    result = BigQueryRunner(client).run("SELECT ...")

    dry_run_config, run_config = client.configs
    assert dry_run_config.dry_run is True
    assert run_config.maximum_bytes_billed == MAX_BYTES_BILLED
    assert int(run_config.job_timeout_ms) == TIMEOUT_SECONDS * 1000
    assert real_job.result_kwargs == {"timeout": TIMEOUT_SECONDS, "max_results": MAX_ROWS}
    assert [column.name for column in result.columns] == ["category", "revenue"]
    assert result.rows == [["desktop", 208815.5], ["mobile", None]]
    assert result.row_count == 3


@pytest.mark.parametrize("statement_type", ["SCRIPT", "INSERT", "DELETE", "DROP_TABLE", "MERGE"])
def test_anything_but_a_select_is_rejected_before_it_runs(statement_type):
    client = FakeClient(dry_run=FakeJob(statement_type=statement_type))

    with pytest.raises(QueryError, match="Only single SELECT"):
        BigQueryRunner(client).run("DELETE ...")
    assert len(client.configs) == 1


def test_query_over_the_byte_cap_is_rejected_before_it_runs():
    client = FakeClient(dry_run=FakeJob(total_bytes_processed=int(3.6 * GB)))

    with pytest.raises(QueryError, match="3.6 GB"):
        BigQueryRunner(client).run("SELECT * ...")
    assert len(client.configs) == 1


def test_bigquery_errors_keep_the_reason_but_not_the_request_url():
    error = BadRequest(
        "POST https://bigquery.googleapis.com/projects/my-project/jobs: Unrecognized name: revenue",
        errors=[{"message": "Unrecognized name: revenue at [1:8]"}],
    )
    client = FakeClient(dry_run=error)

    with pytest.raises(QueryError) as raised:
        BigQueryRunner(client).run("SELECT revenue ...")
    assert str(raised.value) == "Unrecognized name: revenue at [1:8]"


def test_slow_query_becomes_a_timeout_error():
    client = FakeClient(dry_run=FakeJob(), job=FakeJob(error=FuturesTimeoutError()))

    with pytest.raises(QueryError, match=f"{TIMEOUT_SECONDS}s time limit"):
        BigQueryRunner(client).run("SELECT ...")


def test_dates_are_returned_as_iso_strings():
    class DateRows(FakeRows):
        schema = [SchemaField("day", "DATE")]
        total_rows = 1

    class DateJob(FakeJob):
        def result(self, **kwargs):
            return DateRows([FakeRow(date(2020, 12, 1))])

    result = BigQueryRunner(FakeClient(dry_run=FakeJob(), job=DateJob())).run("SELECT day ...")

    assert result.rows == [["2020-12-01"]]
