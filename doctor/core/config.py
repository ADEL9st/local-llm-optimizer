from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from importlib import resources
from pathlib import Path
from typing import Any


SUPPORTED_BACKENDS = ("ollama", "lmstudio", "openai-compatible")
SUPPORTED_LANGUAGES = ("tr", "en")
SUPPORTED_ADVISOR_MODES = ("deterministic",)


class ConfigValidationError(ValueError):
    """Raised when a run config cannot be used safely."""


@dataclass(frozen=True)
class AdvisorConfig:
    enabled: bool = True
    mode: str = "deterministic"
    language: str | None = None

    def normalized(self, default_language: str) -> "AdvisorConfig":
        language = self.language or default_language
        if language == self.language:
            return self
        return replace(self, language=language)

    def to_dict(self, default_language: str) -> dict[str, Any]:
        data = asdict(self)
        data["language"] = self.language or default_language
        return data


@dataclass(frozen=True)
class RunConfig:
    backend: str
    model: str
    prompt: str
    lang: str = "tr"
    output_dir: Path = Path("runs")
    sample_interval: float = 1.0
    timeout_seconds: float = 300.0
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    advisor: AdvisorConfig = field(default_factory=AdvisorConfig)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["output_dir"] = str(self.output_dir)
        data["advisor"] = self.advisor.to_dict(self.lang)
        if data.get("api_key"):
            data["api_key"] = "<redacted>"
        return data

    def validate(self) -> None:
        validate_config(self)


def validate_config(config: RunConfig) -> None:
    errors: list[str] = []

    if config.backend not in SUPPORTED_BACKENDS:
        errors.append(
            f"Unsupported backend `{config.backend}`. Use one of: {', '.join(SUPPORTED_BACKENDS)}."
        )

    if not config.model or not config.model.strip():
        errors.append("Model name cannot be empty.")

    if not config.prompt or not config.prompt.strip():
        errors.append("Prompt cannot be empty.")

    if config.lang not in SUPPORTED_LANGUAGES:
        errors.append(f"Unsupported language `{config.lang}`. Use one of: tr, en.")

    if config.sample_interval <= 0:
        errors.append("--sample-interval must be greater than 0.")

    if config.timeout_seconds <= 0:
        errors.append("--timeout must be greater than 0.")

    if config.max_tokens is not None and config.max_tokens <= 0:
        errors.append("--max-tokens must be greater than 0 when provided.")

    if not 0 <= config.temperature <= 2:
        errors.append("--temperature must be between 0 and 2.")

    if config.backend == "openai-compatible" and not config.base_url:
        errors.append("--base-url is required for --backend openai-compatible.")

    if config.base_url and not config.base_url.startswith(("http://", "https://")):
        errors.append("--base-url must start with http:// or https://.")

    if config.advisor.mode not in SUPPORTED_ADVISOR_MODES:
        errors.append(
            "Unsupported advisor mode "
            f"`{config.advisor.mode}`. Use one of: {', '.join(SUPPORTED_ADVISOR_MODES)}."
        )

    advisor_language = config.advisor.language or config.lang
    if advisor_language not in SUPPORTED_LANGUAGES:
        errors.append(
            f"Unsupported advisor language `{advisor_language}`. Use one of: tr, en."
        )

    if errors:
        raise ConfigValidationError(" ".join(errors))


def load_locale(lang: str) -> dict[str, Any]:
    normalized = lang if lang in {"tr", "en"} else "en"
    locale_path = resources.files("doctor.locales").joinpath(f"{normalized}.json")
    with locale_path.open("r", encoding="utf-8") as file:
        return json.load(file)
