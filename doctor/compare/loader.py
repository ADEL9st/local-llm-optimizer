from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doctor.diagnosis.scoring import to_float


class RunLoadError(ValueError):
    """Raised when a run directory or run.json cannot be loaded for comparison."""


@dataclass(frozen=True)
class RunSummary:
    label: str
    source: Path
    backend: str | None
    model: str | None
    max_tokens: int | None
    success: bool
    duration_seconds: float | None
    words_per_second: float | None
    chars_per_second: float | None
    output_words: int | None
    cpu_avg: float | None
    ram_avg: float | None
    gpu_avg: float | None
    vram_used_avg_mb: float | None
    vram_peak_ratio_percent: float | None


def resolve_run_json(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "run.json"
        if not candidate.is_file():
            raise RunLoadError(f"No run.json found in directory: {path}")
        return candidate
    if path.is_file():
        return path
    raise RunLoadError(f"Run path does not exist: {path}")


def load_run_summary(path: Path, label: str) -> RunSummary:
    run_json = resolve_run_json(path)
    try:
        data = json.loads(run_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunLoadError(f"Could not read {run_json}: {exc}") from exc

    if not isinstance(data, dict):
        raise RunLoadError(f"Unexpected run.json structure in {run_json}")

    config = _as_dict(data.get("config"))
    backend_result = _as_dict(data.get("backend_result"))
    diagnosis = _as_dict(data.get("diagnosis"))
    summaries = _as_dict(diagnosis.get("summaries"))

    def summary_avg(metric: str) -> float | None:
        summary = summaries.get(metric)
        if isinstance(summary, dict):
            return to_float(summary.get("avg"))
        return None

    return RunSummary(
        label=label,
        source=run_json,
        backend=_as_str(config.get("backend")),
        model=_as_str(config.get("model")),
        max_tokens=_as_int(config.get("max_tokens")),
        success=bool(backend_result.get("success", False)),
        duration_seconds=to_float(backend_result.get("duration_seconds")),
        words_per_second=to_float(backend_result.get("words_per_second")),
        chars_per_second=to_float(backend_result.get("chars_per_second")),
        output_words=_as_int(backend_result.get("output_words")),
        cpu_avg=summary_avg("cpu_percent"),
        ram_avg=summary_avg("ram_percent"),
        gpu_avg=summary_avg("gpu_util_percent"),
        vram_used_avg_mb=summary_avg("vram_used_mb"),
        vram_peak_ratio_percent=to_float(diagnosis.get("vram_peak_ratio_percent")),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_int(value: Any) -> int | None:
    number = to_float(value)
    return int(number) if number is not None else None
