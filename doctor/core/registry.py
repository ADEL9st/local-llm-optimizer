from __future__ import annotations

from dataclasses import replace

from doctor.backends.base import BenchmarkBackend
from doctor.backends.lmstudio import LMStudioBackend
from doctor.backends.ollama import OllamaBackend
from doctor.backends.openai_compatible import OpenAICompatibleBackend
from doctor.collectors.base import MetricCollector
from doctor.collectors.cpu import CpuCollector
from doctor.collectors.memory import MemoryCollector
from doctor.collectors.nvidia import NvidiaCollector
from doctor.core.config import RunConfig, SUPPORTED_BACKENDS


BACKEND_NAMES = list(SUPPORTED_BACKENDS)


def normalize_backend_config(config: RunConfig) -> RunConfig:
    base_url = config.base_url.rstrip("/") if config.base_url else None

    if config.backend == "lmstudio":
        base_url = normalize_lmstudio_base_url(base_url)

    if base_url != config.base_url:
        return replace(config, base_url=base_url)

    return config


def normalize_lmstudio_base_url(base_url: str | None) -> str:
    normalized = (base_url or LMStudioBackend.default_base_url).rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def get_backend(name: str, config: RunConfig) -> BenchmarkBackend:
    if name == "ollama":
        return OllamaBackend()
    if name == "lmstudio":
        return LMStudioBackend(
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    if name == "openai-compatible":
        return OpenAICompatibleBackend(
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    raise ValueError(f"Unsupported backend: {name}")


def build_collectors() -> list[MetricCollector]:
    return [
        CpuCollector(),
        MemoryCollector(),
        NvidiaCollector(),
    ]
