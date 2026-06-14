from __future__ import annotations

from typing import Any

from doctor.collectors.base import MetricCollector


class MemoryCollector(MetricCollector):
    name = "memory"

    def collect(self) -> dict[str, Any]:
        try:
            import psutil
        except ImportError:
            return {
                "ram_percent": None,
                "ram_used_gb": None,
                "ram_total_gb": None,
                "memory_error": "psutil is not installed",
            }

        memory = psutil.virtual_memory()
        return {
            "ram_percent": memory.percent,
            "ram_used_gb": round(memory.used / (1024**3), 2),
            "ram_total_gb": round(memory.total / (1024**3), 2),
        }
