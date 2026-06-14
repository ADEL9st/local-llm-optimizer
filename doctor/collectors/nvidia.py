from __future__ import annotations

import csv
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from doctor.collectors.base import MetricCollector


COMMON_NVIDIA_SMI_PATHS = [
    Path(r"C:\Windows\System32\nvidia-smi.exe"),
    Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"),
]
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


class NvidiaCollector(MetricCollector):
    name = "nvidia"

    empty_metrics = {
        "gpu_util_percent": None,
        "vram_used_mb": None,
        "vram_total_mb": None,
        "gpu_temp_c": None,
        "gpu_power_w": None,
    }

    def collect(self) -> dict[str, Any]:
        nvidia_smi = find_nvidia_smi()
        if nvidia_smi is None:
            return {
                **self.empty_metrics,
                "nvidia_error": "nvidia-smi was not found. On Windows, check NVIDIA driver installation and PATH.",
            }

        try:
            result = subprocess.run(
                [
                    str(nvidia_smi),
                    "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=2,
            )
        except Exception as exc:
            return {**self.empty_metrics, "nvidia_error": str(exc)}

        if result.returncode != 0:
            message = (result.stderr or result.stdout or "nvidia-smi failed").strip()
            return {**self.empty_metrics, "nvidia_error": message}

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            return {**self.empty_metrics, "nvidia_error": "nvidia-smi returned no GPU rows"}

        parts = next(csv.reader([lines[0]], skipinitialspace=True))
        if len(parts) != 5:
            return {
                **self.empty_metrics,
                "nvidia_error": f"Unexpected nvidia-smi output: {lines[0]}",
            }

        gpu_util, vram_used, vram_total, temp, power = [to_float(part) for part in parts]
        if gpu_util is None or vram_used is None or vram_total is None:
            return {
                **self.empty_metrics,
                "nvidia_error": f"Could not parse required nvidia-smi metrics: {lines[0]}",
            }

        # Some Windows driver/GPU combinations report power.draw as N/A.
        # Keep the rest of the GPU metrics instead of dropping the sample.

        return {
            "gpu_util_percent": gpu_util,
            "vram_used_mb": vram_used,
            "vram_total_mb": vram_total,
            "gpu_temp_c": temp,
            "gpu_power_w": power,
        }


def find_nvidia_smi() -> Path | None:
    path = shutil.which("nvidia-smi") or shutil.which("nvidia-smi.exe")
    if path:
        return Path(path)

    for candidate in COMMON_NVIDIA_SMI_PATHS:
        if candidate.exists():
            return candidate

    return None


def to_float(value: str) -> float | None:
    text = value.strip()
    if not text or text.lower() in {"n/a", "[n/a]", "not supported", "[not supported]"}:
        return None

    match = NUMBER_RE.search(text)
    return float(match.group(0)) if match else None
