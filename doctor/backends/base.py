from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendResult:
    backend: str
    model: str
    prompt: str
    success: bool
    duration_seconds: float
    output_text: str
    stderr: str
    return_code: int | None
    error: str | None = None
    output_words: int = 0
    output_chars: int = 0
    words_per_second: float | None = None
    chars_per_second: float | None = None


class BenchmarkBackend:
    name = "base"

    def run(self, model: str, prompt: str, timeout_seconds: float) -> BackendResult:
        raise NotImplementedError

    def build_result(
        self,
        *,
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
