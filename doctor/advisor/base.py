from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AdvisorResult:
    enabled: bool
    mode: str
    language: str
    issue_key: str | None
    top_issue: str
    summary: str
    evidence: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AdvisorAgent:
    mode = "base"

    def advise(self, diagnosis: dict[str, Any]) -> AdvisorResult:
        raise NotImplementedError
