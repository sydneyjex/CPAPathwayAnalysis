#!/usr/bin/env python3
"""Compare perceived CPA licensure barriers across respondent groups."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DATA_PATH = Path("Alternative CPA Pathways Survey_December 31, 2025_09.45.csv")
OUTPUT_PATH = Path("analysis/barrier_by_group.md")
CHART_PATH = Path("analysis/barrier_by_group.svg")

GROUP_QUESTION = "Are you currently an undergraduate student or graduate student?"

LIKERT_TOP_TWO = {"Strongly agree", "Somewhat agree", "Agree"}


@dataclass(frozen=True)
class BarrierQuestion:
    label: str
    question_text: str
    indicator_values: set[str]


BARRIER_QUESTIONS = [
    BarrierQuestion(
        label="Graduate degree may delay career advancement",
        question_text=(
            "To what extent do you agree with the following statement about the value of a graduate "
            "accounting degree?\n\n"
            "Earning a graduate degree may delay my career advancement compared to peers who started "
            "full-time jobs earlier."
        ),
        indicator_values=LIKERT_TOP_TWO,
    ),
]


@dataclass(frozen=True)
class BarrierResult:
    label: str
    group: str
    count: int
    total: int

    @property
    def percentage(self) -> float:
        return (self.count / self.total * 100.0) if self.total else 0.0


def iter_rows(path: Path) -> Iterable[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            yield row


def main() -> None:
    rows = list(iter_rows(DATA_PATH))
    if len(rows) < 4:
        raise SystemExit("Dataset does not contain enough rows to parse.")

    questions = rows[1]
    data_rows = rows[3:]

    try:
        group_index = questions.index(GROUP_QUESTION)
    except ValueError as exc:
        raise SystemExit(f"Group question not found: {GROUP_QUESTION}") from exc

    group_values = [row[group_index].strip() for row in data_rows]
    groups = sorted({value for value in group_values if value})
    if not groups:
        raise SystemExit("No respondent group values found.")

    group_totals = {
        group: sum(1 for value in group_values if value == group) for group in groups
    }

    results: list[BarrierResult] = []

    for barrier in BARRIER_QUESTIONS:
        try:
            question_index = questions.index(barrier.question_text)
        except ValueError as exc:
            raise SystemExit(
                f"Barrier question not found in dataset: {barrier.question_text}"
            ) from exc

        for group in groups:
            count = 0
            total = group_totals[group]
            for row in data_rows:
                if row[group_index].strip() != group:
                    continue
                response = row[question_index].strip()
                if response in barrier.indicator_values:
                    count += 1
            results.append(
                BarrierResult(label=barrier.label, group=group, count=count, total=total)
            )

    lines = [
        "# Perceived CPA Licensure Barriers by Respondent Group",
        "",
        f"Grouping question: **{GROUP_QUESTION}**",
        "",
        "## Barrier indicators",
        "",
        "| Barrier | Group | Respondents | Percentage |",
        "| --- | --- | ---: | ---: |",
    ]

    for result in results:
        lines.append(
            f"| {result.label} | {result.group} | {result.count} / {result.total} | "
            f"{result.percentage:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Summary",
            "",
        ]
    )

    for barrier in BARRIER_QUESTIONS:
        barrier_results = [
            result for result in results if result.label == barrier.label
        ]
        if not barrier_results:
            continue
        sorted_results = sorted(barrier_results, key=lambda item: item.percentage)
        lowest = sorted_results[0]
        highest = sorted_results[-1]
        if highest.group == lowest.group:
            continue
        diff = highest.percentage - lowest.percentage
        lines.append(
            f"* {highest.group} respondents were more likely to report the barrier "
            f"\"{barrier.label}\" than {lowest.group} respondents "
            f"({highest.percentage:.1f}% vs. {lowest.percentage:.1f}%, "
            f"a {diff:.1f} percentage point gap)."
        )

    lines.extend(
        [
            "",
            "## Chart",
            "",
            f"![Barrier comparison chart]({CHART_PATH.name})",
        ]
    )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "* The dataset contains one Likert-style barrier statement with negative phrasing that "
            "aligns to a perceived barrier. The analysis above is limited to that item.",
        ]
    )

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    for barrier in BARRIER_QUESTIONS:
        chart_results = [result for result in results if result.label == barrier.label]
        if not chart_results:
            continue
        groups = [result.group for result in chart_results]
        percentages = [result.percentage for result in chart_results]
        counts = [f"{result.count}/{result.total}" for result in chart_results]

        chart_svg = build_svg_chart(
            groups=groups,
            percentages=percentages,
            counts=counts,
            title=barrier.label,
        )
        CHART_PATH.write_text(chart_svg, encoding="utf-8")
        break


def build_svg_chart(
    *, groups: list[str], percentages: list[float], counts: list[str], title: str
) -> str:
    width = 640
    height = 360
    margin = {"top": 50, "right": 40, "bottom": 60, "left": 60}
    chart_width = width - margin["left"] - margin["right"]
    chart_height = height - margin["top"] - margin["bottom"]
    max_value = max(100.0, max(percentages) * 1.2 if percentages else 100.0)
    bar_count = len(groups)
    bar_width = chart_width / max(bar_count, 1) * 0.6
    bar_spacing = chart_width / max(bar_count, 1)
    colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756"]

    def x_for(index: int) -> float:
        return margin["left"] + index * bar_spacing + (bar_spacing - bar_width) / 2

    def y_for(value: float) -> float:
        return margin["top"] + chart_height * (1 - value / max_value)

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        "<style>",
        "text { font-family: Arial, sans-serif; font-size: 12px; fill: #1f2d3d; }",
        ".axis { stroke: #9aa5b1; stroke-width: 1; }",
        "</style>",
        f'<text x="{width/2}" y="24" text-anchor="middle" font-size="16">{title}</text>',
        f'<line class="axis" x1="{margin["left"]}" y1="{margin["top"]}" '
        f'x2="{margin["left"]}" y2="{height - margin["bottom"]}" />',
        f'<line class="axis" x1="{margin["left"]}" y1="{height - margin["bottom"]}" '
        f'x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" />',
        f'<text x="{margin["left"]}" y="{margin["top"] - 10}" '
        f'font-size="12">100%</text>',
        f'<text x="{margin["left"]}" y="{height - margin["bottom"] + 30}" '
        f'font-size="12">0%</text>',
        f'<text x="{margin["left"] - 45}" y="{margin["top"] + chart_height/2}" '
        f'font-size="12" transform="rotate(-90 {margin["left"] - 45},{margin["top"] + chart_height/2})">'
        "Percentage indicating barrier</text>",
    ]

    for idx, (group, value, count) in enumerate(zip(groups, percentages, counts)):
        x = x_for(idx)
        y = y_for(value)
        bar_height = chart_height * (value / max_value)
        color = colors[idx % len(colors)]
        svg_lines.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" '
            f'fill="{color}" />'
        )
        svg_lines.append(
            f'<text x="{x + bar_width / 2}" y="{y - 6}" text-anchor="middle">'
            f'{value:.1f}% ({count})</text>'
        )
        svg_lines.append(
            f'<text x="{x + bar_width / 2}" y="{height - margin["bottom"] + 20}" '
            f'text-anchor="middle">{group}</text>'
        )

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


if __name__ == "__main__":
    main()
