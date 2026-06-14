from __future__ import annotations

import json
from pathlib import Path

import pytest

from doctor.cli import main


def test_estimate_cli_reports_no_fit(capsys):
    exit_code = main(
        [
            "estimate",
            "--model",
            "qwen2.5-32b",
            "--quant",
            "q4_k_m",
            "--vram",
            "12",
            "--ram",
            "32",
            "--lang",
            "en",
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Model Fit Estimate" in out
    assert "does not fit GPU" in out


def test_estimate_cli_errors_on_unparseable_model(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["estimate", "--model", "mistral-latest", "--vram", "12", "--lang", "en"])
    err = capsys.readouterr().err

    assert exc.value.code == 2
    assert "ERROR" in err


def test_estimate_cli_reads_limits_from_hardware_json(tmp_path, capsys):
    profile = tmp_path / "hardware.json"
    profile.write_text(
        json.dumps(
            {
                "gpus": [{"name": "RTX 4090", "vram_total_mb": 24576.0, "driver_version": "1"}],
                "ram_total_gb": 64.0,
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "estimate",
            "--model",
            "llama3-7b",
            "--quant",
            "q4_k_m",
            "--context",
            "2048",
            "--hardware",
            str(profile),
            "--lang",
            "en",
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "fits GPU" in out
    assert "24 GB" in out
