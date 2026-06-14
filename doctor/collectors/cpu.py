from __future__ import annotations

from typing import Any

from doctor.collectors.base import MetricCollector


class CpuCollector(MetricCollector):
    name = "cpu"

    def collect(self) -> dict[str, Any]:
        try:
            import psutil
        except ImportError:
            return {"cpu_percent": None, "cpu_error": "psutil is not installed"}

        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
        }
