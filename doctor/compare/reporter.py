from __future__ import annotations

from typing import Any

from doctor.compare.engine import ComparisonResult, MetricRow


class CompareReporter:
    def __init__(self, locale: dict[str, Any]):
        compare = locale.get("compare", {})
        self.title = compare.get("title", "Run Comparison")
        self.labels = compare.get("labels", {})
        self.metric_names = compare.get("metrics", {})

    def render(self, result: ComparisonResult) -> str:
        lines = self._lines(result)
        text = "\n".join(lines)
        print(text)
        return text

    def _lines(self, result: ComparisonResult) -> list[str]:
        na = self.labels.get("not_available", "n/a")
        run_label = self.labels.get("run_label", "Run")
        name_a = f"{run_label} {result.run_a.label}"
        name_b = f"{run_label} {result.run_b.label}"

        lines: list[str] = ["", f"=== {self.title} ==="]
        lines.append(self._identity_line(name_a, result.run_a, na))
        lines.append(self._identity_line(name_b, result.run_b, na))
        lines.append("")
        lines.extend(self._table(result, name_a, name_b, na))
        lines.append("")
        lines.append(f"--- {self.labels.get('insights_title', 'Insights')} ---")
        if result.insights:
            lines.extend(f"- {item}" for item in result.insights)
        else:
            lines.append(f"- {self.labels.get('no_insights', 'No notable differences.')}")
        lines.append("")
        lines.append(f"--- {self.labels.get('recommendation_title', 'Recommendation')} ---")
        lines.append(result.recommendation or na)
        return lines

    def _identity_line(self, name: str, summary: Any, na: str) -> str:
        max_tokens = summary.max_tokens if summary.max_tokens is not None else na
        return (
            f"{name}: {summary.model or na} | {summary.backend or na} | "
            f"{self.labels.get('max_tokens', 'Max tokens')}={max_tokens} | {summary.source}"
        )

    def _table(
        self,
        result: ComparisonResult,
        name_a: str,
        name_b: str,
        na: str,
    ) -> list[str]:
        header = [
            self.labels.get("metric", "Metric"),
            name_a,
            name_b,
            self.labels.get("difference", "Diff"),
            self.labels.get("better", "Better"),
        ]
        rows = [self._row_cells(row, na) for row in result.rows]
        widths = [
            max(len(header[i]), *(len(r[i]) for r in rows)) if rows else len(header[i])
            for i in range(len(header))
        ]

        def fmt(cells: list[str]) -> str:
            return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

        return [fmt(header), fmt(["-" * w for w in widths])] + [fmt(r) for r in rows]

    def _row_cells(self, row: MetricRow, na: str) -> list[str]:
        return [
            self.metric_names.get(row.key, row.key),
            _value_cell(row.a, row.unit, na),
            _value_cell(row.b, row.unit, na),
            _delta_cell(row.delta_percent, na),
            _better_cell(row.better, self.labels.get("tie", "~")),
        ]


def _value_cell(value: float | None, unit: str, na: str) -> str:
    if value is None:
        return na
    rounded = round(value, 2)
    number = int(rounded) if rounded == int(rounded) else rounded
    return f"{number} {unit}".strip()


def _delta_cell(delta: float | None, na: str) -> str:
    if delta is None:
        return na
    return f"{delta:+.1f}%"


def _better_cell(better: str | None, tie_label: str) -> str:
    return better if better is not None else tie_label
