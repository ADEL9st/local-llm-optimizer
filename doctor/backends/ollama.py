from __future__ import annotations

import os
import subprocess
import time

from doctor.backends.base import BackendResult, BenchmarkBackend
from doctor.backends.text import clean_backend_text


class OllamaBackend(BenchmarkBackend):
    name = "ollama"

    def run(self, model: str, prompt: str, timeout_seconds: float) -> BackendResult:
        start = time.perf_counter()
        command = ["ollama", "run", "--nowordwrap", model, prompt]
        env = os.environ.copy()
        env["NO_COLOR"] = "1"
        env["TERM"] = "dumb"

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                env=env,
            )
            duration = time.perf_counter() - start
            output = clean_backend_text(completed.stdout)
            stderr = clean_backend_text(completed.stderr)
            success = completed.returncode == 0
            error = None if success else friendly_ollama_error(stderr, completed.returncode)

            return self._result(
                model=model,
                prompt=prompt,
                success=success,
                duration_seconds=duration,
                output_text=output,
                stderr="" if success else stderr,
                return_code=completed.returncode,
                error=error,
            )
        except FileNotFoundError:
            duration = time.perf_counter() - start
            return self._result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=duration,
                output_text="",
                stderr="",
                return_code=None,
                error=(
                    "Ollama CLI was not found. Install Ollama and make sure "
                    "`ollama --version` works in this terminal."
                ),
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - start
            stdout = clean_backend_text(exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = clean_backend_text(exc.stderr or "") if isinstance(exc.stderr, str) else ""
            return self._result(
                model=model,
                prompt=prompt,
                success=False,
                duration_seconds=duration,
                output_text=stdout,
                stderr=stderr,
                return_code=None,
                error=(
                    f"Ollama benchmark timed out after {timeout_seconds:.1f}s. "
                    "If the model is still loading, try a longer --timeout or run a warmup first."
                ),
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


def friendly_ollama_error(stderr: str, return_code: int | None) -> str:
    message = stderr.strip()
    lowered = message.lower()

    server_down_markers = [
        "could not connect to ollama",
        "connection refused",
        "actively refused",
        "server not responding",
        "no connection could be made",
    ]
    if any(marker in lowered for marker in server_down_markers):
        return (
            "Ollama CLI is installed, but the Ollama server is not responding. "
            "Start the Ollama app or run `ollama serve`, then retry."
        )

    if "model" in lowered and ("not found" in lowered or "pull" in lowered):
        return (
            "Ollama could not load the requested model. Check the model name with "
            f"`ollama list` or pull it with `ollama pull <model>`. Details: {message}"
        )

    if message:
        return f"Ollama failed: {message}"

    return f"Ollama failed with exit code {return_code}, but did not return an error message."
