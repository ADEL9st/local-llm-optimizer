import json
from pathlib import Path

from doctor.backends.base import BackendResult
from doctor.core.config import load_locale
from doctor.diagnosis.engine import DiagnosisEngine


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_metrics(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def backend_result(success: bool = True) -> BackendResult:
    return BackendResult(
        backend="mock",
        model="mock-model",
        prompt="Say hello",
        success=success,
        duration_seconds=1.0,
        output_text="hello from mock",
        stderr="",
        return_code=0 if success else 1,
        output_words=3,
        output_chars=15,
        words_per_second=3.0,
        chars_per_second=15.0,
    )


def finding_keys(diagnosis):
    return {finding["key"] for finding in diagnosis["findings"]}


def test_gpu_idle_when_gpu_avg_and_vram_are_low():
    diagnosis = DiagnosisEngine(load_locale("en")).analyze(
        backend_result(),
        load_metrics("gpu_idle_metrics.json"),
    )

    assert "gpu_idle" in finding_keys(diagnosis)
    assert "vram_high" not in finding_keys(diagnosis)
    assert "vram_bottleneck" not in finding_keys(diagnosis)
    assert diagnosis["vram_peak_ratio_percent"] < 10


def test_ram_pressure_when_ram_is_high():
    diagnosis = DiagnosisEngine(load_locale("en")).analyze(
        backend_result(),
        load_metrics("ram_pressure_metrics.json"),
    )

    assert "ram_pressure" in finding_keys(diagnosis)
    assert diagnosis["summaries"]["ram_percent"]["max"] == 92.0


def test_backend_failure_adds_backend_failed_finding():
    diagnosis = DiagnosisEngine(load_locale("en")).analyze(
        backend_result(success=False),
        load_metrics("gpu_idle_metrics.json"),
    )

    assert "backend_failed" in finding_keys(diagnosis)
