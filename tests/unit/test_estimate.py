from __future__ import annotations

import json

import pytest

from doctor.core.config import load_locale
from doctor.estimate import EstimateError, estimate_fit
from doctor.estimate.reporter import EstimateReporter

EN = load_locale("en")


def _keys(estimate):
    return [suggestion.key for suggestion in estimate.suggestions]


def test_infers_params_and_reports_fit():
    estimate = estimate_fit("llama3-7b", quant="q4_k_m", context_tokens=2048, vram_gb=24, ram_gb=32)

    assert estimate.inputs.params_billion == 7
    assert estimate.inputs.quant == "q4_k_m"
    assert estimate.status == "fits"
    assert _keys(estimate) == ["good_fit"]


def test_large_model_does_not_fit_with_cpu_offload():
    estimate = estimate_fit("big-70b", quant="q4_k_m", context_tokens=4096, vram_gb=12, ram_gb=64)

    assert estimate.status == "no_fit"
    keys = _keys(estimate)
    assert "lower_quant" in keys
    assert "smaller_model" in keys
    assert "cpu_offload" in keys


def test_no_fit_without_cpu_offload_when_ram_is_small():
    estimate = estimate_fit("big-70b", quant="q4_k_m", context_tokens=4096, vram_gb=12, ram_gb=24)

    assert estimate.status == "no_fit"
    assert "no_cpu_offload" in _keys(estimate)


def test_tight_fit_suggests_reduced_context():
    estimate = estimate_fit("mid-13b", quant="q4_k_m", context_tokens=8192, vram_gb=10, ram_gb=16)

    assert estimate.status == "tight"
    reduce = next(s for s in estimate.suggestions if s.key == "reduce_context")
    assert reduce.data["target"] >= 512
    assert reduce.data["target"] < 8192


def test_unknown_vram_points_to_hardware_command():
    estimate = estimate_fit("x-7b", quant="q4_k_m", vram_gb=None, ram_gb=32)

    assert estimate.status == "unknown_vram"
    assert _keys(estimate) == ["run_hardware"]


def test_params_override_and_quant_normalization():
    estimate = estimate_fit("mystery-model", params_billion=7, quant="Q8_0", vram_gb=24, ram_gb=32)

    assert estimate.inputs.params_billion == 7
    assert estimate.inputs.quant == "q8_0"
    assert estimate.inputs.bits_per_weight == 8.5


def test_bare_digit_quant_maps_to_q_form():
    estimate = estimate_fit("x-7b", quant="4", vram_gb=24, ram_gb=32)

    assert estimate.inputs.quant == "q4"


def test_unknown_quant_raises():
    with pytest.raises(EstimateError):
        estimate_fit("x-7b", quant="q9_special", vram_gb=24)


def test_unparseable_model_without_params_raises():
    with pytest.raises(EstimateError):
        estimate_fit("mistral-latest", quant="q4_k_m", vram_gb=24)


def test_moe_name_adds_note_when_params_inferred():
    estimate = estimate_fit("mixtral-8x7b", quant="q4_k_m", vram_gb=24, ram_gb=64)

    assert estimate.inputs.params_billion == 56
    assert estimate.status == "no_fit"
    assert "moe" in estimate.notes
    assert "approximate" in estimate.notes


def test_uses_largest_b_parameter_when_name_has_active_params():
    estimate = estimate_fit("qwen3-235b-a22b", quant="q4_k_m", vram_gb=80, ram_gb=256)

    assert estimate.inputs.params_billion == 235
    assert estimate.status == "no_fit"


def test_to_dict_is_json_serializable():
    estimate = estimate_fit("x-32b", quant="q4_k_m", vram_gb=12, ram_gb=32)
    data = estimate.to_dict()

    assert data["status"] == "no_fit"
    assert data["model"] == "x-32b"
    # round-trips through JSON without custom encoders
    assert json.loads(json.dumps(data))["context_tokens"] == 4096


def test_reporter_renders_localized_fields():
    estimate = estimate_fit("qwen2.5-32b", quant="q4_k_m", vram_gb=12, ram_gb=32)
    text = EstimateReporter(EN).render(estimate)

    assert "Model Fit Estimate" in text
    assert "Estimated need" in text
    assert "does not fit GPU" in text
    assert "lower-bit quantization" in text
