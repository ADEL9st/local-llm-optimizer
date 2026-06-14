import pytest

from doctor.core.config import AdvisorConfig, ConfigValidationError, RunConfig, validate_config


def test_valid_ollama_config_passes_validation():
    validate_config(RunConfig("ollama", "llama3:latest", "Say hello"))


def test_openai_compatible_requires_base_url():
    with pytest.raises(ConfigValidationError, match="base-url"):
        validate_config(RunConfig("openai-compatible", "model", "prompt"))


def test_config_rejects_empty_model_and_prompt():
    with pytest.raises(ConfigValidationError) as exc:
        validate_config(RunConfig("ollama", "", ""))

    message = str(exc.value)
    assert "Model name cannot be empty" in message
    assert "Prompt cannot be empty" in message


def test_config_rejects_invalid_numbers():
    with pytest.raises(ConfigValidationError) as exc:
        validate_config(
            RunConfig(
                "ollama",
                "model",
                "prompt",
                sample_interval=0,
                timeout_seconds=-1,
                max_tokens=0,
                temperature=3,
            )
        )

    message = str(exc.value)
    assert "--sample-interval" in message
    assert "--timeout" in message
    assert "--max-tokens" in message
    assert "--temperature" in message


def test_config_redacts_api_key():
    config = RunConfig(
        "openai-compatible",
        "model",
        "prompt",
        base_url="http://localhost:1234/v1",
        api_key="secret",
    )

    assert config.to_dict()["api_key"] == "<redacted>"
    assert config.to_dict()["advisor"]["mode"] == "deterministic"
    assert config.to_dict()["advisor"]["language"] == "tr"


def test_config_rejects_invalid_advisor_mode():
    with pytest.raises(ConfigValidationError, match="advisor mode"):
        validate_config(
            RunConfig(
                "ollama",
                "model",
                "prompt",
                advisor=AdvisorConfig(mode="experimental"),
            )
        )
