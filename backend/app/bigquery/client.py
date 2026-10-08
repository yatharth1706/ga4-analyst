import json
import math
import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery
from google.oauth2 import service_account

from app.bigquery.guard import QueryRejected, check_dry_run
from app.config import Settings

LOCATION = "US"
MAX_BYTES_BILLED = 3_000_000_000  # a full scan is 3.6 GB; the heaviest realistic query ~1.4 GB
TIMEOUT_SECONDS = 30
MAX_ROWS = 500  # rows fetched per query: shown in the UI table and used for charts


class QueryError(Exception):
    """A query failed or was rejected. The message is safe to show the model and the user."""


@dataclass
class Column:
    name: str
    type: str


@dataclass
class QueryResult:
    columns: list[Column]
    rows: list[list[Any]]
    row_count: int
    bytes_processed: int
    duration_ms: int

    @property
    def truncated(self) -> bool:
        return self.row_count > len(self.rows)


class BigQueryRunner:
    def __init__(self, settings: Settings):
        self._client = bigquery.Client(
            project=settings.gcp_project, location=LOCATION, credentials=_credentials(settings)
        )

    def run(self, sql: str) -> QueryResult:
        started = time.monotonic()
        try:
            dry_run = self._client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
            check_dry_run(dry_run.statement_type, dry_run.total_bytes_processed, MAX_BYTES_BILLED)
            job = self._client.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    maximum_bytes_billed=MAX_BYTES_BILLED, job_timeout_ms=TIMEOUT_SECONDS * 1000
                ),
            )
            rows = job.result(timeout=TIMEOUT_SECONDS, max_results=MAX_ROWS)
            columns = [_column(field) for field in rows.schema]
            values = [[_to_json_value(value) for value in row.values()] for row in rows]
        except QueryRejected as error:
            raise QueryError(str(error)) from error
        except FuturesTimeoutError as error:
            raise QueryError(f"Query exceeded the {TIMEOUT_SECONDS}s time limit.") from error
        except GoogleAPICallError as error:
            raise QueryError(_error_reason(error)) from error

        return QueryResult(
            columns=columns,
            rows=values,
            row_count=rows.total_rows or 0,
            bytes_processed=job.total_bytes_processed or 0,
            duration_ms=round((time.monotonic() - started) * 1000),
        )


def _credentials(settings: Settings) -> service_account.Credentials | None:
    """Deployed: key JSON from an env var. Local: None, so the client uses GOOGLE_APPLICATION_CREDENTIALS."""
    if not settings.gcp_service_account_json:
        return None
    return service_account.Credentials.from_service_account_info(
        json.loads(settings.gcp_service_account_json)
    )


def _column(field: bigquery.SchemaField) -> Column:
    field_type = f"ARRAY<{field.field_type}>" if field.mode == "REPEATED" else field.field_type
    return Column(name=field.name, type=field_type)


def _error_reason(error: GoogleAPICallError) -> str:
    # error.message includes the request URL and project; the structured reason doesn't.
    details = getattr(error, "errors", None) or []
    if details and details[0].get("message"):
        return details[0]["message"]
    return error.message or "BigQuery request failed."


def _to_json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json_value(item) for key, item in value.items()}
    return value
