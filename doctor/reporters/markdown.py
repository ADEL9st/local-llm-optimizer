from __future__ import annotations

from typing import Any

from doctor.advisor.base import AdvisorResult
from doctor.backends.base import BackendResult
from doctor.core.config import RunConfig
from doctor.core.storage import RunArtifacts


class MarkdownReporter:
    def __init__(self, locale: dict[str, Any]):
        self.locale = locale

    def render(
        self,
        config: RunConfig,
        backend_result: BackendResult,
        metrics: list[dict[str, Any]],
        diagnosis: dict[str, Any],
        advisor: AdvisorResult | None,
        artifacts: RunArtifacts,
    ) -> str:
        labels = self.locale["labels"]
        status = labels["ok"] if backend_result.success else labels["failed"]
        lines = [
            f"# {self.locale['report_title']}",
            "",
            f"## {labels['run_summary']}",
            "",
            f"| {labels['field']} | {labels['value']} |",
            "|---|---|",
            f"| {labels['backend']} | `{config.backend}` |",
            f"| {labels['model']} | `{config.model}` |",
            f"| {labels['duration']} | `{backend_result.duration_seconds:.2f}s` |",
            f"| {labels['samples']} | `{len(metrics)}` |",
            f"| {labels['status']} | `{status}` |",
        ]

        if config.base_url:
            lines.append(f"| {labels['base_url']} | `{config.base_url}` |")

        if backend_result.error:
            lines.append(f"| {labels['error']} | `{backend_result.error}` |")

        lines.extend(
            [
                "",
                f"## {labels['throughput']}",
                "",
                f"| {labels['metric']} | {labels['value']} |",
                "|---|---:|",
                f"| {labels['output_words']} | {backend_result.output_words} |",
                f"| {labels['output_chars']} | {backend_result.output_chars} |",
                f"| {labels['words_per_second']} | {_format_optional(backend_result.words_per_second)} |",
                f"| {labels['chars_per_second']} | {_format_optional(backend_result.chars_per_second)} |",
            ]
        )

        lines.extend(
            [
                "",
                f"## {labels['metrics']}",
                "",
                f"| {labels['metric']} | {labels['avg']} | {labels['max']} | {labels['min']} |",
                "|---|---:|---:|---:|",
            ]
        )

        for key, summary in diagnosis["summaries"].items():
            label = labels.get(key, key)
            if summary is None:
                lines.append(f"| {label} | n/a | n/a | n/a |")
            else:
                lines.append(
                    f"| {label} | {summary['avg']} | {summary['max']} | {summary['min']} |"
                )

        vram_ratio = diagnosis.get("vram_peak_ratio_percent")
        if vram_ratio is not None:
            lines.extend(
                [
                    "",
                    f"**{labels['vram_peak_ratio_percent']}**: `{vram_ratio}%`",
                ]
            )

        lines.extend(
            [
                "",
                f"## {labels['findings']}",
                "",
                f"| {labels['severity']} | {labels['finding']} | {labels['detail']} |",
                "|---|---|---|",
            ]
        )
        for finding in diagnosis["findings"]:
            lines.append(
                f"| `{finding['severity'].upper()}` | {finding['title']} | {finding['detail']} |"
            )

        lines.extend(["", f"## {labels['recommendations']}", ""])
        for recommendation in diagnosis["recommendations"]:
            lines.append(f"- {recommendation}")

        if advisor and advisor.enabled:
            lines.extend(
                [
                    "",
                    f"## {labels['advisor']}",
                    "",
                    f"**{labels['top_issue']}**: {advisor.top_issue}",
                    "",
                    advisor.summary,
                ]
            )
            if advisor.evidence:
                lines.extend(["", f"### {labels['evidence']}"])
                for item in advisor.evidence:
                    lines.append(f"- {item}")
            if advisor.recommendations:
                lines.extend(["", f"### {labels['prioritized_recommendations']}"])
                for index, item in enumerate(advisor.recommendations, start=1):
                    lines.append(f"{index}. {item}")

        preview = backend_result.output_text[:1000].strip()
        if preview:
            lines.extend(
                [
                    "",
                    f"## {labels['output_preview']}",
                    "",
                    "```text",
                    preview,
                    "```",
                ]
            )

        lines.extend(
            [
                "",
                f"## {labels['artifacts']}",
                "",
                f"| {labels['file']} | {labels['path']} |",
                "|---|---|",
                f"| `run.json` | `{artifacts.run_json}` |",
                f"| `metrics.csv` | `{artifacts.metrics_csv}` |",
                f"| `report.md` | `{artifacts.report_md}` |",
                "",
            ]
        )

        return "\n".join(lines)


def _format_optional(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"
