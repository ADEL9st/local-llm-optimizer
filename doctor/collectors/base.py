from __future__ import annotations

from typing import Any


class MetricCollector:
    name = "collector"

    def collect(self) -> dict[str, Any]:
        raise NotImplementedError
