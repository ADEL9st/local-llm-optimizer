from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Effective bits per weight, including quantization metadata overhead.
QUANT_BITS: dict[str, float] = {
    "f32": 32.0,
    "fp32": 32.0,
    "f16": 16.0,
    "fp16": 16.0,
    "q8": 8.5,
    "q8_0": 8.5,
    "q6": 6.6,
    "q6_k": 6.6,
    "q5": 5.7,
    "q5_0": 5.5,
    "q5_1": 6.0,
    "q5_k_s": 5.5,
    "q5_k_m": 5.7,
    "q4": 4.85,
    "q4_0": 4.5,
    "q4_1": 5.0,
    "q4_k_s": 4.6,
    "q4_k_m": 4.85,
    "q3": 3.9,
    "q3_k_s": 3.5,
    "q3_k_m": 3.9,
    "q2": 3.35,
    "q2_k": 3.35,
}

DEFAULT_CONTEXT = 4096
DEFAULT_QUANT = "q4_k_m"

# Calibrated so a 7B model at 4096 tokens needs ~2 GB of fp16 KV cache.
KV_GB_PER_TOKEN_PER_BILLION = 7.0e-5
GIB_PER_BILLION_BYTES = 1_000_000_000 / (1024**3)
CUDA_OVERHEAD_GB = 0.7
ACTIVATION_OVERHEAD_RATIO = 0.10
VRAM_USABLE_RATIO = 0.95
RAM_USABLE_RATIO = 0.90
CONTEXT_STEP = 512

PARAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b\b")
MOE_PARAM_RE = re.compile(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*b\b")
MOE_RE = re.compile(r"\d\s*x\s*\d")


class EstimateError(ValueError):
    """Raised when a model fit cannot be estimated from the given inputs."""


@dataclass(frozen=True)
class Suggestion:
    key: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FitInputs:
    model: str
    params_billion: float
    quant: str
    bits_per_weight: float
    context_tokens: int


@dataclass(frozen=True)
class FitEstimate:
    inputs: FitInputs
    weights_gb: float
    kv_cache_gb: float
    overhead_gb: float
    total_gb: float
    vram_gb: float | None
    ram_gb: float | None
    status: str
    suggestions: list[Suggestion]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.inputs.model,
            "params_billion": self.inputs.params_billion,
            "quant": self.inputs.quant,
            "bits_per_weight": self.inputs.bits_per_weight,
            "context_tokens": self.inputs.context_tokens,
            "weights_gb": self.weights_gb,
            "kv_cache_gb": self.kv_cache_gb,
            "overhead_gb": self.overhead_gb,
            "total_gb": self.total_gb,
            "vram_gb": self.vram_gb,
            "ram_gb": self.ram_gb,
            "status": self.status,
            "suggestions": [{"key": s.key, "data": s.data} for s in self.suggestions],
            "notes": list(self.notes),
        }


def estimate_fit(
    model: str,
    *,
    params_billion: float | None = None,
    quant: str = DEFAULT_QUANT,
    context_tokens: int = DEFAULT_CONTEXT,
    vram_gb: float | None = None,
    ram_gb: float | None = None,
) -> FitEstimate:
    if context_tokens <= 0:
        raise EstimateError("Context length must be greater than 0.")

    params = params_billion if params_billion is not None else _parse_params(model)
    if params is None:
        raise EstimateError(
            f"Could not infer parameter count from model name '{model}'. "
            "Pass --params (in billions), for example --params 32."
        )
    if params <= 0:
        raise EstimateError("Parameter count must be greater than 0.")

    quant_key, bits = _resolve_bits(quant)

    weights_gb = params * (bits / 8.0) * GIB_PER_BILLION_BYTES
    kv_per_token_gb = params * KV_GB_PER_TOKEN_PER_BILLION
    kv_cache_gb = kv_per_token_gb * context_tokens
    overhead_gb = CUDA_OVERHEAD_GB + weights_gb * ACTIVATION_OVERHEAD_RATIO
    total_gb = weights_gb + kv_cache_gb + overhead_gb

    notes: list[str] = ["approximate"]
    if params_billion is None and MOE_RE.search(model.lower()):
        notes.append("moe")

    status, suggestions = _decide(
        weights_gb=weights_gb,
        overhead_gb=overhead_gb,
        total_gb=total_gb,
        kv_per_token_gb=kv_per_token_gb,
        vram_gb=vram_gb,
        ram_gb=ram_gb,
    )

    inputs = FitInputs(
        model=model,
        params_billion=round(params, 2),
        quant=quant_key,
        bits_per_weight=bits,
        context_tokens=context_tokens,
    )
    return FitEstimate(
        inputs=inputs,
        weights_gb=round(weights_gb, 2),
        kv_cache_gb=round(kv_cache_gb, 2),
        overhead_gb=round(overhead_gb, 2),
        total_gb=round(total_gb, 2),
        vram_gb=vram_gb,
        ram_gb=ram_gb,
        status=status,
        suggestions=suggestions,
        notes=notes,
    )


def _decide(
    *,
    weights_gb: float,
    overhead_gb: float,
    total_gb: float,
    kv_per_token_gb: float,
    vram_gb: float | None,
    ram_gb: float | None,
) -> tuple[str, list[Suggestion]]:
    if vram_gb is None:
        return "unknown_vram", [Suggestion("run_hardware")]

    usable = vram_gb * VRAM_USABLE_RATIO
    if total_gb <= usable:
        return "fits", [Suggestion("good_fit")]

    base = weights_gb + overhead_gb
    if base < usable and kv_per_token_gb > 0:
        leftover = usable - base
        max_ctx = (int(leftover / kv_per_token_gb) // CONTEXT_STEP) * CONTEXT_STEP
        if max_ctx >= CONTEXT_STEP:
            return "tight", [
                Suggestion("reduce_context", {"target": max_ctx}),
                Suggestion("lower_quant"),
            ]

    suggestions = [Suggestion("lower_quant")]
    suggestions.extend(_offload_suggestions(weights_gb, ram_gb))
    return "no_fit", suggestions


def _offload_suggestions(weights_gb: float, ram_gb: float | None) -> list[Suggestion]:
    out: list[Suggestion] = [Suggestion("smaller_model")]
    if ram_gb is None:
        return out
    if weights_gb < ram_gb * RAM_USABLE_RATIO:
        out.append(Suggestion("cpu_offload"))
    else:
        out.append(Suggestion("no_cpu_offload"))
    return out


def _parse_params(model: str) -> float | None:
    normalized = model.lower()
    moe_match = MOE_PARAM_RE.search(normalized)
    if moe_match:
        experts = int(moe_match.group(1))
        expert_params = float(moe_match.group(2))
        return experts * expert_params

    matches = PARAM_RE.findall(normalized)
    if not matches:
        return None
    return max(float(match) for match in matches)


def _resolve_bits(quant: str) -> tuple[str, float]:
    key = quant.strip().lower()
    if key not in QUANT_BITS and key.isdigit():
        key = f"q{key}"
    if key not in QUANT_BITS:
        supported = ", ".join(sorted(QUANT_BITS))
        raise EstimateError(f"Unknown quantization '{quant}'. Supported: {supported}.")
    return key, QUANT_BITS[key]
