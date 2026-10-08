from app.agent.history import QueryRecord, Turn
from app.agent.loop import Agent
from app.agent.tools import MODEL_MAX_ROWS
from app.llm.gemini import LLMError
from tests.fakes import (
    REVENUE_BY_DEVICE,
    FakeLLM,
    FakeRunner,
    chart,
    result,
    sql,
    text_reply,
    tool_reply,
)


def run_agent(llm, runner=None, question="Revenue by device?", history=None, max_iterations=10):
    agent = Agent(llm, runner or FakeRunner({}), max_iterations=max_iterations)
    return list(agent.run(question, history or []))


def types(events):
    return [event.type for event in events]


def test_answers_directly_when_no_tools_are_needed():
    events = run_agent(FakeLLM(text_reply("Which metric do you mean?")))

    assert types(events) == ["answer", "done"]
    assert events[0].data["text"] == "Which metric do you mean?"


def test_runs_a_query_then_answers():
    runner = FakeRunner({"SELECT device": REVENUE_BY_DEVICE})
    llm = FakeLLM(tool_reply(sql("SELECT device")), text_reply("Desktop leads."))

    events = run_agent(llm, runner)

    assert types(events) == ["query_started", "query_result", "answer", "done"]
    assert events[1].data["rows"] == REVENUE_BY_DEVICE.rows
    function_response = llm.requests[1]["contents"][-1]["parts"][0]["functionResponse"]
    assert function_response["response"]["rows"] == REVENUE_BY_DEVICE.rows


def test_model_gets_a_capped_number_of_rows_while_the_browser_gets_all():
    many_rows = result({"n": "INTEGER"}, [[i] for i in range(MODEL_MAX_ROWS + 50)])
    llm = FakeLLM(tool_reply(sql("SELECT n")), text_reply("Done."))

    events = run_agent(llm, FakeRunner({"SELECT n": many_rows}))

    assert len(events[1].data["rows"]) == MODEL_MAX_ROWS + 50
    response = llm.requests[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]
    assert len(response["rows"]) == MODEL_MAX_ROWS
    assert response["truncated"] is True


def test_parallel_calls_are_answered_together():
    runner = FakeRunner({"SELECT a": REVENUE_BY_DEVICE, "SELECT b": REVENUE_BY_DEVICE})
    llm = FakeLLM(tool_reply(sql("SELECT a"), sql("SELECT b")), text_reply("Done."))

    events = run_agent(llm, runner)

    assert runner.executed == ["SELECT a", "SELECT b"]
    last_turn = llm.requests[1]["contents"][-1]
    assert [part["functionResponse"]["response"]["query_id"] for part in last_turn["parts"]] == ["q1", "q2"]
    assert len(events[-1].data["turn"]["queries"]) == 2


def test_sql_error_goes_back_to_the_model_which_retries():
    runner = FakeRunner({"SELECT bad": "Unrecognized name: revenue", "SELECT good": REVENUE_BY_DEVICE})
    llm = FakeLLM(tool_reply(sql("SELECT bad")), tool_reply(sql("SELECT good")), text_reply("Fixed."))

    events = run_agent(llm, runner)

    assert types(events) == [
        "query_started",
        "query_error",
        "query_started",
        "query_result",
        "answer",
        "done",
    ]
    error_response = llm.requests[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]
    assert error_response == {"query_id": "q1", "error": "Unrecognized name: revenue"}
    assert [query["sql"] for query in events[-1].data["turn"]["queries"]] == ["SELECT good"]


def test_valid_chart_is_streamed():
    runner = FakeRunner({"SELECT device": REVENUE_BY_DEVICE})
    llm = FakeLLM(
        tool_reply(sql("SELECT device")),
        tool_reply(chart("q1", "bar", "device", ["revenue"])),
        text_reply("Desktop leads."),
    )

    events = run_agent(llm, runner)

    chart_event = next(event for event in events if event.type == "chart")
    assert chart_event.data == {
        "query_id": "q1",
        "type": "bar",
        "title": "Chart",
        "x": "device",
        "y": ["revenue"],
    }


def test_invalid_chart_returns_an_error_to_the_model_instead_of_streaming():
    runner = FakeRunner({"SELECT device": REVENUE_BY_DEVICE})
    llm = FakeLLM(
        tool_reply(sql("SELECT device")),
        tool_reply(chart("q1", "bar", "device", ["revenue_usd"])),
        text_reply("Desktop leads."),
    )

    events = run_agent(llm, runner)

    assert "chart" not in types(events)
    response = llm.requests[2]["contents"][-1]["parts"][0]["functionResponse"]["response"]
    assert "not in q1" in response["error"]


def test_iteration_limit_forces_an_answer_without_tools():
    runner = FakeRunner({"SELECT device": REVENUE_BY_DEVICE})
    llm = FakeLLM(
        tool_reply(sql("SELECT device")),
        tool_reply(sql("SELECT device")),
        text_reply("Best effort answer."),
    )

    events = run_agent(llm, runner, max_iterations=2)

    assert events[-2].data["text"] == "Best effort answer."
    assert llm.requests[-1]["allow_tool_calls"] is False
    assert "limit of tool calls" in llm.requests[-1]["system"]


def test_llm_failure_becomes_an_error_event():
    events = run_agent(FakeLLM(LLMError("The AI service is rate-limited.", retryable=True)))

    assert types(events) == ["error"]
    assert events[0].data == {"message": "The AI service is rate-limited.", "retryable": True}


def test_empty_answer_is_an_error():
    events = run_agent(FakeLLM(text_reply("")))

    assert types(events) == ["error"]


def test_unknown_tool_is_reported_to_the_model():
    llm = FakeLLM(tool_reply(("drop_table", {})), text_reply("Sorry."))

    run_agent(llm)

    response = llm.requests[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]
    assert response == {"error": "Unknown tool: drop_table"}


def test_history_is_sent_to_the_model_before_the_new_question():
    past = Turn(
        question="Top products?",
        answer="Zip Hoodie leads.",
        queries=[
            QueryRecord(
                purpose="Top products", sql="SELECT item", columns=["item"], preview=[["Hoodie"]], row_count=1
            )
        ],
    )
    llm = FakeLLM(text_reply("In December..."))

    run_agent(llm, question="What about December?", history=[past])

    contents = llm.requests[0]["contents"]
    assert [turn["role"] for turn in contents] == ["user", "model", "user"]
    assert "SELECT item" in contents[1]["parts"][0]["text"]
    assert contents[2]["parts"][0]["text"] == "What about December?"


def test_done_event_carries_a_compact_turn_for_the_browser():
    many_rows = result({"n": "INTEGER"}, [[i] for i in range(50)])
    runner = FakeRunner({"SELECT n": many_rows})
    llm = FakeLLM(tool_reply(sql("SELECT n", "Numbers")), text_reply("Fifty numbers."))

    turn = run_agent(llm, runner)[-1].data["turn"]

    assert turn["question"] == "Revenue by device?"
    assert turn["queries"][0]["purpose"] == "Numbers"
    assert len(turn["queries"][0]["preview"]) == 10
    assert turn["queries"][0]["row_count"] == 50
