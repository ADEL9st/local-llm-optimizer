from __future__ import annotations

import csv
import json
from pathlib import Path

import doctor.core.pipeline as pipeline_module
from doctor.backends.base import BackendResult
from doctor.collectors.base import MetricCollector
from doctor.core.config import RunConfig


class MockBackend:
    def run(self, model: str, prompt: str, timeout_seconds: float) -> BackendResult:
        output = "mock backend output for reporter"
        return BackendResult(
            backend="mock",
            model=model,
            prompt=prompt,
            success=True,
            duration_seconds=0.25,
            output_text=output,
            stderr="",
            return_code=0,
            output_words=len(output.split()),
            output_chars=len(output),
            words_per_second=120.0,
            chars_per_second=480.0,
        )


class StaticCollector(MetricCollector):
    name = "static"

    def collect(self):
        return {
            "cpu_percent": 28.0,
            "ram_percent": 45.0,
            "ram_used_gb": 14.4,
            "ram_total_gb": 32.0,
            "gpu_util_percent": 4.0,
            "vram_used_mb": 512.0,
            "vram_total_mb": 12288.0,
            "gpu_temp_c": 36.0,
            "gpu_power_w": 10.0,
        }


def test_pipeline_runs_end_to_end_with_mock_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "get_backend", lambda name, config: MockBackend())
    monkeypatch.setattr(pipeline_module, "build_collectors", lambda: [StaticCollector()])

    config = RunConfig(
        backend="ollama",
        model="mock-model",
        prompt="Say hello",
        lang="en",
        output_dir=tmp_path,
        sample_interval=0.1,
        timeout_seconds=5,
    )

    result = pipeline_module.Pipeline(config).run()

    assert result.backend_result.success
    assert result.artifacts.run_json.exists()
    assert result.artifacts.metrics_csv.exists()
    assert result.artifacts.report_md.exists()

    run_json = json.loads(result.artifacts.run_json.read_text(encoding="utf-8"))
    assert run_json["backend_result"]["output_text"] == "mock backend output for reporter"
    assert run_json["diagnosis"]["findings"][0]["key"] == "gpu_idle"
    assert run_json["advisor"]["issue_key"] == "gpu_idle"
    assert run_json["advisor"]["enabled"] is True
    assert run_json["config"]["advisor"]["mode"] == "deterministic"

    metrics = list(csv.DictReader(result.artifacts.metrics_csv.open(encoding="utf-8")))
    assert len(metrics) >= 1
    assert metrics[0]["gpu_util_percent"] == "4.0"

    report = result.artifacts.report_md.read_text(encoding="utf-8")
    assert "Advisor Agent" in report
    assert "Top issue" in report
    assert "GPU may not be used effectively" in report
    assert "Run Summary" in report
    assert "Throughput" in report
    assert "mock backend output for reporter" in report
    assert "| `report.md` |" in report
