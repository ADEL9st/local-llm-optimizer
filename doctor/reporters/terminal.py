from __future__ import annotations

from typing import Any

from doctor.advisor.base import AdvisorResult
from doctor.backends.base import BackendResult
from doctor.core.config import RunConfig
from doctor.core.storage import RunArtifacts


class TerminalReporter:
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
    ) -> None:
        labels = self.locale["labels"]

        print()
        print(f"=== {self.locale['report_title']} ===")
        print(f"{labels['model']}: {config.model}")
        print(f"{labels['backend']}: {config.backend}")
        print(f"{labels['duration']}: {backend_result.duration_seconds:.2f}s")
        print(f"{labels['samples']}: {len(metrics)}")
        print(f"{labels['status']}: {_status_label(labels, backend_result.success)}")

        if backend_result.error:
            print(f"{labels['error']}: {backend_result.error}")

        print()
        print(f"--- {labels['metrics']} ---")
        for key, summary in diagnosis["summaries"].items():
            print(_summary_line(labels, labels.get(key, key), summary))

        print()
        print(f"--- {labels['findings']} ---")
        for finding in diagnosis["findings"]:
            print(f"[{finding['severity'].upper()}] {finding['title']}")
            print(f"  {finding['detail']}")

        print()
        print(f"--- {labels['recommendations']} ---")
        for recommendation in diagnosis["recommendations"]:
            print(f"- {recommendation}")

        if advisor and advisor.enabled:
            print()
            print(f"--- {labels['advisor']} ---")
            print(f"{labels['top_issue']}: {advisor.top_issue}")
            print(advisor.summary)
            if advisor.evidence:
                print(f"{labels['evidence']}:")
                for item in advisor.evidence:
                    print(f"- {item}")
            if advisor.recommendations:
                print(f"{labels['prioritized_recommendations']}:")
                for index, item in enumerate(advisor.recommendations, start=1):
                    print(f"{index}. {item}")

        print()
        print(f"{labels['artifacts']}:")
        print(f"- run.json: {artifacts.run_json}")
        print(f"- metrics.csv: {artifacts.metrics_csv}")
        print(f"- report.md: {artifacts.report_md}")


def _summary_line(
    labels: dict[str, str],
    label: str,
    summary: dict[str, float] | None,
) -> str:
    if summary is None:
        return f"{label}: n/a"
    return (
        f"{label}: {labels['avg']}={summary['avg']} | "
        f"{labels['max']}={summary['max']} | {labels['min']}={summary['min']}"
    )


def _status_label(labels: dict[str, str], success: bool) -> str:
    return labels["ok"] if success else labels["failed"]
