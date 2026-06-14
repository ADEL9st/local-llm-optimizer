import io
import json
from urllib.error import HTTPError, URLError

import pytest

from doctor.backends import openai_compatible as oc
from doctor.backends.lmstudio import LMStudioBackend
from doctor.backends.openai_compatible import (
    OpenAICompatibleBackend,
    _extract_api_error,
    _extract_message_text,
)


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, handler):
    monkeypatch.setattr(oc, "urlopen", handler)


def test_missing_base_url_fails_without_request():
    backend = OpenAICompatibleBackend(base_url=None)
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "Missing base URL" in result.error


def test_successful_completion(monkeypatch):
    body = json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": "hello world"}}]}
    )
    _patch_urlopen(monkeypatch, lambda req, timeout: _FakeResponse(200, body))

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is True
    assert result.output_text == "hello world"
    assert result.output_words == 2
    assert result.return_code == 200


def test_empty_completion_is_failure(monkeypatch):
    body = json.dumps({"choices": [{"message": {"content": ""}}]})
    _patch_urlopen(monkeypatch, lambda req, timeout: _FakeResponse(200, body))

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "empty completion" in result.error


def test_api_error_body_is_surfaced(monkeypatch):
    body = json.dumps({"error": {"message": "model not loaded"}})
    _patch_urlopen(monkeypatch, lambda req, timeout: _FakeResponse(200, body))

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert result.error == "model not loaded"


def test_non_json_response_is_failure(monkeypatch):
    _patch_urlopen(monkeypatch, lambda req, timeout: _FakeResponse(200, "<html>oops</html>"))

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "not valid JSON" in result.error


def test_http_error_includes_status_and_detail(monkeypatch):
    payload = json.dumps({"error": {"message": "bad request detail"}})

    def _raise(req, timeout):
        raise HTTPError(
            url="http://localhost:1234/v1/chat/completions",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(payload.encode("utf-8")),
        )

    _patch_urlopen(monkeypatch, _raise)

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "HTTP 400" in result.error
    assert "bad request detail" in result.error
    assert result.return_code == 400


def test_connection_refused_is_friendly(monkeypatch):
    def _raise(req, timeout):
        raise URLError("Connection refused")

    _patch_urlopen(monkeypatch, _raise)

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "is not reachable" in result.error


def test_timeout_is_friendly(monkeypatch):
    def _raise(req, timeout):
        raise TimeoutError("timed out")

    _patch_urlopen(monkeypatch, _raise)

    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "did not respond" in result.error


def test_lmstudio_display_name_in_error(monkeypatch):
    def _raise(req, timeout):
        raise URLError("Connection refused")

    _patch_urlopen(monkeypatch, _raise)

    backend = LMStudioBackend(base_url="http://localhost:1234/v1")
    result = backend.run("model", "prompt", timeout_seconds=5)

    assert result.success is False
    assert "LM Studio" in result.error


def test_extract_message_text_handles_string_content():
    body = {"choices": [{"message": {"content": "plain text"}}]}
    assert _extract_message_text(body) == "plain text"


def test_extract_message_text_handles_list_content():
    body = {
        "choices": [
            {"message": {"content": [{"text": "a"}, {"text": "b"}, "c"]}}
        ]
    }
    assert _extract_message_text(body) == "abc"


def test_extract_message_text_handles_completion_text():
    body = {"choices": [{"text": "legacy completion"}]}
    assert _extract_message_text(body) == "legacy completion"


def test_extract_message_text_handles_empty_choices():
    assert _extract_message_text({"choices": []}) == ""


def test_extract_api_error_variants():
    assert _extract_api_error({"error": {"message": "boom"}}) == "boom"
    assert _extract_api_error({"error": "string error"}) == "string error"
    assert _extract_api_error({"error": {"message": "  "}}) is None
    assert _extract_api_error({}) is None
    assert _extract_api_error("not a dict") is None


def test_build_result_computes_throughput():
    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.build_result(
        model="m",
        prompt="p",
        success=True,
        duration_seconds=2.0,
        output_text="one two three four",
        stderr="",
        return_code=200,
        error=None,
    )

    assert result.output_words == 4
    assert result.output_chars == len("one two three four")
    assert result.words_per_second == 2.0


def test_build_result_zero_duration_yields_none_rates():
    backend = OpenAICompatibleBackend(base_url="http://localhost:1234/v1")
    result = backend.build_result(
        model="m",
        prompt="p",
        success=True,
        duration_seconds=0.0,
        output_text="word",
        stderr="",
        return_code=200,
        error=None,
    )

    assert result.words_per_second is None
    assert result.chars_per_second is None
