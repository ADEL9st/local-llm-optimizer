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
