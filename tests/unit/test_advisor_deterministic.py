import json
from pathlib import Path

from doctor.advisor.deterministic import DeterministicAdvisor
from doctor.backends.base import BackendResult
from doctor.core.config import AdvisorConfig, RunConfig, load_locale
from doctor.diagnosis.engine import DiagnosisEngine


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_metrics(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_diagnosis(metrics_file: str):
    diagnosis_engine = DiagnosisEngine(load_locale("tr"))
    return diagnosis_engine.analyze(
        BackendResult(
            backend="mock",
            model="mock-model",
            prompt="prompt",
            success=True,
            duration_seconds=1.0,
            output_text="mock output",
            stderr="",
            return_code=0,
            output_words=2,
            output_chars=11,
            words_per_second=2.0,
            chars_per_second=11.0,
        ),
        load_metrics(metrics_file),
    )


def test_deterministic_advisor_prioritizes_gpu_idle():
    config = RunConfig(
        backend="ollama",
        model="mock-model",
        prompt="prompt",
        lang="tr",
        advisor=AdvisorConfig(enabled=True, mode="deterministic", language="tr"),
    )
    advisor = DeterministicAdvisor(load_locale("tr"), config)
    result = advisor.advise(make_diagnosis("gpu_idle_metrics.json"))

    assert result.issue_key == "gpu_idle"
    assert "GPU" in result.top_issue
    assert "olabilir" in result.top_issue
    assert len(result.evidence) >= 2
    assert "GPU acceleration" in result.recommendations[0]


def test_deterministic_advisor_explains_ram_pressure():
    config = RunConfig(
        backend="ollama",
        model="mock-model",
        prompt="prompt",
        lang="tr",
        advisor=AdvisorConfig(enabled=True, mode="deterministic", language="tr"),
    )
    advisor = DeterministicAdvisor(load_locale("tr"), config)
    result = advisor.advise(make_diagnosis("ram_pressure_metrics.json"))

    assert result.issue_key == "ram_pressure"
    assert "RAM" in result.top_issue
    assert any("RAM" in item for item in result.evidence)


def test_disabled_advisor_returns_disabled_result():
    config = RunConfig(
        backend="ollama",
        model="mock-model",
        prompt="prompt",
        lang="en",
        advisor=AdvisorConfig(enabled=False, mode="deterministic", language="en"),
    )
    advisor = DeterministicAdvisor(load_locale("en"), config, enabled=False)
    result = advisor.advise(make_diagnosis("gpu_idle_metrics.json"))

    assert result.enabled is False
    assert result.issue_key is None
