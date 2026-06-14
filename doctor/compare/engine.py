from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from doctor.compare.loader import RunSummary

REL_THRESHOLD_PERCENT = 3.0


@dataclass(frozen=True)
class MetricRow:
    key: str
    unit: str
    lower_is_better: bool
    a: float | None
    b: float | None
    delta_percent: float | None
    better: str | None  # "A", "B", or None for tie / not comparable


@dataclass(frozen=True)
class ComparisonResult:
    run_a: RunSummary
    run_b: RunSummary
    rows: list[MetricRow]
    insights: list[str]
    recommendation: str


# (metric key, RunSummary attribute, unit, lower_is_better)
_METRICS: list[tuple[str, str, str, bool]] = [
    ("duration_seconds", "duration_seconds", "s", True),
    ("words_per_second", "words_per_second", "w/s", False),
    ("chars_per_second", "chars_per_second", "c/s", False),
    ("cpu_avg", "cpu_avg", "%", True),
    ("ram_avg", "ram_avg", "%", True),
    ("gpu_avg", "gpu_avg", "%", False),
    ("vram_used_avg_mb", "vram_used_avg_mb", "MB", True),
    ("vram_peak_ratio_percent", "vram_peak_ratio_percent", "%", True),
]


def compare_runs(
    run_a: RunSummary,
    run_b: RunSummary,
    locale: dict[str, Any],
) -> ComparisonResult:
    rows = [
        _build_row(key, getattr(run_a, attr), getattr(run_b, attr), unit, lower)
        for key, attr, unit, lower in _METRICS
    ]

    templates = _section(locale, "templates")
    run_label = _section(locale, "labels").get("run_label", "Run")

    def name(summary: RunSummary) -> str:
        return f"{run_label} {summary.label}".strip()

    insights = _build_insights(run_a, run_b, templates, name)
    recommendation = _build_recommendation(run_a, run_b, templates, name)

    return ComparisonResult(
        run_a=run_a,
        run_b=run_b,
        rows=rows,
        insights=insights,
        recommendation=recommendation,
    )


def _build_row(
    key: str,
    a: float | None,
    b: float | None,
    unit: str,
    lower_is_better: bool,
) -> MetricRow:
    delta = _relative_delta(a, b)
    better = _decide_better(a, b, lower_is_better, delta)
    return MetricRow(
        key=key,
        unit=unit,
        lower_is_better=lower_is_better,
        a=a,
        b=b,
        delta_percent=round(delta, 1) if delta is not None else None,
        better=better,
    )


def _build_insights(
    run_a: RunSummary,
    run_b: RunSummary,
    templates: dict[str, str],
    name: Callable[[RunSummary], str],
) -> list[str]:
    insights: list[str] = []

    if not run_a.success or not run_b.success:
        failed = run_a if not run_a.success else run_b
        line = _format(templates, "failed_run", run=name(failed))
        if line:
            insights.append(line)

    speed = _speed_insight(run_a, run_b, templates, name)
    if speed:
        insights.append(speed)

    ram = _lower_is_better_insight(
        run_a, run_b, "ram_avg", "less_ram", templates, name, min_abs=1.0
    )
    if ram:
        insights.append(ram)

    gpu = _gpu_insight(run_a, run_b, templates, name)
    if gpu:
        insights.append(gpu)

    vram = _lower_is_better_insight(
        run_a, run_b, "vram_used_avg_mb", "lower_vram", templates, name, min_abs=64.0
    )
    if vram:
        insights.append(vram)

    return insights


def _speed_insight(
    run_a: RunSummary,
    run_b: RunSummary,
    templates: dict[str, str],
    name: Callable[[RunSummary], str],
) -> str | None:
    wa, wb = run_a.words_per_second, run_b.words_per_second
    if wa and wb and wa > 0 and wb > 0:
        faster, slower = (run_b, run_a) if wb > wa else (run_a, run_b)
        fast_v, slow_v = (wb, wa) if wb > wa else (wa, wb)
        pct = (fast_v - slow_v) / slow_v * 100
        if pct < REL_THRESHOLD_PERCENT:
            return _format(templates, "speed_tie")
        return _format(
            templates,
            "faster",
            run=name(faster),
            pct=round(pct),
            fast=round(fast_v, 1),
            slow=round(slow_v, 1),
        )

    # Fallback to wall-clock duration when throughput is unavailable.
    da, db = run_a.duration_seconds, run_b.duration_seconds
    if da and db and da > 0 and db > 0:
        faster, slower = (run_b, run_a) if db < da else (run_a, run_b)
        fast_v, slow_v = (db, da) if db < da else (da, db)
        pct = (slow_v - fast_v) / slow_v * 100
        if pct < REL_THRESHOLD_PERCENT:
            return _format(templates, "speed_tie")
        return _format(
            templates,
            "faster_duration",
            run=name(faster),
            pct=round(pct),
            fast=round(fast_v, 2),
            slow=round(slow_v, 2),
        )
    return None


def _lower_is_better_insight(
    run_a: RunSummary,
    run_b: RunSummary,
    attr: str,
    template_key: str,
    templates: dict[str, str],
    name: Callable[[RunSummary], str],
    min_abs: float,
) -> str | None:
    a, b = getattr(run_a, attr), getattr(run_b, attr)
    if a is None or b is None:
        return None
    if abs(a - b) < min_abs:
        return None
    delta = _relative_delta(a, b)
    if delta is not None and abs(delta) < REL_THRESHOLD_PERCENT:
        return None
    winner, low, high = (run_a, a, b) if a < b else (run_b, b, a)
    return _format(
        templates,
        template_key,
        run=name(winner),
        low=round(low, 1),
        high=round(high, 1),
    )


def _gpu_insight(
    run_a: RunSummary,
    run_b: RunSummary,
    templates: dict[str, str],
    name: Callable[[RunSummary], str],
) -> str | None:
    a, b = run_a.gpu_avg, run_b.gpu_avg
    if a is None or b is None:
        return None
    if abs(a - b) < 5.0:
        return None
    busier, high, low = (run_a, a, b) if a > b else (run_b, b, a)
    return _format(
        templates,
        "gpu_busier",
        run=name(busier),
        high=round(high, 1),
        low=round(low, 1),
    )


def _build_recommendation(
    run_a: RunSummary,
    run_b: RunSummary,
    templates: dict[str, str],
    name: Callable[[RunSummary], str],
) -> str:
    if run_a.success != run_b.success:
        winner = run_a if run_a.success else run_b
        return _format(templates, "recommend", run=name(winner)) or ""

    winner = _better_run(run_a, run_b)
    if winner is None:
        return _format(templates, "recommend_tie") or ""
    return _format(templates, "recommend", run=name(winner)) or ""


def _better_run(run_a: RunSummary, run_b: RunSummary) -> RunSummary | None:
    # Primary: throughput. Tiebreaker: lower average RAM.
    wa, wb = run_a.words_per_second, run_b.words_per_second
    if wa and wb and wa > 0 and wb > 0:
        delta = _relative_delta(wa, wb)
        if delta is not None and abs(delta) >= REL_THRESHOLD_PERCENT:
            return run_b if wb > wa else run_a

    ra, rb = run_a.ram_avg, run_b.ram_avg
    if ra is not None and rb is not None:
        delta = _relative_delta(ra, rb)
        if delta is not None and abs(delta) >= REL_THRESHOLD_PERCENT:
            return run_a if ra < rb else run_b

    return None


def _relative_delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or a == 0:
        return None
    return (b - a) / abs(a) * 100


def _decide_better(
    a: float | None,
    b: float | None,
    lower_is_better: bool,
    delta: float | None,
) -> str | None:
    if a is None or b is None or a == b:
        return None
    if delta is not None and abs(delta) < REL_THRESHOLD_PERCENT:
        return None
    a_is_better = a < b if lower_is_better else a > b
    return "A" if a_is_better else "B"


def _section(locale: dict[str, Any], key: str) -> dict[str, str]:
    compare = locale.get("compare")
    if isinstance(compare, dict):
        value = compare.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _format(templates: dict[str, str], key: str, **params: Any) -> str | None:
    template = templates.get(key)
    if not template:
        return None
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template
