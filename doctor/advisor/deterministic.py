from __future__ import annotations

from typing import Any

from doctor.advisor.base import AdvisorAgent, AdvisorResult
from doctor.core.config import RunConfig


SUPPORTED_ISSUES = (
    "vram_bottleneck",
    "ram_pressure",
    "cpu_inference_likely",
    "gpu_idle",
    "vram_high",
    "ram_pressure_soft",
)


class DeterministicAdvisor(AdvisorAgent):
    mode = "deterministic"

    def __init__(self, locale: dict[str, Any], config: RunConfig, enabled: bool = True):
        self.locale = locale
        self.config = config
        self.enabled = enabled

    def advise(self, diagnosis: dict[str, Any]) -> AdvisorResult:
        language = self.config.advisor.language or self.config.lang
        advisor_locale = self.locale["advisor"]

        if not self.enabled:
            return AdvisorResult(
                enabled=False,
                mode=self.mode,
                language=language,
                issue_key=None,
                top_issue=advisor_locale["disabled_title"],
                summary=advisor_locale["disabled_summary"],
                evidence=[],
                recommendations=[],
            )

        issue_key = _pick_issue_key(diagnosis)
        if issue_key is None:
            return AdvisorResult(
                enabled=True,
                mode=self.mode,
                language=language,
                issue_key=None,
                top_issue=advisor_locale["no_issue"]["title"],
                summary=advisor_locale["no_issue"]["summary"],
                evidence=[],
                recommendations=advisor_locale["no_issue"]["recommendations"],
            )

        issue = advisor_locale["issues"][issue_key]
        evidence = _build_evidence(issue_key, diagnosis, advisor_locale)

        return AdvisorResult(
            enabled=True,
            mode=self.mode,
            language=language,
            issue_key=issue_key,
            top_issue=issue["title"],
            summary=issue["summary"],
            evidence=evidence,
            recommendations=issue["recommendations"],
        )


def _pick_issue_key(diagnosis: dict[str, Any]) -> str | None:
    finding_keys = {finding["key"] for finding in diagnosis.get("findings", [])}
    for issue_key in SUPPORTED_ISSUES:
        if issue_key in finding_keys:
            return issue_key
    return None


def _build_evidence(
    issue_key: str,
    diagnosis: dict[str, Any],
    advisor_locale: dict[str, Any],
) -> list[str]:
    summaries = diagnosis.get("summaries", {})
    evidence = advisor_locale["issues"][issue_key].get("evidence", []).copy()
    dynamic_evidence: list[str] = []

    gpu = summaries.get("gpu_util_percent")
    cpu = summaries.get("cpu_percent")
    ram = summaries.get("ram_percent")
    vram = summaries.get("vram_used_mb")
    vram_ratio = diagnosis.get("vram_peak_ratio_percent")

    if issue_key == "gpu_idle":
        if gpu:
            dynamic_evidence.append(
                advisor_locale["templates"]["gpu_avg"].format(avg=gpu["avg"])
            )
        if vram_ratio is not None:
            dynamic_evidence.append(
                advisor_locale["templates"]["vram_ratio_low"].format(ratio=round(vram_ratio, 1))
            )
    elif issue_key in {"ram_pressure", "ram_pressure_soft"} and ram:
        dynamic_evidence.append(
            advisor_locale["templates"]["ram_max"].format(max=ram["max"], avg=ram["avg"])
        )
    elif issue_key in {"vram_bottleneck", "vram_high"}:
        if vram_ratio is not None:
            dynamic_evidence.append(
                advisor_locale["templates"]["vram_ratio_high"].format(ratio=round(vram_ratio, 1))
            )
        if vram:
            dynamic_evidence.append(
                advisor_locale["templates"]["vram_used"].format(max=vram["max"])
            )
    elif issue_key == "cpu_inference_likely":
        if cpu:
            dynamic_evidence.append(
                advisor_locale["templates"]["cpu_avg"].format(avg=cpu["avg"])
            )
        if gpu:
            dynamic_evidence.append(
                advisor_locale["templates"]["gpu_avg"].format(avg=gpu["avg"])
            )

    return dynamic_evidence or evidence
