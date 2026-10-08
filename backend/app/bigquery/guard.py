"""Decides whether a query may run, based on BigQuery's own dry-run analysis.

We don't parse SQL ourselves: the dry run reports the statement type and the bytes
the query would scan, which is more reliable than matching keywords.
"""


class QueryRejected(Exception):
    pass


def check_dry_run(statement_type: str, bytes_processed: int, max_bytes: int) -> None:
    if statement_type != "SELECT":
        raise QueryRejected(
            f"Only single SELECT statements are allowed (got {statement_type})."
        )
    if bytes_processed > max_bytes:
        raise QueryRejected(
            f"Query would scan {bytes_processed / 1e9:.1f} GB, over the "
            f"{max_bytes / 1e9:.1f} GB limit. Select fewer columns or narrow the "
            "date range with _TABLE_SUFFIX."
        )
