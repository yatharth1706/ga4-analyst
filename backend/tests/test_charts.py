import pytest

from app.agent.tools import ChartError, ExecutedQuery, validate_chart
from tests.fakes import REVENUE_BY_DEVICE, result

TOTAL = result({"revenue": "FLOAT"}, [[362165.0]])
MONTHLY = result({"month": "STRING", "nov": "FLOAT", "dec": "FLOAT"}, [["a", 1.0, 2.0]])
TRUNCATED = result({"day": "STRING", "users": "INTEGER"}, [["d", 1]], row_count=900)
MANY_BARS = result({"item": "STRING", "units": "INTEGER"}, [[str(i), i] for i in range(60)])

QUERIES = {
    query_id: ExecutedQuery(query_id, "purpose", "SELECT", query_result)
    for query_id, query_result in {
        "devices": REVENUE_BY_DEVICE,
        "total": TOTAL,
        "monthly": MONTHLY,
        "truncated": TRUNCATED,
        "many": MANY_BARS,
    }.items()
}


def spec(query_id, chart_type="bar", x="device", y=("revenue",), title="Title"):
    return {"query_id": query_id, "type": chart_type, "title": title, "x": x, "y": list(y)}


def test_valid_bar_chart():
    assert validate_chart(spec("devices"), QUERIES)["x"] == "device"


def test_kpi_chart_ignores_x():
    assert validate_chart(spec("total", "kpi", x="anything", y=["revenue"]), QUERIES)["x"] is None


def test_multi_series_comparison():
    assert validate_chart(spec("monthly", "bar", x="month", y=["nov", "dec"]), QUERIES)["y"] == ["nov", "dec"]


@pytest.mark.parametrize(
    "chart_spec, message",
    [
        (spec("missing"), "Unknown query_id"),
        (spec("devices", "pie"), "type must be one of"),
        (spec("devices", title=" "), "title is required"),
        (spec("devices", y=["revenue_usd"]), "not in devices"),
        (spec("devices", y=["device"]), "must be numeric"),
        (spec("devices", y=[]), "1 to 3 columns"),
        (spec("devices", x=None), "needs an x column"),
        (spec("devices", "kpi"), "single-row result"),
        (spec("truncated", "line", x="day", y=["users"]), "Aggregate further"),
        (spec("many", x="item", y=["units"]), "Too many bars"),
    ],
)
def test_invalid_charts_are_rejected_with_a_fixable_message(chart_spec, message):
    with pytest.raises(ChartError, match=message):
        validate_chart(chart_spec, QUERIES)
