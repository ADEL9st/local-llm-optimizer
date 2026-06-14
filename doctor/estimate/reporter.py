from __future__ import annotations

from typing import Any

from doctor.estimate.model import FitEstimate


class EstimateReporter:
    def __init__(self, locale: dict[str, Any]):
        estimate = locale.get("estimate", {})
        self.title = estimate.get("title", "Model Fit Estimate")
        self.labels = estimate.get("labels", {})
        self.status_text = estimate.get("status", {})
        self.suggestion_text = estimate.get("suggestions", {})
        self.note_text = estimate.get("notes", {})

    def render(self, estimate: FitEstimate) -> str:
        text = "\n".join(self._lines(estimate))
        print(text)
        return text

    def _lines(self, estimate: FitEstimate) -> list[str]:
        labels = self.labels
        unknown = labels.get("unknown", "unknown")
        not_detected = labels.get("not_detected", "not detected")
        tokens = labels.get("tokens", "tokens")
        bit_unit = labels.get("bit_per_weight", "bit/weight")
        inputs = estimate.inputs

        rows: list[tuple[str, str]] = [
            (labels.get("model", "Model"), inputs.model),
            (labels.get("parameters", "Parameters"), f"{_trim(inputs.params_billion)} B"),
            (
                labels.get("quantization", "Quantization"),
                f"{inputs.quant} ({_trim(inputs.bits_per_weight)} {bit_unit})",
            ),
            (labels.get("context", "Context"), f"{inputs.context_tokens} {tokens}"),
            (labels.get("weights", "Weights"), f"{_trim(estimate.weights_gb)} GB"),
            (labels.get("kv_cache", "KV cache"), f"{_trim(estimate.kv_cache_gb)} GB"),
            (labels.get("overhead", "Overhead"), f"{_trim(estimate.overhead_gb)} GB"),
            (labels.get("estimated_need", "Estimated need"), f"{_trim(estimate.total_gb)} GB"),
            (labels.get("your_vram", "Your VRAM"), _limit(estimate.vram_gb, not_detected)),
            (labels.get("your_ram", "Your RAM"), _limit(estimate.ram_gb, not_detected)),
        ]

        width = max(len(label) for label, _ in rows)
        lines = ["", f"=== {self.title} ==="]
        lines += [f"{label.ljust(width)} : {value}" for label, value in rows]

        lines.append("")
        status_label = labels.get("status_title", "Status")
        status_value = self.status_text.get(estimate.status, estimate.status)
        lines.append(f"{status_label}: {status_value}")

        lines.append("")
        lines.append(f"--- {labels.get('suggested_title', 'Suggested')} ---")
        for suggestion in estimate.suggestions:
            template = self.suggestion_text.get(suggestion.key, suggestion.key)
            lines.append(f"- {_format(template, suggestion.data)}")

        notes = [self.note_text.get(note) for note in estimate.notes]
        notes = [note for note in notes if note]
        if notes:
            lines.append("")
            lines.append(f"--- {labels.get('notes_title', 'Notes')} ---")
            lines += [f"- {note}" for note in notes]

        return lines


def _limit(value: float | None, not_detected: str) -> str:
    return f"{_trim(value)} GB" if value is not None else not_detected


def _format(template: str, data: dict[str, Any]) -> str:
    try:
        return template.format(**data)
    except (KeyError, IndexError):
        return template


def _trim(value: float) -> float | int:
    rounded = round(value, 2)
    return int(rounded) if rounded == int(rounded) else rounded
