import pytest

from doctor.backends.lmstudio import LMStudioBackend
from doctor.backends.ollama import OllamaBackend
from doctor.backends.openai_compatible import OpenAICompatibleBackend
from doctor.core.config import RunConfig
from doctor.core.registry import (
    BACKEND_NAMES,
    get_backend,
    normalize_backend_config,
    normalize_lmstudio_base_url,
)


def test_registry_contains_supported_backends():
    assert BACKEND_NAMES == ["ollama", "lmstudio", "openai-compatible"]


def test_get_backend_returns_expected_backend_types():
    assert isinstance(get_backend("ollama", RunConfig("ollama", "m", "p")), OllamaBackend)
    assert isinstance(get_backend("lmstudio", RunConfig("lmstudio", "m", "p")), LMStudioBackend)
    assert isinstance(
        get_backend(
            "openai-compatible",
            RunConfig("openai-compatible", "m", "p", base_url="http://localhost:1234/v1"),
        ),
        OpenAICompatibleBackend,
    )


def test_get_backend_rejects_unknown_backend():
    with pytest.raises(ValueError):
        get_backend("missing", RunConfig("ollama", "m", "p"))


def test_lmstudio_base_url_normalization():
    assert normalize_lmstudio_base_url(None) == "http://localhost:1234/v1"
    assert normalize_lmstudio_base_url("http://localhost:1234") == "http://localhost:1234/v1"
    assert normalize_lmstudio_base_url("http://localhost:1234/v1/") == "http://localhost:1234/v1"


def test_normalize_backend_config_adds_lmstudio_base_url():
    config = normalize_backend_config(RunConfig("lmstudio", "model", "prompt"))

    assert config.base_url == "http://localhost:1234/v1"
