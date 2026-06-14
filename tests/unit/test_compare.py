import json
from pathlib import Path

import pytest

from doctor.compare import RunLoadError, compare_runs, load_run_summary
from doctor.core.config import load_locale

EN = load_locale("en")


def _run_payload(
    *,
    backend="ollama",
    model="llama3",
    success=True,
    duration=10.0,
    words_per_second=20.0,
    cpu_avg=30.0,
    ram_avg=50.0,
    gpu_avg=60.0,
    vram_used_avg=4000.0,
    vram_peak_ratio=40.0,
    max_tokens=256,
):
    return {
        "schema_version": "0.2",
        "config": {"backend": backend, "model": model, "max_tokens": max_tokens},
        "backend_result": {
            "backend": backend,
            "model": model,
            "success": success,
            "duration_seconds": duration,
            "words_per_second": words_per_second,
            "chars_per_second": words_per_second * 5,
            "output_words": 100,
        },
        "diagnosis": {
            "summaries": {
                "cpu_percent": {"avg": cpu_avg, "max": cpu_avg, "min": cpu_avg},
                "ram_percent": {"avg": ram_avg, "max": ram_avg, "min": ram_avg},
                "gpu_util_percent": {"avg": gpu_avg, "max": gpu_avg, "min": gpu_avg},
                "vram_used_mb": {"avg": vram_used_avg, "max": vram_used_avg, "min": vram_used_avg},
            },
            "vram_peak_ratio_percent": vram_peak_ratio,
        },
    }


def _write_run(tmp_path: Path, name: str, payload: dict) -> Path:
    run_dir = tmp_path / name
    run_dir.mkdir()
    (run_dir / "run.json").write_text(json.dumps(payload), encoding="utf-8")
    return run_dir


def test_loader_reads_directory_and_summaries(tmp_path):
    run_dir = _write_run(tmp_path, "run_a", _run_payload(model="qwen", gpu_avg=12.5))
    summary = load_run_summary(run_dir, "A")

    assert summary.label == "A"
    assert summary.model == "qwen"
    assert summary.backend == "ollama"
    assert summary.max_tokens == 256
    assert summary.gpu_avg == 12.5
    assert summary.source == run_dir / "run.json"


def test_loader_accepts_direct_run_json_path(tmp_path):
    run_dir = _write_run(tmp_path, "run_a", _run_payload())
    summary = load_run_summary(run_dir / "run.json", "A")
    assert summary.success is True


def test_loader_handles_missing_diagnosis(tmp_path):
    payload = _run_payload()
    del payload["diagnosis"]
    run_dir = _write_run(tmp_path, "run_a", payload)

    summary = load_run_summary(run_dir, "A")
    assert summary.gpu_avg is None
    assert summary.ram_avg is None
    assert summary.duration_seconds == 10.0


def test_loader_raises_for_missing_path(tmp_path):
    with pytest.raises(RunLoadError):
        load_run_summary(tmp_path / "nope", "A")


def test_compare_flags_faster_run_and_recommends_it(tmp_path):
    slow = load_run_summary(
        _write_run(tmp_path, "slow", _run_payload(words_per_second=10.0, duration=20.0)), "A"
    )
    fast = load_run_summary(
        _write_run(tmp_path, "fast", _run_payload(words_per_second=20.0, duration=10.0)), "B"
    )

    result = compare_runs(slow, fast, EN)

    throughput = next(r for r in result.rows if r.key == "words_per_second")
    assert throughput.better == "B"
    assert throughput.delta_percent == 100.0

    assert any("100% faster" in line for line in result.insights)
    assert "Run B" in result.recommendation


def test_compare_detects_lower_ram_run(tmp_path):
    high_ram = load_run_summary(
        _write_run(tmp_path, "a", _run_payload(ram_avg=80.0)), "A"
    )
    low_ram = load_run_summary(
        _write_run(tmp_path, "b", _run_payload(ram_avg=40.0)), "B"
    )

    result = compare_runs(high_ram, low_ram, EN)

    ram_row = next(r for r in result.rows if r.key == "ram_avg")
    assert ram_row.better == "B"
    assert any("uses less RAM" in line for line in result.insights)


def test_compare_handles_missing_metrics_as_tie(tmp_path):
    payload = _run_payload()
    del payload["diagnosis"]
    a = load_run_summary(_write_run(tmp_path, "a", payload), "A")
    b = load_run_summary(_write_run(tmp_path, "b", payload), "B")

    result = compare_runs(a, b, EN)

    gpu_row = next(r for r in result.rows if r.key == "gpu_avg")
    assert gpu_row.a is None
    assert gpu_row.better is None


def test_compare_recommends_successful_run_over_failed(tmp_path):
    ok = load_run_summary(_write_run(tmp_path, "ok", _run_payload(success=True)), "A")
    failed = load_run_summary(
        _write_run(tmp_path, "failed", _run_payload(success=False)), "B"
    )

    result = compare_runs(ok, failed, EN)
    assert "Run A" in result.recommendation
    assert any("did not complete" in line for line in result.insights)
