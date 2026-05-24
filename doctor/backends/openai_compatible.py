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
            return self._result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=time.perf_counter() - start,
                output_text="",
                stderr="",
                return_code=None,
                error="Missing --base-url for OpenAI-compatible backend.",
            )

        payload = self._request_payload(model, prompt)
        request = self._request(payload)

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw_body = response.read().decode("utf-8", errors="replace")
                body = json.loads(raw_body)
                output_text = clean_backend_text(_extract_message_text(body))
                return self._result(
                    model=model,
                    prompt=prompt,
                    success=True,
                    duration_seconds=time.perf_counter() - start,
                    output_text=output_text,
                    stderr="",
                    return_code=response.status,
                    error=None,
                )
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            message = clean_backend_text(body) or str(exc)
            return self._result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=time.perf_counter() - start,
                output_text="",
                stderr=message,
                return_code=exc.code,
                error=message,
            )
        except (TimeoutError, URLError, json.JSONDecodeError) as exc:
            return self._result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=time.perf_counter() - start,
                output_text="",
                stderr=str(exc),
                return_code=None,
                error=str(exc),
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

    def _result(
        self,
        model: str,
        prompt: str,
        success: bool,
        duration_seconds: float,
        output_text: str,
        stderr: str,
        return_code: int | None,
        error: str | None,
    ) -> BackendResult:
        words = len(output_text.split())
        chars = len(output_text)
        words_per_second = words / duration_seconds if duration_seconds > 0 else None
        chars_per_second = chars / duration_seconds if duration_seconds > 0 else None

        return BackendResult(
            backend=self.name,
            model=model,
            prompt=prompt,
            success=success,
            duration_seconds=round(duration_seconds, 4),
            output_text=output_text,
            stderr=stderr,
            return_code=return_code,
            error=error,
            output_words=words,
            output_chars=chars,
            words_per_second=round(words_per_second, 4) if words_per_second is not None else None,
            chars_per_second=round(chars_per_second, 4) if chars_per_second is not None else None,
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
