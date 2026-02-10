#!/usr/bin/env python3
"""Generate a ranked summary of perceived CPA licensure barriers."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DATA_PATH = Path("Alternative CPA Pathways Survey_December 31, 2025_09.45.csv")
OUTPUT_PATH = Path("analysis/barrier_summary.md")
CHART_PATH = Path("analysis/barrier_summary.png")

BARRIER_KEYWORDS = (
    "barrier",
    "obstacle",
    "challenge",
    "difficulty",
    "difficult",
)

LIKERT_TOP_TWO = {
    "Strongly agree",
    "Agree",
}

LIKERT_SETS = {
    frozenset(
        {
            "Strongly agree",
            "Agree",
            "Neither agree nor disagree",
            "Disagree",
            "Strongly disagree",
        }
    ),
    frozenset(
        {
            "Very important",
            "Extremely important",
            "Moderately important",
            "Slightly important",
            "Not at all important",
        }
    ),
    frozenset(
        {
            "Very likely",
            "Somewhat likely",
            "Neither likely nor unlikely",
            "Somewhat unlikely",
            "Very unlikely",
        }
    ),
}


@dataclass(frozen=True)
class BarrierResult:
    name: str
    count: int
    percentage: float


def is_barrier_question(question: str) -> bool:
    lower = question.lower()
    return any(keyword in lower for keyword in BARRIER_KEYWORDS)


def is_multiselect(values: set[str]) -> bool:
    return values.issubset({"Selected", "Not Selected"})


def is_likert(values: set[str]) -> bool:
    for likert_set in LIKERT_SETS:
        if values.issubset(likert_set):
            return True
    return False


def iter_rows(path: Path) -> Iterable[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            yield row


def main() -> None:
    rows = list(iter_rows(DATA_PATH))
    if len(rows) < 4:
        raise SystemExit("Dataset does not contain enough rows to parse.")

    headers = rows[0]
    questions = rows[1]
    data_rows = rows[3:]

    response_id_index = headers.index("ResponseId")
    total_respondents = sum(1 for row in data_rows if row[response_id_index].strip())

    barrier_columns: dict[int, str] = {
        idx: question
        for idx, question in enumerate(questions)
        if is_barrier_question(question)
    }

    results: list[BarrierResult] = []

    for idx, question in barrier_columns.items():
        column_values = {row[idx] for row in data_rows if row[idx]}
        count = 0
        if not column_values:
            continue

        if is_multiselect(column_values):
            count = sum(1 for row in data_rows if row[idx] == "Selected")
        elif is_likert(column_values):
            count = sum(1 for row in data_rows if row[idx] in LIKERT_TOP_TWO)
        else:
            count = sum(1 for row in data_rows if row[idx].strip())

        percentage = (count / total_respondents * 100) if total_respondents else 0.0
        results.append(BarrierResult(name=question, count=count, percentage=percentage))

    results.sort(key=lambda item: item.count, reverse=True)

    lines = [
        "# Perceived CPA Licensure Barriers Summary",
        "",
        f"Total respondents analyzed: **{total_respondents}**",
        "",
    ]

    if not results:
        lines.extend(
            [
                "No survey columns with barrier-related keywords were detected in the",
                "question text row of the dataset. If there are barrier questions in a",
                "different sheet or dataset, please provide that file to compute the",
                "requested ranked summary.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "| Barrier | Respondents | Percentage |",
                "| --- | ---: | ---: |",
            ]
        )
        for result in results:
            lines.append(
                f"| {result.name} | {result.count} | {result.percentage:.1f}% |"
            )
        lines.append("")

        try:
            import matplotlib.pyplot as plt  # type: ignore

            top_results = results[:10]
            labels = [item.name for item in top_results]
            counts = [item.count for item in top_results]

            plt.figure(figsize=(12, 6))
            plt.barh(range(len(labels)), counts, color="#3B82F6")
            plt.yticks(range(len(labels)), labels, fontsize=8)
            plt.xlabel("Respondents")
            plt.title("Top 10 Perceived CPA Licensure Barriers")
            plt.gca().invert_yaxis()
            plt.tight_layout()
            plt.savefig(CHART_PATH, dpi=200)
            plt.close()

            lines.append("![Barrier summary chart](barrier_summary.png)")
        except ModuleNotFoundError:
            lines.append(
                "Visualization not generated because matplotlib is not installed."
            )
        lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
