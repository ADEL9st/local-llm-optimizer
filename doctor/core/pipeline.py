from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from doctor.advisor import build_advisor
from doctor.advisor.base import AdvisorResult
from doctor.backends.base import BackendResult
from doctor.core.config import RunConfig, load_locale
from doctor.core.monitor import MetricsMonitor
from doctor.core.registry import build_collectors, get_backend, normalize_backend_config
from doctor.core.storage import RunArtifacts, RunStorage
from doctor.diagnosis.engine import DiagnosisEngine
from doctor.reporters.markdown import MarkdownReporter
from doctor.reporters.terminal import TerminalReporter


@dataclass(frozen=True)
class PipelineResult:
    backend_result: BackendResult
    metrics: list[dict[str, Any]]
    diagnosis: dict[str, Any]
    advisor: AdvisorResult | None
    artifacts: RunArtifacts


class Pipeline:
    def __init__(self, config: RunConfig):
        normalized_config = normalize_backend_config(config)
        normalized_advisor = normalized_config.advisor.normalized(normalized_config.lang)
        self.config = replace(normalized_config, advisor=normalized_advisor)
        self.config.validate()
        self.locale = load_locale(self.config.lang)

    def run(self) -> PipelineResult:
        backend = get_backend(self.config.backend, self.config)
        monitor = MetricsMonitor(
            collectors=build_collectors(),
            interval_seconds=self.config.sample_interval,
        )

        print(self.locale["messages"]["starting"])
        monitor.start()
        try:
            backend_result = backend.run(
                model=self.config.model,
                prompt=self.config.prompt,
                timeout_seconds=self.config.timeout_seconds,
            )
        finally:
            metrics = monitor.stop()

        if not metrics:
            metrics = [monitor.sample_once()]

        diagnosis = DiagnosisEngine(self.locale).analyze(backend_result, metrics)
        advisor = build_advisor(self.config, self.locale).advise(diagnosis)
        storage = RunStorage(self.config)
        artifacts = storage.write_all(backend_result, metrics, diagnosis, advisor)

        TerminalReporter(self.locale).render(
            config=self.config,
            backend_result=backend_result,
            metrics=metrics,
            diagnosis=diagnosis,
            advisor=advisor,
            artifacts=artifacts,
        )

        markdown = MarkdownReporter(self.locale).render(
            config=self.config,
            backend_result=backend_result,
            metrics=metrics,
            diagnosis=diagnosis,
            advisor=advisor,
            artifacts=artifacts,
        )
        artifacts.report_md.write_text(markdown, encoding="utf-8")

        return PipelineResult(
            backend_result=backend_result,
            metrics=metrics,
            diagnosis=diagnosis,
            advisor=advisor,
            artifacts=artifacts,
        )
