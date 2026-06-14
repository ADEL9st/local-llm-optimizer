from __future__ import annotations

from pathlib import Path
from typing import Any

from doctor.hardware.profile import HardwareProfile


class HardwareReporter:
    def __init__(self, locale: dict[str, Any]):
        hardware = locale.get("hardware", {})
        self.title = hardware.get("title", "Hardware Profile")
        self.labels = hardware.get("labels", {})

    def render(self, profile: HardwareProfile, output_path: Path | None = None) -> str:
        text = "\n".join(self._lines(profile, output_path))
        print(text)
        return text

    def _lines(self, profile: HardwareProfile, output_path: Path | None) -> list[str]:
        labels = self.labels
        unknown = labels.get("unknown", "unknown")

        rows: list[tuple[str, str]] = [
            (labels.get("os", "OS"), self._os(profile, unknown)),
            (labels.get("cpu", "CPU"), self._cpu(profile, unknown)),
            (labels.get("ram", "RAM"), self._ram(profile, unknown)),
            (labels.get("gpu", "GPU"), self._gpu(profile)),
            (labels.get("vram", "VRAM"), self._vram(profile)),
            (labels.get("cuda", "CUDA"), self._cuda(profile)),
        ]

        driver = self._driver(profile)
        if driver:
            rows.append((labels.get("driver", "Driver"), driver))
        rows.append((labels.get("python", "Python"), profile.python_version or unknown))

        width = max(len(label) for label, _ in rows)
        lines = ["", f"=== {self.title} ==="]
        lines += [f"{label.ljust(width)} : {value}" for label, value in rows]

        if profile.notes:
            lines.append("")
            lines.append(f"--- {labels.get('notes_title', 'Notes')} ---")
            lines += [f"- {note}" for note in profile.notes]

        if output_path is not None:
            lines.append("")
            lines.append(f"{labels.get('saved_to', 'Saved to')}: {output_path}")

        return lines

    def _os(self, profile: HardwareProfile, unknown: str) -> str:
        name = profile.os_name or unknown
        return f"{name} {profile.os_release}".strip() if profile.os_release else name

    def _cpu(self, profile: HardwareProfile, unknown: str) -> str:
        name = profile.cpu_name or unknown
        physical = profile.cpu_physical_cores
        logical = profile.cpu_logical_cores
        if physical is None and logical is None:
            return name

        cores_label = self.labels.get("cores", "cores")
        threads_label = self.labels.get("threads", "threads")
        physical_text = physical if physical is not None else "?"
        logical_text = logical if logical is not None else "?"
        return f"{name} ({physical_text} {cores_label} / {logical_text} {threads_label})"

    def _ram(self, profile: HardwareProfile, unknown: str) -> str:
        if profile.ram_total_gb is None:
            return unknown
        return f"{_trim(profile.ram_total_gb)} GB"

    def _gpu(self, profile: HardwareProfile) -> str:
        if not profile.gpus:
            return self.labels.get("none_detected", "none detected")
        return ", ".join(gpu.name for gpu in profile.gpus)

    def _vram(self, profile: HardwareProfile) -> str:
        gpu = profile.primary_gpu
        if gpu is None or gpu.vram_total_mb is None:
            return self.labels.get("none_detected", "none detected")
        return f"{_trim(round(gpu.vram_total_mb / 1024, 1))} GB"

    def _cuda(self, profile: HardwareProfile) -> str:
        if not profile.cuda_available:
            return self.labels.get("not_available", "not available")
        available = self.labels.get("available", "available")
        if profile.cuda_version:
            return f"{available} ({profile.cuda_version})"
        return available

    def _driver(self, profile: HardwareProfile) -> str | None:
        gpu = profile.primary_gpu
        return gpu.driver_version if gpu is not None else None


def _trim(value: float) -> float | int:
    rounded = round(value, 2)
    return int(rounded) if rounded == int(rounded) else rounded
