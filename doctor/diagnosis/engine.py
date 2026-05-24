from __future__ import annotations

from typing import Any

from doctor.backends.base import BackendResult
from doctor.diagnosis.scoring import max_ratio, metric_values, summarize


class DiagnosisEngine:
    def __init__(self, locale: dict[str, Any]):
        self.locale = locale

    def analyze(
        self,
        backend_result: BackendResult,
        metrics: list[dict[str, Any]],
    ) -> dict[str, Any]:
        summaries = {
            "cpu_percent": summarize(metrics, "cpu_percent"),
            "ram_percent": summarize(metrics, "ram_percent"),
            "gpu_util_percent": summarize(metrics, "gpu_util_percent"),
            "vram_used_mb": summarize(metrics, "vram_used_mb"),
        }
        vram_ratio = max_ratio(
            metric_values(metrics, "vram_used_mb"),
            metric_values(metrics, "vram_total_mb"),
        )

        findings: list[dict[str, Any]] = []
        recommendations: list[str] = []

        cpu = summaries["cpu_percent"]
        ram = summaries["ram_percent"]
        gpu = summaries["gpu_util_percent"]

        if not backend_result.success:
            self._add_finding(findings, recommendations, "backend_failed", "warning")

        self._check_gpu(cpu, gpu, findings, recommendations)
        self._check_ram(ram, findings, recommendations)
        self._check_vram(vram_ratio, findings, recommendations)

        if not findings:
            self._add_finding(findings, recommendations, "no_clear_bottleneck", "info")

        return {
            "summaries": summaries,
            "vram_peak_ratio_percent": round(vram_ratio, 2) if vram_ratio is not None else None,
            "findings": findings,
            "recommendations": _dedupe(recommendations),
        }

    def _check_gpu(
        self,
        cpu: dict[str, float] | None,
        gpu: dict[str, float] | None,
        findings: list[dict[str, Any]],
        recommendations: list[str],
    ) -> None:
        if gpu is None:
            self._add_finding(findings, recommendations, "gpu_missing", "info")
            if cpu and cpu["avg"] >= 50:
                self._add_finding(findings, recommendations, "cpu_inference_likely", "warning")
            return

        if gpu["avg"] >= 15 or gpu["max"] >= 40:
            return

        self._add_finding(findings, recommendations, "gpu_idle", "warning")
        if cpu and cpu["avg"] >= 50:
            self._add_finding(findings, recommendations, "cpu_inference_likely", "warning")

    def _check_ram(
        self,
        ram: dict[str, float] | None,
        findings: list[dict[str, Any]],
        recommendations: list[str],
    ) -> None:
        if not ram:
            return

        if ram["max"] >= 90:
            self._add_finding(findings, recommendations, "ram_pressure", "critical")
        elif ram["avg"] >= 80:
            self._add_finding(findings, recommendations, "ram_pressure_soft", "warning")

    def _check_vram(
        self,
        vram_ratio: float | None,
        findings: list[dict[str, Any]],
        recommendations: list[str],
    ) -> None:
        if vram_ratio is None:
            return

        ratio = round(vram_ratio, 1)
        if ratio >= 90:
            self._add_finding(
                findings,
                recommendations,
                "vram_bottleneck",
                "critical",
                ratio=ratio,
            )
        elif ratio >= 75:
            self._add_finding(
                findings,
                recommendations,
                "vram_high",
                "warning",
                ratio=ratio,
            )

    def _add_finding(
        self,
        findings: list[dict[str, Any]],
        recommendations: list[str],
        key: str,
        severity: str,
        **params: Any,
    ) -> None:
        findings.append(self._finding(key, severity, **params))
        recommendation = self.locale["recommendations"].get(key)
        if recommendation:
            recommendations.append(recommendation)

    def _finding(self, key: str, severity: str, **params: Any) -> dict[str, Any]:
        template = self.locale["findings"][key]
        title = template["title"].format(**params)
        detail = template["detail"].format(**params)
        return {
            "key": key,
            "severity": severity,
            "title": title,
            "detail": detail,
        }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
