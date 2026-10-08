"""Runs the golden questions through the real agent (Gemini + BigQuery) and checks the key numbers.

Usage, from backend/:  uv run python -m evals.run_evals [case_id ...]
Writes a readable report to evals/report.md.
"""

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.agent.history import Turn
from app.agent.loop import Agent
from app.main import get_agent

GOLDEN_FILE = Path(__file__).with_name("golden.yaml")
REPORT_FILE = Path(__file__).with_name("report.md")
TOLERANCE = 0.01
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass
class CaseResult:
    case: dict[str, Any]
    answer: str = ""
    error: str | None = None
    queries: int = 0
    seconds: float = 0.0
    checks: list[tuple[str, str]] = field(default_factory=list)  # (label, "answer" | "data only" | "missing")
    ungrounded: list[str] = field(default_factory=list)  # numbers in the answer that no query returned

    @property
    def status(self) -> str:
        if self.error:
            return "ERROR"
        if not self.checks:
            return "manual"
        return "FAIL" if any(found == "missing" for _, found in self.checks) else "pass"


def run_case(agent: Agent, case: dict[str, Any]) -> CaseResult:
    """Asks every turn in order, carrying history like the browser does; checks apply to the last answer."""
    result = CaseResult(case)
    history: list[Turn] = []
    data_values: list[float] = []  # from every turn, since a follow-up may quote earlier results
    started = time.monotonic()
    for question in case["turns"]:
        for event in agent.run(question, history):
            if event.type == "query_result":
                result.queries += 1
                data_values += numbers_in_rows(event.data["rows"])
            elif event.type == "answer":
                result.answer = event.data["text"]
            elif event.type == "done":
                history.append(Turn(**event.data["turn"]))
            elif event.type == "error":
                result.error = event.data["message"]
    result.seconds = time.monotonic() - started

    answer_values = [float(match.replace(",", "")) for match in NUMBER.findall(result.answer)]
    for expected in case.get("expect", []):
        if contains(answer_values, expected["value"]):
            found = "answer"
        elif contains(data_values, expected["value"]):
            found = "data only"
        else:
            found = "missing"
        result.checks.append((expected["label"], found))
    result.ungrounded = ungrounded_numbers(result.answer, data_values)
    return result


def ungrounded_numbers(answer: str, data_values: list[float]) -> list[str]:
    """Numbers the model wrote that don't match any query result, i.e. arithmetic it did itself.

    Small whole numbers (ranks, "top 5", days of the month) and years are skipped.
    A percentage may come back from SQL as a fraction (11.3 vs 0.113).
    """
    as_percentages = [value * 100 for value in data_values]
    ungrounded = []
    for text in NUMBER.findall(answer):
        value = float(text.replace(",", ""))
        if (value.is_integer() and value <= 31) or 2019 <= value <= 2022:
            continue
        if not (contains(data_values, value) or contains(as_percentages, value)):
            ungrounded.append(text)
    return ungrounded


def numbers_in_rows(rows: list[list[Any]]) -> list[float]:
    return [float(value) for row in rows for value in row if isinstance(value, (int, float))]


def contains(values: list[float], target: float) -> bool:
    """Signs are ignored ("fell 64.3%" vs -64.3); allows 1% or one-decimal rounding."""
    return any(abs(abs(value) - target) <= max(target * TOLERANCE, 0.05) for value in values)


def write_report(results: list[CaseResult]) -> None:
    lines = [
        "# Golden question results",
        "",
        "| Case | Result | Key numbers | Ungrounded numbers | Queries | Time |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        checks = "<br>".join(f"{label}: {found}" for label, found in result.checks) or "—"
        ungrounded = ", ".join(result.ungrounded) or "none"
        lines.append(
            f"| {result.case['id']} | {result.status} | {checks} | {ungrounded} "
            f"| {result.queries} | {result.seconds:.0f}s |"
        )
    for result in results:
        lines += ["", f"## {result.case['id']}", ""]
        lines += [f"> {question}" for question in result.case["turns"]]
        if result.case.get("manual"):
            lines += ["", f"**Check by eye:** {result.case['manual']}"]
        lines += ["", result.error or result.answer]
    REPORT_FILE.write_text("\n".join(lines) + "\n")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, force=True)
    selected = set(sys.argv[1:])
    cases = [
        case for case in yaml.safe_load(GOLDEN_FILE.read_text()) if not selected or case["id"] in selected
    ]
    agent = get_agent()

    results = []
    for case in cases:
        result = run_case(agent, case)
        results.append(result)
        print(
            f"{result.status:7} {case['id']:24} {result.queries} queries  {result.seconds:5.1f}s  "
            f"{result.checks}  ungrounded={result.ungrounded}",
            flush=True,
        )

    write_report(results)
    failed = sum(result.status in ("FAIL", "ERROR") for result in results)
    print(f"\n{len(results) - failed}/{len(results)} without failures. Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
