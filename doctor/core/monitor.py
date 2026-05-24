from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from doctor.collectors.base import MetricCollector


class MetricsMonitor:
    def __init__(self, collectors: list[MetricCollector], interval_seconds: float = 1.0):
        self.collectors = collectors
        self.interval_seconds = max(0.1, interval_seconds)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._rows: list[dict[str, Any]] = []

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="doctor-metrics-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> list[dict[str, Any]]:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval_seconds + 1.0)
        return self.rows

    @property
    def rows(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._rows)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.sample_once()
            self._stop_event.wait(self.interval_seconds)

    def sample_once(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        for collector in self.collectors:
            try:
                row.update(collector.collect())
            except Exception as exc:
                row[f"{collector.name}_error"] = str(exc)

        with self._lock:
            self._rows.append(row)

        return row
