from __future__ import annotations

import json
from pathlib import Path

import pytest

from doctor.cli import main


def _write_run(tmp_path: Path, name: str, *, words_per_second: float, duration: float) -> Path:
    run_dir = tmp_path / name
    run_dir.mkdir()
    payload = {
        "schema_version": "0.2",
        "config": {"backend": "ollama", "model": "llama3", "max_tokens": 256},
        "backend_result": {
            "success": True,
            "duration_seconds": duration,
            "words_per_second": words_per_second,
            "chars_per_second": words_per_second * 5,
            "output_words": 100,
        },
        "diagnosis": {
            "summaries": {
                "cpu_percent": {"avg": 30.0, "max": 35.0, "min": 25.0},
                "ram_percent": {"avg": 50.0, "max": 55.0, "min": 45.0},
                "gpu_util_percent": {"avg": 60.0, "max": 70.0, "min": 50.0},
                "vram_used_mb": {"avg": 4000.0, "max": 4200.0, "min": 3800.0},
            },
            "vram_peak_ratio_percent": 40.0,
        },
    }
    (run_dir / "run.json").write_text(json.dumps(payload), encoding="utf-8")
    return run_dir


def test_compare_cli_renders_table_and_recommendation(tmp_path, capsys):
    slow = _write_run(tmp_path, "slow", words_per_second=10.0, duration=20.0)
    fast = _write_run(tmp_path, "fast", words_per_second=20.0, duration=10.0)

    exit_code = main(["compare", str(slow), str(fast), "--lang", "en"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Run Comparison" in out
    assert "Throughput (words/s)" in out
    assert "faster" in out
    assert "Use Run B config" in out


def test_compare_cli_errors_on_missing_run(tmp_path, capsys):
    ok = _write_run(tmp_path, "ok", words_per_second=10.0, duration=20.0)

    with pytest.raises(SystemExit) as exc:
        main(["compare", str(ok), str(tmp_path / "missing"), "--lang", "en"])
    err = capsys.readouterr().err

    assert exc.value.code == 2
    assert "ERROR" in err
