from __future__ import annotations

from doctor.advisor.base import AdvisorAgent, AdvisorResult
from doctor.advisor.deterministic import DeterministicAdvisor
from doctor.core.config import RunConfig


def build_advisor(config: RunConfig, locale: dict[str, object]) -> AdvisorAgent:
    if not config.advisor.enabled:
        return DeterministicAdvisor(locale, config, enabled=False)

    if config.advisor.mode == "deterministic":
        return DeterministicAdvisor(locale, config, enabled=True)

    raise ValueError(f"Unsupported advisor mode: {config.advisor.mode}")


__all__ = ["AdvisorAgent", "AdvisorResult", "DeterministicAdvisor", "build_advisor"]
