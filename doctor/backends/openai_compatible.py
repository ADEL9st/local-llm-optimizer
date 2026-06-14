from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from doctor.backends.base import BackendResult, BenchmarkBackend
from doctor.backends.text import clean_backend_text


class OpenAICompatibleBackend(BenchmarkBackend):
    name = "openai-compatible"
    display_name = "The OpenAI-compatible server"
    default_base_url: str | None = None

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ):
        self.base_url = (base_url or self.default_base_url or "").rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens

    def run(self, model: str, prompt: str, timeout_seconds: float) -> BackendResult:
        start = time.perf_counter()

        if not self.base_url:
            return self.build_result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=time.perf_counter() - start,
                output_text="",
                stderr="",
                return_code=None,
                error=f"Missing base URL for the {self.name} backend.",
            )

        request = self._request(self._request_payload(model, prompt))

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status = response.status
                raw_body = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return self.build_result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=time.perf_counter() - start,
                output_text="",
                stderr=raw[:1000],
                return_code=exc.code,
                error=self._http_error_message(raw, exc),
            )
        except (TimeoutError, URLError) as exc:
            return self.build_result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=time.perf_counter() - start,
                output_text="",
                stderr=str(exc),
                return_code=None,
                error=self._connection_error(exc, timeout_seconds),
            )

        duration = time.perf_counter() - start

        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            return self.build_result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=duration,
                output_text="",
                stderr=raw_body[:1000],
                return_code=status,
                error=f"{self.display_name} returned a response that was not valid JSON.",
            )

        output_text = clean_backend_text(_extract_message_text(body))
        if not output_text:
            api_error = _extract_api_error(body)
            message = api_error or (
                f"{self.display_name} returned an empty completion. "
                "Check that a model is loaded and the model name is correct."
            )
            return self.build_result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=duration,
                output_text="",
                stderr=raw_body[:1000],
                return_code=status,
                error=message,
            )

        return self.build_result(
            model=model,
            prompt=prompt,
            success=True,
            duration_seconds=duration,
            output_text=output_text,
            stderr="",
            return_code=status,
            error=None,
        )

    def _request_payload(self, model: str, prompt: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        return payload

    def _request(self, payload: dict[str, Any]) -> Request:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    def _http_error_message(self, raw_body: str, exc: HTTPError) -> str:
        api_error = _extract_api_error(_safe_json(raw_body))
        detail = api_error or clean_backend_text(raw_body) or str(exc.reason)
        return f"{self.display_name} returned HTTP {exc.code}: {detail}".strip()

    def _connection_error(self, exc: BaseException, timeout_seconds: float) -> str:
        reason = getattr(exc, "reason", exc)
        if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError):
            return (
                f"{self.display_name} did not respond within {timeout_seconds:.1f}s "
                f"at {self.base_url}. Try a longer --timeout or check that the model is loaded."
            )
        return (
            f"{self.display_name} is not reachable at {self.base_url}. "
            f"Start the server and load a model, then retry. Details: {reason}"
        )


def _extract_message_text(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        return ""

    first_choice = choices[0] or {}
    message = first_choice.get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    text = first_choice.get("text")
    return text if isinstance(text, str) else ""


def _extract_api_error(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None

    error = body.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        return message if isinstance(message, str) and message.strip() else None
    if isinstance(error, str) and error.strip():
        return error
    return None


def _safe_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
