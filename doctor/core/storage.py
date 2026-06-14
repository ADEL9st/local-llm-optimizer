from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from doctor.advisor.base import AdvisorResult
from doctor.backends.base import BackendResult
from doctor.core.config import RunConfig


METRIC_FIELDS = [
    "timestamp",
    "cpu_percent",
    "ram_percent",
    "ram_used_gb",
    "ram_total_gb",
    "gpu_util_percent",
    "vram_used_mb",
    "vram_total_mb",
    "gpu_temp_c",
    "gpu_power_w",
    "cpu_error",
    "memory_error",
    "nvidia_error",
]


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    run_json: Path
    metrics_csv: Path
    report_md: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "run_dir": str(self.run_dir),
            "run_json": str(self.run_json),
            "metrics_csv": str(self.metrics_csv),
            "report_md": str(self.report_md),
        }


class RunStorage:
    def __init__(self, config: RunConfig):
        self.config = config

    def create_run_dir(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", self.config.model).strip("-")
        base_name = f"{timestamp}-{model_slug or 'model'}"
        attempt = 0

        while attempt < 100:
            suffix = "" if attempt == 0 else f"-{attempt}"
            run_dir = self.config.output_dir / f"{base_name}{suffix}"
            try:
                run_dir.mkdir(parents=True, exist_ok=False)
                return run_dir
            except FileExistsError:
                attempt += 1

        raise FileExistsError(f"Could not create a unique run directory for {base_name}")

    def write_all(
        self,
        backend_result: BackendResult,
        metrics: list[dict[str, Any]],
        diagnosis: dict[str, Any],
        advisor: AdvisorResult | None,
    ) -> RunArtifacts:
        run_dir = self.create_run_dir()
        artifacts = RunArtifacts(
            run_dir=run_dir,
            run_json=run_dir / "run.json",
            metrics_csv=run_dir / "metrics.csv",
            report_md=run_dir / "report.md",
        )

        self.write_metrics(artifacts.metrics_csv, metrics)
        self.write_run_json(artifacts, backend_result, diagnosis, advisor)
        return artifacts

    def write_metrics(self, path: Path, rows: list[dict[str, Any]]) -> None:
        extra_fields = sorted(
            {
                key
                for row in rows
                for key in row.keys()
                if key not in METRIC_FIELDS
            }
        )
        fieldnames = METRIC_FIELDS + extra_fields

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def write_run_json(
        self,
        artifacts: RunArtifacts,
        backend_result: BackendResult,
        diagnosis: dict[str, Any],
        advisor: AdvisorResult | None,
    ) -> None:
        payload = {
            "schema_version": "0.2",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "config": self.config.to_dict(),
            "backend_result": asdict(backend_result),
            "diagnosis": diagnosis,
            "advisor": advisor.to_dict() if advisor is not None else None,
            "artifacts": artifacts.to_dict(),
        }
        artifacts.run_json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
